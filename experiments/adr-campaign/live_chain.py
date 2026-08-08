"""The live chain behind each pending ADR: every member not completely replaced, in order.

JNL's rule, which this exists to serve: a decision sitting at the end of a chain must not be the
sole informant of the ADR summary. Every member that has not been completely replaced is
considered, and the summary is synthesised along the evolution chain.

So the head stops being the summary and becomes the anchor. What the summary owes its substance to
is the LIVE chain:

- **members** = `adr_membership()` (the proposed/accepted ref plus its predecessors) union every
  event's `supporting_decisions`. Founding pseudo-refs are excluded - a control-file line is a
  placeholder, not a decision with substance to synthesise.
- **dead** = a member with a `replaces` edge pointing away from it. `normalised_lineage_edges()`
  yields `(kind, older, newer, confidence)`, so a `replaces` edge kills its `older` end. Members
  joined by `evolves` ALL stay live - an evolution adds to the position, it does not retire it.
- **order** = oldest to newest along the `evolves` edges among live members, falling back to the
  decision's own date where the graph does not constrain the pair.

Output doubles as the swarm payload (bodies inline, closed member list) and as the artifact JNL
reads at the approval gate.

Usage:  python experiments/adr-campaign/live_chain.py [--json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from memory_seed.adr import adr_membership, iter_adrs, proposal_for, replay_adr  # noqa: E402
from memory_seed.retrieval import get_chunk  # noqa: E402

from audit_link_topic_join import normalised_lineage_edges  # noqa: E402

BODY_CHARS = 420
PER_BATCH = 4


def norm(text: str) -> str:
    return " ".join(text.split())


def members_of(record) -> set[str]:
    refs = {r for r in adr_membership(record) if not r.startswith("founding:")}
    for event in record.events:
        refs |= {r for r in (event.supporting_decisions or ()) if not r.startswith("founding:")}
    return refs


def chain_order(live: list[str], evolves: dict[str, set[str]], dated: dict[str, str]) -> list[str]:
    """Oldest to newest: topological along `evolves`, date as the tie-break and the fallback."""
    live_set = set(live)
    indegree = {ref: 0 for ref in live}
    for older, newers in evolves.items():
        if older not in live_set:
            continue
        for newer in newers & live_set:
            indegree[newer] += 1
    ordered, ready = [], sorted((r for r in live if not indegree[r]), key=lambda r: dated.get(r, ""))
    while ready:
        ref = ready.pop(0)
        ordered.append(ref)
        for newer in sorted(evolves.get(ref, set()) & live_set, key=lambda r: dated.get(r, "")):
            indegree[newer] -= 1
            if not indegree[newer]:
                ready.append(newer)
        ready.sort(key=lambda r: dated.get(r, ""))
    # A cycle would strand members; the graph is acyclic by contract, but never drop silently.
    ordered.extend(sorted(set(live) - set(ordered), key=lambda r: dated.get(r, "")))
    return ordered


def main() -> int:
    edges, _tally = normalised_lineage_edges(REPO)
    replaced_by: dict[str, set[str]] = {}
    evolves: dict[str, set[str]] = {}
    for kind, older, newer, _conf in edges:
        (replaced_by if kind == "replaces" else evolves).setdefault(older, set()).add(newer)

    payload = []
    for record in sorted(iter_adrs(REPO), key=lambda r: r.adr_id):
        state = replay_adr(record)
        if not state.pending_decisions:
            continue
        ref = state.pending_decisions[0]
        proposal = proposal_for(record, ref)
        refs = members_of(record)

        chunks, dated = {}, {}
        for member in refs:
            try:
                chunk = get_chunk(member, REPO)
            except Exception:
                continue
            chunks[member] = chunk
            dated[member] = str(chunk.get("date") or chunk.get("timestamp") or "")

        dead = {m: sorted(replaced_by.get(m, set())) for m in refs if replaced_by.get(m)}
        live = chain_order([m for m in refs if m not in dead], evolves, dated)

        def rendered(member: str) -> dict:
            chunk = chunks.get(member, {})
            title = norm(chunk.get("title") or "")
            body = norm(chunk.get("text") or "")
            if title and body.startswith(title):
                body = body[len(title):].strip()
            elif title:
                body = body.replace(title, " ").strip()
            return {"ref": member, "title": title, "date": dated.get(member, ""),
                    "body": body[:BODY_CHARS], "is_head": member == ref}

        payload.append({
            "adr_id": record.adr_id,
            "title": record.title,
            "head": ref,
            "head_is_newest_live": bool(live) and live[-1] == ref,
            "current_summary": norm(proposal.decision if proposal else ""),
            "current_why": norm(proposal.why if proposal else ""),
            "live_chain": [rendered(m) for m in live],
            "replaced": [{"ref": m, "replaced_by": v} for m, v in sorted(dead.items())],
            "unresolvable": sorted(refs - set(chunks)),
        })

    if "--json" in sys.argv:
        (HERE / "live-chain.json").write_text(
            json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
        for i in range(0, len(payload), PER_BATCH):
            (HERE / f"synth-batch-{i // PER_BATCH}.json").write_text(
                json.dumps(payload[i:i + PER_BATCH], indent=1, ensure_ascii=False),
                encoding="utf-8")
        print(f"wrote live-chain.json and {-(-len(payload) // PER_BATCH)} synth batches")

    total_live = sum(len(p["live_chain"]) for p in payload)
    no_live = [p["adr_id"] for p in payload if not p["live_chain"]]
    not_newest = [p["adr_id"] for p in payload if p["live_chain"] and not p["head_is_newest_live"]]
    print(f"pending ADRs: {len(payload)}; live members to synthesise from: {total_live}")
    print(f"  head is NOT the newest live member: {len(not_newest)}")
    for adr_id in not_newest:
        print(f"    {adr_id}")
    print(f"  ADRs with NO live member at all:    {len(no_live)}")
    for adr_id in no_live:
        print(f"    {adr_id}")
    for entry in payload:
        if entry["replaced"]:
            for item in entry["replaced"]:
                print(f"  REPLACED {entry['adr_id']:<36} {item['ref']} -> {', '.join(item['replaced_by'])}")
        if entry["unresolvable"]:
            print(f"  UNRESOLVABLE {entry['adr_id']:<32} {', '.join(entry['unresolvable'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
