"""Relevance-band calibration on the real corpus.

Answers six questions in one deterministic, model-free run:

  1. N-CURVE       Does a chunk's score depend on corpus size? The proposal that motivated this
                   assumed it did (IDF drift). Reading `_lexical_score` says otherwise - it is pure
                   per-chunk term overlap with fixed field weights. This TESTS the prediction that
                   a positive's absolute score is invariant to N while the top-of-set, and
                   therefore the 0.55-of-top ratio rule, is not.
  2. SEPARATION    Do positives and negatives separate under any candidate statistic?
  3. THRESHOLDS    Fit each statistic's threshold on half the labels, report on the held-out half.
  4. COST          Served payload size against corpus size.
  5. SMALL-N       What the band does on a small store, where it was originally tuned.
  6. SHIPPED       What the shipped rule (floor 6.0, ratio 0.55) scores on the same labels.

Kill condition, stated before the run: if no statistic reaches 0.80 held-out balanced accuracy
with a confidence interval excluding 0.5, the recommendation is to DELETE the band rather than
ship a retuned version of the same false confidence.

Lexical only (`embedding_provider=None`), matching the ranking-ab convention: deterministic and
reproducible, no model spend.

Usage:
  python experiments/band-calibration/calibrate.py [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(HERE))

from memory_seed.retrieval import (  # noqa: E402
    RELEVANCE_FLOOR,
    RELEVANCE_STRONG_RATIO,
    ranked_to_dict,
)
from memory_seed.semantic_cache import (  # noqa: E402
    _query_terms,
    extract_memory_chunks,
    rank_session_memory,
)

import labels as labels_mod  # noqa: E402

TOP_K = 8
N_SIZES = [25, 50, 100, 200, 400, 800]
CORPUS_SEED = 20260805


# --------------------------------------------------------------------------------------------
# statistics computed from one query's result set
# --------------------------------------------------------------------------------------------

def features(query: str, ranked: list, k: int = TOP_K) -> dict:
    """Candidate band statistics. Each is a number where HIGHER should mean 'more trustworthy'."""
    top_rows = ranked[:k]
    scores = [r.final_score for r in top_rows]
    if not scores:
        return {}
    top = scores[0]
    terms = _query_terms(query)
    n_terms = max(len(terms), 1)
    median = statistics.median(scores)
    mad = statistics.median([abs(s - median) for s in scores]) or 1e-9
    second = scores[1] if len(scores) > 1 else 0.0

    matched = len(set(top_rows[0].matched_terms))

    return {
        # what the shipped rule uses
        "top_abs": top,
        # normalise by how much a query could possibly score
        "top_per_term": top / n_terms,
        # fraction of the query the best result actually explains
        "matched_frac": matched / n_terms,
        # scale-free shape of the result set
        "top_over_median": top / median if median > 0 else 0.0,
        "robust_z": (top - median) / mad,
        "gap1": top / second if second > 0 else (top if top > 0 else 0.0),
    }


FEATURE_NAMES = ["top_abs", "top_per_term", "matched_frac", "top_over_median", "robust_z", "gap1"]


# --------------------------------------------------------------------------------------------
# evaluation
# --------------------------------------------------------------------------------------------

def auc(pos: list[float], neg: list[float]) -> float:
    """Mann-Whitney AUC: P(random positive scores above random negative), ties counted as half."""
    if not pos or not neg:
        return float("nan")
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else (0.5 if p == n else 0.0)
    return wins / (len(pos) * len(neg))


def auc_ci(pos: list[float], neg: list[float], iterations: int = 2000, seed: int = 7) -> tuple:
    """Bootstrap CI. With ~19 negatives per half a point estimate alone would be misleading."""
    if not pos or not neg:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    samples = []
    for _ in range(iterations):
        p = [rng.choice(pos) for _ in pos]
        n = [rng.choice(neg) for _ in neg]
        samples.append(auc(p, n))
    samples.sort()
    lo = samples[int(0.025 * len(samples))]
    hi = samples[int(0.975 * len(samples)) - 1]
    return (lo, hi)


def best_threshold(pos: list[float], neg: list[float]) -> tuple[float, float]:
    """Threshold maximising balanced accuracy on the FIT half. Returns (threshold, balanced acc)."""
    candidates = sorted(set(pos + neg))
    best = (float("nan"), 0.0)
    for index, value in enumerate(candidates):
        # midpoint between adjacent observed values, so the threshold is not pinned to a data point
        thr = value if index == 0 else (candidates[index - 1] + value) / 2.0
        sens = sum(1 for p in pos if p >= thr) / len(pos)
        spec = sum(1 for n in neg if n < thr) / len(neg)
        bal = (sens + spec) / 2.0
        if bal > best[1]:
            best = (thr, bal)
    return best


def evaluate(threshold: float, pos: list[float], neg: list[float]) -> dict:
    sens = sum(1 for p in pos if p >= threshold) / len(pos) if pos else float("nan")
    spec = sum(1 for n in neg if n < threshold) / len(neg) if neg else float("nan")
    return {
        "threshold": threshold,
        "sensitivity": sens,
        "specificity": spec,
        "balanced_accuracy": (sens + spec) / 2.0,
        "n_pos": len(pos),
        "n_neg": len(neg),
    }


def wilson(successes: int, total: int, z: float = 1.96) -> tuple:
    if total == 0:
        return (float("nan"), float("nan"))
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


# --------------------------------------------------------------------------------------------
# stages
# --------------------------------------------------------------------------------------------

PROVIDER = None  # set by --arm semantic; None keeps the deterministic lexical baseline


# `rank_session_memory` defaults these OFF; `search_memory` - the production path - turns them ON
# (retrieval.py:148-150). The first calibration run called the ranker bare and so measured a
# configuration nobody runs. The effect on the headline numbers should be small (only 4 of 842
# entries are replaced) but "should be small" is not "checked" - it is re-baselined, not assumed.
PRODUCTION_RANKING = {
    "supersession_damping": True,
    "replacing_successor_boost": True,
}


def rank(query: str, cwd: Path, chunks: list, k: int = TOP_K) -> list:
    return rank_session_memory(
        query,
        cwd,
        top_k=max(k, 1),
        chunks=list(chunks),
        embedding_provider=PROVIDER,
        **PRODUCTION_RANKING,
    )


def served_chars(ranked: list, k: int = TOP_K) -> int:
    """Payload size as the caller would actually receive it.

    ASKS the serialiser rather than restating its rule. This used to compute
    `min(len(chunk.text), DECISION_TEXT_LIMIT)` - a private copy of a rule owned by
    `retrieval.ranked_to_dict` - and a measurement script holding its own copy of a production rule
    is worse than one that is simply wrong, because it cannot fail. It does not crash and no test
    catches it; it keeps printing confident numbers that quietly stop describing the system.

    That is exactly what happened on 2026-08-09: previews became a windowed span capped at 280
    characters and decision blocks grew a truncation marker, so the local copy was wrong in both
    directions at once - overstating entry chunks by up to 2220 characters each, understating
    capped decisions by the marker's length. Same defect family as the three copies of the ADR
    replay rules, which diverged twice before they were collapsed into one.
    """
    return sum(len(ranked_to_dict(r).get("excerpt") or "") for r in ranked[:k])


def stage_n_curve(cwd: Path, rows: list[dict], all_chunks: list, sizes: list[int]) -> dict:
    """Hold the query and its correct answer fixed; vary only the number of distractors.

    This is the controlled version: the positive's own chunk is always present, so any movement in
    its score is caused by corpus size and nothing else.
    """
    rng = random.Random(CORPUS_SEED)
    by_entry: dict[str, list] = {}
    for chunk in all_chunks:
        if chunk.entry_id:
            by_entry.setdefault(chunk.entry_id, []).append(chunk)

    probes = [r for r in rows if r["expected"] in by_entry][:40]
    negatives = [r for r in rows if r["expected"] is None][:12]
    entry_ids = list(by_entry)

    out: dict[str, list] = {"sizes": sizes, "rows": []}
    for size in sizes:
        keep_scores, top_scores, ratios, neg_tops = [], [], [], []
        for probe in probes:
            target = probe["expected"]
            distractor_ids = [e for e in entry_ids if e != target]
            rng.shuffle(distractor_ids)
            chosen = [target] + distractor_ids[: max(size - 1, 0)]
            corpus = [c for e in chosen for c in by_entry[e]]
            # FULL-k. Ranking to top_k=8 and then looking for the target scores it 0.0 whenever it
            # falls outside the window, which measures "is the answer in the top 8" and reports it
            # as "the answer's score dropped". The first run of this stage did exactly that.
            ranked = rank(probe["query"], cwd, corpus, k=len(corpus))
            if not ranked:
                continue
            target_score = next(
                (r.final_score for r in ranked if r.chunk.entry_id == target), None
            )
            if target_score is None:
                continue
            keep_scores.append(target_score)
            top_scores.append(ranked[0].final_score)
            ratios.append(target_score / ranked[0].final_score if ranked[0].final_score else 0.0)
        for probe in negatives:
            distractor_ids = list(entry_ids)
            rng.shuffle(distractor_ids)
            corpus = [c for e in distractor_ids[:size] for c in by_entry[e]]
            ranked = rank(probe["query"], cwd, corpus)
            if ranked:
                neg_tops.append(ranked[0].final_score)
        out["rows"].append(
            {
                "n_entries": size,
                "positive_score_mean": round(statistics.mean(keep_scores), 3) if keep_scores else None,
                "positive_score_median": round(statistics.median(keep_scores), 3) if keep_scores else None,
                "top_of_set_mean": round(statistics.mean(top_scores), 3) if top_scores else None,
                "positive_over_top_mean": round(statistics.mean(ratios), 3) if ratios else None,
                "negative_top_mean": round(statistics.mean(neg_tops), 3) if neg_tops else None,
                "probes": len(keep_scores),
            }
        )
    return out


def stage_features(cwd: Path, rows: list[dict], chunks: list) -> list[dict]:
    out = []
    for row in rows:
        ranked = rank(row["query"], cwd, chunks)
        feats = features(row["query"], ranked)
        if not feats:
            continue
        found_rank = None
        if row["expected"]:
            for index, r in enumerate(ranked[:TOP_K], start=1):
                if r.chunk.entry_id == row["expected"]:
                    found_rank = index
                    break
        served = served_chars(ranked)
        out.append(
            {
                **row,
                **feats,
                "is_positive": row["expected"] is not None,
                "answer_rank": found_rank,
                "served_chars": served,
            }
        )
    return out


def stage_shipped_rule(scored: list[dict]) -> dict:
    """What the shipped floor/ratio actually does on these labels.

    The shipped rule bands a result `strong` when score >= FLOOR and >= RATIO * top. Per query,
    `no_match_above_threshold` is the negation of "any result is strong" - so on this label set the
    rule's implied claim is "this query has an answer".
    """
    pos_flagged = neg_flagged = pos = neg = 0
    for row in scored:
        # top result is strong iff top >= FLOOR (it is trivially >= RATIO * top)
        says_answer = row["top_abs"] >= RELEVANCE_FLOOR
        if row["is_positive"]:
            pos += 1
            pos_flagged += int(says_answer)
        else:
            neg += 1
            neg_flagged += int(says_answer)
    sens = pos_flagged / pos if pos else float("nan")
    spec = 1 - (neg_flagged / neg) if neg else float("nan")
    return {
        "floor": RELEVANCE_FLOOR,
        "ratio": RELEVANCE_STRONG_RATIO,
        "sensitivity": sens,
        "specificity": spec,
        "balanced_accuracy": (sens + spec) / 2.0,
        "negatives_called_answerable": neg_flagged,
        "negatives_total": neg,
        "specificity_ci": wilson(neg - neg_flagged, neg),
    }


def stage_small_corpus(cwd: Path, rows: list[dict], all_chunks: list, sizes: list[int]) -> dict:
    """Does the winning statistic still separate on a SMALL store?

    The band's original constants were fitted at 7 entries, so "does this work when the corpus is
    tiny" is not a footnote - it is half the question. Same construction as the N-curve: each
    positive keeps its own answer in the corpus, each negative gets distractors only.
    """
    rng = random.Random(CORPUS_SEED + 2)
    by_entry: dict[str, list] = {}
    for chunk in all_chunks:
        if chunk.entry_id:
            by_entry.setdefault(chunk.entry_id, []).append(chunk)
    entry_ids = list(by_entry)
    # Stratify by source. Taking the first 60 rows in build order yields 4 lifecycle + 56 term
    # queries and NO title queries - the easiest source - which silently changes the positive mix
    # between this stage and the held-out analysis and makes the two sets of AUCs incomparable.
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        if row["expected"] in by_entry:
            grouped.setdefault(row["source"], []).append(row)
    positives = []
    per_source = max(60 // max(len(grouped), 1), 1)
    for source in sorted(grouped):
        positives.extend(grouped[source][:per_source])
    negatives = [r for r in rows if r["expected"] is None]

    out: dict = {"sizes": sizes, "rows": []}
    for size in sizes:
        pos_feats: list[dict] = []
        neg_feats: list[dict] = []
        for probe in positives:
            target = probe["expected"]
            others = [e for e in entry_ids if e != target]
            rng.shuffle(others)
            corpus = [c for e in [target] + others[: max(size - 1, 0)] for c in by_entry[e]]
            ranked = rank(probe["query"], cwd, corpus)
            feats = features(probe["query"], ranked)
            if feats:
                pos_feats.append(feats)
        for probe in negatives:
            others = list(entry_ids)
            rng.shuffle(others)
            corpus = [c for e in others[:size] for c in by_entry[e]]
            ranked = rank(probe["query"], cwd, corpus)
            feats = features(probe["query"], ranked)
            if feats:
                neg_feats.append(feats)
        row = {"n_entries": size, "n_pos": len(pos_feats), "n_neg": len(neg_feats)}
        for name in FEATURE_NAMES:
            p = [f[name] for f in pos_feats]
            n = [f[name] for f in neg_feats]
            row[name] = round(auc(p, n), 3)
        out["rows"].append(row)
    return out


def stage_cost(cwd: Path, rows: list[dict], all_chunks: list, sizes: list[int]) -> list[dict]:
    rng = random.Random(CORPUS_SEED + 1)
    by_entry: dict[str, list] = {}
    for chunk in all_chunks:
        if chunk.entry_id:
            by_entry.setdefault(chunk.entry_id, []).append(chunk)
    entry_ids = list(by_entry)
    probes = [r for r in rows if r["expected"]][:20]
    out = []
    for size in sizes:
        served = []
        for probe in probes:
            ids = list(entry_ids)
            rng.shuffle(ids)
            corpus = [c for e in ids[:size] for c in by_entry[e]]
            ranked = rank(probe["query"], cwd, corpus)
            served.append(served_chars(ranked))
        out.append(
            {
                "n_entries": size,
                "served_chars_mean": int(statistics.mean(served)) if served else 0,
                "approx_tokens_mean": int(statistics.mean(served) / 4) if served else 0,
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", dest="json_out", default=None)
    parser.add_argument("--arm", choices=["lexical", "semantic"], default="lexical",
                        help="semantic uses the local Model2Vec provider - the shipped default")
    args = parser.parse_args()
    json_out = args.json_out or str(HERE / f"results-{args.arm}.json")

    global PROVIDER
    if args.arm == "semantic":
        from memory_seed.retrieval import resolve_semantic_provider
        PROVIDER, provider_name, _ = resolve_semantic_provider("probe", None, enabled=True)
        if PROVIDER is None:
            raise SystemExit("semantic arm requested but no provider resolved")
        print(f"arm: semantic ({provider_name})")
    else:
        print("arm: lexical (deterministic baseline)")

    cwd = REPO_ROOT
    entry_chunks = extract_memory_chunks(cwd, granularity="entry")
    decision_chunks = extract_memory_chunks(cwd, granularity="decision")
    print(f"corpus: {len(entry_chunks)} entries / {len(decision_chunks)} decision chunks")

    rows = labels_mod.build(cwd)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["source"]] = counts.get(row["source"], 0) + 1
    print(f"labels: {counts} (total {len(rows)})\n")

    report: dict = {
        "entries": len(entry_chunks),
        "decision_chunks": len(decision_chunks),
        "label_counts": counts,
        "top_k": TOP_K,
        "kill_condition": "no statistic reaches 0.80 held-out balanced accuracy with CI excluding 0.5",
    }

    print("=== 1. N-curve: is a positive's score invariant to corpus size? ===")
    curve = stage_n_curve(cwd, rows, decision_chunks, N_SIZES)
    report["n_curve"] = curve
    print(f"{'N':>6} {'pos_score':>10} {'top_of_set':>11} {'pos/top':>8} {'neg_top':>8}")
    for r in curve["rows"]:
        print(
            f"{r['n_entries']:>6} {r['positive_score_mean']!s:>10} {r['top_of_set_mean']!s:>11} "
            f"{r['positive_over_top_mean']!s:>8} {r['negative_top_mean']!s:>8}"
        )

    print("\n=== 2/3. separation and held-out thresholds ===")
    scored = stage_features(cwd, rows, decision_chunks)
    report["n_scored"] = len(scored)
    fit_rows, held_rows = labels_mod.split(scored)

    def vals(group, name, positive):
        return [r[name] for r in group if r["is_positive"] is positive]

    stats_out = {}
    for name in FEATURE_NAMES:
        f_pos, f_neg = vals(fit_rows, name, True), vals(fit_rows, name, False)
        h_pos, h_neg = vals(held_rows, name, True), vals(held_rows, name, False)
        thr, fit_bal = best_threshold(f_pos, f_neg)
        held = evaluate(thr, h_pos, h_neg)
        a = auc(h_pos, h_neg)
        lo, hi = auc_ci(h_pos, h_neg)
        stats_out[name] = {
            "fit_threshold": thr,
            "fit_balanced_accuracy": fit_bal,
            "heldout": held,
            "heldout_auc": a,
            "heldout_auc_ci": [lo, hi],
        }
        print(
            f"{name:>16}  thr={thr:8.3f}  held sens={held['sensitivity']:.2f} "
            f"spec={held['specificity']:.2f} bal={held['balanced_accuracy']:.2f}  "
            f"AUC={a:.3f} [{lo:.3f},{hi:.3f}]"
        )
    report["statistics"] = stats_out

    print("\n=== 6. the shipped rule on the same labels ===")
    shipped = stage_shipped_rule(scored)
    report["shipped_rule"] = shipped
    print(
        f"floor={shipped['floor']} ratio={shipped['ratio']}: sens={shipped['sensitivity']:.2f} "
        f"spec={shipped['specificity']:.2f} bal={shipped['balanced_accuracy']:.2f}"
    )
    print(
        f"  negatives called answerable: {shipped['negatives_called_answerable']}"
        f"/{shipped['negatives_total']}  specificity 95% CI "
        f"[{shipped['specificity_ci'][0]:.2f},{shipped['specificity_ci'][1]:.2f}]"
    )

    print("\n=== 5. does separation survive on a SMALL store? (AUC per statistic) ===")
    small = stage_small_corpus(cwd, rows, decision_chunks, N_SIZES)
    report["small_corpus"] = small
    header = "     N  " + "".join(f"{n[:14]:>15}" for n in FEATURE_NAMES)
    print(header)
    for row in small["rows"]:
        line = f"{row['n_entries']:>6}  " + "".join(f"{row[n]:>15.3f}" for n in FEATURE_NAMES)
        print(line)

    print("\n=== 4. cost against corpus size ===")
    cost = stage_cost(cwd, rows, decision_chunks, N_SIZES)
    report["cost"] = cost
    for row in cost:
        print(f"  N={row['n_entries']:>4}  served ~{row['approx_tokens_mean']} tokens (top {TOP_K})")

    print("\n=== 5. answer-rank health (is retrieval finding the answer at all?) ===")
    by_source: dict[str, list] = {}
    for row in scored:
        if row["is_positive"]:
            by_source.setdefault(row["source"], []).append(row["answer_rank"])
    health = {}
    for source, ranks in sorted(by_source.items()):
        at1 = sum(1 for r in ranks if r == 1)
        ink = sum(1 for r in ranks if r is not None)
        health[source] = {"n": len(ranks), "at_1": at1, "in_top_k": ink}
        lo, hi = wilson(at1, len(ranks))
        print(
            f"  {source:8} n={len(ranks):>3}  answer@1 {at1:>3} ({100*at1/len(ranks):.0f}%, "
            f"95% CI {100*lo:.0f}-{100*hi:.0f}%)  answer@{TOP_K} {ink}"
        )
    report["answer_health"] = health

    report["arm"] = args.arm
    Path(json_out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
