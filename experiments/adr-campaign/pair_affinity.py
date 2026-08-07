"""Which AREA pairs recur across lineage hops - so a topically "unrelated" candidate can still count.

JNL's question: are there characteristic hop TYPES between areas? If `schema` and `lifecycle-edges`
keep evolving into each other, a candidate in one is relevant to an ADR in the other even though a
plain topic match would call them unrelated.

Measured with lift = observed / expected-under-independence, because **count and lift disagree and
lift is the right lens**: `feature-build -> feature-build` has the highest raw count (57) at lift
1.13, which is chance - `feature-build` is simply everywhere. The characteristic hops are rarer.

Ten cross-area pairs survive n>=3 and lift>=2.0, several bidirectional, and they replicated across
three corpus states (231 -> 265 -> 267 edges):

    lifecycle-edges <-> schema      11.14 / 6.27
    diagram-view    <-> memory-trace 9.36 / 2.93
    memory-trace     -> panes        4.88
    hooks            -> session-logging 4.18
    docs-lifecycle  <-> package      3.15 / 3.04

=== THE TWO RULES THIS MODULE EXISTS TO ENFORCE ===

**1. RECALL ONLY. Never gate, never rank.** Both uses were measured and both failed:

  - As a GATE: applying the table to the labelled hops gave the KNOWN-BAD hop the highest lift of
    all (11.30) - from n=1, because that very edge was in the data the table learned from. Leakage,
    not signal. Hence leave-one-out and the n>=3 floor below.
  - As a RANKER: every topic-derived scorer placed JNL's approved picks at chance (mean rank
    3.00/5, indistinguishable from random). Reading the decision body is what selects.

  What topics DO earn: recall. All 5 approved picks were surfaced from ~1050 topiced decisions.
  This table widens that surfacing, and nothing else. A wrong pair costs one extra candidate a
  worker reads and discards.

**2. The table is DERIVED FROM SWARM OUTPUT.** 229 of 267 lineage edges are machine-suggested;
learning from authored edges alone yields 1 usable pair from 38. The circularity cannot be removed,
so it is contained by bounding the blast radius (rule 1) rather than by pretending the input is
clean. Regenerate it, never store it as authority - Constitution Invariant #6.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from audit_link_topic_join import decision_axes, normalised_lineage_edges  # noqa: E402

MIN_COUNT = 3
MIN_LIFT = 2.0


def affinity_table(exclude_edge: tuple[str, str] | None = None) -> dict[tuple[str, str], tuple[float, int]]:
    """(area_older, area_newer) -> (lift, count) for cross-area pairs clearing the floors.

    `exclude_edge` implements leave-one-out: when scoring a specific hop, the hop's own edge must
    not contribute to the table judging it. Without this the table simply confirms whatever it was
    trained on - measured at lift 11.30 on a single self-supporting observation.
    """
    area, _ = decision_axes()
    edges, _ = normalised_lineage_edges()
    pairs: collections.Counter = collections.Counter()
    older_marg: collections.Counter = collections.Counter()
    newer_marg: collections.Counter = collections.Counter()
    for _kind, older, newer, _conf in edges:
        if exclude_edge and (older, newer) == exclude_edge:
            continue
        for x in area.get(older, ()):
            older_marg[x] += 1
            for y in area.get(newer, ()):
                pairs[(x, y)] += 1
        for y in area.get(newer, ()):
            newer_marg[y] += 1
    total = sum(pairs.values()) or 1
    table: dict[tuple[str, str], tuple[float, int]] = {}
    for (x, y), count in pairs.items():
        if x == y or count < MIN_COUNT:
            continue
        expected = (older_marg[x] * newer_marg[y]) / total
        if not expected:
            continue
        lift = count / expected
        if lift >= MIN_LIFT:
            table[(x, y)] = (lift, count)
    return table


def expansion_map(table: dict[tuple[str, str], tuple[float, int]]) -> dict[str, dict[str, tuple[float, int]]]:
    """area -> {partner area: (lift, count)}, symmetric.

    Symmetric because recall does not care about direction: if `schema` decisions evolve into
    `lifecycle-edges` ones, a `lifecycle-edges` ADR wants to see `schema` candidates and vice versa.
    Direction matters for lineage; this is not lineage.
    """
    out: dict[str, dict[str, tuple[float, int]]] = collections.defaultdict(dict)
    for (x, y), (lift, count) in table.items():
        for a, b in ((x, y), (y, x)):
            prior = out[a].get(b)
            if prior is None or lift > prior[0]:
                out[a][b] = (lift, count)
    return dict(out)


def main() -> int:
    table = affinity_table()
    print(f"cross-area pairs at n>={MIN_COUNT}, lift>={MIN_LIFT}: {len(table)}\n")
    for (x, y), (lift, count) in sorted(table.items(), key=lambda kv: -kv[1][0]):
        rev = table.get((y, x))
        print(f"  lift {lift:5.2f}  n={count:<3} {x:<22} -> {y:<22}"
              f"{'  [bidirectional]' if rev else ''}")
    expand = expansion_map(table)
    print(f"\nexpansion map: {len(expand)} areas gain partners")
    for a in sorted(expand):
        parts = ", ".join(f"{b} ({l:.1f})" for b, (l, _n) in sorted(expand[a].items(), key=lambda kv: -kv[1][0]))
        print(f"  {a:<22} -> {parts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
