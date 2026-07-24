from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .core import (
    MEMORY_DIR_NAME,
    _git_text,
    branch_status,
    commit_reference_ids,
    resolve_runtime,
    session_fuse,
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
    replacing_lineage_heads,
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
        "name": "memory_session_append",
        "description": (
            "Append a session entry with every structural guarantee enforced. THIS IS THE ONLY WAY TO AUTHOR AN ENTRY - "
            "do not hand-write session files. The tool owns structure (target path, heading timestamp from the server "
            "clock, canonical entry_id, YAML shape, chronological ordering) and refuses malformed or out-of-order writes; "
            "you own voice (title, topics, lifecycle classification, and the D/R/A/F/T body prose, all taken verbatim). "
            "Guards run together and nothing is written when any fails: chronology, ref existence (fabricated ids are "
            "refused), forward-only lifecycle edges, controlled topic vocabulary, id collision, and DRAFT body format. "
            "Refusals come back as ok=false with an issues list, each independently fixable. Pair with "
            "memory_link_suggest / memory_link_show to choose related_entries, replaces and evolves before calling. "
            "Set dry_run to run every guard and get the id, timestamp, target path and the rendered entry back without writing - inspect the final output, then commit by calling again WITH the returned timestamp, so a minute tick between preview and write cannot change the id."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "."},
                "title": {"type": "string", "description": "Entry title (the text after 'YYYY-MM-DD HH:MM - ')."},
                "body": {
                    "type": "string",
                    "description": "The entry body, verbatim. DRAFT shape: '### Decision' (or '### Decisions' with '#### Dn - name' subsections) then '- D:' and a mandatory '- R:', optionally '- A:', '- F:', '- T:'.",
                },
                "user_initials": {"type": "string", "description": "user_initials field, e.g. JNL."},
                "agent_type": {"type": "string", "description": "agent_type field, e.g. claude."},
                "agent_name": {"type": "string", "description": "Active .agents/ persona slug; omit for null."},
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Controlled-vocabulary slugs or aliases; aliases are stored canonically. Unknown slugs are refused.",
                },
                "related_entries": {"type": "array", "items": {"type": "string"}, "description": "entry_id values this entry relates to. Must already exist and predate it."},
                "replaces": {"type": "array", "items": {"type": "string"}, "description": "entry_id values this entry retires (the old decision is now wrong or dead)."},
                "evolves": {"type": "array", "items": {"type": "string"}, "description": "entry_id values this entry refines (the old decision stays valid but incomplete)."},
                "project_path": {"type": "string", "default": "."},
                "subproject_path": {"type": "string", "description": "subproject_path field; omit for null."},
                "branch": {"type": "string", "description": "branch field; omit to auto-capture from git."},
                "auto_branch": {"type": "boolean", "default": True, "description": "Set false to omit the branch field entirely."},
                "timestamp": {
                    "type": "string",
                    "description": "Heading timestamp 'YYYY-MM-DD HH:MM'. OMIT in normal use: the server stamps from its own clock. Two sanctioned explicit uses: echoing a dry_run's returned timestamp back on the real write (the id is a hash of the timestamp, so a fresh stamp that ticks to the next minute mints a DIFFERENT id than previewed - echoing pins preview and write to the same bytes), and backfill. Values far from the server clock earn a drift warning.",
                },
                "user": {"type": "string", "description": "Override the active user slug when resolving a per-user target."},
                "dry_run": {"type": "boolean", "default": False, "description": "Run every guard and report entry_id, timestamp, path and `rendered` - the exact entry block a real call would append - without writing."},
            },
            "required": ["title", "body", "user_initials", "agent_type"],
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
            "pull request. Set dry_run to see the plan without merging."
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
            exclude_replaced=bool(
                args.get("exclude_replaced", args.get("exclude_superseded", False))
            ),  # legacy param spelling accepted (renamed 2026-07-24)
            supersession_damping=bool(args.get("supersession_damping", True)),
            replacing_successor_boost=bool(args.get("replacing_successor_boost", True)),
            topics=list(args.get("topics") or []) or None,
        )

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
            "suggestions": [
                {
                    **ranked_to_dict(item.result),
                    # D5 evidence: alias-canonicalized F: paths shared with the
                    # target, and the rarity-weighted boost they contributed -
                    # shown so the evolves/replaces/related call is concrete.
                    "shared_files": list(item.shared_files),
                    "file_overlap_bonus": round(item.file_overlap_bonus, 6),
                    "adjusted_score": round(item.adjusted_score, 6),
                    # Provenance: True when this candidate was in the caller's
                    # `consulted` set (memory axis) vs surfaced by file overlap
                    # alone (structural axis). Consulted candidates sort first.
                    "consulted": item.consulted,
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

    if name == "memory_session_integrate":
        from .core import read_integration_mode, session_merge_branch

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

        result = session_merge_branch(root, branch=branch, dry_run=dry_run)

        # session_merge_branch deliberately parks a non-session conflict for a
        # human to resolve. An autonomous caller cannot resolve one and must not
        # walk away from a half-merged tree, so abort back to a clean state and
        # report - the branch is untouched and the operator can retry by hand.
        aborted = False
        if result.merge_in_progress:
            abort_code, abort_out = _git_text(root, ("merge", "--abort"))
            aborted = abort_code == 0
            if not aborted:
                result.issues.append(f"merge left in progress and could not be aborted: {abort_out or '(no output)'}")

        return {
            "ok": result.committed or (dry_run and not result.issues),
            "committed": result.committed,
            "integration_mode": mode,
            "dry_run": dry_run,
            "planned_entries": result.planned_entries,
            "planned_sidecars": result.planned_sidecars,
            "planned_link_sidecars": result.planned_link_sidecars,
            "removed_sources": result.removed_sources,
            "already_present": result.already_present,
            "stamped_entries": result.stamped_entries,
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

        result = session_append_entry(
            cwd,
            title=_required_str(args, "title"),
            body=body,
            user_initials=_required_str(args, "user_initials"),
            agent_type=_required_str(args, "agent_type"),
            agent_name=_optional_str(args, "agent_name"),
            topics=list(args.get("topics") or []),
            related_entries=list(args.get("related_entries") or []),
            replaces=list(args.get("replaces") or args.get("supersedes") or []),  # legacy key accepted
            evolves=list(args.get("evolves") or []),
            project_path=str(args.get("project_path", ".")),
            subproject_path=_optional_str(args, "subproject_path"),
            branch=_optional_str(args, "branch"),
            auto_branch=bool(args.get("auto_branch", True)),
            timestamp=supplied or now,
            explicit_user=_optional_str(args, "user"),
            dry_run=bool(args.get("dry_run", False)),
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
        }
        # Only a dry run carries the rendered block: pre-commit inspection is
        # its purpose, while echoing the body back after a real write would
        # bloat every payload with text the caller already has.
        if result.rendered is not None:
            payload["rendered"] = result.rendered
        if supplied:
            drift = _clock_drift_warning(supplied, now)
            if drift:
                payload["clock_drift_warning"] = drift
        return payload

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
