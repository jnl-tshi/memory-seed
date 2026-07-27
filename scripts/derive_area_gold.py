"""Derive a BEHAVIOURAL gold set for the area axis, from the files entries touched.

Every measure of the topic swarm so far has been scored against authored topic
tags, and the pilot adjudication already found those upheld only ~50% of the time
when contested. So "accuracy" has been measured against a proxy of unknown
quality. This closes that hole for one axis, and it costs no human judgement:

    an entry that changed `client/src/TrailWorkspace.tsx` is `trail` work

not as an opinion but as a description of what happened. 87% of entries in this
corpus record their touched files in `- F:` bullets, so the label is derivable.

THE RULES THAT MAKE IT GOLD RATHER THAN ANOTHER GUESS:

1. A path maps to an area only when the mapping is unarguable. `TrailWorkspace.tsx`
   is `trail`. `service.py` is NOT mapped at all - it holds the HTTP routes, the
   graph projection and the cache in one 3000-line module, so it discriminates
   nothing.
2. An entry is gold only when its mapped paths agree on ONE area. Entries whose
   files span several are EXCLUDED, not resolved by majority or by proximity -
   those are the genuinely ambiguous rows, and letting an author's guess in
   would encode exactly the opinion this exists to avoid.
3. Entries with no mapped path are excluded.

The result is a small, high-confidence set. Small is correct: a gold set earns its
authority by being unarguable, not by being large.

Usage:
  python scripts/derive_area_gold.py [repo_root] [--out gold.tsv]
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from memory_seed.semantic_cache import extract_memory_chunks  # noqa: E402

# Ordered: the FIRST pattern that matches a path wins, so the specific
# (TrailWorkspace) is tested before the general (client/src).
PATH_AREA: list[tuple[str, str]] = [
    # --- Trace: the timeline view ---
    (r"client/src/(TrailWorkspace|trailModel|trailScroll|trailGeometry)", "trail"),
    # --- Trace: the relationship map ---
    (r"client/src/(GraphWorkspace|graphCommunities|graphLayout|graphForces|graphEdges|graphOverview|graphDecisionRows)", "graph"),
    # --- Trace: the reader pane ---
    (r"client/src/(EntryReader|inspectorScroll)", "inspector"),
    # --- Trace: the diagram viewer ---
    (r"client/src/(DiagramViewer|arc2d)", "diagram-view"),
    # --- Trace: the apparatus that proves it works ---
    (r"client/\.storybook/", "trace-harness"),
    (r"client/[^ ]*\.stories\.tsx", "trace-harness"),
    (r"(playwright|vitest)\.config", "trace-harness"),
    (r"memory-trace/tests/e2e/", "trace-harness"),
    # --- Trace: the versioned HTTP contract ---
    (r"memory_trace/models\.py", "trace-api"),
    (r"memory-trace/tests/contract/", "trace-api"),
    # --- Trace: startup and caching ---
    (r"memory_trace/cache\.py", "trace-cache"),
    # --- Trace: the app frame ---
    (r"client/src/(App\.tsx|SettingsMenu|styles\.css|main\.tsx)", "TRACE-WIDE"),
    # --- Seed ---
    (r"memory_seed/", "seed"),
]

# Paths that are real but discriminate NOTHING, listed explicitly so the
# exclusion is a decision rather than an oversight.
NON_DISCRIMINATING = [
    r"memory_trace/service\.py",   # routes + projection + cache in one module
    r"memory-trace/memory_trace/static/",  # built assets
    r"docs/",
    r"\.memory-seed/",
    r"README",
    r"CHANGELOG",
]

# A path votes only if it is RARE. Measured 2026-07-27: the first version of this
# script mislabelled "Trail complete: brackets and two-stage selection" as
# `trace-api`, because the only MAPPABLE file it listed was `models.py` - and
# `App.tsx`, `styles.css` and `models.py` are touched by a large share of all UI
# work, so their presence says nothing about what an entry was about.
#
# "Exactly one mapped area" therefore does not mean "the entry is about that
# area"; it can mean "only one of its files happened to be mappable". Rarity is
# the fix, and it is the same idf-weighting principle `link audit` already uses on
# shared files. A path touched by more than this share of entries is dropped
# before any vote is counted.
MAX_PATH_SHARE = 0.03


def paths_in(text: str) -> list[str]:
    out: list[str] = []
    for line in re.findall(r"(?m)^\s*-\s*F:\s*(.+)$", text or ""):
        out.extend(re.findall(r"`([^`]+)`", line))
        # bare paths too, for entries that did not backtick them
        out.extend(re.findall(r"(?<![`\w])((?:[\w.\-]+/)+[\w.\-]+\.\w+)", line))
    return out


def area_of(path: str) -> str | None:
    for pattern in NON_DISCRIMINATING:
        if re.search(pattern, path):
            return None
    for pattern, area in PATH_AREA:
        if re.search(pattern, path):
            return area
    return None


def main(argv: list[str]) -> int:
    root = Path(argv[0]) if argv and not argv[0].startswith("--") else Path.cwd()
    out_path = None
    for i, a in enumerate(argv):
        if a == "--out" and i + 1 < len(argv):
            out_path = Path(argv[i + 1])

    entries = [c for c in extract_memory_chunks(root, granularity="entry") if c.entry_id]
    # Pass 1: how common is each path? A path in many entries cannot discriminate.
    frequency: Counter[str] = Counter()
    for chunk in entries:
        for path in set(paths_in(chunk.text or "")):
            frequency[path] += 1
    ceiling = max(2, int(len(entries) * MAX_PATH_SHARE))
    common = {p for p, n in frequency.items() if n > ceiling}
    print(f"corpus {len(entries)} entries; a path may appear in at most {ceiling}")
    print(f"dropped as too common: {len(common)} paths -> {sorted(common)[:6]}...")
    print()

    gold: dict[str, str] = {}
    stats = Counter()
    for chunk in entries:
        rare = [p for p in paths_in(chunk.text or "") if p not in common]
        found = {a for a in (area_of(p) for p in rare) if a}
        if not found:
            stats["no rare mapped path"] += 1
        elif len(found) > 1:
            stats["spans several areas (excluded)"] += 1
        else:
            gold[chunk.entry_id] = found.pop()
            stats["GOLD"] += 1

    print(f"gold entries: {len(gold)}")
    for k, v in stats.most_common():
        print(f"  {k:34} {v}")
    print()
    print("gold label distribution:")
    for k, v in Counter(gold.values()).most_common():
        print(f"  {k:16} {v}")
    if out_path:
        out_path.write_text("\n".join(f"{k}\t{v}" for k, v in sorted(gold.items())), encoding="utf-8")
        print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
