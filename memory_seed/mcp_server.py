from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from .core import (
    branch_status,
    commit_reference_ids,
    generate_session_entry_id,
    resolve_runtime,
    session_fuse,
    session_target,
    worktree_guard,
)
# The MCP server is a thin JSON-RPC wrapper over the public retrieval service
# (memory_seed/retrieval.py) - the same service the in-package Lense and the
# future companion UI distribution consume, so every surface returns the same
# answers. `format_search_results` is re-exported here for compatibility.
from .retrieval import (
    augment_chunks_with_link_sidecars,
    chunk_to_dict,
    format_search_results,
    get_chunk,
    ranked_to_dict,
    search_memory,
)
from .semantic_cache import (
    build_related_entry_graph,
    extract_memory_chunks,
    suggest_related_entries,
)


SERVER_NAME = "memory-seed"
SERVER_VERSION = "0.1.0"


TOOLS: list[dict[str, Any]] = [
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
                    "enum": ["entry", "section"],
                    "default": "entry",
                    "description": "Return coherent ## entries by default, or narrower ###+ sections when requested.",
                },
                "exclude_superseded": {
                    "type": "boolean",
                    "default": False,
                    "description": "Opt-in: drop entries that a later decision has superseded (non-empty superseded_by). Off by default - superseded entries stay retrievable.",
                },
                "supersession_damping": {
                    "type": "boolean",
                    "default": True,
                    "description": "On by default: down-rank (not drop) entries a later decision superseded, so a live replacement out-ranks the decision it retires. Draws superseded_by from the sidecar-augmented graph. Superseded entries stay fully retrievable (down-rank only, never hidden); pass false to rank them at full weight.",
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
        "description": "Fetch an exact Memory Seed chunk by chunk_id.",
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
        "name": "memory_session_target",
        "description": "Resolve the active session-log target path (where a new entry should be appended) for the nearest runtime. Read-only; never creates the file. The agent appends the entry itself.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "."},
                "date": {
                    "type": "string",
                    "description": "Target session date in YYYY-MM-DD format. Defaults to today (system clock).",
                },
                "user": {
                    "type": "string",
                    "description": "Override the active user slug when resolving a per-user target.",
                },
            },
        },
    },
    {
        "name": "memory_entry_id",
        "description": "Compute the canonical entry_id for a new session entry from its metadata (deterministic sha256, no randomness). Closes the authoring loop: call this instead of inventing an id - hand-rolled ids drift outside the canonical Crockford alphabet and are not reproducible. Read-only; the agent writes the id into its own new entry.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "timestamp": {
                    "type": "string",
                    "description": "Entry heading timestamp, e.g. '2026-07-12 14:45'.",
                },
                "title": {
                    "type": "string",
                    "description": "Entry title (the text after 'YYYY-MM-DD HH:MM - ').",
                },
                "user_initials": {"type": "string", "description": "user_initials field, e.g. JNL."},
                "agent_type": {"type": "string", "description": "agent_type field, e.g. claude."},
                "project_path": {"type": "string", "default": "."},
                "subproject_path": {
                    "type": "string",
                    "description": "subproject_path field; omit for null.",
                },
            },
            "required": ["timestamp", "title", "user_initials", "agent_type"],
        },
    },
]


def call_tool(
    name: str,
    arguments: dict[str, Any] | None = None,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    args = arguments or {}
    if name == "memory_search":
        query = _required_str(args, "query")
        return search_memory(
            query,
            args.get("cwd", "."),
            top_k=int(args.get("top_k", 8)),
            today=today,
            lambda_days=float(args.get("lambda_days", 0.01)),
            recency_enabled=bool(args.get("recency_enabled", True)),
            recency_floor=float(args.get("recency_floor", 0.15)),
            semantic_enabled=bool(args.get("semantic_enabled", True)),
            embedding_provider=args.get("_embedding_provider"),
            granularity=str(args.get("granularity", "entry")),
            user=_optional_str(args, "user"),
            date_from=_optional_date(args, "date_from"),
            date_to=_optional_date(args, "date_to"),
            exclude_superseded=bool(args.get("exclude_superseded", False)),
            supersession_damping=bool(args.get("supersession_damping", True)),
            topics=list(args.get("topics") or []) or None,
        )

    if name == "memory_link_suggest":
        entry_id = _optional_str(args, "entry_id")
        target, ranked = suggest_related_entries(
            cwd=args.get("cwd", "."),
            entry_id=entry_id,
            top_k=int(args.get("top_k", 5)),
        )
        return {
            "target": {
                "entry_id": target.entry_id,
                "title": target.title,
                "session_date": target.session_date.isoformat(),
                "source": target.source_path,
            },
            "suggestions": [
                {
                    **ranked_to_dict(item.result),
                    # D5 evidence: alias-canonicalized F: paths shared with the
                    # target, and the rarity-weighted boost they contributed -
                    # shown so the evolves/supersedes/related call is concrete.
                    "shared_files": list(item.shared_files),
                    "file_overlap_bonus": round(item.file_overlap_bonus, 6),
                    "adjusted_score": round(item.adjusted_score, 6),
                }
                for item in ranked
            ],
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
            "supersedes": list(node.supersedes),
            "superseded_by": list(node.superseded_by),
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
            "removed_sources": result.removed_sources,
            "already_present": result.already_present,
            "issues": result.issues,
            "write_surface": "CLI-only; run apply during an in-progress git merge.",
            "merge_checkpoint_command": f"git merge --no-ff --no-commit {branch}",
            "apply_command": f"memory-seed session fuse --branch {branch} --base {base.strip()} --apply",
        }

    if name == "memory_get_chunk":
        chunk_id = _required_str(args, "chunk_id")
        return {"chunk": get_chunk(chunk_id, args.get("cwd", "."))}

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
            for chunk in extract_memory_chunks(cwd, granularity="entry"):
                if any(resolution.get(topic, topic) == canonical for topic in chunk.topics):
                    entries.append(
                        {
                            "entry_id": chunk.entry_id,
                            "title": chunk.title,
                            "session_date": chunk.session_date.isoformat(),
                            "source": chunk.source_path,
                            "topics": list(chunk.topics),
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

    if name == "memory_session_target":
        root = Path(args.get("cwd", ".")).resolve()
        target = session_target(
            cwd=root,
            date_str=_optional_str(args, "date"),
            explicit_user=_optional_str(args, "user"),
            create=False,
        )
        try:
            rel_path = target.path.relative_to(root).as_posix()
        except ValueError:
            rel_path = target.path.as_posix()
        return {
            "path": rel_path,
            "absolute_path": target.path.as_posix(),
            "session_date": target.session_date,
            "user": target.user,
            "layout": target.layout,
            "exists": target.path.exists(),
            "write_surface": "Agent appends the entry directly; MCP never writes session files.",
        }

    if name == "memory_entry_id":
        entry_id = generate_session_entry_id(
            timestamp=_required_str(args, "timestamp"),
            title=_required_str(args, "title"),
            user_initials=_required_str(args, "user_initials"),
            agent_type=_required_str(args, "agent_type"),
            project_path=str(args.get("project_path", ".")),
            subproject_path=_optional_str(args, "subproject_path"),
        )
        return {
            "entry_id": entry_id,
            "write_surface": "Agent writes this id into its own new entry; MCP never writes session files.",
        }

    raise ValueError(f"Unknown tool: {name}")


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
            return _result(
                message_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(tool_result, indent=2, sort_keys=True, ensure_ascii=False),
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
    if args.stdio:
        return serve_stdio(semantic_enabled=not args.no_semantic)
    parser.print_help()
    return 0


def _required_str(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing required string argument: {key}")
    return value


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
