"""Render a compiled Task Packet as a client-neutral spawn prompt.

Every client spawns agents with text, so a packet only seeds a worker once it
becomes the worker's opening prompt.  ``render_task_packet`` turns the
canonical packet into that prompt: orientation first, then the task, scope,
acceptance, the packet's own evidence and governance pins, and the packet
file's path and fingerprint so the worker can verify it and load governance
(task-packet-handoff-integration-plan.md, T3).  Rendering is deterministic and
reads the packet only; it never compiles, dispatches, or modifies it.
"""

from __future__ import annotations

import html
from collections.abc import Mapping, Sequence
from typing import Any

from .task_packet import GOVERNANCE_LOAD_CLI, GOVERNANCE_LOAD_MCP_TOOL, canonical_task_packet_json

RENDER_SCHEMA = "memory-seed/task-packet-render"
RENDER_VERSION = 1
_LITE_PATH = ".memory-seed/skills/subagent_orientation.md"


def _attr(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _quoted(tag: str, attributes: Mapping[str, Any], content: str) -> list[str]:
    """Quote verbatim content in a tag it cannot close early.

    A literal closing tag inside the content is written as ``<\\/tag>`` so a
    source can never break out of its quote; everything else stays verbatim.
    """
    attrs = "".join(f' {key}="{_attr(value)}"' for key, value in attributes.items())
    body = str(content).rstrip("\n").replace(f"</{tag}>", f"<\\/{tag}>")
    return [f"<{tag}{attrs}>", body, f"</{tag}>"]


def _bullets(items: Sequence[Any], empty: str = "none") -> list[str]:
    values = [str(item) for item in items]
    return [f"- {value}" for value in values] if values else [f"- {empty}"]


def render_task_packet(packet: Mapping[str, Any], packet_path: str, *, handoff: str | None = None) -> str:
    """Return the spawn prompt for one canonical packet saved at ``packet_path``."""
    canonical_task_packet_json(packet)  # identity + fingerprint, or refuse
    dispatch = packet["dispatch"]
    execution = dispatch["execution"]
    binding = packet["runtime_binding"]
    context = dispatch["project_context"]
    lines: list[str] = [f"# Task: {dispatch['objective']}", ""]

    orientation = packet.get("worker_orientation")
    if isinstance(orientation, Mapping):
        lines += [
            "You are a delegated worker. Your orientation skill is embedded below; follow it before anything",
            f"else. It is the file `{orientation['source']}` ({orientation['content_digest']}).",
            "",
            *_quoted("orientation", {"source": orientation["source"]}, orientation["content"]),
        ]
    else:
        # v1 packets carry the full rules instead of the lite skill: render
        # them, so the prompt holds what it claims to hold.
        lines += [
            "You are a delegated worker. This v1 packet embeds the full worker rules below; follow them before",
            "anything else.",
        ]
        for name, source in sorted(((packet.get("worker_baseline") or {}).get("sources") or {}).items()):
            if isinstance(source, Mapping):
                lines += ["", *_quoted("governance", {"name": name, "source": source["source"]}, source["content"])]
    lines += [
        "",
        "## Packet",
        "",
        f"- File: `{packet_path}`",
        f"- Fingerprint: `{packet['fingerprint']}`",
        f"- Version: {packet['packet_version']}",
        f"- Handoff: {handoff or 'unspecified'}",
        f"- Write intent: {execution['write_intent']}",
        f"- Directory: `{binding['worktree'] or binding['expected_directory']}`",
        (
            f"- Branch: `{binding['working_branch']}` (base `{binding['base_branch']}` at `{binding['base_sha']}`)"
            if execution["write_intent"] == "writing"
            else f"- Read-only: do not edit or commit (base `{binding['base_branch']}` at `{binding['base_sha']}`)"
        ),
        "",
        "## Scope",
        "",
        "Allowed files:",
        *_bullets(execution["allowed_files"]),
        "",
        "Forbidden files:",
        *_bullets(execution["forbidden_files"]),
        "",
        "Files you are expected to create:",
        *_bullets(execution["expected_absent"]),
        "",
        "Decisions this task implements:",
        *_bullets(execution["implements"]),
        "",
        "## Context",
        "",
        f"- Project: {context['project_type_and_purpose']}",
        f"- Subsystem: {context['relevant_subsystem']}",
        f"- Why this task fits: {context['task_fit']}",
        f"- Who uses the result: {context['downstream_use']}",
        "",
        "Non-goals:",
        *_bullets(context["non_goals"]),
        "",
        "## Acceptance",
        "",
        "Validation:",
        *_bullets(execution["validation"]),
        "",
        "Observables (each must exit with the stated code):",
        *_bullets([
            f"`{item['command']}` -> exit {item['expected_exit_code']} ({item['name']})"
            for item in execution["acceptance_observables"]
        ]),
        "",
        "Output contract:",
        *_bullets(execution["output_contract"]),
        "",
        *_execution_section(packet["execution_defaults"]),
        "## Evidence",
        "",
        "Supplied evidence is authoritative for this task; do not refetch it. Each item is quoted verbatim",
        "inside its own tag: headings inside a tag belong to the source, not to this prompt.",
    ]
    for item in packet["materialized_evidence"]:
        start, end = item["line_range"]
        lines += [
            "",
            *_quoted("evidence", {"id": item["id"], "kind": item["kind"], "source": item["source"],
                                  "lines": f"{start}-{end}"}, item["content"]),
        ]
    projection = packet["constitution_projection"]
    lines += ["", "## Constitution", ""]
    if projection["mode"] == "anchored_clauses":
        for clause in projection["clauses"]:
            lines += [*_quoted("clause", {"ref": clause["ref"], "heading": clause["heading"].lstrip("# ")},
                               clause["content"]), ""]
    else:
        lines += [*_quoted("constitution", {"mode": "full-document"}, projection["full_document"]["content"]), ""]

    references = packet.get("governance_references")
    if isinstance(references, Mapping):
        lines += [
            "## Governance loaded on demand",
            "",
            f"Load a pinned file only when an orientation trigger fires, with the `{GOVERNANCE_LOAD_MCP_TOOL}` MCP",
            f"tool or `{GOVERNANCE_LOAD_CLI}`. Both refuse bytes that changed since compile.",
            "",
            *_bullets([
                f"{name}: `{reference['source']}` ({reference['token_estimate']} tokens, {reference['content_digest']})"
                for name, reference in sorted(references.items())
            ]),
            "",
        ]
    handoff_fields = list(packet["execution_defaults"].get("handoff") or [])
    lines += [
        "## Return",
        "",
        "End with the return contract from your orientation skill, extended to report every field below. Where",
        "the two differ, this list wins:",
        *_bullets(handoff_fields),
    ]
    return "\n".join(lines) + "\n"


def _execution_section(defaults: Mapping[str, Any]) -> list[str]:
    """The packet's own execution rules: preflight, escalation, session writes."""
    session = defaults.get("session_logging") or {}
    delegated = bool(session.get("delegated"))
    lines = [
        "## Execution",
        "",
        "Run this preflight before any other action and stop with `BLOCKED` if it disagrees with this packet:",
        *_bullets([f"`{command}`" for command in defaults.get("preflight") or []]),
        "",
        "Escalate to the orchestrator instead of proceeding on:",
        *_bullets(defaults.get("conflict_escalation") or []),
        "",
        f"Session writes: {'delegated' if delegated else 'not delegated; do not write session entries'}.",
    ]
    if delegated:
        lines += _bullets([
            session.get("append_requirement", ""),
            session.get("clock_ownership", ""),
            *(session.get("prohibitions") or []),
        ])
    return [*lines, ""]


def render_payload(packet: Mapping[str, Any], packet_path: str, *, handoff: str | None = None) -> dict[str, Any]:
    """The prompt plus its identity, as returned by the CLI and MCP surfaces."""
    return {
        "schema": RENDER_SCHEMA,
        "version": RENDER_VERSION,
        "packet_path": packet_path,
        "packet_fingerprint": packet["fingerprint"],
        "handoff": handoff,
        "prompt": render_task_packet(packet, packet_path, handoff=handoff),
    }
