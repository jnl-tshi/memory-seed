"""Build attachment payloads for founding-only ADRs from SEMANTIC recall, with bodies inline.

Replaces the topic-area recall that produced the first attachment payload. That earlier list was
measured to under-recall: for `adr_branch_session_fuse` the true founding decision was never
offered at all, and every worker that read it correctly answered "none".

`recall_probe.py` measured the replacement against the eight ADRs that already carry a real head:

    undamped, full query   8/8 at K=5     (leaky - the record quotes its own attached decision)
    leak-free (title+topics only)   5/8 @5, 7/8 @10, 8/8 @25

The leak-free arm is the honest lower bound for these 15 - and a strict one, since they carry a
long verbatim founding quote where the attached eight carry none. K=25 is chosen from it.
`supersession_damping` is OFF: it down-ranks anything carrying a `replaced_by`, and a FOUNDING
decision is by construction the most-superseded node in its chain.

Each candidate ships with its decision BODY excerpt inline. Two failures that buys off: workers
spent 30+ tool calls opening every candidate to learn what it said, and the campaign's most common
grounding failure is quoting the title because the body was never in front of them.

Usage:  python experiments/adr-campaign/build_attach_payload.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from memory_seed.adr import adr_membership, iter_adrs, replay_adr  # noqa: E402
from memory_seed.retrieval import get_chunk, search_memory  # noqa: E402

from recall_probe import concern_query  # noqa: E402

TOP_K = 25
BODY_CHARS = 420
PER_BATCH = 3


def norm(text: str) -> str:
    return " ".join(text.split())


def body_excerpt(ref: str) -> tuple[str, str]:
    """(title, body-only excerpt). The title is stripped so a worker cannot copy it as a quote."""
    chunk = get_chunk(ref, REPO)
    title = norm(chunk.get("title") or "")
    body = norm(chunk.get("text") or "")
    if title and body.startswith(title):
        body = body[len(title):].strip()
    elif title:
        body = body.replace(title, " ").strip()
    return title, body[:BODY_CHARS]


def main() -> int:
    claimed: dict[str, set[str]] = {}
    targets = []
    for record in iter_adrs(REPO):
        for ref in adr_membership(record):
            claimed.setdefault(ref, set()).add(record.adr_id)
        head = replay_adr(record).authoritative_decision or ""
        if head.startswith("founding:"):
            targets.append(record)
    print(f"founding-only ADRs: {len(targets)}")

    payload = []
    for record in targets:
        query = concern_query(record)
        results = search_memory(
            query, REPO, top_k=TOP_K, recency_enabled=False,
            granularity="decision", supersession_damping=False,
        )["results"]
        candidates = []
        for hit in results:
            ref = hit.get("chunk_id") or ""
            if ":d" not in ref:  # ADR refs are always <entry>:dN; never offer a bare entry
                continue
            try:
                title, body = body_excerpt(ref)
            except Exception:
                continue
            candidates.append({
                "ref": ref,
                "title": title,
                "body": body,
                "claimed_by": sorted(claimed.get(ref, ())),
            })
        payload.append({
            "adr_id": record.adr_id,
            "title": record.title,
            "concern": norm(record.current_decision or ""),
            "founding_head": replay_adr(record).authoritative_decision,
            "candidates": candidates,
        })
        print(f"  {record.adr_id:<36} {len(candidates)} candidates")

    (HERE / "attach-payload-v2.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    for i in range(0, len(payload), PER_BATCH):
        (HERE / f"attach-v2-batch-{i // PER_BATCH}.json").write_text(
            json.dumps(payload[i:i + PER_BATCH], indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"batches: {-(-len(payload) // PER_BATCH)} of up to {PER_BATCH} ADRs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
