from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import tempfile
import threading
import time
import uuid
import webbrowser
import gc
from dataclasses import asdict
from datetime import date, datetime, time as datetime_time, timedelta
from importlib import resources
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

# Memory Trace consumes the core control plane's public API only - it never
# reimplements parsing, ranking, the graph-edge contract, or diagram-sidecar
# reading. These are the frozen surfaces the distribution split depends on.
from memory_seed.core import iter_session_documents, resolve_runtime
from memory_seed.retrieval import EntryRollup, entry_diagram_sidecars, rollup_entry_matches
from memory_seed.semantic_cache import (
    MemoryChunk,
    RankedMemoryChunk,
    build_related_entry_graph,
    extract_memory_chunks,
    rank_memory_chunks,
)


ZOOMS = {"day": 24, "12h": 12, "6h": 6, "3h": 3}


def missing_optional_dependency_hint() -> str:
    return 'Install with: pip install memory-trace'


def default_cache_path(cwd: str | Path = ".", *, cache_root: str | Path | None = None) -> Path:
    runtime = resolve_runtime(cwd)
    digest = hashlib.sha256(str(runtime.workspace_root).encode("utf-8")).hexdigest()[:16]
    if cache_root is not None:
        root = Path(cache_root)
    elif os.environ.get("MEMORY_SEED_CACHE_DIR"):
        root = Path(os.environ["MEMORY_SEED_CACHE_DIR"])
    elif os.environ.get("MEMORY_SEED_LENSE_CACHE_ROOT"):
        root = Path(os.environ["MEMORY_SEED_LENSE_CACHE_ROOT"])
    elif os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        root = Path(os.environ["LOCALAPPDATA"]) / "memory-seed" / "lense"
    else:
        root = Path.home() / ".cache" / "memory-seed" / "lense"
    return root / f"{digest}.sqlite3"


class LenseCache:
    def __init__(
        self,
        cwd: str | Path = ".",
        *,
        db_path: str | Path | None = None,
        cache_root: str | Path | None = None,
    ):
        self.cwd = Path(cwd).resolve()
        self.runtime = resolve_runtime(self.cwd)
        self.db_path = Path(db_path) if db_path is not None else default_cache_path(self.cwd, cache_root=cache_root)
        # Serializes rebuilds within this process. The UI fires several API
        # calls concurrently on first load; without this, two threads raced the
        # same pid-named tmp file ("table meta already exists", then Windows
        # PermissionError on replace/unlink).
        self._rebuild_lock = threading.Lock()

    def rebuild(self) -> None:
        with self._rebuild_lock:
            self._rebuild_locked()

    def _rebuild_locked(self) -> None:
        self._ensure_cache_parent()
        # Unique per attempt (not just per pid): concurrent threads share a pid,
        # and a crashed run's stale tmp must never be another rebuild's target.
        tmp = self.db_path.with_name(f"{self.db_path.name}.{uuid.uuid4().hex}.tmp")
        conn = sqlite3.connect(tmp)
        try:
            self._create_schema(conn)
            docs = list(iter_session_documents(self.runtime.memory_dir / "sessions"))
            file_rows = [_file_row(self.runtime.workspace_root, doc.path) for doc in docs]
            chunks = [
                *extract_memory_chunks(self.cwd, granularity="entry"),
            ]
            entry_ranges = {(chunk.chunk_id, chunk.start_line, chunk.end_line) for chunk in chunks}
            chunks.extend(
                chunk
                for chunk in extract_memory_chunks(self.cwd, granularity="section")
                if (chunk.chunk_id, chunk.start_line, chunk.end_line) not in entry_ranges
            )
            conn.executemany(
                "insert into files(path, mtime_ns, size) values(?, ?, ?)",
                file_rows,
            )
            conn.executemany(
                "insert into chunks(chunk_id, granularity, entry_id, session_date, entry_datetime, json) values(?, ?, ?, ?, ?, ?)",
                [
                    (
                        chunk.chunk_id,
                        chunk.granularity,
                        chunk.entry_id,
                        chunk.session_date.isoformat(),
                        chunk.entry_datetime.isoformat() if chunk.entry_datetime else None,
                        json.dumps(_chunk_to_storage(chunk), sort_keys=True),
                    )
                    for chunk in chunks
                ],
            )
            conn.execute(
                "insert into meta(key, value) values('rebuilt_at', ?)",
                (str(time.time_ns()),),
            )
            conn.execute(
                "insert into meta(key, value) values('runtime_root', ?)",
                (str(self.runtime.workspace_root),),
            )
            conn.execute(
                "insert into meta(key, value) values('entry_commits', ?)",
                (json.dumps(_entry_commit_map(self.runtime.workspace_root)),),
            )
            conn.commit()
        finally:
            conn.close()
        gc.collect()
        # Windows: a reader connection that has not finished closing can hold
        # the destination briefly; retry the atomic swap instead of failing the
        # whole rebuild, and never leave the tmp file behind.
        try:
            for attempt in range(5):
                try:
                    os.replace(tmp, self.db_path)
                    break
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.1 * (attempt + 1))
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

    def ensure_current(self) -> None:
        # Double-checked around the lock: the common already-current path stays
        # lock-free; racing first-load threads serialize, and the losers see the
        # winner's fresh cache instead of rebuilding again.
        if self.db_path.exists() and self._metadata_matches():
            return
        with self._rebuild_lock:
            if self.db_path.exists() and self._metadata_matches():
                return
            self._rebuild_locked()

    def status(self) -> dict[str, Any]:
        if not self.db_path.exists():
            return {"rebuilt_at": 0, "file_count": 0, "chunk_count": 0}
        with sqlite3.connect(self.db_path) as conn:
            rebuilt = conn.execute("select value from meta where key='rebuilt_at'").fetchone()
            file_count = conn.execute("select count(*) from files").fetchone()[0]
            chunk_count = conn.execute("select count(*) from chunks").fetchone()[0]
        return {
            "rebuilt_at": int(rebuilt[0]) if rebuilt else 0,
            "file_count": file_count,
            "chunk_count": chunk_count,
        }

    def entry_commits(self) -> dict[str, dict[str, str]]:
        self.ensure_current()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("select value from meta where key='entry_commits'").fetchone()
        return json.loads(row[0]) if row else {}

    def chunks(self, *, granularity: str | None = None) -> list[MemoryChunk]:
        self.ensure_current()
        sql = "select json from chunks"
        params: tuple[Any, ...] = ()
        if granularity is not None:
            sql += " where granularity = ?"
            params = (granularity,)
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_chunk_from_storage(json.loads(row[0])) for row in rows]

    def _metadata_matches(self) -> bool:
        current = sorted(_file_row(self.runtime.workspace_root, doc.path) for doc in iter_session_documents(self.runtime.memory_dir / "sessions"))
        try:
            with sqlite3.connect(self.db_path) as conn:
                stored = conn.execute("select path, mtime_ns, size from files order by path").fetchall()
                # Caches from before commit tracking lack the key; rebuild once.
                has_commits = conn.execute("select 1 from meta where key='entry_commits'").fetchone()
        except sqlite3.Error:
            return False
        if not has_commits:
            return False
        return [(str(path), int(mtime), int(size)) for path, mtime, size in current] == [
            (str(path), int(mtime), int(size)) for path, mtime, size in stored
        ]

    def _ensure_cache_parent(self) -> None:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            fallback = Path(tempfile.gettempdir()) / "memory-seed" / "lense"
            fallback.mkdir(parents=True, exist_ok=True)
            self.db_path = fallback / self.db_path.name

    @staticmethod
    def _create_schema(conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            create table meta(key text primary key, value text not null);
            create table files(path text primary key, mtime_ns integer not null, size integer not null);
            create table chunks(
              chunk_id text not null,
              granularity text not null,
              entry_id text,
              session_date text not null,
              entry_datetime text,
              json text not null,
              primary key(chunk_id, granularity)
            );
            create index chunks_entry_id_idx on chunks(entry_id);
            create index chunks_date_idx on chunks(session_date);
            """
        )


class LenseService:
    def __init__(self, cache: LenseCache):
        self.cache = cache

    def runtime(self) -> dict[str, Any]:
        self.cache.ensure_current()
        entries = self._entry_chunks()
        dates = [chunk.session_date for chunk in entries]
        return {
            "label": self.cache.runtime.workspace_root.name,
            "workspace_root": str(self.cache.runtime.workspace_root),
            "memory_dir": str(self.cache.runtime.memory_dir),
            "cache_path": str(self.cache.db_path),
            "legacy": self.cache.runtime.legacy,
            "entry_count": len(entries),
            "date_bounds": [min(dates).isoformat(), max(dates).isoformat()] if dates else [None, None],
        }

    def facets(self) -> dict[str, Any]:
        entries = self._entry_chunks()
        all_chunks = self.cache.chunks()
        dates = [chunk.session_date for chunk in entries]
        agents: dict[str, int] = {}
        users: dict[str, int] = {}
        topics: dict[str, int] = {}
        for chunk in entries:
            agents[chunk.agent_type or chunk.agent_name or "unknown"] = agents.get(chunk.agent_type or chunk.agent_name or "unknown", 0) + 1
            if chunk.user:
                users[chunk.user] = users.get(chunk.user, 0) + 1
            for topic in _topics(chunk):
                topics[topic] = topics.get(topic, 0) + 1
        return {
            "runtime": {
                **self.runtime(),
                "chunk_count": len(all_chunks),
                "entry_count": len(entries),
                "date_bounds": [min(dates).isoformat(), max(dates).isoformat()] if dates else [None, None],
            },
            "agents": dict(sorted(agents.items())),
            "users": dict(sorted(users.items())),
            "topics": dict(sorted(topics.items(), key=lambda item: (-item[1], item[0]))),
        }

    def search(
        self,
        *,
        q: str = "",
        limit: int = 25,
        cursor: str | None = None,
        granularity: str = "entry",
        agent: str | None = None,
        user: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        topic: str | None = None,
        sort: str = "relevance",
    ) -> dict[str, Any]:
        query = q.strip()
        if query and granularity == "entry":
            # Entry-level rollup (memory-explorer-entry-level-ui-results-plan.md):
            # rank across entry AND section chunks so a strong subsection match
            # can drive an entry's score, then collapse to one visible result
            # per session entry via the shared retrieval-service grouping.
            pool = _filter_chunks(
                self.cache.chunks(),
                agent=agent,
                user=user,
                date_from=date_from,
                date_to=date_to,
                topic=topic,
            )
            ranked_pool = rank_memory_chunks(query, pool, top_k=len(pool), embedding_provider=None)
            rollups = rollup_entry_matches(ranked_pool)
            if sort == "newest":
                rollups.sort(key=lambda r: (_chunk_datetime(r.representative.chunk), r.representative.chunk.start_line), reverse=True)
            elif sort == "oldest":
                rollups.sort(key=lambda r: (_chunk_datetime(r.representative.chunk), r.representative.chunk.start_line))
            offset = _cursor_offset(cursor)
            page_rollups = rollups[offset : offset + _limit(limit)]
            return {
                "query": q,
                "limit": _limit(limit),
                "cursor": cursor,
                "next_cursor": str(offset + len(page_rollups)) if offset + len(page_rollups) < len(rollups) else None,
                "total": len(rollups),
                "results": [_rollup_to_api(rollup) for rollup in page_rollups],
            }
        chunks = self.cache.chunks(granularity=None if granularity == "all" else granularity)
        chunks = _filter_chunks(chunks, agent=agent, user=user, date_from=date_from, date_to=date_to, topic=topic)
        if query:
            ranked = rank_memory_chunks(query, chunks, top_k=len(chunks), embedding_provider=None)
        else:
            ranked = [_unscored(chunk) for chunk in chunks]
        if sort == "newest" or not query:
            ranked.sort(key=lambda item: (_chunk_datetime(item.chunk), item.chunk.start_line), reverse=True)
        elif sort == "oldest":
            ranked.sort(key=lambda item: (_chunk_datetime(item.chunk), item.chunk.start_line))
        offset = _cursor_offset(cursor)
        page = ranked[offset : offset + _limit(limit)]
        next_cursor = str(offset + len(page)) if offset + len(page) < len(ranked) else None
        return {
            "query": q,
            "limit": _limit(limit),
            "cursor": cursor,
            "next_cursor": next_cursor,
            "total": len(ranked),
            "results": [_ranked_to_api(result) for result in page],
        }

    def chunk(self, chunk_id: str) -> dict[str, Any]:
        entries = self._entry_chunks()
        graph = build_related_entry_graph(self.cache.cwd, chunks=entries)
        selected = next((chunk for chunk in self.cache.chunks() if chunk.chunk_id == chunk_id), None)
        if selected is None:
            selected = next((chunk for chunk in entries if chunk.entry_id == chunk_id), None)
        if selected is None:
            raise KeyError(chunk_id)
        node = graph.get(selected.entry_id or "")
        sidecar = entry_diagram_sidecars(self.cache.cwd).get(selected.entry_id or "")
        # Commit packaging: which git commit first captured this entry, and
        # which other entries rode the same commit (batch commits on main and
        # pre-branching history included - the map is diff-derived, not
        # merge-derived). commit None + commit_tracking True = not yet
        # committed; commit_tracking False = no git data at all.
        commit_map = self.cache.entry_commits()
        commit = commit_map.get(selected.entry_id or "")
        commit_entry_ids: list[str] = []
        commit_entries: list[dict[str, Any]] = []
        if commit:
            commit_entry_ids = sorted(
                entry_id for entry_id, info in commit_map.items() if info.get("sha") == commit.get("sha")
            )
            by_entry = {chunk.entry_id: chunk for chunk in entries if chunk.entry_id}
            commit_entries = [
                _chunk_summary(by_entry[entry_id])
                for entry_id in commit_entry_ids
                if entry_id in by_entry and entry_id != selected.entry_id
            ]
        return {
            **_chunk_to_api(selected),
            "commit": commit or None,
            "commit_entry_ids": commit_entry_ids,
            "commit_entries": commit_entries,
            "commit_tracking": bool(commit_map),
            "backlinks": list(node.inbound if node else ()),
            "related_entries": list(selected.related_entries),
            # Authored decision-diagram sidecar metadata (Class 2, frozen);
            # rendering is the Explorer/Trail Phase-2 job - metadata-only here.
            "diagrams": [sidecar] if sidecar else [],
            "suggestions": self._suggestions(selected),
            "metadata": {
                "source": selected.source_path,
                "agent_type": selected.agent_type,
                "agent_name": selected.agent_name,
                "user": selected.user,
                "file_hash_id": selected.file_hash_id,
                "project_path": selected.project_path,
                "subproject_path": selected.subproject_path,
                "granularity": selected.granularity,
            },
        }

    def timeline(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        agent: str | None = None,
        user: str | None = None,
        topic: str | None = None,
        zoom: str = "day",
        limit: int = 50,
        cursor: str | None = None,
        include_empty: bool = True,
    ) -> dict[str, Any]:
        if zoom not in ZOOMS:
            raise ValueError("zoom must be day, 12h, 6h, or 3h")
        entries = _filter_chunks(
            self._entry_chunks(),
            agent=agent,
            user=user,
            date_from=date_from,
            date_to=date_to,
            topic=topic,
        )
        if entries:
            start_day = _parse_date(date_from) or min(chunk.session_date for chunk in entries)
            end_day = _parse_date(date_to) or max(chunk.session_date for chunk in entries)
        else:
            today = date.today()
            start_day = _parse_date(date_from) or today
            end_day = _parse_date(date_to) or start_day
        buckets = _timeline_buckets(entries, start_day, end_day, zoom, include_empty=include_empty)
        stream = sorted(entries, key=lambda chunk: (_chunk_datetime(chunk), chunk.start_line), reverse=True)
        offset = _cursor_offset(cursor)
        page = stream[offset : offset + _limit(limit, maximum=500)]
        return {
            "zoom": zoom,
            "date_from": start_day.isoformat(),
            "date_to": end_day.isoformat(),
            "buckets": buckets,
            "stream": [_chunk_to_api(chunk) for chunk in page],
            "next_cursor": str(offset + len(page)) if offset + len(page) < len(stream) else None,
        }

    def graph(
        self,
        *,
        entry_id: str | None = None,
        depth: int = 1,
        edge_types: Sequence[str] = ("related", "topic", "agent", "day"),
        limit: int = 80,
        granularity: str = "entry",
        agent: str | None = None,
        user: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        topic: str | None = None,
    ) -> dict[str, Any]:
        if granularity not in {"entry", "all"}:
            raise ValueError("granularity must be entry or all")
        granularity = "entry"
        entries = self.cache.chunks(granularity="entry")
        entries = _filter_chunks(entries, agent=agent, user=user, date_from=date_from, date_to=date_to, topic=topic)
        node_id = _graph_node_id_for(granularity)
        by_id = {node_id(chunk): chunk for chunk in entries if node_id(chunk)}
        edge_type_set = set(edge_types)
        edges = _graph_edges(entries, edge_type_set, node_id=node_id)
        graph = build_related_entry_graph(chunks=entries)
        connectivity = _connectivity_degrees(entries, node_id=node_id, graph=graph)
        importance = _importance_scores(entries, node_id=node_id, graph=graph)
        if entry_id and entry_id in by_id:
            visible_ids = _neighborhood(entry_id, edges, depth=max(depth, 1))
        else:
            visible_ids = list(by_id)
        limited_ids = set(visible_ids[: _limit(limit, maximum=1000)])
        nodes = [
            _graph_node(
                by_id[item_id],
                node_id=item_id,
                connectivity=connectivity.get(item_id, 0),
                importance_score=importance.get(item_id, 0.0),
            )
            for item_id in visible_ids
            if item_id in limited_ids and item_id in by_id
        ]
        visible_edges = [
            edge
            for edge in edges
            if edge["source"] in limited_ids and edge["target"] in limited_ids and edge["type"] in edge_type_set
        ][: _limit(limit, maximum=1000)]
        return {"entry_id": entry_id, "granularity": granularity, "nodes": nodes, "edges": visible_edges, "edge_types": sorted(edge_type_set)}

    def rebuild(self) -> dict[str, Any]:
        self.cache.rebuild()
        return self.cache.status()

    def _entry_chunks(self) -> list[MemoryChunk]:
        return self.cache.chunks(granularity="entry")

    def _suggestions(self, selected: MemoryChunk) -> dict[str, list[dict[str, Any]]]:
        entries = [chunk for chunk in self._entry_chunks() if chunk.chunk_id != selected.chunk_id]
        same_day = [chunk for chunk in entries if chunk.session_date == selected.session_date][:5]
        selected_topics = set(_topics(selected))
        same_topic = [chunk for chunk in entries if selected_topics.intersection(_topics(chunk))][:5]
        same_agent = [chunk for chunk in entries if chunk.agent_type == selected.agent_type][:5]
        return {
            "same_day": [_chunk_summary(chunk) for chunk in same_day],
            "same_topic": [_chunk_summary(chunk) for chunk in same_topic],
            "same_agent": [_chunk_summary(chunk) for chunk in same_agent],
        }


def create_app(cwd: str | Path = ".", *, rebuild_cache: bool = False) -> Any:
    try:
        from fastapi import FastAPI, HTTPException, Query
        from fastapi.responses import FileResponse, HTMLResponse
    except ModuleNotFoundError as exc:
        raise RuntimeError(missing_optional_dependency_hint()) from exc

    cache = LenseCache(cwd)
    if rebuild_cache:
        cache.rebuild()
    service = LenseService(cache)
    app = FastAPI(title="Memory Trace", version="1.0")

    @app.get("/", response_class=HTMLResponse)
    def index() -> Any:
        return HTMLResponse(_static_text("index.html", "text/html"))

    @app.get("/assets/{name}")
    def asset(name: str) -> Any:
        if name not in {"app.js", "styles.css"}:
            raise HTTPException(status_code=404, detail="asset not found")
        path = resources.files("memory_trace").joinpath("static", name)
        return FileResponse(path)

    @app.get("/assets/fonts/{name}")
    def asset_font(name: str) -> Any:
        # Self-hosted type pairing (OFL, license files ship alongside the
        # woff2s): no CDN call, Trace stays fully local/offline.
        if name not in {"inter-var.woff2", "space-grotesk-var.woff2"}:
            raise HTTPException(status_code=404, detail="asset not found")
        path = resources.files("memory_trace").joinpath("static", "fonts", name)
        return FileResponse(path, media_type="font/woff2")

    @app.get("/api/runtime")
    def api_runtime() -> dict[str, Any]:
        return service.runtime()

    @app.get("/api/facets")
    def api_facets() -> dict[str, Any]:
        return service.facets()

    @app.get("/api/search")
    def api_search(
        q: str = "",
        limit: int = 25,
        cursor: str | None = None,
        granularity: str = "entry",
        agent: str | None = None,
        user: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        topic: str | None = None,
        sort: str = "relevance",
    ) -> dict[str, Any]:
        return service.search(
            q=q,
            limit=limit,
            cursor=cursor,
            granularity=granularity,
            agent=agent,
            user=user,
            date_from=date_from,
            date_to=date_to,
            topic=topic,
            sort=sort,
        )

    @app.get("/api/chunks/{chunk_id:path}")
    def api_chunk(chunk_id: str) -> dict[str, Any]:
        try:
            return service.chunk(chunk_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="chunk not found") from None

    @app.get("/api/timeline")
    def api_timeline(
        date_from: str | None = None,
        date_to: str | None = None,
        zoom: str = Query("day", pattern="^(day|12h|6h|3h)$"),
        limit: int = 50,
        cursor: str | None = None,
        agent: str | None = None,
        user: str | None = None,
        topic: str | None = None,
        include_empty: bool = True,
    ) -> dict[str, Any]:
        return service.timeline(
            date_from=date_from,
            date_to=date_to,
            zoom=zoom,
            limit=limit,
            cursor=cursor,
            agent=agent,
            user=user,
            topic=topic,
            include_empty=include_empty,
        )

    @app.get("/api/graph")
    def api_graph(
        entry_id: str | None = None,
        depth: int = 1,
        edge_types: str = "related,topic,agent,day",
        limit: int = 80,
        granularity: str = Query("entry", pattern="^(entry|all)$"),
        agent: str | None = None,
        user: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        topic: str | None = None,
    ) -> dict[str, Any]:
        return service.graph(
            entry_id=entry_id,
            depth=depth,
            edge_types=tuple(x for x in edge_types.split(",") if x),
            limit=limit,
            granularity=granularity,
            agent=agent,
            user=user,
            date_from=date_from,
            date_to=date_to,
            topic=topic,
        )

    @app.post("/api/cache/rebuild")
    def api_rebuild() -> dict[str, Any]:
        return service.rebuild()

    return app


def run_server(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        print(missing_optional_dependency_hint(), file=os.sys.stderr)
        return 1
    try:
        app = create_app(args.cwd, rebuild_cache=args.rebuild_cache)
    except RuntimeError as exc:
        print(str(exc), file=os.sys.stderr)
        return 1
    port = int(args.port)
    if port == 0:
        port = _free_port(args.host)
    url = f"http://{args.host}:{port}"
    if not args.no_open and not os.environ.get("MEMORY_SEED_LENSE_SKIP_BROWSER"):
        webbrowser.open(url)
    print(f"Memory Trace serving {Path(args.cwd).resolve()} at {url}")
    uvicorn.run(app, host=args.host, port=port, log_level="info")
    return 0


def _file_row(root: Path, path: Path) -> tuple[str, int, int]:
    stat = path.stat()
    return (path.relative_to(root).as_posix(), stat.st_mtime_ns, stat.st_size)


def _entry_commit_map(root: Path) -> dict[str, dict[str, str]]:
    """entry_id -> the oldest commit whose diff added that entry's id line.

    One ``git log -p`` pass over the session tree, newest-first; assignment
    overwrites on every sighting, so the final value is the OLDEST commit -
    migrations and fuse rewrites that re-add an entry never steal attribution
    from the commit that first captured it. This is what makes "work done on
    main with no commit rides the next commit that occurs" true by
    construction, including pre-branching history. Fails open to an empty map
    when git or a repository is unavailable.
    """
    try:
        proc = subprocess.run(
            [
                "git", "-C", str(root), "log", "-p",
                "--format=%x01%H%x1f%h%x1f%aI%x1f%s",
                "--", ".memory-seed/sessions",
            ],
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if proc.returncode != 0:
        return {}
    mapping: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for line in proc.stdout.decode("utf-8", errors="replace").splitlines():
        if line.startswith("\x01"):
            parts = (line[1:].split("\x1f") + ["", "", "", ""])[:4]
            current = {"sha": parts[0], "short": parts[1], "date": parts[2], "subject": parts[3]}
        elif current is not None and line.startswith("+entry_id:"):
            entry_id = line[len("+entry_id:"):].strip()
            if entry_id:
                mapping[entry_id] = current
    return mapping


def _chunk_to_storage(chunk: MemoryChunk) -> dict[str, Any]:
    data = asdict(chunk)
    data["session_date"] = chunk.session_date.isoformat()
    data["entry_datetime"] = chunk.entry_datetime.isoformat() if chunk.entry_datetime else None
    return data


def _chunk_from_storage(data: dict[str, Any]) -> MemoryChunk:
    data = dict(data)
    data["session_date"] = datetime.strptime(data["session_date"], "%Y-%m-%d").date()
    data["entry_datetime"] = datetime.fromisoformat(data["entry_datetime"]) if data.get("entry_datetime") else None
    for key in (
        "heading_path",
        "tags",
        "contexts",
        "lexical_terms",
        "related_entries",
        "sections",
    ):
        data[key] = tuple(data.get(key) or ())
    if data.get("entry_line_range"):
        data["entry_line_range"] = tuple(data["entry_line_range"])
    return MemoryChunk(**data)


def _chunk_to_api(chunk: MemoryChunk) -> dict[str, Any]:
    return {
        "chunk_id": chunk.chunk_id,
        "entry_id": chunk.entry_id,
        "title": chunk.title,
        "entry_title": chunk.entry_title,
        "date": chunk.session_date.isoformat(),
        "time": chunk.entry_datetime.strftime("%H:%M") if chunk.entry_datetime else None,
        "entry_datetime": chunk.entry_datetime.isoformat() if chunk.entry_datetime else None,
        "source": chunk.source_path,
        "path": chunk.source_path,
        "line_range": [chunk.start_line, chunk.end_line],
        "heading_path": list(chunk.heading_path),
        "sections": list(chunk.sections),
        "tags": list(chunk.tags),
        "topics": _topics(chunk),
        "contexts": list(chunk.contexts),
        "lexical_terms": list(chunk.lexical_terms),
        "agent_type": chunk.agent_type,
        "agent_name": chunk.agent_name,
        "user": chunk.user,
        "branch": chunk.branch,
        "text": chunk.text,
        "excerpt": _excerpt(chunk.text),
        "granularity": chunk.granularity,
        "related_entries": list(chunk.related_entries),
    }


def _ranked_to_api(result: Any) -> dict[str, Any]:
    return {
        **_chunk_to_api(result.chunk),
        "score": round(result.final_score, 6),
        "match_score": round(result.match_score, 6),
        "lexical_score": round(result.lexical_score, 6),
        "semantic_score": result.semantic_score,
        "recency_multiplier": round(result.recency_multiplier, 6),
        "matched_terms": list(result.matched_terms),
        "matched_fields": list(result.matched_fields),
        "score_explanation": _score_explanation(result),
    }


def _rollup_to_api(rollup: EntryRollup) -> dict[str, Any]:
    """One selectable entry-level search result. Section matches ride along as
    highlight metadata ("Matched section" context in the UI), never as their
    own selectable records - per the entry-level UI results plan."""
    best = rollup.best
    return {
        **_chunk_to_api(rollup.representative.chunk),
        "score": round(best.final_score, 6),
        "match_score": round(best.match_score, 6),
        "lexical_score": round(best.lexical_score, 6),
        "semantic_score": best.semantic_score,
        "recency_multiplier": round(best.recency_multiplier, 6),
        "matched_terms": list(best.matched_terms),
        "matched_fields": list(best.matched_fields),
        "score_explanation": _score_explanation(best),
        "best_match_chunk_id": best.chunk.chunk_id,
        "score_source": rollup.score_source,
        "matched_sections": [
            {
                "chunk_id": section.chunk.chunk_id,
                "heading_path": list(section.chunk.heading_path),
                "line_range": [section.chunk.start_line, section.chunk.end_line],
                "excerpt": _excerpt(section.chunk.text),
            }
            for section in rollup.sections
        ],
    }


def _unscored(chunk: MemoryChunk) -> Any:
    return RankedMemoryChunk(
        chunk=chunk,
        final_score=0.0,
        match_score=0.0,
        lexical_score=0.0,
        semantic_score=None,
        recency_multiplier=1.0,
        age_days=0,
        matched_terms=(),
        matched_fields=(),
    )


def _score_explanation(result: Any) -> str:
    if not result.matched_fields:
        return "No query match; ordered by date."
    fields = ", ".join(result.matched_fields)
    terms = ", ".join(result.matched_terms)
    return f"Matched {terms} in {fields}; recency x{result.recency_multiplier:.2f}."


def _filter_chunks(
    chunks: Sequence[MemoryChunk],
    *,
    agent: str | None = None,
    user: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    topic: str | None = None,
) -> list[MemoryChunk]:
    start = _parse_date(date_from)
    end = _parse_date(date_to)
    return [
        chunk
        for chunk in chunks
        if (not agent or chunk.agent_type == agent or chunk.agent_name == agent)
        and (not user or chunk.user == user)
        and (start is None or chunk.session_date >= start)
        and (end is None or chunk.session_date <= end)
        and (not topic or topic in _topics(chunk))
    ]


def _timeline_buckets(
    entries: Sequence[MemoryChunk],
    start_day: date,
    end_day: date,
    zoom: str,
    *,
    include_empty: bool = True,
) -> list[dict[str, Any]]:
    hours = ZOOMS[zoom]
    counts: dict[datetime, list[MemoryChunk]] = {}
    for chunk in entries:
        dt = _chunk_datetime(chunk)
        bucket_hour = 0 if zoom == "day" else (dt.hour // hours) * hours
        bucket = datetime.combine(dt.date(), datetime_time(hour=bucket_hour))
        counts.setdefault(bucket, []).append(chunk)

    buckets: list[dict[str, Any]] = []
    current = datetime.combine(start_day, datetime_time.min)
    stop = datetime.combine(end_day + timedelta(days=1), datetime_time.min)
    step = timedelta(hours=hours)
    while current < stop:
        grouped = counts.get(current, [])
        if not grouped and not include_empty:
            current += step
            continue
        buckets.append(
            {
                "start": current.isoformat(),
                "end": (current + step).isoformat(),
                "date": current.date().isoformat(),
                "label": current.date().isoformat() if zoom == "day" else current.strftime("%Y-%m-%d %H:%M"),
                "count": len(grouped),
                "entries": [_chunk_summary(chunk) for chunk in sorted(grouped, key=lambda item: (_chunk_datetime(item), item.start_line))[:10]],
            }
        )
        current += step
    return buckets


def _graph_edges(
    entries: Sequence[MemoryChunk],
    edge_types: set[str],
    *,
    node_id: Callable[[MemoryChunk], str | None] | None = None,
) -> list[dict[str, str]]:
    node_id = node_id or (lambda chunk: chunk.entry_id)
    by_id = {chunk.entry_id: chunk for chunk in entries if chunk.entry_id}
    node_ids = {node_id(chunk) for chunk in entries if node_id(chunk)}
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def add(source: str | None, target: str | None, edge_type: str) -> None:
        if not source or not target or source == target or source not in node_ids or target not in node_ids:
            return
        key = (source, target, edge_type)
        if key not in seen:
            seen.add(key)
            edges.append({"source": source, "target": target, "type": edge_type})

    if edge_types & {"related", "supersedes", "evolves"}:
        graph = build_related_entry_graph(chunks=entries)
        for node in graph.values():
            source_chunk = by_id.get(node.entry_id)
            source = node_id(source_chunk) if source_chunk else node.entry_id
            if "related" in edge_types:
                for target in node.outbound:
                    target_chunk = by_id.get(target)
                    add(source, node_id(target_chunk) if target_chunk else target, "related")
            # Trail view: supersession is a directed, typed *status* edge
            # ("this decision replaced that one"), rendered distinctly from plain
            # relatedness per docs/3_Spec/graph-edge-contract.md - never conflated.
            if "supersedes" in edge_types:
                for target in node.supersedes:
                    target_chunk = by_id.get(target)
                    add(source, node_id(target_chunk) if target_chunk else target, "supersedes")
            # evolves is the freshness-without-retirement lifecycle edge: the
            # source refines the target while the target stays valid.
            if "evolves" in edge_types:
                for target in node.evolves:
                    target_chunk = by_id.get(target)
                    add(source, node_id(target_chunk) if target_chunk else target, "evolves")

    def chain(grouped: dict[str, list[MemoryChunk]], edge_type: str) -> None:
        if edge_type not in edge_types:
            return
        for group in grouped.values():
            ordered = sorted(group, key=lambda chunk: (_chunk_datetime(chunk), chunk.start_line))
            for left, right in zip(ordered, ordered[1:]):
                add(node_id(left), node_id(right), edge_type)

    topic_groups: dict[str, list[MemoryChunk]] = {}
    agent_groups: dict[str, list[MemoryChunk]] = {}
    day_groups: dict[str, list[MemoryChunk]] = {}
    branch_groups: dict[str, list[MemoryChunk]] = {}
    for chunk in entries:
        for topic in _topics(chunk):
            topic_groups.setdefault(topic, []).append(chunk)
        agent_groups.setdefault(chunk.agent_type or chunk.agent_name or "unknown", []).append(chunk)
        day_groups.setdefault(chunk.session_date.isoformat(), []).append(chunk)
        # Trail view: entries sharing a recorded `branch:` value form a
        # time-ordered intra-branch lineage thread (same shape as topic/agent/day
        # chains). Entries with no branch recorded simply don't participate.
        if chunk.branch:
            branch_groups.setdefault(chunk.branch, []).append(chunk)
    chain(topic_groups, "topic")
    chain(agent_groups, "agent")
    chain(day_groups, "day")
    chain(branch_groups, "branch")
    return edges


def _connectivity_degrees(
    entries: Sequence[MemoryChunk],
    *,
    node_id: Callable[[MemoryChunk], str | None] | None = None,
    graph: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Undirected connectivity per node: how many distinct other entries it
    touches via a ``related_entries`` edge in *either* direction. This is a
    graph-display weight (bigger node = more connected), deliberately distinct
    from the directional ``inbound_relation_count`` importance signal exposed by
    the CLI/MCP, which counts inbound backlinks only. Pass ``graph`` to reuse an
    already-built related-entry graph."""
    node_id = node_id or (lambda chunk: chunk.entry_id)
    by_entry_id = {chunk.entry_id: chunk for chunk in entries if chunk.entry_id}
    node_ids = {node_id(chunk) for chunk in entries if node_id(chunk)}
    degree = {item_id: 0 for item_id in node_ids if item_id}
    graph = graph if graph is not None else build_related_entry_graph(chunks=entries)
    for graph_node in graph.values():
        source_chunk = by_entry_id.get(graph_node.entry_id)
        source = node_id(source_chunk) if source_chunk else graph_node.entry_id
        if source not in node_ids:
            continue
        for target_entry_id in {*graph_node.outbound, *graph_node.inbound}:
            target_chunk = by_entry_id.get(target_entry_id)
            target = node_id(target_chunk) if target_chunk else target_entry_id
            if target in node_ids and target != source:
                degree[source] = degree.get(source, 0) + 1
    return degree


def _importance_scores(
    entries: Sequence[MemoryChunk],
    *,
    node_id: Callable[[MemoryChunk], str | None] | None = None,
    graph: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Per-node ``importance_score`` (inbound relation count, supersession-dampened)
    from the related-entry graph, keyed by graph node id. This is the same
    directional importance signal the CLI/MCP expose; it lets the Lense graph
    optionally size nodes by importance instead of ``connectivity``."""
    node_id = node_id or (lambda chunk: chunk.entry_id)
    by_entry_id = {chunk.entry_id: chunk for chunk in entries if chunk.entry_id}
    node_ids = {node_id(chunk) for chunk in entries if node_id(chunk)}
    scores = {item_id: 0.0 for item_id in node_ids if item_id}
    graph = graph if graph is not None else build_related_entry_graph(chunks=entries)
    for graph_node in graph.values():
        source_chunk = by_entry_id.get(graph_node.entry_id)
        source = node_id(source_chunk) if source_chunk else graph_node.entry_id
        if source in node_ids:
            scores[source] = graph_node.importance_score
    return scores


def _neighborhood(entry_id: str, edges: Sequence[dict[str, str]], *, depth: int) -> list[str]:
    ordered = [entry_id]
    seen = {entry_id}
    frontier = {entry_id}
    for _ in range(depth):
        next_frontier: set[str] = set()
        for edge in edges:
            if edge["source"] in frontier:
                next_frontier.add(edge["target"])
            if edge["target"] in frontier:
                next_frontier.add(edge["source"])
        next_frontier -= seen
        ordered.extend(sorted(next_frontier))
        seen |= next_frontier
        frontier = next_frontier
    return ordered


def _graph_node_id_for(granularity: str) -> Callable[[MemoryChunk], str | None]:
    if granularity == "all":
        return lambda chunk: chunk.chunk_id
    return lambda chunk: chunk.entry_id


def _graph_node(
    chunk: MemoryChunk,
    *,
    node_id: str | None = None,
    connectivity: int = 0,
    importance_score: float = 0.0,
) -> dict[str, Any]:
    return {
        "id": node_id or chunk.entry_id or chunk.chunk_id,
        "chunk_id": chunk.chunk_id,
        "entry_id": chunk.entry_id,
        "title": chunk.title,
        "date": chunk.session_date.isoformat(),
        "datetime": chunk.entry_datetime.isoformat() if chunk.entry_datetime else None,
        "branch": chunk.branch,
        "agent": chunk.agent_type or chunk.agent_name or "unknown",
        "topics": _topics(chunk),
        "granularity": chunk.granularity,
        "connectivity": connectivity,
        "importance_score": round(importance_score, 3),
    }


def _chunk_summary(chunk: MemoryChunk) -> dict[str, Any]:
    return {
        "chunk_id": chunk.chunk_id,
        "entry_id": chunk.entry_id,
        "title": chunk.title,
        "date": chunk.session_date.isoformat(),
        "time": chunk.entry_datetime.strftime("%H:%M") if chunk.entry_datetime else None,
        "agent": chunk.agent_type or chunk.agent_name or "unknown",
        "topics": _topics(chunk),
    }


def _chunk_datetime(chunk: MemoryChunk) -> datetime:
    return chunk.entry_datetime or datetime.combine(chunk.session_date, datetime_time.min)


def _topics(chunk: MemoryChunk) -> list[str]:
    return sorted(set(chunk.topics) | set(chunk.tags) | set(chunk.contexts))


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _cursor_offset(cursor: str | None) -> int:
    try:
        return max(0, int(cursor or "0"))
    except ValueError:
        return 0


def _limit(limit: int, *, maximum: int = 100) -> int:
    return max(1, min(int(limit), maximum))


def _excerpt(text: str, *, length: int = 220) -> str:
    cleaned = " ".join(line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("```"))
    return cleaned[: length - 1] + "…" if len(cleaned) > length else cleaned


def _static_text(name: str, media_type: str) -> str:
    return resources.files("memory_trace").joinpath("static", name).read_text(encoding="utf-8")


def _free_port(host: str) -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])
