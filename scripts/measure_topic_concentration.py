"""Measure topic concentration before and after a vocabulary change.

This is the re-runnable form of the hand-authored table in
``docs/2_Todo/topic-vocabulary-concentration-review.md``. The hierarchical
vocabulary proposal makes concentration the *trigger* for earning children
("a slug earns children when it is carrying too much of its scope"), so the
measurement has to be a command anyone can repeat rather than a one-off audit -
otherwise the rule has no way to say when a level has stopped earning its place.

It reports three numbers per slug, and the difference between them is the whole
point of the hierarchy:

  authored   how many entries literally wrote this slug. Unaffected by any
             vocabulary change - no entry is ever rewritten.
  canonical  how many entries RESOLVE to this slug. Alias resolution folds a
             name in and discards it, so promoting an alias to a child slug
             moves volume OUT of the parent's canonical count and into the
             child's. This is the number that deflates.
  rollup     canonical plus every descendant's canonical. A parent's REACH is
             invariant across the change: filtering on it still matches
             everything it matched before, because ``expand_topic_filter``
             expands downward. Rollup proves the deflation cost no coverage.

Compare two vocabularies by passing ``--baseline`` a topics.yaml from before the
change (``git show <rev>:.memory-seed/topics.yaml > /tmp/before.yaml``). With no
baseline it prints the current state only.

Usage:
  python scripts/measure_topic_concentration.py [repo_root] [--baseline PATH]
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from memory_seed.semantic_cache import extract_memory_chunks  # noqa: E402
from memory_seed.topics import TopicIndex, load_topic_index  # noqa: E402


def _index_from_file(path: Path) -> TopicIndex:
    """Load a standalone topics.yaml by staging it where the reader expects it.

    ``load_topic_index`` is deliberately runtime-anchored (it resolves
    ``.memory-seed/`` rather than taking a file path), so rather than duplicate
    its line scanner - the second parser that would drift from the first - the
    baseline file is written into a throwaway runtime and read back with the
    same function.
    """
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="topic-baseline-"))
    memory_dir = tmp / ".memory-seed"
    memory_dir.mkdir()
    (memory_dir / "topics.yaml").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return load_topic_index(tmp)


def _counts(index: TopicIndex, authored: list[tuple[str, ...]]) -> tuple[Counter[str], Counter[str]]:
    """Canonical and rollup entry counts under ``index``.

    Counted per ENTRY, not per slug occurrence: an entry that writes both
    ``continuity`` and ``graph`` counts once toward ``graph``, matching how the
    concentration review computed share-of-corpus.
    """
    resolution = index.resolution()
    canonical: Counter[str] = Counter()
    rollup: Counter[str] = Counter()
    for slugs in authored:
        resolved = {resolution[slug] for slug in slugs if slug in resolution}
        for slug in resolved:
            canonical[slug] += 1
        reach = set(resolved)
        for slug in resolved:
            reach.update(index.ancestors(slug))
        for slug in reach:
            rollup[slug] += 1
    return canonical, rollup


def main(argv: list[str]) -> int:
    baseline_path: Path | None = None
    args: list[str] = []
    rest = argv[1:]
    while rest:
        item = rest.pop(0)
        if item == "--baseline":
            baseline_path = Path(rest.pop(0))
        elif item.startswith("--baseline="):
            baseline_path = Path(item.split("=", 1)[1])
        elif item.startswith("--"):
            continue
        else:
            args.append(item)
    cwd = Path(args[0]) if args else Path.cwd()

    chunks = extract_memory_chunks(cwd, granularity="entry")
    authored = [tuple(chunk.topics) for chunk in chunks if chunk.topics]
    total = len(authored)

    raw: Counter[str] = Counter()
    for slugs in authored:
        for slug in set(slugs):
            raw[slug] += 1

    current = load_topic_index(cwd)
    after_canonical, after_rollup = _counts(current, authored)

    print(f"topiced entries: {total}")
    print(f"vocabulary: {current.path} schema_version={current.schema_version} slugs={len(current.topics)}")
    print()

    if baseline_path is None:
        print(f"{'slug':<28}{'axis':<10}{'canonical':>10}{'share':>8}{'rollup':>8}")
        for slug, count in after_canonical.most_common():
            share = 100.0 * count / total if total else 0.0
            print(f"{slug:<28}{current.axis_of(slug) or '-':<10}{count:>10}{share:>7.1f}%{after_rollup[slug]:>8}")
        return 0

    before = _index_from_file(baseline_path)
    before_canonical, _ = _counts(before, authored)

    print("BEFORE -> AFTER canonical entry counts (share of topiced entries)")
    print(f"{'slug':<28}{'axis':<10}{'before':>8}{'after':>8}{'delta':>8}{'share<':>9}{'share>':>9}{'rollup':>8}")
    slugs = sorted(
        set(before_canonical) | set(after_canonical),
        key=lambda s: (-max(before_canonical[s], after_canonical[s]), s),
    )
    for slug in slugs:
        b, a = before_canonical[slug], after_canonical[slug]
        bs = 100.0 * b / total if total else 0.0
        as_ = 100.0 * a / total if total else 0.0
        mark = "" if b == a else "  <--"
        axis = current.axis_of(slug) or before.axis_of(slug) or "-"
        print(
            f"{slug:<28}{axis:<10}{b:>8}{a:>8}{a - b:>8}{bs:>8.1f}%{as_:>8.1f}%{after_rollup[slug]:>8}{mark}"
        )

    print()
    gained = sum(
        1
        for slugs_ in authored
        if {before.resolution().get(s, s) for s in slugs_} != {current.resolution().get(s, s) for s in slugs_}
    )
    print(f"entries whose resolved topic set changed (gained specificity): {gained}")

    print()
    print("slugs promoted from alias to canonical child:")
    before_canonicals = {r.slug for r in before.topics}
    for record in current.topics:
        if record.slug not in before_canonicals:
            print(
                f"  {record.slug:<28} parent={record.parent or '-':<20} "
                f"authored by {raw.get(record.slug, 0)} entries"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
