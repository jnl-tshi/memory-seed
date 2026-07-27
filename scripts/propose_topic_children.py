"""Proposal mode: gather the material for a vocabulary change, and judge one.

`vocabulary-proposal-mode-proposal.md` splits the swarm's two jobs and refuses to
let them merge. ASSIGN picks slugs from `topics.yaml`, is validated, and writes
sidecars. PROPOSE reads every entry under one over-broad slug and emits a
document for human review - and **cannot write to the corpus at all**. This
script is the propose side, and it is deliberately two commands that do not talk
to each other:

  gather   dump every entry carrying a slug, with the fields a reader needs to
           cluster them. Read-only. Produces the material a judgement is made
           FROM; it makes no judgement itself.

  score    take a candidate split (child -> entry ids) and compute whether it is
           worth making: the projected share, the floor test, and the coverage
           left behind. Read-only. It cannot create a slug; it can only tell you
           what one would do.

Neither writes `topics.yaml`. That file is deploy-once project-local governance -
`memory-seed update` never overwrites it - so a vocabulary change is a human act
with a document behind it, which is the whole safety argument for letting the
proposal side be speculative.

The TRIGGER is `measure_topic_concentration.py`, not this script: a slug over the
threshold is a candidate for children and nothing else is. Run that first; its
output is the work queue.

Usage:
  python scripts/propose_topic_children.py gather <slug> [repo_root] [--limit N]
  python scripts/propose_topic_children.py score <slug> <split.json> [repo_root]

`split.json` is `{"child-slug": ["mse_...", ...], ...}`.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from memory_seed.semantic_cache import extract_memory_chunks  # noqa: E402
from memory_seed.topics import load_topic_index  # noqa: E402

# A candidate claiming fewer than this many entries is unearned depth. Stated up
# front so a proposal can FAIL cleanly rather than being argued about: the
# vocabulary's own promotion rule already declined `supply-chain` and `profiling`
# for want of evidence, and an invented child has to clear at least as much.
MIN_CHILD_ENTRIES = 8

# ...but the floor applies only to the SECOND generation - a direct child of a
# root. From the third generation down there is no floor at all (JNL,
# 2026-07-27).
#
# The reason is that depth is cheap once a parent exists to aggregate it. Every
# consumer already rolls up: `expand_topic_filter` matches a parent against every
# descendant transitively, community colour keys on the ROOT so the palette never
# grows, and any analysis can be run at whatever generation makes sense. A
# one-off grandchild therefore costs nothing and loses nothing - it is strictly
# more information than its parent carried alone.
#
# What the floor still buys at generation 2 is a check on whether a new BRANCH of
# the tree is justified at all. That is the expensive decision; refining a branch
# that already exists is not.
#
# The incentive this creates is deliberate: three sub-floor candidates that share
# a natural grouping should be proposed UNDER that grouping rather than beside it.
# `panes` was the worked example - inspector (6), topbar (6), navigation (4),
# settings (4), workspace-bar (2) and diagram-view (2) all fail the floor
# individually, while `panes` clears it at 23 and makes every one of them a
# floor-free grandchild.
#
# NOT to be confused with COMMUNITY_TOPIC_FLOOR (10) in graphCommunities.ts, which
# governs which topics may NAME a graph community. That one stays: it is about
# how many colours the palette hands out, not about what the vocabulary may say.
FLOOR_APPLIES_UP_TO_GENERATION = 2

# A split that leaves the parent above this has not solved the problem it was
# triggered by. Same number the concentration review used to call a slug broad.
TARGET_PARENT_SHARE = 0.20


def _entries(root: Path):
    """Every entry chunk with its resolved topics, newest first."""
    index = load_topic_index(root)
    resolve = index.resolution()
    out = []
    for chunk in extract_memory_chunks(root, granularity="entry"):
        if not chunk.entry_id:
            continue
        topics = tuple(resolve.get(t, t) for t in (chunk.topics or ()))
        out.append((chunk, topics))
    out.sort(key=lambda item: (item[0].session_date or "", item[0].entry_id), reverse=True)
    return out, index


def gather(root: Path, slug: str, limit: int | None) -> int:
    entries, index = _entries(root)
    descendants = set(index.descendants(slug)) | {slug}
    carrying = [(c, t) for c, t in entries if descendants & set(t)]
    total_topiced = sum(1 for _c, t in entries if t)
    print(f"# {slug}: {len(carrying)} entries, {len(carrying) / max(1, total_topiced):.1%} of {total_topiced} topiced")
    print(f"# axis: {index.axis_of(slug) or '(none)'}")
    existing = sorted(index.descendants(slug))
    print(f"# existing children: {', '.join(existing) if existing else '(none)'}")
    print()
    # Co-occurring topics are the cheapest signal for where the natural seams
    # are: a parent that always appears beside the same three topics is usually
    # carrying three jobs.
    beside = Counter(t for _c, topics in carrying for t in topics if t not in descendants)
    print("# co-occurring topics (the seams a split usually follows):")
    for topic, count in beside.most_common(12):
        print(f"#   {topic:26} {count:4}  {count / len(carrying):.0%}")
    print()
    for chunk, topics in carrying[: limit or len(carrying)]:
        others = " ".join(sorted(t for t in topics if t not in descendants))
        title = (chunk.entry_title or chunk.title or "").strip()
        print(f"{chunk.entry_id}\t{chunk.session_date}\t{others}\t{title}")
    return 0


def score(root: Path, slug: str, split_path: Path) -> int:
    entries, index = _entries(root)
    descendants = set(index.descendants(slug)) | {slug}
    carrying = [(c, t) for c, t in entries if descendants & set(t)]
    by_id = {c.entry_id: c for c, _t in carrying}
    total_topiced = sum(1 for _c, t in entries if t)
    split: dict[str, list[str]] = json.loads(split_path.read_text(encoding="utf-8"))

    # Generation of the PROPOSED children: root is 1, so a child of a root is 2.
    generation = len(index.ancestors(slug)) + 2
    floored = generation <= FLOOR_APPLIES_UP_TO_GENERATION
    print(f"parent {slug}: {len(carrying)} entries, {len(carrying) / total_topiced:.1%} of {total_topiced}")
    print(
        f"proposed children are generation {generation} - "
        + (f"floor of {MIN_CHILD_ENTRIES} applies" if floored else "NO FLOOR (depth is free below generation 2)")
    )
    print()
    claimed: set[str] = set()
    failures: list[str] = []
    for child, ids in sorted(split.items()):
        known = [i for i in ids if i in by_id]
        unknown = [i for i in ids if i not in by_id]
        overlap = sorted(set(known) & claimed)
        claimed.update(known)
        if not floored:
            verdict = "ok (no floor at this depth)"
        elif len(known) >= MIN_CHILD_ENTRIES:
            verdict = "ok"
        else:
            verdict = f"UNDER FLOOR ({MIN_CHILD_ENTRIES})"
            failures.append(
                f"{child} claims {len(known)}, floor is {MIN_CHILD_ENTRIES}"
                " - consider proposing it UNDER a grouping child instead, where no floor applies"
            )
        if unknown:
            failures.append(f"{child} names {len(unknown)} entries that do not carry {slug}: {unknown[:3]}")
        if overlap:
            failures.append(f"{child} overlaps an earlier child on {len(overlap)} entries: {overlap[:3]}")
        print(f"  {child:30} {len(known):4} entries  {len(known) / total_topiced:5.1%} of corpus   {verdict}")
    residual = len(carrying) - len(claimed)
    share = residual / total_topiced
    print()
    print(f"  {'(residual on the parent)':30} {residual:4} entries  {share:5.1%} of corpus")
    print()
    if share > TARGET_PARENT_SHARE:
        failures.append(
            f"parent still {share:.1%} after the split, target is <={TARGET_PARENT_SHARE:.0%}"
            " - the split does not solve what triggered it"
        )
    if failures:
        print("REJECT:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    cleared = (
        f"every child clears {MIN_CHILD_ENTRIES}"
        if floored
        else f"generation {generation} carries no floor, so size was not a criterion"
    )
    print(f"ACCEPTABLE: {cleared}, parent falls to {share:.1%}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    command = argv[0]
    if command == "gather":
        slug = argv[1]
        rest = [a for a in argv[2:] if not a.startswith("--")]
        limit = None
        for arg in argv[2:]:
            if arg.startswith("--limit"):
                limit = int(arg.split("=", 1)[1]) if "=" in arg else None
        root = Path(rest[0]) if rest else Path.cwd()
        return gather(root, slug, limit)
    if command == "score":
        slug, split_path = argv[1], Path(argv[2])
        root = Path(argv[3]) if len(argv) > 3 else Path.cwd()
        return score(root, slug, split_path)
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
