"""Is the paraphrase-recall failure caused by the semantic blend weight?

`rank_session_memory` scores `lexical + 3.0 * cosine`. Cosine is bounded by 1, so a PERFECT
semantic match contributes 3.0 - less than one heading-path term match (6.0) and a quarter of one
tag match (12.0). Turning semantic ranking on therefore cannot reorder anything that differs by
more than three lexical points, which is most things.

The band-calibration run showed exactly that signature: paraphrase queries recovered the right
entry in the top 8 in 63/120 cases with semantic OFF and 63/120 with it ON. Identical.

This sweeps the weight and measures whether recall is recoverable at all, or whether the embedding
simply carries no usable signal for these queries. Corpus embeddings are computed once and reused,
so the sweep is cheap.

Usage:
  python experiments/band-calibration/semantic_weight.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(HERE))

from memory_seed.retrieval import resolve_semantic_provider  # noqa: E402
from memory_seed.semantic_cache import (  # noqa: E402
    _cosine_similarity,
    _lexical_score,
    _query_terms,
    extract_memory_chunks,
)

import labels as labels_mod  # noqa: E402

WEIGHTS = [0.0, 3.0, 10.0, 30.0, 60.0, 120.0]
TOP_K = 8


def main() -> int:
    cwd = REPO_ROOT
    chunks = extract_memory_chunks(cwd, granularity="decision")
    provider, name, _ = resolve_semantic_provider("probe", None, enabled=True)
    if provider is None:
        raise SystemExit("no semantic provider")
    print(f"provider: {name}")
    print(f"corpus: {len(chunks)} decision chunks")

    # Embed the corpus once. The per-query cost then collapses to one embedding plus dot products.
    corpus_vectors = provider.embed([c.text for c in chunks])

    rows = labels_mod.build(cwd)
    positives = [r for r in rows if r["source"] == "P_terms"]
    negatives = [r for r in rows if r["expected"] is None]
    print(f"paraphrase positives: {len(positives)}  negatives: {len(negatives)}\n")

    query_texts = [r["query"] for r in positives + negatives]
    query_vectors = provider.embed(query_texts)

    # Precompute the two components per (query, chunk) so the sweep only changes the blend.
    lex: list[list[float]] = []
    cos: list[list[float]] = []
    for index, row in enumerate(positives + negatives):
        terms = _query_terms(row["query"])
        lex.append([_lexical_score(terms, c)[0] for c in chunks])
        qv = query_vectors[index]
        cos.append([_cosine_similarity(qv, v) for v in corpus_vectors])

    n_pos = len(positives)
    share = [
        statistics.mean(
            [3.0 * max(c, 0.0) / (l + 3.0 * max(c, 0.0)) for l, c in zip(lex[i], cos[i]) if l > 0]
            or [0.0]
        )
        for i in range(n_pos)
    ]
    print(f"semantic share of match_score at the shipped weight 3.0: "
          f"{100*statistics.mean(share):.1f}% (mean over scoring chunks)\n")

    print(f"{'weight':>8} {'answer@1':>10} {'answer@8':>10}   {'neg top-1 is noise':>20}")
    report = []
    for weight in WEIGHTS:
        at1 = ink = 0
        for i, row in enumerate(positives):
            scored = [
                (l + weight * max(c, 0.0), chunks[j].entry_id)
                for j, (l, c) in enumerate(zip(lex[i], cos[i]))
            ]
            scored.sort(key=lambda t: -t[0])
            top_ids: list[str] = []
            for _score, entry_id in scored:
                if entry_id and entry_id not in top_ids:
                    top_ids.append(entry_id)
                if len(top_ids) >= TOP_K:
                    break
            if top_ids and top_ids[0] == row["expected"]:
                at1 += 1
            if row["expected"] in top_ids:
                ink += 1
        report.append({"weight": weight, "answer_at_1": at1, "answer_at_k": ink, "n": n_pos})
        print(f"{weight:>8.0f} {at1:>6}/{n_pos:<3} {ink:>6}/{n_pos:<3}")

    (HERE / "semantic-weight-sweep.json").write_text(
        json.dumps({"weights": report, "n_positives": n_pos,
                    "semantic_share_at_3": statistics.mean(share)}, indent=2),
        encoding="utf-8",
    )
    print(f"\nwrote {HERE / 'semantic-weight-sweep.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
