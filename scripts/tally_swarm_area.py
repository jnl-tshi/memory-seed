"""Tally the area swarm's saved answers, and emit the split the scorer reads.

The approval document quotes counts. This is where they come from, so the
document can be re-derived instead of trusted.

TWO INDEPENDENT WORKERS, AND ONLY THEIR AGREEMENT COUNTS. The experiment kept
each worker blind to the other (that was its point - a coherence audit needs
independence), so the corpus has two answers per entry. This reports all three
columns but the split it writes uses the AGREED label only:

    a count both workers reached independently is evidence;
    a count one worker reached is a hypothesis.

That is the conservative reading and it matters at the margin - `trace-harness`
is 9 by worker 1, 7 by worker 2, and 7 agreed, so it clears the floor of 8 on
one reading and fails it on another. A proposal that quotes the favourable
number is not measuring, it is arguing.

DUAL-TAGGED ENTRIES ARE ADDED BACK. The swarm judged the 116 entries carrying
`memory-trace` as their only area. Entries already carrying `memory-trace` AND
`graph` were never put to it - they are pre-labelled - so they are unioned into
the `graph` claim afterwards. Without this the split understates `graph` by an
order of magnitude and the scorer rejects it for the wrong reason.

Usage:
  python scripts/tally_swarm_area.py [repo_root] [--out split.json]
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from memory_seed.semantic_cache import extract_memory_chunks  # noqa: E402
from memory_seed.topics import load_topic_index  # noqa: E402

CYCLES = "docs/4_Reference/topic-swarm-cycles"
WORKER_1 = ("B_area1.tsv", "H_area1.tsv")  # dev half + held-out half
WORKER_2 = ("B_area2.tsv", "H_area2.tsv")

# Answers that are not candidate children of `memory-trace`. `TRACE-WIDE` is the
# deliberate "no child fits, it stays on the root" answer; `NONE` means the entry
# is not Trace work at all; the seed-* answers belong under `memory-seed`.
NOT_A_CHILD = {"TRACE-WIDE", "NONE", "seed-other", "lifecycle-edges"}


def _load(root: Path, names: tuple[str, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in names:
        path = root / CYCLES / name
        # NB: B_area1.tsv has no trailing newline. Reading line-by-line is safe;
        # `cat`-ing the files together is NOT - it glues the last row of one to
        # the first row of the next and silently corrupts two records.
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                out[parts[0]] = parts[1]
    return out


def main(argv: list[str]) -> int:
    root = Path(argv[0]) if argv and not argv[0].startswith("--") else Path.cwd()
    out_path = None
    for i, a in enumerate(argv):
        if a == "--out" and i + 1 < len(argv):
            out_path = Path(argv[i + 1])

    index = load_topic_index(root)
    resolve = index.resolution()
    carrying: dict[str, set[str]] = {}
    for chunk in extract_memory_chunks(root, granularity="entry"):
        if not chunk.entry_id:
            continue
        topics = {resolve.get(t, t) for t in (chunk.topics or ())}
        if "memory-trace" in topics:
            carrying[chunk.entry_id] = topics

    w1 = _load(root, WORKER_1)
    w2 = _load(root, WORKER_2)
    judged = sorted(set(w1) & set(w2))
    agreed = {i: w1[i] for i in judged if w1[i] == w2[i]}

    print(f"entries carrying memory-trace : {len(carrying)}")
    print(f"judged by both workers        : {len(judged)}")
    print(f"agreed                        : {len(agreed)}  ({len(agreed) / len(judged):.0%})")
    print()

    c1, c2 = Counter(w1[i] for i in judged), Counter(w2[i] for i in judged)
    ca = Counter(agreed.values())
    print(f"{'label':18} {'w1':>4} {'w2':>4} {'agreed':>7}   the count to quote")
    for label, _n in c1.most_common():
        print(f"{label:18} {c1[label]:4} {c2[label]:4} {ca[label]:7}")
    print()

    split: dict[str, list[str]] = defaultdict(list)
    for entry_id, label in agreed.items():
        if label not in NOT_A_CHILD and entry_id in carrying:
            split[label].append(entry_id)
    dual = [i for i, t in carrying.items() if "graph" in t]
    for entry_id in dual:
        if entry_id not in split["graph"]:
            split["graph"].append(entry_id)
    print(f"dual-tagged memory-trace+graph added back to `graph`: {len(dual)}")
    print()
    for label, ids in sorted(split.items()):
        print(f"  {label:18} {len(ids):4}")

    if out_path:
        out_path.write_text(json.dumps(dict(split), indent=1), encoding="utf-8")
        print(f"\nwrote {out_path} - feed it to propose_topic_children.py score memory-trace")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
