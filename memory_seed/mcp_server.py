from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from .core import (
    MEMORY_DIR_NAME,
    RETRACTABLE_KINDS,
    _git_text,
    branch_status,
    commit_reference_ids,
    foreign_package_message,
    package_provenance,
    resolve_runtime,
    session_fuse,
    worktree_guard,
)
# The MCP server is a thin JSON-RPC wrapper over the public retrieval service
# (memory_seed/retrieval.py) - the same service the in-package Lense and the
# future companion UI distribution consume, so every surface returns the same
# answers. `format_search_results` is re-exported here for compatibility.
from .retrieval import (
    RetrievalSpecResolutionError,
    augment_chunks_with_link_sidecars,
    canonical_retrieval_json,
    chunk_to_dict,
    describe_refines_chain,
    format_search_results,
    get_chunk,
    audit_link_gaps,
    link_audit_payload,
    ranked_to_dict,
    search_memory,
)
from .retrieval_adapters import (
    RetrievalInputValidationError,
    preview_retrieval_input,
    resolve_retrieval_input_pack,
)
from .semantic_cache import (
    build_related_entry_graph,
    extract_memory_chunks,
    suggest_related_entries,
    suggest_related_for_draft,
    replacing_lineage_heads,
)


SERVER_NAME = "memory-seed"
SERVER_VERSION = "0.1.0"
_MCP_TOPIC_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

# The only MCP tools allowed to mutate project state.  Keep this production
# classifier explicit: a schema feature such as ``dry_run`` is not evidence of
# mutation, and read tools must never gain write status by convention alone.
MUTATING_TOOL_NAMES = frozenset(
    {
        "memory_session_append",
        "memory_session_integrate",
        "memory_adr_reviewed",
        "memory_link_retract",
        "memory_decision_provenance_bind",
        "memory_reflection_ledger_init",
        "memory_reflection_ledger_append",
        "memory_reflection_ledger_close",
    }
)


def _link_suggestion_rows(ranked: Any) -> list[dict[str, Any]]:
    return [
        {
            **ranked_to_dict(item.result),
            "shared_files": list(item.shared_files),
            "file_overlap_bonus": round(item.file_overlap_bonus, 6),
            "adjusted_score": round(item.adjusted_score, 6),
            "consulted": item.consulted,
        }
        for item in ranked
    ]


def _append_link_suggestion_rows(ranked: Any) -> list[dict[str, Any]]:
    """Stable suggestion rows for preview/write parity.

    Appending a following entry can extend the preceding entry's parsed line
    range by one separator line. That location metadata is useful in the
    dedicated suggest tool but is not part of the append nudge, whose preview
    and write payloads should compare byte-for-byte.
    """
    rows = _link_suggestion_rows(ranked)
    for row in rows:
        row.pop("line_range", None)
        row.pop("entry_line_range", None)
    return rows


def _unlinked_decisions(decisions: Any) -> list[str]:
    """Decision ordinals carrying no related or lifecycle link at write time."""
    missing: list[str] = []
    for item in decisions if isinstance(decisions, list) else []:
        if not isinstance(item, Mapping):
            continue
        links = item.get("links")
        linked = isinstance(links, Mapping) and any(
            isinstance(links.get(kind), list) and bool(links.get(kind))
            for kind in ("related_entries", "replaces", "evolves")
        )
        if not linked and item.get("decision"):
            missing.append(str(item["decision"]))
    return missing


def _mcp_authored_decision_issues(body: str, decisions: Any) -> list[str]:
    """Validate the MCP-only authored-topic contract before any write.

    ``session_append_entry`` intentionally remains permissive enough to import
    and repair historical entries.  MCP is the authoring boundary, so it makes
    every body decision explicit and classifies it with authored area/activity
    topics before the core writer can publish either an entry or a sidecar.
    """
    from .core import entry_body_decisions

    issues: list[str] = []
    expected = [decision.ordinal for decision in entry_body_decisions(body)]
    if not isinstance(decisions, list) or not decisions:
        return [
            "decisions is required and must be a non-empty list with one topic envelope for every body decision"
        ]

    supplied_ordinals: list[str] = []
    for index, raw in enumerate(decisions, start=1):
        if not isinstance(raw, dict):
            issues.append(f"decisions[{index}] must be an object")
            continue
        ordinal = raw.get("decision")
        if not isinstance(ordinal, str) or not ordinal.strip():
            issues.append(f"decisions[{index}].decision must name a body ordinal such as 'd1'")
        else:
            supplied_ordinals.append(ordinal)

        topics = raw.get("topics")
        if not isinstance(topics, dict):
            issues.append(f"decisions[{index}].topics must be an object with required area and activity")
            continue

        area = topics.get("area")
        if not isinstance(area, str) or not _MCP_TOPIC_SLUG_RE.fullmatch(area):
            issues.append(f"decisions[{index}].topics.area must be one non-empty topic slug")

        activity = topics.get("activity")
        if isinstance(activity, str):
            activity_values = [activity]
        elif isinstance(activity, list):
            activity_values = activity
        else:
            activity_values = []
        if not activity_values or not all(
            isinstance(value, str) and _MCP_TOPIC_SLUG_RE.fullmatch(value)
            for value in activity_values
        ):
            issues.append(
                f"decisions[{index}].topics.activity must be one non-empty topic slug or a non-empty list of topic slugs"
            )

    expected_set = set(expected)
    supplied_set = set(supplied_ordinals)
    missing = sorted(
        {
            ordinal
            for ordinal in expected
            if supplied_ordinals.count(ordinal) < expected.count(ordinal)
        }
    )
    unexpected = sorted(supplied_set - expected_set)
    duplicate = sorted({ordinal for ordinal in supplied_ordinals if supplied_ordinals.count(ordinal) > 1})
    if missing:
        issues.append(
            "decisions must cover every body decision exactly once; missing " + ", ".join(missing)
        )
    if unexpected:
        issues.append(
            "decisions must name only body decision ordinals; unexpected " + ", ".join(unexpected)
        )
    if duplicate:
        issues.append(
            "decisions must cover every body decision exactly once; duplicated " + ", ".join(duplicate)
        )
    return issues


TOOLS: list[dict[str, Any]] = [
    {
        "name": "memory_decision_provenance",
        "description": "Show a decision's validated Git-reference bindings and temporary before/after code projections. Read-only; code is unavailable rather than inferred when Git evidence cannot be resolved.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "decision_ref": {"type": "string", "description": "Exact <entry_id>:dN decision reference."},
                "cwd": {"type": "string", "default": "."},
                "context_lines": {"type": "integer", "default": 3, "minimum": 0, "maximum": 20},
                "runtime": {"type": "object", "description": "Explicit runtime ownership record when inspecting an active descendant or retired metadata."},
            },
            "required": ["decision_ref"], "additionalProperties": False,
        },
    },
    {
        "name": "memory_decision_provenance_bind",
        "description": "Validate and append one reference-only provenance binding to its owning runtime sidecar. Default is a dry run; set apply true to write. Uses the same validation and output shape as CLI provenance bind.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "binding": {"type": "object"}, "cwd": {"type": "string", "default": "."},
                "runtime": {"type": "object", "description": "The current runtime's owned sidecar; retired and detached owners are read-only."},
                "apply": {"type": "boolean", "default": False},
            },
            "required": ["binding"], "additionalProperties": False,
        },
    },
    {
        "name": "memory_retrieval_spec_preview",
        "description": (
            "Validate and plan one inline Retrieval Specification or exact local profile against canonical "
            "Markdown. Read-only; creates no Evidence Pack."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec": {"type": "object"},
                "profile": {"type": "string"},
                "profile_version": {"type": "integer"},
                "overrides": {"type": "object"},
                "cwd": {"type": "string", "default": "."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "memory_retrieval_spec_resolve",
        "description": (
            "Resolve one inline Retrieval Specification or exact local profile into an ephemeral Evidence "
            "Pack returned inline. Read-only; no cache, registry, provider, or Trace dependency."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec": {"type": "object"},
                "profile": {"type": "string"},
                "profile_version": {"type": "integer"},
                "overrides": {"type": "object"},
                "cwd": {"type": "string", "default": "."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "memory_task_packet_preview",
        "description": "Validate, measure, resolve, and return one complete deterministic Task Packet inline. Read-only; it does not export, dispatch workers, or create worktrees.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dispatch": {"type": "object"}, "binding": {"type": "object"},
                "environment": {"type": "object"}, "pricing": {"type": "object"},
                "cwd": {"type": "string", "default": "."},
            },
            "required": ["dispatch", "binding"], "additionalProperties": False,
        },
    },
    {
        "name": "memory_task_packet_compile",
        "description": "Compile and return one complete deterministic Task Packet inline. Read-only; MCP never exports a file or dispatches workers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dispatch": {"type": "object"}, "binding": {"type": "object"},
                "environment": {"type": "object"}, "pricing": {"type": "object"},
                "cwd": {"type": "string", "default": "."},
            },
            "required": ["dispatch", "binding"], "additionalProperties": False,
        },
    },
    {
        "name": "memory_search",
        "description": "Search local Memory Seed session logs and return ranked, source-linked context chunks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "cwd": {"type": "string", "default": "."},
                "top_k": {"type": "integer", "default": 8},
                "lambda_days": {"type": "number", "default": 0.01},
                "recency_enabled": {"type": "boolean", "default": True},
                "recency_floor": {"type": "number", "default": 0.15},
                "semantic_enabled": {"type": "boolean", "default": True},
                "user": {
                    "type": "string",
                    "description": "Filter to per-user session files whose filename/user slug matches this value.",
                },
                "date_from": {
                    "type": "string",
                    "description": "Inclusive session_date lower bound in YYYY-MM-DD format.",
                },
                "date_to": {
                    "type": "string",
                    "description": "Inclusive session_date upper bound in YYYY-MM-DD format.",
                },
                "granularity": {
                    "type": "string",
                    "enum": ["decision", "entry", "section"],
                    "default": "decision",
                    "description": "Default 'decision': one result per recorded decision, keyed by its canonical mse_<id>:dN identity and carrying that decision's whole DRAFT block (D/R/A/F/T) plus only its own topics and lifecycle edges; entries without decision headings return whole. 'entry' returns the ## entry as one unit; 'section' splits on ###+ headings.",
                },
                "exclude_replaced": {
                    "type": "boolean",
                    "default": False,
                    "description": "Opt-in: drop entries that a later decision has replaced (non-empty replaced_by). Off by default - replaced entries stay retrievable.",
                },
                "supersession_damping": {
                    "type": "boolean",
                    "default": True,
                    "description": "On by default: down-rank (not drop) entries a later decision replaced, so a live replacement out-ranks the decision it retires. Draws replaced_by from the sidecar-augmented graph. Replaced entries stay fully retrievable (down-rank only, never hidden); pass false to rank them at full weight.",
                },
                "replacing_successor_boost": {
                    "type": "boolean",
                    "default": True,
                    "description": "On by default bounded successor lift: when a retired entry matches the query, its terminal live replacement may be boosted only if that replacement already has positive query relevance. Never hard-injects, never bypasses exclude_replaced; pass false to restore damp-only ordering.",
                },
                "attention_boost": {
                    "type": "boolean",
                    "default": False,
                    "description": "Opt-in: fold decayed fetch-frequency (how often agents actually opened each entry via memory_get_chunk) into ranking. Off by default pending the ranking-ab gate; the signal is always exposed read-only as attention_score/fetch_count/last_fetch on every result.",
                },
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Opt-in pre-ranking filter: keep only entries whose stored topics: match one of these slugs (aliases from .memory-seed/topics.yaml resolve both ways). Unknown slugs narrow, never error.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_link_suggest",
        "description": "Rank older session entries to link from a target entry, closing the authoring loop: returns paste-ready related_entries candidates. Read-only; the agent writes the edge into its own new entry.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "."},
                "entry_id": {
                    "type": "string",
                    "description": "Entry to suggest links for. Defaults to the newest entry (the one just written).",
                },
                "top_k": {"type": "integer", "default": 5},
                "consulted": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Entry ids you retrieved while grounding this work (the memory axis). Any candidate in this set is flagged `consulted` and sorted first - the natural source for replaces/evolves lineage edges that shared-file evidence misses. Candidates only; you still classify. Omit for file-overlap-only ranking.",
                },
            },
        },
    },
    {
        "name": "memory_link_show",
        "description": "Show one entry's related-entry graph node: stored outbound edges, computed inbound backlinks, supersession edges, importance score, and linked-commit count. Read-only graph traversal.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "string"},
                "cwd": {"type": "string", "default": "."},
            },
            "required": ["entry_id"],
        },
    },
    {
        "name": "memory_links_chain",
        "description": "Return the derived refines lifecycle chain for one known entry or decision ref: root, ordered members, head, length, and owning ADR evidence. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ref": {"type": "string", "description": "Entry or decision ref: mse_<id> or mse_<id>:dN."},
                "cwd": {"type": "string", "default": "."},
            },
            "required": ["ref"],
            "additionalProperties": False,
        },
    },
    {
        "name": "memory_link_audit",
        "description": "Return judgment-ready lifecycle gap candidates and ranking provenance. Mirrors the read-only part of `link audit`; it cannot apply or scaffold sidecars.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "."},
                "entry_id": {"type": "string", "description": "Audit one target entry; omit to audit every entry."},
                "session_date": {"type": "string", "description": "Scope targets to YYYY-MM-DD while retaining earlier corpus candidates."},
                "top_k": {"type": "integer", "default": 5, "minimum": 1},
                "semantic_enabled": {"type": "boolean", "default": True, "description": "Set false for lexical-only candidate ranking."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "memory_esr",
        "description": "Return the complete structured End-of-Session Report. Equivalent to `esr --json`; it never repairs authoritative memory, but may incrementally refresh the rebuildable ignored temporal-lineage cache and other derived cache state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "."},
                "session_date": {"type": "string", "description": "Session date in YYYY-MM-DD; defaults to today."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "memory_decision_provenance_check",
        "description": "Audit one runtime-owned provenance sidecar and its Git reference evidence. Read-only; unavailable Git is reported as unverifiable rather than raised.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "."},
                "runtime": {"type": "object", "description": "Explicit measured runtime record for descendant or retired inspection."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "memory_branch_status",
        "description": "Read Git branch/worktree posture and return Memory Seed branch-history guidance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "."},
            },
        },
    },
    {
        "name": "memory_worktree_guard",
        "description": "Classify whether the current Git worktree is safe for a named agent. Read-only pre-write guard.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_type": {
                    "type": "string",
                    "description": "Agent slug to check, e.g. codex, claude, gemini, or cursor.",
                },
                "write_intent": {
                    "type": "boolean",
                    "default": False,
                    "description": "When true, root and foreign namespace policy is enforced as a write gate.",
                },
                "allow_root_write": {
                    "type": "boolean",
                    "default": False,
                    "description": "Explicit override for approved root-checkout integration or cleanup writes.",
                },
                "cwd": {"type": "string", "default": "."},
            },
            "required": ["agent_type"],
        },
    },
    {
        "name": "memory_session_fuse_preview",
        "description": "Dry-run branch-local session entry and diagram-sidecar fuse planning. Read-only; use the CLI --apply path during an in-progress merge to write.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "branch": {
                    "type": "string",
                    "description": "Source task branch whose branch-local session entries and sidecars should be inspected.",
                },
                "cwd": {"type": "string", "default": "."},
                "base": {
                    "type": "string",
                    "default": "HEAD",
                    "description": "Base ref to compare against, normally the current integration branch HEAD.",
                },
            },
            "required": ["branch"],
        },
    },
    {
        "name": "memory_get_chunk",
        "description": "Fetch an exact Memory Seed chunk by chunk_id. Decision ids (entry_id:d1) resolve, and a decision payload carries `entry_context`: the entry-level sections that frame it - Summary, Follow-up, Validation - since a decision block alone omits what the session was doing and what was left open. Sibling decisions are not included. The payload is a projection of the full record: exact aliases (path/date/source_file/entry_title) and the lexical_terms scoring index are omitted, as are empty optional fields - but lifecycle fields (replaces/replaced_by/evolves/evolved_by/replacing_head) and the attention triple are always present, because their emptiness is a statement: unsuperseded, never fetched.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chunk_id": {"type": "string"},
                "cwd": {"type": "string", "default": "."},
            },
            "required": ["chunk_id"],
        },
    },
    {
        "name": "memory_topics_list",
        "description": "List the controlled topic vocabulary from .memory-seed/topics.yaml. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "."},
            },
        },
    },
    {
        "name": "memory_topic_inspect",
        "description": "Inspect one controlled topic or alias and show matching session entries. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Canonical topic slug or alias to inspect.",
                },
                "cwd": {"type": "string", "default": "."},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "memory_topics_check",
        "description": "Validate controlled topic vocabulary shape and entry topic usage. Mirrors `memory-seed topics check`; read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "."},
            },
        },
    },
    {
        "name": "memory_adrs_list",
        "description": "List living architectural decision threads and their replay-derived authoritative heads. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {"cwd": {"type": "string", "default": "."}},
            "additionalProperties": False,
        },
    },
    {
        "name": "memory_adr_show",
        "description": "Read one composed ADR sidecar and return its replay-derived status and source decision.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "."},
                "adr_id": {"type": "string"},
            },
            "required": ["adr_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "memory_adr_review",
        "description": "Resolve lifecycle decision references to every ADR whose current or historical lineage they affect. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "."},
                "targets": {"type": "array", "minItems": 1, "items": {"type": "string"}},
            },
            "required": ["targets"],
            "additionalProperties": False,
        },
    },
    {
        "name": "memory_adr_reviewed",
        "description": (
            "Append a reviewed-no-change event to one ADR using an existing session entry as "
            "the evidence anchor. This moves no ADR head and creates no session entry. CLI twin: "
            "memory-seed adr reviewed --adr-id <id> --entry <entry-id> --reason <text>."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "."},
                "adr_id": {"type": "string"},
                "entry_id": {"type": "string"},
                "reason": {"type": "string", "minLength": 1},
                "timestamp": {"type": "string", "description": "UTC ISO timestamp; default: now."},
                "dry_run": {"type": "boolean", "default": False},
            },
            "required": ["adr_id", "entry_id", "reason"],
            "additionalProperties": False,
        },
    },
    {
        "name": "memory_adrs_check",
        "description": "Validate every ADR sidecar and replay its append-only lifecycle. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {"cwd": {"type": "string", "default": "."}},
            "additionalProperties": False,
        },
    },
    {
        "name": "memory_session_append",
        "description": (
            "Append a session entry with every structural guarantee enforced. THIS IS THE ONLY WAY TO AUTHOR AN ENTRY - "
            "do not hand-write session files. The tool owns structure (target path, heading timestamp from the server "
            "clock, canonical entry_id, YAML shape, chronological ordering) and refuses malformed or out-of-order writes; "
            "you own voice (title and D/R/A/F/T body prose, all taken verbatim). New semantic fields belong in the "
            "decision-sidecar envelope: use `decisions` to attach each body decision's controlled topics and lifecycle "
            "links. The writer stores those only in topic/link sidecars, before it publishes the narrative entry; do not "
            "combine `decisions` with the legacy top-level topic/link fields. "
            "Guards run together and nothing is written when any fails: chronology, ref existence (fabricated ids are "
            "refused), forward-only lifecycle edges, controlled topic vocabulary, id collision, and DRAFT body format. "
            "Refusals come back as ok=false with an issues list, each independently fixable. Pair with "
            "memory_link_suggest / memory_link_show to choose related_entries, replaces and evolves before calling. "
            "If any decision remains unlinked, every passing response includes link_suggestions; pass consulted entry "
            "ids to rank retrieved memory first. Lifecycle links into an ADR run the same content-bound review "
            "preflight as CLI session append and may return a zero-write receipt plus full ADR contexts. "
            "Set dry_run to run every guard and get the id, timestamp, target path and the rendered entry back without writing - inspect the final output, then commit by calling again WITH the returned timestamp, so a minute tick between preview and write cannot change the id."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "."},
                "title": {"type": "string", "description": "Entry title (the text after 'YYYY-MM-DD HH:MM - ')."},
                "body": {
                    "type": "string",
                    "description": "The entry body, verbatim. Current DRAFT shape: '### Decisions' with one or more '#### Dn - name' subsections, each containing '- D:' and mandatory '- R:' items, optionally '- A:', '- F:', and '- T:'. Legacy singular '### Decision' remains readable but is refused for new appends.",
                },
                "user_initials": {"type": "string", "description": "user_initials field, e.g. JNL."},
                "agent_type": {"type": "string", "description": "agent_type field, e.g. claude."},
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Controlled-vocabulary slugs or aliases; aliases are stored canonically. Unknown slugs are refused.",
                },
                "decisions": {
                    "type": "array",
                    "minItems": 1,
                    "description": "Required decision-sidecar envelope. Supply exactly one object for every body decision: {decision: 'dN', topics: {area: slug, activity: slug | slug[], source?: 'write-time'}, links: {related_entries?: entry_id[], replaces?: entry_id[], evolves?: entry_id[]}}. Each decision must carry one Area and at least one Activity; topic and lifecycle values are written only to their respective sidecars.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "decision": {"type": "string", "minLength": 1, "description": "Body decision ordinal, e.g. d1."},
                            "topics": {
                                "type": "object",
                                "properties": {
                                    "area": {"type": "string", "minLength": 1, "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$", "description": "One controlled-vocabulary Area slug or alias."},
                                    "activity": {
                                        "oneOf": [
                                            {"type": "string", "minLength": 1, "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
                                            {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1, "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"}},
                                        ],
                                        "description": "One or more controlled-vocabulary Activity slugs or aliases.",
                                    },
                                    "source": {"type": "string", "enum": ["write-time"]},
                                    "proposed_topic": {
                                        "type": "object",
                                        "properties": {
                                            "slug": {
                                                "type": "string",
                                                "minLength": 1,
                                                "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$",
                                            },
                                            "axis": {"type": "string", "enum": ["area", "activity"]},
                                        },
                                        "required": ["slug", "axis"],
                                        "description": (
                                            "A REQUEST for vocabulary that does not exist yet. Never a topic: it does "
                                            "not resolve, is never returned as an attribution, and cannot enter "
                                            "topics.yaml by being used. Supply it ALONGSIDE the still-mandatory area "
                                            "and activity, so the write is never blocked; ESR surfaces it for "
                                            "adjudication with this decision as the evidence. `axis` is required - a "
                                            "request nobody can place on an axis cannot be ruled on. Refused if the "
                                            "slug already resolves; use it as area or activity instead."
                                        ),
                                    },
                                },
                                "required": ["area", "activity"],
                            },
                            "links": {"type": "object"},
                            "adrs": {
                                "type": "array",
                                "description": "Mandatory review outcomes for ADRs matched by this decision's evolves/replaces links.",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "adr_id": {"type": "string"},
                                        "outcome": {"type": "string", "enum": ["revise", "no-change"]},
                                        "decision": {"type": "string"},
                                        "reason": {"type": "string"},
                                        "impact": {"type": "string"},
                                        "why": {"type": "string", "description": "deprecated alias for reason"},
                                        "evolution": {"type": "string", "description": "deprecated alias for impact"},
                                        "assertions": {"type": "object"},
                                    },
                                    "required": ["adr_id", "outcome"],
                                    "additionalProperties": False,
                                },
                            },
                        },
                        "required": ["decision", "topics"],
                    },
                },
                "related_entries": {"type": "array", "items": {"type": "string"}, "description": "entry_id values this entry relates to. Must already exist and predate it."},
                "replaces": {"type": "array", "items": {"type": "string"}, "description": "entry_id values this entry retires (the old decision is now wrong or dead). Granularity is mandated (2026-07-24): name an ordinal only when the entry it belongs to has 2+ decisions. A target with 2+ decisions must be narrowed as <entry_id>:dN (comma-separated for several, e.g. mse_x:d1,d4); a single- or no-decision target stays a bare id (:d1 there is rejected as redundant). When THIS entry's body has 2+ decisions each item needs a 'dN -> ' prefix naming the authoring decision."},
                "evolves": {"type": "array", "items": {"type": "string"}, "description": "entry_id values this entry refines (the old decision stays valid but incomplete). Same decision-granularity grammar as replaces: :dN only on a 2+-decision target (bare otherwise), 'dN -> ' source prefix only when this entry is multi-decision."},
                "project_path": {"type": "string", "default": "."},
                "subproject_path": {"type": "string", "description": "subproject_path field; omit for null."},
                "branch": {"type": "string", "description": "branch field; omit to auto-capture from git."},
                "auto_branch": {"type": "boolean", "default": True, "description": "Set false to omit the branch field entirely."},
                "timestamp": {
                    "type": "string",
                    "description": "Heading timestamp 'YYYY-MM-DD HH:MM'. OMIT in normal use: the server stamps from its own clock. Two sanctioned explicit uses: echoing a dry_run's returned timestamp back on the real write (the id is a hash of the timestamp, so a fresh stamp that ticks to the next minute mints a DIFFERENT id than previewed - echoing pins preview and write to the same bytes), and backfill. Values far from the server clock earn a drift warning.",
                },
                "user": {"type": "string", "description": "Override the active user slug when resolving a per-user target."},
                "consulted": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Entry ids fetched while grounding this work. Used only to rank the append response's link suggestions; it writes no edge by itself.",
                },
                "adr_review_receipt": {"type": "string", "description": "Content-bound receipt returned by the mandatory ADR review gate."},
                "dry_run": {"type": "boolean", "default": False, "description": "Run every guard and report entry_id, timestamp, path and `rendered` - the exact entry block a real call would append - without writing."},
            },
            "required": ["title", "body", "user_initials", "agent_type", "decisions"],
        },
    },
    {
        "name": "memory_link_retract",
        "description": (
            "Retract a published lifecycle edge, append-only, and optionally re-author it under the right kind or "
            "evolution type in the same block. THIS IS THE MANDATED FIX for the `links check` errors "
            "`untyped-evolves`, `unknown-evolution-type` and `multiple-refines-successors`: the declaring block is "
            "never reopened, so the correction is a fresh block in the SOURCE entry's dated link sidecar that names "
            "the old edge under `retracts:` and re-authors it beside. Do not hand-write retract blocks. "
            "`ref` is the retracted edge's target in the ordinary ref grammar (`mse_x`, `mse_x:d1`, `mse_x:d1,d3`, "
            "optionally `dM -> ` prefixed and `(type)` suffixed) written EXACTLY as the edge was authored - a "
            "comma-separated ref fans out to one retract line per ordinal, because a retract names exactly one edge, "
            "while the re-authored line keeps the comma form. Guards run before anything is written and report "
            "together: unknown kind or unparseable ref, an unknown source entry, an edge the corpus never declared "
            "(the checker's dangling-retract), a retraction that would pre-date its declaration, a date_pin that is "
            "not the declaration date, and a `refines` retype whose one successor slot another entry already holds. "
            "Set dry_run to run every guard and get `rendered` - the exact block a real call would append - back "
            "without writing."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "."},
                "from_entry": {
                    "type": "string",
                    "description": "The edge's SOURCE entry_id; its session date selects the sidecar file.",
                },
                "kind": {
                    "type": "string",
                    "enum": list(RETRACTABLE_KINDS),
                    "description": "The kind of edge being retracted, as authored ('supersedes'/'related' are the legacy spellings).",
                },
                "ref": {
                    "type": "string",
                    "description": "The retracted edge's target ref, spelled as the edge was authored.",
                },
                "retype": {
                    "type": "string",
                    "description": "Re-author the same ref under a new kind (replaces/evolves/related_entries) or with an evolution type (refines/builds-on). Omit for a pure retraction.",
                },
                "note": {"type": "string", "description": "One-line note recorded beside the correction."},
                "date_pin": {
                    "type": "string",
                    "description": "The ORIGINAL declaration date (YYYY-MM-DD), recorded on each retract line and validated against it.",
                },
                "timestamp": {
                    "type": "string",
                    "description": "Block heading timestamp 'YYYY-MM-DD HH:MM'. OMIT in normal use: the server stamps from its own clock. Block identity is (entry_id, heading timestamp), so a fresh stamp lets a later correction join the same entry.",
                },
                "dry_run": {"type": "boolean", "default": False, "description": "Run every guard and report `rendered` without writing."},
            },
            "required": ["from_entry", "kind", "ref"],
        },
    },
    {
        "name": "memory_session_integrate",
        "description": (
            "Merge a task branch and fuse its branch-local session memory in one step, so branch entries land in "
            "chronological order on the trunk instead of wherever a raw line-merge puts them. Fails closed: any session "
            "problem (modified existing entry, missing entry_id, duplicate ids) aborts before the git merge starts, and "
            "a conflict outside session files aborts the merge and restores a clean tree rather than leaving one "
            "half-merged. Refused when the project's integration_mode is 'pr', because that path pushes and opens a "
            "pull request, and refused when merge_trigger is 'manual', because landing then needs explicit user "
            "authorization the unattended path cannot represent (run the CLI with --user-approved instead). Set "
            "dry_run to see the plan without merging (never refused)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "."},
                "branch": {"type": "string", "description": "Task branch to merge and fuse."},
                "dry_run": {"type": "boolean", "default": False, "description": "Report the fuse plan without merging or writing."},
            },
            "required": ["branch"],
        },
    },
    {
        "name": "memory_reflection_board_view",
        "description": "Read every active Reflection Board v1 candidate from the current branch's trusted Git history. Read-only; malformed and unsupported reserved candidates remain visible.",
        "inputSchema": {"type": "object", "properties": {"cwd": {"type": "string", "default": "."}}, "additionalProperties": False},
    },
    {
        "name": "memory_reflection_ledger_view",
        "description": "Read one committed, history-classified Reflection Board v1 ledger. Read-only; this never reads an uncommitted ledger suffix.",
        "inputSchema": {"type": "object", "properties": {"workstream_id": {"type": "string"}, "cwd": {"type": "string", "default": "."}}, "required": ["workstream_id"], "additionalProperties": False},
    },
    {
        "name": "memory_reflection_ledger_init",
        "description": "Preview or apply initialization of the current branch's only Reflection Board v1 ledger through the kernel-owned transaction writer. The server never accepts a caller-supplied ID, ledger bytes, Git commit, or ref.",
        "inputSchema": {"type": "object", "properties": {"retention_days": {"type": "integer", "enum": [7, 14, 30], "default": 7}, "apply": {"type": "boolean", "default": False}, "cwd": {"type": "string", "default": "."}}, "additionalProperties": False},
    },
    {
        "name": "memory_reflection_ledger_append",
        "description": "Preview or apply one Reflection Board v1 record through the same kernel-owned transaction writer as the CLI. It never accepts raw ledger bytes, Git identities, receipts, or a history override.",
        "inputSchema": {"type": "object", "properties": {"workstream_id": {"type": "string"}, "role": {"type": "string", "enum": ["planner", "implementer", "reviewer", "orchestrator"]}, "chain_id": {"type": "string"}, "relationship": {"type": "string", "default": "refines"}, "parents": {"type": "array", "items": {"type": "string"}, "default": []}, "no_related_thread": {"type": "boolean", "default": False}, "conclusion": {"type": "string"}, "reasoning": {"type": "string"}, "source": {"type": "string"}, "confidence": {"type": "string", "default": "high"}, "to_phase": {"type": "string"}, "apply": {"type": "boolean", "default": False}, "cwd": {"type": "string", "default": "."}}, "required": ["workstream_id", "role", "conclusion", "reasoning", "source"], "additionalProperties": False},
    },
]


TOOLS.extend([
    {
        "name": "memory_reflection_ledger_check",
        "description": "Check one committed Reflection Board v1 ledger and report pending close receipts.",
        "inputSchema": {"type": "object", "properties": {"cwd": {"type": "string", "default": "."},
            "workstream_id": {"type": "string"}}, "required": ["workstream_id"], "additionalProperties": False},
    },
    {
        "name": "memory_reflection_ledger_close",
        "description": "Preview exact ordinary session receipt mappings or close a resolved, integrated chain. Apply revalidates Git history and receipt coverage through the guarded kernel transaction. A successful close remains closed_receipts_pending until its new member and outcome receipts are committed by the ordinary session writer.",
        "inputSchema": {"type": "object", "properties": {
            "cwd": {"type": "string", "default": "."}, "workstream_id": {"type": "string"},
            "chain_id": {"type": "string"}, "apply": {"type": "boolean", "default": False},
            "receipts": {"type": "array", "default": [], "items": {"type": "object", "properties": {
                "session_path": {"type": "string"}, "entry_id": {"type": "string"},
                "decision_id": {"type": "string"}, "disposition": {"type": "string"},
                "record_id": {"type": "string"}}, "required": ["session_path", "entry_id", "decision_id", "disposition"],
                "additionalProperties": False}},
        }, "required": ["workstream_id", "chain_id"], "additionalProperties": False},
    },
])
for _reflection_tool in TOOLS:
    if _reflection_tool["name"] in {"memory_reflection_ledger_init", "memory_reflection_ledger_append", "memory_reflection_ledger_close"}:
        _reflection_tool["inputSchema"]["properties"]["expected_head"] = {
            "type": "string", "description": "Refuse a changed branch head after a reviewed preview."}
        if _reflection_tool["name"] != "memory_reflection_ledger_init":
            _reflection_tool["inputSchema"]["properties"]["expected_ledger_digest"] = {
                "type": "string", "description": "Refuse changed ledger bytes after a reviewed preview."}


def call_tool(
    name: str,
    arguments: dict[str, Any] | None = None,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    args = arguments or {}
    if name in {
        "memory_retrieval_spec_preview",
        "memory_retrieval_spec_resolve",
    }:
        from .retrieval_profiles import RetrievalProfileValidationError
        from .retrieval_spec import RetrievalSpecValidationError

        if not isinstance(args, dict):
            return {
                "ok": False,
                "error": {
                    "code": "invalid_arguments",
                    "message": "tool arguments must be a JSON object",
                    "stage": "validation",
                    "completed_stages": [],
                    "details": {},
                },
            }
        unsupported = sorted(
            set(args) - {"spec", "profile", "profile_version", "overrides", "cwd"}
        )
        if unsupported:
            return {
                "ok": False,
                "error": {
                    "code": "invalid_arguments",
                    "message": "unsupported retrieval tool argument(s)",
                    "stage": "validation",
                    "completed_stages": [],
                    "details": {"unsupported_arguments": unsupported},
                },
            }
        try:
            if name == "memory_retrieval_spec_preview":
                return {
                    "ok": True,
                    "preview": preview_retrieval_input(
                        spec=args.get("spec"), profile=args.get("profile"),
                        profile_version=args.get("profile_version"),
                        overrides=args.get("overrides"), cwd=args.get("cwd", "."),
                    ),
                }
            return {
                "ok": True,
                "pack": resolve_retrieval_input_pack(
                    spec=args.get("spec"), profile=args.get("profile"),
                    profile_version=args.get("profile_version"),
                    overrides=args.get("overrides"), cwd=args.get("cwd", "."),
                ),
            }
        except (RetrievalInputValidationError, RetrievalSpecValidationError) as exc:
            return {
                "ok": False,
                "error": {
                    "code": "invalid_spec",
                    "message": str(exc),
                    "stage": "validation",
                    "completed_stages": [],
                    "details": {},
                },
            }
        except RetrievalProfileValidationError as exc:
            return {
                "ok": False,
                "error": {
                    "code": "invalid_profile",
                    "message": str(exc),
                    "stage": "profile_expansion",
                    "completed_stages": [],
                    "details": {},
                },
            }
        except RetrievalSpecResolutionError as exc:
            return {"ok": False, "error": exc.to_dict()}

    if name in {"memory_task_packet_preview", "memory_task_packet_compile"}:
        from .task_packet import TaskPacketValidationError, compile_task_packet
        from .retrieval_profiles import RetrievalProfileValidationError
        from .retrieval_spec import RetrievalSpecValidationError

        if not isinstance(args, dict):
            return {"ok": False, "error": {"code": "invalid_arguments", "message": "tool arguments must be a JSON object", "stage": "validation", "completed_stages": [], "details": {}}}
        unsupported = sorted(set(args) - {"dispatch", "binding", "environment", "pricing", "cwd"})
        if unsupported:
            return {"ok": False, "error": {"code": "invalid_arguments", "message": "unsupported task packet tool argument(s)", "stage": "validation", "completed_stages": [], "details": {"unsupported_arguments": unsupported}}}
        dispatch, binding = args.get("dispatch"), args.get("binding")
        if not isinstance(dispatch, dict) or not isinstance(binding, dict):
            return {"ok": False, "error": {"code": "invalid_arguments", "message": "dispatch and binding must be JSON objects", "stage": "validation", "completed_stages": [], "details": {}}}
        try:
            packet = compile_task_packet(dispatch, binding, args.get("cwd", "."), environment=args.get("environment"), pricing=args.get("pricing"))
            return {"ok": True, "preview" if name.endswith("_preview") else "packet": packet}
        except TaskPacketValidationError as exc:
            return {"ok": False, "error": exc.to_dict()}
        except RetrievalSpecValidationError as exc:
            return {"ok": False, "error": {
                "code": "invalid_spec", "message": str(exc),
                "stage": "validation", "completed_stages": [], "details": {},
            }}
        except RetrievalSpecResolutionError as exc:
            return {"ok": False, "error": exc.to_dict()}
        except RetrievalProfileValidationError as exc:
            return {"ok": False, "error": {"code": "invalid_profile", "message": str(exc), "stage": "profile_expansion", "details": {}}}

    if name in {"memory_reflection_board_view", "memory_reflection_ledger_view", "memory_reflection_ledger_check",
                "memory_reflection_ledger_init", "memory_reflection_ledger_append", "memory_reflection_ledger_close"}:
        from .reflection_operations import run_reflection_operation
        return run_reflection_operation(name.removeprefix("memory_reflection_"), arguments)

    if name == "memory_search":
        query = _required_str(args, "query")
        return _project_search_payload(search_memory(
            query,
            args.get("cwd", "."),
            top_k=int(args.get("top_k", 8)),
            today=today,
            lambda_days=float(args.get("lambda_days", 0.01)),
            recency_enabled=bool(args.get("recency_enabled", True)),
            recency_floor=float(args.get("recency_floor", 0.15)),
            semantic_enabled=bool(args.get("semantic_enabled", True)),
            embedding_provider=args.get("_embedding_provider"),
            granularity=str(args.get("granularity", "decision")),
            user=_optional_str(args, "user"),
            date_from=_optional_date(args, "date_from"),
            date_to=_optional_date(args, "date_to"),
            exclude_replaced=bool(
                args.get("exclude_replaced", args.get("exclude_superseded", False))
            ),  # legacy param spelling accepted (renamed 2026-07-24)
            supersession_damping=bool(args.get("supersession_damping", True)),
            replacing_successor_boost=bool(args.get("replacing_successor_boost", True)),
            attention_boost=bool(args.get("attention_boost", False)),
            topics=list(args.get("topics") or []) or None,
        ))

    if name == "memory_link_suggest":
        entry_id = _optional_str(args, "entry_id")
        target, ranked = suggest_related_entries(
            cwd=args.get("cwd", "."),
            entry_id=entry_id,
            top_k=int(args.get("top_k", 5)),
            consulted=list(args.get("consulted") or []) or None,
        )
        return {
            "target": {
                "entry_id": target.entry_id,
                "title": target.title,
                "session_date": target.session_date.isoformat(),
                "source": target.source_path,
            },
            "suggestions": _link_suggestion_rows(ranked),
            "related_entries": [item.chunk.entry_id for item in ranked],
        }

    if name == "memory_link_show":
        entry_id = _required_str(args, "entry_id")
        cwd = args.get("cwd", ".")
        entry_chunks = augment_chunks_with_link_sidecars(
            extract_memory_chunks(cwd, granularity="entry"),
            cwd,
        )
        graph = build_related_entry_graph(cwd=cwd, chunks=entry_chunks)
        node = graph.get(entry_id)
        if node is None:
            raise ValueError(f"entry_id {entry_id} not found")
        chunk = next((c for c in entry_chunks if c.entry_id == entry_id), None)
        commit_refs = commit_reference_ids(
            resolve_runtime(cwd).workspace_root,
            entry_id,
            chunk.commits if chunk else (),
        )
        return {
            "entry_id": node.entry_id,
            "title": node.title,
            "source_path": node.source_path,
            "session_date": node.session_date.isoformat(),
            "outbound": list(node.outbound),
            "inbound": list(node.inbound),
            "replaces": list(node.replaces),
            "replaced_by": list(node.replaced_by),
            "replacing_head": list(replacing_lineage_heads(graph, entry_id)),
            "evolves": list(node.evolves),
            "evolved_by": list(node.evolved_by),
            "continuity": [
                {"kind": block.kind, "from": block.from_ref, "to": block.to_ref}
                for block in (chunk.continuity if chunk else ())
            ],
            "inbound_relation_count": len(node.inbound),
            "importance_score": round(node.importance_score, 6),
            "commit_reference_count": len(commit_refs),
        }

    if name == "memory_links_chain":
        _reject_unsupported_arguments(args, {"ref", "cwd"})
        ref = _required_str(args, "ref")
        cwd = _cwd(args)
        return describe_refines_chain(cwd, ref)

    if name == "memory_link_audit":
        _reject_unsupported_arguments(args, {"cwd", "entry_id", "session_date", "top_k", "semantic_enabled"})
        cwd = _cwd(args)
        entry_id = _optional_str(args, "entry_id")
        session_date = _optional_date(args, "session_date")
        top_k = _positive_int(args, "top_k", default=5)
        semantic_enabled = _optional_bool(args, "semantic_enabled", default=True)
        semantic_status: dict[str, Any] = {}
        gaps = audit_link_gaps(
            cwd=cwd,
            entry_id=entry_id,
            session_date=session_date.isoformat() if session_date else None,
            top_k=top_k,
            semantic_enabled=semantic_enabled,
            semantic_status=semantic_status,
        )
        return link_audit_payload(gaps, semantic_status)

    if name == "memory_esr":
        from .esr import esr_report

        _reject_unsupported_arguments(args, {"cwd", "session_date"})
        session_date = _optional_date(args, "session_date")
        return esr_report(
            cwd=_cwd(args),
            session_date=session_date.isoformat() if session_date else None,
        ).to_dict()

    if name == "memory_decision_provenance":
        from .cli import provenance_surface

        _reject_unsupported_arguments(args, {"decision_ref", "cwd", "context_lines", "runtime"})
        return provenance_surface(
            "show", cwd=_cwd(args), decision_ref=_required_str(args, "decision_ref"),
            context_lines=args.get("context_lines", 3), owner=args.get("runtime"),
        )

    if name == "memory_decision_provenance_bind":
        from .cli import provenance_surface

        _reject_unsupported_arguments(args, {"binding", "cwd", "runtime", "apply"})
        binding = args.get("binding")
        if not isinstance(binding, Mapping):
            raise ValueError("binding must be an object")
        runtime = args.get("runtime")
        if runtime is not None and not isinstance(runtime, Mapping):
            raise ValueError("runtime must be an object")
        return provenance_surface(
            "bind", cwd=_cwd(args), binding=binding, owner=runtime,
            apply=_optional_bool(args, "apply", default=False),
        )

    if name == "memory_decision_provenance_check":
        from .cli import provenance_surface

        _reject_unsupported_arguments(args, {"cwd", "runtime"})
        runtime = args.get("runtime")
        if runtime is not None and not isinstance(runtime, Mapping):
            raise ValueError("runtime must be an object")
        return provenance_surface("check", cwd=_cwd(args), owner=runtime)

    if name == "memory_branch_status":
        return {"status": branch_status(cwd=args.get("cwd", ".")).to_dict()}

    if name == "memory_worktree_guard":
        status = worktree_guard(
            cwd=args.get("cwd", "."),
            agent_type=_required_str(args, "agent_type"),
            write_intent=bool(args.get("write_intent", False)),
            allow_root_write=bool(args.get("allow_root_write", False)),
        )
        return status.to_dict()

    if name == "memory_session_fuse_preview":
        branch = _required_str(args, "branch")
        base = args.get("base", "HEAD")
        if not isinstance(base, str) or not base.strip():
            raise ValueError("Invalid string argument: base")
        result = session_fuse(
            cwd=args.get("cwd", "."),
            branch=branch,
            base=base.strip(),
            apply=False,
        )
        return {
            "ok": not result.issues,
            "changed": result.changed,
            "planned_entries": result.planned_entries,
            "planned_sidecars": result.planned_sidecars,
            "planned_link_sidecars": result.planned_link_sidecars,
            "planned_topic_sidecars": result.planned_topic_sidecars,
            "removed_sources": result.removed_sources,
            "already_present": result.already_present,
            "issues": result.issues,
            "write_surface": "CLI-only; run apply during an in-progress git merge.",
            "merge_checkpoint_command": f"git merge --no-ff --no-commit {branch}",
            "apply_command": f"memory-seed session fuse --branch {branch} --base {base.strip()} --apply",
        }

    if name == "memory_get_chunk":
        chunk_id = _required_str(args, "chunk_id")
        return {"chunk": _project_chunk_payload(get_chunk(chunk_id, args.get("cwd", ".")))}

    if name == "memory_topics_list":
        from .topics import load_topic_index

        index = load_topic_index(args.get("cwd", "."))
        return {
            "path": index.path,
            "exists": index.exists,
            "schema_version": index.schema_version,
            "topics": [_topic_record_to_dict(record) for record in index.topics],
            "write_surface": "Read-only. Use CLI/project file edits with user approval to change topics.yaml.",
        }

    if name == "memory_topic_inspect":
        from .topics import load_topic_index

        cwd = args.get("cwd", ".")
        requested = _required_str(args, "topic")
        index = load_topic_index(cwd)
        resolution = index.resolution()
        canonical = resolution.get(requested)
        record = next((item for item in index.topics if item.slug == canonical), None) if canonical else None
        matching_names = sorted(name for name, slug in resolution.items() if slug == canonical) if canonical else []
        entries = []
        if canonical:
            from .retrieval import augment_chunks_with_topic_sidecars

            for chunk in augment_chunks_with_topic_sidecars(
                extract_memory_chunks(cwd, granularity="entry"), cwd
            ):
                authored_match = any(resolution.get(topic, topic) == canonical for topic in chunk.topics)
                inferred_match = any(
                    resolution.get(topic, topic) == canonical for topic in chunk.inferred_topics
                )
                if authored_match or inferred_match:
                    entries.append(
                        {
                            "entry_id": chunk.entry_id,
                            "title": chunk.title,
                            "session_date": chunk.session_date.isoformat(),
                            "source": chunk.source_path,
                            "topics": list(chunk.topics),
                            "inferred_topics": list(chunk.inferred_topics),
                            # Which channel put this entry in the list. Inspect
                            # is a provenance surface, so a caller must never
                            # have to guess whether a human vouched for it.
                            "matched_via": "authored" if authored_match else "inferred",
                        }
                    )
        return {
            "requested": requested,
            "found": record is not None,
            "canonical": canonical,
            "topic": _topic_record_to_dict(record) if record else None,
            "matching_names": matching_names,
            "usage_count": len(entries),
            "entries": entries,
            "write_surface": "Read-only. Use CLI/project file edits with user approval to change topics.yaml.",
        }

    if name == "memory_topics_check":
        from .topics import check_topics

        result = check_topics(args.get("cwd", "."))
        return {
            "ok": result.ok,
            "topics_defined": result.topics_defined,
            "entries_checked": result.entries_checked,
            "issues": [
                {
                    "severity": issue.severity,
                    "kind": issue.kind,
                    "detail": issue.detail,
                    "source": issue.source,
                }
                for issue in result.issues
            ],
            "write_surface": "Read-only. Use CLI/project file edits with user approval to change topics.yaml.",
        }

    if name == "memory_adrs_list":
        from .adr import adr_to_dict, iter_adrs

        cwd = Path(str(args.get("cwd", "."))).resolve()
        return {"ok": True, "adrs": [adr_to_dict(record, include_events=False) for record in iter_adrs(cwd)]}

    if name == "memory_adr_show":
        from .adr import adr_to_dict, parse_adr

        cwd = Path(str(args.get("cwd", "."))).resolve()
        adr_id = _required_str(args, "adr_id")
        path = resolve_runtime(cwd).memory_dir / "decisions" / f"{adr_id}.md"
        if not path.exists():
            return {"ok": False, "issues": [f"ADR not found: {adr_id}"]}
        try:
            record = parse_adr(path)
        except (OSError, ValueError) as exc:
            return {"ok": False, "issues": [str(exc)]}
        return {"ok": True, **adr_to_dict(record)}

    if name == "memory_adr_review":
        from .adr import adr_review_context, canonical_decision_refs

        cwd = Path(str(args.get("cwd", "."))).resolve()
        raw_targets = args.get("targets")
        if not isinstance(raw_targets, list) or not raw_targets:
            return {"ok": False, "issues": ["targets must be a non-empty list"]}
        targets: list[str] = []
        for raw in raw_targets:
            if isinstance(raw, str):
                targets.extend(canonical_decision_refs(cwd, raw))
        contexts = adr_review_context(cwd, tuple(dict.fromkeys(targets)))
        return {"ok": True, "targets": list(dict.fromkeys(targets)), "matched_adrs": contexts}

    if name == "memory_adr_reviewed":
        from .adr import record_reviewed_no_change

        result = record_reviewed_no_change(
            Path(str(args.get("cwd", "."))).resolve(),
            adr_id=_required_str(args, "adr_id"),
            entry_id=_required_str(args, "entry_id"),
            reason=_required_str(args, "reason"),
            timestamp=_optional_str(args, "timestamp"),
            dry_run=bool(args.get("dry_run", False)),
        )
        payload = {
            "ok": result.ok,
            "written": result.written,
            "adr_id": result.adr_id,
            "current_status": result.current_status,
            "authoritative_decision": result.authoritative_decision,
            "path": str(result.path) if result.path else None,
            "issues": list(result.issues),
        }
        if result.rendered is not None:
            payload["rendered"] = result.rendered
        return payload

    if name == "memory_adrs_check":
        from .adr import check_adrs

        ok, issues = check_adrs(Path(str(args.get("cwd", "."))).resolve())
        return {"ok": ok, "issues": issues}

    if name == "memory_session_integrate":
        from .core import read_integration_mode, read_merge_trigger, session_merge_branch

        cwd = Path(str(args.get("cwd", "."))).resolve()
        runtime = resolve_runtime(cwd)
        root = runtime.workspace_root
        branch = _required_str(args, "branch")
        dry_run = bool(args.get("dry_run", False))

        # PR mode pushes and opens a pull request - outward-facing actions that
        # should not happen unattended. Hand the operator the command instead.
        mode = read_integration_mode(root)
        if mode == "pr":
            return {
                "ok": False,
                "committed": False,
                "integration_mode": mode,
                "issues": ["project integration_mode is 'pr'; opening a pull request pushes and is not run unattended"],
                "cli_command": f"memory-seed session integrate --branch {branch}",
            }

        # merge_trigger: manual holds a landing for the user. The autonomous MCP
        # path cannot represent user authorization, so it declines a real
        # integrate and hands the operator the CLI command carrying the approval
        # flag. A dry run only previews and is allowed through.
        trigger = read_merge_trigger(root)
        if trigger == "manual" and not dry_run:
            return {
                "ok": False,
                "committed": False,
                "integration_mode": mode,
                "merge_trigger": trigger,
                "issues": ["project merge_trigger is 'manual'; landing a branch needs explicit user authorization and is not run unattended"],
                "cli_command": f"memory-seed session merge-branch --branch {branch} --user-approved",
            }

        result = session_merge_branch(root, branch=branch, dry_run=dry_run)

        # session_merge_branch deliberately parks a non-session conflict for a
        # human to resolve. An autonomous caller cannot resolve one and must not
        # walk away from a half-merged tree, so abort back to a clean state and
        # report - the branch is untouched and the operator can retry by hand.
        # Refusals now roll their own merge back in core, so `merge_aborted` may
        # already be true here; this stays as the backstop for the one exit core
        # deliberately parks (a non-session conflict) plus a failed core abort.
        aborted = result.merge_aborted
        if result.merge_in_progress:
            abort_code, abort_out = _git_text(root, ("merge", "--abort"))
            aborted = aborted or abort_code == 0
            if abort_code != 0:
                result.issues.append(f"merge left in progress and could not be aborted: {abort_out or '(no output)'}")

        return {
            "ok": result.committed or (dry_run and not result.issues),
            "committed": result.committed,
            "integration_mode": mode,
            "dry_run": dry_run,
            "planned_entries": result.planned_entries,
            "planned_sidecars": result.planned_sidecars,
            "planned_link_sidecars": result.planned_link_sidecars,
            "planned_topic_sidecars": result.planned_topic_sidecars,
            "removed_sources": result.removed_sources,
            "already_present": result.already_present,
            "stamped_entries": result.stamped_entries,
            "source_worktree": result.source_worktree,
            "worktree_cleanup_status": result.worktree_cleanup_status,
            "worktree_cleanup_detail": result.worktree_cleanup_detail,
            "worktree_cleanup_attempts": result.worktree_cleanup_attempts,
            "conflicts": result.conflicts,
            "merge_aborted": aborted,
            "merge_in_progress": result.merge_in_progress and not aborted,
            "issues": result.issues,
        }

    if name == "memory_session_append":
        # Deferred import for the writer only. `resolve_runtime` must NOT be
        # re-imported here: a function-local import binds the name for the whole
        # function scope, shadowing the module-level one and leaving every
        # earlier branch that uses it reading an unassigned local.
        from .core import session_append_entry

        cwd = Path(str(args.get("cwd", "."))).resolve()
        # The one hazard MCP adds that the CLI does not have. resolve_runtime
        # fails open and the writer does mkdir(parents=True), so a wrong cwd
        # would not error - it would create a phantom .memory-seed tree and
        # write a real-looking entry into it. Worse, the id-collision and
        # fabricated-ref guards read that empty tree and pass vacuously, so the
        # entry would look clean. The CLI is immune because it hardcodes its own
        # directory; a server started from an arbitrary cwd is not.
        runtime = resolve_runtime(cwd)
        if not runtime.memory_dir.is_dir():
            return {
                "ok": False,
                "written": False,
                "issues": [
                    f"no Memory Seed runtime at {cwd} (looked for {MEMORY_DIR_NAME}/); "
                    "pass cwd pointing at the project root - refusing rather than creating an empty one"
                ],
            }

        # Same clock discipline the id tool carried: the server stamps, because
        # authored timestamps drifted hours from reality in practice and the
        # Trail renders them as fact. Explicit stamps stay allowed for sanctioned
        # backfill and earn a drift warning.
        now = args.get("_now") or datetime.now().strftime("%Y-%m-%d %H:%M")
        supplied = _optional_str(args, "timestamp")

        body = args.get("body")
        if not isinstance(body, str) or not body.strip():
            return {"ok": False, "written": False, "issues": ["body is empty - pass the D/R/A/F/T prose"]}

        authored_decision_issues = _mcp_authored_decision_issues(body, args.get("decisions"))
        if authored_decision_issues:
            return {"ok": False, "written": False, "issues": authored_decision_issues}

        # A lifecycle link to any current or historical ADR member is a
        # mandatory, content-bound review gate. MCP cannot push unsolicited
        # context, so the first append call returns the ADRs and writes zero
        # bytes; the caller retries with the exact receipt and one outcome per
        # matched ADR.
        from .adr import append_review_proposal, preflight_append_adr_review

        decisions = args["decisions"]
        proposal = append_review_proposal(
            title=args.get("title"),
            body=body,
            timestamp=supplied or now,
            user_initials=args.get("user_initials"),
            agent_type=args.get("agent_type"),
            decisions=decisions,
        )
        review = preflight_append_adr_review(
            cwd,
            proposal=proposal,
            decisions=decisions,
            supplied_receipt=_optional_str(args, "adr_review_receipt"),
        )
        if not review.ok:
            return {
                "ok": False,
                "written": False,
                "review_required": review.review_required,
                "issues": list(review.issues),
                "adr_review_receipt": review.receipt,
                "matched_adrs": list(review.contexts),
                "lifecycle_targets": list(review.targets),
                "timestamp": supplied or now,
            }

        unlinked = _unlinked_decisions(decisions)
        needs_chain_snapshot = any(
            isinstance(decision, Mapping)
            and isinstance(decision.get("links"), Mapping)
            and isinstance(decision["links"].get("evolves"), Sequence)
            and not isinstance(decision["links"].get("evolves"), (str, bytes))
            and len(decision["links"]["evolves"]) >= 2
            for decision in decisions
        )
        snapshot = None
        if needs_chain_snapshot:
            # One pre-write view can serve both the chain guard and the draft
            # suggestion response. Cache maintenance is best-effort; the core
            # guard retains its existing source-based fallback on an unexpected
            # snapshot error.
            try:
                from .corpus_cache import get_corpus_snapshot

                snapshot = get_corpus_snapshot(cwd)
            except Exception:
                snapshot = None

        result = session_append_entry(
            cwd,
            title=_required_str(args, "title"),
            body=body,
            user_initials=_required_str(args, "user_initials"),
            agent_type=_required_str(args, "agent_type"),
            topics=list(args.get("topics") or []),
            related_entries=list(args.get("related_entries") or []),
            replaces=list(args.get("replaces") or args.get("supersedes") or []),  # legacy key accepted
            evolves=list(args.get("evolves") or []),
            decisions=args["decisions"],
            adr_review_contexts=review.contexts,
            adr_review_outcomes=review.outcomes,
            project_path=str(args.get("project_path", ".")),
            subproject_path=_optional_str(args, "subproject_path"),
            branch=_optional_str(args, "branch"),
            auto_branch=bool(args.get("auto_branch", True)),
            timestamp=supplied or now,
            explicit_user=_optional_str(args, "user"),
            dry_run=bool(args.get("dry_run", False)),
            snapshot=snapshot,
        )
        # Refusals are results, not JSON-RPC errors: the guards report several
        # independently-fixable problems at once, and an error string would
        # flatten them into one line the caller cannot act on item by item.
        payload: dict[str, Any] = {
            "ok": result.ok,
            "written": result.written,
            "entry_id": result.entry_id,
            "timestamp": result.timestamp,
            "path": str(result.path) if result.path else None,
            "issues": list(result.issues),
            "sidecar_paths": [str(path) for path in result.sidecar_paths],
            "journal_path": str(result.journal_path) if result.journal_path else None,
        }
        # Only a dry run carries the rendered block: pre-commit inspection is
        # its purpose, while echoing the body back after a real write would
        # bloat every payload with text the caller already has.
        if result.rendered is not None:
            payload["rendered"] = result.rendered
        if result.rendered_sidecars is not None:
            payload["rendered_sidecars"] = result.rendered_sidecars
        if result.ok and unlinked:
            if snapshot is None:
                try:
                    from .corpus_cache import get_corpus_snapshot

                    snapshot = get_corpus_snapshot(cwd)
                except Exception:
                    # Cache maintenance must not turn a successful source write
                    # into a reported failure. The suggestion helper retains its
                    # authoritative raw-source fallback when no snapshot exists.
                    snapshot = None
            instruction = (
                "Classify each consequential consulted candidate as replaces, evolves, related, "
                "or no-edge before treating this append as fully linked."
            )
            try:
                _, ranked = suggest_related_for_draft(
                    cwd,
                    entry_id=result.entry_id or "",
                    title=_required_str(args, "title"),
                    body=body,
                    timestamp=result.timestamp or (supplied or now),
                    top_k=5,
                    consulted=list(args.get("consulted") or []) or None,
                    chunks=snapshot.chunks("entry", "augmented") if snapshot is not None else None,
                )
            except Exception:
                payload["link_suggestions"] = {
                    "unlinked_decisions": unlinked,
                    "suggestions": [],
                    "related_entries": [],
                    "instruction": instruction,
                    "warning": "suggestion ranking was unavailable; the append result is unaffected",
                }
            else:
                payload["link_suggestions"] = {
                    "unlinked_decisions": unlinked,
                    "suggestions": _append_link_suggestion_rows(ranked),
                    "related_entries": [item.chunk.entry_id for item in ranked],
                    "instruction": instruction,
                }
        if supplied:
            drift = _clock_drift_warning(supplied, now)
            if drift:
                payload["clock_drift_warning"] = drift
        return payload

    if name == "memory_link_retract":
        # The first MCP link-WRITE tool. No merge_trigger gate: an append-only
        # correction publishes nothing and lands nothing, so the authorization
        # the integrate path needs has no counterpart here.
        from .core import apply_link_retract

        cwd = Path(str(args.get("cwd", "."))).resolve()
        # Same cwd hazard memory_session_append guards: resolve_runtime fails
        # open and the writer does mkdir(parents=True), so a wrong cwd would
        # mint a phantom .memory-seed tree rather than error - and the
        # declaration guard would then read that empty tree and refuse every
        # real edge as dangling, which reads like a corpus problem.
        runtime = resolve_runtime(cwd)
        if not runtime.memory_dir.is_dir():
            return {
                "ok": False,
                "written": False,
                "issues": [
                    f"no Memory Seed runtime at {cwd} (looked for {MEMORY_DIR_NAME}/); "
                    "pass cwd pointing at the project root - refusing rather than creating an empty one"
                ],
            }
        for field_name in ("from_entry", "kind", "ref"):
            value = args.get(field_name)
            if not isinstance(value, str) or not value.strip():
                return {"ok": False, "written": False, "issues": [f"{field_name} is required"]}
        result = apply_link_retract(
            cwd,
            from_entry=str(args["from_entry"]).strip(),
            kind=str(args["kind"]).strip(),
            ref=str(args["ref"]).strip(),
            retype=_optional_str(args, "retype"),
            note=_optional_str(args, "note"),
            date_pin=_optional_str(args, "date_pin"),
            timestamp=_optional_str(args, "timestamp") or args.get("_now"),
            dry_run=bool(args.get("dry_run", False)),
        )
        return {
            "ok": result.ok,
            "written": result.written,
            "entry_id": result.entry_id,
            "timestamp": result.timestamp,
            "path": str(result.path) if result.path else None,
            "retracted": list(result.retracted),
            "reauthored": result.reauthored,
            "reauthored_key": result.reauthored_key,
            "rendered": result.rendered,
            "issues": list(result.issues),
        }

    raise ValueError(f"Unknown tool: {name}")


def _record_retrieval_attention(name: Any, arguments: dict[str, Any], tool_result: Any) -> None:
    """Log retrieval events at the dispatch choke point (attention-retrieval-signal-proposal).

    ``memory_get_chunk`` results are fetches (they score); ``memory_search``
    results are impressions (logged, weigh zero - counting the ranker's own
    output would be a feedback loop). Fail-open: attention is telemetry and must
    never break the tool call it observed.
    """
    try:
        if name not in ("memory_get_chunk", "memory_search"):
            return
        if not isinstance(tool_result, dict):
            return
        from .attention import compact_if_needed, record_event
        from .core import resolve_runtime

        memory_dir = resolve_runtime(arguments.get("cwd") or ".").memory_dir
        if name == "memory_get_chunk":
            # The tool wraps its payload: {"chunk": {..., "entry_id": ...}}.
            chunk = tool_result.get("chunk")
            entry_id = chunk.get("entry_id") if isinstance(chunk, dict) else None
            if entry_id:
                record_event(memory_dir, "memory_get_chunk", entry_id)
        else:
            # One entry supplies several rows under decision granularity, so
            # logging every row counts a single search as N impressions. That
            # inflates the log toward compaction and would bias any future
            # impression weighting toward whichever entries hold the most
            # decisions. One impression per entry per search.
            seen: set[str] = set()
            for row in tool_result.get("results") or []:
                if isinstance(row, dict) and row.get("entry_id"):
                    if row["entry_id"] in seen:
                        continue
                    seen.add(row["entry_id"])
                    record_event(memory_dir, "memory_search", row["entry_id"])
        compact_if_needed(memory_dir)
    except Exception:
        return


def handle_jsonrpc_message(
    message: dict[str, Any],
    *,
    default_semantic_enabled: bool = True,
) -> dict[str, Any] | None:
    message_id = message.get("id")
    method = message.get("method")
    try:
        if method == "initialize":
            return _result(
                message_id,
                {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                    "capabilities": {"tools": {}},
                },
            )
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return _result(message_id, {"tools": TOOLS})
        if method == "tools/call":
            params = message.get("params") or {}
            arguments = params.get("arguments") or {}
            if params.get("name") == "memory_search" and "semantic_enabled" not in arguments:
                arguments = {**arguments, "semantic_enabled": default_semantic_enabled}
            tool_result = call_tool(params.get("name"), arguments)
            _record_retrieval_attention(params.get("name"), arguments, tool_result)
            tool_text = (
                canonical_retrieval_json(tool_result)
                if params.get("name")
                in {
                    "memory_retrieval_spec_preview",
                    "memory_retrieval_spec_resolve",
                    "memory_task_packet_preview",
                    "memory_task_packet_compile",
                }
                else json.dumps(
                    tool_result,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                )
            )
            return _result(
                message_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": tool_text,
                        }
                    ]
                },
            )
        return _error(message_id, -32601, f"Method not found: {method}")
    except Exception as exc:
        return _error(message_id, -32603, str(exc))


def serve_stdio(input_stream=None, output_stream=None, *, semantic_enabled: bool = True) -> int:
    input_stream = input_stream or sys.stdin
    output_stream = output_stream or sys.stdout
    for line in input_stream:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            response = handle_jsonrpc_message(
                message,
                default_semantic_enabled=semantic_enabled,
            )
        except Exception as exc:
            response = _error(None, -32700, str(exc))
        if response is not None:
            output_stream.write(json.dumps(response, separators=(",", ":"), ensure_ascii=False) + "\n")
            output_stream.flush()
    return 0


def _configure_utf8_stdio() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _configure_utf8_stdio()
    parser = argparse.ArgumentParser(prog="memory-seed-mcp")
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="run the Memory Seed MCP server over newline-delimited stdio JSON-RPC",
    )
    parser.add_argument(
        "--no-semantic",
        action="store_true",
        help="disable Model2Vec semantic scoring and use lexical metadata ranking only",
    )
    args = parser.parse_args(argv)
    # Advisory, never fatal - unlike the CLI, which refuses. A hard block here
    # would take the harness's MCP server down at launch, and the server's own
    # tools are how an agent would read the diagnosis. The launcher's cwd is the
    # only thing measurable at startup; per-call `cwd` arguments are not.
    provenance = package_provenance(Path("."))
    if provenance.foreign and not provenance.allowed:
        print(foreign_package_message(provenance, command="mcp"), file=sys.stderr, flush=True)
    if args.stdio:
        return serve_stdio(semantic_enabled=not args.no_semantic)
    parser.print_help()
    return 0


def _clock_drift_warning(supplied: str, now: str) -> str | None:
    """Flag an authored timestamp that is far from the server clock.

    Advisory, never fatal: explicit stamps are legitimate for sanctioned
    backfill. The threshold exists because agents estimating elapsed time
    drifted hours in practice, and the Trail renders those stamps as fact.
    """
    try:
        drift_minutes = abs(
            (datetime.strptime(supplied, "%Y-%m-%d %H:%M") - datetime.strptime(now, "%Y-%m-%d %H:%M")).total_seconds()
        ) / 60
    except ValueError:
        return f"timestamp {supplied!r} does not parse as 'YYYY-MM-DD HH:MM'; server clock reads {now}."
    if drift_minutes > 10:
        return (
            f"supplied timestamp is {drift_minutes:.0f} minutes from the server clock ({now}); "
            "session entries must carry real wall-clock times - omit timestamp to let the server stamp."
        )
    return None


def _required_str(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing required string argument: {key}")
    return value


# Exact aliases of fields that stay: `path` == `source`, `date` == `session_date`, `source_file`
# is the basename of `source`, `entry_title` == `heading_path[0]`. Plus `lexical_terms`, which
# earns its BM25F weight for SCORING but, serialised, restates strings already present in `text` -
# an index the reading agent cannot query. `chunk_to_dict` keeps all of them: Trace hard-indexes
# `payload["entry_title"]`, `payload["source_file"]`, `payload["contexts"]`,
# `payload["lexical_terms"]` and `payload["path"]`, so this projection exists at the MCP boundary
# precisely so the internal record does not have to change.
_CHUNK_PROJECTION_DROP = frozenset(
    {"path", "date", "source_file", "entry_title", "lexical_terms"}
)

# Empty here is a CLAIM, not an absence, and must survive the empty-field omission below. Empty
# lifecycle fields say "this decision stands unsuperseded"; fetch_count 0 says "never fetched".
# Omitting them would make those statements indistinguishable from "the server did not say" -
# exactly the ambiguity a memory system exists to avoid.
_CHUNK_PROJECTION_KEEP_EMPTY = frozenset(
    {
        "replaces",
        "replaced_by",
        "replacing_head",
        "evolves",
        "evolved_by",
        "attention_score",
        "fetch_count",
        "last_fetch",
        "entry_context",
        "text",
        # Search results only: a null `semantic_score` says the semantic pass did not run - the
        # other half of the sentence `semantic_fallback_reason` starts. Dropping it as "empty"
        # would hide the fallback rather than report it.
        "semantic_score",
    }
)


def _project_chunk_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """The agent-facing view of a chunk: full record minus aliases and silent empties."""
    projected: dict[str, Any] = {}
    for key, value in payload.items():
        if key in _CHUNK_PROJECTION_DROP:
            continue
        if key not in _CHUNK_PROJECTION_KEEP_EMPTY and value in ([], None, "", {}):
            continue
        projected[key] = value
    return projected


def _project_search_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """The agent-facing view of a search result set: same alias pruning `memory_get_chunk` uses.

    `_project_chunk_payload` has dropped `path`/`date`/`source_file`/`entry_title` from single
    chunks since it was written - they are aliases of `source`/`session_date`/`heading_path[0]` in
    the same object - but `memory_search` shipped all ~43 keys per result unprojected, so the two
    agent-facing surfaces disagreed about what an alias was. This applies the same rule to each
    result, at the MCP boundary rather than inside `search_memory`, so the library's return shape
    stays stable for the experiments and tests that read it directly.

    Deliberately NOT dropped: the scoring internals (`lexical_score`, `semantic_score`,
    `recency_multiplier`, `match_score`). An agent cannot act on them, but they are the only
    debuggability MCP output has, and removing them is a separate call.
    """
    projected = dict(payload)
    results = payload.get("results")
    if isinstance(results, list):
        projected["results"] = [
            _project_chunk_payload(item) if isinstance(item, dict) else item for item in results
        ]
    return projected


def _optional_str(arguments: dict[str, Any], key: str) -> str | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid string argument: {key}")
    return value.strip()


def _optional_date(arguments: dict[str, Any], key: str) -> date | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid date argument: {key}")
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(f"Invalid {key}; expected YYYY-MM-DD") from exc


def _positive_int(arguments: dict[str, Any], key: str, *, default: int) -> int:
    value = arguments.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"Invalid {key}; expected an integer >= 1")
    return value


def _optional_bool(arguments: dict[str, Any], key: str, *, default: bool) -> bool:
    value = arguments.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"Invalid {key}; expected a boolean")
    return value


def _cwd(arguments: dict[str, Any]) -> str:
    value = arguments.get("cwd", ".")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Invalid string argument: cwd")
    return value


def _reject_unsupported_arguments(arguments: dict[str, Any], allowed: set[str]) -> None:
    unsupported = sorted(set(arguments) - allowed)
    if unsupported:
        raise ValueError("Unsupported argument(s): " + ", ".join(unsupported))


def _topic_record_to_dict(record: Any) -> dict[str, Any]:
    return {
        "slug": record.slug,
        "label": record.label,
        "description": record.description,
        "status": record.status,
        "aliases": list(record.aliases),
    }


def _result(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


if __name__ == "__main__":
    raise SystemExit(main())
