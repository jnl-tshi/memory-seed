"""Pure, shared planning policy and candidate assessment.

Callers supply project YAML text/mappings and evidence from the existing readers.
This service performs no retrieval, writes, lifecycle transitions, integration,
or authorization. Topic relevance selects candidates, never proves a conflict or
exhaustive coverage. Authority precedence is independent of retrieval order.
"""

from __future__ import annotations

import re
from copy import deepcopy
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


def validate_implementation_plan(
    value: Mapping[str, Any] | None, *,
    evidence_references: Sequence[str], assessed_paths: Sequence[str],
) -> dict[str, Any] | None:
    """Validate optional task/strategy evidence, without planning or executing work.

    Paths are the exact, validated assessed paths supplied by the packet compiler.
    References carry supplied approval/exception evidence, never authenticate it.
    Semantic suitability of checks and compatibility with governing authority remain
    review obligations; this validator cannot infer either from prose.
    """
    if value is None:
        return None

    def fields(item: Any, required: set[str], name: str) -> Mapping[str, Any]:
        if not isinstance(item, Mapping):
            raise PlanningValidationError(f"{name} must be a mapping")
        missing, unknown = required - item.keys(), item.keys() - required
        if missing or unknown:
            raise PlanningValidationError(
                f"{name} missing fields {sorted(missing)}; unknown fields {sorted(map(str, unknown))}"
            )
        return item

    def strings(items: Any, name: str, *, empty: bool = False) -> list[str]:
        if not isinstance(items, list) or (not items and not empty):
            raise PlanningValidationError(f"{name} must be a {'possibly empty' if empty else 'nonempty'} list")
        for item in items:
            _text(item, name)
        if len(set(items)) != len(items):
            raise PlanningValidationError(f"{name} must not contain duplicates")
        return items

    sources, paths = set(evidence_references), set(assessed_paths)

    def reference(item: Any, name: str) -> None:
        if _text(item, name) not in sources:
            raise PlanningValidationError(f"{name} must name selected evidence")

    plan = fields(value, {"approval_reference", "tasks", "test_strategy"}, "implementation_plan")
    reference(plan["approval_reference"], "approval_reference")
    tasks = plan["tasks"]
    if not isinstance(tasks, list) or not tasks:
        raise PlanningValidationError("tasks must be a nonempty ordered list")
    prior: dict[str, set[str]] = {}
    ownership: dict[str, list[tuple[str, int, int]]] = {}
    for task in tasks:
        task = fields(task, {"id", "acceptance_observables", "edit_ownership", "dependencies",
                             "evidence_references", "verification", "replan_conditions"}, "task")
        identity = _text(task["id"], "task.id")
        if identity in prior:
            raise PlanningValidationError("task.id must be unique")
        dependencies = strings(task["dependencies"], "dependencies", empty=True)
        if not set(dependencies).issubset(prior):
            raise PlanningValidationError("dependencies must name earlier tasks; unknown/forward/cyclic dependencies require replan")
        ancestors = set(dependencies)
        for dependency in dependencies:
            ancestors.update(prior[dependency])
        for field in ("acceptance_observables", "verification", "replan_conditions"):
            strings(task[field], field)
        for source in strings(task["evidence_references"], "evidence_references"):
            reference(source, "evidence_references")
        edits = task["edit_ownership"]
        if not isinstance(edits, list) or not edits:
            raise PlanningValidationError("edit_ownership must be a nonempty list")
        for edit in edits:
            edit = fields(edit, {"path", "line_range"}, "edit_ownership")
            path = _text(edit["path"], "edit_ownership.path")
            if path not in paths:
                raise PlanningValidationError("edit_ownership.path expands assessed scope; replan required")
            span = edit["line_range"]
            if (not isinstance(span, list) or len(span) != 2
                    or any(type(number) is not int for number in span)
                    or not 1 <= span[0] <= span[1]):
                raise PlanningValidationError("edit_ownership.line_range requires inclusive positive start/end")
            for owner, start, end in ownership.get(path.casefold(), []):
                if span[0] <= end and start <= span[1] and owner not in ancestors:
                    raise PlanningValidationError("overlapping edit_ownership requires an explicit dependency")
            ownership.setdefault(path.casefold(), []).append((identity, *span))
        prior[identity] = ancestors
    strategy = fields(plan["test_strategy"], {
        "tests", "alternative_checks", "exceptions", "tests_before_behavior_change", "behavior_changes",
    }, "test_strategy")
    if strategy["tests_before_behavior_change"] is not True:
        raise PlanningValidationError("test_strategy cannot weaken tests-before-behavior project policy")
    tests = strings(strategy["tests"], "test_strategy.tests", empty=True)
    alternatives = strings(strategy["alternative_checks"], "test_strategy.alternative_checks", empty=True)
    if type(strategy["behavior_changes"]) is not bool:
        raise PlanningValidationError("test_strategy.behavior_changes must be a boolean")
    if strategy["behavior_changes"] and not tests:
        raise PlanningValidationError("tests-before-behavior policy requires tests for behavior changes, including with exceptions")
    if not tests and not alternatives:
        raise PlanningValidationError("test_strategy requires viable tests or alternative checks; an exception is not a pass")
    exceptions = strategy["exceptions"]
    if not isinstance(exceptions, list):
        raise PlanningValidationError("test_strategy.exceptions must be a list")
    for exception in exceptions:
        exception = fields(exception, {"reason", "affected_scope", "compensating_checks",
                                       "risk", "authority_reference"}, "exception")
        for field in ("reason", "risk"):
            _text(exception[field], f"exception.{field}")
        affected = strings(exception["affected_scope"], "exception.affected_scope")
        if not {path.casefold() for path in affected}.issubset(ownership):
            raise PlanningValidationError("exception.affected_scope must name planned edit paths")
        strings(exception["compensating_checks"], "exception.compensating_checks")
        reference(exception["authority_reference"], "exception.authority_reference")
    return deepcopy(dict(plan))


_REVIEW_SHA = re.compile(r"^[0-9a-f]{40}$")
_REVIEW_FINDING_SEVERITIES = {"minor", "important", "critical"}
_REVIEW_FINDING_KINDS = {"bug", "style", "spec", "authority"}
_REVIEW_DISPOSITIONS = {"accept", "reject", "defer"}


def validate_review_record(
    value: Mapping[str, Any], *, current_range: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a review receipt without acting on review feedback or execution.

    The caller supplies the current immutable range; this pure validator establishes
    only whether the record is complete, fresh, and internally bound. It never
    decides a finding, authenticates evidence, runs a check, or grants authority.
    """
    def fields(item: Any, required: set[str], name: str) -> Mapping[str, Any]:
        if not isinstance(item, Mapping):
            raise PlanningValidationError(f"{name} must be a mapping")
        missing, unknown = required - item.keys(), item.keys() - required
        if missing or unknown:
            raise PlanningValidationError(
                f"{name} missing fields {sorted(missing)}; unknown fields {sorted(map(str, unknown))}"
            )
        return item

    def text_list(items: Any, name: str, *, empty: bool = False) -> list[str]:
        if not isinstance(items, list) or (not items and not empty):
            raise PlanningValidationError(f"{name} must be a {'possibly empty' if empty else 'nonempty'} list")
        values = [_text(item, name) for item in items]
        if len(values) != len(set(values)):
            raise PlanningValidationError(f"{name} must not contain duplicates")
        return values

    def review_range(item: Any, name: str) -> dict[str, str]:
        item = fields(item, {"base", "head"}, name)
        base, head = _text(item["base"], f"{name}.base"), _text(item["head"], f"{name}.head")
        if not _REVIEW_SHA.fullmatch(base) or not _REVIEW_SHA.fullmatch(head) or base == head:
            raise PlanningValidationError(f"{name} requires distinct full immutable base/head SHAs")
        return {"base": base, "head": head}

    def optional_range(item: Any, name: str) -> dict[str, str] | None:
        if item is None:
            return None
        return review_range(item, name)

    def validation(item: Any, name: str, expected_range: dict[str, str]) -> None:
        item = fields(item, {
            "command_or_check", "changed_scope", "freshness_marker", "outcome", "status",
            "executed_after_change", "range", "omission_reason", "waiver_authority",
        }, name)
        for field in ("command_or_check", "changed_scope", "freshness_marker", "outcome"):
            _text(item[field], f"{name}.{field}")
        if item["status"] != "passed" or item["outcome"] != "passed":
            raise PlanningValidationError(f"{name} must record a passed status and outcome")
        if item["executed_after_change"] is not True:
            raise PlanningValidationError(f"{name} must be executed after the relevant change")
        if item["omission_reason"] is not None or item["waiver_authority"] is not None:
            raise PlanningValidationError(f"{name} cannot carry an omission or waiver when passed")
        if review_range(item["range"], f"{name}.range") != expected_range:
            raise PlanningValidationError(f"{name}.range must bind the reviewed/final fix range")

    record = fields(value, {
        "review_range", "acceptance_criteria", "authority", "local_rationale", "changed_files",
        "validation_evidence", "findings", "dispositions", "fix_range", "re_review_range",
        "deferred_findings", "final_validation",
    }, "review_record")
    current = review_range(current_range, "current_range")
    reviewed = review_range(record["review_range"], "review_record.review_range")
    if reviewed != current:
        raise PlanningValidationError("review_record.review_range is stale or moving; refresh before disposition")
    for name in ("acceptance_criteria", "authority", "local_rationale", "changed_files"):
        text_list(record[name], f"review_record.{name}")
    evidence = record["validation_evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise PlanningValidationError("review_record.validation_evidence must be a nonempty list")
    for index, item in enumerate(evidence):
        validation(item, f"review_record.validation_evidence[{index}]", reviewed)

    if not isinstance(record["findings"], list) or not isinstance(record["dispositions"], list):
        raise PlanningValidationError("review_record.findings and dispositions must be lists")
    findings: dict[str, Mapping[str, Any]] = {}
    for item in record["findings"]:
        item = fields(item, {"id", "severity", "kind", "description"}, "review_finding")
        identifier = _text(item["id"], "review_finding.id")
        if identifier in findings:
            raise PlanningValidationError("duplicate review finding id")
        if item["severity"] not in _REVIEW_FINDING_SEVERITIES or item["kind"] not in _REVIEW_FINDING_KINDS:
            raise PlanningValidationError("review_finding severity or kind is invalid")
        _text(item["description"], "review_finding.description")
        findings[identifier] = item
    dispositions: dict[str, Mapping[str, Any]] = {}
    for item in record["dispositions"]:
        item = fields(item, {
            "finding_id", "disposition", "reason", "evidence", "resolved_outcome", "governing_resolution",
        }, "finding_disposition")
        identifier = _text(item["finding_id"], "finding_disposition.finding_id")
        if identifier in dispositions:
            raise PlanningValidationError("duplicate finding disposition id")
        if item["disposition"] not in _REVIEW_DISPOSITIONS:
            raise PlanningValidationError("finding_disposition.disposition must be accept, reject, or defer")
        _text(item["reason"], "finding_disposition.reason")
        text_list(item["evidence"], "finding_disposition.evidence")
        for field in ("resolved_outcome", "governing_resolution"):
            if item[field] is not None:
                _text(item[field], f"finding_disposition.{field}")
        dispositions[identifier] = item
    if set(findings) != set(dispositions):
        raise PlanningValidationError("every review finding requires exactly one disposition")

    deferred = set(text_list(record["deferred_findings"], "review_record.deferred_findings", empty=True))
    accepted = False
    for identifier, finding in findings.items():
        disposition = dispositions[identifier]
        load_bearing = finding["severity"] in {"important", "critical"} or finding["kind"] in {"spec", "authority"}
        if load_bearing and disposition["disposition"] in {"reject", "defer"} and not disposition["governing_resolution"]:
            raise PlanningValidationError("load-bearing rejected/deferred finding requires governing resolution")
        if load_bearing and disposition["disposition"] == "accept" and not disposition["resolved_outcome"]:
            raise PlanningValidationError("accepted important/critical/spec finding requires resolved outcome")
        if disposition["disposition"] == "defer":
            if identifier not in deferred:
                raise PlanningValidationError("deferred finding must remain visible to final review")
            if load_bearing:
                raise PlanningValidationError("open load-bearing deferred finding blocks task completion")
        accepted = accepted or disposition["disposition"] == "accept"
    if deferred != {identifier for identifier, item in dispositions.items() if item["disposition"] == "defer"}:
        raise PlanningValidationError("deferred_findings must match deferred dispositions")

    fix_range = optional_range(record["fix_range"], "review_record.fix_range")
    re_review_range = optional_range(record["re_review_range"], "review_record.re_review_range")
    final_validation = record["final_validation"]
    if accepted:
        if fix_range is None or re_review_range is None or fix_range != re_review_range:
            raise PlanningValidationError("accepted finding requires a nonempty exact fix range and scoped re-review range")
        if final_validation is None:
            raise PlanningValidationError("accepted finding requires final validation after the fix")
        validation(final_validation, "review_record.final_validation", fix_range)
    elif fix_range is not None or re_review_range is not None or final_validation is not None:
        raise PlanningValidationError("fix/re-review and final validation require an accepted finding")
    return deepcopy(dict(record))


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
    # Recognition must be broader than the supported column-zero block syntax:
    # otherwise indented/flow policy can silently disappear into defaults. This
    # lexical guard only identifies keys; the existing YAML reader still parses
    # supported values. Keep quoted values, comments and literal/folded scalar
    # bodies opaque so documentation mentions do not become configuration.
    token_pattern = r'''"(?:\\.|[^"\\])*"|'(?:''|[^'])*'|\#[^\n]*|[{}\[\],:]|[^\s{}\[\],:#]+'''
    scalar_indent: int | None = None
    for line_number, line in enumerate(lines):
        indent = len(line) - len(line.lstrip(" "))
        if scalar_indent is not None:
            if not line.strip() or indent > scalar_indent:
                continue
            scalar_indent = None
        matches = list(re.finditer(token_pattern, line))
        tokens = [match.group() for match in matches]
        if tokens and tokens[-1].startswith("#"):
            tokens.pop()
        if tokens and re.fullmatch(r"[|>](?:[+-][1-9]?|[1-9][+-]?)?", tokens[-1]):
            # The scalar body ends when indentation returns to its owning key
            # (or sequence marker); a later real policy must still be examined.
            colons = [i for i, token in enumerate(tokens[:-1]) if token == ":" and i > 0]
            if colons:
                scalar_indent = matches[colons[-1] - 1].start()
            elif len(tokens) > 1 and tokens[-2] == "-":
                scalar_indent = matches[len(tokens) - 2].start()
        for position, token in enumerate(tokens[:-1]):
            if token.startswith("#"):
                break
            if (token in ("delivery_quality", "'delivery_quality'", '"delivery_quality"')
                    and tokens[position + 1] == ":"
                    and (position == 0 or tokens[position - 1] in ("{", ","))
                    and (line_number not in starts or position != 0)):
                raise PlanningValidationError(
                    "unsupported delivery_quality YAML syntax; use a column-zero delivery_quality mapping"
                )
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
