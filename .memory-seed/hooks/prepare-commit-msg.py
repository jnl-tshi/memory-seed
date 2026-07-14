#!/usr/bin/env python3
"""Git prepare-commit-msg hook: stamp Memory-Entry trailers automatically.

`session merge-branch` stamps one `Memory-Entry: <entry_id>` trailer per
fused session entry, but ordinary commits that carry entries only get the
trailer if the author remembers to write it - and a forgotten trailer
silently downgrades Memory Trace's commit-accurate merge rendering to a
positional estimate. This hook makes the entry->commit join true by
construction: it scans the staged diff for newly added `entry_id:` lines
under the session tree and appends one trailer per new id, deduplicated
against trailers already present in the message.

Standalone by design (no memory_seed import): git invokes it through the
`.git/hooks/prepare-commit-msg` shim that `memory-seed init` (or
`memory-seed hooks install`) writes. It NEVER fails the commit - any error
exits 0 so a broken hook cannot block work.
"""

import re
import subprocess
import sys

# Both id generations plus the wider lowercase ids other agents author
# (mirrors memory_seed.core._TRAILER_ENTRY_ID_RE; kept in sync by the
# hook-contract test in the control-plane repo).
_ENTRY_ID_RE = re.compile(r"^\+entry_id:\s*((?:ms-[0-9a-f]{8}|mse_[0-9a-z]{8,32}))\s*$")
_TRAILER_RE = re.compile(r"^Memory-Entry:\s*(\S+)\s*$", re.MULTILINE)


def staged_entry_ids() -> list[str]:
    # Restricted to session trees (root and nested subproject runtimes): the
    # control-plane repo's own test fixtures also contain entry_id: lines and
    # must never be stamped.
    proc = subprocess.run(
        [
            "git", "diff", "--cached", "-U0", "--",
            ".memory-seed/sessions",
            ":(glob)**/.memory-seed/sessions/**",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        return []
    ids: list[str] = []
    for line in proc.stdout.splitlines():
        match = _ENTRY_ID_RE.match(line)
        if match and match.group(1) not in ids:
            ids.append(match.group(1))
    return ids


def main() -> int:
    if len(sys.argv) < 2:
        return 0
    msg_path = sys.argv[1]
    ids = staged_entry_ids()
    if not ids:
        return 0
    try:
        with open(msg_path, "r", encoding="utf-8") as handle:
            message = handle.read()
    except OSError:
        return 0
    existing = set(_TRAILER_RE.findall(message))
    missing = [entry_id for entry_id in ids if entry_id not in existing]
    if not missing:
        return 0
    trailer_block = "\n".join(f"Memory-Entry: {entry_id}" for entry_id in missing)
    body = message.rstrip("\n")
    if not body:
        message = trailer_block + "\n"
    else:
        last_line = body.rsplit("\n", 1)[-1]
        # Append CONTIGUOUSLY when the message already ends in a trailer line: a
        # blank line would split the trailer block, and git's trailer parser
        # (and Memory Trace's commit-accurate merge geometry) reads ONLY the
        # final contiguous block - silently dropping every earlier Memory-Entry,
        # including a merge's own branch entry. Separate with a blank line only
        # when the message ends in prose, so the trailers still form a block.
        joiner = "\n" if re.match(r"[A-Za-z][A-Za-z0-9-]*: ", last_line) else "\n\n"
        message = body + joiner + trailer_block + "\n"
    try:
        with open(msg_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(message)
    except OSError:
        return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Never block a commit on hook failure.
        sys.exit(0)
