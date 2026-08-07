"""Segment the lineage graph into per-concern chains, and surface the ones no ADR claims.

The lineage graph as a whole is unreadable: its largest connected component spans 67 decisions
across `session-logging`, `docs-lifecycle`, `panes`, `graph`, `package` and `trail` - subject matter
with nothing in common but the fact that something evolved into something else. Filtering edges to
those whose endpoints share a declared AREA breaks that into chains that read as single concerns:
11 decisions all in `mcp-tools`, 8 all in `session-fuse`, 7 all in `docs-lifecycle`.

Measured three times as the corpus grew (231 -> 265 -> 267 edges, with topic coverage nearly
doubling); the largest chain was the same 11 `mcp-tools` decisions every time.

**A chain that no ADR claims is a concern we have not recorded.** That is the second output here,
and it is a better ADR-discovery mechanism than the control-file harvest that seeded the corpus -
the harvest could only find concerns someone had already written down in `index.md`.

Read-only. Emits LINEAGE-CHAINS.md.
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
from memory_seed.adr import adr_membership, current_proposal, iter_adrs  # noqa: E402
from memory_seed.retrieval import load_corpus  # noqa: E402


def adr_claims() -> dict[str, list[str]]:
    """decision ref -> the ADRs claiming it, counting SOFT context as a claim.

    `adr_membership` covers decision_ref + predecessors only. A decision attached as
    `supporting_decisions` (hard) or through a `context-added` event (soft) is equally spoken for,
    and reporting its chain as unclaimed would send a reviewer to look at something already read.
    """
    claims: dict[str, list[str]] = collections.defaultdict(list)
    for record in iter_adrs(REPO):
        refs = set(adr_membership(record))
        for event in record.events:
            refs.update(event.supporting_decisions or ())
        proposal = current_proposal(record)
        if proposal:
            refs.update(proposal.supporting_decisions or ())
        for ref in refs:
            claims[ref].append(record.adr_id)
    return dict(claims)


def components(pairs: list[tuple[str, str]]) -> list[list[str]]:
    parent: dict[str, str] = {}

    def find(node: str) -> str:
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for older, newer in pairs:
        a, b = find(older), find(newer)
        if a != b:
            parent[b] = a
    groups: dict[str, list[str]] = collections.defaultdict(list)
    for node in list(parent):
        groups[find(node)].append(node)
    return sorted(groups.values(), key=len, reverse=True)


def main() -> int:
    area, _activity = decision_axes()
    edges, dropped = normalised_lineage_edges()
    claims = adr_claims()

    chunks = load_corpus(REPO, "decision")
    titles = {c.chunk_id: (c.title or "").strip() for c in chunks if c.chunk_id}
    stamps = {
        c.entry_id: str(c.entry_datetime or c.session_date or "")[:16]
        for c in load_corpus(REPO, "entry") if c.entry_id
    }
    when = lambda ref: stamps.get(ref.split(":")[0], "")  # noqa: E731

    same_area = [
        (o, n) for _k, o, n, _c in edges
        if area.get(o) and area.get(n) and area[o] & area[n]
    ]
    chains = [c for c in components(same_area) if len(c) >= 3]

    lines = [
        "# Lineage chains (same-area segmentation)", "",
        f"From {len(edges)} lineage edges ({dropped}), {len(same_area)} of which join decisions "
        "sharing a declared area.", "",
        "The unfiltered graph's largest component is 67 decisions spanning six unrelated areas. "
        "Filtering to shared area produces the chains below - each one reads as a single concern.",
        "", "Chains of 3+ decisions, largest first. **UNCLAIMED** means no ADR names any member "
        "(counting hard membership and soft `context-added` alike) - those are candidate concerns.",
        "",
    ]
    unclaimed = []
    for i, chain in enumerate(chains, 1):
        members = sorted(chain, key=lambda r: (when(r), r))
        areas = collections.Counter(a for r in members for a in area.get(r, ()))
        owning = sorted({adr for r in members for adr in claims.get(r, [])})
        label = f"chain {i}"
        head = f"## {label} — {areas.most_common(1)[0][0]} ({len(members)} decisions)"
        if not owning:
            unclaimed.append((label, members, areas.most_common(1)[0][0]))
            head += "  **UNCLAIMED**"
        lines.append(head)
        lines.append(f"- areas: {', '.join(f'{a} x{n}' for a, n in areas.most_common())}")
        lines.append(f"- claimed by: {', '.join(f'`{a}`' for a in owning) if owning else '*nothing*'}")
        for ref in members:
            mark = "".join(f" [`{a}`]" for a in claims.get(ref, []))
            lines.append(f"    - `{ref}`  {when(ref)}  {titles.get(ref, '?')[:70]}{mark}")
        lines.append("")

    lines += [
        "## ADR candidates", "",
        f"{len(unclaimed)} of {len(chains)} chains are unclaimed. Each is a concern with recorded "
        "lineage and no ADR - the strongest kind of candidate, because the decisions are already "
        "connected and already topic-coherent.", "",
    ]
    owed = 0
    for label, members, area_name in unclaimed:
        owed += len(members)
        lines.append(f"- **{area_name}** ({len(members)} decisions, {label}): "
                     f"`{members[0]}` … `{members[-1]}`")
        lines.append(f"    - suggested head: `{members[-1]}` — {titles.get(members[-1], '?')[:66]}")
    lines += [
        "",
        f"**Cost if all {len(unclaimed)} were founded and their members attached: {owed} diagram "
        "answers owed** (a decision attached to an ADR owes a diagram or an explicit "
        "`diagram_status: not_applicable` with a reason, per 2026-08-07). Choose the cost; do not "
        "discover it.",
        "",
    ]
    (HERE / "LINEAGE-CHAINS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"lineage edges: {len(edges)} | same-area edges: {len(same_area)}")
    print(f"chains of 3+: {len(chains)} | sizes: {[len(c) for c in chains[:8]]}")
    print(f"UNCLAIMED chains: {len(unclaimed)} | diagram answers they would owe: {owed}")
    for label, members, area_name in unclaimed[:8]:
        print(f"   {area_name:<20} {len(members):>2} decisions   ({label})")
    print("\nwrote LINEAGE-CHAINS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
