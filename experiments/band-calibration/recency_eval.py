"""Evaluate recency variants against BOTH recall and the lifecycle guard.

Recency multiplies the match score by `max(floor, exp(-lambda * age_days))`. Measured cost: it
removes correct answers from the top 8. Measured urgency: the corpus is 80 days old at most, so the
current penalty spread is only 2.2x and it is already costing recall; past ~190 days entries hit the
0.15 floor and the spread becomes 6.7x. The damage grows as the archive ages, which is backwards for
a decision store.

Every variant here is expressible through existing parameters, so nothing is reimplemented:

  current    lambda 0.01, floor 0.15    shipped
  off        recency_enabled=False      upper bound on the recall win
  floor_05   lambda 0.01, floor 0.50    caps the penalty at 2x permanently, one constant
  lambda_low lambda 0.002, floor 0.15   half-life 69d -> ~347d, still unbounded as the archive ages
  tiebreak   lambda 0.01, floor 0.98    compresses the whole range into 2%, so recency orders
                                        near-equals and never overrides a clearly better match

**The guard is the point, not the recall number.** Recency is partly doing supersession's job by
accident: a retired decision is older than the entry that replaced it, so age demotes it whether or
not supersession damping does. Weakening recency could let retired decisions climb back above their
replacements while the recall column looks like a clean win. The lifecycle arm measures exactly that,
per edge kind, and a recall gain that costs `beats_rival` is a rejected candidate.

Usage:
  python experiments/band-calibration/recency_eval.py --corpus <root> [--arm semantic]
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

TOP_K = 8
PRODUCTION_RANKING = {"supersession_damping": True, "replacing_successor_boost": True}

VARIANTS: dict[str, dict] = {
    "current": {"recency_enabled": True, "lambda_days": 0.01, "recency_floor": 0.15},
    "off": {"recency_enabled": False, "lambda_days": 0.01, "recency_floor": 0.15},
    "floor_05": {"recency_enabled": True, "lambda_days": 0.01, "recency_floor": 0.50},
    "lambda_low": {"recency_enabled": True, "lambda_days": 0.002, "recency_floor": 0.15},
    "tiebreak": {"recency_enabled": True, "lambda_days": 0.01, "recency_floor": 0.98},
}


def entry_order(query: str, cwd: Path, chunks: list, provider, variant: dict, k: int) -> list[str]:
    ranked = rank_session_memory(
        query, cwd, top_k=max(k * 4, 1), chunks=chunks, embedding_provider=provider,
        **PRODUCTION_RANKING, **variant,
    )
    order: list[str] = []
    for row in ranked:
        entry_id = row.chunk.entry_id
        if entry_id and entry_id not in order:
            order.append(entry_id)
    return order


def measure(rows: list[dict], cwd: Path, chunks: list, provider, variant: dict) -> dict:
    recall: dict[str, dict] = {}
    life = {
        "replaces": {"n": 0, "surfaced": 0, "beats_rival": 0},
        "evolves": {"n": 0, "head_surfaced": 0},
    }
    for row in rows:
        order = entry_order(row["query"], cwd, chunks, provider, variant, TOP_K)
        window = order[:TOP_K]
        kind = row.get("edge_kind")
        if kind == "replaces":
            life["replaces"]["n"] += 1
            accepted = set(row["accepted"])
            if accepted & set(window):
                life["replaces"]["surfaced"] += 1
            head_pos = min((order.index(i) for i in accepted if i in order), default=None)
            rival_pos = order.index(row["rival"]) if row["rival"] in order else None
            if head_pos is not None and (rival_pos is None or head_pos < rival_pos):
                life["replaces"]["beats_rival"] += 1
        elif kind == "evolves":
            life["evolves"]["n"] += 1
            if (set(row["accepted"]) - {row["origin"]}) & set(window):
                life["evolves"]["head_surfaced"] += 1
        else:
            bucket = recall.setdefault(row["source"], {"n": 0, "at_1": 0, "at_k": 0})
            bucket["n"] += 1
            expected = row.get("expected")
            if expected and window and window[0] == expected:
                bucket["at_1"] += 1
            if expected in window:
                bucket["at_k"] += 1
    return {"recall": recall, "lifecycle": life}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default=str(REPO_ROOT))
    parser.add_argument("--arm", choices=["lexical", "semantic"], default="lexical")
    parser.add_argument("--json", dest="json_out", default=str(HERE / "recency-eval.json"))
    args = parser.parse_args()

    cwd = Path(args.corpus)
    chunks = load_corpus(cwd, "decision")
    provider = None
    if args.arm == "semantic":
        from memory_seed.retrieval import resolve_semantic_provider

        from blend_eval import CachingProvider

        inner, name, _ = resolve_semantic_provider("probe", None, enabled=True)
        provider = CachingProvider(inner)
        print(f"provider: {name} (cached)")
    print(f"corpus: {cwd} ({len(chunks)} decision chunks), arm={args.arm}\n")

    rows = labels_mod.build(cwd)
    report = {}
    header = f"{'variant':>11} | {'P_terms3':>10} {'P_terms7':>10} {'P_terms15':>10} {'P_title':>10} | {'beats_rival':>12} {'evolves@8':>10}"
    print(header)
    print("-" * len(header))
    for name, variant in VARIANTS.items():
        result = measure(rows, cwd, chunks, provider, variant)
        report[name] = {"params": variant, **result}
        r, life = result["recall"], result["lifecycle"]

        def cell(source):
            row = r.get(source)
            return f"{row['at_k']:>3}/{row['n']:<3}" if row else "   -   "

        rep = life["replaces"]
        evo = life["evolves"]
        print(
            f"{name:>11} | {cell('P_terms3'):>10} {cell('P_terms7'):>10} {cell('P_terms15'):>10} "
            f"{cell('P_title'):>10} | {rep['beats_rival']:>5}/{rep['n']:<6} "
            f"{evo['head_surfaced']:>4}/{evo['n']:<5}"
        )

    Path(args.json_out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {args.json_out}")
    print("\nA recall gain that costs beats_rival is a rejected candidate, not a trade.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
