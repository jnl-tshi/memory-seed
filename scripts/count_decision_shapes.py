"""Classify every session entry by the shape of its decision section.

This is the ONE agreed classifier behind the corpus table in
``docs/3_Spec/draft/adr-lifecycle-sidecar-contract.md``. That table's numbers
were authored by hand on 2026-07-20 and a later recount disagreed with them
(see open question 4 in ``decision-level-link-sidecar-refs.md``), so the fix is
not a better hand count but a script anyone can re-run.

Buckets are mutually exclusive and follow the ADR's identity table, resolved in
the same precedence ``_entry_decision_ordinals`` uses so the counts and the
shipped addressability agree by construction rather than by coincidence:

  numbered     >=1 '#### Dn - name' heading.
  singular     no numbered heading, but a singular '### Decision' heading.
  inline       no heading of either kind, but '- D1:'-style numbered bullets
               (the legacy '### Decisions' + inline-bullet shape).
  none         no decision section at all - not an ADR source.

Addressability is reported separately and deliberately NOT derived from the
buckets: it is whatever ``_entry_decision_ordinals`` actually returns, which is
what a decision ref is validated against. The two can legitimately differ - the
inline bucket has no ordinals under the current implementation - and printing
both is how that gap stays visible instead of being averaged away.

Entry boundaries and body extraction come from ``_walk_entry_bodies``, the same
splitter ``links check`` uses, so "how many entries are there" cannot drift
between this script and the validator.

That splitter is also *why* the earlier hand counts disagreed, so the script
prints the rival total too. ``_ENTRY_HEADING_RE`` requires a ``HH:MM`` stamp,
while the semantic-cache entry extractor accepts a date-only ``## YYYY-MM-DD -
title``. The corpus's earliest entries (May 2026, before the timestamp
convention) are date-only, so the two splitters legitimately count different
populations over identical files. Reporting one number without saying which
splitter produced it is what made the original table unreproducible.

Usage:  python scripts/count_decision_shapes.py [repo_root]
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import re  # noqa: E402

from memory_seed.core import (  # noqa: E402
    _ENTRY_HEADING_RE,
    _INLINE_NUMBERED_DECISION_RE,
    _NUMBERED_DECISION_HEADING_RE,
    _SINGULAR_DECISION_HEADING_RE,
    _entry_decision_ordinals,
    _walk_entry_bodies,
    iter_session_documents,
    resolve_runtime,
)


# Any '## YYYY-MM-DD' heading, stamped or not - the looser boundary the
# semantic-cache entry extractor accepts.
_DATE_HEADING_RE = re.compile(r"^##\s+\d{4}-\d{2}-\d{2}")


def classify(body: str) -> str:
    lines = body.splitlines()
    if any(_NUMBERED_DECISION_HEADING_RE.match(line) for line in lines):
        return "numbered"
    if any(_SINGULAR_DECISION_HEADING_RE.match(line) for line in lines):
        return "singular"
    if any(_INLINE_NUMBERED_DECISION_RE.match(line) for line in lines):
        return "inline"
    return "none"


def main(argv: list[str]) -> int:
    cwd = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    runtime = resolve_runtime(cwd)
    sessions_dir = runtime.memory_dir / "sessions"
    shapes: Counter[str] = Counter()
    ordinal_counts: Counter[int] = Counter()
    files = 0
    date_only_headings = 0
    for document in iter_session_documents(sessions_dir):
        files += 1
        text = document.path.read_text(encoding="utf-8")
        date_only_headings += sum(
            1
            for line in text.splitlines()
            if _DATE_HEADING_RE.match(line) and not _ENTRY_HEADING_RE.match(line)
        )
        for _entry_id, shape in _walk_entry_bodies(text, lambda body: [classify(body)]):
            shapes[shape] += 1
        for _entry_id, ordinals in _walk_entry_bodies(
            text, lambda body: [len(_entry_decision_ordinals(body))]
        ):
            ordinal_counts[ordinals] += 1

    total = sum(shapes.values())
    addressable = sum(count for n, count in ordinal_counts.items() if n >= 1)
    multi = sum(count for n, count in ordinal_counts.items() if n >= 2)
    print(f"session files read:       {files}")
    print(f"entries total (stamped, validator splitter): {total}")
    print(f"  + date-only legacy headings (chunk extractor also counts these): {date_only_headings}")
    print(f"  = entries under the chunk extractor's looser boundary: {total + date_only_headings}")
    for shape in ("numbered", "singular", "inline", "none"):
        print(f"  {shape:<22}{shapes[shape]}")
    print(f"entries with >=1 addressable decision: {addressable}")
    print(f"entries with >=2 addressable decisions: {multi}")
    print(f"addressable decisions total:           {sum(n * c for n, c in ordinal_counts.items())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
