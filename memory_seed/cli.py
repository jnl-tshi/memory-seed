from __future__ import annotations

import argparse
import io
import sys
from datetime import date
from pathlib import Path

from .core import (
    KNOWN_AGENTS,
    add_agent,
    add_skill,
    check_session_links,
    clear_local_user,
    compact_sessions,
    doctor,
    get_version,
    init_project,
    migrate_session_layout,
    read_local_user,
    read_project_agents,
    remove_agent,
    remove_skill,
    resolve_agents,
    selected_agents,
    session_target,
    skill_status,
    update_project,
    write_local_user,
)
from .text_files import write_text_file


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
            + "); default: all. Non-selected agents' files are skipped."
        ),
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

    agents_parser = subparsers.add_parser("agents", help="manage which agents are installed")
    agents_sub = agents_parser.add_subparsers(dest="agents_command", required=True)
    agents_sub.add_parser("list", help="show the selected agents")
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

    session_parser = subparsers.add_parser("session", help="inspect session targets")
    session_sub = session_parser.add_subparsers(dest="session_command", required=True)
    session_target_parser = session_sub.add_parser("target", help="print the active session log target")
    session_target_parser.add_argument("--date", default=None, help="target date (YYYY-MM-DD); default: today")
    session_target_parser.add_argument("--user", default=None, help="override the active user slug")
    session_target_parser.add_argument("--create", action="store_true", help="create the target file if needed")

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
        help="split legacy flat session files into per-day/per-user files",
    )
    migrate_sessions.add_argument("--dry-run", action="store_true", help="show planned migrations without writing")

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

    lense_parser = subparsers.add_parser("lense", help="[deprecated] moved to the 'memory-trace' package/command")
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
            print()
            print("Paste into the entry's YAML:")
            print("related_entries:")
            for item in ranked:
                print(f"  - {item.chunk.entry_id}")
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
        # Deprecated shim: the review UI moved to the standalone `memory-trace`
        # package/command. This delegates when memory-trace is installed and
        # otherwise points the user at it - core ships no web stack of its own.
        try:
            from memory_trace.lense import run_server
        except ModuleNotFoundError:
            print(
                "Memory Lense has moved to the 'memory-trace' package.\n"
                "  Install:  pip install memory-trace\n"
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
            print("Selected agents: " + ", ".join(sorted(selected_agents(target))))
            if read_project_agents(target) is None:
                print("(no .memory-seed/project.yaml — all agents active by default)")
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
        if not args.agents and isatty:
            print("Which agents will use this project? (comma-separated; Enter = all)")
            for slug in KNOWN_AGENTS:
                print(f"  - {slug}")
            print(
                "Always installed: AGENTS.md, the .memory-seed/ runtime, and .agents/ "
                "personas. 'copilot' covers both the CLI and VS Code."
            )
            try:
                prompt_response = input("agents> ")
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
