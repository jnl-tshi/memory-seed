"""Measure recall@K for semantic candidate generation, held out against attached ADRs.

The topic-recall candidate lists offered to the attachment swarm under-recalled: for
`adr_branch_session_fuse` the true founding decision (`mse_81v7vk4x5ys3k2n0:d1`) was never on the
list, and a semantic query over the ADR's own concern text puts it first by a wide margin. Before
rebuilding 15 payloads on that observation, this measures it on ADRs that ALREADY carry a real
attached decision - the held-out set - so K is chosen rather than guessed.

The query is built MECHANICALLY from the record (title + founding quote + derived Decision/Why) so
the same generator can run unattended in S2/S4; a hand-written query proves nothing that transfers.

Two arms, because `supersession_damping` defaults ON and down-ranks anything carrying a
`replaced_by` - and a FOUNDING decision is by construction the most-superseded node in its chain,
so the damper works against exactly what this hunts.

Usage:  python experiments/adr-campaign/recall_probe.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from memory_seed.adr import iter_adrs, replay_adr, current_proposal, proposal_for  # noqa: E402
from memory_seed.retrieval import search_memory  # noqa: E402

KS = (5, 10, 15, 25, 40)
TOP_K = max(KS)


def concern_query(record, *, leak_free: bool = False) -> str:
    """Mechanical query text: title, topics, founding quote, and the derived decision/why.

    `leak_free` drops the decision/why prose. That matters: on an ADR that already carries an
    attached head, `revise_adr` copied THAT decision's own text into the record, so including it
    queries the corpus with the answer. The 15 founding-only ADRs have no such text, so the
    leak-free arm is the honest proxy for them - and a strict lower bound, since those 15 do carry
    a long verbatim founding quote where the attached eight carry none.
    """
    parts = [record.title or record.adr_id.replace("adr_", "").replace("_", " ")]
    parts.extend(record.topics or ())
    seen = set()
    for event in record.events:
        if event.founding_quote and event.founding_quote not in seen:
            seen.add(event.founding_quote)
            parts.append(event.founding_quote)
        if leak_free:
            continue
        for field in (event.decision, event.why):
            if field and field not in seen and not field.startswith("See the authoritative"):
                seen.add(field)
                parts.append(field)
    return " ".join(p for p in parts if p)


def head_ref(record) -> str | None:
    state = replay_adr(record)
    ref = state.authoritative_decision
    if not ref or ref.startswith("founding:"):
        return None
    return ref


def ranked_refs(query: str, damping: bool) -> list[str]:
    payload = search_memory(
        query, REPO, top_k=TOP_K, recency_enabled=False, granularity="decision",
        supersession_damping=damping,
    )
    return [r.get("chunk_id") or r.get("id") or "" for r in payload["results"]]


def main() -> int:
    records = list(iter_adrs(REPO))
    attached = [(r, head_ref(r)) for r in records]
    attached = [(r, ref) for r, ref in attached if ref]
    print(f"ADRs: {len(records)}; with a real attached head: {len(attached)}")

    rows = []
    for record, truth in attached:
        full = concern_query(record)
        bare = concern_query(record, leak_free=True)
        row = {"adr_id": record.adr_id, "truth": truth,
               "query_chars": len(full), "leak_free_chars": len(bare)}
        for arm, query, damping in (
            ("damped", full, True),
            ("undamped", full, False),
            ("leakfree", bare, False),
        ):
            refs = ranked_refs(query, damping)
            row[arm] = refs.index(truth) + 1 if truth in refs else None
        rows.append(row)
        print(f"  {record.adr_id:<36} truth={truth:<24} "
              f"damped={row['damped']} undamped={row['undamped']} leakfree={row['leakfree']}")

    print()
    for arm in ("damped", "undamped", "leakfree"):
        ranks = [r[arm] for r in rows]
        line = [f"{arm:<9}"]
        for k in KS:
            hit = sum(1 for x in ranks if x is not None and x <= k)
            line.append(f"@{k}={hit}/{len(ranks)} ({hit / len(ranks):.0%})")
        print("  ".join(line))

    (HERE / "recall-probe.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
