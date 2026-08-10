"""Deterministic Stage-1 semantic-compression ablation.

This is intentionally stdlib-only and read-only with respect to canonical Memory Seed data.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_seed.retrieval import load_corpus
from memory_seed.semantic_cache import rank_memory_chunks

ARMS = ("raw", "core", "core_why", "core_why_constraint", "structured")
MODAL = re.compile(r"\b(must|should|shall|only|never|without|require[ds]?|cannot|can't|do not|don't|may not|unless|instead of)\b", re.I)
PREFIX = re.compile(r"^D\d+\s*[-—:]\s*")
FIELD = re.compile(r"^\s*-\s*([DRAFT]):\s*(.*)$")
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z`])")


def stable(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def first_sentence(value: str) -> str:
    value = " ".join(value.split()).strip()
    return SENTENCE.split(value, maxsplit=1)[0].strip() if value else ""


def fields(text: str) -> dict[str, list[str]]:
    found = {"D": [], "R": [], "A": []}
    active = None
    for line in text.splitlines():
        match = FIELD.match(line)
        if match:
            active = match.group(1)
            if active in found:
                found[active].append(match.group(2).strip())
            else:
                active = None
        elif active and line.strip():
            found[active][-1] += " " + line.strip()
    return found


def representations(text: str) -> dict[str, str]:
    parsed = fields(text)
    core = first_sentence(" ".join(parsed["D"])) or first_sentence(text)
    why = first_sentence(" ".join(parsed["R"]))
    sentences = []
    for value in parsed["D"] + parsed["R"] + parsed["A"]:
        sentences.extend(SENTENCE.split(" ".join(value.split())))
    constraints = [s.strip() for s in sentences if MODAL.search(s)]
    constraints = [s for s in constraints if s and s not in {core, why}]
    constraints = list(dict.fromkeys(constraints))[:2]
    core_why = "\n".join(v for v in (core, why) if v)
    cwc = "\n".join([core_why, *constraints]).strip()
    structured = "\n".join(
        [f"claim: {core}"]
        + ([f"because: {why}"] if why else [])
        + [f"constraint: {item}" for item in constraints]
    )
    return {"raw": text.strip(), "core": core, "core_why": core_why,
            "core_why_constraint": cwc, "structured": structured}


def choose_sample(chunks: list, count: int = 100) -> list:
    ordered = sorted(chunks, key=lambda c: (len(c.text), stable(c.chunk_id)))
    buckets = [[] for _ in range(5)]
    for index, chunk in enumerate(ordered):
        buckets[min(4, index * 5 // max(1, len(ordered)))].append(chunk)
    selected = []
    for bucket in buckets:
        selected.extend(sorted(bucket, key=lambda c: stable("sample:" + c.chunk_id))[: count // 5])
    return sorted(selected, key=lambda c: c.chunk_id)


def token_proxy(text: str) -> int:
    return max(1, math.ceil(len(text.encode("utf-8")) / 4))


def provenance(source: str, rendered: str) -> list[dict[str, int | str]]:
    """Locate each source-grounded rendered clause in the canonical decision block."""
    spans = []
    for line in rendered.splitlines():
        clause = re.sub(r"^(claim|because|constraint):\s*", "", line).strip()
        if not clause:
            continue
        pattern = re.compile(r"\s+".join(re.escape(part) for part in clause.split()))
        match = pattern.search(source)
        if match is None:
            raise ValueError(f"derived clause is not source-grounded: {clause!r}")
        spans.append({"sha256": stable(clause), "start_char": match.start(),
                      "end_char": match.end()})
    return spans


def retrieval(sample: list, reps: dict[str, dict[str, str]]) -> dict:
    out = {}
    for arm in ARMS:
        corpus = [replace(c, title="", entry_title="", heading_path=(), text=reps[c.chunk_id][arm],
                          lexical_terms=(), topics=(), inferred_topics=(),
                          inferred_decision_topics=(), tags=()) for c in sample]
        ranks = []
        for source in sample:
            query = PREFIX.sub("", source.title).strip()
            ranked = rank_memory_chunks(query, corpus, top_k=len(corpus), recency_enabled=False,
                                        embedding_provider=None)
            rank = next((i for i, row in enumerate(ranked, 1) if row.chunk.chunk_id == source.chunk_id), None)
            ranks.append(rank or len(corpus) + 1)
        out[arm] = {
            "recall_at_1": sum(r <= 1 for r in ranks) / len(ranks),
            "recall_at_3": sum(r <= 3 for r in ranks) / len(ranks),
            "recall_at_5": sum(r <= 5 for r in ranks) / len(ranks),
            "mrr": sum(1 / r for r in ranks) / len(ranks),
            "ndcg_at_5": sum((1 / math.log2(r + 1)) if r <= 5 else 0 for r in ranks) / len(ranks),
            "mean_token_proxy": sum(token_proxy(reps[c.chunk_id][arm]) for c in sample) / len(sample),
        }
    raw_tokens = out["raw"]["mean_token_proxy"]
    for arm, row in out.items():
        relative = row["mean_token_proxy"] / raw_tokens
        row["relative_context"] = relative
        row["efficiency_mrr_per_relative_context"] = row["mrr"] / relative
    return out


def terms(text: str) -> Counter:
    return Counter(re.findall(r"[a-z][a-z0-9_-]{2,}", text.lower()))


def idf_vectors(texts: dict[str, str]) -> dict[str, dict[str, float]]:
    counts = {key: terms(value) for key, value in texts.items()}
    df = Counter(term for row in counts.values() for term in row)
    n = len(counts)
    return {key: {term: (1 + math.log(freq)) * math.log((n + 1) / (df[term] + 1))
                  for term, freq in row.items()} for key, row in counts.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    dot = sum(value * b.get(key, 0.0) for key, value in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def ref_target(value: str) -> str:
    return value.split(" -> ")[-1].strip()


def relationship_pairs(sample: list, all_chunks: list) -> list[tuple[str, str, int]]:
    by_ref = {c.chunk_id: c for c in all_chunks if c.granularity == "decision"}
    positives = set()
    for c in sample:
        # decision_edges are canonical tuples: (kind, source_ordinal, target_ref,
        # target_ordinal, subtype). Entry-level fields remain rendered refs.
        ordinal = c.chunk_id.rsplit(":", 1)[-1]
        # Decision-level experiment: do not project entry edges onto each sibling decision. A
        # decision edge with an explicit source ordinal belongs only to that source decision.
        raw_targets: Iterable[str] = tuple(
            edge[2] + ((":" + edge[3]) if edge[3] else "")
            for edge in c.decision_edges
            if edge[1] == ordinal and edge[3]
        )
        for raw in raw_targets:
            target = ref_target(str(raw))
            if ":d" not in target and target in {x.entry_id for x in all_chunks}:
                candidates = [x.chunk_id for x in all_chunks if x.entry_id == target and x.granularity == "decision"]
                if len(candidates) == 1:
                    target = candidates[0]
            if target in by_ref and target != c.chunk_id:
                positives.add((c.chunk_id, target))
    # Preserve sampled-source orientation. Targets may be outside the sample; the task asks whether
    # a representation of the sampled source helps distinguish its authored target from a hard
    # unlabeled candidate.
    negatives = set()
    pool = [c for c in all_chunks if c.granularity == "decision"]
    for source_ref, target_ref in sorted(positives):
        source = by_ref[source_ref]
        candidates = [c for c in pool if c.chunk_id not in {source_ref, target_ref}
                      and (source_ref, c.chunk_id) not in positives
                      and (source_ref, c.chunk_id) not in negatives
                      and (set(c.topics) & set(source.topics) or c.session_date == source.session_date)]
        if not candidates:
            candidates = [c for c in pool if c.chunk_id not in {source_ref, target_ref}
                          and (source_ref, c.chunk_id) not in positives
                          and (source_ref, c.chunk_id) not in negatives]
        chosen = min(candidates, key=lambda c: stable(source_ref + ":negative:" + target_ref + ":" + c.chunk_id))
        negatives.add((source_ref, chosen.chunk_id))
    return [(a, b, 1) for a, b in sorted(positives)] + [(a, b, 0) for a, b in sorted(negatives)]


def relation_metrics(sample: list, all_chunks: list, reps: dict[str, dict[str, str]]) -> dict:
    pairs = relationship_pairs(sample, all_chunks)
    by_ref = {c.chunk_id: c for c in all_chunks if c.granularity == "decision"}
    out = {"pair_count": len(pairs), "positive_count": sum(y for _, _, y in pairs), "arms": {}}
    for arm in ARMS:
        texts = {ref: representations(chunk.text)[arm] for ref, chunk in by_ref.items()}
        vectors = idf_vectors(texts)
        # Split by sampled source, not pair, so a source cannot leak across train and test. IDF is
        # deliberately transductive: Memory Seed indexes the full available corpus at query time.
        sources = sorted({a for a, _, _ in pairs}, key=lambda ref: (by_ref[ref].session_date, ref))
        train_sources = set(sources[: math.ceil(len(sources) * 0.7)])
        scored = [(cosine(vectors[a], vectors[b]), y, a) for a, b, y in pairs]
        train = [row for row in scored if row[2] in train_sources]
        test = [row for row in scored if row[2] not in train_sources]
        candidates = sorted({score for score, _, _ in train} | {0.0, 1.0})
        def stats(rows, threshold):
            tp = sum(score >= threshold and y for score, y, _ in rows)
            fp = sum(score >= threshold and not y for score, y, _ in rows)
            fn = sum(score < threshold and y for score, y, _ in rows)
            tn = sum(score < threshold and not y for score, y, _ in rows)
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            return {"precision": precision, "recall": recall, "f1": f1,
                    "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
                    "tp": tp, "fp": fp, "fn": fn, "tn": tn}
        threshold = max(candidates, key=lambda t: (stats(train, t)["f1"], -t))
        out["arms"][arm] = {"threshold": threshold, "train_count": len(train),
                            "test_count": len(test), **stats(test, threshold)}
    return out


def main() -> None:
    all_chunks = load_corpus(ROOT, granularity="decision")
    decisions = [c for c in all_chunks if c.granularity == "decision" and c.entry_id]
    sample = choose_sample(decisions)
    reps = {c.chunk_id: representations(c.text) for c in sample}
    dataset = [{"ref": c.chunk_id, "title": c.title, "source_path": c.source_path,
                "start_line": c.start_line, "end_line": c.end_line,
                "session_date": c.session_date.isoformat(), "source_chars": len(c.text),
                "source_sha256": stable(c.text), "topics": list(c.topics),
                "representations": reps[c.chunk_id],
                "provenance": {arm: provenance(c.text, reps[c.chunk_id][arm]) for arm in ARMS}}
               for c in sample]
    metrics = {"schema": "semantic-compression-stage1.v1", "sample_count": len(sample),
               "corpus_decision_count": len(decisions), "selection_fingerprint": stable(json.dumps([c.chunk_id for c in sample])),
               "query_exact_in_raw_count": sum(PREFIX.sub("", c.title).strip().lower() in c.text.lower() for c in sample),
               "retrieval": retrieval(sample, reps),
               "relationships": relation_metrics(sample, all_chunks, reps),
               "stage2_status": "not-run"}
    (HERE / "dataset.json").write_text(json.dumps(dataset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (HERE / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows = []
    for arm in ARMS:
        r = metrics["retrieval"][arm]; rel = metrics["relationships"]["arms"][arm]
        rows.append(f"| {arm} | {r['mean_token_proxy']:.1f} | {r['relative_context']:.3f} | {r['recall_at_5']:.3f} | {r['mrr']:.3f} | {r['efficiency_mrr_per_relative_context']:.3f} | {rel['f1']:.3f} | {rel['false_positive_rate']:.3f} |")
    report = """# Results\n\nStage 1 is complete; Stage 2 comprehension and fidelity evaluation has not run. These results cannot justify a production sidecar.\n\n| Arm | Mean token proxy | Relative context | Recall@5 | MRR | Efficiency | Link F1 | Link FPR |\n|---|---:|---:|---:|---:|---:|---:|---:|\n""" + "\n".join(rows) + """

See `metrics.json` for raw counts, thresholds, confusion matrices, and fingerprints.

## Interpretation

- Raw achieved the best retrieval MRR (`0.582`).
- Core used 12.9% of raw representation-body context, but retrieval MRR fell to `0.371` and
  Recall@5 to `0.470`.
- Core + why + constraint is the most plausible compact frontier point in Stage 1: 39.1% of raw
  context and MRR `0.508`. That remains a material loss from raw, not
  non-inferiority.
- Structured semantics used more context than core + why + constraint and did not improve its
  Recall@5, nDCG@5, or relationship confusion matrix. Labels alone earned nothing in this arm.
- Only 14 fully scoped positive decision edges exist in this sample, leaving six test pairs. The
  relationship task is underpowered and inconclusive. It is also a synthetic
  known-edge-versus-unlabeled diagnostic: unlabeled candidates may be real but unauthored
  relationships, so apparent precision/FPR are not semantic truth.

The efficiency composite rises as text shrinks, but that arithmetic does not erase absolute quality
losses. Stage 1 therefore provides no evidence that compression improves retrieval; relationship
detection is inconclusive. It establishes a measurable context/quality tradeoff for Stage 2 to test on actual
comprehension and fidelity.
"""
    (HERE / "results.md").write_text(report, encoding="utf-8")
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
