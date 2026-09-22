"""Read-only inventory of local branch sessions and attached worktrees.

Usage:
    python scripts/branch_session_inventory.py
    python scripts/branch_session_inventory.py --branch codex/feature/example
    python scripts/branch_session_inventory.py --all --json

An entry is unique when its ``entry_id`` is absent from the selected base tree.
This is an inventory, not a merge, deletion, or content-equivalence verdict.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path, PurePosixPath


HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) - (.+)$")
ENTRY_ID = re.compile(r"^\s*entry_id:\s*(\S+)\s*$")
BRANCH = re.compile(r"^\s*branch:\s*(\S+)\s*$")
GREP_PATTERN = r"^(## [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2} -|entry_id:|branch:)"


def git(root: Path, *args: str, allow_no_match: bool = False) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode and not (allow_no_match and result.returncode == 1):
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def is_session_file(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return (
        len(parts) >= 3
        and parts[:2] == (".memory-seed", "sessions")
        and parts[2] not in {"links", "topics", "diagrams"}
        and parts[-1].endswith(".md")
    )


def parse_session_text(text: str, path: str) -> list[dict[str, str]]:
    """Extract entry identity, authored branch, and heading from a session file."""
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        heading = HEADING.match(line)
        if heading:
            current = {
                "timestamp": heading.group(1),
                "title": heading.group(2),
                "path": path,
            }
            continue
        if current is None:
            continue
        entry_id = ENTRY_ID.match(line)
        if entry_id:
            current["id"] = entry_id.group(1)
            entries.append(current)
            continue
        branch = BRANCH.match(line)
        if branch and "id" in current:
            current["authored_branch"] = branch.group(1)
    return entries


def tree_sessions(root: Path, ref: str) -> dict[str, dict[str, str]]:
    """Read headings and IDs from one Git tree without checking it out."""
    output = git(
        root,
        "grep",
        "-n",
        "-I",
        "-E",
        GREP_PATTERN,
        ref,
        "--",
        ".memory-seed/sessions",
        allow_no_match=True,
    )
    entries: dict[str, dict[str, str]] = {}
    current_by_path: dict[str, dict[str, str]] = {}
    for row in output.splitlines():
        prefix = f"{ref}:"
        if not row.startswith(prefix):
            continue
        try:
            path, _line, value = row[len(prefix) :].split(":", 2)
        except ValueError:
            continue
        if not is_session_file(path):
            continue
        heading = HEADING.match(value)
        if heading:
            current_by_path[path] = {
                "timestamp": heading.group(1),
                "title": heading.group(2),
                "path": path,
            }
            continue
        current = current_by_path.get(path)
        if current is None:
            continue
        entry_id = ENTRY_ID.match(value)
        if entry_id:
            current["id"] = entry_id.group(1)
            entries[current["id"]] = current
            continue
        branch = BRANCH.match(value)
        if branch and "id" in current:
            current["authored_branch"] = branch.group(1)
    return entries


def worktrees(root: Path) -> list[dict[str, object]]:
    blocks = git(root, "worktree", "list", "--porcelain").strip().split("\n\n")
    found: list[dict[str, object]] = []
    for block in blocks:
        fields: dict[str, str] = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            fields[key] = value
        if not fields.get("worktree"):
            continue
        path = Path(fields["worktree"])
        branch = fields.get("branch", "").removeprefix("refs/heads/") or None
        found.append(
            {
                "path": str(path),
                "branch": branch,
                "head": fields.get("HEAD", ""),
                "locked": "locked" in fields,
                "prunable": "prunable" in fields,
            }
        )
    return found


def live_sessions(path: Path) -> dict[str, dict[str, str]]:
    sessions = path / ".memory-seed" / "sessions"
    result: dict[str, dict[str, str]] = {}
    if not sessions.is_dir():
        return result
    for file in sessions.rglob("*.md"):
        relative = file.relative_to(path).as_posix()
        if not is_session_file(relative):
            continue
        for entry in parse_session_text(file.read_text(encoding="utf-8"), relative):
            result[entry["id"]] = entry
    return result


def _ordered(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(entries, key=lambda entry: (entry["timestamp"], entry["id"]))


def inspect_worktree(
    root: Path, item: dict[str, object], committed: dict[str, dict[str, str]]
) -> dict[str, object]:
    path = Path(str(item["path"]))
    dirty = git(root, "-C", str(path), "status", "--short", "--untracked-files=all")
    live = live_sessions(path)
    uncommitted = _ordered(
        [entry for key, entry in live.items() if key not in committed]
    )
    return {
        **item,
        "dirty_paths": dirty.splitlines(),
        "uncommitted_sessions": uncommitted,
    }


def build_inventory(
    root: Path, *, base: str = "main", selected: list[str] | None = None
) -> dict[str, object]:
    root = Path(git(root, "rev-parse", "--show-toplevel").strip())
    base_sha = git(root, "rev-parse", "--verify", f"{base}^{{commit}}").strip()
    main_entries = tree_sessions(root, base_sha)
    names = [
        name
        for name in git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines()
        if name != base
    ]
    if selected:
        missing = sorted(set(selected) - set(names))
        if missing:
            raise ValueError(f"unknown local branch(es): {', '.join(missing)}")
        names = [name for name in names if name in selected]
    attached = worktrees(root)
    branches: list[dict[str, object]] = []
    for name in names:
        head = git(root, "rev-parse", "--verify", f"{name}^{{commit}}").strip()
        branch_entries = tree_sessions(root, head)
        unique = _ordered(
            [entry for key, entry in branch_entries.items() if key not in main_entries]
        )
        authored = _ordered(
            [
                entry
                for entry in branch_entries.values()
                if entry.get("authored_branch") == name
            ]
        )
        base_only, branch_only = (
            int(value)
            for value in git(root, "rev-list", "--left-right", "--count", f"{base_sha}...{head}").split()
        )
        branch_worktrees: list[dict[str, object]] = []
        for item in attached:
            if item["branch"] != name:
                continue
            branch_worktrees.append(inspect_worktree(root, item, branch_entries))
        commits = [
            {"short_sha": line.split("\t", 1)[0], "subject": line.split("\t", 1)[1]}
            for line in git(root, "log", "--format=%h%x09%s", f"{base_sha}..{head}").splitlines()
            if "\t" in line
        ]
        branches.append(
            {
                "branch": name,
                "head": head,
                "ahead": branch_only,
                "behind": base_only,
                "unique_sessions": unique,
                "authored_sessions": authored,
                "commits": commits,
                "worktrees": branch_worktrees,
            }
        )
    detached = []
    for item in attached:
        if item["branch"] is not None:
            continue
        committed = tree_sessions(root, str(item["head"]))
        inspected = inspect_worktree(root, item, committed)
        inspected["unique_sessions"] = _ordered(
            [entry for key, entry in committed.items() if key not in main_entries]
        )
        detached.append(inspected)
    return {
        "base": base,
        "base_sha": base_sha,
        "branches": branches,
        "detached_worktrees": detached,
    }


def format_report(report: dict[str, object], *, show_all: bool = False, detail: bool = False) -> str:
    branches = report["branches"]
    assert isinstance(branches, list)
    lines = [
        f"Base: {report['base']} ({str(report['base_sha'])[:8]})",
        "Unique sessions mean entry_id absent from base; no content-equivalence or cleanup claim.",
    ]
    visible = [
        branch
        for branch in branches
        if show_all
        or detail
        or branch["ahead"]
        or branch["unique_sessions"]
        or any(wt["dirty_paths"] for wt in branch["worktrees"])
    ]
    lines.append(f"Showing {len(visible)} of {len(branches)} local branches")
    for branch in visible:
        dirty_count = sum(len(wt["dirty_paths"]) for wt in branch["worktrees"])
        lines.append(
            f"\n{branch['branch']} @ {str(branch['head'])[:8]}: "
            f"{branch['ahead']} commits ahead, {branch['behind']} behind, "
            f"{len(branch['unique_sessions'])} unique sessions, "
            f"{len(branch['worktrees'])} worktrees, {dirty_count} dirty paths"
        )
        if not detail:
            continue
        authored_ids = {entry["id"] for entry in branch["authored_sessions"]}
        unique_ids = {entry["id"] for entry in branch["unique_sessions"]}
        for entry in branch["authored_sessions"]:
            lines.append(
                f"  session {entry['timestamp']} {entry['id']} {entry['title']} "
                f"[{'unique' if entry['id'] in unique_ids else 'on base'}] "
                f"[{entry['path']}]"
            )
        for entry in branch["unique_sessions"]:
            if entry["id"] in authored_ids:
                continue
            lines.append(
                f"  session {entry['timestamp']} {entry['id']} {entry['title']} "
                "[unique; authored branch differs or is absent] "
                f"[{entry['path']}]"
            )
        for wt in branch["worktrees"]:
            lines.append(f"  worktree {wt['path']}" + (" [locked]" if wt["locked"] else ""))
            for path in wt["dirty_paths"]:
                lines.append(f"    dirty {path}")
            for entry in wt["uncommitted_sessions"]:
                lines.append(
                    f"    uncommitted session {entry['timestamp']} {entry['id']} "
                    f"{entry['title']} [{entry['path']}]"
                )
        for commit in reversed(branch["commits"]):
            lines.append(f"  commit {commit['short_sha']} {commit['subject']}")
    detached = report["detached_worktrees"]
    assert isinstance(detached, list)
    if detached:
        lines.append(f"\nDetached worktrees: {len(detached)}")
        for wt in detached:
            lines.append(
                f"  {wt['path']} @ {str(wt['head'])[:8]}: "
                f"{len(wt['dirty_paths'])} dirty paths, "
                f"{len(wt['unique_sessions'])} committed unique sessions, "
                f"{len(wt['uncommitted_sessions'])} uncommitted sessions"
            )
            if detail:
                for entry in wt["unique_sessions"]:
                    lines.append(
                        f"    session {entry['timestamp']} {entry['id']} "
                        f"{entry['title']} [{entry['path']}]"
                    )
                for path in wt["dirty_paths"]:
                    lines.append(f"    dirty {path}")
                for entry in wt["uncommitted_sessions"]:
                    lines.append(
                        f"    uncommitted session {entry['timestamp']} {entry['id']} "
                        f"{entry['title']} [{entry['path']}]"
                    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only inventory of local branch sessions and attached worktrees.",
        epilog="Unique means entry_id absent from base; this does not prove content differs or authorize cleanup.",
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--base", default="main")
    parser.add_argument("--branch", action="append", help="show one branch's full history; repeatable")
    parser.add_argument("--all", action="store_true", help="include fully contained branches")
    parser.add_argument("--json", action="store_true", help="print machine-readable inventory")
    args = parser.parse_args()
    try:
        report = build_inventory(args.repo, base=args.base, selected=args.branch)
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(format_report(report, show_all=args.all, detail=bool(args.branch)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
