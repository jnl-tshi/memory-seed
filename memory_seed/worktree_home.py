"""Persistent home worktree per agent (design discovery 2026-09-25).

Each agent owns one long-lived worktree at ``<namespace>/home`` (``<namespace>/<user>/home`` once a
second participant is registered). Work happens on task branches inside it; after a merge the home
is *parked* - HEAD detached at the integration commit - instead of being removed. A second live
session of the same agent gets an ``overflow-<id>`` worktree, which keeps the old remove-after-merge
lifecycle.

Busy/free is read from git itself (a checked-out branch is busy, a detached HEAD is free). Liveness
comes from a small lease file in the home's git administration directory, so it is never tracked,
never shows as a dirty file, and disappears with the worktree registration.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

HOME_NAME = "home"
OVERFLOW_PREFIX = "overflow-"
LEASE_FILE = "memory-seed-lease.json"
LEASE_SCHEMA = 1
DEFAULT_LEASE_STALE_MINUTES = 180
DEFAULT_TOUCH_INTERVAL_SECONDS = 60
_BRANCH_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

ACTIONS = ("status", "claim", "park", "release")


@dataclass
class WorktreeHomeResult:
    agent: str
    action: str
    state: str
    path: str | None = None
    branch: str | None = None
    dirty: bool | None = None
    lease: dict | None = None
    session_id: str | None = None
    overflow_path: str | None = None
    action_taken: str | None = None
    next_step: str | None = None
    exit_code: int = 0
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "action": self.action,
            "state": self.state,
            "path": self.path,
            "branch": self.branch,
            "dirty": self.dirty,
            "lease": self.lease,
            "session_id": self.session_id,
            "overflow_path": self.overflow_path,
            "action_taken": self.action_taken,
            "next_step": self.next_step,
            "exit_code": self.exit_code,
            "issues": list(self.issues),
        }


# --- paths --------------------------------------------------------------------


def _core():
    from . import core

    return core


def _repo_root(cwd: Path | str) -> Path | None:
    """The primary checkout, whether ``cwd`` is the primary or any linked worktree."""
    core = _core()
    code, porcelain = core._git_text(Path(cwd).resolve(), ("worktree", "list", "--porcelain"))
    if code != 0:
        return None
    items = core._parse_worktree_list(porcelain)
    if not items:
        return None
    return Path(items[0]["path"]).resolve()


def _namespaces(root: Path) -> dict[str, str]:
    return dict(_core()._worktree_guard_config_for(root).namespaces)


def _user_segment(root: Path) -> str | None:
    return _core()._multi_user_segment(root)


def home_worktree_path(root: Path | str, agent: str) -> Path:
    root = Path(root).resolve()
    agent = agent.strip().lower()
    namespace = _namespaces(root).get(agent) or f".{agent}/worktrees"
    base = root / namespace
    user = _user_segment(root)
    return (base / user / HOME_NAME) if user else (base / HOME_NAME)


def is_home_worktree(root: Path | str, path: Path | str) -> str | None:
    """Return the owning agent when ``path`` is a home worktree (``<ns>/home`` or ``<ns>/<user>/home``)."""
    core = _core()
    root = Path(root).resolve()
    try:
        target = Path(path).resolve()
    except (OSError, ValueError):
        return None
    if target.name.casefold() != HOME_NAME:
        return None
    for agent, namespace in sorted(_namespaces(root).items()):
        namespace_root = root / namespace
        if not core._is_relative_to_casefold(target, namespace_root):
            continue
        depth = len(target.parts) - len(namespace_root.resolve().parts)
        if depth in (1, 2):
            return agent
    return None


def _overflow_path(root: Path, agent: str) -> Path:
    home = home_worktree_path(root, agent)
    return home.parent / f"{OVERFLOW_PREFIX}{secrets.token_hex(3)}"


# --- lease ----------------------------------------------------------------------


def home_admin_dir(home: Path | str) -> Path | None:
    """The worktree's private git directory (never guessed from the folder name)."""
    core = _core()
    home = Path(home)
    code, git_dir = core._git_text(home, ("rev-parse", "--git-dir"))
    if code != 0 or not git_dir:
        return None
    admin = Path(git_dir)
    if not admin.is_absolute():
        admin = home / admin
    return admin.resolve()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def read_lease(home: Path | str) -> dict | None:
    admin = home_admin_dir(home)
    if admin is None:
        return None
    try:
        payload = json.loads((admin / LEASE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def lease_is_fresh(lease: dict | None, stale_minutes: int, now: datetime | None = None) -> bool:
    if not lease:
        return False
    last = _parse_time(lease.get("last_active")) or _parse_time(lease.get("started_at"))
    if last is None:
        return False
    return ((now or _now()) - last).total_seconds() < stale_minutes * 60


def _write_lease(home: Path, lease: dict, *, exclusive: bool) -> bool:
    admin = home_admin_dir(home)
    if admin is None:
        return False
    target = admin / LEASE_FILE
    data = json.dumps(lease, sort_keys=True, indent=2)
    if exclusive:
        try:
            fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(data)
        return True
    temp = admin / f"{LEASE_FILE}.{secrets.token_hex(4)}.tmp"
    temp.write_text(data, encoding="utf-8")
    os.replace(temp, target)
    current = read_lease(home)
    return bool(current) and current.get("session_id") == lease.get("session_id")


def _lease_write_issue(home: Path, exc: OSError) -> str:
    """Explain a lease write the OS refused (e.g. an agent sandbox that blocks `.git` writes)."""
    admin = home_admin_dir(home)
    return (
        f"could not write the home lease in {admin or 'the worktree git directory'}: {exc}. "
        "The home was not claimed. If an agent sandbox blocks writes under .git, rerun the claim with "
        "the host's write approval."
    )


def release_lease(home: Path | str) -> bool:
    admin = home_admin_dir(home)
    if admin is None:
        return False
    try:
        (admin / LEASE_FILE).unlink()
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True


def touch_lease(
    home: Path | str, session_id: str, *, min_interval_seconds: int = DEFAULT_TOUCH_INTERVAL_SECONDS
) -> bool:
    """Refresh ``last_active`` when ``session_id`` owns the lease. Never raises."""
    try:
        lease = read_lease(home)
        if not lease or lease.get("session_id") != session_id:
            return False
        now = _now()
        last = _parse_time(lease.get("last_active"))
        if last is not None and (now - last).total_seconds() < min_interval_seconds:
            return True
        lease["last_active"] = now.isoformat()
        return _write_lease(Path(home), lease, exclusive=False)
    except Exception:
        return False


def heartbeat(cwd: Path | str, *, min_interval_seconds: int = DEFAULT_TOUCH_INTERVAL_SECONDS) -> bool:
    """Refresh the lease of the home worktree containing ``cwd``, if any. Never raises.

    Called from the per-tool hook, so it avoids git subprocesses: it finds the checkout's
    ``.git`` pointer file by walking up, and touches the lease only when the checkout folder
    is named ``home``. Whoever works inside the home is its live holder - overflow sessions
    work elsewhere - so the lease's session id is not re-checked here.
    """
    try:
        current = Path(cwd).resolve()
        for candidate in (current, *current.parents):
            marker = candidate / ".git"
            if marker.is_dir():
                return False  # primary checkout
            if not marker.is_file():
                continue
            if candidate.name.casefold() != HOME_NAME:
                return False
            text = marker.read_text(encoding="utf-8").strip()
            if not text.lower().startswith("gitdir:"):
                return False
            admin = Path(text.split(":", 1)[1].strip())
            if not admin.is_absolute():
                admin = candidate / admin
            lease_path = admin / LEASE_FILE
            if not lease_path.is_file():
                return False
            age = _now().timestamp() - lease_path.stat().st_mtime
            if age < min_interval_seconds:
                return True
            lease = json.loads(lease_path.read_text(encoding="utf-8"))
            if not isinstance(lease, dict):
                return False
            lease["last_active"] = _now().isoformat()
            temp = admin / f"{LEASE_FILE}.{secrets.token_hex(4)}.tmp"
            temp.write_text(json.dumps(lease, sort_keys=True, indent=2), encoding="utf-8")
            os.replace(temp, lease_path)
            return True
        return False
    except Exception:
        return False


def _new_lease(agent: str, user: str | None, session_id: str, branch: str | None) -> dict:
    now = _now().isoformat()
    return {
        "schema": LEASE_SCHEMA,
        "agent": agent,
        "user": user,
        "session_id": session_id,
        "branch": branch,
        "started_at": now,
        "last_active": now,
    }


# --- git helpers ------------------------------------------------------------------


def _registered(root: Path, path: Path) -> bool:
    core = _core()
    code, porcelain = core._git_text(root, ("worktree", "list", "--porcelain"))
    if code != 0:
        return False
    want = core._casefold_parts(path.resolve())
    return any(
        core._casefold_parts(Path(item.get("path", "")).resolve()) == want
        for item in core._parse_worktree_list(porcelain)
    )


def _base_ref(root: Path) -> str:
    """The integration branch homes park on: ``main`` when it exists, else the primary's branch."""
    core = _core()
    code, _ = core._git_text(root, ("rev-parse", "--verify", "--quiet", "refs/heads/main"))
    if code == 0:
        return "main"
    code, branch = core._git_text(root, ("branch", "--show-current"))
    return branch if code == 0 and branch else "HEAD"


def _branch_of(worktree: Path) -> str | None:
    code, branch = _core()._git_text(worktree, ("branch", "--show-current"))
    return branch if code == 0 and branch else None


def _is_dirty(worktree: Path) -> bool | None:
    code, status = _core()._git_text(worktree, ("status", "--porcelain"))
    if code != 0:
        return None
    return bool(status.strip())


def _merged_into(root: Path, branch: str, base: str) -> bool:
    code, _ = _core()._git_text(root, ("merge-base", "--is-ancestor", branch, base))
    return code == 0


def _valid_branch(agent: str, branch: str | None) -> str | None:
    if not branch:
        return "a task branch is required (--branch <agent>/<kind>/<topic>)"
    parts = branch.split("/")
    if len(parts) < 3 or parts[0] != agent or not all(_BRANCH_SEGMENT_RE.match(p) for p in parts):
        return f"branch '{branch}' must look like {agent}/<kind>/<topic>"
    return None


def _ensure_locally_ignored(root: Path, path: Path) -> None:
    """Keep a new worktree folder out of the primary's ``git status``.

    Uses ``.git/info/exclude`` rather than ``.gitignore`` so creating a home never dirties a
    tracked file in the shared primary checkout.
    """
    core = _core()
    code, _ = core._git_text(root, ("check-ignore", "-q", str(path)))
    if code == 0:
        return
    code, common = core._git_text(root, ("rev-parse", "--git-common-dir"))
    if code != 0 or not common:
        return
    common_dir = Path(common)
    if not common_dir.is_absolute():
        common_dir = root / common_dir
    exclude = common_dir / "info" / "exclude"
    try:
        relative = path.resolve().relative_to(root.resolve()).parent.as_posix()
    except ValueError:
        return
    entry = f"/{relative}/"
    try:
        existing = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
        if entry in existing.splitlines():
            return
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open("a", encoding="utf-8") as handle:
            if existing and not existing.endswith("\n"):
                handle.write("\n")
            handle.write(f"# memory-seed agent worktrees\n{entry}\n")
    except OSError:
        return


def park_home(root: Path | str, home: Path | str, target: str | None = None) -> tuple[bool, str]:
    """Detach a clean home at ``target`` (default: the integration branch) and release its lease."""
    core = _core()
    root = Path(root).resolve()
    home = Path(home)
    if _is_dirty(home):
        return False, "home worktree has uncommitted or untracked changes"
    commit = target or _base_ref(root)
    code, output = core._git_text(home, ("checkout", "--detach", commit))
    if code != 0:
        return False, f"could not park home at {commit}: {output or 'git checkout failed'}"
    release_lease(home)
    return True, f"parked home at {commit}"


# --- the lifecycle -------------------------------------------------------------------


def _stale_minutes(root: Path) -> int:
    return int(getattr(_core()._worktree_guard_config_for(root), "home_lease_stale_minutes", DEFAULT_LEASE_STALE_MINUTES))


def _observe(result: WorktreeHomeResult, root: Path, home: Path, session: str | None, stale: int) -> None:
    """Fill ``state`` and facts from git + the lease, without changing anything."""
    result.path = str(home)
    if not _registered(root, home):
        result.state = "missing"
        return
    result.branch = _branch_of(home)
    result.dirty = _is_dirty(home)
    result.lease = read_lease(home)
    fresh = lease_is_fresh(result.lease, stale)
    owner = (result.lease or {}).get("session_id")
    if fresh and (session is None or owner == session):
        result.state = "claimed"
        return
    if fresh:
        result.state = "busy"
        return
    if result.branch is None:
        result.state = "stale-dirty" if result.dirty else "parked"
        return
    if result.dirty:
        result.state = "stale-dirty"
    elif _merged_into(root, result.branch, _base_ref(root)):
        result.state = "merged"
    else:
        result.state = "stale-resumable"


def worktree_home(
    cwd: Path | str = ".",
    *,
    agent: str,
    action: str = "status",
    branch: str | None = None,
    session: str | None = None,
    resume: bool = False,
) -> WorktreeHomeResult:
    agent = agent.strip().lower()
    result = WorktreeHomeResult(agent=agent, action=action, state="unknown")
    if action not in ACTIONS:
        result.issues.append(f"unknown action '{action}'")
        result.exit_code = 2
        return result
    root = _repo_root(cwd)
    if root is None:
        result.issues.append("not inside a git repository")
        result.exit_code = 2
        return result
    home = home_worktree_path(root, agent)
    stale = _stale_minutes(root)
    if action == "claim" and not session:
        # A claim always has an identity, so a live foreign lease reads as busy, never as ours.
        session = f"s-{secrets.token_hex(4)}"
    result.session_id = session
    _observe(result, root, home, session, stale)

    if action == "status":
        if session and result.lease and result.lease.get("session_id") == session:
            touch_lease(home, session, min_interval_seconds=0)
        result.next_step = _next_step(result)
        return result

    if action == "release":
        if result.state != "missing":
            release_lease(home)
            result.lease = None
            result.action_taken = "released"
        return result

    if result.state == "missing":
        if home.exists():
            result.issues.append(f"{home} exists but is not a registered worktree; reconcile it first")
            result.exit_code = 2
            return result
        home.parent.mkdir(parents=True, exist_ok=True)
        _ensure_locally_ignored(root, home)
        code, output = _core()._git_text(root, ("worktree", "add", "--detach", str(home), _base_ref(root)))
        if code != 0:
            result.issues.append(f"could not create home worktree: {output}")
            result.exit_code = 2
            return result
        result.action_taken = "created"
        _observe(result, root, home, session, stale)

    if action == "park":
        if result.state in {"stale-dirty"} or result.dirty:
            result.issues.append("home has uncommitted or untracked changes; commit or hand them to the user")
            result.exit_code = 3
            return result
        if result.branch and not _merged_into(root, result.branch, _base_ref(root)):
            result.issues.append(f"branch '{result.branch}' is not merged into {_base_ref(root)}; land it first")
            result.exit_code = 2
            return result
        ok, detail = park_home(root, home)
        if not ok:
            result.issues.append(detail)
            result.exit_code = 2
            return result
        result.action_taken = (result.action_taken + "+parked") if result.action_taken else "parked"
        _observe(result, root, home, session, stale)
        return result

    # --- claim ---
    user = _user_segment(root)

    if result.state == "busy":
        problem = _valid_branch(agent, branch)
        if problem:
            result.issues.append(problem)
            result.exit_code = 2
            return result
        overflow = _overflow_path(root, agent)
        code, output = _core()._git_text(root, ("worktree", "add", "-b", branch, str(overflow), _base_ref(root)))
        if code != 0:
            result.issues.append(f"home is busy and the overflow worktree could not be created: {output}")
            result.exit_code = 2
            return result
        result.overflow_path = str(overflow)
        result.action_taken = "overflow"
        result.next_step = f"Home is in use by another live session; work in {overflow} (removed after merge)."
        return result

    if result.state == "claimed" and result.lease and result.lease.get("session_id") == session:
        if branch and result.branch and branch != result.branch:
            result.issues.append(
                f"this session already holds the home on '{result.branch}'; land and park it before starting '{branch}'"
            )
            result.exit_code = 2
        result.next_step = _next_step(result)
        return result

    if result.state == "stale-dirty":
        result.issues.append(
            "home has uncommitted or untracked changes and no live session; leftover work is never "
            "committed or discarded automatically - review it with the user"
        )
        result.exit_code = 3
        return result

    if result.state == "stale-resumable":
        if not resume:
            result.issues.append(
                f"home holds unmerged branch '{result.branch}' from an inactive session; "
                "rerun with --resume to continue it, or ask the user"
            )
            result.exit_code = 2
            return result
        try:
            taken = _write_lease(home, _new_lease(agent, user, session, result.branch), exclusive=False)
        except OSError as exc:
            result.issues.append(_lease_write_issue(home, exc))
            result.exit_code = 2
            return result
        if not taken:
            result.issues.append("could not take over the stale lease")
            result.exit_code = 2
            return result
        result.action_taken = "resumed"
        _observe(result, root, home, session, stale)
        return result

    if result.state == "merged":
        ok, detail = park_home(root, home)
        if not ok:
            result.issues.append(detail)
            result.exit_code = 2
            return result
        _observe(result, root, home, session, stale)

    # parked and free
    problem = _valid_branch(agent, branch)
    if problem:
        result.issues.append(problem)
        result.exit_code = 2
        return result
    stale_lease = result.lease is not None
    lease = _new_lease(agent, user, session, branch)
    try:
        written = _write_lease(home, lease, exclusive=not stale_lease)
    except OSError as exc:
        result.issues.append(_lease_write_issue(home, exc))
        result.exit_code = 2
        return result
    if not written:
        result.issues.append("another session claimed the home at the same moment; retry to get an overflow worktree")
        result.exit_code = 2
        return result
    code, output = _core()._git_text(home, ("checkout", "-b", branch, _base_ref(root)))
    if code != 0:
        release_lease(home)
        result.issues.append(f"could not create task branch '{branch}': {output}")
        result.exit_code = 2
        return result
    result.action_taken = (result.action_taken + "+claimed") if result.action_taken else "claimed"
    _observe(result, root, home, session, stale)
    result.next_step = _next_step(result)
    return result


def _next_step(result: WorktreeHomeResult) -> str:
    if result.state == "missing":
        return "Run `memory-seed worktree home --claim --branch <agent>/<kind>/<topic>` to create and claim it."
    if result.state == "parked":
        return "Free. Claim it with --claim --branch <agent>/<kind>/<topic> before editing."
    if result.state == "claimed":
        return f"Enter {result.path} (Claude: EnterWorktree with this path; others: cd) and work on '{result.branch}'."
    if result.state == "busy":
        return "Another live session holds the home; --claim will give you an overflow worktree."
    if result.state == "merged":
        return "Its branch is merged; --park (or --claim) returns it to the free state."
    if result.state == "stale-resumable":
        return "An inactive session left an unmerged branch; --claim --resume continues it."
    if result.state == "stale-dirty":
        return "Uncommitted leftovers with no live session; review them with the user before anything else."
    return ""


def format_worktree_home(result: WorktreeHomeResult) -> str:
    lines = [
        f"Home ({result.agent}): {result.path or '(unavailable)'}",
        f"State: {result.state}",
        f"Branch: {result.branch or '(detached)'}",
    ]
    if result.dirty is not None:
        lines.append(f"Dirty: {'yes' if result.dirty else 'no'}")
    if result.lease:
        lines.append(
            f"Lease: session {result.lease.get('session_id')} last active {result.lease.get('last_active')}"
        )
    if result.session_id:
        lines.append(f"Session: {result.session_id}")
    if result.action_taken:
        lines.append(f"Action: {result.action_taken}")
    if result.overflow_path:
        lines.append(f"Overflow worktree: {result.overflow_path}")
    for issue in result.issues:
        lines.append(f"Issue: {issue}")
    if result.next_step:
        lines.append(f"Next: {result.next_step}")
    return "\n".join(lines)
