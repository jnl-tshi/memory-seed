"""Real-corpus validation of decision-granularity retrieval.

Everything in the 2026-08-05 retrieval change was validated on a 7-entry fixture store. This
measures the same properties on the live corpus (~832 entries / ~1,234 decision chunks), where the
questions are different in kind:

  1. Does the relevance band DISCRIMINATE at scale, or saturate? On the small store every result
     came back `strong`, which is a non-signal. RELEVANCE_FLOOR and the strong-ratio were chosen
     against that store, so this is a calibration check, not a confirmation run.
  2. What does a search actually COST in tokens, decision vs entry? The 2.3k/3.6k figures were
     estimated from character counts over chunk text, not measured over real payloads.
  3. Does decision granularity keep the RIGHT answer at rank 1 more often than entry granularity?
     Expected answers are derived mechanically from lifecycle structure - a superseded decision's
     live replacement is a known-correct target - so nothing is hand-labelled and nothing is tuned
     against the queries it scores.

No model spend: lexical ranking only (`semantic_enabled=False`) so the numbers are deterministic
and reproducible, matching the ranking-ab convention of using lexical as the stable baseline.

Usage:
  python experiments/decision-retrieval-scale/measure.py [--top-k 8] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from memory_seed.retrieval import (  # noqa: E402
    RELEVANCE_FLOOR,
    RELEVANCE_STRONG_RATIO,
    search_memory,
)
from memory_seed.semantic_cache import (  # noqa: E402
    build_related_entry_graph,
    extract_memory_chunks,
    replacing_lineage_heads,
)

# Queries spanning the shapes the store is actually asked: a named artifact, a lifecycle question,
# a person/role question, a mechanism question, and two that should find nothing.
PROBE_QUERIES = [
    "why does the commit hook stamp a Memory-Entry trailer",
    "how are topics validated at write time",
    "what is the retrieval specification",
    "supersession damping ranking",
    "who owns the release process",
    "worktree guard root checkout",
    "decision level topics sidecar",
    "semantic embedding provider fallback",
    "quantum error correction surface codes",   # expect: nothing
    "recipe for sourdough starter hydration",   # expect: nothing
]


def band_and_cost(cwd: Path, granularity: str, top_k: int) -> dict:
    bands: Counter = Counter()
    no_match = 0
    payload_chars: list[int] = []
    per_query = []
    for query in PROBE_QUERIES:
        payload = search_memory(
            query, cwd, top_k=top_k, granularity=granularity, semantic_enabled=False
        )
        results = payload["results"]
        for row in results:
            bands[row.get("relevance", "?")] += 1
        if payload.get("no_match_above_threshold"):
            no_match += 1
        served = sum(len(r.get("excerpt") or "") for r in results)
        payload_chars.append(served)
        per_query.append(
            {
                "query": query,
                "results": len(results),
                "served_chars": served,
                "bands": Counter(r.get("relevance") for r in results),
                "no_match": bool(payload.get("no_match_above_threshold")),
                "top_score": round(results[0]["score"], 2) if results else 0.0,
            }
        )
    return {
        "granularity": granularity,
        "bands": dict(bands),
        "no_match_queries": no_match,
        "served_chars": payload_chars,
        "per_query": per_query,
    }


def lifecycle_targets(cwd: Path, limit: int = 25) -> list[tuple[str, str, str]]:
    """(query, superseded_entry_id, expected_live_head) triples derived from real lifecycle edges.

    Querying a retired decision's own title should surface its live replacement - that is the
    behaviour supersession damping and the successor boost exist to produce, so it is a fair
    mechanical target that predates today's change.
    """
    chunks = extract_memory_chunks(cwd, granularity="entry")
    graph = build_related_entry_graph(cwd, chunks=chunks)
    by_id = {c.entry_id: c for c in chunks if c.entry_id}
    triples = []
    for node in graph.values():
        if not node.replaced_by:
            continue
        heads = replacing_lineage_heads(graph, node.entry_id)
        chunk = by_id.get(node.entry_id)
        if not heads or chunk is None or not chunk.entry_title:
            continue
        title = chunk.entry_title.split(" - ", 1)[-1].strip()
        if len(title.split()) < 3:
            continue
        triples.append((title, node.entry_id, heads[0]))
        if len(triples) >= limit:
            break
    return triples


def top_rank_of(results: list[dict], entry_id: str) -> int | None:
    for index, row in enumerate(results, start=1):
        if row.get("entry_id") == entry_id:
            return index
    return None


def lifecycle_stability(cwd: Path, top_k: int) -> dict:
    triples = lifecycle_targets(cwd)
    out: dict[str, dict] = {}
    for granularity in ("entry", "decision"):
        head_at_1 = head_in_k = measured = 0
        for query, _retired, head in triples:
            results = search_memory(
                query, cwd, top_k=top_k, granularity=granularity, semantic_enabled=False
            )["results"]
            rank = top_rank_of(results, head)
            measured += 1
            if rank == 1:
                head_at_1 += 1
            if rank is not None:
                head_in_k += 1
        out[granularity] = {"n": measured, "head_at_1": head_at_1, "head_in_top_k": head_in_k}
    out["queries"] = len(triples)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--json", dest="json_out", default=None)
    args = parser.parse_args()

    cwd = REPO_ROOT
    entry_chunks = extract_memory_chunks(cwd, granularity="entry")
    decision_chunks = extract_memory_chunks(cwd, granularity="decision")
    print(f"corpus: {len(entry_chunks)} entries, {len(decision_chunks)} decision chunks")
    print(f"band rule: strong >= {RELEVANCE_FLOOR} and >= {RELEVANCE_STRONG_RATIO:.0%} of top\n")

    report: dict = {
        "entries": len(entry_chunks),
        "decision_chunks": len(decision_chunks),
        "relevance_floor": RELEVANCE_FLOOR,
        "strong_ratio": RELEVANCE_STRONG_RATIO,
        "top_k": args.top_k,
    }

    print("=== 1/2. relevance bands + served payload size ===")
    for granularity in ("entry", "decision"):
        measured = band_and_cost(cwd, granularity, args.top_k)
        report[granularity] = measured
        chars = measured["served_chars"]
        total = sum(measured["bands"].values()) or 1
        strong_pct = 100.0 * measured["bands"].get("strong", 0) / total
        print(
            f"{granularity:9} bands={measured['bands']} "
            f"strong={strong_pct:.0f}% no_match_queries={measured['no_match_queries']}/"
            f"{len(PROBE_QUERIES)}"
        )
        print(
            f"          served chars: mean {int(statistics.mean(chars))} "
            f"median {int(statistics.median(chars))} max {max(chars)} "
            f"(~{int(statistics.mean(chars))//4} tokens mean)"
        )

    print("\n=== 3. lifecycle top-1 stability (live head for a retired decision's title) ===")
    stability = lifecycle_stability(cwd, args.top_k)
    report["lifecycle"] = stability
    print(f"queries derived from real supersession edges: {stability['queries']}")
    for granularity in ("entry", "decision"):
        row = stability[granularity]
        if row["n"]:
            print(
                f"  {granularity:9} head@1 {row['head_at_1']}/{row['n']} "
                f"({100*row['head_at_1']/row['n']:.0f}%)  head@k {row['head_in_top_k']}/{row['n']}"
            )

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(report, indent=2, default=str), encoding="utf-8"
        )
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
