"""Experiment-only tiered ADR and Constitution context materializer.

This is deliberately a pure resolver.  It accepts already ranked decision
results and an explicit JSON binding between ADR lineage and Constitution
sections.  It has no dependency on production retrieval, ADR parsing, or MCP
write paths: the experiment can therefore measure this expansion separately
before any public contract changes.

The materialization policy is intentionally mechanical:

* expansion is selected by canonical decision rank, not an uncalibrated
  relevance band; the band remains visible as a diagnostic;
* the first configured strong signals receive full decision, ADR, lineage, and
  Constitution context, subject to global ADR and local detail caps;
* every other result is compact and names ADRs but never expands them;
* ``related`` references are evidence only.  They never create ADR membership
  or trigger an expansion.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence


BINDINGS_SCHEMA = "strong-context-v2-bindings.v1"
RESULT_SCHEMA = "strong-context-v2-result.v1"
TOP_K_SCHEMA = "strong-context-v2-top-k-recall.v1"

CANONICAL_DECISION_REF_RE = re.compile(
    r"^(?:mse_[a-z0-9]+|ms-[a-z0-9]+):d[1-9][0-9]*$"
)
_ROLES = frozenset({"governing", "supporting"})

DEFAULT_CONFIGURATION: dict[str, int] = {
    "result_cap": 5,
    "strong_cap": 2,
    "adr_cap": 3,
    "lineage_item_cap": 8,
    "constitution_binding_cap": 2,
    "constitution_excerpt_chars": 800,
    "compact_decision_chars": 400,
}

EXPANSION_POLICIES = frozenset({"ranked", "calibrated-strong", "legacy-band-strong"})


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def is_canonical_decision_ref(value: object) -> bool:
    return isinstance(value, str) and bool(CANONICAL_DECISION_REF_RE.fullmatch(value))


@dataclass(frozen=True)
class BindingIndex:
    """Validated binding data, indexed without changing source ordering."""

    adrs: tuple[dict[str, Any], ...]
    by_id: Mapping[str, dict[str, Any]]
    by_member: Mapping[str, tuple[str, ...]]
    fingerprint: str


def _unique_strings(value: object, label: str, *, canonical: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be an array of strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} must not contain duplicates")
    if canonical and not all(is_canonical_decision_ref(item) for item in value):
        raise ValueError(f"{label} must contain canonical decision refs")
    return tuple(value)


def _normalized_current(value: object, adr_id: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"ADR {adr_id} current must be an object")
    required = {"authoritative_ref", "status", "decision", "why", "evolution"}
    if set(value) != required:
        raise ValueError(f"ADR {adr_id} current must contain exactly {sorted(required)!r}")
    authoritative = value["authoritative_ref"]
    if authoritative is not None and not is_canonical_decision_ref(authoritative):
        raise ValueError(f"ADR {adr_id} authoritative_ref must be canonical or null")
    if not all(isinstance(value[key], str) for key in ("status", "decision", "why", "evolution")):
        raise ValueError(f"ADR {adr_id} current fields must be strings")
    if value["status"] not in {"accepted", "proposed", "rejected", "superseded", "invalid"}:
        raise ValueError(f"ADR {adr_id} current status is invalid")
    return dict(value)


def _normalized_lineage(value: object, adr_id: str, membership: set[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"ADR {adr_id} lineage must be an array")
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for row in value:
        if not isinstance(row, Mapping) or set(row) != {"ref", "predecessors", "decision", "why", "evolution", "status"}:
            raise ValueError(f"ADR {adr_id} lineage rows have an invalid shape")
        ref = row["ref"]
        if not is_canonical_decision_ref(ref) or ref not in membership or ref in seen:
            raise ValueError(f"ADR {adr_id} lineage ref must be a unique membership ref")
        if row["status"] not in {"accepted", "proposed", "rejected"}:
            raise ValueError(f"ADR {adr_id} lineage status is invalid")
        predecessors: list[dict[str, str]] = []
        predecessor_refs: set[str] = set()
        if not isinstance(row["predecessors"], list):
            raise ValueError(f"ADR {adr_id} lineage predecessors must be an array")
        for predecessor in row["predecessors"]:
            if not isinstance(predecessor, Mapping) or set(predecessor) != {"ref", "type"}:
                raise ValueError(f"ADR {adr_id} lineage predecessor has an invalid shape")
            target, kind = predecessor["ref"], predecessor["type"]
            if not is_canonical_decision_ref(target) or target not in membership or target in predecessor_refs:
                raise ValueError(f"ADR {adr_id} lineage predecessors must be unique membership refs")
            if kind not in {"evolves", "replaces"}:
                raise ValueError(f"ADR {adr_id} lineage predecessor type is invalid")
            predecessor_refs.add(target)
            predecessors.append({"ref": target, "type": kind})
        if not all(isinstance(row[key], str) for key in ("decision", "why", "evolution")):
            raise ValueError(f"ADR {adr_id} lineage text fields must be strings")
        seen.add(ref)
        rows.append({**dict(row), "predecessors": predecessors})
    by_ref = {row["ref"]: row for row in rows}
    for row in rows:
        if any(predecessor["ref"] == row["ref"] for predecessor in row["predecessors"]):
            raise ValueError(f"ADR {adr_id} lineage must not contain a self predecessor")
    visiting, visited = set(), set()
    def visit(ref: str) -> None:
        if ref in visiting:
            raise ValueError(f"ADR {adr_id} lineage must not contain a cycle")
        if ref in visited or ref not in by_ref:
            return
        visiting.add(ref)
        for predecessor in by_ref[ref]["predecessors"]:
            visit(predecessor["ref"])
        visiting.remove(ref)
        visited.add(ref)
    for ref in by_ref:
        visit(ref)
    return rows


def _normalized_constitution(value: object, adr_id: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError(f"ADR {adr_id} constitution_refs must be an array")
    seen: set[str] = set()
    rows: list[dict[str, str]] = []
    for row in value:
        if not isinstance(row, Mapping) or set(row) != {"ref", "role", "excerpt"}:
            raise ValueError(f"ADR {adr_id} Constitution bindings have an invalid shape")
        ref, role, excerpt = row["ref"], row["role"], row["excerpt"]
        if not isinstance(ref, str) or not ref or ref in seen:
            raise ValueError(f"ADR {adr_id} Constitution refs must be unique non-empty strings")
        if role not in _ROLES or not isinstance(excerpt, str):
            raise ValueError(f"ADR {adr_id} Constitution binding role or excerpt is invalid")
        seen.add(ref)
        rows.append({"ref": ref, "role": role, "excerpt": excerpt})
    return rows


def load_bindings(value: Mapping[str, Any]) -> BindingIndex:
    """Validate the experiment-only ADR-to-Constitution binding JSON."""
    if not isinstance(value, Mapping) or set(value) != {"schema", "adrs"}:
        raise ValueError("binding document must contain exactly schema and adrs")
    if value.get("schema") != BINDINGS_SCHEMA or not isinstance(value.get("adrs"), list):
        raise ValueError(f"binding document schema must be {BINDINGS_SCHEMA!r}")
    adrs: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    by_member: dict[str, list[str]] = {}
    for raw in value["adrs"]:
        if not isinstance(raw, Mapping) or set(raw) != {
            "adr_id", "membership", "current", "lineage", "constitution_refs", "related_refs"
        }:
            raise ValueError("ADR binding rows have an invalid shape")
        adr_id = raw["adr_id"]
        if not isinstance(adr_id, str) or not adr_id.startswith("adr_") or adr_id in by_id:
            raise ValueError("ADR IDs must be unique adr_ identifiers")
        membership = _unique_strings(raw["membership"], f"ADR {adr_id} membership", canonical=True)
        related = _unique_strings(raw["related_refs"], f"ADR {adr_id} related_refs", canonical=True)
        # A related link is intentionally not ADR lineage.  Keeping it in the
        # fixture binding makes the exclusion explicit and testable.
        if set(membership) & set(related):
            raise ValueError(f"ADR {adr_id} related_refs must not be membership refs")
        current = _normalized_current(raw["current"], adr_id)
        if current["authoritative_ref"] is not None and current["authoritative_ref"] not in membership:
            raise ValueError(f"ADR {adr_id} authoritative_ref must be ADR membership")
        lineage = _normalized_lineage(raw["lineage"], adr_id, set(membership))
        lineage_by_ref = {item["ref"]: item for item in lineage}
        head = current["authoritative_ref"]
        if head is not None and (head not in lineage_by_ref or lineage_by_ref[head]["status"] != "accepted"):
            raise ValueError(f"ADR {adr_id} authoritative_ref must be an accepted lineage revision")
        if head is not None and current["status"] not in {"accepted", "superseded"}:
            raise ValueError(f"ADR {adr_id} authoritative status conflicts with its accepted head")
        if head is None and current["status"] in {"accepted", "superseded"}:
            raise ValueError(f"ADR {adr_id} accepted status requires an authoritative_ref")
        row = {
            "adr_id": adr_id,
            "membership": list(membership),
            "current": current,
            "lineage": lineage,
            "constitution_refs": _normalized_constitution(raw["constitution_refs"], adr_id),
            "related_refs": list(related),
        }
        adrs.append(row)
        by_id[adr_id] = row
        for ref in membership:
            by_member.setdefault(ref, []).append(adr_id)
    return BindingIndex(
        tuple(adrs), by_id,
        {ref: tuple(ids) for ref, ids in by_member.items()},
        fingerprint({"schema": BINDINGS_SCHEMA, "adrs": adrs}),
    )


def normalize_configuration(configuration: Mapping[str, Any] | None = None) -> dict[str, Any]:
    configuration = configuration or {}
    if not isinstance(configuration, Mapping):
        raise ValueError("configuration must be an object")
    unknown = set(configuration) - (set(DEFAULT_CONFIGURATION) | {"expansion_policy", "relevance_calibrated"})
    if unknown:
        raise ValueError(f"unknown configuration field(s): {', '.join(sorted(unknown))}")
    normalized: dict[str, Any] = {**DEFAULT_CONFIGURATION, **configuration}
    numeric = {key: normalized[key] for key in DEFAULT_CONFIGURATION}
    if not all(isinstance(value, int) and value >= 0 for value in numeric.values()):
        raise ValueError("configuration values must be non-negative integers")
    normalized.setdefault("expansion_policy", "ranked")
    normalized.setdefault("relevance_calibrated", False)
    if normalized["expansion_policy"] not in EXPANSION_POLICIES:
        raise ValueError("expansion_policy must be ranked, calibrated-strong, or legacy-band-strong")
    if not isinstance(normalized["relevance_calibrated"], bool):
        raise ValueError("relevance_calibrated must be boolean")
    return normalized


def _ranked_results(value: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError("ranked results must be an array")
    result: list[dict[str, Any]] = []
    for rank, raw in enumerate(value, 1):
        if not isinstance(raw, Mapping):
            raise ValueError("ranked results must contain objects")
        ref, relevance = raw.get("ref"), raw.get("relevance")
        text = raw.get("excerpt", raw.get("text", ""))
        if not isinstance(ref, str) or relevance not in {"strong", "weak", "none"} or not isinstance(text, str):
            raise ValueError("each ranked result requires string ref, relevance, and excerpt/text")
        links = raw.get("links", {})
        if not isinstance(links, Mapping):
            raise ValueError("ranked result links must be an object")
        # Retain only typed link references as compact context. Never traverse
        # these links to discover ADRs; membership is the sole join key.
        normalized_links: dict[str, list[str]] = {}
        for kind in ("evolves", "replaces", "related"):
            values = links.get(kind, [])
            if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
                raise ValueError(f"ranked result {kind} links must be an array of strings")
            normalized_links[kind] = list(values)
        result.append({"rank": rank, "ref": ref, "relevance": relevance, "excerpt": text, "links": normalized_links})
    return result


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit] + "\n[truncated by strong-context-v2]", True


def _lineage_slice(adr: Mapping[str, Any], matched: Sequence[str], cap: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return accepted authority plus the matched revision's evidence path.

    A pending/rejected branch can be relevant to a query even when it does not
    descend from the accepted head.  Preserve that branch (and its typed
    predecessors) alongside the governing path rather than silently dropping
    it from the context.
    """
    nodes = {row["ref"]: row for row in adr["lineage"]}
    current = adr["current"]["authoritative_ref"]
    wanted = set(matched) & set(nodes)
    included: set[str] = set()
    roots = [ref for ref in (current, *sorted(wanted)) if ref in nodes]
    stack = list(dict.fromkeys(roots))
    while stack:
        ref = stack.pop()
        if ref in included:
            continue
        included.add(ref)
        stack.extend(
            predecessor["ref"]
            for predecessor in reversed(nodes[ref]["predecessors"])
            if predecessor["ref"] in nodes
        )
    # A predecessor can be curated membership without being a revision node.
    # Keep that match visible but do not invent a lineage block for it.
    dangling = sorted(set(matched) - set(nodes))
    ordered = [row for row in adr["lineage"] if row["ref"] in included]
    omissions: list[dict[str, Any]] = []
    if cap < len(ordered):
        required = list(dict.fromkeys(ref for ref in (current, *sorted(wanted)) if ref in nodes))
        mandatory_roots = tuple(required)
        required.extend(
            predecessor["ref"]
            for ref in mandatory_roots
            for predecessor in nodes[ref]["predecessors"]
            if predecessor["ref"] in nodes
        )
        required = list(dict.fromkeys(required))
        selected = list(required)
        selected.extend(row["ref"] for row in ordered if row["ref"] not in selected)
        # A cap is a budget for supplementary history.  It may never remove
        # the accepted head, the matched revision, or its direct typed link.
        kept = set(selected[:max(cap, len(required))])
        omissions.append({"kind": "lineage-cap", "adr_id": adr["adr_id"], "omitted_refs": [row["ref"] for row in ordered if row["ref"] not in kept]})
        ordered = [row for row in ordered if row["ref"] in kept]
    if dangling:
        omissions.append({"kind": "membership-without-revision-node", "adr_id": adr["adr_id"], "refs": dangling})
    return [dict(row) for row in ordered], omissions


def _compact(item: Mapping[str, Any], index: BindingIndex, configuration: Mapping[str, Any]) -> dict[str, Any]:
    text, truncated = _truncate(item["excerpt"], configuration["compact_decision_chars"])
    refs = list(index.by_member.get(item["ref"], ())) if is_canonical_decision_ref(item["ref"]) else []
    result = {
        "tier": "compact",
        "rank": item["rank"],
        "decision": {"ref": item["ref"], "relevance": item["relevance"], "excerpt": text, "links": item["links"]},
        "adr_refs": refs,
    }
    if truncated:
        result["decision"]["truncated"] = True
    return result


def resolve_strong_context(
    ranked_results: Sequence[Mapping[str, Any]],
    bindings: BindingIndex | Mapping[str, Any],
    configuration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Materialize tiered context and a deterministic audit trace.

    Expansion is driven only by the searched decision's membership. In
    particular, a ``related`` link is carried as compact evidence but never
    followed to find a different ADR.
    """
    index = bindings if isinstance(bindings, BindingIndex) else load_bindings(bindings)
    config = normalize_configuration(configuration)
    ranked = _ranked_results(ranked_results)[:config["result_cap"]]
    omissions: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    tiers: list[dict[str, Any]] = []
    expanded_signals = 0
    selected_adrs: set[str] = set()
    for item in ranked:
        ref = item["ref"]
        policy = config["expansion_policy"]
        canonical = is_canonical_decision_ref(ref)
        if policy == "ranked":
            eligible = canonical
        elif policy == "calibrated-strong":
            eligible = canonical and config["relevance_calibrated"] and item["relevance"] == "strong"
        else:
            eligible = canonical and item["relevance"] == "strong"
        if not eligible:
            if not canonical:
                reason = "non-canonical-ref"
            elif policy == "calibrated-strong" and not config["relevance_calibrated"]:
                reason = "uncalibrated-band"
            else:
                reason = "non-strong"
            trace.append({"rank": item["rank"], "ref": ref, "action": "compact", "reason": reason})
            tiers.append(_compact(item, index, config))
            continue
        if expanded_signals >= config["strong_cap"]:
            trace.append({"rank": item["rank"], "ref": ref, "action": "compact", "reason": "strong-cap"})
            omissions.append({"kind": "strong-cap", "rank": item["rank"], "ref": ref})
            tiers.append(_compact(item, index, config))
            continue
        expanded_signals += 1
        candidate_ids = index.by_member.get(ref, ())
        included_adrs: list[dict[str, Any]] = []
        skipped_adrs: list[str] = []
        reused_adrs: list[str] = []
        lineage_deltas: list[dict[str, Any]] = []
        for adr_id in candidate_ids:
            adr = index.by_id[adr_id]
            if adr_id in selected_adrs:
                reused_adrs.append(adr_id)
                lineage, lineage_omissions = _lineage_slice(adr, (ref,), config["lineage_item_cap"])
                omissions.extend(lineage_omissions)
                lineage_deltas.append({"adr_id": adr_id, "matched_decision_refs": [ref], "relevant_lineage": lineage})
                continue
            if adr_id not in selected_adrs and len(selected_adrs) >= config["adr_cap"]:
                skipped_adrs.append(adr_id)
                continue
            selected_adrs.add(adr_id)
            lineage, lineage_omissions = _lineage_slice(adr, (ref,), config["lineage_item_cap"])
            omissions.extend(lineage_omissions)
            constitution: list[dict[str, Any]] = []
            for position, binding in enumerate(adr["constitution_refs"]):
                if position >= config["constitution_binding_cap"]:
                    omissions.append({"kind": "constitution-binding-cap", "adr_id": adr_id, "ref": binding["ref"]})
                    continue
                excerpt, truncated = _truncate(binding["excerpt"], config["constitution_excerpt_chars"])
                constitution.append({"ref": binding["ref"], "role": binding["role"], "excerpt": excerpt, "truncated": truncated})
                if truncated:
                    omissions.append({"kind": "constitution-excerpt-truncated", "adr_id": adr_id, "ref": binding["ref"]})
            included_adrs.append({
                "adr_id": adr_id,
                "matched_decision_refs": [ref],
                "current": dict(adr["current"]),
                "relevant_lineage": lineage,
                "constitution": constitution,
                "related_refs": list(adr["related_refs"]),
            })
        if skipped_adrs:
            omissions.append({"kind": "adr-cap", "rank": item["rank"], "ref": ref, "adr_ids": skipped_adrs})
        trace.append({
            "rank": item["rank"], "ref": ref, "action": "expand",
            "matched_adr_ids": list(candidate_ids), "included_adr_ids": [row["adr_id"] for row in included_adrs],
            "skipped_adr_ids": skipped_adrs,
        })
        tiers.append({
            "tier": "full",
            "rank": item["rank"],
            "decision": {"ref": ref, "relevance": item["relevance"], "excerpt": item["excerpt"], "links": item["links"]},
            "adrs": included_adrs,
            "adr_refs": reused_adrs,
            "lineage_deltas": lineage_deltas,
        })
    payload = {
        "schema": RESULT_SCHEMA,
        "configuration": config,
        "binding_fingerprint": index.fingerprint,
        "tiers": tiers,
        "omissions": omissions,
        "trace": trace,
    }
    payload["fingerprint"] = fingerprint(payload)
    return payload


def _coverage(found: Iterable[str], required: Sequence[str]) -> dict[str, Any]:
    required_tuple = tuple(dict.fromkeys(required))
    found_set = set(found)
    hit = [ref for ref in required_tuple if ref in found_set]
    return {
        "found": hit,
        "missing": [ref for ref in required_tuple if ref not in found_set],
        "total": len(required_tuple),
        "recall": 1.0 if not required_tuple else len(hit) / len(required_tuple),
        "complete": len(hit) == len(required_tuple),
    }


def top_k_recall(
    ranked_results: Sequence[Mapping[str, Any]],
    bindings: BindingIndex | Mapping[str, Any],
    *,
    required_decision_refs: Sequence[str],
    required_adr_ids: Sequence[str],
    required_constitution_refs: Sequence[str],
    ks: Sequence[int] = (1, 2, 3, 5),
    strong_only: bool = False,
) -> dict[str, Any]:
    """Measure upstream rank recall before any token/detail budget is spent.

    ADR and Constitution recall are derived by membership and explicit bindings
    from the top-K decisions.  Related edges cannot improve these values.
    """
    index = bindings if isinstance(bindings, BindingIndex) else load_bindings(bindings)
    ranked = _ranked_results(ranked_results)
    if not ks or not all(isinstance(k, int) and k > 0 for k in ks):
        raise ValueError("ks must be non-empty positive integers")
    required_decisions = _unique_strings(list(required_decision_refs), "required_decision_refs", canonical=True)
    required_adrs = _unique_strings(list(required_adr_ids), "required_adr_ids")
    required_constitution = _unique_strings(list(required_constitution_refs), "required_constitution_refs")
    rows: list[dict[str, Any]] = []
    for k in sorted(set(ks)):
        top = ranked[:k]
        refs = [item["ref"] for item in top if is_canonical_decision_ref(item["ref"]) and (not strong_only or item["relevance"] == "strong")]
        # Preserve ranking order but do not let duplicate rows inflate discovery.
        refs = list(dict.fromkeys(refs))
        adr_ids = list(dict.fromkeys(adr_id for ref in refs for adr_id in index.by_member.get(ref, ())))
        constitution_refs = list(dict.fromkeys(
            binding["ref"] for adr_id in adr_ids for binding in index.by_id[adr_id]["constitution_refs"]
        ))
        decision = _coverage(refs, required_decisions)
        adr = _coverage(adr_ids, required_adrs)
        constitution = _coverage(constitution_refs, required_constitution)
        rows.append({
            "k": k,
            "ranked_decision_refs": refs,
            "derived_adr_ids": adr_ids,
            "derived_constitution_refs": constitution_refs,
            "decision": decision,
            "adr": adr,
            "constitution": constitution,
            "complete": decision["complete"] and adr["complete"] and constitution["complete"],
        })
    payload = {
        "schema": TOP_K_SCHEMA,
        "strong_only": strong_only,
        "binding_fingerprint": index.fingerprint,
        "required": {
            "decision_refs": list(required_decisions),
            "adr_ids": list(required_adrs),
            "constitution_refs": list(required_constitution),
        },
        "rows": rows,
    }
    payload["fingerprint"] = fingerprint(payload)
    return payload
