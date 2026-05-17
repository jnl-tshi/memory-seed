from __future__ import annotations

import argparse
import sys

from .core import doctor, get_version, init_project, update_project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="memory-seed")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="copy Memory Seed into this project")
    init_parser.add_argument("--dry-run", action="store_true", help="show planned files without writing")
    init_parser.add_argument("--force", action="store_true", help="backup and overwrite existing seed files")

    update_parser = subparsers.add_parser("update", help="update reusable control-plane files")
    update_parser.add_argument("--dry-run", action="store_true", help="show planned files without writing")

    subparsers.add_parser("doctor", help="check Memory Seed control-plane files")
    subparsers.add_parser("version", help="print Memory Seed control-plane version")

    args = parser.parse_args(argv)

    if args.command == "version":
        print(get_version())
        return 0

    if args.command == "doctor":
        result = doctor()
        if result.ok:
            print("Memory Seed control plane looks healthy.")
            return 0
        for missing in result.missing:
            print(f"Missing: {missing}")
        for mismatch in result.version_mismatches:
            print(
                "Version mismatch: "
                f"{mismatch['file']} expected {mismatch['expected']} "
                f"but found {mismatch['actual']}"
            )
        return 1

    if args.command == "init":
        try:
            result = init_project(dry_run=args.dry_run, force=args.force)
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            print("Use --force to backup and replace existing seed files.", file=sys.stderr)
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
        if result.backed_up:
            print("Added .AGENTS/backups/ to .gitignore to reduce accidental backup leaks.")
        print("Next: open AGENTS.md and follow bootstrap mode.")
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
        if result.backed_up:
            print("Added .AGENTS/backups/ to .gitignore to reduce accidental backup leaks.")
        if result.changed:
            print("Project memory files were not changed.")
        else:
            print("Control-plane files are already current. No files changed.")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
