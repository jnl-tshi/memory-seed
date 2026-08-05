"""Evaluate candidate lexical/semantic blends through the REAL ranking path.

The shipped blend is `lexical + 3.0 * cosine`. Cosine is bounded by 1 and one tag-term match is
12.0, so semantic similarity contributes ~21% of the match score and cannot reorder anything
separated by more than three lexical points. Measured effect of turning it on: zero.

Three candidate shapes, evaluated on a held-out split STRATIFIED BY QUERY LENGTH:

  A  additive        lexical + w * cosine            the shipped shape, w swept
  B  per-term        lexical + w * n_terms * cosine  lets the semantic side grow with the query the
                                                    way the lexical side already does
  C  normalised      lexical + w * cosine * lexical_scale, lexical_scale = max lexical this query
                                                    makes the weight relative rather than absolute

Length stratification is the point. The earlier sweep that found w=60 used 7-term queries
throughout, so it measured one point on the axis the additive shape is most suspected of getting
wrong.

Everything runs through `rank_session_memory` with production flags, not a reimplementation - the
recurring failure in this project is a harness that scores differently from the shipped path. The
embedding provider is wrapped in a cache so repeated runs over the same corpus stay affordable.

Usage:
  python experiments/band-calibration/blend_eval.py --corpus <root> [--arm semantic]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(HERE))

from memory_seed import semantic_cache as sc  # noqa: E402
from memory_seed.retrieval import load_corpus, resolve_semantic_provider  # noqa: E402

import labels as labels_mod  # noqa: E402

TOP_K = 8
PRODUCTION_RANKING = {"supersession_damping": True, "replacing_successor_boost": True}

# Swept per shape. A's shipped value is 3.0; B and C are relative so their useful range differs.
CANDIDATES: list[tuple[str, float]] = (
    [("A", w) for w in (3.0, 10.0, 30.0, 60.0, 120.0)]
    + [("B", w) for w in (1.0, 3.0, 6.0, 12.0)]
    + [("C", w) for w in (0.25, 0.5, 1.0, 2.0)]
)


class CachingProvider:
    """Memoise embeddings per text.

    `_semantic_scores` embeds [query, *every chunk text] on every call, so without this each
    candidate would re-embed the whole corpus for every query. The cache makes the corpus a
    one-off cost and leaves the ranking path itself untouched.
    """

    def __init__(self, inner):
        self._inner = inner
        self._cache: dict[str, tuple] = {}

    def embed(self, texts):
        missing = [t for t in texts if t not in self._cache]
        if missing:
            for text, vector in zip(missing, self._inner.embed(missing)):
                self._cache[text] = vector
        return [self._cache[t] for t in texts]


def make_blend(shape: str, weight: float):
    """Return a drop-in replacement for `semantic_cache.blend_match_score`."""
    if shape == "A":
        def blend(lexical, semantic, n_terms):
            return lexical + weight * max(semantic or 0.0, 0.0)
    elif shape == "B":
        def blend(lexical, semantic, n_terms):
            return lexical + weight * max(n_terms, 1) * max(semantic or 0.0, 0.0)
    elif shape == "C":
        def blend(lexical, semantic, n_terms):
            # Relative to this query's own lexical ceiling, set per call below.
            return lexical + weight * _SCALE[0] * max(semantic or 0.0, 0.0)
    else:
        raise ValueError(shape)
    return blend


_SCALE = [1.0]  # shape C's per-query lexical ceiling


def entry_order(query: str, cwd: Path, chunks: list, provider, k: int) -> list[str]:
    ranked = sc.rank_session_memory(
        query, cwd, top_k=max(k * 4, 1), chunks=chunks, embedding_provider=provider,
        **PRODUCTION_RANKING,
    )
    order: list[str] = []
    for row in ranked:
        entry_id = row.chunk.entry_id
        if entry_id and entry_id not in order:
            order.append(entry_id)
    return order


def lexical_ceiling(query: str, cwd: Path, chunks: list) -> float:
    """Top lexical-only score for this query - shape C's scale."""
    ranked = sc.rank_session_memory(
        query, cwd, top_k=1, chunks=chunks, embedding_provider=None, **PRODUCTION_RANKING
    )
    return ranked[0].final_score if ranked else 1.0


def evaluate(rows: list[dict], cwd: Path, chunks: list, provider, shape: str, weight: float) -> dict:
    original = sc.blend_match_score
    sc.blend_match_score = make_blend(shape, weight)
    try:
        by_source: dict[str, list[int | None]] = {}
        for row in rows:
            if shape == "C":
                _SCALE[0] = lexical_ceiling(row["query"], cwd, chunks)
            order = entry_order(row["query"], cwd, chunks, provider, TOP_K)[:TOP_K]
            expected = row.get("expected")
            rank = order.index(expected) + 1 if expected in order else None
            by_source.setdefault(row["source"], []).append(rank)
    finally:
        sc.blend_match_score = original

    out: dict = {"shape": shape, "weight": weight, "by_source": {}}
    for source, ranks in sorted(by_source.items()):
        n = len(ranks)
        out["by_source"][source] = {
            "n": n,
            "at_1": sum(1 for r in ranks if r == 1),
            "at_k": sum(1 for r in ranks if r is not None),
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default=str(REPO_ROOT))
    parser.add_argument("--json", dest="json_out", default=str(HERE / "blend-eval.json"))
    args = parser.parse_args()

    cwd = Path(args.corpus)
    print(f"corpus: {cwd}")
    chunks = load_corpus(cwd, "decision")
    print(f"decision chunks: {len(chunks)}")

    inner, name, _ = resolve_semantic_provider("probe", None, enabled=True)
    provider = CachingProvider(inner)
    print(f"provider: {name} (cached)")

    rows = labels_mod.build(cwd)
    fit, held = labels_mod.split(rows)
    # Paraphrase strata are what the blend is being fitted on; title and negatives are guards.
    para = [r for r in held if r["source"].startswith("P_terms")]
    title = [r for r in held if r["source"] == "P_title"]
    print(f"held-out: {len(para)} paraphrase, {len(title)} title\n")

    print(f"{'shape':>6} {'weight':>7} | " + " ".join(f"{s:>12}" for s in
          ("P_terms3", "P_terms7", "P_terms15", "P_title")) + "   (answer@8)")
    report = []
    for shape, weight in CANDIDATES:
        result = evaluate(para + title, cwd, chunks, provider, shape, weight)
        report.append(result)
        cells = []
        for source in ("P_terms3", "P_terms7", "P_terms15", "P_title"):
            row = result["by_source"].get(source)
            cells.append(f"{row['at_k']:>4}/{row['n']:<3}" if row else "     -   ")
        print(f"{shape:>6} {weight:>7.2f} | " + " ".join(f"{c:>12}" for c in cells))

    Path(args.json_out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
