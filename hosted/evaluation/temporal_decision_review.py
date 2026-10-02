"""Offline, reviewer-labelled comparison of decision-time evidence and later logs.

This is a diagnostic companion to ``adaptive_comparison``. It never infers
temporal provenance from a log entry, promotes a candidate, or grants a gate.
Raw dialogue and private model output remain with the reviewers; the return
value contains only aggregate counts and unresolved field identities.
"""
from __future__ import annotations

from collections import Counter
from typing import Any


FIELDS = frozenset({
    "issue", "selected_action", "deciding_actor", "acceptance", "scope",
    "conditions", "proposal_reference", "topic_origin", "reason",
    "implementation",
})
PHASES = frozenset({"at_turn", "later_only", "outside_dialogue_at_turn", "unknown"})
RELATIONS = frozenset({"matched", "missing", "mismatch", "unsupported", "unknown"})
COUNT_KEYS = (
    "scorable_at_turn", "recovered_at_turn", "extraction_error",
    "unresolved_at_turn", "later_enrichment", "possible_hindsight_or_unsupported",
    "unresolved_later", "context_gap", "unresolved_phase",
    "unresolved_review",
)


def _references(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(ref, str) or not ref.strip() for ref in value):
        raise ValueError(f"{name} must be a list of nonempty reference IDs")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} contains duplicate references")
    return value


def _validate(review: Any) -> tuple[str, str, str]:
    if not isinstance(review, dict):
        raise ValueError("review must be an object")
    for name in ("reviewer_id", "case_id"):
        if not isinstance(review.get(name), str) or not review[name].strip():
            raise ValueError(f"{name} must be a nonempty string")
    if review.get("field") not in FIELDS:
        raise ValueError("unknown decision field")
    if review.get("evidence_phase") not in PHASES:
        raise ValueError("unknown evidence phase")
    if review.get("candidate_relation") not in RELATIONS:
        raise ValueError("unknown candidate relation")
    source_refs = _references(review.get("source_refs"), "source_refs")
    post_turn_refs = _references(review.get("post_turn_refs"), "post_turn_refs")
    external_refs = _references(review.get("external_refs"), "external_refs")
    log_refs = _references(review.get("log_refs"), "log_refs")
    if not log_refs:
        raise ValueError("review requires a later-log reference")
    if review["evidence_phase"] == "at_turn" and not source_refs:
        raise ValueError("at-turn evidence requires a dialogue reference")
    phase = review["evidence_phase"]
    if phase == "later_only" and (source_refs or external_refs or not post_turn_refs):
        raise ValueError("later-only fact requires post-turn evidence and no prior evidence")
    if phase == "outside_dialogue_at_turn" and (source_refs or post_turn_refs or not external_refs):
        raise ValueError("outside-dialogue fact requires contemporaneous external evidence")
    if phase in {"at_turn", "unknown"} and (post_turn_refs or external_refs):
        raise ValueError("phase has incompatible evidence references")
    return review["case_id"], review["field"], review["reviewer_id"]


def compare_temporal_reviews(reviews: list[dict]) -> dict:
    """Compare two independent field reviews without treating later facts as misses.

    ``source_refs`` and ``log_refs`` are opaque private-evidence IDs, not
    source text. Reviewers must establish their provenance independently.
    Discordant reviews are unresolved, never silently adjudicated.
    """
    if not isinstance(reviews, list) or not reviews:
        raise ValueError("reviews must be a nonempty list")
    keyed: dict[tuple[str, str], dict[str, dict]] = {}
    for review in reviews:
        case_id, field, reviewer = _validate(review)
        pair = keyed.setdefault((case_id, field), {})
        if reviewer in pair:
            raise ValueError("duplicate reviewer for field")
        pair[reviewer] = review
    counts: Counter[str] = Counter()
    unresolved: list[dict[str, str]] = []
    for (case_id, field), pair in sorted(keyed.items()):
        if len(pair) != 2:
            raise ValueError("exactly two independent reviewers required per field")
        a, b = pair.values()
        if (a["evidence_phase"], a["candidate_relation"]) != (b["evidence_phase"], b["candidate_relation"]):
            counts["unresolved_review"] += 1
            unresolved.append({"case_id": case_id, "field": field})
            continue
        phase, relation = a["evidence_phase"], a["candidate_relation"]
        if phase == "at_turn":
            counts["scorable_at_turn"] += 1
            if relation == "matched":
                counts["recovered_at_turn"] += 1
            elif relation in {"missing", "mismatch"}:
                counts["extraction_error"] += 1
            else:
                counts["unresolved_at_turn"] += 1
        elif phase == "later_only":
            if relation == "missing":
                counts["later_enrichment"] += 1
            elif relation in {"matched", "mismatch", "unsupported"}:
                counts["possible_hindsight_or_unsupported"] += 1
            else:
                counts["unresolved_later"] += 1
        elif phase == "outside_dialogue_at_turn":
            counts["context_gap"] += 1
        else:
            counts["unresolved_phase"] += 1
    return {"field_count": len(keyed), "counts": {key: counts[key] for key in COUNT_KEYS},
            "unresolved": unresolved, "gate": "diagnostic_only"}
