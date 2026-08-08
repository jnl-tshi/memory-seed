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
    every_chain = components(same_area)
    chains = [c for c in every_chain if len(c) >= 3]
    # A pair is a candidate too (JNL, 2026-08-08) - two linked decisions in one area can be a
    # concern - but a pair is far weaker evidence than a chain: two decisions touching the same
    # area may simply be two decisions. Pairs are reported separately and want an architectural
    # judgement, not automatic founding.
    pairs = [c for c in every_chain if len(c) == 2]
    # GROWTH: a chain some ADR claims, carrying members that ADR does not name. The concern was
    # reviewed at one size and has since grown, so the review is stale - it may want the new
    # decisions attached, or it may have grown into a second concern that deserves splitting off.
    grown = []
    for chain in every_chain:
        owners = sorted({a for r in chain for a in claims.get(r, [])})
        if not owners:
            continue
        unnamed = [r for r in chain if not claims.get(r)]
        if unnamed:
            grown.append((owners, chain, unnamed))

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
    for label, members, area_name in unclaimed:
        lines.append(f"- **{area_name}** ({len(members)} decisions, {label}): "
                     f"`{members[0]}` … `{members[-1]}`")
        lines.append(f"    - suggested head: `{members[-1]}` — {titles.get(members[-1], '?')[:66]}")
    lines += [
        "",
        f"**Cost if all {len(unclaimed)} were founded: {len(unclaimed)} diagram answers** — one per "
        "ADR, not one per attached decision. A diagram block keys on `adr_id` and is filed under "
        "the head's session date, so an ADR is looked at once and the verdict recorded (a diagram, "
        "or `diagram_status: not_applicable` with a reason); ESR counts "
        "`adrs_without_diagram_answer` over ADR ids. Attaching 11 decisions to one ADR owes one "
        "answer, not eleven.",
        "",
    ]
    # --- Re-review: chains that have grown past the size their ADR was reviewed at ---
    lines += [
        "## Chains that have grown since review", "",
        f"{len(grown)} chains carry decisions the claiming ADR does not name. The concern was "
        "reviewed at one size and the lineage has since extended, so the review is stale in one of "
        "two ways: the new decisions belong to the concern and should be attached, or the chain "
        "has grown into a SECOND concern that should be split off into its own ADR. Either way it "
        "wants a look.", "",
    ]
    for owners, chain, unnamed in sorted(grown, key=lambda g: -len(g[2])):
        members = sorted(chain, key=lambda r: (when(r), r))
        lines.append(f"- {', '.join(f'`{a}`' for a in owners)} — "
                     f"{len(unnamed)} of {len(members)} members unnamed")
        for ref in sorted(unnamed, key=lambda r: (when(r), r)):
            lines.append(f"    - `{ref}`  {when(ref)}  {titles.get(ref, '?')[:66]}")
    lines.append("")

    # --- Pairs: candidates, but weaker evidence than a chain ---
    unclaimed_pairs = [c for c in pairs if not any(claims.get(r) for r in c)]
    lines += [
        "## Candidate pairs (two linked decisions)", "",
        f"{len(unclaimed_pairs)} of {len(pairs)} pairs are unclaimed. A pair is a candidate, not a "
        "chain: two decisions sharing an area and one edge may be a concern, or may just be two "
        "decisions. Each needs an architectural judgement before it is founded - read both, and "
        "found only what a reader would expect to find recorded as a standing concern.", "",
    ]
    for chain in sorted(unclaimed_pairs, key=lambda c: sorted(c)):
        members = sorted(chain, key=lambda r: (when(r), r))
        areas = sorted({a for r in members for a in area.get(r, ())})
        lines.append(f"- **{'/'.join(areas)}**")
        for ref in members:
            lines.append(f"    - `{ref}`  {when(ref)}  {titles.get(ref, '?')[:66]}")
    lines.append("")

    (HERE / "LINEAGE-CHAINS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"lineage edges: {len(edges)} | same-area edges: {len(same_area)}")
    print(f"chains of 3+: {len(chains)} | sizes: {[len(c) for c in chains[:8]]}")
    print(f"UNCLAIMED chains: {len(unclaimed)} | diagram answers they would owe: {len(unclaimed)} (one per ADR)")
    for label, members, area_name in unclaimed[:8]:
        print(f"   {area_name:<20} {len(members):>2} decisions   ({label})")
    print(f"GROWN since review: {len(grown)} chains carry members their ADR does not name")
    for owners, chain, unnamed in sorted(grown, key=lambda g: -len(g[2])):
        print(f"   {','.join(owners):<44} +{len(unnamed)} unnamed of {len(chain)}")
    print(f"CANDIDATE PAIRS: {len(unclaimed_pairs)} unclaimed of {len(pairs)}")
    print("\nwrote LINEAGE-CHAINS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
