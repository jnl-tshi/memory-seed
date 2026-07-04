from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from .semantic_cache import (
    EmbeddingProvider,
    MemoryChunk,
    Model2VecEmbeddingProvider,
    RankedMemoryChunk,
    build_related_entry_graph,
    extract_memory_chunks,
    rank_session_memory,
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
            },
            "required": ["query"],
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
        cwd = args.get("cwd", ".")
        top_k = int(args.get("top_k", 8))
        semantic_requested = bool(args.get("semantic_enabled", True))
        embedding_provider, semantic_provider, fallback_reason = _semantic_provider(
            query,
            args.get("_embedding_provider"),
            enabled=semantic_requested,
        )
        ranked = rank_session_memory(
            query,
            cwd,
            top_k=top_k,
            today=today or date.today(),
            lambda_days=float(args.get("lambda_days", 0.01)),
            recency_enabled=bool(args.get("recency_enabled", True)),
            recency_floor=float(args.get("recency_floor", 0.15)),
            embedding_provider=embedding_provider,
            granularity=str(args.get("granularity", "entry")),
            user=_optional_str(args, "user"),
            date_from=_optional_date(args, "date_from"),
            date_to=_optional_date(args, "date_to"),
            exclude_superseded=bool(args.get("exclude_superseded", False)),
        )
        return format_search_results(
            query,
            ranked,
            top_k=top_k,
            semantic_enabled=embedding_provider is not None,
            semantic_provider=semantic_provider,
            semantic_fallback_reason=fallback_reason,
        )

    if name == "memory_get_chunk":
        chunk_id = _required_str(args, "chunk_id")
        cwd = args.get("cwd", ".")
        entry_chunks = extract_memory_chunks(cwd, granularity="entry")
        found = next((chunk for chunk in entry_chunks if chunk.chunk_id == chunk_id), None)
        if found is None:
            found = next(
                (chunk for chunk in extract_memory_chunks(cwd, granularity="section") if chunk.chunk_id == chunk_id),
                None,
            )
        if found is None:
            raise ValueError(f"chunk_id not found: {chunk_id}")
        payload = _chunk_to_dict(found)
        superseded_by: list[str] = []
        inbound_relation_count = 0
        importance_score = 0.0
        if found.entry_id:
            node = build_related_entry_graph(chunks=entry_chunks).get(found.entry_id)
            if node is not None:
                superseded_by = list(node.superseded_by)
                # How many other entries reference this one via related_entries
                # (inbound backlinks only) - the raw signal importance_score is
                # built on. Distinct from Lense's `connectivity`, which counts
                # combined inbound+outbound edges for node sizing.
                inbound_relation_count = len(node.inbound)
                # inbound_relation_count dampened when this entry is superseded
                # (read-only; not blended into default search ranking).
                importance_score = node.importance_score
        payload["superseded_by"] = superseded_by
        payload["inbound_relation_count"] = inbound_relation_count
        payload["importance_score"] = importance_score
        return {"chunk": payload}

    raise ValueError(f"Unknown tool: {name}")


def format_search_results(
    query: str,
    ranked: list[RankedMemoryChunk],
    *,
    top_k: int = 8,
    semantic_enabled: bool | None = None,
    semantic_provider: str | None = None,
    semantic_fallback_reason: str | None = None,
) -> dict[str, Any]:
    results = [_ranked_to_dict(result) for result in ranked[:top_k]]
    effective_semantic_enabled = (
        any(result["semantic_score"] is not None for result in results)
        if semantic_enabled is None
        else semantic_enabled
    )
    return {
        "query": query,
        "semantic_enabled": effective_semantic_enabled,
        "semantic_provider": semantic_provider if effective_semantic_enabled else semantic_provider,
        "semantic_fallback_reason": semantic_fallback_reason,
        "results": results,
        "human_report": _human_report(query, results),
    }


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
                            "text": json.dumps(tool_result, indent=2, sort_keys=True),
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
            output_stream.write(json.dumps(response, separators=(",", ":")) + "\n")
            output_stream.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
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


def _ranked_to_dict(result: RankedMemoryChunk) -> dict[str, Any]:
    chunk = result.chunk
    return {
        "chunk_id": chunk.chunk_id,
        "score": round(result.final_score, 6),
        "match_score": round(result.match_score, 6),
        "lexical_score": round(result.lexical_score, 6),
        "semantic_score": None
        if result.semantic_score is None
        else round(result.semantic_score, 6),
        "recency_multiplier": round(result.recency_multiplier, 6),
        "age_days": result.age_days,
        "date": chunk.session_date.isoformat(),
        "session_date": chunk.session_date.isoformat(),
        "entry_datetime": None
        if chunk.entry_datetime is None
        else chunk.entry_datetime.isoformat(),
        "source": chunk.source_path,
        "path": chunk.source_path,
        "user": chunk.user,
        "file_hash_id": chunk.file_hash_id,
        "related_entries": list(chunk.related_entries),
        "supersedes": list(chunk.supersedes),
        "line_range": [chunk.start_line, chunk.end_line],
        "heading_path": list(chunk.heading_path),
        "matched_terms": list(result.matched_terms),
        "matched_fields": list(result.matched_fields),
        "excerpt": _excerpt(chunk.text),
        "entry_id": chunk.entry_id,
        "user_initials": chunk.user_initials,
        "agent_type": chunk.agent_type,
        "agent_name": chunk.agent_name,
        "project_path": chunk.project_path,
        "subproject_path": chunk.subproject_path,
        "entry_title": chunk.entry_title,
        "entry_line_range": None if chunk.entry_line_range is None else list(chunk.entry_line_range),
        "sections": list(chunk.sections),
        "granularity": chunk.granularity,
    }


def _chunk_to_dict(chunk: MemoryChunk) -> dict[str, Any]:
    return {
        "chunk_id": chunk.chunk_id,
        "source": chunk.source_path,
        "path": chunk.source_path,
        "source_file": chunk.source_file,
        "date": chunk.session_date.isoformat(),
        "session_date": chunk.session_date.isoformat(),
        "user": chunk.user,
        "file_hash_id": chunk.file_hash_id,
        "related_entries": list(chunk.related_entries),
        "supersedes": list(chunk.supersedes),
        "entry_datetime": None
        if chunk.entry_datetime is None
        else chunk.entry_datetime.isoformat(),
        "line_range": [chunk.start_line, chunk.end_line],
        "heading_path": list(chunk.heading_path),
        "heading_level": chunk.heading_level,
        "title": chunk.title,
        "text": chunk.text,
        "tags": list(chunk.tags),
        "contexts": list(chunk.contexts),
        "lexical_terms": list(chunk.lexical_terms),
        "entry_id": chunk.entry_id,
        "user_initials": chunk.user_initials,
        "agent_type": chunk.agent_type,
        "agent_name": chunk.agent_name,
        "project_path": chunk.project_path,
        "subproject_path": chunk.subproject_path,
        "entry_title": chunk.entry_title,
        "entry_line_range": None if chunk.entry_line_range is None else list(chunk.entry_line_range),
        "sections": list(chunk.sections),
        "granularity": chunk.granularity,
    }


def _human_report(query: str, results: list[dict[str, Any]]) -> str:
    lines = [f"Query: {query}", "Top results:"]
    for index, result in enumerate(results, start=1):
        heading = " > ".join(result["heading_path"]) or "(untitled)"
        lines.append(
            f"{index}. {result['date']} {heading} "
            f"[score={result['score']}, source={result['source']}:{result['line_range'][0]}]"
        )
    if not results:
        lines.append("No matching memory chunks found.")
    return "\n".join(lines)


def _excerpt(text: str, limit: int = 280) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _semantic_provider(
    query: str,
    override: Any,
    *,
    enabled: bool,
) -> tuple[EmbeddingProvider | None, str | None, str | None]:
    if not enabled:
        return None, None, None
    provider = override or Model2VecEmbeddingProvider()
    provider_name = getattr(provider, "name", f"model2vec:{Model2VecEmbeddingProvider.default_model_name}")
    try:
        provider.embed([query])
    except Exception as exc:
        return None, provider_name, str(exc)
    return provider, provider_name, None


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


def _result(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


if __name__ == "__main__":
    raise SystemExit(main())
