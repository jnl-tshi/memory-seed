"""Lifecycle guard for ranking changes - the check F2 exists to not break.

Recency is partly doing supersession's job by accident: a retired decision is older than the entry
that replaced it, so the age penalty demotes it whether or not supersession damping does. Weakening
recency (F2) could therefore let retired decisions climb back above their replacements while the
recall numbers look like a clean win.

Two metrics, kept apart because the edge kinds mean different things:

  replaces   The replacement must SURFACE for the retired title, and must OUTRANK the entry it
             retired. Both are scored. `beats_rival` is the one that detects the F2 regression.
  evolves    The original stays valid and is expected to rank first - that is correct behaviour,
             not a failure. Only `head_surfaced` is scored: does the newer form also appear.

Pooling the two would score correct `evolves` behaviour as a miss and manufacture a regression that
is not there.

Usage:
  python experiments/band-calibration/lifecycle_guard.py [--top-k 8] [--arm lexical|semantic]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(HERE))

from memory_seed.retrieval import load_corpus  # noqa: E402
from memory_seed.semantic_cache import rank_session_memory  # noqa: E402

import labels as labels_mod  # noqa: E402


# `rank_session_memory` defaults these OFF; `search_memory` - the production path - turns them ON
# (retrieval.py:148-150). Calling the ranker directly without them measures a configuration nobody
# runs, and it silently changes the answer for exactly the replaced entries this guard is about.
PRODUCTION_RANKING = {
    "supersession_damping": True,
    "replacing_successor_boost": True,
}


def rank_ids(query: str, cwd: Path, chunks: list, provider, top_k: int) -> list[str]:
    """Distinct entry ids in rank order.

    Deduplicated because under decision granularity one entry can occupy several slots, and the
    question here is about entries beating entries, not chunks beating chunks.
    """
    ranked = rank_session_memory(
        query,
        cwd,
        top_k=max(top_k * 4, 1),
        chunks=list(chunks),
        embedding_provider=provider,
        **PRODUCTION_RANKING,
    )
    seen: list[str] = []
    for row in ranked:
        entry_id = row.chunk.entry_id
        if entry_id and entry_id not in seen:
            seen.append(entry_id)
    return seen


def measure(cwd: Path, top_k: int = 8, provider=None) -> dict:
    chunks = load_corpus(cwd, "decision")
    rows = [r for r in labels_mod.build(cwd) if r.get("edge_kind")]

    out: dict = {"top_k": top_k, "replaces": {}, "evolves": {}}

    replaces = [r for r in rows if r["edge_kind"] == "replaces"]
    surfaced = beats = 0
    for row in replaces:
        order = rank_ids(row["query"], cwd, chunks, provider, top_k)
        window = order[:top_k]
        accepted = set(row["accepted"])
        if accepted & set(window):
            surfaced += 1
        # Rank comparison over the FULL order, not the window: if both fall outside the top-k the
        # relative question is still answerable, and treating "neither present" as a pass would
        # hide the regression.
        head_pos = min((order.index(i) for i in accepted if i in order), default=None)
        rival_pos = order.index(row["rival"]) if row["rival"] in order else None
        if head_pos is not None and (rival_pos is None or head_pos < rival_pos):
            beats += 1
    out["replaces"] = {
        "n": len(replaces),
        "head_surfaced": surfaced,
        "beats_rival": beats,
    }

    evolves = [r for r in rows if r["edge_kind"] == "evolves"]
    head_in_k = origin_in_k = 0
    for row in evolves:
        window = rank_ids(row["query"], cwd, chunks, provider, top_k)[:top_k]
        # Only the newer form is scored. The origin supplied the query text, so its presence is
        # self-retrieval and says nothing about lifecycle surfacing - it is counted separately as a
        # sanity reading, never folded into the metric.
        heads = set(row["accepted"]) - {row["origin"]}
        if heads & set(window):
            head_in_k += 1
        if row["origin"] in window:
            origin_in_k += 1
    out["evolves"] = {
        "n": len(evolves),
        "head_surfaced": head_in_k,
        "origin_surfaced": origin_in_k,
    }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--arm", choices=["lexical", "semantic"], default="lexical")
    parser.add_argument("--json", dest="json_out", default=None)
    parser.add_argument("--corpus", default=str(REPO_ROOT),
                        help="corpus root; point at the frozen snapshot so before/after "
                             "comparisons cannot absorb drift from concurrent sessions")
    args = parser.parse_args()

    provider = None
    if args.arm == "semantic":
        from memory_seed.retrieval import resolve_semantic_provider

        provider, name, _ = resolve_semantic_provider("probe", None, enabled=True)
        print(f"arm: semantic ({name})")
    else:
        print("arm: lexical")

    print(f"corpus: {args.corpus}")
    report = measure(Path(args.corpus), top_k=args.top_k, provider=provider)
    rep, evo = report["replaces"], report["evolves"]
    print(f"\nreplaces  n={rep['n']}")
    print(f"  replacement surfaced in top-{args.top_k}: {rep['head_surfaced']}/{rep['n']}")
    print(f"  replacement outranks the retired entry: {rep['beats_rival']}/{rep['n']}   <- F2 guard")
    print(f"\nevolves   n={evo['n']}")
    print(f"  newer form surfaced in top-{args.top_k}: {evo['head_surfaced']}/{evo['n']}")
    print(f"  (origin also present: {evo['origin_surfaced']}/{evo['n']} - self-retrieval, not scored)")
    print("\n(the two are never pooled: for evolves the original outranking its head is correct)")

    out = args.json_out or str(HERE / f"lifecycle-guard-{args.arm}.json")
    report["arm"] = args.arm
    Path(out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
