"""Held-out diagnostic for the lexical-term normalization defect.

This is a new experiment, not a rewrite of the scored front-door ablation.  It uses targets that
were absent from that development set, source-only authored queries, and the shipped BM25F ranker.
Only the representation of the dedicated lexical-term field changes.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import random
import re
import sys
from dataclasses import replace
from pathlib import Path

# Make direct ``python experiments/.../identifier_lane_ablation.py`` invocations resolve the
# checkout's package rather than a global install (or nothing at all).
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from memory_seed import semantic_cache as SEMANTIC


HERE = Path(__file__).resolve().parent
BENCHMARK_PATH = HERE / "benchmark.py"
LEAN_PATH = HERE / "lean_draft_pilot.py"
FRONT_PATH = HERE / "front_door_ablation.py"
QUERY_PATH = HERE / "identifier-lane-queries.json"
QUERY_REVIEW_PATH = HERE / "identifier-lane-query-review.json"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


BENCHMARK = _load_module("identifier_lane_benchmark", BENCHMARK_PATH)
LEAN = _load_module("identifier_lane_lean", LEAN_PATH)
FRONT = _load_module("identifier_lane_front", FRONT_PATH)

ARMS = (
    "body_only",
    "current_lexical_terms",
    "normalized_current_terms",
    "normalized_authored_terms",
    "normalized_union_terms",
)
EXPECTED_SOURCE_REVISION = LEAN.EXPECTED_SOURCE_REVISION
EXPECTED_CORPUS_FINGERPRINT = LEAN.EXPECTED_CORPUS_FINGERPRINT
EXPECTED_SELECTION_FINGERPRINT = "sha256:0fed7e7afb0e3d5bc599786e773c005cf46fd1a59068fe90b1bb65008ff3dfbc"
EXPECTED_SELECTOR_SHA256 = "sha256:06f7c52844a578066deb829948ff4d6611a81bb36ed636799bb7512ef28740a6"
EXPECTED_QUERY_SHA256 = "sha256:6bb711f0b3f87c675f624e0704d26c17a30eff4da160926b2aea825f5759ed22"
EXPECTED_QUERY_REVIEW_SHA256 = "sha256:940b5c05a233ce3bde0200cd3288740754ef117b80ce30b748daf1cf3244beea"
FORBIDDEN_QUERY_TERMS = (
    "body_only",
    "lexical_terms",
    "normalized_current",
    "normalized_authored",
    "normalized_union",
    "identifier lane",
    "bm25f",
    "packet_id",
    "entry_id",
    "mse_",
    "ms-",
)
WORD = re.compile(r"[A-Za-z0-9]+")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def notable_authored_identifiers(text: str) -> tuple[str, ...]:
    """Exact notable identifiers from author-backticked D/R/F source; no synthesized aliases."""
    parsed = LEAN.parse_fields(text)
    identifiers: list[str] = []
    for anchor in LEAN.exact_anchors(parsed, limit=None):
        for identifier in FRONT.identifier_tokens(anchor):
            if FRONT.contains_exact_identifier(text, identifier) and identifier not in identifiers:
                identifiers.append(identifier)
    return tuple(identifiers)


def normalized_terms(values) -> tuple[str, ...]:
    """Use production normalization so the experiment cannot restate the scorer's token rule."""
    output: list[str] = []
    for value in values:
        normalized = SEMANTIC._normalize(value)
        if normalized and normalized not in output:
            output.append(normalized)
    return tuple(output)


def current_authored_identifiers(chunk) -> tuple[str, ...]:
    """Authored exact identifiers the current lexical field actually extracted."""
    current = set(normalized_terms(chunk.lexical_terms))
    return tuple(
        identifier for identifier in notable_authored_identifiers(chunk.text)
        if SEMANTIC._normalize(identifier) in current
    )


def choose_holdout(sample: list, count: int = 30) -> list:
    """Select a length-stratified holdout disjoint by entry from the development targets."""
    prior_entries = {chunk.entry_id for chunk in LEAN.choose_pilot(sample)}
    eligible = [
        chunk for chunk in sample
        if chunk.entry_id not in prior_entries
        and LEAN.parse_fields(chunk.text)["R"]
        and current_authored_identifiers(chunk)
    ]
    ordered = sorted(eligible, key=lambda chunk: (len(chunk.text), BENCHMARK.stable(chunk.chunk_id)))
    buckets = [[] for _ in range(3)]
    for index, chunk in enumerate(ordered):
        buckets[min(2, index * 3 // max(1, len(ordered)))].append(chunk)
    selected = []
    for bucket in buckets:
        selected.extend(sorted(
            bucket,
            key=lambda chunk: BENCHMARK.stable("identifier-lane-holdout:" + chunk.chunk_id),
        )[: count // 3])
    if len(selected) != count:
        raise RuntimeError(f"need {count} disjoint rationale+identifier decisions, found {len(selected)}")
    return sorted(selected, key=lambda chunk: chunk.chunk_id)


def packet_id(ref: str) -> str:
    return "il_" + BENCHMARK.stable("identifier-lane-holdout:" + ref)[:12]


def selection_fingerprint(selected: list) -> str:
    return "sha256:" + BENCHMARK.stable(json.dumps([chunk.chunk_id for chunk in selected]))


def _candidate_targets() -> tuple[list, list, dict]:
    decisions, identity = BENCHMARK.frozen_corpus()
    if identity.get("source_revision") != EXPECTED_SOURCE_REVISION:
        raise RuntimeError("unexpected frozen source revision")
    if identity.get("corpus_fingerprint") != EXPECTED_CORPUS_FINGERPRINT:
        raise RuntimeError("unexpected frozen corpus fingerprint")
    sample = BENCHMARK.choose_sample(decisions)
    selected = choose_holdout(sample)
    return sample, selected, identity


def freeze_info() -> dict:
    """Return candidate pins without exposing authoring packets or permitting scoring."""
    _, selected, identity = _candidate_targets()
    return {
        "source_revision": identity["source_revision"],
        "corpus_fingerprint": identity["corpus_fingerprint"],
        "selection_fingerprint": selection_fingerprint(selected),
        "selector_sha256": selector_sha256(),
        "target_count": len(selected),
    }


def frozen_targets() -> tuple[list, list, dict]:
    if EXPECTED_SELECTOR_SHA256 == "PENDING" or EXPECTED_SELECTION_FINGERPRINT == "PENDING":
        raise RuntimeError("identifier-lane selector and target selection must be frozen before authoring")
    if selector_sha256() != EXPECTED_SELECTOR_SHA256:
        raise RuntimeError("identifier-lane selector is not frozen")
    sample, selected, identity = _candidate_targets()
    if selection_fingerprint(selected) != EXPECTED_SELECTION_FINGERPRINT:
        raise RuntimeError("identifier holdout selection is not frozen")
    return sample, selected, identity


def query_packets(batch: int | None = None, batches: int = 3) -> list[dict]:
    _, selected, _ = frozen_targets()
    packets = [
        {
            "packet_id": packet_id(chunk.chunk_id),
            "source": chunk.text,
            "allowed_identifiers": list(current_authored_identifiers(chunk)),
        }
        for chunk in selected
    ]
    if batch is not None:
        packets = [item for index, item in enumerate(packets) if index % batches == batch]
    return packets


def _query_words(value: str) -> list[str]:
    return WORD.findall(value.lower())


def _copied_source_window(query: str, source: str, identifier: str | None) -> str | None:
    candidate = query
    if identifier:
        candidate = re.sub(re.escape(identifier), " ", candidate, flags=re.I)
    query_words = _query_words(candidate)
    source_words = _query_words(source)
    windows = {tuple(source_words[i:i + 5]) for i in range(max(0, len(source_words) - 4))}
    for index in range(max(0, len(query_words) - 4)):
        window = tuple(query_words[index:index + 5])
        if window in windows:
            return " ".join(window)
    return None


def validate_queries(payload: dict, selected: list) -> list[dict]:
    if payload.get("schema") != "identifier-lane-queries.v1":
        raise ValueError("unexpected identifier-lane query schema")
    authoring = payload.get("authoring", {})
    authors = authoring.get("authors", [])
    author_ids = [str(author.get("author_id", "")).strip() for author in authors]
    if (
        authoring.get("passes") != 3
        or len(authors) != 3
        or len(set(author_ids)) != 3
        or any(not author_id or not str(author.get("model", "")).strip()
               for author_id, author in zip(author_ids, authors))
        or authoring.get("input_access") != "canonical-source-and-identifiers-only"
        or authoring.get("ranking_results_seen") is not False
        or authoring.get("arm_definitions_seen") is not False
        or authoring.get("prior_results_seen") is not False
    ):
        raise ValueError("query authoring provenance is incomplete or not source-only")
    sources = {packet_id(chunk.chunk_id): chunk.text for chunk in selected}
    allowed = {
        packet_id(chunk.chunk_id): current_authored_identifiers(chunk)
        for chunk in selected
    }
    seen = set()
    query_texts = set()
    author_counts = {author_id: 0 for author_id in author_ids}
    diagnostics = []
    for item in payload.get("queries", []):
        key = item.get("packet_id")
        if key not in sources or key in seen:
            raise ValueError(f"unknown or duplicate query packet: {key}")
        seen.add(key)
        author_id = str(item.get("author_id", "")).strip()
        if author_id not in author_counts:
            raise ValueError(f"{key} has an unknown query author")
        author_counts[author_id] += 1
        semantic = str(item.get("semantic_query", "")).strip()
        identifier_query = str(item.get("identifier_query", "")).strip()
        identifier = str(item.get("identifier", "")).strip()
        if identifier not in allowed[key]:
            raise ValueError(f"{key} identifier is not an exact authored source identifier")
        for kind, query in (("semantic", semantic), ("identifier", identifier_query)):
            words = _query_words(query)
            if not 6 <= len(words) <= 32:
                raise ValueError(f"{key} {kind} query must contain 6-32 words")
            lowered = query.lower()
            if any(term in lowered for term in FORBIDDEN_QUERY_TERMS):
                raise ValueError(f"{key} {kind} query leaks benchmark metadata")
            copied = _copied_source_window(query, sources[key], identifier if kind == "identifier" else None)
            if copied:
                raise ValueError(f"{key} {kind} query copies a five-word source window: {copied}")
            if lowered in query_texts:
                raise ValueError("query texts must be globally unique")
            query_texts.add(lowered)
        if FRONT.identifier_tokens(semantic) or any(
            FRONT.contains_exact_identifier(semantic, candidate) for candidate in allowed[key]
        ):
            raise ValueError(f"{key} semantic query contains an identifier")
        query_identifiers = FRONT.identifier_tokens(identifier_query)
        if query_identifiers != (identifier,):
            raise ValueError(f"{key} identifier query must contain exactly its declared identifier")
        if not FRONT.contains_exact_identifier(sources[key], identifier):
            raise ValueError(f"{key} identifier is not boundary-exact in source")
        diagnostics.append({"packet_id": key, "identifier": identifier, "author_id": author_id})
    if seen != set(sources):
        raise ValueError("query artifact must cover all 30 holdout packets exactly once")
    if len(selected) % 3 or set(author_counts.values()) != {len(selected) // 3}:
        raise ValueError("the three source-only authors must contribute equal packet counts")
    return diagnostics


def validate_query_review(payload: dict, query_sha256: str, selected: list) -> list[dict]:
    if payload.get("schema") != "identifier-lane-query-review.v1":
        raise ValueError("unexpected identifier-lane review schema")
    if payload.get("query_sha256") != query_sha256:
        raise ValueError("query review does not match the frozen query hash")
    if not str(payload.get("reviewer_model", "")).strip():
        raise ValueError("query review must identify its reviewer model")
    if payload.get("input_access") != "canonical-source-and-queries-only":
        raise ValueError("query review input access is not source-only")
    if payload.get("ranking_results_seen") is not False or payload.get("arm_definitions_seen") is not False:
        raise ValueError("query reviewer must not see rankings or arm definitions")
    expected = {(packet_id(chunk.chunk_id), kind) for chunk in selected for kind in ("semantic", "identifier")}
    seen = set()
    diagnostics = []
    for review in payload.get("reviews", []):
        key = (review.get("packet_id"), review.get("kind"))
        if key not in expected or key in seen:
            raise ValueError(f"unknown or duplicate query review: {key}")
        seen.add(key)
        if review.get("accepted") is not True:
            raise ValueError(f"query review rejected or did not accept: {key}")
        if (
            review.get("target_specific") is not True
            or review.get("natural") is not True
            or review.get("source_copying_absent") is not True
            or not str(review.get("reason", "")).strip()
        ):
            raise ValueError(f"query review lacks a grounded acceptance rationale: {key}")
        diagnostics.append({"packet_id": key[0], "kind": key[1], "accepted": True})
    if seen != expected:
        raise ValueError("query review must accept all 60 holdout queries exactly once")
    return diagnostics


def authored_terms_for_chunk(chunk) -> tuple[str, ...]:
    return notable_authored_identifiers(chunk.text)


def corpus_for_arm(sample: list, arm: str) -> list:
    corpus = []
    for chunk in sample:
        current = tuple(chunk.lexical_terms)
        authored = authored_terms_for_chunk(chunk)
        if arm == "body_only":
            terms = ()
        elif arm == "current_lexical_terms":
            terms = current
        elif arm == "normalized_current_terms":
            terms = normalized_terms(current)
        elif arm == "normalized_authored_terms":
            terms = normalized_terms(authored)
        elif arm == "normalized_union_terms":
            terms = normalized_terms((*current, *authored))
        else:
            raise ValueError(f"unknown identifier-lane arm: {arm}")
        corpus.append(replace(
            chunk,
            title="",
            entry_title="",
            heading_path=(),
            text=chunk.text,
            lexical_terms=terms,
            topics=(),
            inferred_topics=(),
            inferred_decision_topics=(),
            tags=(),
        ))
    return corpus


def selector_sha256() -> str:
    spec = {
        "schema": "identifier-lane-selector.v1",
        "arms": ARMS,
        "forbidden_query_terms": FORBIDDEN_QUERY_TERMS,
        "word_pattern": WORD.pattern,
        "semantic_cache_sha256": sha256_bytes(Path(SEMANTIC.__file__).read_bytes()),
        "benchmark_sha256": sha256_bytes(BENCHMARK_PATH.read_bytes()),
        "lean_selector_sha256": LEAN.selector_sha256(),
        "front_selector_sha256": FRONT.selector_sha256(),
        "functions": {
            function.__name__: inspect.getsource(function)
            for function in (
                notable_authored_identifiers,
                normalized_terms,
                current_authored_identifiers,
                choose_holdout,
                packet_id,
                selection_fingerprint,
                _candidate_targets,
                freeze_info,
                frozen_targets,
                query_packets,
                _query_words,
                _copied_source_window,
                validate_queries,
                validate_query_review,
                authored_terms_for_chunk,
                corpus_for_arm,
                load_frozen_inputs,
                query_rows,
                sensitivity_control,
                retrieval_measurement,
                paired_bootstrap,
                decision_rules,
                render_results,
                write_outputs,
                run,
            )
        },
    }
    return sha256_bytes(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def load_frozen_inputs() -> tuple[list, list, dict, dict, dict]:
    sample, selected, identity = frozen_targets()
    if EXPECTED_QUERY_SHA256 == "PENDING":
        raise RuntimeError("identifier-lane query pin is PENDING")
    if not QUERY_PATH.is_file() or sha256_bytes(QUERY_PATH.read_bytes()) != EXPECTED_QUERY_SHA256:
        raise RuntimeError("identifier-lane queries are not frozen")
    queries = json.loads(QUERY_PATH.read_text(encoding="utf-8"))
    validate_queries(queries, selected)
    if EXPECTED_QUERY_REVIEW_SHA256 == "PENDING":
        raise RuntimeError("identifier-lane query review pin is PENDING")
    if not QUERY_REVIEW_PATH.is_file() or sha256_bytes(QUERY_REVIEW_PATH.read_bytes()) != EXPECTED_QUERY_REVIEW_SHA256:
        raise RuntimeError("identifier-lane query review is not frozen")
    review = json.loads(QUERY_REVIEW_PATH.read_text(encoding="utf-8"))
    validate_query_review(review, EXPECTED_QUERY_SHA256, selected)
    return sample, selected, queries, review, identity


def query_rows(selected: list, payload: dict) -> list[dict]:
    targets = {packet_id(chunk.chunk_id): chunk.chunk_id for chunk in selected}
    rows = []
    for item in payload["queries"]:
        for kind in ("semantic", "identifier"):
            rows.append({
                "packet_id": item["packet_id"],
                "kind": kind,
                "query": item[f"{kind}_query"],
                "target": targets[item["packet_id"]],
            })
    return rows


def sensitivity_control(sample: list) -> dict:
    if len(sample) < 3:
        raise ValueError("sensitivity control needs at least three chunks")
    neutral = [replace(
        chunk,
        title="",
        entry_title="",
        heading_path=(),
        text="neutral control body",
        lexical_terms=(),
        topics=(),
        inferred_topics=(),
        inferred_decision_topics=(),
        tags=(),
    ) for chunk in sample[:3]]
    target_id = neutral[1].chunk_id
    current = [replace(chunk, lexical_terms=(("rare_symbol.py",) if index == 1 else ()))
               for index, chunk in enumerate(neutral)]
    normalized = [replace(chunk, lexical_terms=((SEMANTIC._normalize("rare_symbol.py"),) if index == 1 else ()))
                  for index, chunk in enumerate(neutral)]
    query = "Where is rare_symbol.py configured?"

    def result(corpus):
        ranked = BENCHMARK.rank_memory_chunks(
            query, corpus, top_k=len(corpus), recency_enabled=False, embedding_provider=None
        )
        target = next(item for item in ranked if item.chunk.chunk_id == target_id)
        return {
            "target_rank": next(index for index, item in enumerate(ranked, 1) if item.chunk.chunk_id == target_id),
            "target_lexical_score": target.lexical_score,
            "target_matched_fields": list(target.matched_fields),
        }

    raw = result(current)
    fixed = result(normalized)
    return {
        "query": query,
        "current_representation": raw,
        "normalized_representation": fixed,
        "passes": (
            raw["target_lexical_score"] == 0.0
            and "lexical_terms" not in raw["target_matched_fields"]
            and fixed["target_lexical_score"] > 0.0
            and "lexical_terms" in fixed["target_matched_fields"]
            and fixed["target_rank"] == 1
        ),
    }


def retrieval_measurement(sample: list, selected: list, payload: dict) -> tuple[dict, list[dict]]:
    rows = query_rows(selected, payload)
    per_query = [{
        "packet_id": row["packet_id"],
        "kind": row["kind"],
        "target": row["target"],
        "arms": {},
    } for row in rows]
    aggregates = {}
    for arm in ARMS:
        corpus = corpus_for_arm(sample, arm)
        for row, record in zip(rows, per_query):
            ranked = BENCHMARK.rank_memory_chunks(
                row["query"], corpus, top_k=len(corpus), recency_enabled=False, embedding_provider=None
            )
            target = next(item for item in ranked if item.chunk.chunk_id == row["target"])
            record["arms"][arm] = {
                "target_rank": next(index for index, item in enumerate(ranked, 1)
                                    if item.chunk.chunk_id == row["target"]),
                "target_lexical_score": target.lexical_score,
                "target_lexical_field_match": "lexical_terms" in target.matched_fields,
                "lexical_field_match_count": sum("lexical_terms" in item.matched_fields for item in ranked),
                "top_5": [item.chunk.chunk_id for item in ranked[:5]],
                "full_order_sha256": sha256_bytes(
                    "\n".join(item.chunk.chunk_id for item in ranked).encode("utf-8")
                ),
            }
        aggregates[arm] = {}
        for kind in ("semantic", "identifier", "all"):
            applicable = per_query if kind == "all" else [row for row in per_query if row["kind"] == kind]
            ranks = [row["arms"][arm]["target_rank"] for row in applicable]
            aggregates[arm][kind] = {
                "query_count": len(ranks),
                "recall_at_1": sum(rank <= 1 for rank in ranks) / len(ranks),
                "recall_at_3": sum(rank <= 3 for rank in ranks) / len(ranks),
                "recall_at_5": sum(rank <= 5 for rank in ranks) / len(ranks),
                "mrr": sum(1 / rank for rank in ranks) / len(ranks),
            }
    for arm in ARMS:
        aggregates[arm]["exposure"] = {
            "queries_with_any_lexical_field_match": sum(
                row["arms"][arm]["lexical_field_match_count"] > 0 for row in per_query
            ),
            "targets_with_lexical_field_match": sum(
                row["arms"][arm]["target_lexical_field_match"] for row in per_query
            ),
            "full_order_changes_vs_body_only": sum(
                row["arms"][arm]["full_order_sha256"] != row["arms"]["body_only"]["full_order_sha256"]
                for row in per_query
            ),
            "target_rank_changes_vs_body_only": sum(
                row["arms"][arm]["target_rank"] != row["arms"]["body_only"]["target_rank"]
                for row in per_query
            ),
            "target_score_changes_vs_body_only": sum(
                row["arms"][arm]["target_lexical_score"] != row["arms"]["body_only"]["target_lexical_score"]
                for row in per_query
            ),
        }
    return aggregates, per_query


def paired_bootstrap(per_query: list[dict], *, kind: str, treatment: str,
                     control: str, samples: int = 10000) -> dict:
    rows = [row for row in per_query if row["kind"] == kind]
    differences = [
        1 / row["arms"][treatment]["target_rank"] - 1 / row["arms"][control]["target_rank"]
        for row in rows
    ]
    generator = random.Random(20260810)
    draws = []
    for _ in range(samples):
        draw = [differences[generator.randrange(len(differences))] for _ in differences]
        draws.append(sum(draw) / len(draw))
    draws.sort()
    return {
        "kind": kind,
        "treatment": treatment,
        "control": control,
        "decision_count": len(rows),
        "difference": sum(differences) / len(differences),
        "improved_count": sum(value > 0 for value in differences),
        "regressed_count": sum(value < 0 for value in differences),
        "unchanged_count": sum(value == 0 for value in differences),
        "bootstrap_95_ci": [draws[int(samples * 0.025)], draws[int(samples * 0.975) - 1]],
        "bootstrap_samples": samples,
        "seed": 20260810,
    }


def decision_rules(effects: dict) -> dict:
    outcomes = {}
    for arm in ("normalized_current_terms", "normalized_authored_terms", "normalized_union_terms"):
        identifier = {
            control: effects[f"{arm}_vs_{control}_identifier_mrr"]
            for control in ("body_only", "current_lexical_terms")
        }
        semantic = {
            control: effects[f"{arm}_vs_{control}_semantic_mrr"]
            for control in ("body_only", "current_lexical_terms")
        }
        semantic_non_inferior = all(
            effect["bootstrap_95_ci"][0] >= -0.02 for effect in semantic.values()
        )
        semantic_point_regressive = any(
            effect["difference"] < -0.02 for effect in semantic.values()
        )
        identifier_positive = all(effect["difference"] > 0 for effect in identifier.values())
        identifier_validated = all(
            effect["bootstrap_95_ci"][0] > 0 for effect in identifier.values()
        )
        if semantic_point_regressive:
            classification = "regressive"
        elif not semantic_non_inferior:
            classification = "semantic-noninferiority-not-established"
        elif identifier_validated:
            classification = "validated-on-this-holdout"
        elif identifier_positive:
            classification = "promising-not-validated"
        else:
            classification = "no-improvement"
        outcomes[arm] = {
            "classification": classification,
            "semantic_point_estimate_regressive_vs_either_control": semantic_point_regressive,
            "semantic_non_inferior_vs_both_controls": semantic_non_inferior,
            "identifier_point_estimate_positive_vs_both_controls": identifier_positive,
            "identifier_ci_lower_bound_positive_vs_both_controls": identifier_validated,
            "semantic_non_inferiority_margin": -0.02,
        }
    return outcomes


def render_results(metrics: dict) -> str:
    lines = [
        "# Identifier-lane held-out diagnostic",
        "",
        "This target/query set is disjoint from the development set that exposed the normalization defect.",
        "The ranker and BM25F weight are unchanged; only lexical-field representation differs.",
        "",
        "| Arm | Semantic MRR | Identifier MRR | Identifier R@5 | Full-order changes |",
        "|---|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        row = metrics["retrieval"][arm]
        lines.append(
            f"| {arm} | {row['semantic']['mrr']:.3f} | {row['identifier']['mrr']:.3f} | "
            f"{row['identifier']['recall_at_5']:.3f} | {row['exposure']['full_order_changes_vs_body_only']} |"
        )
    lines.extend(["", "## Paired effects", ""])
    for arm in ("normalized_current_terms", "normalized_authored_terms", "normalized_union_terms"):
        for control in ("body_only", "current_lexical_terms"):
            effect = metrics["paired_effects"][f"{arm}_vs_{control}_identifier_mrr"]
            lines.append(
                f"- `{arm}` vs `{control}` identifier MRR: {effect['difference']:+.3f} "
                f"(95% CI {effect['bootstrap_95_ci'][0]:+.3f} to {effect['bootstrap_95_ci'][1]:+.3f}; "
                f"{effect['improved_count']} improved, {effect['regressed_count']} regressed)."
            )
        rule = metrics["decision_rules"][arm]
        lines.append(f"  Decision: **{rule['classification']}**.")
    lines.extend([
        "",
        f"Sensitivity control passed: **{metrics['sensitivity_control']['passes']}**.",
        "A positive point estimate whose interval crosses zero is promising, not validated.",
        "This diagnostic does not authorize a production retrieval change by itself.",
        "",
    ])
    return "\n".join(lines)


def write_outputs(output_dir: Path, metrics: dict) -> None:
    if output_dir.exists():
        raise RuntimeError("identifier-lane output directory must not already exist")
    output_dir.mkdir(parents=True, exist_ok=False)
    metrics_path = output_dir / "identifier-lane-metrics.json"
    results_path = output_dir / "identifier-lane-results.md"
    manifest_path = output_dir / "identifier-lane-run-manifest.json"
    paths = (metrics_path, results_path, manifest_path)
    metrics_bytes = (json.dumps(metrics, indent=2, sort_keys=True) + "\n").encode("utf-8")
    results_bytes = render_results(metrics).encode("utf-8")
    manifest = {
        "schema": "identifier-lane-run-manifest.v1",
        "metrics_sha256": sha256_bytes(metrics_bytes),
        "results_sha256": sha256_bytes(results_bytes),
        "complete": True,
    }
    temporary = [path.with_name("." + path.name + ".tmp") for path in paths]
    temporary[0].write_bytes(metrics_bytes)
    temporary[1].write_bytes(results_bytes)
    temporary[2].write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    for source, destination in zip(temporary, paths):
        source.replace(destination)


def run(output_dir: Path) -> dict:
    if output_dir.exists():
        raise RuntimeError("identifier-lane output directory must not already exist")
    sample, selected, queries, review, identity = load_frozen_inputs()
    sensitivity = sensitivity_control(sample)
    if not sensitivity["passes"]:
        raise RuntimeError("identifier-lane sensitivity control failed")
    retrieval, per_query = retrieval_measurement(sample, selected, queries)
    for arm in ("normalized_current_terms", "normalized_authored_terms", "normalized_union_terms"):
        missing = [
            row["packet_id"] for row in per_query
            if row["kind"] == "identifier" and not row["arms"][arm]["target_lexical_field_match"]
        ]
        if missing:
            raise RuntimeError(f"identifier-lane real-corpus exposure failed for {arm}: {missing}")
    effects = {
        f"{arm}_vs_{control}_{kind}_mrr": paired_bootstrap(
            per_query, kind=kind, treatment=arm, control=control
        )
        for arm in ARMS[1:]
        for control in ("body_only", "current_lexical_terms")
        for kind in ("semantic", "identifier")
        if arm != control
    }
    metrics = {
        "schema": "identifier-lane-ablation.v1",
        "status": "held-out-development-diagnostic",
        "corpus": identity,
        "selection_fingerprint": EXPECTED_SELECTION_FINGERPRINT,
        "selector_sha256": EXPECTED_SELECTOR_SHA256,
        "query_sha256": EXPECTED_QUERY_SHA256,
        "query_review_sha256": EXPECTED_QUERY_REVIEW_SHA256,
        "query_review": {"review_count": len(review["reviews"]), "accepted_count": len(review["reviews"])},
        "limitations": [
            "30 held-out decisions remain a modest sample for a confidence-bound claim",
            "identifier queries intentionally contain one exact source-authored identifier",
            "lexical-only ranking disables semantic embeddings, recency, headings, topics, and tags",
        ],
        "sensitivity_control": sensitivity,
        "retrieval": retrieval,
        "paired_effects": effects,
        "decision_rules": decision_rules(effects),
        "per_query": per_query,
    }
    write_outputs(output_dir, metrics)
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("freeze-info", help="emit candidate selector/target pins without authoring data")
    packets = commands.add_parser("query-packets", help="emit source-only holdout authoring packets")
    packets.add_argument("--batch", type=int)
    packets.add_argument("--batches", type=int, default=3)
    commands.add_parser("validate-query-draft", help="validate the query artifact before review")
    commands.add_parser("validate-frozen-inputs", help="validate every score-unlocking pin and receipt")
    runner = commands.add_parser("run", help="score only after query and review hashes are frozen")
    runner.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "freeze-info":
        print(json.dumps(freeze_info(), indent=2, sort_keys=True))
        return 0
    if args.command == "query-packets":
        print(json.dumps(query_packets(args.batch, args.batches), indent=2))
        return 0
    if args.command == "validate-query-draft":
        _, selected, _ = frozen_targets()
        payload = json.loads(QUERY_PATH.read_text(encoding="utf-8"))
        diagnostics = validate_queries(payload, selected)
        print(json.dumps({"query_count": len(diagnostics), "query_sha256": sha256_bytes(QUERY_PATH.read_bytes())}, indent=2))
        return 0
    if args.command == "validate-frozen-inputs":
        _, selected, queries, review, identity = load_frozen_inputs()
        print(json.dumps({
            "source_revision": identity["source_revision"],
            "selection_fingerprint": selection_fingerprint(selected),
            "query_count": len(validate_queries(queries, selected)),
            "review_count": len(validate_query_review(review, EXPECTED_QUERY_SHA256, selected)),
            "ready_to_score": True,
        }, indent=2, sort_keys=True))
        return 0
    metrics = run(args.output_dir)
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
