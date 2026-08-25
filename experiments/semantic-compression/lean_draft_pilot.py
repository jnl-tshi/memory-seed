"""Feasibility pilot for a lean Memory Seed decision front door.

The pilot is intentionally derived, extractive, and isolated.  It tests whether a compact
decision/rationale/boundary card can retain retrieval utility when exact source identifiers are
preserved.  It does not rewrite canonical entries or test natural authoring behaviour.
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
from collections import Counter
from dataclasses import replace
from pathlib import Path


HERE = Path(__file__).resolve().parent
BENCHMARK_PATH = HERE / "benchmark.py"
SPEC = importlib.util.spec_from_file_location("semantic_compression_benchmark", BENCHMARK_PATH)
BENCHMARK = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(BENCHMARK)

ARMS = ("raw", "decision_only", "lean_no_supplemental_anchors", "lean_front_door")
QUERY_PATH = HERE / "lean-draft-queries.json"
REVIEW_DIR = HERE / "lean-draft-readability-reviews"
ADJUDICATION_PATH = HERE / "lean-draft-readability-adjudication.json"
EXPECTED_QUERY_SHA256 = "sha256:18ee379659abc407435071eb465565e4dd0b661364b089a1ed56ea8c6a34bcbd"
EXPECTED_REVIEW_SHA256 = {
    "A0.json": "sha256:c63e97de5ea56fd5adf4f4addbee94a1f2d7481d37c0d405109d0f6c150aaf1b",
    "A1.json": "sha256:0456531e558f566d5b691f3e45e91989f73626cfbed7fc3505bba00494e90094",
    "B0.json": "sha256:49ac0bb82e090d70df8452ef7baebafd0e89187f676092eb43b84bb673525a24",
    "B1.json": "sha256:00283ecb78a4781f57a3dce333a9ed3ba5f85e360737f5323052ae12fd0ffc90",
}
EXPECTED_ADJUDICATION_SHA256 = "sha256:b2672745422a25305a5fab8f85195e9a246927a8365be922e47b98180575801f"
EXPECTED_SELECTOR_SHA256 = "sha256:a1b5cea07d493ad793e3a6610b337c8ad8b545e1509c6b07d2f6bbc7a7550dad"
EXPECTED_SELECTION_FINGERPRINT = "sha256:cc25b1744931bb75f7c17ce563c5e965795baa6b2188edef091c1209c00c710a"
EXPECTED_SOURCE_REVISION = "54de83ca7f3e279f1199b721e6aa1bec825e04ac"
EXPECTED_CORPUS_FINGERPRINT = "sha256:ab68ed673415ccf53cc9674476a6f0b49ec2f0cb782cfbc8a26d156d2a64ae00"
FIELD = re.compile(r"^\s*-\s*([DRAFT]):\s*(.*)$")
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z`])")
READABILITY_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
MODAL = re.compile(
    r"\b(must|should|shall|only|never|without|require[ds]?|cannot|can't|do not|don't|"
    r"may not|unless|instead of|refus(?:e|es|ed)|forbid(?:s|den)?)\b",
    re.I,
)
BACKTICK = re.compile(r"`([^`\r\n]{1,100})`")
WORD = re.compile(r"[a-z0-9][a-z0-9_.:/\\-]*", re.I)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "by", "for", "from", "how",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "what",
    "when", "where", "which", "why", "with", "would", "rather", "than",
}


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def normalize_space(value: str) -> str:
    return " ".join(value.split()).strip()


def parse_fields(text: str) -> dict[str, list[str]]:
    found = {label: [] for label in "DRAFT"}
    active: str | None = None
    for line in text.splitlines():
        match = FIELD.match(line)
        if match:
            active = match.group(1)
            found[active].append(match.group(2).strip())
        elif active and line.strip():
            found[active][-1] += " " + line.strip()
    return {label: [normalize_space(value) for value in values if normalize_space(value)]
            for label, values in found.items()}


def sentences(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        out.extend(normalize_space(item) for item in SENTENCE.split(value) if normalize_space(item))
    return out


def exact_anchors(parsed: dict[str, list[str]], selected_text: str = "",
                  limit: int | None = 6) -> list[str]:
    """Return exact, compact identifiers from accepted prose and file evidence.

    Backtick spans are the authored signal that a term is exact.  Long prose-like spans and generic
    literals are excluded; the pilot must not improve retrieval by copying whole source sentences.
    """
    candidates: list[str] = []
    for value in parsed["D"] + parsed["R"] + parsed["F"]:
        for match in BACKTICK.finditer(value):
            span = normalize_space(match.group(1))
            distinctive = []
            for token in WORD.findall(span):
                token = token.rstrip(":")
                if len(token) >= 4 and (re.search(r"[._:/\\-]", token)
                                        or re.search(r"\d", token)
                                        or re.search(r"[a-z][A-Z]", token)
                                        or token.isupper()):
                    distinctive.append(token)
            if any(character.isspace() for character in span) and distinctive:
                candidates.extend(distinctive)
                continue
            if len(span) <= 72 and len(span.split()) <= 4:
                candidates.append(span)
                continue
            # Long command/type expressions are not readable front-door anchors. Preserve their
            # distinctive exact identifiers instead of either copying the whole expression or
            # discarding all of its vocabulary.
            candidates.extend(distinctive)
    selected_lower = selected_text.lower()
    anchors: list[str] = []
    for candidate in candidates:
        compact = normalize_space(candidate)
        if not compact or len(compact) > 72 or len(compact.split()) > 4:
            continue
        if compact.lower() in {"true", "false", "none", "null", "yes", "no"}:
            continue
        # Backticks are the author's exactness signal. Keep ordinary identifier words too, while
        # excluding very short prose fragments and generic literals above.
        if len(compact) < 4:
            continue
        if compact.lower() in selected_lower:
            continue
        if compact not in anchors:
            anchors.append(compact)
        if limit is not None and len(anchors) == limit:
            break
    return anchors


def representations(text: str) -> dict[str, str]:
    parsed = parse_fields(text)
    decision = BENCHMARK.first_sentence(" ".join(parsed["D"])) or BENCHMARK.first_sentence(text)
    rationale = BENCHMARK.first_sentence(" ".join(parsed["R"]))
    accepted = sentences(parsed["D"] + parsed["R"])
    constraints = []
    for item in accepted:
        if MODAL.search(item) and item not in {decision, rationale} and item not in constraints:
            constraints.append(item)
        if len(constraints) == 2:
            break
    lines = ([f"- D: {decision}"] if decision else [])
    if rationale:
        lines.append(f"- R: {rationale}")
    lines.extend(f"- R: {item}" for item in constraints)
    lean_no_anchors = "\n".join(lines)
    anchors = exact_anchors(parsed, lean_no_anchors)
    with_anchors = list(lines)
    if anchors:
        with_anchors.append("- F: " + ", ".join(f"`{item}`" for item in anchors))
    return {
        "raw": text.strip(),
        "decision_only": f"- D: {decision}" if decision else text.strip(),
        "lean_no_supplemental_anchors": lean_no_anchors,
        "lean_front_door": "\n".join(with_anchors),
    }


def selector_sha256() -> str:
    """Fingerprint arm construction, target selection, and the imported Stage-1 helpers.

    This lock was added after the first scored pilot.  It makes subsequent reruns reproducible, but
    it is not evidence of a pre-outcome preregistration.
    """
    spec = {
        "schema": "lean-draft-selector.v1",
        "arms": ARMS,
        "patterns": {
            "field": FIELD.pattern,
            "sentence": SENTENCE.pattern,
            "modal": MODAL.pattern,
            "backtick": BACKTICK.pattern,
            "word": WORD.pattern,
        },
        "stage_1_helper_module_sha256": sha256_bytes(BENCHMARK_PATH.read_bytes()),
        "functions": {
            function.__name__: inspect.getsource(function)
            for function in (
                normalize_space,
                parse_fields,
                sentences,
                exact_anchors,
                representations,
                simple_anchors,
                choose_pilot,
                contains_exact_anchor,
            )
        },
    }
    return sha256_bytes(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def simple_anchors(text: str) -> list[str]:
    parsed = parse_fields(text)
    anchors: list[str] = []
    for item in exact_anchors(parsed, limit=None):
        if len(item.split()) != 1:
            continue
        anchors.append(item)
        basename = re.split(r"[/\\]", item)[-1]
        if basename != item and basename not in anchors:
            anchors.append(basename)
        locationless = re.sub(r":\d+(?:-\d+)?$", "", basename)
        if locationless != basename and locationless not in anchors:
            anchors.append(locationless)
    return anchors


def choose_pilot(sample: list, count: int = 30) -> list:
    """Choose 30 query/review targets across source-length tertiles.

    The anchor-query ablation needs at least one compact exact identifier.  Rationale is required so
    the lean package is not rewarded on trivially one-field decisions.
    """
    eligible = [chunk for chunk in sample if parse_fields(chunk.text)["R"] and simple_anchors(chunk.text)]
    ordered = sorted(eligible, key=lambda chunk: (len(chunk.text), BENCHMARK.stable(chunk.chunk_id)))
    buckets = [[] for _ in range(3)]
    for index, chunk in enumerate(ordered):
        buckets[min(2, index * 3 // max(1, len(ordered)))].append(chunk)
    selected = []
    for bucket in buckets:
        selected.extend(sorted(bucket, key=lambda chunk: BENCHMARK.stable("lean-pilot:" + chunk.chunk_id))[: count // 3])
    if len(selected) != count:
        raise RuntimeError(f"need {count} rationale+anchor decisions, found {len(selected)}")
    return sorted(selected, key=lambda chunk: chunk.chunk_id)


def packet_id(ref: str) -> str:
    return "p_" + BENCHMARK.stable("lean-draft-pilot:" + ref)[:12]


def card_id(ref: str, arm: str) -> str:
    return "c_" + BENCHMARK.stable(f"lean-draft-review:{ref}:{arm}")[:14]


def query_packets(batch: int | None = None, batches: int = 3) -> list[dict[str, str]]:
    decisions, _ = BENCHMARK.frozen_corpus()
    sample = BENCHMARK.choose_sample(decisions)
    selected = choose_pilot(sample)
    packets = [{"packet_id": packet_id(chunk.chunk_id), "source": chunk.text} for chunk in selected]
    if batch is not None:
        packets = [item for index, item in enumerate(packets) if index % batches == batch]
    return packets


def review_packets(batch: int | None = None, batches: int = 2) -> list[dict]:
    decisions, _ = BENCHMARK.frozen_corpus()
    selected = choose_pilot(BENCHMARK.choose_sample(decisions))
    packets = []
    for index, chunk in enumerate(selected):
        if batch is not None and index % batches != batch:
            continue
        reps = representations(chunk.text)
        candidates = [{"card_id": card_id(chunk.chunk_id, arm), "text": reps[arm]}
                      for arm in ARMS]
        candidates.sort(key=lambda item: BENCHMARK.stable("card-order:" + chunk.chunk_id + item["card_id"]))
        packets.append({"packet_id": packet_id(chunk.chunk_id), "source": chunk.text,
                        "candidates": candidates})
    return packets


def normalized_tokens(value: str, *, content_only: bool = False) -> list[str]:
    tokens = [token.lower() for token in WORD.findall(value)]
    return [token for token in tokens if not content_only or token not in STOPWORDS]


def anchor_alias_tokens(value: str) -> set[str]:
    aliases: set[str] = set()
    for token in normalized_tokens(value):
        cleaned = token.strip(":.")
        if cleaned:
            aliases.add(cleaned)
        for part in token.split("::"):
            part = part.strip(":.")
            if part:
                aliases.add(part)
    return aliases


def shared_ngram(query: str, source: str, size: int, *, content_only: bool = False) -> tuple[str, ...] | None:
    query_tokens = normalized_tokens(query, content_only=content_only)
    source_tokens = normalized_tokens(source, content_only=content_only)
    source_ngrams = {tuple(source_tokens[i:i + size]) for i in range(len(source_tokens) - size + 1)}
    return next((tuple(query_tokens[i:i + size]) for i in range(len(query_tokens) - size + 1)
                 if tuple(query_tokens[i:i + size]) in source_ngrams), None)


def validate_queries(payload: dict, selected: list) -> list[dict]:
    if payload.get("schema") != "lean-draft-independent-queries.v1":
        raise ValueError("unexpected query artifact schema")
    expected = {packet_id(chunk.chunk_id): chunk for chunk in selected}
    rows = payload.get("queries", [])
    if len(rows) != len(expected):
        raise ValueError("query artifact must contain exactly one row per packet")
    if {row.get("packet_id") for row in rows} != set(expected):
        raise ValueError("query packet ids must match the frozen 30-target selection exactly")
    normalized_query_texts = [normalize_space(str(row.get(kind, ""))).lower()
                              for row in rows for kind in ("semantic_query", "anchor_query")]
    if len(normalized_query_texts) != len(set(normalized_query_texts)):
        raise ValueError("query artifact contains duplicate normalized query text")
    diagnostics = []
    errors: list[str] = []
    for row in rows:
        source = expected[row["packet_id"]].text
        anchors = {token for anchor in simple_anchors(source) for token in anchor_alias_tokens(anchor)}
        for kind in ("semantic_query", "anchor_query"):
            value = normalize_space(str(row.get(kind, "")))
            words = normalized_tokens(value)
            if not 6 <= len(words) <= 32:
                errors.append(f"{row['packet_id']} {kind} must contain 6-32 tokens")
            if re.search(r"\bmse_[a-z0-9]+|\bms-[a-z0-9]+|\b\d{4}-\d{2}-\d{2}\b|\b[DRAFT]:", value, re.I):
                errors.append(f"{row['packet_id']} {kind} leaks metadata or field labels")
            if re.search(r"\b(raw|decision[_ -]?only|lean[_ -]?front|labeled[_ -]?spans|representation arm)\b", value, re.I):
                errors.append(f"{row['packet_id']} {kind} leaks experiment vocabulary")
            overlap3 = shared_ngram(value, source, 3)
            overlap2 = shared_ngram(value, source, 2, content_only=True)
            if overlap3 or overlap2:
                errors.append(f"{row['packet_id']} {kind} copies source phrase: {overlap3 or overlap2}")
            query_anchors = anchors & {token.lower() for token in normalized_tokens(value)}
            if kind == "semantic_query" and query_anchors:
                errors.append(f"{row['packet_id']} semantic query contains exact anchor {sorted(query_anchors)}")
            if kind == "anchor_query" and not query_anchors:
                errors.append(f"{row['packet_id']} anchor query must contain one exact source identifier")
            diagnostics.append({"packet_id": row["packet_id"], "kind": kind,
                                "token_count": len(words), "anchor_hits": sorted(query_anchors)})
    if errors:
        raise ValueError("; ".join(errors))
    return diagnostics


def query_file_sha256(path: Path = QUERY_PATH) -> str:
    return sha256_bytes(path.read_bytes())


def retrieval_metrics(sample: list, reps: dict[str, dict[str, str]], query_payload: dict,
                      selected: list) -> tuple[dict, list[dict]]:
    by_packet = {packet_id(chunk.chunk_id): chunk.chunk_id for chunk in selected}
    rows = []
    for item in query_payload["queries"]:
        for kind in ("semantic_query", "anchor_query"):
            rows.append((item["packet_id"], kind.removesuffix("_query"), item[kind],
                         by_packet[item["packet_id"]]))
    output: dict[str, dict] = {}
    rank_table = [{"packet_id": packet, "kind": kind, "ranks": {}}
                  for packet, kind, _, _ in rows]
    for arm in ARMS:
        corpus = [replace(chunk, title="", entry_title="", heading_path=(), text=reps[chunk.chunk_id][arm],
                          lexical_terms=(), topics=(), inferred_topics=(), inferred_decision_topics=(), tags=())
                  for chunk in sample]
        arm_rows: dict[str, dict] = {}
        for query_kind in ("semantic", "anchor", "all"):
            applicable = rows if query_kind == "all" else [row for row in rows if row[1] == query_kind]
            ranks = []
            for packet, kind, query, target in applicable:
                ranked = BENCHMARK.rank_memory_chunks(
                    query, corpus, top_k=len(corpus), recency_enabled=False, embedding_provider=None
                )
                rank = next((index for index, result in enumerate(ranked, 1)
                             if result.chunk.chunk_id == target), len(corpus) + 1)
                ranks.append(rank)
                if query_kind != "all":
                    next(item for item in rank_table
                         if item["packet_id"] == packet and item["kind"] == kind)["ranks"][arm] = rank
            arm_rows[query_kind] = {
                "query_count": len(ranks),
                "recall_at_1": sum(rank <= 1 for rank in ranks) / len(ranks),
                "recall_at_3": sum(rank <= 3 for rank in ranks) / len(ranks),
                "recall_at_5": sum(rank <= 5 for rank in ranks) / len(ranks),
                "mrr": sum(1 / rank for rank in ranks) / len(ranks),
            }
        output[arm] = arm_rows
    return output, rank_table


def repeated_token_fraction(text: str) -> float:
    tokens = normalized_tokens(text, content_only=True)
    if not tokens:
        return 0.0
    counts = Counter(tokens)
    return sum(count - 1 for count in counts.values() if count > 1) / len(tokens)


def contains_exact_anchor(text: str, anchor: str) -> bool:
    identifier_character = r"A-Za-z0-9_.:/\\-"
    return re.search(
        rf"(?<![{identifier_character}]){re.escape(anchor)}(?![{identifier_character}])",
        text,
        re.I,
    ) is not None


def readability_sentences(text: str) -> list[str]:
    clean = re.sub(r"(?m)^\s*-\s*[DRAFT]:\s*", "", text)
    return [normalize_space(item) for item in READABILITY_SENTENCE.split(clean) if normalize_space(item)]


def structural_metrics(sample: list, reps: dict[str, dict[str, str]]) -> dict:
    output = {}
    raw_tokens = sum(BENCHMARK.token_proxy(reps[c.chunk_id]["raw"]) for c in sample) / len(sample)
    for arm in ARMS:
        texts = [reps[chunk.chunk_id][arm] for chunk in sample]
        token_values = [BENCHMARK.token_proxy(text) for text in texts]
        sentence_values = [len(normalized_tokens(sentence)) for text in texts
                           for sentence in readability_sentences(text)]
        output[arm] = {
            "mean_token_proxy": sum(token_values) / len(token_values),
            "median_token_proxy": sorted(token_values)[len(token_values) // 2],
            "relative_context": (sum(token_values) / len(token_values)) / raw_tokens,
            "mean_words_per_sentence": sum(sentence_values) / len(sentence_values),
            "mean_repeated_content_token_fraction": sum(repeated_token_fraction(text) for text in texts) / len(texts),
        }
    source_anchors = [(chunk, anchor) for chunk in sample
                      for anchor in exact_anchors(parse_fields(chunk.text), limit=None)]
    output["lean_front_door"]["source_exact_anchor_coverage"] = (
        sum(contains_exact_anchor(reps[chunk.chunk_id]["lean_front_door"], anchor)
            for chunk, anchor in source_anchors) / len(source_anchors)
        if source_anchors else 1.0
    )
    return output


def paired_bootstrap(rank_table: list[dict], *, kind: str, treatment: str, control: str,
                     metric: str, samples: int = 10_000) -> dict:
    rows = [row for row in rank_table if row["kind"] == kind]
    def contribution(rank: int) -> float:
        if metric == "mrr":
            return 1 / rank
        if metric == "recall_at_5":
            return float(rank <= 5)
        raise ValueError(metric)
    differences = [contribution(row["ranks"][treatment]) - contribution(row["ranks"][control])
                   for row in rows]
    rng = random.Random(20260810)
    boot = []
    for _ in range(samples):
        boot.append(sum(differences[rng.randrange(len(differences))] for _ in differences) / len(differences))
    boot.sort()
    return {
        "kind": kind,
        "metric": metric,
        "treatment": treatment,
        "control": control,
        "decision_count": len(differences),
        "difference": sum(differences) / len(differences),
        "bootstrap_95_ci": [boot[int(samples * 0.025)], boot[int(samples * 0.975) - 1]],
        "bootstrap_samples": samples,
        "seed": 20260810,
    }


def cohen_kappa(pairs: list[tuple[bool, bool]]) -> float | None:
    if not pairs:
        return None
    agreement = sum(left == right for left, right in pairs) / len(pairs)
    left_yes = sum(left for left, _ in pairs) / len(pairs)
    right_yes = sum(right for _, right in pairs) / len(pairs)
    expected = left_yes * right_yes + (1 - left_yes) * (1 - right_yes)
    return (agreement - expected) / (1 - expected) if expected < 1 else None


def readability_metrics(selected: list, payload: dict, adjudication: dict | None = None) -> dict:
    if payload.get("schema") != "lean-draft-readability-ratings.v1":
        raise ValueError("unexpected readability artifact schema")
    key = {card_id(chunk.chunk_id, arm): (chunk.chunk_id, arm)
           for chunk in selected for arm in ARMS}
    by_card: dict[str, list[dict]] = {identifier: [] for identifier in key}
    reviewer_ids = set()
    for review in payload.get("reviews", []):
        reviewer = str(review.get("reviewer", "")).strip()
        if not reviewer or reviewer in reviewer_ids:
            raise ValueError("readability reviewer ids must be non-empty and unique")
        reviewer_ids.add(reviewer)
        seen = set()
        for rating in review.get("ratings", []):
            identifier = rating.get("card_id")
            if identifier not in key or identifier in seen:
                raise ValueError(f"unknown or duplicate readability card: {identifier}")
            seen.add(identifier)
            if rating.get("clarity") not in range(1, 6) or rating.get("findability") not in range(1, 6):
                raise ValueError(f"invalid readability scale for {identifier}")
            for field in ("decision_complete", "rationale_complete", "boundary_complete", "critical_error"):
                if not isinstance(rating.get(field), bool):
                    raise ValueError(f"{identifier} {field} must be boolean")
            by_card[identifier].append({**rating, "reviewer": reviewer})
    wrong_counts = {identifier: len(rows) for identifier, rows in by_card.items() if len(rows) != 2}
    if wrong_counts:
        raise ValueError(f"every readability card needs exactly two ratings: {wrong_counts}")
    disagreements = {identifier for identifier, rows in by_card.items()
                     if rows[0]["critical_error"] != rows[1]["critical_error"]}
    adjudicated = {}
    if adjudication is not None:
        if adjudication.get("schema") != "lean-draft-readability-adjudication.v1":
            raise ValueError("unexpected readability adjudication schema")
        adjudicated = {row["card_id"]: row for row in adjudication.get("adjudications", [])}
        if set(adjudicated) != disagreements:
            raise ValueError("adjudication must cover every and only critical-rating disagreement")
        if not all(isinstance(row.get("critical_error"), bool) for row in adjudicated.values()):
            raise ValueError("adjudicated critical_error values must be boolean")
    def final_critical(identifier: str, rows: list[dict]) -> bool:
        if identifier in adjudicated:
            return adjudicated[identifier]["critical_error"]
        return rows[0]["critical_error"]
    output = {arm: {} for arm in ARMS}
    for arm in ARMS:
        arm_cards = [(identifier, rows) for identifier, rows in by_card.items() if key[identifier][1] == arm]
        flat = [row for _, rows in arm_cards for row in rows]
        output[arm] = {
            "card_count": len(arm_cards),
            "rating_count": len(flat),
            "mean_clarity": sum(row["clarity"] for row in flat) / len(flat),
            "mean_findability": sum(row["findability"] for row in flat) / len(flat),
            "decision_completeness": sum(row["decision_complete"] for row in flat) / len(flat),
            "rationale_completeness": sum(row["rationale_complete"] for row in flat) / len(flat),
            "boundary_completeness": sum(row["boundary_complete"] for row in flat) / len(flat),
            "critical_rating_rate": sum(row["critical_error"] for row in flat) / len(flat),
            "any_critical_card_rate": sum(any(row["critical_error"] for row in rows)
                                          for _, rows in arm_cards) / len(arm_cards),
            "adjudicated_critical_card_rate": (
                sum(final_critical(identifier, rows) for identifier, rows in arm_cards) / len(arm_cards)
                if adjudication is not None else None
            ),
        }
    critical_pairs = [(rows[0]["critical_error"], rows[1]["critical_error"])
                      for rows in by_card.values()]
    pair_groups: dict[tuple[str, str], list[tuple[bool, bool]]] = {}
    for rows in by_card.values():
        ordered = sorted(rows, key=lambda row: row["reviewer"])
        pair = (ordered[0]["reviewer"], ordered[1]["reviewer"])
        pair_groups.setdefault(pair, []).append(
            (ordered[0]["critical_error"], ordered[1]["critical_error"])
        )
    output["agreement"] = {
        "reviewer_process_count": len(reviewer_ids),
        "ratings_per_card": 2,
        "critical_raw_agreement": sum(left == right for left, right in critical_pairs) / len(critical_pairs),
        "critical_pair_agreement": [
            {
                "reviewers": list(pair),
                "card_count": len(pairs),
                "raw_agreement": sum(left == right for left, right in pairs) / len(pairs),
                "cohen_kappa": cohen_kappa(pairs),
            }
            for pair, pairs in sorted(pair_groups.items())
        ],
        "critical_disagreement_count": len(disagreements),
        "critical_disagreements_adjudicated": len(adjudicated),
    }
    return output


def disagreement_packets() -> list[dict]:
    decisions, _ = BENCHMARK.frozen_corpus()
    selected = choose_pilot(BENCHMARK.choose_sample(decisions))
    key = {card_id(chunk.chunk_id, arm): (chunk, arm) for chunk in selected for arm in ARMS}
    by_card = {identifier: [] for identifier in key}
    for path in sorted(REVIEW_DIR.glob("*.json")):
        review = json.loads(path.read_text(encoding="utf-8"))
        for row in review["ratings"]:
            by_card[row["card_id"]].append({"reviewer": review["reviewer"],
                                               "critical_error": row["critical_error"],
                                               "critical_reasons": row["critical_reasons"]})
    packets = []
    for identifier, ratings in by_card.items():
        if len(ratings) == 2 and ratings[0]["critical_error"] != ratings[1]["critical_error"]:
            chunk, arm = key[identifier]
            packets.append({"card_id": identifier, "source": chunk.text,
                            "candidate": representations(chunk.text)[arm], "ratings": ratings})
    return sorted(packets, key=lambda row: row["card_id"])


def render_results(metrics: dict) -> str:
    lines = [
        "# Lean DRAFT feasibility pilot",
        "",
        "This is a derived decision-block pilot, not a natural-authoring study and not a change to the DRAFT grammar.",
        "",
        "| Arm | Mean token proxy | Relative context | Semantic R@5 | Semantic MRR | Anchor R@5 | Anchor MRR |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        size = metrics["structure"][arm]
        retrieval = metrics["retrieval"][arm]
        lines.append(
            f"| {arm} | {size['mean_token_proxy']:.1f} | {size['relative_context']:.3f} | "
            f"{retrieval['semantic']['recall_at_5']:.3f} | {retrieval['semantic']['mrr']:.3f} | "
            f"{retrieval['anchor']['recall_at_5']:.3f} | {retrieval['anchor']['mrr']:.3f} |"
        )
    if "readability" in metrics:
        lines.extend([
            "",
            "| Arm | Model-rated clarity /5 | Model-rated findability /5 | Decision complete | Rationale complete | Boundary complete | Adjudicated critical error |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ])
        for arm in ARMS:
            row = metrics["readability"][arm]
            critical = row["adjudicated_critical_card_rate"]
            if critical is None:
                critical = row["any_critical_card_rate"]
            lines.append(
                f"| {arm} | {row['mean_clarity']:.2f} | {row['mean_findability']:.2f} | "
                f"{row['decision_completeness']:.1%} | {row['rationale_completeness']:.1%} | "
                f"{row['boundary_completeness']:.1%} | {critical:.1%} |"
            )
    raw = metrics["retrieval"]["raw"]
    naive = metrics["retrieval"]["decision_only"]
    lean = metrics["retrieval"]["lean_front_door"]
    no_anchor = metrics["retrieval"]["lean_no_supplemental_anchors"]
    semantic_effect = metrics["paired_effects"]["lean_vs_raw_semantic_mrr"]
    anchor_effect = metrics["paired_effects"]["supplemental_anchors_identifier_mrr"]
    readability = metrics.get("readability", {})
    lines.extend([
        "",
        "## Interpretation",
        "",
        f"- The lean card uses {metrics['structure']['lean_front_door']['relative_context']:.1%} of raw decision-block context; decision-only uses {metrics['structure']['decision_only']['relative_context']:.1%}.",
        f"- On independently worded semantic queries, lean MRR is {lean['semantic']['mrr']:.3f} versus raw {raw['semantic']['mrr']:.3f} and decision-only {naive['semantic']['mrr']:.3f}.",
        f"- Lean minus raw semantic MRR is {semantic_effect['difference']:+.3f} (decision-bootstrap 95% CI {semantic_effect['bootstrap_95_ci'][0]:+.3f} to {semantic_effect['bootstrap_95_ci'][1]:+.3f}), failing the provisional -0.05 margin.",
        f"- On identifier queries, supplemental exact anchors change MRR from {no_anchor['anchor']['mrr']:.3f} to {lean['anchor']['mrr']:.3f}; the paired effect is {anchor_effect['difference']:+.3f} (95% CI {anchor_effect['bootstrap_95_ci'][0]:+.3f} to {anchor_effect['bootstrap_95_ci'][1]:+.3f}), so this pilot does not establish a non-zero benefit.",
        f"- The strict anchor gate also missed: semantic MRR changed from {no_anchor['semantic']['mrr']:.3f} without supplemental anchors to {lean['semantic']['mrr']:.3f} with them, rather than remaining non-decreasing.",
        "- Every compact clause and identifier is extractive. That establishes source grounding, not full semantic completeness.",
    ])
    if readability:
        lines.extend([
            f"- An arm-label-hidden, same-model structured audit (two ratings per card across four reviewer processes) plus adjudication flagged a critical loss on {readability['lean_front_door']['adjudicated_critical_card_rate']:.1%} of lean cards versus {readability['raw']['adjudicated_critical_card_rate']:.1%} raw; pooled raw agreement was {readability['agreement']['critical_raw_agreement']:.1%}. Candidate form and exact source matching made the raw arm recognizable, so this is not confirmatory reader evidence.",
            f"- Model-rated lean clarity was slightly higher ({readability['lean_front_door']['mean_clarity']:.2f} vs {readability['raw']['mean_clarity']:.2f}), but its findability was lower ({readability['lean_front_door']['mean_findability']:.2f} vs {readability['raw']['mean_findability']:.2f}); these ratings cannot offset the fidelity failure.",
        ])
    lines.extend([
        "- Outcome: the theory is not validated for shortening canonical drafts, and the measured selector should not ship. Progressive disclosure with a safer selector and immediate full-source access is the next hypothesis worth testing; exact identifiers are a candidate field, not a validated feature.",
        "- A confirmatory authoring study still needs independently authored paired records, human readers, and delayed recall before changing guidance.",
        "",
    ])
    return "\n".join(lines)


def run(output_dir: Path = HERE) -> dict:
    if not QUERY_PATH.is_file():
        raise RuntimeError("query artifact is missing; author and validate it before scoring")
    query_hash = query_file_sha256()
    if query_hash != EXPECTED_QUERY_SHA256:
        raise RuntimeError(f"query artifact is not frozen: expected {EXPECTED_QUERY_SHA256}, got {query_hash}")
    selector_hash = selector_sha256()
    if selector_hash != EXPECTED_SELECTOR_SHA256:
        raise RuntimeError(
            f"selector is not frozen: expected {EXPECTED_SELECTOR_SHA256}, got {selector_hash}"
        )
    review_paths = sorted(REVIEW_DIR.glob("*.json")) if REVIEW_DIR.is_dir() else []
    actual_review_hashes = {path.name: sha256_bytes(path.read_bytes()) for path in review_paths}
    if actual_review_hashes != EXPECTED_REVIEW_SHA256:
        raise RuntimeError(f"readability artifacts are missing or not frozen: {actual_review_hashes}")
    if not ADJUDICATION_PATH.is_file():
        raise RuntimeError("readability adjudication artifact is missing")
    actual_adjudication_hash = sha256_bytes(ADJUDICATION_PATH.read_bytes())
    if actual_adjudication_hash != EXPECTED_ADJUDICATION_SHA256:
        raise RuntimeError("readability adjudication artifact is not frozen")
    decisions, identity = BENCHMARK.frozen_corpus()
    if identity.get("source_revision") != EXPECTED_SOURCE_REVISION:
        raise RuntimeError(f"unexpected frozen source revision: {identity.get('source_revision')}")
    if identity.get("corpus_fingerprint") != EXPECTED_CORPUS_FINGERPRINT:
        raise RuntimeError(f"unexpected frozen corpus fingerprint: {identity.get('corpus_fingerprint')}")
    sample = BENCHMARK.choose_sample(decisions)
    selected = choose_pilot(sample)
    selection_fingerprint = "sha256:" + BENCHMARK.stable(json.dumps([c.chunk_id for c in selected]))
    if selection_fingerprint != EXPECTED_SELECTION_FINGERPRINT:
        raise RuntimeError(
            f"pilot target selection is not frozen: expected {EXPECTED_SELECTION_FINGERPRINT}, "
            f"got {selection_fingerprint}"
        )
    query_payload = json.loads(QUERY_PATH.read_text(encoding="utf-8"))
    diagnostics = validate_queries(query_payload, selected)
    reps = {chunk.chunk_id: representations(chunk.text) for chunk in sample}
    retrieval, rank_table = retrieval_metrics(sample, reps, query_payload, selected)
    metrics = {
        "schema": "lean-draft-feasibility-pilot.v1",
        "status": "measured-feasibility-pilot",
        "corpus": identity,
        "sample_count": len(sample),
        "query_target_count": len(selected),
        "query_count": len(diagnostics),
        "query_sha256": query_hash,
        "selector_sha256": selector_hash,
        "freeze_record": {
            "query_artifact": "hash-pinned before first ranking run",
            "corpus": "source revision and corpus fingerprint checked before scoring",
            "selector": "post-first-run reproducibility lock; not a pre-outcome preregistration",
        },
        "selection_fingerprint": selection_fingerprint,
        "limitations": [
            "derived extractive decision blocks, not naturally authored drafts",
            "query subset requires rationale plus a compact exact identifier",
            "arm labels were hidden, but canonical source plus all four candidate forms made raw recognizable",
            "all fidelity ratings came from the same model family; they are a structured audit, not independent human-reader evidence",
            "the selector was not independently hash-pinned before the first scored run",
            "no human comprehension or delayed-recall result exists",
            "entry Summary/YAML/title overhead is outside the measured representation body",
        ],
        "structure": structural_metrics(sample, reps),
        "retrieval": retrieval,
        "paired_effects": {
            "lean_vs_raw_semantic_mrr": paired_bootstrap(
                rank_table, kind="semantic", treatment="lean_front_door", control="raw", metric="mrr"
            ),
            "lean_vs_raw_semantic_recall_at_5": paired_bootstrap(
                rank_table, kind="semantic", treatment="lean_front_door", control="raw", metric="recall_at_5"
            ),
            "supplemental_anchors_identifier_mrr": paired_bootstrap(
                rank_table, kind="anchor", treatment="lean_front_door",
                control="lean_no_supplemental_anchors", metric="mrr"
            ),
            "supplemental_anchors_identifier_recall_at_5": paired_bootstrap(
                rank_table, kind="anchor", treatment="lean_front_door",
                control="lean_no_supplemental_anchors", metric="recall_at_5"
            ),
        },
        "query_validation": {
            "query_count": len(diagnostics),
            "semantic_query_count": sum(row["kind"] == "semantic_query" for row in diagnostics),
            "anchor_query_count": sum(row["kind"] == "anchor_query" for row in diagnostics),
            "phrase_or_metadata_leaks": 0,
            "semantic_queries_with_exact_anchor": 0,
            "identifier_queries_without_source_anchor": 0,
        },
    }
    review_payload = {
        "schema": "lean-draft-readability-ratings.v1",
        "reviews": [json.loads(path.read_text(encoding="utf-8")) for path in review_paths],
    }
    adjudication = json.loads(ADJUDICATION_PATH.read_text(encoding="utf-8"))
    metrics["readability"] = readability_metrics(selected, review_payload, adjudication)
    metrics["readability_artifacts"] = actual_review_hashes
    metrics["readability_adjudication_sha256"] = actual_adjudication_hash
    rendered_metrics = json.dumps(metrics, indent=2, sort_keys=True) + "\n"
    rendered_results = render_results(metrics)
    (output_dir / "lean-draft-metrics.json").write_text(
        rendered_metrics, encoding="utf-8", newline="\n"
    )
    (output_dir / "lean-draft-results.md").write_text(
        rendered_results, encoding="utf-8", newline="\n"
    )
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    packets = sub.add_parser("packets", help="print source-only authoring packets")
    packets.add_argument("--batch", type=int, choices=(0, 1, 2))
    review = sub.add_parser("review-packets", help="print arm-label-hidden structured-audit cards")
    review.add_argument("--batch", type=int, choices=(0, 1))
    sub.add_parser("review-disagreements", help="print arm-label-hidden critical-rating disagreements")
    sub.add_parser("validate-queries", help="validate the query artifact without ranking")
    run_parser = sub.add_parser("run", help="run the frozen pilot")
    run_parser.add_argument("--output-dir", type=Path, default=HERE)
    args = parser.parse_args()
    if args.command == "packets":
        print(json.dumps({"schema": "lean-draft-query-packets.v1", "packets": query_packets(args.batch)}, indent=2))
    elif args.command == "review-packets":
        print(json.dumps({"schema": "lean-draft-review-packets.v1", "packets": review_packets(args.batch)}, indent=2))
    elif args.command == "review-disagreements":
        print(json.dumps({"schema": "lean-draft-disagreement-packets.v1",
                          "packets": disagreement_packets()}, indent=2))
    elif args.command == "validate-queries":
        decisions, _ = BENCHMARK.frozen_corpus()
        selected = choose_pilot(BENCHMARK.choose_sample(decisions))
        payload = json.loads(QUERY_PATH.read_text(encoding="utf-8"))
        print(json.dumps({"sha256": query_file_sha256(), "diagnostics": validate_queries(payload, selected)}, indent=2))
    else:
        print(json.dumps(run(args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
