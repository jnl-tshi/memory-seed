"""Development diagnostic for raw ranking and lossless decision front doors.

This deliberately reuses the completed lean-DRAFT pilot's frozen corpus, targets, and queries,
but it does *not* revise that pilot or claim a new confirmatory result.  Ranking is always against
the raw decision body; treatments change lexical evidence or the post-rank display only.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import math
import random
import re
from dataclasses import replace
from pathlib import Path
from typing import NamedTuple


HERE = Path(__file__).resolve().parent
BENCHMARK_PATH = HERE / "benchmark.py"
LEAN_PATH = HERE / "lean_draft_pilot.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


BENCHMARK = _load_module("semantic_compression_benchmark", BENCHMARK_PATH)
LEAN = _load_module("lean_draft_pilot_for_front_door", LEAN_PATH)

RETRIEVAL_ARMS = ("body_only", "current_lexical_terms", "authored_exact_terms", "union_terms")
DISPLAY_ARMS = ("raw", "current_lean", "complete_dra", "query_evidence")
QUERY_PATH = LEAN.QUERY_PATH
ORACLE_PATH = HERE / "front-door-answer-key.json"
ORACLE_REVIEW_PATH = HERE / "front-door-answer-key-review.json"

# The corpus and query set are inherited from the completed pilot intentionally.  They make this
# a development diagnostic, not an independently preregistered study.
EXPECTED_QUERY_SHA256 = LEAN.EXPECTED_QUERY_SHA256
EXPECTED_SOURCE_REVISION = LEAN.EXPECTED_SOURCE_REVISION
EXPECTED_CORPUS_FINGERPRINT = LEAN.EXPECTED_CORPUS_FINGERPRINT
EXPECTED_SELECTION_FINGERPRINT = LEAN.EXPECTED_SELECTION_FINGERPRINT
EXPECTED_SELECTOR_SHA256 = "sha256:cf4e0627c50c5d20e96aabbeae682a3fcb6b66bea9c21c93ffe8fd4f80951c9c"
EXPECTED_ORACLE_SHA256 = "sha256:f5567e33a2ac839bab5ef797a6e3fc7ba43b777df7a73569466f0d71d46757e5"
EXPECTED_ORACLE_REVIEW_SHA256 = "sha256:b4069c73b88677c1eed0911bfd6c8751d80a7fe3830ae2289a2686bfa3fac561"

FIELD_LINE = re.compile(r"(?m)^[ \t]*-[ \t]+([A-Z])(\d*)[ \t]*:[^\n]*(?:\n|$)")
MALFORMED_DRAFT_FIELD = re.compile(r"(?m)^[ \t]*-[ \t]+[DRAFT]\d*[ \t]+[^:\n]+$")
IDENTIFIER_TOKEN = re.compile(r"[A-Za-z0-9_.:/\\-]+")
ALLOWED_FIELDS = frozenset("DRAFT")


class FieldBlock(NamedTuple):
    label: str
    ordinal: str
    text: str
    start_char: int
    end_char: int


class DisplayResult(NamedTuple):
    text: str
    mode: str
    fallback_reason: str | None
    provenance: tuple[dict, ...]


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def normalize_space(value: str) -> str:
    return " ".join(value.split()).strip()


def identifier_tokens(value: str) -> tuple[str, ...]:
    """Literal identifier candidates; ordinary words are intentionally excluded."""
    values = []
    for token in IDENTIFIER_TOKEN.findall(value):
        token = token.strip(".,:;()[]{}<>")
        if len(token) < 3 or not any(mark in token for mark in "._/-"):
            continue
        if token not in values:
            values.append(token)
    return tuple(values)


def contains_exact_identifier(text: str, identifier: str) -> bool:
    characters = r"A-Za-z0-9_.:/\\-"
    return re.search(
        rf"(?<![{characters}]){re.escape(identifier)}(?![{characters}])", text, re.I
    ) is not None


def field_blocks(text: str) -> tuple[FieldBlock, ...]:
    """Parse DRAFT bullets while retaining their original source slices exactly."""
    if MALFORMED_DRAFT_FIELD.search(text):
        raise ValueError("malformed DRAFT field bullet")
    matches = list(FIELD_LINE.finditer(text))
    if not matches:
        raise ValueError("no DRAFT field bullets")
    if text[:matches[0].start()].strip():
        raise ValueError("unparsed text before first DRAFT field")
    blocks = []
    for index, match in enumerate(matches):
        label = match.group(1)
        if label not in ALLOWED_FIELDS:
            raise ValueError(f"unknown field-like bullet: {label}")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append(
            FieldBlock(
                label=label,
                ordinal=match.group(2),
                text=text[match.start():end],
                start_char=match.start(),
                end_char=end,
            )
        )
    return tuple(blocks)


def complete_dra_or_raw(text: str) -> DisplayResult:
    """Return full D/R/A source blocks, or fail open to raw without transformation."""
    raw = text.strip()
    try:
        blocks = field_blocks(raw)
        labels = {block.label for block in blocks}
        if "D" not in labels or "R" not in labels:
            raise ValueError("missing required D or R field")
        projected_blocks = [block for block in blocks if block.label in {"D", "R", "A"}]
        projection = "".join(block.text for block in projected_blocks).strip()
        if not projection:
            raise ValueError("empty D/R/A projection")
        if len(projection) >= len(raw):
            raise ValueError("projection is not smaller than raw")
        return DisplayResult(
            text=projection,
            mode="complete_dra",
            fallback_reason=None,
            provenance=tuple(
                {
                    "label": block.label,
                    "ordinal": block.ordinal or None,
                    "start_char": block.start_char,
                    "end_char": block.end_char,
                }
                for block in projected_blocks
            ),
        )
    except Exception as exc:
        return DisplayResult(
            text=raw,
            mode="raw_fallback",
            fallback_reason=str(exc),
            provenance=(),
        )


def _content_overlap_count(query: str, candidate: str) -> int:
    query_terms = set(LEAN.normalized_tokens(query, content_only=True))
    candidate_terms = set(LEAN.normalized_tokens(candidate, content_only=True))
    return len(query_terms & candidate_terms)


def _exact_query_identifier_match(query: str, candidate: str) -> bool:
    return any(contains_exact_identifier(candidate, identifier) for identifier in identifier_tokens(query))


def with_query_evidence(text: str, query: str) -> DisplayResult:
    """Add one literal F/T block: exact identifier, then overlap count, then source order.

    The choice depends solely on the query and original F/T source blocks.  It is never a
    rank-derived excerpt and fails open if the extra evidence would erase the context saving.
    """
    front = complete_dra_or_raw(text)
    if front.mode == "raw_fallback":
        return front
    try:
        blocks = field_blocks(text.strip())
        candidates = [
            (index, block, _exact_query_identifier_match(query, block.text), _content_overlap_count(query, block.text))
            for index, block in enumerate(blocks)
            if block.label in {"F", "T"}
        ]
        eligible = [candidate for candidate in candidates if candidate[2] or candidate[3]]
        evidence = None
        if eligible:
            # ``max`` preserves the first source block on a complete tie because the final key is
            # negative source order. Exact identifier evidence always outranks broad prose overlap.
            _, evidence, _, _ = max(eligible, key=lambda item: (item[2], item[3], -item[0]))
        if evidence is None:
            return DisplayResult(front.text, "query_evidence", None, front.provenance)
        projected = front.text.rstrip() + "\n\n" + evidence.text.strip()
        if len(projected) >= len(text.strip()):
            return DisplayResult(
                text.strip(), "raw_fallback", "query evidence projection is not smaller than raw", ()
            )
        return DisplayResult(
            text=projected,
            mode="query_evidence",
            fallback_reason=None,
            provenance=front.provenance + (
                {
                    "label": evidence.label,
                    "ordinal": evidence.ordinal or None,
                    "start_char": evidence.start_char,
                    "end_char": evidence.end_char,
                    "selection": "query_content_or_exact_identifier",
                },
            ),
        )
    except Exception as exc:
        return DisplayResult(text.strip(), "raw_fallback", f"query evidence failed: {exc}", ())


def display(text: str, query: str, arm: str) -> DisplayResult:
    if arm == "raw":
        return DisplayResult(text.strip(), "raw", None, ())
    if arm == "current_lean":
        return DisplayResult(LEAN.representations(text)["lean_front_door"], "current_lean", None, ())
    if arm == "complete_dra":
        return complete_dra_or_raw(text)
    if arm == "query_evidence":
        return with_query_evidence(text, query)
    raise ValueError(f"unknown display arm: {arm}")


def authored_exact_terms(text: str) -> tuple[str, ...]:
    """Uncapped literal backtick anchors, never basename/location aliases.

    The historical pilot's ``simple_anchors`` expands a path into synthesized basename aliases.
    This arm deliberately does not: it measures only exact author-authored evidence that occurs
    at an identifier boundary in the raw source.
    """
    parsed = LEAN.parse_fields(text)
    return tuple(
        anchor
        for anchor in LEAN.exact_anchors(parsed, limit=None)
        if contains_exact_identifier(text, anchor)
    )


def corpus_for_arm(sample: list, arm: str) -> list:
    """Raw bodies for all arms; only the declared lexical-evidence field changes."""
    corpus = []
    for chunk in sample:
        authored = authored_exact_terms(chunk.text)
        if arm == "body_only":
            lexical_terms = ()
        elif arm == "current_lexical_terms":
            lexical_terms = chunk.lexical_terms
        elif arm == "authored_exact_terms":
            lexical_terms = authored
        elif arm == "union_terms":
            lexical_terms = tuple(dict.fromkeys((*chunk.lexical_terms, *authored)))
        else:
            raise ValueError(f"unknown retrieval arm: {arm}")
        corpus.append(
            replace(
                chunk,
                title="",
                entry_title="",
                heading_path=(),
                text=chunk.text,
                lexical_terms=lexical_terms,
                topics=(),
                inferred_topics=(),
                inferred_decision_topics=(),
                tags=(),
            )
        )
    return corpus


def selector_sha256() -> str:
    spec = {
        "schema": "front-door-ablation-selector.v1",
        "retrieval_arms": RETRIEVAL_ARMS,
        "display_arms": DISPLAY_ARMS,
        "patterns": {
            "field_line": FIELD_LINE.pattern,
            "malformed_draft_field": MALFORMED_DRAFT_FIELD.pattern,
            "identifier": IDENTIFIER_TOKEN.pattern,
        },
        "benchmark_sha256": sha256_bytes(BENCHMARK_PATH.read_bytes()),
        "lean_selector_sha256": LEAN.selector_sha256(),
        "functions": {
            function.__name__: inspect.getsource(function)
            for function in (
                identifier_tokens,
                contains_exact_identifier,
                field_blocks,
                complete_dra_or_raw,
                _content_overlap_count,
                _exact_query_identifier_match,
                with_query_evidence,
                display,
                authored_exact_terms,
                corpus_for_arm,
                retrieval_metrics,
                _median,
                _full_source_affordance,
                structural_projection_metrics,
                display_metrics,
                validate_oracle,
                validate_oracle_review,
                load_oracle_review,
                score_oracle_disclosure,
                raw_rank_body_invariant,
                render_results,
            )
        },
    }
    return sha256_bytes(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def frozen_inputs() -> tuple[list, list, dict, dict]:
    decisions, identity = BENCHMARK.frozen_corpus()
    if identity.get("source_revision") != EXPECTED_SOURCE_REVISION:
        raise RuntimeError("unexpected frozen source revision")
    if identity.get("corpus_fingerprint") != EXPECTED_CORPUS_FINGERPRINT:
        raise RuntimeError("unexpected frozen corpus fingerprint")
    sample = BENCHMARK.choose_sample(decisions)
    selected = LEAN.choose_pilot(sample)
    selection = "sha256:" + BENCHMARK.stable(json.dumps([chunk.chunk_id for chunk in selected]))
    if selection != EXPECTED_SELECTION_FINGERPRINT:
        raise RuntimeError("target selection is not frozen")
    if sha256_bytes(QUERY_PATH.read_bytes()) != EXPECTED_QUERY_SHA256:
        raise RuntimeError("query artifact is not frozen")
    if selector_sha256() != EXPECTED_SELECTOR_SHA256:
        raise RuntimeError("selector is not frozen")
    payload = json.loads(QUERY_PATH.read_text(encoding="utf-8"))
    LEAN.validate_queries(payload, selected)
    return sample, selected, payload, identity


def query_rows(selected: list, payload: dict) -> list[dict]:
    targets = {LEAN.packet_id(chunk.chunk_id): chunk.chunk_id for chunk in selected}
    rows = []
    for item in payload["queries"]:
        for kind in ("semantic", "anchor"):
            rows.append(
                {
                    "packet_id": item["packet_id"],
                    "kind": kind,
                    "query": item[f"{kind}_query"],
                    "target": targets[item["packet_id"]],
                }
            )
    return rows


def retrieval_metrics(sample: list, selected: list, query_payload: dict) -> tuple[dict, list[dict]]:
    rows = query_rows(selected, query_payload)
    rank_table = [
        {"packet_id": row["packet_id"], "kind": row["kind"], "ranks": {}}
        for row in rows
    ]
    metrics: dict[str, dict] = {}
    for arm in RETRIEVAL_ARMS:
        corpus = corpus_for_arm(sample, arm)
        metrics[arm] = {}
        for kind in ("semantic", "anchor", "all"):
            applicable = rows if kind == "all" else [row for row in rows if row["kind"] == kind]
            ranks = []
            for row in applicable:
                ranked = BENCHMARK.rank_memory_chunks(
                    row["query"], corpus, top_k=len(corpus), recency_enabled=False, embedding_provider=None
                )
                rank = next(
                    (index for index, result in enumerate(ranked, 1)
                     if result.chunk.chunk_id == row["target"]),
                    len(corpus) + 1,
                )
                ranks.append(rank)
                if kind != "all":
                    next(
                        item for item in rank_table
                        if item["packet_id"] == row["packet_id"] and item["kind"] == kind
                    )["ranks"][arm] = rank
            metrics[arm][kind] = {
                "query_count": len(ranks),
                "recall_at_1": sum(rank <= 1 for rank in ranks) / len(ranks),
                "recall_at_3": sum(rank <= 3 for rank in ranks) / len(ranks),
                "recall_at_5": sum(rank <= 5 for rank in ranks) / len(ranks),
                "mrr": sum(1 / rank for rank in ranks) / len(ranks),
            }
    return metrics, rank_table


def paired_bootstrap(rank_table: list[dict], *, kind: str, treatment: str,
                     control: str, samples: int = 10000) -> dict:
    rows = [row for row in rank_table if row["kind"] == kind]
    differences = [1 / row["ranks"][treatment] - 1 / row["ranks"][control] for row in rows]
    generator = random.Random(20260810)
    draws = []
    for _ in range(samples):
        values = [differences[generator.randrange(len(differences))] for _ in differences]
        draws.append(sum(values) / len(values))
    draws.sort()
    return {
        "kind": kind,
        "treatment": treatment,
        "control": control,
        "decision_count": len(rows),
        "difference": sum(differences) / len(differences),
        "bootstrap_95_ci": [draws[int(samples * 0.025)], draws[int(samples * 0.975) - 1]],
        "bootstrap_samples": samples,
        "seed": 20260810,
    }


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    return ordered[midpoint] if len(ordered) % 2 else (ordered[midpoint - 1] + ordered[midpoint]) / 2


def _full_source_affordance(decision_ref: str) -> str:
    return f"Full source: {decision_ref}"


def structural_projection_metrics(sample: list) -> dict:
    """All-100 structural checks: source-preserving projection, context and fail-open behavior."""
    raw_bytes = []
    raw_tokens = []
    projected_bytes = []
    projected_tokens = []
    projected_source_bytes = []
    effective_bytes = []
    effective_tokens = []
    fallback_reasons: dict[str, int] = {}
    integrity_total = 0
    integrity_visible = 0
    for chunk in sample:
        raw = chunk.text.strip()
        raw_bytes.append(len(raw.encode("utf-8")))
        raw_tokens.append(BENCHMARK.token_proxy(raw))
        rendered = complete_dra_or_raw(raw)
        if rendered.fallback_reason:
            fallback_reasons[rendered.fallback_reason] = fallback_reasons.get(rendered.fallback_reason, 0) + 1
            effective_bytes.append(raw_bytes[-1])
            effective_tokens.append(raw_tokens[-1])
            continue
        projected_bytes.append(len(rendered.text.encode("utf-8")))
        projected_tokens.append(BENCHMARK.token_proxy(rendered.text))
        projected_source_bytes.append(raw_bytes[-1])
        effective_bytes.append(projected_bytes[-1])
        effective_tokens.append(projected_tokens[-1])
        for item in rendered.provenance:
            integrity_total += 1
            source_span = raw[item["start_char"]:item["end_char"]].strip()
            integrity_visible += int(bool(source_span) and source_span in rendered.text)
    fallback_count = sum(fallback_reasons.values())
    return {
        "sample_count": len(sample),
        "raw_mean_utf8_bytes": sum(raw_bytes) / len(raw_bytes),
        "raw_median_utf8_bytes": _median(raw_bytes),
        "raw_mean_token_proxy": sum(raw_tokens) / len(raw_tokens),
        "raw_median_token_proxy": _median(raw_tokens),
        "projected_count": len(projected_bytes),
        "projected_mean_utf8_bytes": sum(projected_bytes) / len(projected_bytes) if projected_bytes else 0.0,
        "projected_median_utf8_bytes": _median(projected_bytes) if projected_bytes else 0.0,
        "projected_mean_token_proxy": sum(projected_tokens) / len(projected_tokens) if projected_tokens else 0.0,
        "projected_median_token_proxy": _median(projected_tokens) if projected_tokens else 0.0,
        "successful_projection_to_source_utf8_ratio": (
            sum(projected_bytes) / sum(projected_source_bytes) if projected_bytes else 0.0
        ),
        "effective_with_fallback_to_raw_utf8_ratio": sum(effective_bytes) / sum(raw_bytes),
        "effective_with_fallback_to_raw_token_ratio": sum(effective_tokens) / sum(raw_tokens),
        "fallback_count": fallback_count,
        "fallback_rate": fallback_count / len(sample),
        "fallback_reasons": fallback_reasons,
        "dra_projection_integrity": {
            "source_block_count": integrity_total,
            "exact_source_block_visible_count": integrity_visible,
            "exact_source_block_visible_rate": integrity_visible / integrity_total if integrity_total else 0.0,
        },
    }


def display_metrics(selected: list, payload: dict) -> dict:
    source_by_packet = {LEAN.packet_id(chunk.chunk_id): chunk for chunk in selected}
    rows = query_rows(selected, payload)
    output = {
        arm: {"count": 0, "utf8_bytes": [], "token_proxy": [], "raw_utf8_bytes": [], "affordance_utf8_bytes": [],
              "fallback_count": 0, "fallback_reasons": {}, "identifier_query_count": 0,
              "identifier_query_display_covered_count": 0}
        for arm in DISPLAY_ARMS
    }
    for row in rows:
        chunk = source_by_packet[row["packet_id"]]
        source = chunk.text
        source_identifiers = [
            identifier for identifier in identifier_tokens(row["query"])
            if contains_exact_identifier(source, identifier)
        ]
        for arm in DISPLAY_ARMS:
            rendered = display(source, row["query"], arm)
            record = output[arm]
            shown = rendered.text
            affordance_bytes = 0
            if arm != "raw":
                affordance = _full_source_affordance(chunk.chunk_id)
                shown += "\n\n" + affordance
                affordance_bytes = len(("\n\n" + affordance).encode("utf-8"))
            record["count"] += 1
            record["utf8_bytes"].append(len(shown.encode("utf-8")))
            record["token_proxy"].append(BENCHMARK.token_proxy(shown))
            record["raw_utf8_bytes"].append(len(source.strip().encode("utf-8")))
            record["affordance_utf8_bytes"].append(affordance_bytes)
            if rendered.fallback_reason:
                record["fallback_count"] += 1
                record["fallback_reasons"][rendered.fallback_reason] = (
                    record["fallback_reasons"].get(rendered.fallback_reason, 0) + 1
                )
            if source_identifiers:
                record["identifier_query_count"] += 1
                record["identifier_query_display_covered_count"] += int(
                    all(contains_exact_identifier(shown, identifier) for identifier in source_identifiers)
                )
    for record in output.values():
        record["mean_displayed_utf8_bytes"] = sum(record["utf8_bytes"]) / record["count"]
        record["median_displayed_utf8_bytes"] = _median(record["utf8_bytes"])
        record["mean_displayed_token_proxy"] = sum(record["token_proxy"]) / record["count"]
        record["median_displayed_token_proxy"] = _median(record["token_proxy"])
        record["mean_full_source_affordance_utf8_bytes"] = sum(record["affordance_utf8_bytes"]) / record["count"]
        record["mean_displayed_to_raw_utf8_ratio"] = sum(record["utf8_bytes"]) / sum(record["raw_utf8_bytes"])
        record["median_displayed_to_raw_utf8_ratio"] = _median(
            [shown / raw for shown, raw in zip(record["utf8_bytes"], record["raw_utf8_bytes"])]
        )
        record["fallback_rate"] = record["fallback_count"] / record["count"]
        record["query_identifier_display_coverage"] = (
            record["identifier_query_display_covered_count"] / record["identifier_query_count"]
            if record["identifier_query_count"] else 0.0
        )
        record["full_source_affordance"] = "Full source: <decision_ref>" if record is not output["raw"] else None
        del record["utf8_bytes"]
        del record["token_proxy"]
        del record["raw_utf8_bytes"]
        del record["affordance_utf8_bytes"]
    return output


def oracle_packets() -> list[dict]:
    _, selected, payload, _ = frozen_inputs()
    by_packet = {item["packet_id"]: item for item in payload["queries"]}
    return [
        {
            "packet_id": LEAN.packet_id(chunk.chunk_id),
            "source": chunk.text,
            "semantic_query": by_packet[LEAN.packet_id(chunk.chunk_id)]["semantic_query"],
            "anchor_query": by_packet[LEAN.packet_id(chunk.chunk_id)]["anchor_query"],
        }
        for chunk in selected
    ]


def validate_oracle(payload: dict, selected: list, query_payload: dict) -> list[dict]:
    if payload.get("schema") != "front-door-answer-key.v1":
        raise ValueError("unexpected oracle schema")
    sources = {LEAN.packet_id(chunk.chunk_id): chunk.text for chunk in selected}
    expected = {(packet, kind) for packet in sources for kind in ("semantic", "anchor")}
    answers = payload.get("answers", [])
    seen = set()
    diagnostics = []
    for answer in answers:
        key = (answer.get("packet_id"), answer.get("kind"))
        if key not in expected or key in seen:
            raise ValueError(f"unknown or duplicate oracle answer: {key}")
        seen.add(key)
        spans = answer.get("spans")
        if not isinstance(spans, list) or not 1 <= len(spans) <= 3:
            raise ValueError(f"{key} needs 1-3 exact source spans")
        source = sources[key[0]]
        unique_spans = set()
        for span in spans:
            start, end = span.get("start_char"), span.get("end_char")
            if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(source):
                raise ValueError(f"{key} has invalid source span")
            if start == 0 and end == len(source):
                raise ValueError(f"{key} may not use the whole source as an answer span")
            if not isinstance(span.get("text"), str):
                raise ValueError(f"{key} span text is required")
            if span["text"] != source[start:end]:
                raise ValueError(f"{key} span text is not exact source text")
            coordinate = (start, end)
            if coordinate in unique_spans:
                raise ValueError(f"{key} contains a duplicate source span")
            unique_spans.add(coordinate)
        diagnostics.append({"packet_id": key[0], "kind": key[1], "span_count": len(spans)})
    if seen != expected:
        raise ValueError("oracle must cover every semantic and anchor query exactly once")
    return diagnostics


def load_oracle(selected: list, query_payload: dict) -> dict:
    if EXPECTED_ORACLE_SHA256 == "PENDING":
        raise RuntimeError("oracle pin is PENDING; packets may be generated but scoring is blocked")
    if not ORACLE_PATH.is_file():
        raise RuntimeError("oracle answer key is missing")
    actual = sha256_bytes(ORACLE_PATH.read_bytes())
    if actual != EXPECTED_ORACLE_SHA256:
        raise RuntimeError("oracle answer key is not frozen")
    payload = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
    validate_oracle(payload, selected, query_payload)
    return payload


def validate_oracle_review(payload: dict, oracle_sha256: str, selected: list) -> list[dict]:
    """Require a source-only reviewer acceptance receipt for each oracle query."""
    if payload.get("schema") != "front-door-answer-key-review.v1":
        raise ValueError("unexpected oracle review schema")
    if payload.get("oracle_sha256") != oracle_sha256:
        raise ValueError("oracle review does not match the frozen oracle hash")
    if not str(payload.get("reviewer_model", "")).strip():
        raise ValueError("oracle review must identify the reviewer model")
    if payload.get("input_access") != "canonical-source-query-and-oracle-spans-only":
        raise ValueError("oracle review input access is not the frozen source-only contract")
    if payload.get("ranking_results_seen") is not False or payload.get("display_candidates_seen") is not False:
        raise ValueError("oracle reviewer must not see rankings or display candidates")
    expected = {(LEAN.packet_id(chunk.chunk_id), kind) for chunk in selected for kind in ("semantic", "anchor")}
    seen = set()
    diagnostics = []
    for review in payload.get("reviews", []):
        key = (review.get("packet_id"), review.get("kind"))
        if key not in expected or key in seen:
            raise ValueError(f"unknown or duplicate oracle review: {key}")
        seen.add(key)
        if review.get("accepted") is not True:
            raise ValueError(f"oracle review rejected or did not accept: {key}")
        diagnostics.append({"packet_id": key[0], "kind": key[1], "accepted": True})
    if seen != expected:
        raise ValueError("oracle review must accept all 60 queries exactly once")
    return diagnostics


def load_oracle_review(selected: list, oracle_sha256: str) -> dict:
    if EXPECTED_ORACLE_REVIEW_SHA256 == "PENDING":
        raise RuntimeError("oracle review pin is PENDING; scoring is blocked")
    if not ORACLE_REVIEW_PATH.is_file():
        raise RuntimeError("oracle review artifact is missing")
    actual = sha256_bytes(ORACLE_REVIEW_PATH.read_bytes())
    if actual != EXPECTED_ORACLE_REVIEW_SHA256:
        raise RuntimeError("oracle review artifact is not frozen")
    payload = json.loads(ORACLE_REVIEW_PATH.read_text(encoding="utf-8"))
    validate_oracle_review(payload, oracle_sha256, selected)
    return payload


def score_oracle_disclosure(oracle: dict, selected: list, query_payload: dict) -> dict:
    """Future scoring hook: span and all-required-span visibility per display arm."""
    sources = {LEAN.packet_id(chunk.chunk_id): chunk.text for chunk in selected}
    queries = {(row["packet_id"], row["kind"]): row["query"] for row in query_rows(selected, query_payload)}
    total = {arm: 0 for arm in DISPLAY_ARMS}
    visible = {arm: 0 for arm in DISPLAY_ARMS}
    query_total = {arm: 0 for arm in DISPLAY_ARMS}
    query_all_visible = {arm: 0 for arm in DISPLAY_ARMS}
    by_kind = {
        arm: {
            kind: {"visible": 0, "total": 0, "queries": 0, "all_visible": 0}
            for kind in ("semantic", "anchor")
        }
        for arm in DISPLAY_ARMS
    }
    for answer in oracle["answers"]:
        packet = answer["packet_id"]
        query = queries[(packet, answer["kind"])]
        source = sources[packet]
        for arm in DISPLAY_ARMS:
            rendered = display(source, query, arm).text
            all_visible = True
            for span in answer["spans"]:
                total[arm] += 1
                by_kind[arm][answer["kind"]]["total"] += 1
                if source[span["start_char"]:span["end_char"]] in rendered:
                    visible[arm] += 1
                    by_kind[arm][answer["kind"]]["visible"] += 1
                else:
                    all_visible = False
            query_total[arm] += 1
            query_all_visible[arm] += int(all_visible)
            by_kind[arm][answer["kind"]]["queries"] += 1
            by_kind[arm][answer["kind"]]["all_visible"] += int(all_visible)
    return {
        arm: {"visible_span_count": visible[arm], "span_count": total[arm],
              "coverage": visible[arm] / total[arm] if total[arm] else 0.0,
              "query_count": query_total[arm], "all_required_spans_visible_count": query_all_visible[arm],
              "all_required_spans_visible_rate": (
                  query_all_visible[arm] / query_total[arm] if query_total[arm] else 0.0
              ),
              "by_kind": {
                  kind: {
                      "visible_span_count": by_kind[arm][kind]["visible"],
                      "span_count": by_kind[arm][kind]["total"],
                      "coverage": (
                          by_kind[arm][kind]["visible"] / by_kind[arm][kind]["total"]
                          if by_kind[arm][kind]["total"] else 0.0
                      ),
                      "query_count": by_kind[arm][kind]["queries"],
                      "all_required_spans_visible_count": by_kind[arm][kind]["all_visible"],
                      "all_required_spans_visible_rate": (
                          by_kind[arm][kind]["all_visible"] / by_kind[arm][kind]["queries"]
                          if by_kind[arm][kind]["queries"] else 0.0
                      ),
                  }
                  for kind in ("semantic", "anchor")
              }}
        for arm in DISPLAY_ARMS
    }


def raw_rank_body_invariant(sample: list) -> dict:
    mismatches = []
    expected = [(chunk.chunk_id, chunk.text) for chunk in sample]
    for arm in RETRIEVAL_ARMS:
        actual = [(chunk.chunk_id, chunk.text) for chunk in corpus_for_arm(sample, arm)]
        if actual != expected:
            mismatches.append(arm)
    return {
        "holds": not mismatches,
        "mismatched_retrieval_arms": mismatches,
        "rank_surface": "raw decision body plus the declared lexical-evidence arm only",
        "display_arms_excluded_from_ranking": list(DISPLAY_ARMS),
        "shared_rank_table": "one rank table is reused for every display arm",
    }


def render_results(metrics: dict) -> str:
    """Short diagnostic narrative; it does not make a human-performance claim."""
    lines = [
        "# Front-door development diagnostic",
        "",
        "This reuses the earlier source-conditioned development set. Ranking evaluates raw decision bodies; "
        "display arms never enter the ranker and this is not human-comprehension evidence.",
        "",
        "| Retrieval arm | Semantic MRR | Identifier MRR |",
        "|---|---:|---:|",
    ]
    for arm in RETRIEVAL_ARMS:
        lines.append(
            f"| {arm} | {metrics['retrieval'][arm]['semantic']['mrr']:.3f} | "
            f"{metrics['retrieval'][arm]['anchor']['mrr']:.3f} |"
        )
    lines.extend(["", "| Display arm | Mean displayed bytes | Mean raw-context ratio | Fallback rate |", "|---|---:|---:|---:|"])
    for arm in DISPLAY_ARMS:
        row = metrics["display"][arm]
        lines.append(
            f"| {arm} | {row['mean_displayed_utf8_bytes']:.1f} | "
            f"{row['mean_displayed_to_raw_utf8_ratio']:.3f} | {row['fallback_rate']:.1%} |"
        )
    union_body = metrics["paired_effects"]["union_terms_vs_body_only_anchor_mrr"]
    union_current = metrics["paired_effects"]["union_terms_vs_current_lexical_terms_anchor_mrr"]
    union_semantic = metrics["paired_effects"]["union_terms_vs_body_only_semantic_mrr"]
    disclosure = metrics["oracle_disclosure"]["query_evidence"]
    display_row = metrics["display"]["query_evidence"]
    lines.extend([
        "",
        "The `Full source: <decision_ref>` affordance is included in every non-raw display size. "
        "All displayed D/R/A source blocks are checked mechanically for exact projection integrity.",
        "",
        "## Gate observations",
        "",
        f"- Union identifier terms versus body-only identifier MRR: {union_body['difference']:+.3f} "
        f"(95% CI {union_body['bootstrap_95_ci'][0]:+.3f} to {union_body['bootstrap_95_ci'][1]:+.3f}).",
        f"- Union identifier terms versus the current lexical-term field: {union_current['difference']:+.3f} "
        f"(95% CI {union_current['bootstrap_95_ci'][0]:+.3f} to {union_current['bootstrap_95_ci'][1]:+.3f}).",
        f"- Union semantic MRR versus body-only: {union_semantic['difference']:+.3f} "
        f"(95% CI {union_semantic['bootstrap_95_ci'][0]:+.3f} to {union_semantic['bootstrap_95_ci'][1]:+.3f}).",
        f"- Query-evidence display retains {disclosure['coverage']:.1%} of source-only answer spans and "
        f"all required spans on {disclosure['all_required_spans_visible_rate']:.1%} of queries.",
        f"- Query-evidence median first-view context, including the full-source affordance, is "
        f"{display_row['median_displayed_to_raw_utf8_ratio']:.1%} of raw.",
        "- These are development-set retrieval and evidence-disclosure measurements, not human "
        "comprehension, writing-quality, or delayed-recall results.",
        "",
    ])
    return "\n".join(lines)


def run(output_dir: Path = HERE) -> dict:
    sample, selected, query_payload, identity = frozen_inputs()
    # Both external gates are deliberately before every output write.  Packets are the only
    # pre-oracle action, so no partial metrics/result artifact can be mistaken for scored evidence.
    oracle = load_oracle(selected, query_payload)
    oracle_sha256 = sha256_bytes(ORACLE_PATH.read_bytes())
    review = load_oracle_review(selected, oracle_sha256)
    retrieval, rank_table = retrieval_metrics(sample, selected, query_payload)
    effects = {
        f"{arm}_vs_body_only_{kind}_mrr": paired_bootstrap(
            rank_table, kind=kind, treatment=arm, control="body_only"
        )
        for arm in RETRIEVAL_ARMS[1:]
        for kind in ("semantic", "anchor")
    }
    effects.update({
        f"{arm}_vs_current_lexical_terms_{kind}_mrr": paired_bootstrap(
            rank_table, kind=kind, treatment=arm, control="current_lexical_terms"
        )
        for arm in ("authored_exact_terms", "union_terms")
        for kind in ("semantic", "anchor")
    })
    metrics = {
        "schema": "front-door-ablation.v1",
        "status": "development-diagnostic-not-human-comprehension",
        "corpus": identity,
        "query_sha256": EXPECTED_QUERY_SHA256,
        "selector_sha256": selector_sha256(),
        "selection_fingerprint": EXPECTED_SELECTION_FINGERPRINT,
        "oracle_sha256": EXPECTED_ORACLE_SHA256,
        "oracle_review_sha256": EXPECTED_ORACLE_REVIEW_SHA256,
        "limitations": [
            "reuses the lean pilot's source-conditioned 30 target / 60 query development set",
            "ranking changes lexical evidence only; display never affects rank input",
            "oracle span disclosure is not human comprehension or delayed recall",
        ],
        "retrieval": retrieval,
        "paired_effects": effects,
        "display": display_metrics(selected, query_payload),
        "structural_projection": structural_projection_metrics(sample),
        "oracle_disclosure": score_oracle_disclosure(oracle, selected, query_payload),
        "oracle_review": {"review_count": len(review["reviews"]), "accepted_count": len(review["reviews"]),
                          "rejected_count": 0},
        "shared_display_rank_invariant": raw_rank_body_invariant(sample),
    }
    rendered_metrics = json.dumps(metrics, indent=2, sort_keys=True) + "\n"
    rendered_results = render_results(metrics)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "front-door-ablation-metrics.json").write_text(
        rendered_metrics, encoding="utf-8", newline="\n"
    )
    (output_dir / "front-door-results.md").write_text(rendered_results, encoding="utf-8", newline="\n")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("oracle-packets", help="emit source plus both frozen queries; no scoring required")
    run_parser = sub.add_parser("run", help="score only after the frozen answer-key pin is set")
    run_parser.add_argument("--output-dir", type=Path, default=HERE)
    args = parser.parse_args()
    if args.command == "oracle-packets":
        print(json.dumps({"schema": "front-door-oracle-packets.v1", "packets": oracle_packets()}, indent=2))
    else:
        print(json.dumps(run(args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
