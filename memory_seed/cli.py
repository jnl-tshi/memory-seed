from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from . import processes as process_tools
from .core import (
    KNOWN_AGENTS,
    RETRACTABLE_KINDS,
    add_agent,
    amend_topic_sidecar,
    add_skill,
    apply_link_retract,
    branch_status,
    check_session_links,
    clear_local_user,
    compact_sessions,
    doctor,
    foreign_package_message,
    generate_session_entry_id,
    get_version,
    init_project,
    migrate_session_month_layout,
    migrate_session_layout,
    package_provenance,
    read_declared_integration_mode,
    read_integration_mode,
    read_local_user,
    read_project_agents,
    remove_agent,
    remove_skill,
    resolve_agents,
    resolve_runtime,
    selected_agents,
    session_fuse,
    session_open_pr,
    session_prepare_pr_branch,
    session_merge_branch,
    session_target,
    skill_status,
    suggest_integration_mode,
    update_project,
    worktree_guard,
    write_local_user,
    write_integration_mode,
)
from .text_files import (
    encoding_issue_to_dict,
    repair_text_encoding,
    scan_implicit_text_io,
    scan_text_encoding,
    write_text_file,
)


def _read_json_object(path_text: str, *, label: str) -> dict:
    """Read one UTF-8 JSON object, including the conventional stdin marker."""
    raw = sys.stdin.read() if path_text == "-" else Path(path_text).read_text(encoding="utf-8")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


# Provenance is deliberately persisted as a sequence of Markdown blocks rather
# than one mutable JSON document.  The validation contract owns meaning; this
# thin adapter owns only append-only transport and public-surface parity.
_PROVENANCE_EVENT_RE = re.compile(
    r"<!-- memory-seed-provenance:(runtime|binding|replacement) -->\s*```json\s*(.*?)\s*```",
    re.DOTALL,
)


def _provenance_event(kind: str, value: Mapping[str, Any]) -> str:
    return (
        f"<!-- memory-seed-provenance:{kind} -->\n"
        "```json\n"
        + json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n```\n"
    )


def _provenance_topology(
    cwd: str | Path, owner: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], Path, Path, bool]:
    """Measure the selected runtime against nested ``.memory-seed`` topology."""

    from .provenance import build_runtime_ownership, normalize_runtime_ownership

    active = resolve_runtime(cwd)
    outer = active.workspace_root
    if not (active.workspace_root / ".git").exists():
        parent = active.workspace_root.parent
        for candidate in (parent, *parent.parents):
            if (candidate / ".memory-seed").is_dir():
                outer = candidate
                break
    active_path = active.workspace_root.relative_to(outer).as_posix() if active.workspace_root != outer else "."
    runtime = (
        normalize_runtime_ownership(owner)
        if owner is not None
        else build_runtime_ownership(runtime_path=".", owner_kind="runtime", owner_id="root", owner_state="active")
    )
    declared_path = runtime["runtime_path"]
    selected = outer if declared_path == "." else outer / declared_path
    owner_data = runtime["owner"]
    if owner_data["kind"] == "runtime":
        if declared_path != "." or active_path != ".":
            raise ValueError("a runtime root record is valid only for the measured root runtime")
    elif owner_data["kind"] == "pod" and owner_data["state"] == "active":
        if declared_path == "." or not (selected / ".memory-seed").is_dir():
            raise ValueError("an active pod must name a measured nested .memory-seed runtime")
        if owner_data["id"] != Path(declared_path).name:
            raise ValueError("active pod id must match the measured runtime path leaf")
    return runtime, outer, selected, active_path == declared_path


def _provenance_sidecar(root: Path, runtime: Mapping[str, Any]) -> Path:
    return root / str(runtime["sidecar_path"])


def _read_provenance_ledger(root: Path, runtime: Mapping[str, Any]) -> tuple[dict[str, Any], Path, list[str]]:
    """Read a complete event stream, refusing malformed or cross-runtime history."""

    from .provenance import build_ledger, normalize_ledger

    path = _provenance_sidecar(root, runtime)
    if not path.exists():
        return build_ledger(runtime=runtime), path, []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"provenance sidecar is unreadable: {exc}") from exc
    events = list(_PROVENANCE_EVENT_RE.finditer(text))
    if not events:
        raise ValueError("provenance sidecar has no recognized append-only events")
    declared_runtime: dict[str, Any] | None = None
    bindings: list[dict[str, Any]] = []
    replacements: list[dict[str, Any]] = []
    problems: list[str] = []
    for index, match in enumerate(events, start=1):
        kind, raw = match.groups()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"provenance event {index} is not valid JSON: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"provenance event {index} must contain a JSON object")
        if kind == "runtime":
            if declared_runtime is not None:
                problems.append("more than one runtime event")
            declared_runtime = payload
        elif kind == "binding":
            bindings.append(payload)
        else:
            replacements.append(payload)
    if declared_runtime is None:
        raise ValueError("provenance sidecar is missing its initial runtime event")
    ledger = normalize_ledger({
        "schema": "memory-seed/provenance-ledger", "version": 1,
        "runtime": declared_runtime, "bindings": bindings, "replacements": replacements,
    })
    if ledger["runtime"] != dict(runtime):
        problems.append("sidecar runtime does not match the explicitly selected runtime")
    if problems:
        raise ValueError("provenance sidecar is tampered: " + "; ".join(problems))
    return ledger, path, []


def _git_sidecar_baseline(root: Path, path: Path) -> dict[str, Any]:
    """Read one Git baseline using unavailable-Git audit semantics."""

    from .provenance_git import GitUnavailableError, git_head

    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return {"text": None, "status": "unverifiable", "anchor": "outside-runtime"}
    try:
        git_head(root)
    except GitUnavailableError as exc:
        return {"text": None, "status": "unverifiable", "anchor": "git-unavailable", "detail": str(exc)}
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "show", f"HEAD:{relative}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
    except OSError as exc:
        return {"text": None, "status": "unverifiable", "anchor": "git-unavailable", "detail": str(exc)}
    if completed.returncode:
        return {"text": None, "status": "unverifiable", "anchor": "no-committed-sidecar"}
    try:
        text = completed.stdout.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        return {"text": None, "status": "unverifiable", "anchor": "git-baseline-unreadable", "detail": str(exc)}
    return {"text": text, "status": "available", "anchor": "git-head-prefix"}


def _append_only_status(root: Path, path: Path) -> dict[str, Any]:
    """Mechanically anchor event order to committed Git prefixes when present."""

    if not path.exists():
        baseline = _git_sidecar_baseline(root, path)
        if baseline["text"] is not None:
            return {"status": "violated", "anchor": baseline["anchor"], "detail": "committed sidecar is missing from the working tree"}
        return {"status": "unverifiable" if baseline["anchor"] == "git-unavailable" else "not-applicable", "anchor": baseline["anchor"], **({"detail": baseline["detail"]} if baseline.get("detail") else {})}
    try:
        current = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return {"status": "violated", "anchor": "unreadable", "detail": str(exc)}
    baseline = _git_sidecar_baseline(root, path)
    baseline_text = baseline["text"]
    if baseline_text is None:
        return {"status": "unverifiable", "anchor": baseline["anchor"], **({"detail": baseline["detail"]} if baseline.get("detail") else {})}
    if not current.startswith(baseline_text):
        return {"status": "violated", "anchor": "git-head-prefix", "detail": "working sidecar does not retain committed event prefix"}
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        history = subprocess.run(
            ["git", "-C", str(root), "log", "--format=%H", "--reverse", "HEAD", "--", relative],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if history.returncode:
            return {"status": "unverifiable", "anchor": "git-history-unavailable"}
        commits = history.stdout.decode("ascii", "strict").splitlines()
        previous: str | None = None
        for commit in commits:
            version = subprocess.run(
                ["git", "-C", str(root), "show", f"{commit}:{relative}"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            if version.returncode:
                if previous is not None:
                    return {"status": "violated", "anchor": "git-history-prefix", "detail": "a committed sidecar revision deleted the event history"}
                continue
            text = version.stdout.decode("utf-8", "strict")
            if previous is not None and not text.startswith(previous):
                return {"status": "violated", "anchor": "git-history-prefix", "detail": "a committed sidecar revision rewrote or reordered event history"}
            previous = text
    except (OSError, UnicodeDecodeError, ValueError):
        return {"status": "unverifiable", "anchor": "git-history-unavailable"}
    return {"status": "verified", "anchor": "git-history-prefix"}


def _provenance_decision(cwd: str | Path, decision_ref: str) -> dict[str, Any]:
    """Return first-hand decision text plus a small D/R projection when present."""

    import hashlib

    from .semantic_cache import extract_memory_chunks

    for chunk in extract_memory_chunks(cwd, granularity="decision"):
        if chunk.chunk_id != decision_ref:
            continue
        lines = chunk.text.splitlines()
        decision = next((line[4:].strip() for line in lines if line.startswith("- D:")), chunk.title)
        reason = next((line[4:].strip() for line in lines if line.startswith("- R:")), None)
        return {
            "ref": decision_ref, "decision": decision, "reason": reason,
            "source_path": chunk.source_path,
            "source_digest": "sha256:" + hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
            "claimed_timestamp": chunk.entry_datetime.isoformat() if chunk.entry_datetime else None,
        }
    return {"ref": decision_ref, "decision": None, "reason": None, "source_path": None, "source_digest": None, "claimed_timestamp": None}


def provenance_surface(
    action: str, *, cwd: str | Path = ".", decision_ref: str | None = None,
    binding: Mapping[str, Any] | None = None, owner: Mapping[str, Any] | None = None,
    context_lines: int = 3, apply: bool = False,
) -> dict[str, Any]:
    """Shared CLI/MCP provenance adapter with one validation and write path."""

    from .provenance import (
        authorize_runtime_operation, build_ledger, normalize_binding,
        project_ledger, validate_append_only_update,
    )
    from .provenance_git import GitUnavailableError, project_binding, verify_binding

    if type(context_lines) is not int or not 0 <= context_lines <= 20:
        raise ValueError("context_lines must be an integer from 0 through 20")
    runtime, root, selected_runtime, is_current_runtime = _provenance_topology(cwd, owner)
    try:
        ledger, path, _ = _read_provenance_ledger(root, runtime)
    except ValueError as exc:
        if action != "check":
            raise
        path = _provenance_sidecar(root, runtime)
        return {"ok": False, "action": "check", "path": str(path), "runtime": runtime,
                "append_only": {"status": "violated", "anchor": "event-parse", "detail": str(exc)},
                "reference_audit": [], "error": str(exc)}
    if action == "bind":
        if binding is None:
            raise ValueError("binding is required")
        if not is_current_runtime:
            raise ValueError("a caller may inspect a descendant runtime but cannot append to its sidecar")
        normalized = normalize_binding(binding)
        decision = _provenance_decision(selected_runtime, normalized["decision_ref"])
        if decision["decision"] is None:
            raise ValueError("binding decision_ref does not exist in the owning runtime corpus")
        authorization = authorize_runtime_operation(runtime, operation="append")
        if not authorization.ok:
            raise ValueError(authorization.issues[0].message)
        candidate = build_ledger(
            runtime=runtime, bindings=[*ledger["bindings"], normalized], replacements=ledger["replacements"],
        )
        checked = validate_append_only_update(ledger, candidate)
        if not checked.ok:
            raise ValueError(checked.issues[0].message)
        payload = {
            "ok": True, "action": "bind", "dry_run": not apply, "written": False,
            "path": str(path), "binding": normalized, "runtime": runtime,
        }
        if apply:
            path.parent.mkdir(parents=True, exist_ok=True)
            prefix = "" if path.exists() and path.stat().st_size else _provenance_event("runtime", runtime)
            with path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(prefix + _provenance_event("binding", normalized))
            payload["written"] = True
        return payload
    if action == "check":
        verification: list[dict[str, Any]] = []
        for item in ledger["bindings"]:
            try:
                result = verify_binding(item, root)
            except GitUnavailableError as exc:
                result = {"verified": False, "evidence_state": "git-unavailable", "detail": str(exc)}
            verification.append({"binding_id": item["binding_id"], **result})
        append_only = _append_only_status(root, path)
        return {
            "ok": (all(row.get("verified") for row in verification) if verification else True)
            and append_only["status"] not in {"violated", "unavailable"},
            "action": "check", "path": str(path), "ledger": project_ledger(ledger),
            "append_only": append_only, "reference_audit": verification,
        }
    if action != "show":
        raise ValueError("action must be 'show', 'bind', or 'check'")
    if not isinstance(decision_ref, str) or not decision_ref.strip():
        raise ValueError("decision_ref is required")
    decision_ref = decision_ref.strip()
    decision = _provenance_decision(selected_runtime, decision_ref)
    rows: list[dict[str, Any]] = []
    for item in ledger["bindings"]:
        if item["decision_ref"] != decision_ref:
            continue
        try:
            rows.append(project_binding(item, root, before=context_lines, after=context_lines, decision=decision, reason=decision["reason"]))
        except GitUnavailableError as exc:
            rows.append({"binding_id": item["binding_id"], "decision_ref": decision_ref, "decision": decision, "reason": decision["reason"], "code_available": False, "verification": {"verified": False, "evidence_state": "git-unavailable", "detail": str(exc)}, "hunks": []})
    return {"ok": True, "action": "show", "path": str(path), "runtime": runtime, "decision": decision, "context_lines": context_lines, "projections": rows, "code_available": any(row.get("code_available") for row in rows)}


def provenance_audit_all(cwd: str | Path = ".") -> dict[str, Any]:
    """Audit every discoverable sidecar without granting cross-runtime writes."""

    root = resolve_runtime(cwd).workspace_root
    directory = root / ".memory-seed" / "provenance"
    paths = {directory / "bindings.md"}
    if directory.is_dir():
        paths.update(directory.glob("pods/*.md"))
        paths.update(directory.glob("detached-roots/*.md"))
    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "--name-only", "HEAD", "--", ".memory-seed/provenance"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if tracked.returncode == 0:
        paths.update(root / item for item in tracked.stdout.decode("utf-8", "replace").splitlines() if item.endswith(".md"))
    audits: list[dict[str, Any]] = []
    for path in sorted(paths):
        if not path.exists():
            status = _append_only_status(root, path)
            if status["status"] == "not-applicable":
                continue
            audits.append({"path": str(path), "ok": False, "append_only": status, "reference_audit": [], "error": "committed sidecar is missing from the working tree"})
            continue
        try:
            events = list(_PROVENANCE_EVENT_RE.finditer(path.read_text(encoding="utf-8")))
            if not events or events[0].group(1) != "runtime":
                raise ValueError("missing initial runtime event")
            runtime = json.loads(events[0].group(2))
            result = provenance_surface("check", cwd=root, owner=runtime)
            audits.append({"path": str(path), **result})
        except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
            audits.append({"path": str(path), "ok": False, "append_only": {"status": "violated", "anchor": "event-parse"}, "reference_audit": [], "error": str(exc)})
    return {
        "ok": all(item["ok"] for item in audits), "sidecars": audits,
        "sidecar_count": len(audits),
    }


def _atomic_export_json(path_text: str, payload: str, *, overwrite: bool) -> None:
    """Write an explicitly requested export without exposing a partial file."""
    target = Path(path_text)
    if target.exists() and not overwrite:
        raise FileExistsError(f"output already exists: {target}; pass --overwrite to replace it")
    if not target.parent.is_dir():
        raise FileNotFoundError(f"output directory does not exist: {target.parent}")
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=target.parent,
            prefix=f".{target.name}.", suffix=".tmp", delete=False,
        ) as temporary:
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        if overwrite:
            os.replace(temporary_name, target)
        else:
            # ``exists`` is only an early, friendly error.  The hard link is
            # the publication step: its create-new semantics are atomic on the
            # target filesystem, so a file created after the early check is
            # never replaced.  A sibling temp file keeps both paths on the
            # same volume (including Windows/OneDrive-backed workspaces).
            try:
                os.link(temporary_name, target)
            except FileExistsError as exc:
                raise FileExistsError(
                    f"output already exists: {target}; pass --overwrite to replace it"
                ) from exc
            Path(temporary_name).unlink()
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def _print_session_merge_worktree_cleanup(result, *, dry_run: bool) -> None:
    """Report narrow source-worktree cleanup without hiding merge success."""
    if result.source_worktree is None:
        return
    if dry_run:
        if result.worktree_cleanup_detail:
            print(
                f"Source worktree would be retained: {result.source_worktree} "
                f"({result.worktree_cleanup_detail})"
            )
            return
        print(
            "Would verify and remove the clean source worktree after a successful merge: "
            f"{result.source_worktree}"
        )
        return
    if result.worktree_cleanup_status == "removed":
        print(f"Removed source worktree: {result.source_worktree}")
        return
    if result.worktree_cleanup_status == "cleanup-pending":
        print(
            "Merge succeeded, but source-worktree cleanup is still pending: "
            f"{result.source_worktree} ({result.worktree_cleanup_detail or 'git worktree remove failed'})",
            file=sys.stderr,
        )
        return
    print(
        f"Source worktree retained: {result.source_worktree} "
        f"({result.worktree_cleanup_detail or 'cleanup was not safe'})",
        file=sys.stderr,
    )


def _print_help(parser: argparse.ArgumentParser) -> None:
    print(parser.format_help().rstrip())
    print()
    print("Keeping Memory Seed current:")
    print("  Two separate things stay current, and they are not the same step.")
    print(
        "  1. Upgrade the package (code + bundled seed templates):\n"
        "       memory-seed upgrade --dry-run\n"
        "       memory-seed upgrade\n"
        "     If the package manager cannot be detected, pass --manager uv|pipx|pip.\n"
        "     Direct package-manager alternatives:\n"
        "       uv tool upgrade memory-seed\n"
        "       python -m pip install --upgrade memory-seed"
    )
    print(
        "  2. Propagate the new seed files into a project:\n"
        "       memory-seed update"
    )
    print(
        "  'memory-seed update' copies files from the installed package; it does\n"
        "  not fetch from PyPI. Upgrade the package first, then run update."
    )
    print(
        "  'memory-seed version' reports the control-plane version; "
        "'pip show memory-seed'\n  reports the package version."
    )
    print()
    print("Run 'memory-seed <command> -h' for flags and details on any command.")


def _split_csv(value: str | None) -> set[str]:
    if not value:
        return set()
    return {part.strip() for part in value.split(",") if part.strip()}


def _format_agents(agents: set[str]) -> str:
    ordered = [agent for agent in KNOWN_AGENTS if agent in agents]
    return ", ".join(ordered) if ordered else "(none)"


def _resolve_init_integration_mode(
    target_root: Path,
    *,
    requested_mode: str | None,
    isatty: bool,
) -> tuple[str, bool]:
    declared_mode = read_declared_integration_mode(target_root)
    if declared_mode is not None:
        return declared_mode, False
    if requested_mode is not None:
        return requested_mode, True
    if not isatty:
        return "local-merge", True

    suggested_mode, reason = suggest_integration_mode(target_root)
    print("How should branch work be integrated?")
    print("  - local-merge: merge into local main only; never pushes")
    print("  - pr: prepare the branch, push it normally, and open a pull request")
    print(f"Suggested: {suggested_mode} ({reason}). Existing projects are never switched automatically.")
    try:
        response = input(f"integration-mode [{suggested_mode}]> ")
    except EOFError:
        response = ""
    chosen_mode = response.strip().lower() or suggested_mode
    if chosen_mode not in {"local-merge", "pr"}:
        raise ValueError("Unknown integration mode. Valid modes: local-merge, pr.")
    return chosen_mode, True


def _print_skill_status(status) -> None:
    print("Core skills:")
    for skill in status.core:
        print(f"  - {skill}")
    print("Installed optional skills:")
    if status.installed_optional:
        for skill in status.installed_optional:
            print(f"  - {skill}: {status.descriptions.get(skill, '')}")
    else:
        print("  (none)")
    print("Selected optional skills:")
    if status.selected_optional:
        for skill in status.selected_optional:
            print(f"  - {skill}")
    else:
        print("  (none)")
    print("Ignored optional skills:")
    if status.ignored:
        for skill in status.ignored:
            print(f"  - {skill}: {status.descriptions.get(skill, '')}")
    else:
        print("  (none)")
    print("Profiles:")
    for name, skills in status.profiles.items():
        description = status.profile_descriptions.get(name, "")
        print(f"  - {name}: {', '.join(skills)}")
        if description:
            print(f"    {description}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="memory-seed",
        epilog=(
            "Upgrade the package: memory-seed upgrade --dry-run, then memory-seed upgrade. "
            "Refresh project files afterward with memory-seed update. "
            "Run 'memory-seed help' for details."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    subparsers.add_parser("help", help="list all commands and how they work")
    process_tools.add_package_process_parsers(subparsers)

    init_parser = subparsers.add_parser("init", help="copy Memory Seed into this project")
    init_parser.add_argument("--dry-run", action="store_true", help="show planned files without writing")
    init_parser.add_argument("--force", action="store_true", help="backup and overwrite existing seed files")
    init_parser.add_argument(
        "--agents",
        type=str,
        default=None,
        help=(
            "comma-separated agents to install ("
            + ",".join(KNOWN_AGENTS)
            + ",none); default: all. Non-selected agents' files are skipped."
        ),
    )
    init_parser.add_argument(
        "--no-agent-prompt",
        action="store_true",
        help="skip interactive agent selection and install all agents unless --agents is supplied",
    )
    init_parser.add_argument("--profile", type=str, default=None, help="comma-separated skill profiles to install")
    init_parser.add_argument("--skills", type=str, default=None, help="comma-separated optional skill files to install")
    init_parser.add_argument(
        "--exclude-skills",
        type=str,
        default=None,
        help="comma-separated optional skill files to omit from the selected set",
    )
    init_parser.add_argument("--all-skills", action="store_true", help="install every optional skill")
    init_parser.add_argument("--manual-skills", action="store_true", help="prompt for individual optional skills")
    init_parser.add_argument(
        "--no-skill-prompt",
        action="store_true",
        help="skip interactive skill selection and install the minimal core unless flags are supplied",
    )
    init_parser.add_argument(
        "--integration-mode",
        choices=["local-merge", "pr"],
        default=None,
        help="write .memory-seed/project.yaml integration_mode explicitly (default: prompt in interactive init, else local-merge)",
    )

    skills_parser = subparsers.add_parser("skills", help="manage optional Memory Seed skills")
    skills_sub = skills_parser.add_subparsers(dest="skills_command", required=True)
    skills_sub.add_parser("list", help="show installed, ignored, available skills and profiles")
    skills_sub.add_parser("ignored", help="show optional skills that are not installed")
    skills_add = skills_sub.add_parser("add", help="install a skill or profile")
    skills_add.add_argument("name", help="skill filename or profile name")
    skills_remove = skills_sub.add_parser("remove", help="remove an optional skill")
    skills_remove.add_argument("skill", help="optional skill filename")

    encoding_parser = subparsers.add_parser("encoding", help="check or repair project text-file encoding")
    encoding_sub = encoding_parser.add_subparsers(dest="encoding_command", required=True)
    encoding_check = encoding_sub.add_parser(
        "check",
        help="report encoding drift and implicit text I/O",
    )
    encoding_check.add_argument("path", nargs="?", default=".", help="file or directory to scan (default: current directory)")
    encoding_check.add_argument("--json", action="store_true", help="emit machine-readable issue data")
    encoding_repair = encoding_sub.add_parser(
        "repair",
        help="back up and repair BOM, newline, and NFC drift; mojibake remains manual",
    )
    encoding_repair.add_argument(
        "path",
        nargs="?",
        default=".",
        help="file or directory to repair (default: current directory)",
    )
    encoding_repair.add_argument("--dry-run", action="store_true", help="preview repairs without writing")
    encoding_repair.add_argument("--json", action="store_true", help="emit machine-readable result data")

    agents_parser = subparsers.add_parser("agents", help="manage which agents are installed")
    agents_sub = agents_parser.add_subparsers(dest="agents_command", required=True)
    agents_sub.add_parser("list", help="show selected and ignored agents")
    agents_add = agents_sub.add_parser("add", help="install an agent's files")
    agents_add.add_argument("agent", help="agent slug (" + ",".join(KNOWN_AGENTS) + ")")
    agents_remove = agents_sub.add_parser("remove", help="remove an agent's files")
    agents_remove.add_argument("agent", help="agent slug (" + ",".join(KNOWN_AGENTS) + ")")

    user_parser = subparsers.add_parser("user", help="manage the local Memory Seed user")
    user_sub = user_parser.add_subparsers(dest="user_command", required=True)
    user_sub.add_parser("show", help="show the configured local user")
    user_set = user_sub.add_parser("set", help="set the local user slug")
    user_set.add_argument("slug", help="user slug, e.g. jean")
    user_sub.add_parser("clear", help="clear the local user slug")

    session_parser = subparsers.add_parser(
        "session",
        help="inspect the session-log target or integrate branch-local session memory",
    )
    session_sub = session_parser.add_subparsers(dest="session_command", required=True)
    session_target_parser = session_sub.add_parser("target", help="print the active session log target")
    session_target_parser.add_argument("--date", default=None, help="target date (YYYY-MM-DD); default: today")
    session_target_parser.add_argument("--user", default=None, help="override the active user slug")
    session_target_parser.add_argument("--create", action="store_true", help="create the target file if needed")
    session_fuse_parser = session_sub.add_parser(
        "fuse",
        help="dry-run or apply branch-local session entries into the current integration tree",
    )
    session_fuse_parser.add_argument("--branch", required=True, help="source branch whose session entries should be fused")
    session_fuse_parser.add_argument("--base", default="HEAD", help="base ref to compare against (default: HEAD)")
    session_fuse_parser.add_argument("--apply", action="store_true", help="write the planned fuse; requires an in-progress git merge")
    session_fuse_parser.add_argument(
        "--user-approved",
        action="store_true",
        help="authorize --apply when merge_trigger is 'manual' (an explicit user go-ahead; agents must not set this themselves)",
    )
    session_merge_parser = session_sub.add_parser(
        "merge-branch",
        help="merge a task branch and fuse its branch-local session entries in one step",
    )
    session_merge_parser.add_argument("--branch", required=True, help="task branch to merge into the current branch")
    session_merge_parser.add_argument("--dry-run", action="store_true", help="preview the fuse plan without merging")
    session_merge_parser.add_argument(
        "--user-approved",
        action="store_true",
        help="authorize landing when merge_trigger is 'manual' (an explicit user go-ahead; agents must not set this themselves)",
    )
    session_prepare_pr_parser = session_sub.add_parser(
        "prepare-pr",
        help="prepare the current task branch for a host-side PR merge by replaying session chronology locally",
    )
    session_prepare_pr_parser.add_argument("--branch", required=True, help="current task branch to prepare")
    session_prepare_pr_parser.add_argument(
        "--base-branch",
        default=None,
        help="target integration branch (default: infer from main/master/origin HEAD; fail closed when ambiguous)",
    )
    session_prepare_pr_parser.add_argument("--dry-run", action="store_true", help="preview the preparation plan without merging")
    session_open_pr_parser = session_sub.add_parser(
        "open-pr",
        help="prepare the current task branch, push it normally, and create a PR with gh",
    )
    session_open_pr_parser.add_argument("--branch", required=True, help="current task branch to push and open as a PR")
    session_open_pr_parser.add_argument(
        "--base-branch",
        default=None,
        help="target integration branch (default: infer from main/master/origin HEAD; fail closed when ambiguous)",
    )
    session_open_pr_parser.add_argument("--dry-run", action="store_true", help="preview the PR plan without pushing or creating it")
    session_open_pr_parser.add_argument(
        "--user-approved",
        action="store_true",
        help="authorize opening the PR when merge_trigger is 'manual' (an explicit user go-ahead; agents must not set this themselves)",
    )
    session_integrate_parser = session_sub.add_parser(
        "integrate",
        help="dispatch branch integration according to .memory-seed/project.yaml integration_mode",
    )
    session_integrate_parser.add_argument("--branch", required=True, help="task branch to integrate")
    session_integrate_parser.add_argument(
        "--base-branch",
        default=None,
        help="PR-mode target branch (default: infer from main/master/origin HEAD; ignored by local-merge)",
    )
    session_integrate_parser.add_argument("--dry-run", action="store_true", help="preview the chosen integration flow without writing")
    session_integrate_parser.add_argument(
        "--user-approved",
        action="store_true",
        help="authorize the handoff when merge_trigger is 'manual' (an explicit user go-ahead; agents must not set this themselves)",
    )
    session_append_parser = session_sub.add_parser(
        "append",
        help="append a session entry with structure enforced (id, chronology, refs, topics); body from --body-file or stdin",
    )
    session_append_parser.add_argument("--title", required=True, help="entry title (text after 'YYYY-MM-DD HH:MM - ')")
    session_append_parser.add_argument("--user-initials", required=True, help="user_initials field, e.g. JNL")
    session_append_parser.add_argument("--agent-type", required=True, help="agent_type field, e.g. claude")
    session_append_parser.add_argument(
        "--topics",
        default="",
        help="LEGACY entry-level slugs (no decision keying); prefer --decisions-file",
    )
    session_append_parser.add_argument(
        "--decisions-file",
        default=None,
        help="JSON list of per-record sidecar objects (the compatibility field is named 'decision'); mutually exclusive with --topics/--related/--replaces/--evolves",
    )
    # Repeatable (one ref per flag) AND comma-separated (legacy form), because
    # grammar v2 puts commas INSIDE a ref (`mse_x:d1,d4`) - see _ref_list.
    session_append_parser.add_argument(
        "--related", action="append", default=None, help="related_entries id; repeat for several"
    )
    # --supersedes is the legacy spelling (renamed 2026-07-24); both flags feed
    # one dest so existing automation keeps working while emitting `replaces:`.
    session_append_parser.add_argument(
        "--replaces", "--supersedes", dest="replaces", action="append", default=None,
        help="id this entry retires, e.g. mse_x:d2 or 'd1 -> mse_x:d2'; repeat for several",
    )
    session_append_parser.add_argument(
        "--evolves", action="append", default=None,
        help="id this entry refines (it stays valid); same grammar as --replaces; repeat for several",
    )
    session_append_parser.add_argument("--project-path", default=".", help="project_path field (default: .)")
    session_append_parser.add_argument("--subproject-path", default=None, help="subproject_path field (default: null)")
    session_append_parser.add_argument("--branch", default=None, help="branch field (default: auto-captured from git)")
    session_append_parser.add_argument("--no-branch", action="store_true", help="omit the branch field entirely")
    session_append_parser.add_argument("--timestamp", default=None, help="override heading timestamp 'YYYY-MM-DD HH:MM' (default: now; future values are refused)")
    session_append_parser.add_argument("--user", default=None, help="override the active user slug")
    session_append_parser.add_argument("--body-file", default=None, help="file containing the entry body (default: read stdin)")
    session_append_parser.add_argument(
        "--adr-review-receipt",
        default=None,
        help="content-bound receipt returned by a refused lifecycle-linked append preflight",
    )
    session_append_parser.add_argument("--dry-run", action="store_true", help="run every guard and report the id, timestamp and target path without writing")
    session_reorder_parser = session_sub.add_parser(
        "reorder",
        help="restore chronological entry order in one day's session file (pure block permutation)",
    )
    session_reorder_parser.add_argument("--date", required=True, help="session date (YYYY-MM-DD)")
    session_reorder_parser.add_argument("--user", default=None, help="override the active user slug")
    session_reorder_parser.add_argument("--apply", action="store_true", help="write the reordered file (default: dry run)")
    session_entry_id_parser = session_sub.add_parser(
        "entry-id",
        help="compute the canonical entry_id for a new session entry (deterministic, no randomness)",
    )
    session_entry_id_parser.add_argument("--timestamp", required=True, help="entry heading timestamp, e.g. '2026-07-12 14:45'")
    session_entry_id_parser.add_argument("--title", required=True, help="entry title (the text after the timestamp)")
    session_entry_id_parser.add_argument("--user-initials", required=True, help="user_initials field, e.g. JNL")
    session_entry_id_parser.add_argument("--agent-type", required=True, help="agent_type field, e.g. claude")
    session_entry_id_parser.add_argument("--project-path", default=".", help="project_path field (default: .)")
    session_entry_id_parser.add_argument("--subproject-path", default=None, help="subproject_path field (default: null)")

    adr_parser = subparsers.add_parser("adr", help="promote and transition append-only ADR sidecars")
    adr_sub = adr_parser.add_subparsers(dest="adr_command", required=True)
    adr_promote = adr_sub.add_parser(
        "promote",
        help="promote a session decision or bootstrap founding source into a proposed ADR",
    )
    adr_promote.add_argument("--adr-id", required=True, help="stable lowercase id, e.g. adr_local_index")
    adr_promote.add_argument("--entry-id", default=None, help="source session entry id")
    adr_promote.add_argument("--decision", default=None, help="source decision ordinal, e.g. d1")
    adr_promote.add_argument(
        "--founding-source",
        default=None,
        help="bootstrap or a control-file location such as .memory-seed/index.md#L42",
    )
    adr_promote.add_argument(
        "--founding-quote",
        default="",
        help="exact project evidence for a founding promotion",
    )
    adr_promote.add_argument("--title", required=True)
    adr_promote.add_argument("--topics", default="", help="comma-separated topic slugs")
    adr_promote.add_argument("--user-initials", required=True)
    adr_promote.add_argument("--agent-type", required=True)
    adr_promote.add_argument("--source", required=True, choices=("write-time", "derived"))
    adr_promote.add_argument("--summary-decision", default="See the authoritative session decision.")
    adr_promote.add_argument("--reason", default=None, help="canonical ADR rationale")
    adr_promote.add_argument("--impact", default=None, help="expected falsifiable ADR impact")
    adr_promote.add_argument("--why", default=None, help="deprecated alias for --reason")
    adr_promote.add_argument("--evolution", default=None, help="deprecated alias for --impact")
    adr_promote.add_argument("--update-entry-id", default=None, help="promotion/update entry; defaults to source entry")
    adr_promote.add_argument(
        "--predecessor",
        action="append",
        default=[],
        help="decision=relation_assertion, e.g. mse_old:d1=link:mse_new:d1:evolves:mse_old:d1",
    )
    adr_promote.add_argument(
        "--constitution-ref",
        action="append",
        default=[],
        help="ref=role binding, where role is governing or supporting",
    )
    adr_promote.add_argument(
        "--supporting-decision",
        action="append",
        default=[],
        help="additional evidence decision, e.g. mse_entry:d2 (repeatable)",
    )
    adr_promote.add_argument("--timestamp", default=None, help="UTC ISO timestamp; default: now")
    adr_promote.add_argument("--dry-run", action="store_true")
    adr_revise = adr_sub.add_parser("revise", help="append a proposed revision without changing authority")
    adr_revise.add_argument("--adr-id", required=True)
    adr_revise.add_argument("--decision-ref", required=True, help="canonical session decision ref")
    adr_revise.add_argument("--decision", required=True, help="concise current-decision synopsis")
    adr_revise.add_argument("--reason", default=None, help="canonical ADR rationale")
    adr_revise.add_argument("--impact", default=None, help="expected falsifiable ADR impact")
    adr_revise.add_argument("--why", default=None, help="deprecated alias for --reason")
    adr_revise.add_argument("--evolution", default=None, help="deprecated alias for --impact")
    adr_revise.add_argument("--update-entry-id", required=True)
    adr_revise.add_argument("--source", required=True, choices=("write-time", "derived"))
    adr_revise.add_argument("--predecessor", action="append", default=[], help="decision=relation_assertion")
    adr_revise.add_argument("--timestamp", default=None)
    adr_revise.add_argument("--dry-run", action="store_true")
    adr_transition = adr_sub.add_parser("transition", help="append an expected-state ADR transition")
    adr_transition.add_argument("--adr-id", required=True)
    adr_transition.add_argument("--status", required=True, choices=("accepted", "rejected", "superseded"))
    adr_transition.add_argument("--update-entry-id", required=True)
    adr_transition.add_argument("--decision-ref", default=None)
    adr_transition.add_argument("--expected-authoritative-decision", default=None)
    adr_transition.add_argument("--expected-previous-status", default=None, help="legacy status guard")
    adr_transition.add_argument("--source", required=True, choices=("write-time", "derived"))
    adr_transition.add_argument("--replacement-adr", default=None)
    adr_transition.add_argument("--reason", default="")
    adr_transition.add_argument("--timestamp", default=None, help="UTC ISO timestamp; default: now")
    adr_transition.add_argument("--dry-run", action="store_true")
    adr_reviewed = adr_sub.add_parser(
        "reviewed", help="record reviewed-no-change against an existing evidence entry"
    )
    adr_reviewed.add_argument("--adr-id", required=True)
    adr_reviewed.add_argument("--entry", required=True, help="existing session entry that evidences the review")
    adr_reviewed.add_argument("--reason", required=True, help="why the ADR head remains current")
    adr_reviewed.add_argument("--timestamp", default=None, help="UTC ISO timestamp; default: now")
    adr_reviewed.add_argument("--dry-run", action="store_true")
    adr_show = adr_sub.add_parser("show", help="show one ADR and its derived current status")
    adr_show.add_argument("adr_id")
    adr_show.add_argument("--json", action="store_true")
    adr_list = adr_sub.add_parser("list", help="list architectural concerns and their accepted heads")
    adr_list.add_argument("--json", action="store_true")
    adr_check = adr_sub.add_parser("check", help="validate every ADR sidecar")
    adr_check.add_argument("--json", action="store_true")

    branch_parser = subparsers.add_parser("branch", help="inspect Git branch/worktree posture")
    branch_sub = branch_parser.add_subparsers(dest="branch_command", required=True)
    branch_status_parser = branch_sub.add_parser(
        "status",
        help="show read-only branch guardrails for feature work",
    )
    branch_status_parser.add_argument("--json", action="store_true", help="emit machine-readable status")

    worktree_parser = subparsers.add_parser("worktree", help="inspect agent worktree namespace posture")
    worktree_sub = worktree_parser.add_subparsers(dest="worktree_command", required=True)
    worktree_guard_parser = worktree_sub.add_parser(
        "guard",
        help="check whether the current worktree is safe for this agent before editing",
    )
    worktree_guard_parser.add_argument("--agent", required=True, help="agent slug, e.g. codex or claude")
    worktree_guard_parser.add_argument("--write-intent", action="store_true", help="treat this as a pre-write gate")
    worktree_guard_parser.add_argument(
        "--allow-root-write",
        action="store_true",
        help="explicitly allow root-checkout writes for approved integration or cleanup work",
    )
    worktree_guard_parser.add_argument("--json", action="store_true", help="emit machine-readable status")
    worktree_status_parser = worktree_sub.add_parser(
        "status",
        help="show current worktree namespace posture without blocking read-only inspection",
    )
    worktree_status_parser.add_argument("--agent", default=None, help="optional expected agent slug")
    worktree_status_parser.add_argument("--json", action="store_true", help="emit machine-readable status")

    topics_parser = subparsers.add_parser("topics", help="inspect and validate the controlled topic vocabulary")
    topics_sub = topics_parser.add_subparsers(dest="topics_command", required=True)
    topics_sub.add_parser("list", help="show the topics defined in .memory-seed/topics.yaml")
    topics_sub.add_parser(
        "check",
        help="validate vocabulary shape and entry topics: usage (exit 1 on any error)",
    )
    topics_suggest = topics_sub.add_parser(
        "suggest",
        help="suggest controlled topics for a UTF-8 file (read-only)",
    )
    topics_suggest.add_argument(
        "--from",
        dest="from_path",
        required=True,
        metavar="FILE",
        help="file to inspect for topic suggestions",
    )
    topics_amend = topics_sub.add_parser(
        "amend",
        help="append a corrected full decision-topic snapshot without editing history",
    )
    topics_amend.add_argument("--entry", required=True, help="existing session entry id")
    topics_amend.add_argument("--decision", required=True, help="decision ordinal to amend, e.g. d1")
    topics_amend.add_argument("--area", required=True, help="canonical area topic slug")
    topics_amend.add_argument(
        "--activity",
        action="append",
        required=True,
        help="canonical activity topic slug; repeat for a second activity",
    )
    topics_amend.add_argument("--reason", required=True, help="short audit reason retained in the sidecar heading")
    topics_amend.add_argument("--timestamp", help="optional later timestamp on the entry's original date")
    topics_amend.add_argument("--dry-run", action="store_true", help="render and validate without writing")

    links_parser = subparsers.add_parser("links", help="validate session-memory integrity")
    links_sub = links_parser.add_subparsers(dest="links_command", required=True)
    links_sub.add_parser(
        "check",
        help="report duplicate/dangling IDs and per-user frontmatter problems (exit 1 on any issue)",
    )
    links_chain = links_sub.add_parser(
        "chain",
        help="show the refines chain a decision belongs to (root -> head, owning ADRs)",
    )
    links_chain.add_argument("ref", help="decision ref: mse_x or mse_x:dN")
    links_chain.add_argument("--json", action="store_true", help="emit the derived chain view as JSON")
    links_graph_diff = links_sub.add_parser(
        "graph-diff",
        help="snapshot the effective evolves/refines graph, or compare against a prior snapshot",
    )
    links_graph_diff.add_argument(
        "--snapshot",
        metavar="PATH",
        default=None,
        help="write the current effective graph snapshot to PATH",
    )
    links_graph_diff.add_argument(
        "--against",
        metavar="PATH",
        default=None,
        help="diff a fresh snapshot against the baseline snapshot at PATH",
    )
    links_graph_diff.add_argument(
        "--json", action="store_true", help="with --against, emit the diff as JSON"
    )

    migrate_parser = subparsers.add_parser("migrate", help="migrate Memory Seed data layouts")
    migrate_sub = migrate_parser.add_subparsers(dest="migrate_command", required=True)
    migrate_sessions = migrate_sub.add_parser(
        "sessions-layout",
        help="split legacy flat session files into per-day/per-user files (by author; see sessions-month-layout for folder grouping)",
    )
    migrate_sessions.add_argument("--dry-run", action="store_true", help="show planned migrations without writing")
    migrate_month_sessions = migrate_sub.add_parser(
        "sessions-month-layout",
        help="move old session files into YYYY-MM month folders (by date; see sessions-layout for per-author splitting)",
    )
    migrate_month_sessions.add_argument("--dry-run", action="store_true", help="show planned migrations without writing")

    link_parser = subparsers.add_parser("link", help="inspect and suggest related-entry graph edges")
    link_sub = link_parser.add_subparsers(dest="link_command", required=True)
    link_suggest = link_sub.add_parser(
        "suggest",
        help="rank older entries to link from a target entry (read-only)",
    )
    link_suggest.add_argument(
        "--for",
        dest="for_entry",
        metavar="ENTRY_ID",
        default=None,
        help="entry to suggest links for (default: the newest entry)",
    )
    link_suggest.add_argument("--top-k", type=int, default=5, help="number of candidates to show (default: 5)")
    link_audit = link_sub.add_parser(
        "audit",
        help="find entries that share files/topics but have no recorded edge",
    )
    link_audit.add_argument(
        "--for",
        dest="for_entry",
        metavar="ENTRY_ID",
        default=None,
        help="audit a single entry (default: every entry)",
    )
    link_audit.add_argument(
        "--date",
        dest="audit_date",
        metavar="YYYY-MM-DD",
        default=None,
        help="audit only entries from this session date (the end-of-session sweep scope)",
    )
    link_audit.add_argument("--top-k", type=int, default=5, help="candidates per entry (default: 5)")
    link_audit.add_argument(
        "--apply",
        action="store_true",
        help="write inert classify_pending stubs for --date gaps; never writes a live edge",
    )
    link_audit.add_argument(
        "--json",
        action="store_true",
        help="emit judgment-ready candidates (both ends' decision bodies + criteria) for a narrowing agent",
    )
    link_audit.add_argument(
        "--no-semantic",
        dest="semantic",
        action="store_false",
        help="rank lexically only (shared files + title terms); skips loading the embedding model",
    )
    link_batch_plan = link_sub.add_parser(
        "batch-plan", help="pack complete link-audit pairs into context-bounded, read-only batches"
    )
    link_batch_plan.add_argument("--context-window", type=int, required=True,
                                 help="declared model context window in tokens")
    link_batch_plan.add_argument("--evidence-fraction", type=float, default=0.16,
                                 help="fraction of context reserved for the complete worker document (default: 0.16)")
    link_batch_plan.add_argument("--minimum-score", type=float, default=0.0,
                                 help="minimum combined candidate score admitted to a worker (default: 0)")
    link_batch_plan.add_argument("--semantic-cutoff", type=float, default=None,
                                 help="raw cosine cutoff for semantic-only candidates; when set, admit every pair at or above it")
    link_batch_plan.add_argument("--output-tokens-per-pair", type=int, default=160,
                                 help="estimated structured report reserve per pair (default: 160)")
    link_batch_plan.add_argument("--output-dir", default=None,
                                 help="materialize plan, worker batches, findings slots, and analytics ledger")
    link_batch_plan.add_argument("--for", dest="for_entry", metavar="ENTRY_ID", default=None)
    link_batch_plan.add_argument("--date", dest="audit_date", metavar="YYYY-MM-DD", default=None)
    link_batch_plan.add_argument("--top-k", type=int, default=0,
                                 help="cap lexical candidates per source; 0 enumerates all (default: 0)")
    link_batch_plan.add_argument("--no-semantic", dest="semantic", action="store_false",
                                 help="rank lexically only; skips loading the embedding model")
    link_batch_collect = link_sub.add_parser(
        "batch-collect", help="validate file-written TOON findings and update a run analytics ledger"
    )
    link_batch_collect.add_argument("--run-dir", required=True,
                                    help="materialized run directory containing plan.json and findings/")
    link_batch_finalize = link_sub.add_parser(
        "batch-finalize", help="seal an approved or rejected run for retention and later compaction"
    )
    link_batch_finalize.add_argument("--run-dir", required=True,
                                     help="collected materialized run directory")
    link_batch_finalize.add_argument("--approval-file", required=True,
                                     help="memory-seed.link-swarm-approval.v1 JSON file")
    link_batch_finalize.add_argument("--retention-days", type=int, default=30,
                                     help="days to retain raw batches/findings after finalization (default: 30)")
    link_batch_gc = link_sub.add_parser(
        "batch-gc", help="find finalized runs whose raw evidence is eligible for compaction"
    )
    link_batch_gc.add_argument("--runs-dir", default=None,
                               help="run root or one finalized run (default: .memory-seed/link-swarm-runs)")
    link_batch_gc.add_argument("--apply", action="store_true",
                               help="remove hash-verified expired raw artifacts; default is dry-run")
    link_batch_gc.add_argument("--purge-now", action="store_true",
                               help="ignore expiry dates, but still require a valid finalized receipt and hashes")
    link_add = link_sub.add_parser(
        "add",
        help="add a related_entries edge to the current/newest entry",
    )
    link_add.add_argument("target_entry_id", help="older entry_id to link to")
    link_add.add_argument(
        "--from",
        dest="from_entry",
        default=None,
        metavar="ENTRY_ID",
        help="source entry (default: the newest entry; older entries are refused)",
    )
    link_retract = link_sub.add_parser(
        "retract",
        help="retract a published lifecycle edge (append-only), optionally re-authoring it retyped",
    )
    link_retract.add_argument(
        "kind",
        choices=list(RETRACTABLE_KINDS),
        help="the kind of edge being retracted, as it was authored",
    )
    link_retract.add_argument(
        "ref",
        help="the retracted edge's target: <entry_id>, <entry_id>:dN, or <entry_id>:d1,d3 "
        "(the comma form fans out to one retract line per ordinal); may carry a 'dM -> ' "
        "source prefix and a trailing '(type)' exactly as the edge was authored",
    )
    link_retract.add_argument(
        "--from",
        dest="from_entry",
        required=True,
        metavar="ENTRY_ID",
        help="the edge's SOURCE entry - the entry whose dated link sidecar carries the correction",
    )
    link_retract.add_argument(
        "--retype",
        dest="retype",
        default=None,
        metavar="KIND_OR_TYPE",
        help="re-author the same ref under a new kind (replaces/evolves/related_entries) or with an "
        "evolution type (refines/builds-on) - the mandated fix for untyped-evolves, "
        "unknown-evolution-type and multiple-refines-successors",
    )
    link_retract.add_argument(
        "--note", dest="note", default=None, help="one-line note recorded beside the correction"
    )
    link_retract.add_argument(
        "--date-pin",
        dest="date_pin",
        default=None,
        metavar="YYYY-MM-DD",
        help="the ORIGINAL declaration date, recorded on each retract line and validated against it",
    )
    link_retract.add_argument(
        "--dry-run",
        dest="retract_dry_run",
        action="store_true",
        help="validate and print the block that would be appended, writing nothing",
    )
    link_show = link_sub.add_parser(
        "show",
        help="show outbound edges and computed inbound backlinks for an entry",
    )
    link_show.add_argument("entry_id", help="entry_id to show edges for")
    link_commits = link_sub.add_parser(
        "commits",
        help="show commits linked to an entry (stored commits: field + Memory-Entry trailer scan)",
    )
    link_commits.add_argument("entry_id", help="entry_id to show commits for")

    worktree_classify = worktree_sub.add_parser(
        "classify",
        help="classify every registered worktree for cleanup (read-only dry run)",
    )
    worktree_classify.add_argument(
        "--agent",
        dest="gc_agent",
        default=None,
        help="scope ownership to this agent (worktrees in other namespaces report foreign)",
    )
    worktree_classify.add_argument(
        "--integration-branch",
        dest="gc_integration_branch",
        default="main",
        help="branch to check merge status against (default: main)",
    )
    worktree_classify.add_argument(
        "--json", action="store_true", help="emit the machine-readable classification"
    )
    worktree_classify.add_argument(
        "--apply",
        action="store_true",
        help="DESTRUCTIVE: remove the worktrees a fresh classification calls removable "
        "(git-native, bounded retry, no raw deletion; branches untouched)",
    )

    docs_parser = subparsers.add_parser("docs", help="validate the docs/ lifecycle lanes")
    docs_sub = docs_parser.add_subparsers(dest="docs_command", required=True)
    docs_sub.add_parser(
        "check",
        help="read-only lane/link/pointer validation over docs/",
    )
    docs_index = docs_sub.add_parser(
        "index",
        help="regenerate the lane README tables and front-door roll-up (marker-scoped)",
    )
    docs_index.add_argument(
        "--check",
        action="store_true",
        help="write nothing; exit 1 if the generated index is stale",
    )

    quality_parser = subparsers.add_parser(
        "quality",
        help="read-only memory-quality measurement over the corpus",
    )
    quality_sub = quality_parser.add_subparsers(dest="quality_command", required=True)
    quality_report = quality_sub.add_parser(
        "report",
        help="measure corpus quality metrics (read-only; never feeds ranking)",
    )
    quality_report.add_argument(
        "--json", action="store_true", help="emit the versioned machine-readable report"
    )

    ranking_ab_parser = subparsers.add_parser(
        "ranking-ab",
        help="real-corpus A/B for a ranking signal (the gate before any default flip)",
    )
    ranking_ab_parser.add_argument(
        "--signal",
        required=True,
        help="named ranking signal to A/B (e.g. supersession_damping); see the registry for options",
    )
    ranking_ab_parser.add_argument(
        "--query",
        dest="queries",
        action="append",
        default=None,
        metavar="Q",
        help="query to A/B (repeatable); default: queries derived from the signal (e.g. supersession lineages)",
    )
    ranking_ab_parser.add_argument(
        "--json", action="store_true", help="emit the machine-readable A/B result"
    )

    hooks_parser = subparsers.add_parser("hooks", help="manage git hooks that keep memory metadata true by construction")
    hooks_sub = hooks_parser.add_subparsers(dest="hooks_command", required=True)
    hooks_status = hooks_sub.add_parser(
        "status",
        help="show whether Memory-Entry trailer stamping is installed and current",
    )
    hooks_status.add_argument("--json", action="store_true", help="emit machine-readable status")
    hooks_sub.add_parser(
        "install",
        help="install the prepare-commit-msg shim that auto-stamps Memory-Entry trailers (idempotent)",
    )
    hooks_sub.add_parser(
        "repair",
        help="install or refresh Memory Seed-managed trailer hooks without overwriting foreign hooks",
    )

    provenance_parser = subparsers.add_parser(
        "provenance",
        help="inspect, append, and audit reference-only decision-to-Git provenance",
    )
    provenance_sub = provenance_parser.add_subparsers(dest="provenance_command", required=True)
    provenance_show = provenance_sub.add_parser("show", help="show verified temporary before/after code projections")
    provenance_show.add_argument("decision_ref", help="exact <entry_id>:dN decision reference")
    provenance_show.add_argument("--context-lines", type=int, default=3, help="Git context lines per side, 0-20 (default: 3)")
    provenance_show.add_argument("--runtime-file", help="explicit UTF-8 JSON measured runtime record for descendant/retired inspection")
    provenance_show.add_argument("--json", action="store_true", help="emit machine-readable output")
    provenance_bind = provenance_sub.add_parser("bind", help="append one validated binding reference")
    provenance_bind.add_argument("--binding-file", required=True, help="UTF-8 JSON binding object; use - for stdin")
    provenance_bind.add_argument("--apply", action="store_true", help="append after validation; default is a dry run")
    provenance_bind.add_argument("--runtime-file", help="explicit UTF-8 JSON measured runtime record; writes require the current measured runtime")
    provenance_bind.add_argument("--json", action="store_true", help="emit machine-readable output")
    provenance_check = provenance_sub.add_parser("check", help="audit append-only sidecar and Git references")
    provenance_check.add_argument("--runtime-file", help="explicit UTF-8 JSON measured runtime record for descendant/retired inspection")
    provenance_check.add_argument("--json", action="store_true", help="emit machine-readable output")

    esr_parser = subparsers.add_parser(
        "esr",
        help="end-of-session mechanical preflight: every deterministic check in one read-only report",
    )
    esr_parser.add_argument("--date", default=None, help="session date for the link-gap sweep (default: today)")
    esr_parser.add_argument("--json", action="store_true", help="emit the report as JSON")

    situate_parser = subparsers.add_parser(
        "situate",
        help="orientation preflight: local git/version/session/worktree facts in one read-only report",
    )
    situate_parser.add_argument("--json", action="store_true", help="emit the report as JSON")

    update_parser = subparsers.add_parser("update", help="update reusable control-plane files")
    update_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list control-plane targets without writing",
    )

    compact_parser = subparsers.add_parser("compact", help="summarise recent session activity")
    compact_parser.add_argument("--days", type=int, default=7, help="number of days to scan (default: 7)")
    compact_parser.add_argument("--all", action="store_true", dest="scan_all", help="scan all sessions")
    compact_parser.add_argument("--output", type=str, default=None, help="write summary to file instead of stdout")

    retrieval_spec_parser = subparsers.add_parser(
        "retrieval-spec",
        help="validate and preview an inline Retrieval Specification",
    )
    retrieval_spec_sub = retrieval_spec_parser.add_subparsers(
        dest="retrieval_spec_command",
        required=True,
    )
    retrieval_spec_preview = retrieval_spec_sub.add_parser(
        "preview",
        help="plan a JSON inline spec against canonical Markdown without creating a pack",
    )
    retrieval_spec_preview.add_argument(
        "--spec-file",
        help="UTF-8 JSON file containing the inline spec; use - for stdin",
    )
    retrieval_spec_preview.add_argument(
        "--profile",
        help="exact project-local retrieval profile ID (requires --profile-version)",
    )
    retrieval_spec_preview.add_argument(
        "--profile-version",
        type=int,
        help="exact project-local retrieval profile version (requires --profile)",
    )
    retrieval_spec_preview.add_argument(
        "--overrides-file",
        help="optional UTF-8 JSON object of profile overrides; use - for stdin",
    )
    retrieval_spec_preview.add_argument(
        "--cwd",
        default=".",
        help="project path used for nearest-runtime discovery (default: current directory)",
    )

    task_packet_parser = subparsers.add_parser(
        "task-packet",
        help="preview or compile one deterministic Task Packet",
    )
    task_packet_sub = task_packet_parser.add_subparsers(
        dest="task_packet_command", required=True,
    )
    for task_packet_command in ("preview", "compile"):
        task_packet_operation = task_packet_sub.add_parser(
            task_packet_command,
            help=(
                "validate, measure, resolve, and print the complete deterministic packet"
                if task_packet_command == "preview"
                else "compile and print the complete deterministic packet"
            ),
        )
        task_packet_operation.add_argument(
            "--dispatch-file", required=True,
            help="UTF-8 JSON Task Dispatch object; use - for stdin",
        )
        task_packet_operation.add_argument(
            "--binding-file", required=True,
            help="UTF-8 JSON measured runtime binding object",
        )
        task_packet_operation.add_argument(
            "--cwd", default=".",
            help="project path used for runtime discovery (default: current directory)",
        )
        task_packet_operation.add_argument(
            "--environment-file",
            help="optional UTF-8 JSON environment object",
        )
        task_packet_operation.add_argument(
            "--pricing-file",
            help="optional UTF-8 JSON pricing object",
        )
        if task_packet_command == "compile":
            task_packet_operation.add_argument(
                "--output", help="explicit file export path; stdout is the default",
            )
            task_packet_operation.add_argument(
                "--overwrite", action="store_true",
                help="allow --output to replace an existing file",
            )

    governance_load = task_packet_sub.add_parser(
        "governance-load",
        help="print one digest-verified governance file pinned by a packet-v2 Task Packet",
    )
    governance_load.add_argument("--packet-file", required=True, help="UTF-8 JSON compiled Task Packet; use - for stdin")
    governance_load.add_argument("--name", required=True, choices=("agent_rules", "session_logging"))
    governance_load.add_argument("--cwd", default=".", help="project path used for runtime discovery")

    subparsers.add_parser("doctor", help="check Memory Seed control-plane files")
    subparsers.add_parser("version", help="print Memory Seed control-plane version")

    args = parser.parse_args(argv)

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    if args.command in (None, "help"):
        _print_help(parser)
        return 0

    if args.command == "version":
        print(get_version())
        return 0

    # Fail closed when the console script on PATH is a different build from the
    # checkout the caller is standing in. `version` and `help` are exempt above
    # (and argparse serves `<cmd> --help` before reaching here): they are how you
    # diagnose exactly this, and neither reads nor writes the tree.
    #
    # `situate` and `worktree guard` are deliberately NOT exempt, though they are
    # the orientation commands an agent reaches for first. Their output from a
    # foreign build is precisely the untrustworthy report this guard exists to
    # stop - a stale worktree list or version read as ground truth is worse than
    # no report - and the refusal names both resolved paths and the working
    # invocation, which orients better than a stale answer would.
    provenance = package_provenance(Path("."))
    if provenance.foreign and not provenance.allowed:
        # Echo the caller's own tokens so the remedy line is copy-pasteable;
        # args.command alone would drop the subcommand and every flag.
        invoked = " ".join(sys.argv[1:] if argv is None else argv) or args.command
        print(foreign_package_message(provenance, command=invoked), file=sys.stderr)
        return 2

    if args.command in process_tools.PACKAGE_COMMANDS:
        return process_tools.run_package_process_command("memory-seed", args)

    if args.command == "retrieval-spec":
        from .retrieval import (
            RetrievalSpecResolutionError,
            canonical_retrieval_json,
        )
        from .retrieval_adapters import RetrievalInputValidationError, preview_retrieval_input
        from .retrieval_profiles import RetrievalProfileValidationError
        from .retrieval_spec import RetrievalSpecValidationError

        try:
            spec = _read_json_object(args.spec_file, label="spec") if args.spec_file else None
            overrides = (
                _read_json_object(args.overrides_file, label="overrides")
                if args.overrides_file else None
            )
            payload = {
                "ok": True,
                "preview": preview_retrieval_input(
                    spec=spec,
                    profile=args.profile,
                    profile_version=args.profile_version,
                    overrides=overrides,
                    cwd=args.cwd,
                ),
            }
            sys.stdout.write(canonical_retrieval_json(payload))
            return 0
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            if isinstance(exc, RetrievalProfileValidationError):
                error = {
                    "code": "invalid_profile",
                    "message": str(exc),
                    "stage": "profile_expansion",
                    "completed_stages": [],
                    "details": {},
                }
            elif isinstance(exc, (RetrievalInputValidationError, RetrievalSpecValidationError)):
                error = {
                    "code": "invalid_spec",
                    "message": str(exc),
                    "stage": "validation",
                    "completed_stages": [],
                    "details": {},
                }
            else:
                error = {
                    "code": "invalid_spec",
                    "message": str(exc),
                    "stage": "input",
                    "completed_stages": [],
                    "details": {},
                }
            sys.stderr.write(canonical_retrieval_json({"ok": False, "error": error}))
            return 2
        except RetrievalSpecResolutionError as exc:
            sys.stderr.write(
                canonical_retrieval_json({"ok": False, "error": exc.to_dict()})
            )
            return 1

    if args.command == "task-packet":
        from .retrieval import RetrievalSpecResolutionError, canonical_retrieval_json
        from .retrieval_profiles import RetrievalProfileValidationError
        from .task_packet import (
            TaskPacketValidationError,
            canonical_task_packet_json,
            compile_task_packet,
            load_task_packet_governance,
        )

        if args.task_packet_command == "governance-load":
            try:
                packet = _read_json_object(args.packet_file, label="packet")
                loaded = load_task_packet_governance(packet, args.name, args.cwd)
                sys.stdout.write(canonical_retrieval_json({"ok": True, "governance": loaded}))
                return 0
            except TaskPacketValidationError as exc:
                sys.stderr.write(canonical_retrieval_json({"ok": False, "error": exc.to_dict()}))
                return 1
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                sys.stderr.write(canonical_retrieval_json({"ok": False, "error": {
                    "code": "invalid_input", "message": str(exc), "stage": "input", "details": {},
                }}))
                return 1

        try:
            dispatch = _read_json_object(args.dispatch_file, label="dispatch")
            binding = _read_json_object(args.binding_file, label="binding")
            environment = (
                _read_json_object(args.environment_file, label="environment")
                if args.environment_file else None
            )
            pricing = (
                _read_json_object(args.pricing_file, label="pricing")
                if args.pricing_file else None
            )
            packet = compile_task_packet(
                dispatch, binding, args.cwd, environment=environment, pricing=pricing
            )
            rendered = canonical_task_packet_json(packet)
            if getattr(args, "output", None):
                _atomic_export_json(args.output, rendered, overwrite=args.overwrite)
            else:
                sys.stdout.write(rendered)
            return 0
        except TaskPacketValidationError as exc:
            sys.stderr.write(canonical_retrieval_json({"ok": False, "error": exc.to_dict()}))
            return 1
        except RetrievalSpecResolutionError as exc:
            sys.stderr.write(canonical_retrieval_json({"ok": False, "error": exc.to_dict()}))
            return 1
        except RetrievalProfileValidationError as exc:
            sys.stderr.write(canonical_retrieval_json({"ok": False, "error": {
                "code": "invalid_profile", "message": str(exc),
                "stage": "profile_expansion", "details": {},
            }}))
            return 1
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            error = {
                "code": "invalid_input",
                "message": str(exc),
                "stage": "input",
                "details": {},
            }
            sys.stderr.write(canonical_retrieval_json({"ok": False, "error": error}))
            return 2

    if args.command == "user":
        target = Path(".").resolve()
        if args.user_command == "show":
            user = read_local_user(target)
            if user is None:
                print("No Memory Seed user configured.")
            else:
                print(user)
            return 0
        if args.user_command == "set":
            try:
                write_local_user(target, args.slug)
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            print(f"Active Memory Seed user set to {args.slug}.")
            return 0
        if args.user_command == "clear":
            if clear_local_user(target):
                print("Cleared Memory Seed user.")
            else:
                print("No Memory Seed user configured.")
            return 0

    if args.command == "adr":
        from .adr import (
            AdrPredecessor,
            ConstitutionRef,
            adr_to_dict,
            check_adrs,
            iter_adrs,
            parse_adr,
            promote_decision,
            record_reviewed_no_change,
            revise_adr,
            transition_adr,
        )

        cwd = Path(".").resolve()
        if args.adr_command == "promote":
            predecessors: list[AdrPredecessor] = []
            for raw in args.predecessor:
                if "=" not in raw:
                    print("--predecessor must be decision=relation_assertion", file=sys.stderr)
                    return 1
                decision, assertion = raw.split("=", 1)
                predecessors.append(AdrPredecessor(decision.strip(), assertion.strip()))
            constitution_refs: list[ConstitutionRef] = []
            for raw in args.constitution_ref:
                if "=" not in raw:
                    print("--constitution-ref must be ref=role", file=sys.stderr)
                    return 1
                ref, role = raw.rsplit("=", 1)
                constitution_refs.append(ConstitutionRef(ref.strip(), role.strip()))
            result = promote_decision(
                cwd,
                adr_id=args.adr_id,
                source_entry_id=args.entry_id,
                source_decision=args.decision,
                title=args.title,
                topics=tuple(item.strip() for item in args.topics.split(",") if item.strip()),
                user_initials=args.user_initials,
                agent_type=args.agent_type,
                source=args.source,
                decision=args.summary_decision,
                reason=args.reason, impact=args.impact, why=args.why, evolution=args.evolution,
                update_entry_id=args.update_entry_id,
                direct_predecessors=predecessors,
                supporting_decisions=tuple(args.supporting_decision),
                constitution_refs=constitution_refs,
                founding_source=args.founding_source,
                founding_quote=args.founding_quote,
                timestamp=args.timestamp,
                dry_run=args.dry_run,
            )
        elif args.adr_command == "revise":
            predecessors = []
            for raw in args.predecessor:
                if "=" not in raw:
                    print("--predecessor must be decision=relation_assertion", file=sys.stderr)
                    return 1
                predecessor, assertion = raw.split("=", 1)
                predecessors.append(AdrPredecessor(predecessor.strip(), assertion.strip()))
            result = revise_adr(
                cwd,
                adr_id=args.adr_id,
                decision_ref=args.decision_ref,
                decision=args.decision,
                reason=args.reason, impact=args.impact, why=args.why, evolution=args.evolution,
                update_entry_id=args.update_entry_id,
                source=args.source,
                predecessors=predecessors,
                timestamp=args.timestamp,
                dry_run=args.dry_run,
            )
        elif args.adr_command == "transition":
            result = transition_adr(
                cwd,
                adr_id=args.adr_id,
                status=args.status,
                decision_ref=args.decision_ref,
                update_entry_id=args.update_entry_id,
                expected_authoritative_decision=args.expected_authoritative_decision,
                expected_previous_status=args.expected_previous_status,
                source=args.source,
                replacement_adr=args.replacement_adr,
                reason=args.reason,
                timestamp=args.timestamp,
                dry_run=args.dry_run,
            )
        elif args.adr_command == "reviewed":
            result = record_reviewed_no_change(
                cwd,
                adr_id=args.adr_id,
                entry_id=args.entry,
                reason=args.reason,
                timestamp=args.timestamp,
                dry_run=args.dry_run,
            )
        elif args.adr_command == "show":
            path = resolve_runtime(cwd).memory_dir / "decisions" / f"{args.adr_id}.md"
            if not path.exists():
                print(f"ADR not found: {args.adr_id}", file=sys.stderr)
                return 1
            record = parse_adr(path)
            if args.json:
                print(json.dumps(adr_to_dict(record), indent=2))
                return 0
            print(f"{record.adr_id}: {record.title}")
            print(f"Current decision: {record.current_decision}")
            print(f"Current status: {record.current_status or 'invalid/unset'}")
            print(f"Source: {record.source}")
            print(f"Path: {path}")
            return 0
        elif args.adr_command == "list":
            records = list(iter_adrs(cwd))
            if args.json:
                print(json.dumps([adr_to_dict(record, include_events=False) for record in records], indent=2))
            elif not records:
                print("No ADR sidecars")
            else:
                for record in records:
                    print(
                        f"{record.adr_id}\t{record.current_status}\t"
                        f"{record.authoritative_decision or '-'}\t{record.title}"
                    )
            return 0
        else:
            ok, issues = check_adrs(cwd)
            if args.json:
                print(json.dumps({"ok": ok, "issues": issues}, indent=2))
            elif ok:
                print("ADR sidecars OK")
            else:
                print("ADR sidecar issues:", file=sys.stderr)
                for issue in issues:
                    print(f"  - {issue}", file=sys.stderr)
            return 0 if ok else 1
        if not result.ok:
            print("ADR write refused:", file=sys.stderr)
            for issue in result.issues:
                print(f"  - {issue}", file=sys.stderr)
            return 1
        verb = "Would write" if args.dry_run else "Wrote"
        print(f"{verb} {result.adr_id} ({result.current_status}) to {result.path}")
        if result.rendered:
            print()
            print(result.rendered, end="")
        return 0

    if args.command == "session":
        if args.session_command == "target":
            try:
                target = session_target(
                    cwd=Path(".").resolve(),
                    date_str=args.date,
                    explicit_user=args.user,
                    create=args.create,
                )
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            try:
                print(target.path.relative_to(Path(".").resolve()).as_posix())
            except ValueError:
                print(target.path.as_posix())
            return 0
        if args.session_command == "fuse":
            result = session_fuse(
                cwd=Path(".").resolve(),
                branch=args.branch,
                base=args.base,
                apply=args.apply,
                user_approved=args.user_approved,
            )
            if result.issues:
                print("Session fuse blocked:", file=sys.stderr)
                for issue in result.issues:
                    print(f"  - {issue}", file=sys.stderr)
                return 1
            if not (
                result.planned_entries
                or result.planned_sidecars
                or result.planned_link_sidecars
                or result.planned_topic_sidecars
                or result.removed_sources
            ):
                print("No branch session entries or sidecars need fusing.")
                return 0
            entry_verb = "Imported" if args.apply else "Would import"
            diagram_verb = "Imported diagram" if args.apply else "Would import diagram"
            link_verb = "Imported link sidecar" if args.apply else "Would import link sidecar"
            topic_verb = "Imported topic sidecar" if args.apply else "Would import topic sidecar"
            remove_verb = "Removed source" if args.apply else "Would remove source"
            for planned in result.planned_entries:
                print(f"{entry_verb}: {planned}")
            for planned in result.planned_sidecars:
                print(f"{diagram_verb}: {planned}")
            for planned in result.planned_link_sidecars:
                print(f"{link_verb}: {planned}")
            for planned in result.planned_topic_sidecars:
                print(f"{topic_verb}: {planned}")
            for source in result.removed_sources:
                print(f"{remove_verb}: {source}")
            if result.already_present:
                for entry_id in sorted(set(result.already_present)):
                    if entry_id:
                        print(f"Already present: {entry_id}")
            if args.apply:
                print("Session fuse applied.")
            else:
                print("No files changed. Rerun with --apply during a git merge to write these changes.")
            return 0
        if args.session_command == "merge-branch":
            result = session_merge_branch(
                cwd=Path(".").resolve(),
                branch=args.branch,
                dry_run=args.dry_run,
                user_approved=args.user_approved,
            )
            if result.issues:
                print("Session merge-branch blocked:", file=sys.stderr)
                for issue in result.issues:
                    print(f"  - {issue}", file=sys.stderr)
                # Only a genuinely parked merge (or one that refused to abort)
                # gets the manual-resolution instruction; a refusal that already
                # rolled itself back would strand the reader hunting merge state
                # that no longer exists.
                if result.merge_in_progress:
                    print(
                        "The git merge was left in progress; resolve and commit manually, or git merge --abort.",
                        file=sys.stderr,
                    )
                elif result.merge_aborted:
                    print(
                        "The git merge was aborted automatically; the working tree is back to its "
                        "pre-merge state and nothing was committed.",
                        file=sys.stderr,
                    )
                return 1
            if result.conflicts:
                print("Non-session conflicts require manual resolution:", file=sys.stderr)
                for path in result.conflicts:
                    print(f"  - {path}", file=sys.stderr)
                print(
                    "The git merge was left in progress; resolve these paths, then run "
                    "'memory-seed session fuse --branch <branch> --apply' and commit.",
                    file=sys.stderr,
                )
                return 1
            entry_verb = "Would import" if args.dry_run else "Imported"
            diagram_verb = "Would import diagram" if args.dry_run else "Imported diagram"
            link_verb = "Would import link sidecar" if args.dry_run else "Imported link sidecar"
            topic_verb = "Would import topic sidecar" if args.dry_run else "Imported topic sidecar"
            remove_verb = "Would remove source" if args.dry_run else "Removed source"
            for planned in result.planned_entries:
                print(f"{entry_verb}: {planned}")
            for planned in result.planned_sidecars:
                print(f"{diagram_verb}: {planned}")
            for planned in result.planned_link_sidecars:
                print(f"{link_verb}: {planned}")
            for planned in result.planned_topic_sidecars:
                print(f"{topic_verb}: {planned}")
            for source in result.removed_sources:
                print(f"{remove_verb}: {source}")
            if result.already_present:
                for entry_id in sorted(set(result.already_present)):
                    if entry_id:
                        print(f"Already present: {entry_id}")
            if args.dry_run:
                _print_session_merge_worktree_cleanup(result, dry_run=True)
                print("Dry run - no merge performed. Rerun without --dry-run to merge and fuse.")
            elif result.committed:
                print("Merge committed.")
                if result.stamped_entries:
                    print(f"Stamped {len(result.stamped_entries)} Memory-Entry trailer(s) on the merge commit.")
                else:
                    # A feature branch that carries no session entry usually
                    # means the entry was appended on the trunk instead - the
                    # work is recorded, but as trunk work. Two things are then
                    # gone for good: the Trail draws it in the main lane rather
                    # than its own, and this merge commit gets no Memory-Entry
                    # trailer, so fork/merge geometry falls back to the
                    # positional estimate. Neither is recoverable afterwards
                    # without rewriting published history, which is why this
                    # warns HERE - the last moment it is still cheap to fix.
                    # Legitimately entry-free branches exist (trunk-only
                    # workflows like stub classification), so this never fails.
                    print(
                        f"Note: branch {args.branch} carried no session entry, so the merge commit has "
                        "no Memory-Entry trailer and the Trail will show this work on the trunk lane.",
                        file=sys.stderr,
                    )
                    print(
                        "  If you logged on the trunk instead: append the entry on the branch BEFORE "
                        "merging next time (stash unrelated changes first, so a dirty tree does not "
                        "reorder the steps).",
                        file=sys.stderr,
                    )
                _print_session_merge_worktree_cleanup(result, dry_run=False)
                if result.source_worktree is not None and result.worktree_cleanup_status != "removed":
                    return 2
            else:
                print(f"Branch {args.branch} is already merged into HEAD; nothing to do.")
            return 0
        if args.session_command == "prepare-pr":
            result = session_prepare_pr_branch(
                cwd=Path(".").resolve(),
                branch=args.branch,
                base_branch=args.base_branch,
                dry_run=args.dry_run,
            )
            if result.issues:
                print("Session prepare-pr blocked:", file=sys.stderr)
                for issue in result.issues:
                    print(f"  - {issue}", file=sys.stderr)
                if result.merge_in_progress:
                    print(
                        "The git merge was left in progress; resolve and commit manually, or git merge --abort.",
                        file=sys.stderr,
                    )
                elif result.merge_aborted:
                    print(
                        "The git merge was aborted automatically; the branch is back to its "
                        "pre-merge state and nothing was committed.",
                        file=sys.stderr,
                    )
                return 1
            if result.conflicts:
                print("Non-session conflicts require manual resolution:", file=sys.stderr)
                for path in result.conflicts:
                    print(f"  - {path}", file=sys.stderr)
                print(
                    "The git merge was left in progress; resolve these paths on the task branch, then rerun "
                    "'memory-seed session prepare-pr --branch <branch>'.",
                    file=sys.stderr,
                )
                return 1
            entry_verb = "Would prepare" if args.dry_run else "Prepared"
            diagram_verb = "Would prepare diagram" if args.dry_run else "Prepared diagram"
            link_verb = "Would prepare link sidecar" if args.dry_run else "Prepared link sidecar"
            topic_verb = "Would prepare topic sidecar" if args.dry_run else "Prepared topic sidecar"
            remove_verb = "Would remove source" if args.dry_run else "Removed source"
            for planned in result.planned_entries:
                print(f"{entry_verb}: {planned}")
            for planned in result.planned_sidecars:
                print(f"{diagram_verb}: {planned}")
            for planned in result.planned_link_sidecars:
                print(f"{link_verb}: {planned}")
            for planned in result.planned_topic_sidecars:
                print(f"{topic_verb}: {planned}")
            for source in result.removed_sources:
                print(f"{remove_verb}: {source}")
            if result.already_present:
                for entry_id in sorted(set(result.already_present)):
                    if entry_id:
                        print(f"Already present: {entry_id}")
            if args.dry_run:
                print("Dry run - no branch merge performed.")
            elif result.changed:
                print("Branch prep committed.")
                if result.stamped_entries:
                    print(f"Stamped {len(result.stamped_entries)} Memory-Entry trailer(s) on the prep commit.")
            else:
                print(f"Branch {args.branch} is already up to date with {result.base_branch}; nothing to do.")
            return 0
        if args.session_command == "open-pr":
            result = session_open_pr(
                cwd=Path(".").resolve(),
                branch=args.branch,
                base_branch=args.base_branch,
                dry_run=args.dry_run,
                user_approved=args.user_approved,
            )
            if result.issues:
                print("Session open-pr blocked:", file=sys.stderr)
                for issue in result.issues:
                    print(f"  - {issue}", file=sys.stderr)
                return 1
            if result.conflicts:
                print("Non-session conflicts require manual resolution:", file=sys.stderr)
                for path in result.conflicts:
                    print(f"  - {path}", file=sys.stderr)
                return 1
            for planned in result.planned_entries:
                print(f"Prepared entry: {planned}")
            for planned in result.planned_sidecars:
                print(f"Prepared diagram: {planned}")
            for planned in result.planned_link_sidecars:
                print(f"Prepared link sidecar: {planned}")
            for planned in result.planned_topic_sidecars:
                print(f"Prepared topic sidecar: {planned}")
            for source in result.removed_sources:
                print(f"Removed source: {source}")
            if result.already_present:
                for entry_id in sorted(set(result.already_present)):
                    if entry_id:
                        print(f"Already present: {entry_id}")
            if result.pr_title:
                print(f"PR title: {result.pr_title}")
            if result.pr_body:
                print("PR body:")
                print(result.pr_body)
            if args.dry_run:
                print("Dry run - no push or PR performed.")
            else:
                if result.pushed:
                    print(f"Pushed branch {args.branch} to {result.remote_name}.")
                if result.opened:
                    print(f"PR created: {result.pr_url or '(no URL reported)'}")
            return 0
        if args.session_command == "integrate":
            mode = read_integration_mode(Path(".").resolve())
            print(f"Integration mode: {mode}")
            if mode == "pr":
                result = session_open_pr(
                    cwd=Path(".").resolve(),
                    branch=args.branch,
                    base_branch=args.base_branch,
                    dry_run=args.dry_run,
                    user_approved=args.user_approved,
                )
                if result.issues:
                    print("Session integrate blocked:", file=sys.stderr)
                    for issue in result.issues:
                        print(f"  - {issue}", file=sys.stderr)
                    return 1
                if result.conflicts:
                    print("Non-session conflicts require manual resolution:", file=sys.stderr)
                    for path in result.conflicts:
                        print(f"  - {path}", file=sys.stderr)
                    return 1
                for planned in result.planned_entries:
                    print(f"Prepared entry: {planned}")
                for planned in result.planned_sidecars:
                    print(f"Prepared diagram: {planned}")
                for planned in result.planned_link_sidecars:
                    print(f"Prepared link sidecar: {planned}")
                for planned in result.planned_topic_sidecars:
                    print(f"Prepared topic sidecar: {planned}")
                for source in result.removed_sources:
                    print(f"Removed source: {source}")
                if result.pr_title:
                    print(f"PR title: {result.pr_title}")
                if result.pr_body:
                    print("PR body:")
                    print(result.pr_body)
                if args.dry_run:
                    print("Dry run - no push or PR performed.")
                else:
                    if result.pushed:
                        print(f"Pushed branch {args.branch} to {result.remote_name}.")
                    if result.opened:
                        print(f"PR created: {result.pr_url or '(no URL reported)'}")
                return 0
            result = session_merge_branch(
                cwd=Path(".").resolve(),
                branch=args.branch,
                dry_run=args.dry_run,
                user_approved=args.user_approved,
            )
            if result.issues:
                print("Session integrate blocked:", file=sys.stderr)
                for issue in result.issues:
                    print(f"  - {issue}", file=sys.stderr)
                if result.merge_in_progress:
                    print(
                        "The git merge was left in progress; resolve and commit manually, or git merge --abort.",
                        file=sys.stderr,
                    )
                elif result.merge_aborted:
                    print(
                        "The git merge was aborted automatically; the working tree is back to its "
                        "pre-merge state and nothing was committed.",
                        file=sys.stderr,
                    )
                return 1
            if result.conflicts:
                print("Non-session conflicts require manual resolution:", file=sys.stderr)
                for path in result.conflicts:
                    print(f"  - {path}", file=sys.stderr)
                print(
                    "The git merge was left in progress; resolve these paths, then run "
                    "'memory-seed session fuse --branch <branch> --apply' and commit.",
                    file=sys.stderr,
                )
                return 1
            entry_verb = "Would import" if args.dry_run else "Imported"
            diagram_verb = "Would import diagram" if args.dry_run else "Imported diagram"
            link_verb = "Would import link sidecar" if args.dry_run else "Imported link sidecar"
            topic_verb = "Would import topic sidecar" if args.dry_run else "Imported topic sidecar"
            remove_verb = "Would remove source" if args.dry_run else "Removed source"
            for planned in result.planned_entries:
                print(f"{entry_verb}: {planned}")
            for planned in result.planned_sidecars:
                print(f"{diagram_verb}: {planned}")
            for planned in result.planned_link_sidecars:
                print(f"{link_verb}: {planned}")
            for planned in result.planned_topic_sidecars:
                print(f"{topic_verb}: {planned}")
            for source in result.removed_sources:
                print(f"{remove_verb}: {source}")
            if result.already_present:
                for entry_id in sorted(set(result.already_present)):
                    if entry_id:
                        print(f"Already present: {entry_id}")
            if args.dry_run:
                _print_session_merge_worktree_cleanup(result, dry_run=True)
                print("Dry run - no merge performed. Rerun without --dry-run to merge and fuse.")
            elif result.committed:
                print("Merge committed.")
                if result.stamped_entries:
                    print(f"Stamped {len(result.stamped_entries)} Memory-Entry trailer(s) on the merge commit.")
                _print_session_merge_worktree_cleanup(result, dry_run=False)
            else:
                print(f"Branch {args.branch} is already merged into HEAD; nothing to do.")
            return 0
        if args.session_command == "append":
            from .core import session_append_entry

            if args.body_file:
                body = Path(args.body_file).read_text(encoding="utf-8")
            else:
                body = sys.stdin.read()
            if not body.strip():
                print("Entry body is empty (pass --body-file or pipe the typed DRAFTS record prose on stdin).", file=sys.stderr)
                return 1
            decisions: list[dict] = []
            if args.decisions_file:
                try:
                    decoded = json.loads(Path(args.decisions_file).read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    print(f"Could not read --decisions-file as JSON: {exc}", file=sys.stderr)
                    return 1
                if not isinstance(decoded, list):
                    print("--decisions-file must contain a JSON list of record objects.", file=sys.stderr)
                    return 1
                decisions = decoded
            elif args.topics or args.related or args.replaces or args.evolves:
                # The entry-level flags attribute to the ENTRY, so every decision
                # in a multi-decision entry inherits one shared list and none owns
                # its own. Measured cost of leaving this silent: decision-keyed
                # attribution across this corpus fell 92% (July) -> 8% (August)
                # while coverage stayed at 100%, because `session append` accepted
                # the entry-level form and session_logging.md documented it. MCP
                # has required the envelope since 2026-07-31; this warns rather
                # than refusing, so an existing script keeps working while its
                # author is told what it costs and what to use instead.
                print(
                    "warning: --topics/--related/--replaces/--evolves attribute at ENTRY level, so no "
                    "record owns its own topics or links. Prefer --decisions-file with one object per "
                    "record (see session_logging.md). memory_session_append requires it.",
                    file=sys.stderr,
                )

            def _csv(raw: str) -> tuple[str, ...]:
                return tuple(item.strip() for item in raw.split(",") if item.strip())

            def _ref_list(values: list[str] | None) -> tuple[str, ...]:
                """Lifecycle refs from a repeatable, still-comma-splittable flag.

                Grammar v2 (2026-07-24) puts commas INSIDE a ref -
                `mse_x:d1,d4` addresses two decisions of one target - which
                collides with the comma the flag has always used as its item
                separator. Splitting naively would silently turn that ref into
                a valid one plus the garbage token `d4`. So a fragment that is
                a bare ordinal rejoins the ref it was split from; everything
                else is a separate ref, and repeating the flag avoids the
                ambiguity entirely.
                """
                refs: list[str] = []
                for value in values or ():
                    for part in (p.strip() for p in value.split(",")):
                        if not part:
                            continue
                        if re.fullmatch(r"d\d+", part) and refs:
                            refs[-1] = f"{refs[-1]},{part}"
                        else:
                            refs.append(part)
                return tuple(refs)

            # CLI and MCP share one content-bound ADR review preflight. The
            # first lifecycle-linked call prints the exact receipt and full ADR
            # contexts, writes zero bytes, and the retry supplies outcomes in
            # --decisions-file plus --adr-review-receipt.
            from .adr import append_review_proposal, preflight_append_adr_review

            append_timestamp = args.timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")
            proposal = append_review_proposal(
                title=args.title,
                body=body,
                timestamp=append_timestamp,
                user_initials=args.user_initials,
                agent_type=args.agent_type,
                decisions=decisions,
            )
            review = preflight_append_adr_review(
                Path(".").resolve(),
                proposal=proposal,
                decisions=decisions,
                supplied_receipt=args.adr_review_receipt,
            )
            if not review.ok:
                print("Append refused:", file=sys.stderr)
                for issue in review.issues:
                    print(f"  - {issue}", file=sys.stderr)
                print(f"ADR review receipt: {review.receipt}", file=sys.stderr)
                print(f"Timestamp: {append_timestamp}", file=sys.stderr)
                print("Lifecycle targets: " + ", ".join(review.targets), file=sys.stderr)
                print("Matched ADRs:", file=sys.stderr)
                print(json.dumps(list(review.contexts), indent=2), file=sys.stderr)
                return 1

            result = session_append_entry(
                cwd=Path(".").resolve(),
                title=args.title,
                body=body,
                user_initials=args.user_initials,
                agent_type=args.agent_type,
                topics=_csv(args.topics),
                related_entries=_ref_list(args.related),
                replaces=_ref_list(args.replaces),
                evolves=_ref_list(args.evolves),
                decisions=decisions,
                adr_review_contexts=review.contexts,
                adr_review_outcomes=review.outcomes,
                project_path=args.project_path,
                subproject_path=args.subproject_path,
                branch=args.branch,
                auto_branch=not args.no_branch,
                timestamp=append_timestamp,
                explicit_user=args.user,
                dry_run=args.dry_run,
            )
            if not result.ok:
                print("Append refused:", file=sys.stderr)
                for issue in result.issues:
                    print(f"  - {issue}", file=sys.stderr)
                return 1
            if args.dry_run:
                print(f"Would append {result.entry_id} ({result.timestamp}) to {result.path}")
                if result.rendered:
                    # The exact block a real call would append — inspect, then
                    # rerun without --dry-run to commit to it.
                    print()
                    print(result.rendered, end="")
                return 0
            print(f"Appended {result.entry_id} ({result.timestamp}) to {result.path}")
            return 0
        if args.session_command == "reorder":
            from .core import session_reorder

            result = session_reorder(
                cwd=Path(".").resolve(), date_str=args.date, explicit_user=args.user, apply=args.apply
            )
            if not result.ok:
                print(f"Reorder refused for {result.path}:", file=sys.stderr)
                for issue in result.issues:
                    print(f"  - {issue}", file=sys.stderr)
                return 1
            if not result.changed:
                print(f"{result.path}: already chronological ({len(result.order_before)} entries).")
                return 0
            print(f"{result.path}:")
            print("  current order:")
            for item in result.order_before:
                print(f"    {item}")
            print("  chronological order:")
            for item in result.order_after:
                print(f"    {item}")
            if result.applied:
                print("Applied. Run 'memory-seed links check' to confirm integrity.")
            else:
                print("Dry run - rerun with --apply to write (entry bytes are never altered, only block order).")
            return 0
        if args.session_command == "entry-id":
            print(
                generate_session_entry_id(
                    timestamp=args.timestamp,
                    title=args.title,
                    user_initials=args.user_initials,
                    agent_type=args.agent_type,
                    project_path=args.project_path,
                    subproject_path=args.subproject_path,
                )
            )
            return 0

    if args.command == "branch":
        if args.branch_command == "status":
            status = branch_status(cwd=Path(".").resolve())
            if args.json:
                print(json.dumps(status.to_dict(), indent=2, ensure_ascii=False))
                return 0 if status.is_git_repo else 1
            if not status.is_git_repo:
                print(status.recommendation)
                return 1
            print(f"Branch: {status.branch or '(detached)'}")
            print(f"Integration branch: {'yes' if status.is_integration_branch else 'no'}")
            print(f"Dirty: {'yes' if status.dirty else 'no'}")
            print(f"Upstream: {status.upstream or '(none)'}")
            if status.ahead is not None and status.behind is not None:
                print(f"Ahead/behind: {status.ahead}/{status.behind}")
            else:
                print("Ahead/behind: (unavailable)")
            print(f"Worktrees: {status.worktree_count}")
            print(f"Recent merge commit: {status.recent_merge_commit or '(none)'}")
            if status.warnings:
                print("Warnings:")
                for warning in status.warnings:
                    print(f"  - {warning}")
            print(f"Recommendation: {status.recommendation}")
            return 0

    if args.command == "worktree":
        # `classify` is a different capability from guard/status (every
        # worktree vs. this one) and carries its own flags, so it must be
        # handled before the guard call reads guard-only args.
        if args.worktree_command == "classify":
            if args.apply:
                from .worktree_gc import apply_worktree_gc, format_worktree_gc_apply

                result = apply_worktree_gc(
                    cwd=Path(".").resolve(),
                    agent_type=args.gc_agent,
                    integration_branch=args.gc_integration_branch,
                )
                if args.json:
                    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
                else:
                    print(format_worktree_gc_apply(result))
                return 1 if result.refused else 0

            from .worktree_gc import classify_worktrees, format_worktree_gc_report

            report = classify_worktrees(
                cwd=Path(".").resolve(),
                agent_type=args.gc_agent,
                integration_branch=args.gc_integration_branch,
            )
            if args.json:
                print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
            else:
                print(format_worktree_gc_report(report))
            return 0

        result = worktree_guard(
            cwd=Path(".").resolve(),
            agent_type=args.agent,
            write_intent=args.worktree_command == "guard" and args.write_intent,
            allow_root_write=getattr(args, "allow_root_write", False),
        )
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
            return 0 if result.ok else 1
        print(f"Classification: {result.classification}")
        print(f"Severity: {result.severity}")
        print(f"Agent: {result.agent_type or '(not specified)'}")
        print(f"Safe to write: {'yes' if result.safe_to_write else 'no'}")
        print(f"Branch: {result.current_branch or '(detached/unavailable)'}")
        print(f"HEAD: {result.head or '(unavailable)'}")
        print(f"Dirty: {'yes' if result.dirty else 'no' if result.dirty is False else '(unavailable)'}")
        print(f"Worktree path: {result.worktree_path or '(unavailable)'}")
        print(f"Repository root: {result.repo_root or '(unavailable)'}")
        print(f"Expected namespace: {result.expected_namespace or '(not configured)'}")
        print(f"Actual namespace owner: {result.actual_namespace_owner or '(none)'}")
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
        print(f"Recommendation: {result.recommended_next_action}")
        return 0 if result.ok else 1

    if args.command == "encoding":
        if args.encoding_command == "check":
            root = Path(args.path).resolve()
            display_root = root if root.is_dir() else root.parent
            issues = scan_text_encoding(root) + scan_implicit_text_io(root)
            if args.json:
                print(
                    json.dumps(
                        {
                            "path": root.as_posix(),
                            "issue_count": len(issues),
                            "issues": [encoding_issue_to_dict(issue, root=display_root) for issue in issues],
                        },
                        indent=2,
                        ensure_ascii=False,
                    )
                )
                return 1 if issues else 0
            if not issues:
                print("Encoding check OK.")
                return 0
            print(f"Encoding check found {len(issues)} issue(s):", file=sys.stderr)
            for issue in issues:
                data = encoding_issue_to_dict(issue, root=display_root)
                location = f"{data['path']}:{data['line']}" if "line" in data else data["path"]
                print(f"  [{data['kind']}] {location}: {data['detail']}", file=sys.stderr)
            return 1
        if args.encoding_command == "repair":
            root = Path(args.path).resolve()
            display_root = root if root.is_dir() else root.parent
            result = repair_text_encoding(root, dry_run=args.dry_run)

            def display_path(path: Path) -> str:
                try:
                    return path.relative_to(display_root).as_posix()
                except ValueError:
                    return path.as_posix()

            if args.json:
                print(
                    json.dumps(
                        {
                            "path": root.as_posix(),
                            "dry_run": args.dry_run,
                            "planned_count": len(result.planned),
                            "repaired_count": len(result.repaired),
                            "backed_up_count": len(result.backed_up),
                            "blocked_count": len(result.blocked),
                            "planned": [
                                {
                                    "path": display_path(item.path),
                                    "issue_kinds": list(item.issue_kinds),
                                }
                                for item in result.planned
                            ],
                            "repaired": [display_path(item.path) for item in result.repaired],
                            "backed_up": [path.as_posix() for path in result.backed_up],
                            "blocked": [
                                encoding_issue_to_dict(issue, root=display_root)
                                for issue in result.blocked
                            ],
                        },
                        indent=2,
                        ensure_ascii=False,
                    )
                )
                return 1 if result.blocked else 0
            action = "Would repair" if args.dry_run else "Repaired"
            items = result.planned if args.dry_run else result.repaired
            for item in items:
                print(f"{action}: {display_path(item.path)} ({', '.join(item.issue_kinds)})")
            for backup in result.backed_up:
                print(f"Backed up: {backup.as_posix()}")
            for issue in result.blocked:
                data = encoding_issue_to_dict(issue, root=display_root)
                print(f"Blocked [{data['kind']}] {data['path']}: {data['detail']}", file=sys.stderr)
            if not items and not result.blocked:
                print("Encoding repair found no changes.")
            elif args.dry_run:
                print("No files changed.")
            return 1 if result.blocked else 0

    if args.command == "links":
        if args.links_command == "check":
            result = check_session_links(cwd=Path(".").resolve())
            warnings = [issue for issue in result.issues if issue.severity == "warning"]
            errors = [issue for issue in result.issues if issue.severity == "error"]
            for issue in warnings:
                print(f"  [warning] [{issue.kind}] {issue.file}: {issue.detail}")
            if result.ok:
                print(f"Session memory integrity OK ({result.files_checked} file(s) checked).")
                return 0
            print(
                f"Session memory integrity: {len(errors)} error(s) across "
                f"{result.files_checked} file(s):",
                file=sys.stderr,
            )
            for issue in errors:
                print(f"  [{issue.kind}] {issue.file}: {issue.detail}", file=sys.stderr)
            return 1
        if args.links_command == "chain":
            from .retrieval import describe_refines_chain

            view = describe_refines_chain(Path(".").resolve(), args.ref)
            if view is None:
                print(f"{args.ref}: not part of any refines chain (no refines predecessor or successor).")
                return 0
            if args.json:
                import json as _json

                print(_json.dumps(view, indent=2))
                return 0
            print(f"Chain {view['root']} — {view['length']} members, head {view['head']}")
            last = len(view["members"]) - 1
            for index, member in enumerate(view["members"]):
                marker = "root" if index == 0 else ("head" if index == last else "    ")
                date = member["session_date"] or "?"
                title = member["title"] or "(unknown entry)"
                print(f"  {marker}  {member['ref']}  {date}  {title}")
            for adr in view["adrs"]:
                print(f"  ADR: {adr['adr_id']} (authoritative decision {adr['member']})")
            return 0
        if args.links_command == "graph-diff":
            import json as _json

            from .retrieval import diff_graph_snapshots, effective_graph_snapshot

            if bool(args.snapshot) == bool(args.against):
                print(
                    "links graph-diff requires exactly one of --snapshot PATH or --against PATH",
                    file=sys.stderr,
                )
                return 2
            if args.snapshot:
                snapshot = effective_graph_snapshot(Path(".").resolve())
                snapshot_path = Path(args.snapshot)
                snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                snapshot_path.write_text(
                    _json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
                print(
                    f"Graph snapshot written: {snapshot_path.as_posix()} "
                    f"({snapshot['aggregates']['evolves_refs']} evolves refs, "
                    f"{snapshot['aggregates']['nodes_with_successors']} nodes with successors, "
                    f"{snapshot['aggregates']['nodes_refined']} nodes refined)."
                )
                return 0
            # args.against
            against_path = Path(args.against)
            try:
                before = _json.loads(against_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, ValueError) as exc:
                print(f"links graph-diff: cannot read baseline {against_path.as_posix()}: {exc}", file=sys.stderr)
                return 2
            if not isinstance(before, dict):
                print(
                    f"links graph-diff: baseline {against_path.as_posix()} is not a snapshot object",
                    file=sys.stderr,
                )
                return 2
            after = effective_graph_snapshot(Path(".").resolve())
            diff = diff_graph_snapshots(before, after)
            if diff["verdict"] == "error":
                print(f"links graph-diff: {diff['error']}", file=sys.stderr)
                return 2
            if args.json:
                print(_json.dumps(diff, indent=2, sort_keys=True))
                return 0 if diff["verdict"] == "unchanged" else 1
            if diff["verdict"] == "unchanged":
                print("Effective evolves edge set unchanged.")
            else:
                print("Effective evolves edge set CHANGED:", file=sys.stderr)
                for node_id, targets in sorted(diff["evolves_added"].items()):
                    print(f"  + {node_id} evolves {', '.join(targets)}", file=sys.stderr)
                for node_id, targets in sorted(diff["evolves_removed"].items()):
                    print(f"  - {node_id} evolves {', '.join(targets)}", file=sys.stderr)
                deltas = diff["aggregate_deltas"]
                if deltas["evolves_refs"]["delta"] != 0:
                    print(
                        f"  evolves_refs: {deltas['evolves_refs']['before']} -> {deltas['evolves_refs']['after']}",
                        file=sys.stderr,
                    )
                if deltas["nodes_with_successors"]["delta"] != 0:
                    print(
                        "  nodes_with_successors: "
                        f"{deltas['nodes_with_successors']['before']} -> {deltas['nodes_with_successors']['after']}",
                        file=sys.stderr,
                    )
            if diff["refines_successors_added"] or diff["refines_successors_removed"]:
                print("Refines/typing deltas (informational, does not affect verdict):")
                for node_id, targets in sorted(diff["refines_successors_added"].items()):
                    print(f"  + {node_id} refines-successor {', '.join(targets)}")
                for node_id, targets in sorted(diff["refines_successors_removed"].items()):
                    print(f"  - {node_id} refines-successor {', '.join(targets)}")
            return 0 if diff["verdict"] == "unchanged" else 1

    if args.command == "migrate":
        if args.migrate_command == "sessions-layout":
            result = migrate_session_layout(cwd=Path(".").resolve(), dry_run=args.dry_run)
            if result.issues:
                print("Session layout migration blocked:", file=sys.stderr)
                for issue in result.issues:
                    print(f"  - {issue}", file=sys.stderr)
                return 1
            if not result.planned:
                print("No legacy flat session files need migration.")
                return 0
            if args.dry_run:
                for planned in result.planned:
                    print(f"Would migrate: {planned}")
                print("No files changed.")
                return 0
            for migrated in result.migrated:
                print(f"Migrated: {migrated}")
            for backup in result.backed_up:
                print(f"Backed up: {backup.as_posix()}")
            print("Legacy flat session files migrated.")
            return 0
        if args.migrate_command == "sessions-month-layout":
            result = migrate_session_month_layout(cwd=Path(".").resolve(), dry_run=args.dry_run)
            if result.issues:
                print("Session month-layout migration blocked:", file=sys.stderr)
                for issue in result.issues:
                    print(f"  - {issue}", file=sys.stderr)
                return 1
            if not result.planned:
                print("No old session files need month-layout migration.")
                return 0
            if args.dry_run:
                for planned in result.planned:
                    print(f"Would migrate: {planned}")
                print("No files changed.")
                return 0
            for migrated in result.migrated:
                print(f"Migrated: {migrated}")
            for backup in result.backed_up:
                print(f"Backed up: {backup.as_posix()}")
            print("Session files migrated to month folders.")
            return 0

    if args.command == "topics":
        from .topics import TopicSuggestError, check_topics, load_topic_index, suggest_topics_from_file

        if args.topics_command == "list":
            index = load_topic_index(Path(".").resolve())
            if not index.exists:
                print(f"No topic index found at {index.path}.")
                return 1
            print(f"{index.path} (schema_version {index.schema_version or '?'}, {len(index.topics)} topics):")
            for record in index.topics:
                status = "" if record.status == "active" else f"  [{record.status}]"
                aliases = f"  (aliases: {', '.join(record.aliases)})" if record.aliases else ""
                print(f"  {record.slug}{status}{aliases}")
                if record.description:
                    print(f"    {record.description}")
            return 0
        if args.topics_command == "check":
            result = check_topics(Path(".").resolve())
            for issue in result.issues:
                where = f" ({issue.source})" if issue.source else ""
                print(f"  [{issue.severity}] {issue.kind}: {issue.detail}{where}")
            inferred_note = (
                f" {result.entries_with_inferred_topics_only} more carry sidecar-inferred topics only"
                f" (validated by `links check`, not here)."
                if result.entries_with_inferred_topics_only
                else ""
            )
            print(
                f"Topics check: {result.topics_defined} topics defined, "
                f"{result.entries_checked} entries with authored topics checked.{inferred_note}"
            )
            if result.ok:
                print("Topic vocabulary OK.")
                return 0
            print("Topic vocabulary has errors.", file=sys.stderr)
            return 1
        if args.topics_command == "suggest":
            try:
                source, suggestions = suggest_topics_from_file(args.from_path, cwd=Path(".").resolve())
            except TopicSuggestError as exc:
                print(exc.detail, file=sys.stderr)
                return 1
            print(f"Suggested topics for {source}:")
            if not suggestions:
                print("  (no controlled topics matched this file)")
                return 0
            for item in suggestions:
                aliases = f"  aliases: {', '.join(item.topic.aliases)}" if item.topic.aliases else ""
                print(f"  {item.topic.slug}  (score {item.score:.1f})")
                if item.topic.label:
                    print(f"    label: {item.topic.label}")
                if item.topic.description:
                    print(f"    description: {item.topic.description}")
                if aliases:
                    print(aliases)
                why = ", ".join(f"{field}: {', '.join(terms)}" for field, terms in item.evidence)
                print(f"    why: {why}")
            print()
            print("Paste into the entry's YAML:")
            print("topics:")
            for item in suggestions:
                print(f"  - {item.topic.slug}")
            return 0
        if args.topics_command == "amend":
            result = amend_topic_sidecar(
                cwd=Path(".").resolve(),
                entry_id=args.entry,
                decision=args.decision,
                area=args.area,
                activities=args.activity,
                reason=args.reason,
                timestamp=args.timestamp,
                dry_run=args.dry_run,
            )
            if not result.ok:
                print("Topic amendment refused:", file=sys.stderr)
                for issue in result.issues:
                    print(f"  - {issue}", file=sys.stderr)
                return 1
            if args.dry_run:
                print(f"Would append corrected snapshot to {result.path}")
                print()
                print(result.rendered, end="")
            else:
                print(f"Appended corrected snapshot for {result.entry_id}:{result.decision} to {result.path}")
            return 0

    if args.command == "docs":
        if args.docs_command == "check":
            from .docs_check import check_docs, format_docs_check

            result = check_docs(Path(".").resolve())
            text = format_docs_check(result)
            print(text) if result.ok else print(text, file=sys.stderr)
            return 0 if result.ok else 1
        if args.docs_command == "index":
            from .docs_index import apply_docs_index, format_docs_index

            result = apply_docs_index(Path(".").resolve(), check=args.check)
            print(format_docs_index(result, check=args.check))
            return 1 if (args.check and result.stale) else 0

    if args.command == "quality":
        if args.quality_command == "report":
            import json as _json

            from .quality import build_quality_report, format_quality_report

            report = build_quality_report(Path(".").resolve())
            if args.json:
                print(_json.dumps(report.to_dict(), indent=2))
            else:
                print(format_quality_report(report))
            return 0

    if args.command == "link":
        from .semantic_cache import (
            add_related_entry,
            build_related_entry_graph,
            suggest_related_entries,
        )

        cwd = Path(".").resolve()
        if args.link_command == "add":
            try:
                result = add_related_entry(
                    cwd=cwd,
                    target_entry_id=args.target_entry_id,
                    from_entry_id=args.from_entry,
                )
            except LookupError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            source_id = result.source.entry_id
            target_id = result.target.entry_id
            if not result.added:
                print(f"{source_id} already links to {target_id}; nothing to do.")
                return 0
            print(f"Added related_entries edge {source_id} -> {target_id}")
            print(f"  {result.path}")
            check = check_session_links(cwd=cwd)
            errors = [issue for issue in check.issues if issue.severity == "error"]
            if errors:
                print("links check reported errors after the write:", file=sys.stderr)
                for issue in errors:
                    print(f"  [{issue.kind}] {issue.file}: {issue.detail}", file=sys.stderr)
                return 1
            return 0
        if args.link_command == "retract":
            result = apply_link_retract(
                cwd,
                from_entry=args.from_entry,
                kind=args.kind,
                ref=args.ref,
                retype=args.retype,
                note=args.note,
                date_pin=args.date_pin,
                dry_run=args.retract_dry_run,
            )
            if not result.ok:
                # Every guard reports at once: each line is independently
                # fixable, so flattening them into one message would cost the
                # caller a round trip per problem.
                print("link retract refused; nothing was written:", file=sys.stderr)
                for issue in result.issues:
                    print(f"  {issue}", file=sys.stderr)
                return 1
            if not result.written:
                print(f"Would append to {result.path}:")
                print()
                print(result.rendered.rstrip())
                return 0
            for item in result.retracted:
                print(f"Retracted {result.entry_id}: {item}")
            if result.reauthored:
                print(f"Re-authored under {result.reauthored_key}: {result.reauthored}")
            print(f"  {result.path}")
            check = check_session_links(cwd=cwd)
            errors = [issue for issue in check.issues if issue.severity == "error"]
            if errors:
                print("links check reported errors after the write:", file=sys.stderr)
                for issue in errors:
                    print(f"  [{issue.kind}] {issue.file}: {issue.detail}", file=sys.stderr)
                return 1
            return 0
        if args.link_command == "suggest":
            try:
                target, ranked = suggest_related_entries(
                    cwd=cwd, entry_id=args.for_entry, top_k=args.top_k
                )
            except LookupError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            label = target.entry_id or target.title
            print(f"Suggested related_entries for {label} ({target.title}):")
            if not ranked:
                print("  (no older candidate entries found)")
                return 0
            from .core import entry_body_decisions

            for item in ranked:
                chunk = item.chunk
                print(f"  {chunk.entry_id}  {chunk.session_date}  {chunk.title}  (score {item.final_score:.3f})")
                if item.shared_files:
                    print(f"    shares: {', '.join(item.shared_files)}")
                # Decision structure, so a lifecycle edge can be narrowed to
                # :dN at authoring time - the one moment the author knows which
                # decision the edge targets (write-time grammar, 2026-07-24).
                decisions = entry_body_decisions(chunk.text)
                if len(decisions) >= 2:
                    listing = " / ".join(f"{d.ordinal} {d.name}".strip() for d in decisions)
                    print(f"    decisions: {listing}  (narrow a lifecycle edge as {chunk.entry_id}:dN)")
            print()
            print("Litmus: retires it -> replaces; refines while it stays valid -> evolves; else related.")
            print("Patterns that are evolves: implementing what an earlier entry proposed/scoped, and")
            print("completing a design call an earlier entry deferred. Landing/merging existing work is")
            print("NOT a lifecycle edge; parallel steps of one campaign are related at most.")
            print()
            print("Paste into the entry's YAML (or narrow lifecycle refs to :dN):")
            print("related_entries:")
            for item in ranked:
                print(f"  - {item.chunk.entry_id}")
            return 0
        if args.link_command == "batch-collect":
            from .retrieval import collect_link_swarm_run

            try:
                result = collect_link_swarm_run(args.run_dir)
            except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
                print(str(exc), file=sys.stderr)
                return 1
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0

        if args.link_command == "batch-finalize":
            from .retrieval import finalize_link_swarm_run

            try:
                approval = _read_json_object(args.approval_file, label="approval file")
                result = finalize_link_swarm_run(
                    args.run_dir,
                    approval,
                    cwd=cwd,
                    retention_days=args.retention_days,
                )
            except (FileExistsError, FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
                print(str(exc), file=sys.stderr)
                return 1
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0

        if args.link_command == "batch-gc":
            from .retrieval import gc_link_swarm_runs

            runs_dir = args.runs_dir or (
                resolve_runtime(cwd).memory_dir / "link-swarm-runs"
            )
            try:
                result = gc_link_swarm_runs(
                    runs_dir, apply=args.apply, purge_now=args.purge_now,
                )
            except (FileNotFoundError, OSError, ValueError) as exc:
                print(str(exc), file=sys.stderr)
                return 1
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0

        if args.link_command in {"audit", "batch-plan"}:
            from .retrieval import (
                apply_link_gap_stubs,
                audit_link_gaps,
                link_audit_payload,
                materialize_link_swarm_run,
                plan_link_audit_batches,
            )

            if args.link_command == "batch-plan":
                semantic_status: dict[str, Any] = {}
                try:
                    runtime = resolve_runtime(cwd)
                    worker_skill_path = runtime.memory_dir / "skills" / "link_swarm.md"
                    worker_skill_text = worker_skill_path.read_text(encoding="utf-8")
                    worker_skill_source = worker_skill_path.relative_to(
                        runtime.workspace_root
                    ).as_posix()
                    gaps = audit_link_gaps(
                        cwd=cwd, entry_id=args.for_entry, session_date=args.audit_date,
                        top_k=None if args.top_k == 0 else args.top_k,
                        semantic_enabled=args.semantic, semantic_status=semantic_status,
                        semantic_candidate_threshold=args.semantic_cutoff,
                    )
                    plan = plan_link_audit_batches(
                        link_audit_payload(gaps, semantic_status),
                        context_window_tokens=args.context_window,
                        evidence_fraction=args.evidence_fraction,
                        minimum_score=args.minimum_score,
                        output_tokens_per_pair=args.output_tokens_per_pair,
                        worker_skill_text=worker_skill_text,
                        worker_skill_source=worker_skill_source,
                    )
                    if args.output_dir:
                        result = materialize_link_swarm_run(plan, args.output_dir, cwd=cwd)
                except (FileExistsError, LookupError, OSError, ValueError) as exc:
                    print(str(exc), file=sys.stderr)
                    return 1
                print(json.dumps(result if args.output_dir else plan, indent=2, ensure_ascii=False))
                return 0

            if args.apply and args.audit_date is None:
                print("link audit --apply requires --date YYYY-MM-DD", file=sys.stderr)
                return 2
            if args.apply and args.for_entry is not None:
                print("link audit --apply cannot be combined with --for", file=sys.stderr)
                return 2
            if args.json and args.apply:
                print("link audit --json cannot be combined with --apply", file=sys.stderr)
                return 2

            semantic_status: dict[str, Any] = {}
            try:
                gaps = audit_link_gaps(
                    cwd=cwd,
                    entry_id=args.for_entry,
                    session_date=args.audit_date,
                    top_k=args.top_k,
                    semantic_enabled=args.semantic,
                    semantic_status=semantic_status,
                )
            except LookupError as exc:
                print(str(exc), file=sys.stderr)
                return 1

            if args.json:
                # Judgment-ready: each candidate pair carries both ends' decision
                # bodies plus the link/no-link criteria, so a narrowing agent (or
                # a human) has a self-contained task. Mechanical recall in; the
                # decision-level judgment stays out of the network-free core.
                import json as _json

                print(_json.dumps(link_audit_payload(gaps, semantic_status), indent=2))
                return 0
            # Ranking provenance BEFORE the ranked list. The semantic term carries a
            # weight of 160 against unbounded-but-small idf sums, so it dominates
            # ordering; if the provider is missing the list is a different list and
            # nothing else on screen would say so.
            def _semantic_note() -> str:
                if not semantic_status.get("requested"):
                    return "Ranking: lexical only (--no-semantic); shared files + title terms."
                if semantic_status.get("active"):
                    return f"Ranking: lexical + semantic ({semantic_status.get('provider')})."
                if not semantic_status.get("fallback_reason"):
                    # Nothing to embed (empty corpus) - not a provider failure.
                    return "Ranking: lexical only - no entries to embed."
                return (
                    "Ranking: lexical only - semantic ranking was requested but is UNAVAILABLE "
                    f"({semantic_status.get('fallback_reason')}). Order differs from a semantic run."
                )

            if not gaps:
                print(_semantic_note())
                print("No unlinked structural neighbours found (no shared files or topics without an edge).")
                return 0
            print(_semantic_note())
            print("Entries sharing files/topics with no recorded edge - classify each and record in a link sidecar:")

            def _fmt_decisions(decisions: Any) -> str:
                return " · ".join(f"{d.ordinal} {d.name}".strip() for d in decisions)

            for gap in gaps:
                print()
                print(f"{gap.entry_id}  {gap.session_date}  {gap.title}")
                # Only when there is a choice to make: a single-decision entry is
                # addressable as :d1 already, so its decision line is just noise.
                if len(gap.decisions) >= 2:
                    print(f"    decisions: {_fmt_decisions(gap.decisions)}")
                for cand in gap.candidates:
                    evidence = []
                    # An ungated candidate leads with that fact. It carries no
                    # overlap a reader can check, so presenting it like a gated
                    # one would overstate it.
                    if cand.ungated:
                        evidence.append("UNGATED - semantic rank only")
                    # Chain position next: it changes what may be recorded at
                    # all, so it outranks any evidence weighing.
                    if cand.chain_position == "interior":
                        evidence.append(
                            f"INTERIOR chain member - related-only (refines taken by {cand.refines_taken_by}; "
                            f"chain lives at {cand.current_form})"
                        )
                    if cand.substitute_for:
                        evidence.append(f"substitute for replaced {cand.substitute_for}")
                    # Shared title terms lead: they are the strongest signal
                    # for a lifecycle predecessor, and the one a human can
                    # judge at a glance without opening either entry.
                    if cand.shared_title_terms:
                        evidence.append(f"terms: {', '.join(cand.shared_title_terms)}")
                    if cand.shared_files:
                        evidence.append(f"files: {', '.join(cand.shared_files)}")
                    if cand.shared_topics:
                        evidence.append(f"topics: {', '.join(cand.shared_topics)}")
                    # Cosine last: it is the term the reader cannot verify by eye, so
                    # it is labelled rather than folded invisibly into the score.
                    if cand.semantic_score is not None:
                        evidence.append(f"cosine: {cand.semantic_score:.2f}")
                    if cand.already_related:
                        evidence.append("already related — consider upgrading to a lifecycle edge")
                    print(f"    -> {cand.entry_id}  {cand.session_date}  {cand.title}")
                    print(f"       {' | '.join(evidence)}")
                    if len(cand.decisions) >= 2:
                        print(f"       decisions: {_fmt_decisions(cand.decisions)}  (target one as {cand.entry_id}:dN)")
            print()
            print("Litmus: retires it -> replaces; refines while it stays valid -> evolves; else related.")
            print("Where both ends carry decisions, narrow the edge to :dN - especially for ADR-promoted decisions.")
            if args.apply:
                try:
                    applied = apply_link_gap_stubs(gaps, session_date=args.audit_date, cwd=cwd)
                except (OSError, UnicodeDecodeError, ValueError) as exc:
                    print(f"Could not apply link-audit stubs: {exc}", file=sys.stderr)
                    return 1
                try:
                    display_path = applied.path.relative_to(resolve_runtime(cwd).workspace_root).as_posix()
                except ValueError:
                    display_path = applied.path.as_posix()
                if applied.changed:
                    print(f"Applied {len(applied.added_entry_ids)} inert stub(s) to {display_path}.")
                else:
                    print(f"No stubs added; every audited entry already has a sidecar block in {display_path}.")
            return 0
        if args.link_command == "show":
            from .core import commit_reference_ids
            from .retrieval import augment_chunks_with_link_sidecars
            from .semantic_cache import extract_memory_chunks

            # Union entry-YAML edges with late-authored link-sidecar edges so
            # `show` reflects the SAME effective graph that retrieval/MCP/Trace
            # read - otherwise a sidecar-recorded replaces/evolves/related is
            # invisible here (its computed inverse and importance too).
            entry_chunks = augment_chunks_with_link_sidecars(
                extract_memory_chunks(cwd, granularity="entry"), cwd=cwd
            )
            graph = build_related_entry_graph(cwd=cwd, chunks=entry_chunks)
            node = graph.get(args.entry_id)
            if node is None:
                print(f"entry_id {args.entry_id} not found", file=sys.stderr)
                return 1
            chunk = next((c for c in entry_chunks if c.entry_id == args.entry_id), None)
            commit_refs = commit_reference_ids(
                resolve_runtime(cwd).workspace_root,
                args.entry_id,
                chunk.commits if chunk else (),
            )
            print(f"{node.entry_id}  {node.title}")
            print(f"  outbound ({len(node.outbound)}): " + (", ".join(node.outbound) or "-"))
            print(f"  inbound  ({len(node.inbound)}): " + (", ".join(node.inbound) or "-"))
            print(f"  replaces ({len(node.replaces)}): " + (", ".join(node.replaces) or "-"))
            print(f"  replaced_by ({len(node.replaced_by)}): " + (", ".join(node.replaced_by) or "-"))
            print(f"  evolves ({len(node.evolves)}): " + (", ".join(node.evolves) or "-"))
            print(f"  evolved_by ({len(node.evolved_by)}): " + (", ".join(node.evolved_by) or "-"))
            continuity_blocks = chunk.continuity if chunk else ()
            rendered_continuity = ", ".join(
                f"{block.kind}: {block.from_ref}" + (f" -> {block.to_ref}" if block.to_ref else "")
                for block in continuity_blocks
            )
            print(f"  continuity ({len(continuity_blocks)}): " + (rendered_continuity or "-"))
            print(f"  inbound_relation_count: {len(node.inbound)}")
            print(f"  importance_score: {node.importance_score:.2f}" + ("  (replaced: dampened)" if node.replaced_by else ""))
            print(f"  commit_reference_count: {len(commit_refs)}")
            return 0
        if args.link_command == "commits":
            from .core import find_trailer_commits
            from .semantic_cache import extract_memory_chunks

            chunk = next(
                (c for c in extract_memory_chunks(cwd, granularity="entry") if c.entry_id == args.entry_id),
                None,
            )
            if chunk is None:
                print(f"entry_id {args.entry_id} not found", file=sys.stderr)
                return 1
            print(f"{chunk.entry_id}  {chunk.title}")
            print(f"  commits field ({len(chunk.commits)}): " + (", ".join(chunk.commits) or "-"))
            trailer_hits = find_trailer_commits(resolve_runtime(cwd).workspace_root, args.entry_id)
            if trailer_hits is None:
                print("  trailer scan: skipped (not a git repository or git unavailable)")
            else:
                print(f"  trailer scan ({len(trailer_hits)}):" + ("" if trailer_hits else " -"))
                for line in trailer_hits:
                    print(f"    {line}")
            return 0

    if args.command == "compact":
        result = compact_sessions(days=args.days, scan_all=args.scan_all)

        if not result.sessions_scanned:
            print("No session files found.")
            return 0

        lines: list[str] = []
        lines.append("# Compact Summary")
        lines.append("")
        lines.append(f"Generated: {date.today().isoformat()}")
        lines.append(f"Sessions scanned: {', '.join(result.sessions_scanned)}")
        lines.append("")
        lines.append("## Session Activity")

        for date_str, heading_list in result.headings.items():
            lines.append("")
            lines.append(f"### {date_str}")
            for heading in heading_list:
                lines.append(f"- {heading}")

        lines.append("")
        lines.append("## All Entries")
        lines.append("")
        lines.append(result.full_text)

        output = "\n".join(lines)

        if args.output:
            write_text_file(Path(args.output), output)
            print(f"Summary written to {args.output}")
        else:
            print(output)
        return 0

    if args.command == "doctor":
        result = doctor()
        if result.control_plane_ok:
            print("Memory Seed reusable control plane looks healthy.")
        else:
            print("Memory Seed reusable control plane has issues.")
        if result.bootstrap_complete:
            print("Memory Seed bootstrap is complete.")
        else:
            print("Memory Seed bootstrap is incomplete.")
        for warning in result.warnings:
            print(f"Warning: {warning}")
        if result.ok:
            return 0
        for missing in result.missing:
            print(f"Missing: {missing}")
        for mismatch in result.version_mismatches:
            print(
                "Version mismatch: "
                f"{mismatch['file']} expected {mismatch['expected']} "
                f"but found {mismatch['actual']}"
            )
        for missing in result.bootstrap_missing:
            print(f"Bootstrap incomplete: {missing}")
        return 1

    if args.command == "agents":
        target = Path(".").resolve()
        if args.agents_command == "list":
            agent_selection = selected_agents(target)
            print("Selected agents: " + _format_agents(agent_selection))
            print("Ignored agents: " + _format_agents(set(KNOWN_AGENTS) - agent_selection))
            if read_project_agents(target) is None:
                print("(no .memory-seed/project.yaml - all agents active by default)")
            return 0
        if args.agents_command == "add":
            try:
                res = add_agent(agent=args.agent)
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            print(res["message"])
            for created in res["created"]:
                print(f"Installed: {created}")
            return 0
        if args.agents_command == "remove":
            try:
                res = remove_agent(agent=args.agent)
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            print(res["message"])
            for removed in res.get("removed", []):
                print(f"Removed: {removed}")
            for backup in res.get("backed_up", []):
                print(f"Backed up: {backup}")
            if res.get("warning"):
                print(f"Warning: {res['warning']}")
            return 0

    if args.command == "skills":
        target = Path(".").resolve()
        if args.skills_command == "list":
            _print_skill_status(skill_status(target))
            return 0
        if args.skills_command == "ignored":
            status = skill_status(target)
            if not status.ignored:
                print("No ignored optional skills.")
                return 0
            print("Ignored optional skills:")
            for skill in status.ignored:
                profiles = [name for name, skills in status.profiles.items() if skill in skills]
                suffix = f" (profiles: {', '.join(profiles)})" if profiles else ""
                print(f"  - {skill}{suffix}: {status.descriptions.get(skill, '')}")
            return 0
        if args.skills_command == "add":
            try:
                res = add_skill(target, name=args.name)
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            print(res["message"])
            for created in res.get("created", []):
                print(f"Installed: {created}")
            return 0
        if args.skills_command == "remove":
            try:
                res = remove_skill(target, skill=args.skill)
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            print(res["message"])
            for removed in res.get("removed", []):
                print(f"Removed: {removed}")
            for backup in res.get("backed_up", []):
                print(f"Backed up: {backup}")
            return 0

    if args.command == "init":
        target_root = Path(".").resolve()
        isatty = sys.stdin.isatty() and not args.dry_run
        prompt_response = None
        if not args.agents and isatty and not args.no_agent_prompt:
            print("Which agent integrations should be installed? (comma-separated)")
            for slug in KNOWN_AGENTS:
                print(f"  - {slug}")
            print(
                "Always installed: AGENTS.md, the .memory-seed/ runtime, and .agents/ "
                "personas. 'copilot' covers both the CLI and VS Code."
            )
            print("Recommended default: all. Enter 'none' for shared runtime only.")
            try:
                prompt_response = input("agents [all]> ")
            except EOFError:
                prompt_response = None
        try:
            agents = resolve_agents(args.agents, isatty=isatty, prompt_response=prompt_response)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        skill_profiles = _split_csv(args.profile)
        skills = _split_csv(args.skills)
        exclude_skills = _split_csv(args.exclude_skills)
        if (
            isatty
            and not args.no_skill_prompt
            and not args.manual_skills
            and not args.all_skills
            and not skill_profiles
            and not skills
            and not exclude_skills
        ):
            recommended = "coding,planning"
            print("Which optional skill profiles should be installed? (comma-separated)")
            for name, profile_skills in skill_status(Path(".").resolve()).profiles.items():
                print(f"  - {name}: {', '.join(profile_skills)}")
            print(f"Recommended default: {recommended}. Enter 'none' for core skills only.")
            try:
                response = input(f"profiles [{recommended}]> ")
            except EOFError:
                response = ""
            if response.strip().lower() == "none":
                skill_profiles = set()
            elif response.strip():
                skill_profiles = _split_csv(response)
            else:
                skill_profiles = _split_csv(recommended)
        if args.manual_skills and isatty and not args.skills:
            print("Optional skills available. Enter skill filenames to install, comma-separated; Enter = none.")
            for skill in skill_status(Path(".").resolve()).available_optional:
                print(f"  - {skill}")
            try:
                skills = _split_csv(input("skills> "))
            except EOFError:
                skills = set()
        try:
            integration_mode, should_write_integration_mode = _resolve_init_integration_mode(
                target_root,
                requested_mode=args.integration_mode,
                isatty=isatty,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        try:
            result = init_project(
                cwd=target_root,
                dry_run=args.dry_run,
                force=args.force,
                agents=agents,
                skill_profiles=skill_profiles,
                skills=skills,
                exclude_skills=exclude_skills,
                all_skills=args.all_skills,
            )
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            print("Use --force to backup and replace existing seed files.", file=sys.stderr)
            return 1
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1

        if args.dry_run:
            for planned in result.planned:
                print(f"Would copy: {planned}")
            if should_write_integration_mode:
                print(f"Would set integration mode: {integration_mode}")
            print("No files changed.")
            return 0

        if should_write_integration_mode:
            try:
                write_integration_mode(target_root, integration_mode)
            except (OSError, ValueError) as exc:
                print(str(exc), file=sys.stderr)
                return 1

        for created in result.created:
            print(f"Copied: {created}")
        for backup in result.backed_up:
            print(f"Backed up: {backup}")
        for archived in result.archived:
            print(f"Archived: {archived}")
        if result.backed_up:
            print("Added .memory-seed/backups/ to .gitignore to reduce accidental backup leaks.")
        agent_selection = selected_agents(target_root)
        ignored_agents = set(KNOWN_AGENTS) - agent_selection
        print("Installed agents: " + _format_agents(agent_selection))
        print("Ignored agents: " + _format_agents(ignored_agents))
        print("Always installed: AGENTS.md, .memory-seed/, and .agents/ personas.")
        status = skill_status(target_root)
        print("Installed core skills: " + ", ".join(status.core))
        if status.installed_optional:
            print("Selected optional skills: " + ", ".join(status.installed_optional))
        else:
            print("Selected optional skills: (none)")
        if status.ignored:
            print("Ignored optional skills: " + ", ".join(status.ignored))
        print(f"Integration mode: {integration_mode}")
        print("Next: open AGENTS.md and follow nearest-runtime mode.")
        return 0

    if args.command == "hooks":
        if args.hooks_command == "status":
            from .core import git_hook_status

            status = git_hook_status(Path(".").resolve())
            payload = {
                "is_git_repo": status.is_git_repo,
                "state": status.state,
                "message": status.message,
                "hook_path": status.hook_path,
                "managed": status.managed,
                "current": status.current,
                "repairable": status.repairable,
            }
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                print(f"state: {status.state}")
                print(status.message)
                if status.hook_path:
                    print(f"path: {status.hook_path}")
                if status.repairable:
                    print("Next: run `memory-seed hooks repair`.")
            return 0 if status.state in {"current", "no-git"} else 1

        if args.hooks_command in {"install", "repair"}:
            from .core import install_git_hooks

            actions = install_git_hooks(Path(".").resolve())
            if not actions:
                print("No git repository found - nothing installed.")
                return 0
            for action in actions:
                print(action)
            return 0

    if args.command == "provenance":
        try:
            runtime = _read_json_object(args.runtime_file, label="runtime") if args.runtime_file else None
            if args.provenance_command == "bind":
                payload = provenance_surface(
                    "bind", cwd=Path(".").resolve(),
                    binding=_read_json_object(args.binding_file, label="binding"), owner=runtime, apply=args.apply,
                )
            elif args.provenance_command == "show":
                payload = provenance_surface(
                    "show", cwd=Path(".").resolve(), decision_ref=args.decision_ref,
                    owner=runtime, context_lines=args.context_lines,
                )
            else:
                payload = provenance_surface("check", cwd=Path(".").resolve(), owner=runtime)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"provenance {args.provenance_command} refused: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        elif args.provenance_command == "bind":
            print(("Appended" if payload["written"] else "Would append") + f" {payload['binding']['binding_id']} to {payload['path']}")
        elif args.provenance_command == "show":
            print(f"{payload['decision_ref'] if 'decision_ref' in payload else payload['decision']['ref']}: {len(payload['projections'])} binding(s); code available: {payload['code_available']}")
            if payload["decision"]["reason"]:
                print(f"Reason: {payload['decision']['reason']}")
        else:
            print("Provenance references OK" if payload["ok"] else "Provenance references need attention")
            for row in payload["reference_audit"]:
                print(f"  {row['binding_id']}: {row.get('evidence_state', 'available')}")
        return 0 if payload["ok"] else 1

    if args.command == "esr":
        from .esr import esr_report, format_esr_report

        report = esr_report(cwd=Path(".").resolve(), session_date=args.date)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(format_esr_report(report))
        # Preflight, not a gate: only hard integrity failures are fatal -
        # link gaps, stale worktrees, and topic warnings are report lines.
        return 0 if report.integrity_ok else 1

    if args.command == "situate":
        from .situate import format_situate_report, situate_report

        report = situate_report(cwd=Path(".").resolve())
        if args.json:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(format_situate_report(report))
        return 0

    if args.command == "ranking-ab":
        from .ranking_ab import ab_result_to_dict, format_ab_report, run_ab

        try:
            result = run_ab(
                args.signal,
                cwd=Path(".").resolve(),
                queries=args.queries,
            )
        except KeyError as exc:
            print(exc.args[0], file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(ab_result_to_dict(result), indent=2, ensure_ascii=False))
        else:
            print(format_ab_report(result))
        return 0 if result.passed else 1

    if args.command == "update":
        result = update_project(dry_run=args.dry_run)

        if args.dry_run:
            for planned in result.planned:
                print(f"Would update: {planned}")
            print("No files changed.")
            return 0

        for created in result.created:
            print(f"Updated: {created}")
        for backup in result.backed_up:
            print(f"Backed up: {backup}")
        for archived in result.archived:
            print(f"Archived: {archived}")
        if result.backed_up:
            print("Added .memory-seed/backups/ to .gitignore to reduce accidental backup leaks.")
        if result.changed:
            print("Updated missing or stale seed files. Existing .memory-seed runtime files were preserved.")
        else:
            print("Control-plane files are already current. No files changed.")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
