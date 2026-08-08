"""Is the answer even visible to the quiz agent? Old ranking versus new, on the seeded store.

The free gate before spending on a full re-quiz. An agent cannot answer from context it was never
shown, so retrieval quality is measurable without a single model call: does the expected answer
appear in the excerpts `search_memory` serves?

**Why this run matters more than the blended score.** The dry-run is saturated - run 3 scored 30/31,
so the end-to-end number can move by at most one question. This metric is not saturated, and it
tests something the 842-entry tuning never did: the seeded store holds 10 entries / 12 decision
chunks, and BM25F derives term rarity from the corpus. With few documents a term that appears in
most of them carries almost no information, which is not a hypothetical - two `ranking_ab` fixtures
collapsed under exactly that effect and had to be rebuilt. A regression at this size is plausible.

Method, deliberately mechanical:

  - The 8 `false_memory` traps are EXCLUDED. "The answer is not visible" is their correct state, so
    scoring them here would reward the wrong thing; abstention is an end-to-end judgement.
  - Key terms come from each question's `expected` string with stopwords dropped. A question counts
    as answer-visible at k when the served excerpts of the top k results contain enough of them.
  - `search_memory` is called exactly as production calls it, so this measures the shipped path.

**What this run found, which stopped the spend.** Answer-visible is 7 of 23 at k=8, identical under
both configurations - while the end-to-end dry-run scored 30 of 31. Those cannot both describe the
same path, and the explanation is that they do not: the expected answers live in
`.memory-seed/index.md` ("Marcus owns the benchmark suite", "Dana is lead maintainer", the 1.2us
baseline), `memory_search` indexes only `.memory-seed/sessions/**`, and `AGENTS.md` instructs the
agent to read `index.md` directly as step 2 of orientation.

So the blended dry-run score is carried by an agent reading a summary file, not by ranked retrieval.
That also re-reads run 3's +22.6 jump: the fix credited for it was routing durable facts INTO
index.md at capture time, and the doc records decision-level retrieval as worth only +3.2 of it.

Consequences worth keeping:

  - The dry-run cannot measure a ranking change. Re-running it after the BM25F rebuild would have
    returned roughly 96.8 either way, and that null would have been easy to read as "ranking did no
    harm" when the truthful reading is "ranking was not on the critical path".
  - The identical old/new columns below are NOT evidence that the configurations behave the same.
    They differ - same query, different order and scores - but with 12 chunks in the store and k=8,
    the top 8 contain 8 of 12 either way, so this metric cannot resolve them at this size.
  - The honest end-to-end test of retrieval is to quiz with `index.md` withheld, so the only route
    to an answer is `memory_search`. That is a different measurement from run 3, not a comparison.

Usage:
  python experiments/memory-index-dryrun/answer_visible.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from memory_seed import retrieval as retr  # noqa: E402
from memory_seed import semantic_cache as sc  # noqa: E402

WORKSPACE = HERE / "runs" / "workspace"
FACTS = json.loads((HERE / "facts.json").read_text(encoding="utf-8"))
KS = (1, 3, 8)

# Configurations under test. "old" is the state before today's ranking work; "new" is the shipped
# default. Everything else is held constant.
CONFIGS = {
    "old": {"bm25f": False, "weight": 60.0, "floor": 0.15, "damping": 0.25},
    "new": {
        "bm25f": sc.BM25F_ENABLED,
        "weight": sc.SEMANTIC_BLEND_WEIGHT,
        "floor": sc.RECENCY_FLOOR,
        "damping": sc.REPLACED_RANK_DAMPING,
    },
}

_STOP = {
    "the", "and", "for", "that", "with", "this", "from", "was", "were", "not", "but", "its", "are",
    "his", "her", "they", "them", "their", "what", "when", "which", "while", "would", "could",
    "should", "have", "has", "had", "our", "out", "per", "via", "any", "all", "one", "two", "use",
    "used", "using", "make", "made", "does", "did", "done", "other", "others", "leads", "lead",
    "recorded", "recorded.", "as", "is", "of", "in", "to", "a", "an", "on", "at", "by", "it",
}


def key_terms(expected: str) -> list[str]:
    """Distinctive tokens from the expected answer - names, numbers, identifiers."""
    tokens = re.findall(r"[A-Za-z0-9_.\-]+", expected.lower())
    out: list[str] = []
    for token in tokens:
        token = token.strip(".-_")
        if len(token) < 3 or token in _STOP:
            continue
        if token not in out:
            out.append(token)
    return out


def visible(excerpts: str, terms: list[str]) -> bool:
    """Answer-visible when a majority of the expected answer's distinctive terms are present.

    A majority rather than all: expected strings carry connective wording the store has no reason to
    reproduce verbatim ("recorded as the no-regression baseline"). Requiring every token would score
    a served correct answer as invisible.
    """
    if not terms:
        return False
    hits = sum(1 for t in terms if t in excerpts)
    return hits >= max(1, (len(terms) + 1) // 2)


def run(config: dict) -> dict:
    saved = (sc.BM25F_ENABLED, sc.SEMANTIC_BLEND_WEIGHT, sc.REPLACED_RANK_DAMPING)
    sc.BM25F_ENABLED = config["bm25f"]
    sc.SEMANTIC_BLEND_WEIGHT = config["weight"]
    sc.REPLACED_RANK_DAMPING = config["damping"]
    try:
        per_category: dict[str, dict[int, int]] = {}
        totals = {k: 0 for k in KS}
        counted = 0
        detail = []
        for q in FACTS["questions"]:
            if q["category"] == "false_memory":
                continue
            counted += 1
            terms = key_terms(q["expected"])
            payload = retr.search_memory(
                q["question"], WORKSPACE, top_k=max(KS), granularity="decision",
                recency_floor=config["floor"],
            )
            results = payload["results"]
            row = {"id": q["id"], "category": q["category"], "terms": terms}
            bucket = per_category.setdefault(q["category"], {k: 0 for k in KS})
            for k in KS:
                joined = " ".join((r.get("excerpt") or "").lower() for r in results[:k])
                hit = visible(joined, terms)
                row[f"at_{k}"] = hit
                if hit:
                    bucket[k] += 1
                    totals[k] += 1
            detail.append(row)
        return {"totals": totals, "per_category": per_category, "n": counted, "detail": detail}
    finally:
        sc.BM25F_ENABLED, sc.SEMANTIC_BLEND_WEIGHT, sc.REPLACED_RANK_DAMPING = saved


def main() -> int:
    if not WORKSPACE.exists():
        raise SystemExit(f"seeded workspace not found: {WORKSPACE}")
    from memory_seed.retrieval import load_corpus

    served = load_corpus(WORKSPACE, "decision")
    decisions = [c for c in served if c.granularity == "decision"]
    previews = [c for c in served if c.granularity != "decision"]
    print(f"store: {len(load_corpus(WORKSPACE,'entry'))} entries / "
          f"{len(served)} decision chunks")
    print("(BM25F was fitted on 842 entries - this is the small-corpus end)")

    # What this run can and cannot detect, printed BEFORE the numbers so nobody reads an
    # unchanged score as evidence of no effect. A decision chunk is served whole, so a change to
    # preview construction cannot move it; only the preview-served chunks below are in play. On
    # 2026-08-09 that was 1 of 12, and "22/23 unchanged" was no-regression evidence rather than
    # no-effect evidence - an instrument that cannot say which of those it measured is a trap.
    print(f"sensitivity: {len(decisions)} chunks served WHOLE (decision), "
          f"{len(previews)} served as a PREVIEW")
    if not previews:
        print("  -> this run is BLIND to preview construction: no chunk is served as one")
    elif len(previews) * 4 < len(served):
        print(f"  -> near-blind to preview construction: only {len(previews)}/{len(served)} "
              "chunks could move, so an unchanged score says little either way")
    print()

    out = {}
    for name, cfg in CONFIGS.items():
        out[name] = run(cfg)
        print(f"{name:>4}: bm25f={cfg['bm25f']!s:<5} weight={cfg['weight']:<5g} "
              f"recency_floor={cfg['floor']:<5g} damping={cfg['damping']}")

    n = out["new"]["n"]
    print(f"\nanswer-visible over {n} answerable questions (8 traps excluded)\n")
    print(f"{'':<22} " + "  ".join(f"{'@'+str(k):>10}" for k in KS))
    for name in ("old", "new"):
        cells = "  ".join(f"{out[name]['totals'][k]:>4}/{n:<5}" for k in KS)
        print(f"{name:<22} {cells}")
    delta = {k: out["new"]["totals"][k] - out["old"]["totals"][k] for k in KS}
    print(f"{'delta':<22} " + "  ".join(f"{delta[k]:>+4}      " for k in KS))

    print("\nby category (@8):")
    cats = sorted(out["new"]["per_category"])
    for cat in cats:
        o = out["old"]["per_category"][cat][8]
        w = out["new"]["per_category"][cat][8]
        total = sum(1 for q in FACTS["questions"] if q["category"] == cat)
        flag = "  <- regression" if w < o else ("  <- gain" if w > o else "")
        print(f"  {cat:<22} old {o}/{total}   new {w}/{total}{flag}")

    gate = all(delta[k] >= 0 for k in KS)
    print(f"\nGATE: {'CLEAR - phase 2 may spend' if gate else 'FAILED - do not spend'}")
    if not gate:
        print("  A drop here is a small-corpus regression in BM25F. The response is to make the")
        print("  scorer corpus-size aware or fall back below a document threshold - not to revert")
        print("  the gains measured on 842 entries.")

    (HERE / "answer-visible.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {HERE / 'answer-visible.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
