from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import date
from pathlib import Path

from . import processes as process_tools
from .core import (
    KNOWN_AGENTS,
    add_agent,
    add_skill,
    branch_status,
    check_session_links,
    clear_local_user,
    compact_sessions,
    doctor,
    generate_session_entry_id,
    get_version,
    init_project,
    migrate_session_month_layout,
    migrate_session_layout,
    read_local_user,
    read_project_agents,
    remove_agent,
    remove_skill,
    resolve_agents,
    selected_agents,
    session_fuse,
    session_merge_branch,
    session_target,
    skill_status,
    update_project,
    write_local_user,
)
from .text_files import (
    encoding_issue_to_dict,
    repair_text_encoding,
    scan_implicit_text_io,
    scan_text_encoding,
    write_text_file,
)


def _print_help(parser: argparse.ArgumentParser) -> None:
    print(parser.format_help().rstrip())
    print()
    print("Keeping Memory Seed current:")
    print("  Two separate things stay current, and they are not the same step.")
    print(
        "  1. Upgrade the package (code + bundled seed templates):\n"
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
    parser = argparse.ArgumentParser(prog="memory-seed")
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
    session_merge_parser = session_sub.add_parser(
        "merge-branch",
        help="merge a task branch and fuse its branch-local session entries in one step",
    )
    session_merge_parser.add_argument("--branch", required=True, help="task branch to merge into the current branch")
    session_merge_parser.add_argument("--dry-run", action="store_true", help="preview the fuse plan without merging")
    session_append_parser = session_sub.add_parser(
        "append",
        help="append a session entry with structure enforced (id, chronology, refs, topics); body from --body-file or stdin",
    )
    session_append_parser.add_argument("--title", required=True, help="entry title (text after 'YYYY-MM-DD HH:MM - ')")
    session_append_parser.add_argument("--user-initials", required=True, help="user_initials field, e.g. JNL")
    session_append_parser.add_argument("--agent-type", required=True, help="agent_type field, e.g. claude")
    session_append_parser.add_argument("--agent-name", default=None, help="agent_name field (default: null)")
    session_append_parser.add_argument("--topics", default="", help="comma-separated controlled-vocabulary slugs or aliases")
    session_append_parser.add_argument("--related", default="", help="comma-separated related_entries ids")
    session_append_parser.add_argument("--supersedes", default="", help="comma-separated ids this entry retires")
    session_append_parser.add_argument("--evolves", default="", help="comma-separated ids this entry refines (they stay valid)")
    session_append_parser.add_argument("--project-path", default=".", help="project_path field (default: .)")
    session_append_parser.add_argument("--subproject-path", default=None, help="subproject_path field (default: null)")
    session_append_parser.add_argument("--branch", default=None, help="branch field (default: auto-captured from git)")
    session_append_parser.add_argument("--no-branch", action="store_true", help="omit the branch field entirely")
    session_append_parser.add_argument("--timestamp", default=None, help="override heading timestamp 'YYYY-MM-DD HH:MM' (default: now)")
    session_append_parser.add_argument("--user", default=None, help="override the active user slug")
    session_append_parser.add_argument("--body-file", default=None, help="file containing the entry body (default: read stdin)")
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

    branch_parser = subparsers.add_parser("branch", help="inspect Git branch/worktree posture")
    branch_sub = branch_parser.add_subparsers(dest="branch_command", required=True)
    branch_status_parser = branch_sub.add_parser(
        "status",
        help="show read-only branch guardrails for feature work",
    )
    branch_status_parser.add_argument("--json", action="store_true", help="emit machine-readable status")

    topics_parser = subparsers.add_parser("topics", help="inspect and validate the controlled topic vocabulary")
    topics_sub = topics_parser.add_subparsers(dest="topics_command", required=True)
    topics_sub.add_parser("list", help="show the topics defined in .memory-seed/topics.yaml")
    topics_sub.add_parser(
        "check",
        help="validate vocabulary shape and entry topics: usage (exit 1 on any error)",
    )

    links_parser = subparsers.add_parser("links", help="validate session-memory integrity")
    links_sub = links_parser.add_subparsers(dest="links_command", required=True)
    links_sub.add_parser(
        "check",
        help="report duplicate/dangling IDs and per-user frontmatter problems (exit 1 on any issue)",
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
        help="find entries that share files/topics but have no recorded edge (read-only)",
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

    esr_parser = subparsers.add_parser(
        "esr",
        help="end-of-session mechanical preflight: every deterministic check in one read-only report",
    )
    esr_parser.add_argument("--date", default=None, help="session date for the link-gap sweep (default: today)")
    esr_parser.add_argument("--json", action="store_true", help="emit the report as JSON")

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

    lense_parser = subparsers.add_parser("lense", help="[deprecated] use the 'memory-trace' command")
    lense_parser.add_argument("--cwd", default=".", help="project/runtime path to inspect (default: current directory)")
    lense_parser.add_argument("--host", default="127.0.0.1", help="host to bind (default: 127.0.0.1)")
    lense_parser.add_argument("--port", type=int, default=0, help="port to bind; 0 chooses a free port")
    lense_parser.add_argument("--no-open", action="store_true", help="do not open a browser")
    lense_parser.add_argument("--rebuild-cache", action="store_true", help="rebuild the SQLite cache before serving")

    subparsers.add_parser("doctor", help="check Memory Seed control-plane files")
    subparsers.add_parser("version", help="print Memory Seed control-plane version")

    args = parser.parse_args(argv)

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    if args.command in (None, "help"):
        _print_help(parser)
        return 0

    if args.command in process_tools.PACKAGE_COMMANDS:
        return process_tools.run_package_process_command("memory-seed", args)

    if args.command == "version":
        print(get_version())
        return 0

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
            )
            if result.issues:
                print("Session fuse blocked:", file=sys.stderr)
                for issue in result.issues:
                    print(f"  - {issue}", file=sys.stderr)
                return 1
            if not (result.planned_entries or result.planned_sidecars or result.removed_sources):
                print("No branch session entries or sidecars need fusing.")
                return 0
            entry_verb = "Imported" if args.apply else "Would import"
            diagram_verb = "Imported diagram" if args.apply else "Would import diagram"
            remove_verb = "Removed source" if args.apply else "Would remove source"
            for planned in result.planned_entries:
                print(f"{entry_verb}: {planned}")
            for planned in result.planned_sidecars:
                print(f"{diagram_verb}: {planned}")
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
            )
            if result.issues:
                print("Session merge-branch blocked:", file=sys.stderr)
                for issue in result.issues:
                    print(f"  - {issue}", file=sys.stderr)
                if result.merge_in_progress:
                    print(
                        "The git merge was left in progress; resolve and commit manually, or git merge --abort.",
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
            remove_verb = "Would remove source" if args.dry_run else "Removed source"
            for planned in result.planned_entries:
                print(f"{entry_verb}: {planned}")
            for planned in result.planned_sidecars:
                print(f"{diagram_verb}: {planned}")
            for source in result.removed_sources:
                print(f"{remove_verb}: {source}")
            if result.already_present:
                for entry_id in sorted(set(result.already_present)):
                    if entry_id:
                        print(f"Already present: {entry_id}")
            if args.dry_run:
                print("Dry run - no merge performed. Rerun without --dry-run to merge and fuse.")
            elif result.committed:
                print("Merge committed.")
                if result.stamped_entries:
                    print(f"Stamped {len(result.stamped_entries)} Memory-Entry trailer(s) on the merge commit.")
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
                print("Entry body is empty (pass --body-file or pipe the D/R/A/F/T prose on stdin).", file=sys.stderr)
                return 1

            def _csv(raw: str) -> tuple[str, ...]:
                return tuple(item.strip() for item in raw.split(",") if item.strip())

            result = session_append_entry(
                cwd=Path(".").resolve(),
                title=args.title,
                body=body,
                user_initials=args.user_initials,
                agent_type=args.agent_type,
                agent_name=args.agent_name,
                topics=_csv(args.topics),
                related_entries=_csv(args.related),
                supersedes=_csv(args.supersedes),
                evolves=_csv(args.evolves),
                project_path=args.project_path,
                subproject_path=args.subproject_path,
                branch=args.branch,
                auto_branch=not args.no_branch,
                timestamp=args.timestamp,
                explicit_user=args.user,
            )
            if not result.ok:
                print("Append refused:", file=sys.stderr)
                for issue in result.issues:
                    print(f"  - {issue}", file=sys.stderr)
                return 1
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
            if result.ok:
                print(f"Session memory integrity OK ({result.files_checked} file(s) checked).")
                return 0
            print(
                f"Session memory integrity: {len(result.issues)} issue(s) across "
                f"{result.files_checked} file(s):",
                file=sys.stderr,
            )
            for issue in result.issues:
                print(f"  [{issue.kind}] {issue.file}: {issue.detail}", file=sys.stderr)
            return 1

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
        from .topics import check_topics, load_topic_index

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
            print(
                f"Topics check: {result.topics_defined} topics defined, "
                f"{result.entries_checked} entries with topics checked."
            )
            if result.ok:
                print("Topic vocabulary OK.")
                return 0
            print("Topic vocabulary has errors.", file=sys.stderr)
            return 1

    if args.command == "link":
        from .semantic_cache import build_related_entry_graph, suggest_related_entries

        cwd = Path(".").resolve()
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
            for item in ranked:
                chunk = item.chunk
                print(f"  {chunk.entry_id}  {chunk.session_date}  {chunk.title}  (score {item.final_score:.3f})")
                if item.shared_files:
                    print(f"    shares: {', '.join(item.shared_files)}")
            print()
            print("Paste into the entry's YAML:")
            print("related_entries:")
            for item in ranked:
                print(f"  - {item.chunk.entry_id}")
            return 0
        if args.link_command == "audit":
            from .retrieval import audit_link_gaps

            try:
                gaps = audit_link_gaps(
                    cwd=cwd, entry_id=args.for_entry, session_date=args.audit_date, top_k=args.top_k
                )
            except LookupError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            if not gaps:
                print("No unlinked structural neighbours found (no shared files or topics without an edge).")
                return 0
            print("Entries sharing files/topics with no recorded edge - classify each and record in a link sidecar:")
            for gap in gaps:
                print()
                print(f"{gap.entry_id}  {gap.session_date}  {gap.title}")
                for cand in gap.candidates:
                    evidence = []
                    if cand.shared_files:
                        evidence.append(f"files: {', '.join(cand.shared_files)}")
                    if cand.shared_topics:
                        evidence.append(f"topics: {', '.join(cand.shared_topics)}")
                    if cand.already_related:
                        evidence.append("already related — consider upgrading to a lifecycle edge")
                    print(f"    -> {cand.entry_id}  {cand.session_date}  {cand.title}")
                    print(f"       {' | '.join(evidence)}")
            print()
            print("Litmus: retires it -> supersedes; refines while it stays valid -> evolves; else related.")
            return 0
        if args.link_command == "show":
            from .core import commit_reference_ids, resolve_runtime
            from .semantic_cache import extract_memory_chunks

            entry_chunks = extract_memory_chunks(cwd, granularity="entry")
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
            print(f"  supersedes ({len(node.supersedes)}): " + (", ".join(node.supersedes) or "-"))
            print(f"  superseded_by ({len(node.superseded_by)}): " + (", ".join(node.superseded_by) or "-"))
            print(f"  evolves ({len(node.evolves)}): " + (", ".join(node.evolves) or "-"))
            print(f"  evolved_by ({len(node.evolved_by)}): " + (", ".join(node.evolved_by) or "-"))
            continuity_blocks = chunk.continuity if chunk else ()
            rendered_continuity = ", ".join(
                f"{block.kind}: {block.from_ref}" + (f" -> {block.to_ref}" if block.to_ref else "")
                for block in continuity_blocks
            )
            print(f"  continuity ({len(continuity_blocks)}): " + (rendered_continuity or "-"))
            print(f"  inbound_relation_count: {len(node.inbound)}")
            print(f"  importance_score: {node.importance_score:.2f}" + ("  (superseded: dampened)" if node.superseded_by else ""))
            print(f"  commit_reference_count: {len(commit_refs)}")
            return 0
        if args.link_command == "commits":
            from .core import find_trailer_commits, resolve_runtime
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

    if args.command == "lense":
        # Deprecated shim: the review UI now lives behind the `trace` extra and
        # the `memory-trace` command. Plain core installs ship no web stack.
        try:
            from memory_trace.lense import run_server
        except ModuleNotFoundError:
            print(
                "Memory Lense has moved to the Memory Trace command.\n"
                "  Install:  pip install \"memory-seed[trace]\"\n"
                "  Run:      memory-trace",
                file=sys.stderr,
            )
            return 1
        print(
            "note: 'memory-seed lense' is deprecated; run the 'memory-trace' command instead.",
            file=sys.stderr,
        )
        return run_server(args)

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
            result = init_project(
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
            print("No files changed.")
            return 0

        for created in result.created:
            print(f"Copied: {created}")
        for backup in result.backed_up:
            print(f"Backed up: {backup}")
        for archived in result.archived:
            print(f"Archived: {archived}")
        if result.backed_up:
            print("Added .memory-seed/backups/ to .gitignore to reduce accidental backup leaks.")
        agent_selection = selected_agents(Path(".").resolve())
        ignored_agents = set(KNOWN_AGENTS) - agent_selection
        print("Installed agents: " + _format_agents(agent_selection))
        print("Ignored agents: " + _format_agents(ignored_agents))
        print("Always installed: AGENTS.md, .memory-seed/, and .agents/ personas.")
        status = skill_status(Path(".").resolve())
        print("Installed core skills: " + ", ".join(status.core))
        if status.installed_optional:
            print("Selected optional skills: " + ", ".join(status.installed_optional))
        else:
            print("Selected optional skills: (none)")
        if status.ignored:
            print("Ignored optional skills: " + ", ".join(status.ignored))
        print("Next: open AGENTS.md and follow nearest-runtime mode.")
        return 0

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
