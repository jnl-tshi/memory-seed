"""Find candidate session decisions for an ADR by decision-level topic agreement.

JNL's question - "do the topics not allow you to find relevant decision candidates?" - has two
answers, and they differ:

**As a candidate FINDER: yes, and it is the best signal available.** 20 ADRs carry no attached
decision at all, and the swarm that was asked to find them invented refs instead
(`mse_a4282580` for what is really `ms-a4282580`). Ranking real decisions by shared topics recovers
the right ones - `adr_draft_format` surfaces "Use DRAFT for compact decision records";
`adr_entry_id_scheme` surfaces "80-bit generated entry IDs", the decision the swarm hallucinated.
This is recall-oriented work reviewed by a human, which is exactly where topic matching is strong.

**As a hard GATE on lineage hops: no, measured against the 4 known-good authored edges and the 1
known-bad machine edge:**

| granularity | blocks the bad hop | preserves the 3 good authored hops |
|---|---|---|
| leaf slug   | yes | 1 of 3 |
| area axis   | yes | 0 of 3 |
| root area   | NO (`agent-rules` and `skill-architecture` share `control-plane`) | 1 of 3 |

The activity axis is *supposed* to change along a chain - a `bugfix` evolving into a
`feature-build` is normal - and sibling areas like `session-logging`/`session-fuse` are genuinely
adjacent, so leaf matching rejects real evolutions. Root matching is coarse enough to readmit the
cross-concern hop it was meant to stop. n=5, so this is a pattern, not a measurement; it is enough
to say topic agreement should ANNOTATE the lineage review rather than gate it.

Topics come from the sidecar, which is the authority: precedence sidecar -> authored, never a
union (`adr_topic_authority`). Emits ATTACHMENT-REVIEW.md. Writes nothing.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from memory_seed.adr import adr_membership, current_proposal, iter_adrs  # noqa: E402
from memory_seed.retrieval import load_corpus  # noqa: E402

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

    def topics_of(ref: str) -> set[str]:
        return sidecar.get(ref) or authored.get(ref) or set()

    lines = [
        "# ADR attachment candidates (topic-matched)", "",
        "Decisions ranked by topics shared with the ADR. Topics come from the decision-level "
        "sidecar, which is the authority (precedence sidecar -> authored, never a union).", "",
        "Candidates only. Attaching a decision means a `revise` event, which moves the ADR head - "
        "the same stakes as a lineage move - so nothing here is applied without being named.", "",
    ]
    unattached = matched = 0
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
        if not ranked:
            continue
        matched += 1
        lines.append(f"## {record.adr_id}")
        lines.append(f"*{record.title}*")
        lines.append(f"- ADR topics: {', '.join(sorted(wanted))}")
        for shared, ref in ranked:
            overlap = ", ".join(sorted(wanted & topics_of(ref)))
            lines.append(f"- `{ref}` ({shared} shared: {overlap})")
            lines.append(f"    - {titles[ref]}")
        lines.append("")
    header = [
        f"- ADRs with no attached decision and at least one topic: **{unattached}**",
        f"- of those, with candidates: **{matched}**", "",
    ]
    (HERE / "ATTACHMENT-REVIEW.md").write_text(
        "\n".join(lines[:4] + header + lines[4:]) + "\n", encoding="utf-8"
    )
    print(f"unattached ADRs with topics: {unattached} | with candidates: {matched}")
    print("wrote ATTACHMENT-REVIEW.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
