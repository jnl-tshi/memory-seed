"""Map each ADR's members forward through link-sidecar lineage to their current head.

An ADR's member decisions may have been evolved or replaced after the ADR was founded. The link
sidecars record those edges at decision granularity; this walks them forward so the ADR can be
re-anchored on the decision that is current, with `related` edges recorded as context.

Three rules do the real work, the third learned the hard way:

**Stop on fan-out, not on hop count.** Follow a chain only while a node has exactly ONE qualifying
successor. A branch means the concern split, and choosing a branch is judgement, not mechanics -
a 6-hop unrestricted walk from `adr_control_file_authority` reached the decision-identity mandate,
which belongs to a different ADR entirely.

**Absent confidence means authored, not unscored-therefore-weak.** Per the edge-confidence
contract, an ABSENT `edge_confidence` is the strongest evidence: a human wrote that edge.

**Only an AUTHORED edge may move an ADR's head; a machine-scored edge is surfaced for review.**
This was measured, not assumed. Applying a 0.75-scored edge moved `adr_subproject_scoping` onto
`ms-0bd3d8b2:d1` - "Use a seeded trigger registry instead of only prose triggers" - a decision
about skill triggers, not sub-project scoping. The write was reverted before publication. The
link campaign's own premise is that the swarm only suggests and a human decides; an ADR head is
exactly the kind of decision that reserves. Confidence tiers do not help here: that edge scored
0.75 and the corpus has candidates at 0.9 with the same failure mode available.

Read-only. Emits `lineage-map.json` plus `LINEAGE-REVIEW.md`, the human queue.
`reconcile_lineage.py` applies ONLY ADRs named explicitly with --approve.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from memory_seed.adr import (  # noqa: E402
    DECISION_REF_RE,
    _entry_decisions,
    adr_membership,
    current_proposal,
    iter_adrs,
)
from memory_seed.retrieval import entry_link_sidecars, get_chunk  # noqa: E402

# sha256-pinned by experiments/context-derivation/fixture_source/real-current.json. Mapped and
# reported, never written - re-pinning is JNL's call, not a side effect of this pass.
PINNED = {
    "adr_mcp_decision_envelope_review",
    "adr_parent_first_sidecar_transaction",
    "adr_session_decision_authority",
}
CONFIDENCE_FLOOR = 0.7


def build_successor_index(cwd: Path) -> tuple[dict, int, int]:
    """target_ref -> [(kind, source_ref, confidence)]. evolves/replaces point BACKWARD in time."""
    # Resolve the entry->ordinals map once: canonical_decision_refs() rescans the whole session
    # corpus per call, and this normalises both ends of every edge.
    _, ordinals = _entry_decisions(cwd)

    def canonical(ref: str) -> str | None:
        """Bare refs normalise only where the entry has exactly one decision (contract rule)."""
        if DECISION_REF_RE.fullmatch(ref):
            return ref
        choices = sorted(ordinals.get(ref, set()))
        return f"{ref}:{choices[0]}" if len(choices) == 1 else None

    index: dict[str, list[tuple[str, str, float | None]]] = {}
    total = unnormalised = 0
    for src_entry, rec in entry_link_sidecars(cwd).items():
        conf = rec.get("edge_confidence") or {}
        for kind, s_ord, t_entry, t_ord in (rec.get("decision_edges") or ()):
            total += 1
            source = canonical(f"{src_entry}:{s_ord}" if s_ord else src_entry)
            target = canonical(f"{t_entry}:{t_ord}" if t_ord else t_entry)
            if not source or not target:
                unnormalised += 1
                continue
            index.setdefault(target, []).append((kind, source, conf.get((s_ord, t_entry, t_ord))))
    return index, total, unnormalised


def qualifies(confidence: float | None) -> bool:
    """Absent confidence means authored - the strongest evidence, not the weakest."""
    return confidence is None or confidence >= CONFIDENCE_FLOOR


def walk(seed: str, index: dict) -> dict:
    """Follow lineage while each node has exactly one qualifying successor."""
    path, related, node, stop = [], [], seed, "no-successor"
    seen = {seed}
    while True:
        edges = index.get(node, [])
        related += [
            {"from": node, "ref": s, "confidence": c}
            for k, s, c in edges if k == "related" and qualifies(c)
        ]
        lineage = [(k, s, c) for k, s, c in edges if k in {"evolves", "replaces"}]
        strong = [e for e in lineage if qualifies(e[2])]
        weak = len(lineage) - len(strong)
        # Dedupe: the same edge can be declared in more than one sidecar block.
        uniq = {(k, s): c for k, s, c in strong}
        if not uniq:
            stop = "no-qualifying-successor" if weak else "no-successor"
            break
        if len(uniq) > 1:
            stop = "fan-out"
            break
        (kind, successor), confidence = next(iter(uniq.items()))
        if successor in seen:
            stop = "cycle"
            break
        path.append({"from": node, "kind": kind, "to": successor, "confidence": confidence})
        seen.add(successor)
        node = successor
    return {"seed": seed, "head": node, "path": path, "related": related, "stop_reason": stop}


def title_of(ref: str) -> str:
    try:
        return (get_chunk(ref, REPO).get("title") or "")[:100]
    except Exception:
        return ""


def _decision_topic_maps() -> tuple[dict, dict]:
    """Sidecar is the topic authority: precedence sidecar -> authored, never a union."""
    import collections

    from memory_seed.retrieval import load_corpus

    sidecar: dict[str, set[str]] = collections.defaultdict(set)
    authored: dict[str, set[str]] = {}
    for chunk in load_corpus(REPO, "decision"):
        entry = (chunk.chunk_id or "").split(":")[0]
        for ordinal, slug in (getattr(chunk, "inferred_decision_topics", None) or ()):
            sidecar[f"{entry}:{ordinal}"].add(slug)
        if chunk.chunk_id:
            authored[chunk.chunk_id] = set(getattr(chunk, "topics", None) or ())
    return sidecar, authored


_SIDECAR_TOPICS, _AUTHORED_TOPICS = None, None


def decision_topics(ref: str) -> set[str]:
    global _SIDECAR_TOPICS, _AUTHORED_TOPICS
    if _SIDECAR_TOPICS is None:
        _SIDECAR_TOPICS, _AUTHORED_TOPICS = _decision_topic_maps()
    return _SIDECAR_TOPICS.get(ref) or _AUTHORED_TOPICS.get(ref) or set()


def main() -> int:
    index, total, unnormalised = build_successor_index(REPO)
    print(f"decision-level sidecar edges: {total} | unusable after normalisation: {unnormalised}")

    rows = []
    for record in sorted(iter_adrs(REPO), key=lambda r: r.adr_id):
        proposal = current_proposal(record)
        members = sorted(
            adr_membership(record) | set((proposal.supporting_decisions if proposal else ()) or ())
        )
        walks = [walk(m, index) for m in members if DECISION_REF_RE.fullmatch(m)]
        moved = [w for w in walks if w["path"]]
        related = [r for w in walks for r in w["related"]]
        if not moved and not related:
            continue
        # An ADR head may move automatically only when EVERY step of its chain is authored.
        auto = [w for w in moved if all(s["confidence"] is None for s in w["path"])]
        rows.append({
            "adr_id": record.adr_id,
            "title": record.title,
            "pinned": record.adr_id in PINNED,
            "current_head": record.authoritative_decision,
            "members": members,
            "walks": walks,
            "authored_head": auto[0]["head"] if len(auto) == 1 else None,
            "suggested_heads": [
                {"head": w["head"], "head_title": title_of(w["head"]), "seed": w["seed"],
                 "seed_title": title_of(w["seed"]),
                 "confidences": [s["confidence"] for s in w["path"]]}
                for w in moved if w not in auto
            ],
            "related_refs": sorted({r["ref"] for r in related}),
        })

    (HERE / "lineage-map.json").write_text(json.dumps({"adrs": rows}, indent=1), encoding="utf-8")

    auto_rows = [r for r in rows if not r["pinned"] and r["authored_head"]]
    review_rows = [r for r in rows if not r["pinned"] and r["suggested_heads"]]
    lines = [
        "# ADR lineage review queue", "",
        f"Generated from {total} decision-level link-sidecar edges "
        f"({unnormalised} unusable after normalisation).", "",
        "A head moves automatically only when every step of its chain is AUTHORED. Machine-scored "
        "edges land here instead: the swarm suggests, a human decides. Read both titles before "
        "approving - a 0.75 edge already carried one ADR onto an unrelated concern.", "",
        f"- automatic (authored chain): **{len(auto_rows)}**",
        f"- needs review (machine-suggested): **{len(review_rows)}**",
        f"- pinned, report only: **{sum(1 for r in rows if r['pinned'])}**", "",
    ]
    for r in rows:
        lines.append(f"## {r['adr_id']}{' (PINNED - report only)' if r['pinned'] else ''}")
        lines.append(f"*{r['title']}*")
        lines.append(f"- head now: `{r['current_head']}`")
        for w in r["walks"]:
            if w["path"]:
                chain = " -> ".join(f"{s['kind']} `{s['to']}`"
                                    + (f" ({s['confidence']})" if s["confidence"] is not None else " (authored)")
                                    for s in w["path"])
                lines.append(f"- `{w['seed']}` => {chain}")
                lines.append(f"    - from: {title_of(w['seed'])}")
                lines.append(f"    - to:   {title_of(w['head'])}")
                # Topic agreement ANNOTATES rather than gates (see topic_candidates.py for why
                # every granularity fails as a gate). Shared topics support a hop; no shared
                # topic is the concern-drift smell that the bad 0.75 hop showed.
                seed_t, head_t = decision_topics(w["seed"]), decision_topics(w["head"])
                shared = sorted(seed_t & head_t)
                lines.append(
                    f"    - topics: {'shared ' + ', '.join(shared) if shared else 'NO OVERLAP - check concern drift'}"
                    f"  ({', '.join(sorted(seed_t)) or 'none'} vs {', '.join(sorted(head_t)) or 'none'})"
                )
            else:
                lines.append(f"- `{w['seed']}` unmoved ({w['stop_reason']})")
        for ref in r["related_refs"]:
            lines.append(f"- related: `{ref}` - {title_of(ref)}")
        lines.append("")
    (HERE / "LINEAGE-REVIEW.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nADRs with lineage or related edges: {len(rows)}")
    print(f"  automatic (authored chain): {len(auto_rows)}")
    print(f"  needs review (machine-suggested): {len(review_rows)}")
    print(f"  pinned (report only): {sum(1 for r in rows if r['pinned'])}")
    print("\nwrote lineage-map.json and LINEAGE-REVIEW.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
