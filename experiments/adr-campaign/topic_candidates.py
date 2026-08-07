"""Find candidate session decisions for an ADR that has none - a RECALL tool, not a ranker.

JNL's framing, and the measurement agrees: topics exist here to bound which decisions a swarm
should even consider. **All 5 of JNL's approved picks were surfaced from ~1050 topiced decisions**,
taking the search space to five per ADR with the right answer inside every time. That is the job.

What topics do NOT do is choose within that set. Against those same 5 labelled picks, with 5
candidates each (random = mean rank 3.0): shared-topic count 3.00, IDF rarity 2.80, semantic 2.20,
IDF+semantic 2.80. Every scorer sits at chance. What selected correctly was a worker READING the
decision body. So this file surfaces and labels; it never orders by confidence it does not have.

Two channels feed the candidate set:

- **Direct topic match** - the decision shares a topic with the ADR.
- **Pair expansion** - the decision's area is a high-lift partner of one of the ADR's areas, from
  the affinity table in `pair_affinity.py` (e.g. `schema` <-> `lifecycle-edges` at lift 11.1).
  These are labelled `[pair-expanded]` with their lift and n so a reviewer can see how they
  arrived. Recall widening only; see `pair_affinity.py` for why it may never gate or rank.

Topics are read from the DECLARED axis channel via `audit_link_topic_join.decision_axes()` -
sidecar `area:`/`activity:` sub-keys, never `proposed_topics`, which are vocabulary requests rather
than attributions. Emits ATTACHMENT-REVIEW.md. Writes nothing.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from audit_link_topic_join import decision_axes  # noqa: E402
from memory_seed.adr import adr_membership, current_proposal, iter_adrs  # noqa: E402
from memory_seed.retrieval import load_corpus  # noqa: E402
from pair_affinity import affinity_table, expansion_map  # noqa: E402

TOP_N = 5


def topic_maps(chunks):
    sidecar: dict[str, set[str]] = collections.defaultdict(set)
    authored: dict[str, set[str]] = {}
    titles: dict[str, str] = {}
    for chunk in chunks:
        entry = (chunk.chunk_id or "").split(":")[0]
        for ordinal, slug in (getattr(chunk, "inferred_decision_topics", None) or ()):
            sidecar[f"{entry}:{ordinal}"].add(slug)
        if chunk.chunk_id:
            authored[chunk.chunk_id] = set(getattr(chunk, "topics", None) or ())
            titles[chunk.chunk_id] = (chunk.title or "").strip()[:80]
    return sidecar, authored, titles


def main() -> int:
    chunks = load_corpus(REPO, "decision")
    sidecar, authored, titles = topic_maps(chunks)
    # Pair-affinity EXPANSION - recall only. See pair_affinity.py for why this may never gate or
    # rank: as a gate it scored the known-bad hop highest (leakage), and as a ranker every
    # topic-derived scorer sat at chance.
    area_map, _activity = decision_axes()
    expand = expansion_map(affinity_table())

    def topics_of(ref: str) -> set[str]:
        return sidecar.get(ref) or authored.get(ref) or set()

    lines = [
        "# ADR attachment candidates (topic-matched)", "",
        "Decisions matched by topics shared with the ADR. Topics come from the decision-level "
        "sidecar, which is the authority (precedence sidecar -> authored, never a union).", "",
        "**These are candidates, not a ranking.** Topic overlap earns its place on RECALL - all 5 "
        "of JNL's approved picks were surfaced from ~1050 topiced decisions - but every "
        "topic-derived scorer ranked those picks at chance. Read the decision body to choose.", "",
        "Entries marked **[pair-expanded]** share no topic with the ADR; they arrived through a "
        "high-lift area coupling measured across the corpus (e.g. `schema` <-> `lifecycle-edges`). "
        "That is a recall widening only - treat it as one more thing worth reading.", "",
        "Attaching a decision means a `revise` event, which moves the ADR head, so nothing here is "
        "applied without being named.", "",
    ]
    unattached = matched = expanded_total = 0
    for record in sorted(iter_adrs(REPO), key=lambda r: r.adr_id):
        proposal = current_proposal(record)
        members = adr_membership(record) | set(
            (proposal.supporting_decisions if proposal else ()) or ()
        )
        if members or not record.topics:
            continue
        unattached += 1
        wanted = set(record.topics)
        ranked = sorted(
            ((len(wanted & topics_of(ref)), ref) for ref in titles if wanted & topics_of(ref)),
            key=lambda pair: (-pair[0], pair[1]),
        )[:TOP_N]
        # Partner areas of anything this ADR is about, minus what direct matching already found.
        partners: dict[str, tuple[float, int]] = {}
        for slug in wanted:
            for partner, (lift, count) in expand.get(slug, {}).items():
                if partner in wanted:
                    continue
                if partner not in partners or lift > partners[partner][0]:
                    partners[partner] = (lift, count)
        direct = {ref for _n, ref in ranked}
        expanded = []
        for ref in titles:
            if ref in direct or wanted & topics_of(ref):
                continue
            for slug in area_map.get(ref, ()):
                if slug in partners:
                    expanded.append((partners[slug][0], ref, slug, partners[slug][1]))
                    break
        expanded = sorted(expanded, key=lambda t: (-t[0], t[1]))[:TOP_N]
        expanded_total += len(expanded)
        if not ranked and not expanded:
            continue
        matched += 1
        lines.append(f"## {record.adr_id}")
        lines.append(f"*{record.title}*")
        lines.append(f"- ADR topics: {', '.join(sorted(wanted))}")
        for shared, ref in ranked:
            overlap = ", ".join(sorted(wanted & topics_of(ref)))
            lines.append(f"- `{ref}` ({shared} shared: {overlap})")
            lines.append(f"    - {titles[ref]}")
        for lift, ref, via, count in expanded:
            lines.append(f"- `{ref}` **[pair-expanded]** via `{via}` (lift {lift:.1f}, n={count})")
            lines.append(f"    - {titles[ref]}")
        lines.append("")
    header = [
        f"- ADRs with no attached decision and at least one topic: **{unattached}**",
        f"- of those, with candidates: **{matched}**",
        f"- pair-expanded candidates offered: **{expanded_total}** (recall widening only)", "",
    ]
    (HERE / "ATTACHMENT-REVIEW.md").write_text(
        "\n".join(lines[:4] + header + lines[4:]) + "\n", encoding="utf-8"
    )
    print(f"unattached ADRs with topics: {unattached} | with candidates: {matched}")
    print(f"pair-expanded candidates: {expanded_total}")
    print("wrote ATTACHMENT-REVIEW.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
