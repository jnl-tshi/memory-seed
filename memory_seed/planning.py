"""Pure, shared planning policy and candidate assessment.

Callers supply project YAML text/mappings and evidence from the existing readers.
This service performs no retrieval, writes, lifecycle transitions, integration,
or authorization. Topic relevance selects candidates, never proves a conflict or
exhaustive coverage. Authority precedence is independent of retrieval order.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .retrieval_profiles import RetrievalProfileValidationError, _read_profile_yaml
from .topics import TopicIndex, _validate_topic_index


AUTHORITY_PRECEDENCE = (
    "constitution", "control_file", "accepted_adr", "session_evidence", "derived_projection",
)
_DEFAULT_POLICY = {
    "schema_version": 1,
    "constitutional_conflict": "stop",
    "adr_conflict": "stop",
    "individual_decision_conflict": "warn",
    "failed_hypothesis_threshold": 3,
}
_SEVERITY = {"proceed": 0, "warn": 1, "stop": 2}


class PlanningValidationError(ValueError):
    """Recognized planning input is invalid; do not silently use defaults."""


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanningValidationError(f"{field} must be nonempty text")
    return value


def _policy_block(value: Any, *, partial: bool = False) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise PlanningValidationError("delivery_quality must be a mapping")
    unknown = set(value) - _DEFAULT_POLICY.keys()
    if unknown:
        raise PlanningValidationError(f"delivery_quality has unknown settings: {sorted(map(str, unknown))}")
    if not partial and "schema_version" not in value:
        raise PlanningValidationError("delivery_quality.schema_version is required")
    for key, setting in value.items():
        if key == "schema_version":
            valid = type(setting) is int and setting == 1
        elif key == "failed_hypothesis_threshold":
            valid = type(setting) is int and setting > 0
        elif key == "constitutional_conflict":
            valid = setting == "stop"
        else:
            valid = isinstance(setting, str) and setting in _SEVERITY
        if not valid:
            raise PlanningValidationError(f"delivery_quality.{key} has invalid value {setting!r}")
    return dict(value)


def resolve_delivery_quality(
    project_config: Mapping[str, Any] | None = None,
    *, local_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve tracked defaults, then a tightening-only local/task override.

    An absent mapping uses v1 defaults; a present mapping must declare version 1.
    Unknown keys *inside* delivery_quality fail to expose spelling mistakes.
    Unrelated project settings belong to their existing readers. Lower failed
    hypothesis thresholds tighten policy; higher thresholds weaken it. Acceptance
    and recommendations are evidence fields, never configuration overrides.
    """
    if project_config is not None and not isinstance(project_config, Mapping):
        raise PlanningValidationError("project_config must be a mapping")
    effective = dict(_DEFAULT_POLICY)
    if project_config is not None and "delivery_quality" in project_config:
        effective.update(_policy_block(project_config["delivery_quality"]))
    if local_override is not None:
        for key, value in _policy_block(local_override, partial=True).items():
            weakens = (
                value > effective[key] if key == "failed_hypothesis_threshold"
                else key != "schema_version" and _SEVERITY[value] < _SEVERITY[effective[key]]
            )
            if weakens:
                raise PlanningValidationError(f"local override cannot weaken delivery_quality.{key}")
            effective[key] = value
    return effective


def parse_delivery_quality(
    project_yaml: str, *, local_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Read only the delivery_quality block of supplied project YAML text.

    Reuse the existing strict, dependency-free YAML subset reader (two-space
    indentation, scalar/flow values). Unsupported syntax in this recognized block
    fails explicitly; other top-level settings are left to their current readers.
    Filesystem/runtime discovery stays with the calling surface.
    """
    if not isinstance(project_yaml, str):
        raise PlanningValidationError("project_yaml must be text")
    lines = project_yaml.splitlines()
    starts = [i for i, line in enumerate(lines)
              if re.match(r"^(?:delivery_quality|'delivery_quality'|\"delivery_quality\")\s*:", line)]
    if len(starts) > 1:
        raise PlanningValidationError("duplicate delivery_quality mapping")
    if not starts:
        return resolve_delivery_quality(local_override=local_override)
    start = starts[0]
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if line.strip() and not line.startswith((" ", "\t", "#")):
            break
        end += 1
    try:
        config = _read_profile_yaml("\n".join(lines[start:end]), path="delivery_quality")
    except RetrievalProfileValidationError as exc:
        raise PlanningValidationError(f"invalid delivery_quality YAML: {exc}") from exc
    return resolve_delivery_quality(config, local_override=local_override)


@dataclass(frozen=True)
class PlanningCandidate:
    """A source-backed candidate supplied by a reader, not a new decision store.

    `active` means the caller checked current source/lifecycle: a declared ratified
    Constitution, the concern-owning control file, an accepted ADR head, or an
    unsuperseded individual decision. Proposed ADRs/draft Constitutions must use
    `proposed`; superseded records remain explanatory. `topics` must retain their
    source provenance; semantic suggestions do not become recorded tags.
    """

    reference: str
    decision: str
    authority: str
    topics: tuple[str, ...] = ()
    status: str = "active"
    topic_source: str = "write-time"
    discovery: str = "source"
    scope: str = "topics"
    scope_reason: str = ""


@dataclass(frozen=True)
class CandidateAssessment:
    candidate: PlanningCandidate
    task_topics: tuple[str, ...]
    matched_topics: tuple[str, ...]
    applicability: str
    binding: bool
    reason: str
    coverage: str = "candidate-only; not exhaustive"


def _canonical_topics(values: Sequence[str], index: TopicIndex) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise PlanningValidationError("topics must be a sequence of controlled slugs")
    resolution = index.resolution()
    canonical = []
    for value in values:
        if not isinstance(value, str) or value not in resolution:
            raise PlanningValidationError(f"unknown controlled topic: {value!r}")
        if resolution[value] not in canonical:
            canonical.append(resolution[value])
    return tuple(canonical)


def assess_candidate(
    candidate: PlanningCandidate, task_topics: Sequence[str], topic_index: TopicIndex,
) -> CandidateAssessment:
    """Assess supplied evidence without ranking, tagging, or changing lifecycle.

    A decision's topic must equal a task topic or be its ancestor. Search filters
    expand downward for retrieval; planning deliberately does not use them. Area
    and activity are topic types in this same tree, not independent scope axes.
    Global scope is explicit and limited to governing Constitution/control files.
    """
    _text(candidate.reference, "candidate.reference")
    _text(candidate.decision, "candidate.decision")
    if candidate.authority not in AUTHORITY_PRECEDENCE:
        raise PlanningValidationError("candidate.authority is unknown")
    if candidate.status not in ("active", "proposed", "superseded", "rejected", "withdrawn"):
        raise PlanningValidationError("candidate.status is unknown")
    if candidate.topic_source not in ("write-time", "derived"):
        raise PlanningValidationError("candidate.topic_source is unknown")
    if candidate.discovery not in ("source", "semantic"):
        raise PlanningValidationError("candidate.discovery is unknown")
    if candidate.scope not in ("topics", "global"):
        raise PlanningValidationError("candidate.scope is unknown")
    issues = [issue for issue in _validate_topic_index(topic_index) if issue.severity == "error"]
    if issues:
        raise PlanningValidationError("invalid topic vocabulary: " + "; ".join(issue.detail for issue in issues))
    task = _canonical_topics(task_topics, topic_index)
    recorded = _canonical_topics(candidate.topics, topic_index)
    applicable_topics = set(task)
    for topic in task:
        applicable_topics.update(topic_index.ancestors(topic))
    matched = tuple(topic for topic in recorded if topic in applicable_topics)
    global_scope = candidate.scope == "global"
    if global_scope:
        if candidate.authority not in ("constitution", "control_file"):
            raise PlanningValidationError("individual/ADR decisions require classified topic scope")
        _text(candidate.scope_reason, "candidate.scope_reason")
    if not recorded and not global_scope:
        applicability, reason = "unclassified", "No recorded controlled topics; coverage requires judgment."
    elif candidate.status in ("superseded", "rejected", "withdrawn"):
        applicability, reason = "historical", "Retained as explanatory evidence, not binding authority."
    elif not matched and not global_scope:
        applicability, reason = "out-of-scope", "No task topic or ancestor matches; descendants bind only within their branch."
    elif (candidate.status != "active" or candidate.authority == "derived_projection"
          or candidate.discovery == "semantic" or candidate.topic_source == "derived"):
        applicability, reason = "review-required", "Nomination/projection/proposal needs source and applicability judgment."
    else:
        applicability, reason = "applicable", "Explicit global scope or a recorded task topic/ancestor matches."
    return CandidateAssessment(candidate, task, matched, applicability,
                               applicability == "applicable", reason)


def assess_conflict(
    assessment: CandidateAssessment, *, proposed_action: str, conflict_reason: str,
    policy: Mapping[str, Any] | None = None, agent_recommendation: str | None = None,
    user_acceptance: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Disposition an explicitly described conflict; never infer contradiction.

    The disposition is a policy response, not permission. Supplied acceptance is
    copied with its reference, scope and reason; its authenticity/authority must
    be checked against the source by the governing workflow. Even an acceptance
    record cannot bypass a constitutional stop or change shared policy. Consumers
    must satisfy required_follow_up before proceeding; this service grants none.
    """
    _text(proposed_action, "proposed_action")
    _text(conflict_reason, "conflict_reason")
    if not assessment.binding or assessment.applicability != "applicable":
        raise PlanningValidationError("a conflict requires an applicable source-backed decision")
    effective = resolve_delivery_quality(None if policy is None else {"delivery_quality": policy})
    if agent_recommendation is not None and (
        not isinstance(agent_recommendation, str) or agent_recommendation not in _SEVERITY
    ):
        raise PlanningValidationError("agent_recommendation must be stop, warn or proceed")
    acceptance = None
    if user_acceptance is not None:
        if not isinstance(user_acceptance, Mapping) or set(user_acceptance) != {"reference", "scope", "reason"}:
            raise PlanningValidationError("user_acceptance requires reference, scope and reason")
        acceptance = {key: _text(value, f"user_acceptance.{key}") for key, value in user_acceptance.items()}
    authority = assessment.candidate.authority
    if authority == "constitution":
        disposition, follow_up = "stop", ["formal_constitutional_amendment"]
    elif authority == "control_file":
        disposition, follow_up = "stop", ["resolve_with_concern_owning_control_file"]
    elif authority == "accepted_adr":
        disposition = effective["adr_conflict"]
        follow_up = ["verify_governing_authority_allows_departure", "record_adr_review"]
    elif authority == "session_evidence":
        disposition = effective["individual_decision_conflict"]
        follow_up = ["record_departure_and_lifecycle_review"]
    else:
        raise PlanningValidationError("derived evidence cannot be binding")
    if disposition == "stop" and authority != "constitution":
        follow_up.append("resolve_stop_with_governing_authority")
    return {
        "decision_reference": assessment.candidate.reference,
        "prior_decision": assessment.candidate.decision,
        "proposed_action": proposed_action,
        "conflict_reason": conflict_reason,
        "authority": authority,
        "disposition": disposition,
        "effective_policy": effective,
        "agent_recommendation": agent_recommendation,
        "user_acceptance": acceptance,
        "authority_granted": False,
        "lifecycle_changed": False,
        "required_follow_up": follow_up,
    }
