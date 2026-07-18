from __future__ import annotations

import argparse
import hashlib
import re
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
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import date, datetime, time as datetime_time, timedelta
from importlib import resources
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

# Memory Trace consumes the core control plane's public API only - it never
# reimplements parsing, ranking, the graph-edge contract, or diagram-sidecar
# reading. These are the frozen surfaces the distribution split depends on.
from memory_seed.core import (
    iter_diagram_sidecar_documents,
    iter_link_sidecar_documents,
    iter_session_documents,
    resolve_runtime,
)
from memory_seed.retrieval import EntryRollup, entry_diagram_sidecars, entry_link_sidecars, rollup_entry_matches
from memory_seed.semantic_cache import (
    ContinuityBlock,
    MemoryChunk,
    RankedMemoryChunk,
    build_related_entry_graph,
    extract_memory_chunks,
    rank_memory_chunks,
)
from memory_seed.topics import expand_topic_filter
from .graph_projection import project_trace_graph


ZOOMS = {"day": 24, "12h": 12, "6h": 6, "3h": 3}

# Derived-projection schema version (contract G4). Bump when the ingest/row
# shape or stored-meta contract changes so an older cache is fully rebuilt
# rather than reused. Checked before any git work in ensure_current.
PROJECTION_SCHEMA_VERSION = 1


def _git_head(root: Path) -> str | None:
    """Current HEAD sha for the repo containing ``root`` - the projection's
    build watermark (contract G5). None when git is unavailable, which routes
    ensure_current to the no-git mtime fallback (G7)."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _porcelain_paths(output: str) -> list[str]:
    """Paths from ``git status --porcelain -z`` output. Renames/copies carry a
    trailing NUL-separated original path; both the new and original path are
    returned so a rename in or out of the sessions tree still invalidates."""
    tokens = output.split("\x00")
    paths: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if len(token) < 4:
            continue
        status, path = token[:2], token[3:]
        if not path:
            continue
        paths.append(path)
        if status[0] in ("R", "C") or status[1] in ("R", "C"):
            if index < len(tokens) and tokens[index]:
                paths.append(tokens[index])
                index += 1
    return paths


def _working_tree_signature(root: Path, pathspec: str) -> str | None:
    """Signature of the git-dirty files under ``pathspec`` (relative to
    ``root``): each dirty path's (path, mtime_ns, size), or a deleted marker.

    This is the uncommitted half of the freshness delta (contract G5): session
    entries are appended-then-committed-later, so the dirty case is the common
    one. ``git status`` reports ONLY what changed, so this is O(changes), never
    a whole-corpus scan - and it detects a re-edit of an already-dirty file
    (its mtime moves) that the porcelain status alone would miss. None when git
    is unavailable (caller uses the no-git fallback)."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "-z", "--", pathspec],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    entries: list[tuple[str, Any, Any]] = []
    seen: set[str] = set()
    for path in _porcelain_paths(proc.stdout):
        if path in seen:
            continue
        seen.add(path)
        target = root / path
        try:
            stat = target.stat()
            entries.append((path, stat.st_mtime_ns, stat.st_size))
        except OSError:
            entries.append((path, "deleted", "deleted"))
    return json.dumps(sorted(entries, key=lambda item: item[0]))


def missing_optional_dependency_hint() -> str:
    return 'Install with: pip install "memory-seed[trace]"'


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


class _CacheRebuildLease:
    """A short-lived, cross-process writer lease for one derived cache file.

    SQLite connections are deliberately short lived, but Windows can still deny
    ``os.replace`` while a second Trace process is rebuilding the same cache.
    An advisory lock next to the cache serializes writers without making the
    Markdown source or normal read paths depend on a daemon.
    """

    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def hold(self, *, timeout_seconds: float, retry_seconds: float):
        fd: int | None = None
        locked = False
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"0")
        except OSError:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            yield False
            return

        try:
            deadline = time.monotonic() + timeout_seconds
            while True:
                if self._try_lock(fd):
                    locked = True
                    break
                if time.monotonic() >= deadline:
                    break
                time.sleep(retry_seconds)
            yield locked
        finally:
            if locked:
                self._unlock(fd)
            os.close(fd)

    @staticmethod
    def _try_lock(fd: int) -> bool:
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (ImportError, OSError):
            return False
        return True

    @staticmethod
    def _unlock(fd: int) -> None:
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_UN)
        except (ImportError, OSError):
            pass


def list_worktrees(cwd: str | Path = ".") -> list[dict[str, Any]]:
    """Enumerate the git worktrees for the repository containing ``cwd``.

    Returns ``{path, branch, head, is_primary}`` dicts in git's own order (the
    primary working tree first). Each worktree is a checkout of a different
    branch with its own ``.memory-seed/sessions``, so pointing a TraceService
    at one shows that branch's memory. Returns an empty list when git or the
    repository is unavailable - callers fall back to the launch checkout alone.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(cwd), "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    worktrees: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for raw in proc.stdout.splitlines():
        line = raw.rstrip()
        if not line:
            if current.get("path"):
                worktrees.append(current)
            current = {}
            continue
        if line.startswith("worktree "):
            current = {"path": line[len("worktree "):].strip(), "head": None, "branch": None}
        elif line.startswith("HEAD "):
            current["head"] = line[len("HEAD "):].strip()
        elif line.startswith("branch "):
            ref = line[len("branch "):].strip()
            current["branch"] = ref.rsplit("/", 1)[-1] if "/" in ref else ref
        elif line == "detached":
            current["branch"] = None
    if current.get("path"):
        worktrees.append(current)
    for index, entry in enumerate(worktrees):
        entry["is_primary"] = index == 0
    return worktrees


class TraceCache:
    # How long a positive freshness verdict is trusted before re-checking. The
    # check reads git (tens of ms on Windows/OneDrive) and runs per read, so a
    # single interaction fires it several times; memoizing over a short window
    # keeps switching snappy while a real change is still seen within the TTL.
    _FRESHNESS_TTL_SECONDS = 2.0
    # A normal full rebuild is much shorter than this. A bounded wait lets a
    # second server reuse the first server's fresh projection; if that server
    # does not release the lease, it builds an isolated disposable projection.
    _REBUILD_LEASE_TIMEOUT_SECONDS = 5.0
    _REBUILD_LEASE_RETRY_SECONDS = 0.05

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
        self._primary_db_path = self.db_path
        self._rebuild_lease_path = self._primary_db_path.with_name(f"{self._primary_db_path.name}.lock")
        self._using_temporary_cache = False
        # Serializes rebuilds within this process. The UI fires several API
        # calls concurrently on first load; without this, two threads raced the
        # same pid-named tmp file ("table meta already exists", then Windows
        # PermissionError on replace/unlink).
        self._rebuild_lock = threading.Lock()
        # Monotonic deadline until which the projection is trusted current
        # without re-running the freshness check. The check spawns git (tens of
        # ms on Windows/OneDrive) and every read calls ensure_current, so a
        # single UI interaction (several reads) would otherwise pay it many
        # times over - the switching lag this collapses.
        self._fresh_until = 0.0
        # Deserialized chunks by granularity, memoized until the next rebuild.
        # Deserializing all chunks from JSON is the dominant read cost (~60 ms
        # for the full corpus), and every read endpoint calls chunks() one or
        # more times per request; the rows only change when the projection
        # rebuilds, so cache the parsed list and clear it on rebuild.
        self._chunks_memo: dict[str | None, list[MemoryChunk]] = {}
        # Bumped on every rebuild. The derived-bundle memo (TraceService) keys on
        # it so the sidecar-derived reads (augmented entries, related graph,
        # diagram badges) refresh exactly when the projection does - safe now
        # that sidecar changes participate in the freshness signal (see
        # _tracked_document_paths).
        self._generation = 0

    def generation(self) -> int:
        self.ensure_current()
        return self._generation

    def rebuild(self) -> None:
        with self._rebuild_lock:
            self._rebuild_coordinated(force=True)
        # A just-built projection is current; open the freshness window so the
        # first reads after an explicit rebuild don't immediately re-check.
        self._mark_fresh()

    def _rebuild_locked(self) -> None:
        self._ensure_cache_parent()
        # Unique per attempt (not just per pid): concurrent threads share a pid,
        # and a crashed run's stale tmp must never be another rebuild's target.
        tmp = self.db_path.with_name(f"{self.db_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            conn = sqlite3.connect(tmp)
        except sqlite3.OperationalError:
            # Sandboxed desktop launches can permit directory creation beneath
            # LOCALAPPDATA but still deny SQLite's file handle. Keep the cache
            # derived and disposable by retrying in the system temp directory.
            self._use_temporary_cache()
            tmp = self.db_path.with_name(f"{self.db_path.name}.{uuid.uuid4().hex}.tmp")
            conn = sqlite3.connect(tmp)
        try:
            self._create_schema(conn)
            file_rows = [
                _file_row(self.runtime.workspace_root, path)
                for path in _tracked_document_paths(self.runtime)
            ]
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
            commit_map = _entry_commit_map(self.runtime.workspace_root)
            conn.execute(
                "insert into meta(key, value) values('entry_commits', ?)",
                (json.dumps(commit_map),),
            )
            # Evidence-based main attribution: an entry with no recorded
            # branch whose capturing commit sits on the trunk's first-parent
            # history was committed directly on main - proven, not assumed.
            main_shas = _first_parent_main_shas(self.runtime.workspace_root)
            conn.execute(
                "insert into meta(key, value) values('main_commit_entries', ?)",
                (json.dumps(sorted(eid for eid, info in commit_map.items() if info.get("sha") in main_shas)),),
            )
            # Merge-commit ground truth for the Trail: Memory-Entry trailers on
            # trunk first-parent commits, each with its merge-base fork point.
            conn.execute(
                "insert into meta(key, value) values('trailer_merges', ?)",
                (json.dumps(_first_parent_trailer_commits(self.runtime.workspace_root)),),
            )
            # Derived-projection provenance (contract G4/G5): the schema version
            # (rebuild on bump) and the build watermark (HEAD) + dirty-file
            # signature, so a warm start proves "nothing changed" from git in
            # O(changes) instead of scanning the whole corpus. Empty watermark =
            # built without git; ensure_current then uses the mtime fallback.
            head = _git_head(self.runtime.workspace_root)
            conn.execute(
                "insert into meta(key, value) values('schema_version', ?)",
                (str(PROJECTION_SCHEMA_VERSION),),
            )
            conn.execute(
                "insert into meta(key, value) values('build_watermark', ?)",
                (head or "",),
            )
            signature = (
                _working_tree_signature(self.runtime.workspace_root, self._sessions_pathspec())
                if head
                else None
            )
            conn.execute(
                "insert into meta(key, value) values('dirty_signature', ?)",
                (signature if signature is not None else "",),
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
                        if self._is_temporary_cache():
                            raise
                        self._use_temporary_cache()
                        self._rebuild_locked()
                        return
                    time.sleep(0.1 * (attempt + 1))
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
        # The swap succeeded (a failed swap raises above, never reaching here):
        # the parsed-chunk memo now describes the previous projection, so drop
        # it and bump the generation so the derived-bundle memo invalidates too.
        self._chunks_memo = {}
        self._generation += 1

    def _rebuild_coordinated(self, *, force: bool) -> None:
        with self._rebuild_lease() as acquired:
            if not acquired:
                # A separate server owns the shared cache. Never make a UI
                # request fail because its rebuild is slow or wedged: build an
                # isolated, disposable projection instead.
                self._use_temporary_cache()
            elif not force and self.db_path.exists() and self._is_current():
                # Another server may have refreshed the projection while this
                # process waited for the lease. Reuse that winning snapshot.
                return
            self._rebuild_locked()

    def _rebuild_lease(self):
        return _CacheRebuildLease(self._rebuild_lease_path).hold(
            timeout_seconds=self._REBUILD_LEASE_TIMEOUT_SECONDS,
            retry_seconds=self._REBUILD_LEASE_RETRY_SECONDS,
        )

    def ensure_current(self) -> None:
        # Fast path: within the freshness window, trust the last verdict without
        # re-checking. This is what collapses a burst of reads (one UI
        # interaction) into a single freshness check instead of one per read.
        if time.monotonic() < self._fresh_until and self.db_path.exists():
            return
        # Double-checked around the lock: the common already-current path stays
        # lock-free; racing first-load threads serialize, and the losers see the
        # winner's fresh cache instead of rebuilding again.
        if self.db_path.exists() and self._is_current():
            self._mark_fresh()
            return
        with self._rebuild_lock:
            if time.monotonic() < self._fresh_until and self.db_path.exists():
                return
            if self.db_path.exists() and self._is_current():
                self._mark_fresh()
                return
            self._rebuild_coordinated(force=False)
            self._mark_fresh()

    def _mark_fresh(self) -> None:
        self._fresh_until = time.monotonic() + self._FRESHNESS_TTL_SECONDS

    def _sessions_pathspec(self) -> str:
        """The sessions tree as a git pathspec relative to the workspace root
        (git runs with -C workspace_root). Falls back to the absolute path if
        sessions lives outside the root (unusual runtime layout)."""
        sessions = self.runtime.memory_dir / "sessions"
        try:
            return sessions.relative_to(self.runtime.workspace_root).as_posix()
        except ValueError:
            return str(sessions)

    def _is_current(self) -> bool:
        """Warm-start freshness (contract G5): true iff the projection is
        provably up to date. With git this is O(changes) - HEAD unmoved AND the
        dirty sessions signature unchanged - never a whole-corpus scan. Without
        git it degrades to the mtime scan (G7). Every ambiguity fails toward a
        rebuild (return False), so stale is never served."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                meta = dict(
                    conn.execute(
                        "select key, value from meta where key in "
                        "('schema_version', 'build_watermark', 'dirty_signature')"
                    ).fetchall()
                )
                has_commits = conn.execute("select 1 from meta where key='entry_commits'").fetchone()
                has_main = conn.execute("select 1 from meta where key='main_commit_entries'").fetchone()
                has_merges = conn.execute("select 1 from meta where key='trailer_merges'").fetchone()
        except sqlite3.Error:
            return False
        # Pre-provenance or partial caches (missing any required meta) rebuild once.
        if not (has_commits and has_main and has_merges):
            return False
        if meta.get("schema_version") != str(PROJECTION_SCHEMA_VERSION):
            return False  # schema bump -> full rebuild, before any git work
        head = _git_head(self.runtime.workspace_root)
        if head is None:
            # No git (G7): the projection self-heals to current Markdown but the
            # past cannot be proven unaltered; fall back to the mtime scan.
            return self._metadata_matches()
        # A moved HEAD (new commit) - or a watermark commit that git can no
        # longer resolve (rebase/gc left it != HEAD) - is not current: rebuild.
        if meta.get("build_watermark") != head:
            return False
        signature = _working_tree_signature(self.runtime.workspace_root, self._sessions_pathspec())
        if signature is None:
            return False  # git status failed unexpectedly -> fail toward rebuild
        return signature == meta.get("dirty_signature", "")

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

    def main_commit_entries(self) -> set[str]:
        self.ensure_current()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("select value from meta where key='main_commit_entries'").fetchone()
        return set(json.loads(row[0])) if row else set()

    def trailer_merges(self) -> list[dict[str, Any]]:
        self.ensure_current()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("select value from meta where key='trailer_merges'").fetchone()
        return json.loads(row[0]) if row else []

    def chunks(self, *, granularity: str | None = None) -> list[MemoryChunk]:
        # ensure_current() clears _chunks_memo when it rebuilds, so a hit is
        # always for the current projection. MemoryChunk is frozen and callers
        # never mutate the returned list in place (they filter/copy), so the
        # memoized list is safe to share.
        self.ensure_current()
        cached = self._chunks_memo.get(granularity)
        if cached is not None:
            return cached
        sql = "select json from chunks"
        params: tuple[Any, ...] = ()
        if granularity is not None:
            sql += " where granularity = ?"
            params = (granularity,)
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        result = [_chunk_from_storage(json.loads(row[0])) for row in rows]
        self._chunks_memo[granularity] = result
        return result

    def _metadata_matches(self) -> bool:
        current = sorted(
            _file_row(self.runtime.workspace_root, path)
            for path in _tracked_document_paths(self.runtime)
        )
        try:
            with sqlite3.connect(self.db_path) as conn:
                stored = conn.execute("select path, mtime_ns, size from files order by path").fetchall()
                # Caches from before commit tracking lack these keys; rebuild once.
                has_commits = conn.execute("select 1 from meta where key='entry_commits'").fetchone()
                has_main_map = conn.execute("select 1 from meta where key='main_commit_entries'").fetchone()
                has_merges = conn.execute("select 1 from meta where key='trailer_merges'").fetchone()
        except sqlite3.Error:
            return False
        if not has_commits or not has_main_map or not has_merges:
            return False
        return [(str(path), int(mtime), int(size)) for path, mtime, size in current] == [
            (str(path), int(mtime), int(size)) for path, mtime, size in stored
        ]

    def _ensure_cache_parent(self) -> None:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            self._use_temporary_cache()

    def _use_temporary_cache(self) -> None:
        fallback = self._temporary_cache_dir()
        fallback.mkdir(parents=True, exist_ok=True)
        if not self._using_temporary_cache:
            # A generic tempfile fallback used the same filename for every
            # Trace process, reproducing the original shared-cache race in the
            # fallback directory. Keep it derived and disposable, but make it
            # process/attempt specific so a blocked primary cache cannot cause
            # another server's UI to fail.
            self.db_path = fallback / (
                f"{self._primary_db_path.stem}.{os.getpid()}.{uuid.uuid4().hex}{self._primary_db_path.suffix}"
            )
            self._using_temporary_cache = True

    def _is_temporary_cache(self) -> bool:
        return self._using_temporary_cache

    @staticmethod
    def _temporary_cache_dir() -> Path:
        return Path(tempfile.gettempdir()) / "memory-seed" / "lense"

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


class TraceService:
    def __init__(self, cache: TraceCache):
        self.cache = cache
        # (generation, (augmented_entries, related_graph, diagram_map)) memo.
        # These are the sidecar-derived read structures - the per-request disk
        # walk + augmentation cost. Now that sidecar changes bump the cache
        # generation (they participate in the freshness signal), this memo is
        # safe: it refreshes exactly when Markdown or a sidecar changes.
        self._derived_memo: tuple[int, tuple[list[MemoryChunk], dict[str, Any], dict[str, Any]]] | None = None

    def _derived(self) -> tuple[list[MemoryChunk], dict[str, Any], dict[str, Any]]:
        """Augmented all-entry chunks + related graph + diagram-sidecar map,
        memoized per cache generation. Filtered views (graph()) reuse the
        augmented entries and build their own small graph; the shared cost saved
        here is the sidecar disk reads and the whole-corpus augmentation."""
        generation = self.cache.generation()
        if self._derived_memo is not None and self._derived_memo[0] == generation:
            return self._derived_memo[1]
        entries = _augment_with_link_sidecars(self.cache.chunks(granularity="entry"), self.cache.cwd)
        graph = build_related_entry_graph(chunks=entries)
        diagram_map = entry_diagram_sidecars(self.cache.cwd)
        bundle = (entries, graph, diagram_map)
        self._derived_memo = (generation, bundle)
        return bundle

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
                cwd=self.cache.cwd,
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
        chunks = _filter_chunks(
            chunks, agent=agent, user=user, date_from=date_from, date_to=date_to, topic=topic, cwd=self.cache.cwd
        )
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
        # Augmented entries + related graph from the shared per-generation
        # derived bundle (same augmentation as graph()), so the reader's inverse
        # edges (superseded_by/evolved_by) agree with the Trail - without
        # re-reading sidecars and re-augmenting on every request.
        entries, graph, diagram_map = self._derived()
        selected = next((chunk for chunk in self.cache.chunks() if chunk.chunk_id == chunk_id), None)
        if selected is None:
            selected = next((chunk for chunk in entries if chunk.entry_id == chunk_id), None)
        if selected is None:
            raise KeyError(chunk_id)
        node = graph.get(selected.entry_id or "")
        sidecar = diagram_map.get(selected.entry_id or "")
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
        # Distinct from the authoring commit above: the merge commit whose
        # Memory-Entry trailer landed this entry on the trunk ("Merged to main
        # by" in the reader). None for unmerged or pre-trailer-era entries.
        merge_event = _entry_merge_map(self.cache.trailer_merges()).get(selected.entry_id or "")
        merged_by = (
            {
                "sha": merge_event["sha"],
                "short": merge_event["short"],
                "date": merge_event["date"],
                "subject": merge_event["subject"],
            }
            if merge_event
            else None
        )
        return {
            **_chunk_to_api(selected),
            "commit": commit or None,
            "commit_entry_ids": commit_entry_ids,
            "commit_entries": commit_entries,
            "commit_tracking": bool(commit_map),
            "merged_by": merged_by,
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
            cwd=self.cache.cwd,
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
        # Augmented all-entry chunks + diagram map from the shared per-generation
        # derived bundle. The link-sidecar augmentation is per-entry, so filtering
        # the already-augmented set yields the same entries (with the same edges)
        # as augmenting the filtered set - the agent/user/date/topic filters never
        # touch the augmented edge fields. Sidecar edits still show promptly:
        # a sidecar change bumps the generation, invalidating this bundle.
        all_entries, _all_graph, diagram_map = self._derived()
        entries = _filter_chunks(
            all_entries, agent=agent, user=user, date_from=date_from, date_to=date_to, topic=topic, cwd=self.cache.cwd
        )
        node_id = _graph_node_id_for(granularity)
        by_id = {node_id(chunk): chunk for chunk in entries if node_id(chunk)}
        edge_type_set = set(edge_types)
        edges = _graph_edges(entries, edge_type_set, node_id=node_id)
        graph = build_related_entry_graph(chunks=entries)
        connectivity = _connectivity_degrees(entries, node_id=node_id, graph=graph)
        importance = _importance_scores(entries, node_id=node_id, graph=graph)
        if entry_id and entry_id in by_id:
            visible_ids = _neighborhood(entry_id, edges, depth=max(depth, 1))
            limited_ids = set(visible_ids[: _limit(limit, maximum=1000)])
        else:
            # Overview (no focus entry): corpus order starts at the oldest
            # entries, which largely predate lifecycle links and authored
            # topics, so a positional cut used to yield an edgeless slice.
            # Prefer a connected subgraph instead, expanding from high-degree
            # seeds with newest-first tie-breaks.
            visible_ids = list(by_id)
            recency_rank = {
                item_id: rank
                for rank, (item_id, _chunk) in enumerate(
                    sorted(
                        by_id.items(),
                        key=lambda item: (_chunk_datetime(item[1]), item[1].start_line),
                        reverse=True,
                    )
                )
            }
            limited_ids = _overview_slice(
                visible_ids, edges, limit=_limit(limit, maximum=1000), recency_rank=recency_rank
            )
        inferred_main = self.cache.main_commit_entries()
        # Entry ids carrying an authored Class-2 decision-diagram sidecar, from
        # the per-generation derived bundle (a newly authored diagram bumps the
        # generation, so it still badges promptly).
        diagram_ids = set(diagram_map)
        displayed = [by_id[item_id] for item_id in visible_ids if item_id in limited_ids and item_id in by_id]
        nodes = [
            _graph_node(
                chunk,
                node_id=node_id(chunk),
                connectivity=connectivity.get(node_id(chunk), 0),
                importance_score=importance.get(node_id(chunk), 0.0),
                inferred_main=not chunk.branch and (chunk.entry_id or "") in inferred_main,
                has_diagram=(chunk.entry_id or "") in diagram_ids,
            )
            for chunk in displayed
        ]
        visible_edges = [
            edge
            for edge in edges
            if edge["source"] in limited_ids and edge["target"] in limited_ids and edge["type"] in edge_type_set
        ][: _limit(limit, maximum=1000)]
        # Commit-accurate merges: served on both the legacy /api surface and the
        # versioned /api/v1 surface (the v1 GraphResponse/TrailResponse models
        # formalize these keys as of the 2.18 polish; see models.py).
        merge_events = self.cache.trailer_merges()
        displayed_entry_ids = {chunk.entry_id for chunk in displayed if chunk.entry_id}
        merges = []
        for event in merge_events:
            ids = [eid for eid in event.get("entry_ids", ()) if eid in displayed_entry_ids]
            if ids:
                merges.append(
                    {
                        "sha": event["sha"],
                        "short": event["short"],
                        "date": event["date"],
                        "subject": event["subject"],
                        "entry_ids": ids,
                    }
                )
        entry_merge = _entry_merge_map(merge_events)
        # Branch closure semantics: a branch's lane closes with a merge only
        # when its NEWEST displayed entry was merged - if newer unmerged work
        # exists the branch is open and dangles (accurate), while its earlier
        # merges remain visible as trunk merge dots. The fork comes from the
        # OLDEST entry's merge event (its merge-base is where the branch first
        # left the trunk; later re-merges base off the previous merge).
        # estimated=True only when no entry of the branch has any trailer
        # event - the pre-trailer era, where the frontend keeps its positional
        # heuristic.
        branch_chunks: dict[str, list[MemoryChunk]] = {}
        for chunk in sorted(displayed, key=lambda chunk: (_chunk_datetime(chunk), chunk.start_line), reverse=True):
            branch = chunk.branch
            if not branch or branch in {"main", "master"}:
                continue
            branch_chunks.setdefault(branch, []).append(chunk)
        branches: dict[str, dict[str, Any]] = {}
        for branch, chunks_newest_first in branch_chunks.items():
            events = [
                entry_merge[chunk.entry_id]
                for chunk in chunks_newest_first
                if chunk.entry_id and chunk.entry_id in entry_merge
            ]
            newest_event = entry_merge.get(chunks_newest_first[0].entry_id or "")
            branches[branch] = {
                "merge": (
                    {
                        "sha": newest_event["sha"],
                        "short": newest_event["short"],
                        "date": newest_event["date"],
                        "subject": newest_event["subject"],
                    }
                    if newest_event
                    else None
                ),
                "fork": events[-1].get("fork") if events else None,
                "estimated": not events,
            }
        return {
            "entry_id": entry_id,
            "granularity": granularity,
            "nodes": nodes,
            "edges": visible_edges,
            "edge_types": sorted(edge_type_set),
            "merges": merges,
            "branches": branches,
        }

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


def _resolve_static_root(static_root: str | Path | None) -> Path | None:
    """Resolve a static-asset override to the directory holding index.html.

    Accepts either the static directory itself or a checkout root (a git
    worktree), in which case the packaged layout
    ``memory-trace/memory_trace/static`` is tried underneath. This is the
    verify-a-worktree's-UI path: the running server keeps its data source but
    serves that checkout's index.html/app.js/styles.css, replacing the
    copy-into-primary-then-restore dance. Raises when the override points at
    nothing servable - a typo must not silently fall back to packaged assets.
    """
    if static_root is None:
        return None
    candidate = Path(static_root).resolve()
    if (candidate / "index.html").is_file():
        return candidate
    nested = candidate / "memory-trace" / "memory_trace" / "static"
    if (nested / "index.html").is_file():
        return nested
    raise RuntimeError(
        f"static root {candidate} contains no index.html (looked in the directory itself and "
        "under memory-trace/memory_trace/static/)"
    )


def create_app(
    cwd: str | Path = ".",
    *,
    rebuild_cache: bool = False,
    static_root: str | Path | None = None,
) -> Any:
    try:
        from fastapi import FastAPI, HTTPException, Query
        from fastapi.responses import FileResponse, HTMLResponse
    except ModuleNotFoundError as exc:
        raise RuntimeError(missing_optional_dependency_hint()) from exc

    cache = TraceCache(cwd)
    if rebuild_cache:
        cache.rebuild()
    service = TraceService(cache)
    app = FastAPI(title="Memory Trace", version="1.0")

    static_dir = _resolve_static_root(static_root or os.environ.get("MEMORY_TRACE_STATIC_ROOT"))

    def _static_file(*parts: str) -> Any:
        if static_dir is not None:
            override = static_dir.joinpath(*parts)
            if override.is_file():
                return override
        return resources.files("memory_trace").joinpath("static", *parts)

    def _asset_version() -> str:
        # Serve-time cache busting: the ?v= tags in index.html are rewritten
        # per request with a content hash of the two mutable assets, so a
        # changed app.js/styles.css can never be masked by a stale browser
        # cache and no manual tag bump exists to forget. Recomputed per page
        # load (two small file reads) so even a same-process asset swap - the
        # static-root override pointing at an actively edited worktree - stays
        # correct without a restart.
        digest = hashlib.sha256()
        for name in ("app.js", "styles.css"):
            try:
                digest.update(_static_file(name).read_bytes())
            except OSError:
                pass
        return digest.hexdigest()[:10]

    def _benchmark_asset_version() -> str:
        digest = hashlib.sha256()
        for name in ("renderer-benchmark.js", "renderer-benchmark.css"):
            try:
                digest.update(_static_file(name).read_bytes())
            except OSError:
                pass
        return digest.hexdigest()[:10]

    # Worktree switching: one running Trace can show each on-device worktree's
    # branch-specific memory. The launch checkout is the default; other
    # worktrees get a lazily built, cached TraceService the first time they are
    # requested. Services are keyed by resolved path and only paths git reports
    # as worktrees of this repo are ever served (no arbitrary-path reads).
    launch_path = cache.cwd
    worktree_services: dict[Path, TraceService] = {launch_path: service}
    worktree_lock = threading.Lock()

    def worktree_entries() -> list[dict[str, Any]]:
        entries = list_worktrees(launch_path)
        if not entries:
            return [{"path": str(launch_path), "branch": None, "head": None, "is_primary": True}]
        return entries

    def service_for(worktree: str | None) -> TraceService:
        if not worktree:
            return service
        target = Path(worktree).resolve()
        if target == launch_path:
            return service
        known = {Path(entry["path"]).resolve() for entry in worktree_entries()}
        if target not in known:
            raise HTTPException(status_code=404, detail="unknown worktree")
        with worktree_lock:
            existing = worktree_services.get(target)
            if existing is None:
                wt_cache = TraceCache(target)
                wt_cache.rebuild()
                existing = TraceService(wt_cache)
                worktree_services[target] = existing
            return existing

    @app.get("/", response_class=HTMLResponse)
    def index() -> Any:
        text = _static_file("index.html").read_text(encoding="utf-8")
        text = re.sub(r"\?v=[^\"']+", f"?v={_asset_version()}", text)
        return HTMLResponse(text)

    @app.get("/assets/{name}")
    def asset(name: str) -> Any:
        if name not in {"app.js", "styles.css"}:
            raise HTTPException(status_code=404, detail="asset not found")
        return FileResponse(_static_file(name))

    @app.get("/next", response_class=HTMLResponse)
    def next_index() -> Any:
        # The React shell is additive while it earns parity. Its Vite output
        # has content-addressed asset names, so the document itself can be
        # served directly without the legacy app's mutable-asset rewrite.
        return HTMLResponse(_static_file("react", "index.html").read_text(encoding="utf-8"))

    @app.get("/assets/react/{asset_path:path}")
    def next_asset(asset_path: str) -> Any:
        # Never turn the package/static-root route into arbitrary file access.
        relative = Path(asset_path)
        if not asset_path or relative.is_absolute() or ".." in relative.parts:
            raise HTTPException(status_code=404, detail="asset not found")
        target = _static_file("react", *relative.parts)
        if not target.is_file():
            raise HTTPException(status_code=404, detail="asset not found")
        return FileResponse(target)

    @app.get("/benchmarks/renderer", response_class=HTMLResponse)
    def renderer_benchmark() -> Any:
        text = _static_file("benchmark.html").read_text(encoding="utf-8")
        text = re.sub(r"\?v=[^\"']+", f"?v={_benchmark_asset_version()}", text)
        return HTMLResponse(text)

    @app.get("/assets/benchmark/{name}")
    def benchmark_asset(name: str) -> Any:
        if name not in {"renderer-benchmark.js", "renderer-benchmark.css"}:
            raise HTTPException(status_code=404, detail="asset not found")
        return FileResponse(_static_file(name))

    @app.get("/assets/fonts/{name}")
    def asset_font(name: str) -> Any:
        # Self-hosted type pairing (OFL, license files ship alongside the
        # woff2s): no CDN call, Trace stays fully local/offline.
        if name not in {"inter-var.woff2", "space-grotesk-var.woff2"}:
            raise HTTPException(status_code=404, detail="asset not found")
        return FileResponse(_static_file("fonts", name), media_type="font/woff2")

    @app.get("/api/worktrees")
    def api_worktrees() -> dict[str, Any]:
        out = []
        for entry in worktree_entries():
            path = str(Path(entry["path"]).resolve())
            branch = entry.get("branch")
            out.append(
                {
                    "id": path,
                    "path": path,
                    "branch": branch,
                    "label": branch or f"{Path(path).name} (detached)",
                    "is_primary": bool(entry.get("is_primary")),
                    "is_default": Path(path).resolve() == launch_path,
                }
            )
        return {"worktrees": out, "default": str(launch_path)}

    @app.get("/api/runtime")
    def api_runtime(worktree: str | None = None) -> dict[str, Any]:
        return service_for(worktree).runtime()

    @app.get("/api/facets")
    def api_facets(worktree: str | None = None) -> dict[str, Any]:
        return service_for(worktree).facets()

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
        worktree: str | None = None,
    ) -> dict[str, Any]:
        return service_for(worktree).search(
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
    def api_chunk(chunk_id: str, worktree: str | None = None) -> dict[str, Any]:
        try:
            return service_for(worktree).chunk(chunk_id)
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
        worktree: str | None = None,
    ) -> dict[str, Any]:
        return service_for(worktree).timeline(
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
        worktree: str | None = None,
    ) -> dict[str, Any]:
        return service_for(worktree).graph(
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

    # Versioned contract (roadmap Phase 1): same TraceService, same params,
    # response_model-validated/typed. The legacy /api/* routes above are
    # untouched and keep serving the vanilla frontend unchanged - v1 is
    # additive, not a replacement, so a future React client has something
    # stable to build against. /api/timeline has no v1 counterpart: Trail is
    # its designated successor (roadmap Phase 4) and nothing consumes it.
    from .models import ChunkResponse, Facets, GraphResponse, RendererGraphResponse, RuntimeInfo, SearchResponse, TrailResponse

    @app.get("/api/v1/runtime", response_model=RuntimeInfo)
    def v1_runtime() -> dict[str, Any]:
        return service.runtime()

    @app.get("/api/v1/facets", response_model=Facets)
    def v1_facets() -> dict[str, Any]:
        return service.facets()

    @app.get("/api/v1/search", response_model=SearchResponse)
    def v1_search(
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

    @app.get("/api/v1/chunks/{chunk_id:path}", response_model=ChunkResponse)
    def v1_chunk(chunk_id: str) -> dict[str, Any]:
        try:
            return service.chunk(chunk_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="chunk not found") from None

    @app.get("/api/v1/graph", response_model=GraphResponse)
    def v1_graph(
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

    @app.get("/api/v1/graph/projection", response_model=RendererGraphResponse)
    def v1_renderer_graph(
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
        return project_trace_graph(
            service.graph(
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
        )

    @app.get("/api/v1/trail", response_model=TrailResponse)
    def v1_trail(
        entry_id: str | None = None,
        depth: int = 1,
        limit: int = 1000,
        agent: str | None = None,
        user: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        topic: str | None = None,
    ) -> dict[str, Any]:
        # Fixed to the Trail's own edge set (app.js TRAIL_EDGE_TYPES) - the
        # Trail is a dedicated product surface, not a parameterization of the
        # general graph, so its contract doesn't expose edge_types at all.
        return service.graph(
            entry_id=entry_id,
            depth=depth,
            edge_types=("branch", "supersedes", "evolves", "related"),
            limit=limit,
            granularity="entry",
            agent=agent,
            user=user,
            date_from=date_from,
            date_to=date_to,
            topic=topic,
        )

    return app


def run_server(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        print(missing_optional_dependency_hint(), file=os.sys.stderr)
        return 1
    try:
        app = create_app(args.cwd, rebuild_cache=args.rebuild_cache, static_root=getattr(args, "static_root", None))
    except RuntimeError as exc:
        print(str(exc), file=os.sys.stderr)
        return 1
    port = int(args.port)
    if port == 0:
        port = _free_port(args.host)
    url = f"http://{args.host}:{port}"
    if not args.no_open and not os.environ.get("MEMORY_SEED_LENSE_SKIP_BROWSER"):
        if getattr(args, "open_both", False):
            webbrowser.open(url, new=2)
            webbrowser.open(f"{url}/next", new=2)
        else:
            webbrowser.open(url)
    print(f"Memory Trace serving {Path(args.cwd).resolve()} at {url}")
    uvicorn.run(app, host=args.host, port=port, log_level="info")
    return 0


def _file_row(root: Path, path: Path) -> tuple[str, int, int]:
    stat = path.stat()
    return (path.relative_to(root).as_posix(), stat.st_mtime_ns, stat.st_size)


def _tracked_document_paths(runtime: Any) -> list[Path]:
    """Every file whose content feeds a read result: session documents plus link
    and diagram sidecars. Sidecars carry lifecycle edges and diagram badges the
    reader/graph show, so a change to one must invalidate the projection.

    On git this is already caught (sidecars live under the ``.memory-seed/sessions``
    pathspec the freshness check scopes to); enumerating them here makes the
    no-git mtime scan catch them too - so ``rebuilt_at`` is a complete generation
    over ALL inputs, which is what lets the sidecar-derived read structures be
    memoized safely instead of re-read per request."""
    sessions = runtime.memory_dir / "sessions"
    return (
        [doc.path for doc in iter_session_documents(sessions)]
        + [doc.path for doc in iter_link_sidecar_documents(sessions)]
        + [doc.path for doc in iter_diagram_sidecar_documents(sessions)]
    )


def _first_parent_main_shas(root: Path) -> set[str]:
    """Commit SHAs on the trunk's first-parent history. Work committed
    directly on main (the pre-branching era) lives here; branch work reaches
    main only through merge commits, which first-parent traversal skips.
    Fails open to an empty set without git."""
    for ref in ("main", "master", "HEAD"):
        try:
            proc = subprocess.run(
                ["git", "-C", str(root), "rev-list", "--first-parent", ref],
                capture_output=True,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired):
            return set()
        if proc.returncode == 0:
            return set(proc.stdout.decode("utf-8", errors="replace").split())
    return set()


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


def _first_parent_trailer_commits(root: Path) -> list[dict[str, Any]]:
    """Merge-commit ground truth for the Trail: trunk first-parent commits
    carrying ``Memory-Entry:`` trailers, newest-first.

    ``session merge-branch`` stamps one trailer per merged entry on the merge
    commit - the only place the entry/commit join can be recorded atomically,
    since an entry cannot contain the SHA of a commit that hashes over it. For
    true merge commits (>=2 parents) ``fork`` is the parents' merge-base; a
    non-merge commit carrying a trailer keeps ``fork: None``. Fails open to an
    empty list without git.
    """
    for ref in ("main", "master", "HEAD"):
        try:
            proc = subprocess.run(
                # Read the FULL body (%B), NUL-terminated per commit (-z), and scan
                # every `Memory-Entry:` line ourselves - NOT git's %(trailers:...),
                # which only parses the final contiguous trailer block. A blank
                # line (or an interleaved non-Memory-Entry trailer) between
                # Memory-Entry lines splits the block, and %(trailers:...) would
                # silently drop every earlier line - losing a merge's own branch
                # entry, which downgrades the branch to a positional estimate
                # (rendered parallel instead of at its real fork/merge). Scanning
                # the body is layout-agnostic and repairs already-committed merges.
                [
                    "git", "-C", str(root), "log", "--first-parent", ref, "-z",
                    "--format=%H%x1f%h%x1f%cI%x1f%P%x1f%s%x1f%B",
                ],
                capture_output=True,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired):
            return []
        if proc.returncode != 0:
            continue
        events: list[dict[str, Any]] = []
        for record in proc.stdout.decode("utf-8", errors="replace").split("\x00"):
            if "\x1f" not in record:
                continue
            sha, short, date, parents, subject, body = (record.split("\x1f", 5) + [""] * 6)[:6]
            entry_ids: list[str] = []
            for raw in body.splitlines():
                stripped = raw.strip()
                if stripped.startswith("Memory-Entry:"):
                    value = stripped[len("Memory-Entry:"):].strip()
                    if value and value not in entry_ids:
                        entry_ids.append(value)
            if not entry_ids:
                continue
            parent_list = parents.split()
            events.append(
                {
                    "sha": sha,
                    "short": short,
                    "date": date,
                    "subject": subject,
                    "entry_ids": entry_ids,
                    "fork": _merge_fork_point(root, parent_list[0], parent_list[1]) if len(parent_list) >= 2 else None,
                }
            )
        return events
    return []


def _merge_fork_point(root: Path, parent_a: str, parent_b: str) -> dict[str, str] | None:
    """Where the merged branch left the trunk: the merge-base of the merge
    commit's parents. None when the base cannot be resolved (shallow clone,
    unrelated histories) - callers fall back to the positional estimate."""
    try:
        base = subprocess.run(
            ["git", "-C", str(root), "merge-base", parent_a, parent_b],
            capture_output=True,
            timeout=30,
        )
        if base.returncode != 0:
            return None
        sha = base.stdout.decode("utf-8", errors="replace").strip()
        if not sha:
            return None
        shown = subprocess.run(
            ["git", "-C", str(root), "show", "-s", "--format=%H%x1f%h%x1f%cI", sha],
            capture_output=True,
            timeout=30,
        )
        if shown.returncode != 0:
            return None
        parts = (shown.stdout.decode("utf-8", errors="replace").strip().split("\x1f") + ["", ""])[:3]
        return {"sha": parts[0], "short": parts[1], "date": parts[2]}
    except (OSError, subprocess.TimeoutExpired):
        return None


def _entry_merge_map(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """entry_id -> the merge event that landed it on the trunk. Events arrive
    newest-first and assignment overwrites, so the OLDEST merge wins - the same
    attribution rule as _entry_commit_map (re-merges never steal credit)."""
    mapping: dict[str, dict[str, Any]] = {}
    for event in events:
        for entry_id in event.get("entry_ids", ()):
            mapping[entry_id] = event
    return mapping


def _augment_with_link_sidecars(entries: Sequence[MemoryChunk], cwd: str | Path) -> list[MemoryChunk]:
    """Union each entry's YAML-declared lifecycle edges with any authored later
    in a link sidecar (see ``entry_link_sidecars``). The sidecar is the
    append-only enrichment layer: write-time YAML stays canonical, late-found
    ``supersedes``/``evolves``/``related_entries`` ride alongside. Augments the
    INPUT chunk list so ``build_related_entry_graph``'s inverse edges
    (superseded_by/evolved_by) and ``_graph_edges`` both pick them up with no
    change of their own. ``cwd`` must be the per-worktree path so the switcher
    reads each branch's own sidecars. Fails open (returns ``entries``) when no
    sidecars exist."""
    sidecars = entry_link_sidecars(cwd)
    if not sidecars:
        return list(entries)

    def union(base: tuple[str, ...], extra: Iterable[str], entry_id: str | None) -> tuple[str, ...]:
        merged = list(base)
        for ref in extra:
            if ref and ref != entry_id and ref not in merged:
                merged.append(ref)
        return tuple(merged)

    augmented: list[MemoryChunk] = []
    for chunk in entries:
        extra = sidecars.get(chunk.entry_id or "")
        if not extra:
            augmented.append(chunk)
            continue
        augmented.append(
            replace(
                chunk,
                supersedes=union(chunk.supersedes, extra.get("supersedes", ()), chunk.entry_id),
                evolves=union(chunk.evolves, extra.get("evolves", ()), chunk.entry_id),
                related_entries=union(chunk.related_entries, extra.get("related_entries", ()), chunk.entry_id),
            )
        )
    return augmented


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
        "supersedes",
        "evolves",
        "commits",
        "topics",
        "sections",
    ):
        data[key] = tuple(data.get(key) or ())
    data["continuity"] = tuple(
        ContinuityBlock(
            kind=block.get("kind", ""),
            from_ref=block.get("from_ref") or block.get("from", ""),
            to_ref=block.get("to_ref") or block.get("to") or None,
        )
        for block in (data.get("continuity") or ())
    )
    if data.get("entry_line_range"):
        data["entry_line_range"] = tuple(data["entry_line_range"])
    return MemoryChunk(**data)


def _continuity_to_api(chunk: MemoryChunk) -> list[dict[str, Any]]:
    return [
        {"kind": block.kind, "from": block.from_ref, "to": block.to_ref}
        for block in chunk.continuity
    ]


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
        "continuity": _continuity_to_api(chunk),
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
    cwd: str | Path | None = None,
) -> list[MemoryChunk]:
    start = _parse_date(date_from)
    end = _parse_date(date_to)
    # Vocabulary-aware topic filter (topic-neighbourhoods plan Phase 4): expand
    # the requested slug to its canonical form plus every alias from
    # topics.yaml, so filtering by a canonical topic matches entries that stored
    # an alias and vice versa - the same expansion the core retrieval/MCP paths
    # use. Fail-open: an unknown name (a derived hashtag on an old entry, or a
    # project with no topics.yaml) passes through as an exact-match set, so
    # pre-vocabulary filtering is unchanged.
    if topic:
        topic_match = expand_topic_filter(cwd, [topic]) if cwd is not None else {topic}
    else:
        topic_match = None
    return [
        chunk
        for chunk in chunks
        if (not agent or chunk.agent_type == agent or chunk.agent_name == agent)
        and (not user or chunk.user == user)
        and (start is None or chunk.session_date >= start)
        and (end is None or chunk.session_date <= end)
        and (topic_match is None or bool(topic_match & set(_topics(chunk))))
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


def _overview_slice(
    candidate_ids: Sequence[str],
    edges: Sequence[dict[str, str]],
    *,
    limit: int,
    recency_rank: Mapping[str, int],
) -> set[str]:
    """Pick the overview node slice by connectivity instead of corpus order.

    Greedy deterministic expansion: seed with the highest-degree node, then
    repeatedly take the best-ranked node adjacent to the current selection,
    starting a new component from the next-best seed only when the frontier is
    exhausted. Ranking is (degree desc, newest first, node id), a total order,
    so the same corpus and edge set always select the same slice. Isolated
    nodes only enter once every reachable connected node is in.
    """
    if len(candidate_ids) <= limit:
        return set(candidate_ids)
    candidates = set(candidate_ids)
    adjacency: dict[str, set[str]] = {item_id: set() for item_id in candidates}
    for edge in edges:
        source, target = edge["source"], edge["target"]
        if source in candidates and target in candidates and source != target:
            adjacency[source].add(target)
            adjacency[target].add(source)

    def rank(item_id: str) -> tuple[int, int, str]:
        return (-len(adjacency[item_id]), recency_rank.get(item_id, 0), item_id)

    seeds = sorted(candidates, key=rank)
    seed_index = 0
    selected: set[str] = set()
    frontier: set[str] = set()
    while len(selected) < limit:
        if frontier:
            item_id = min(frontier, key=rank)
            frontier.remove(item_id)
        else:
            while seed_index < len(seeds) and seeds[seed_index] in selected:
                seed_index += 1
            if seed_index >= len(seeds):
                break
            item_id = seeds[seed_index]
            seed_index += 1
        selected.add(item_id)
        frontier |= adjacency[item_id] - selected
    return selected


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
    inferred_main: bool = False,
    has_diagram: bool = False,
) -> dict[str, Any]:
    # inferred_main: no branch was recorded, but the entry's capturing commit
    # sits on main's first-parent history - committed directly on main, so it
    # joins the trunk. Recorded branches are never overridden; the raw
    # metadata surface keeps showing the recorded (null) value.
    return {
        "id": node_id or chunk.entry_id or chunk.chunk_id,
        "chunk_id": chunk.chunk_id,
        "entry_id": chunk.entry_id,
        "title": chunk.title,
        "date": chunk.session_date.isoformat(),
        "datetime": chunk.entry_datetime.isoformat() if chunk.entry_datetime else None,
        "branch": chunk.branch or ("main" if inferred_main else None),
        "branch_inferred": inferred_main,
        "agent": chunk.agent_type or chunk.agent_name or "unknown",
        "topics": _topics(chunk),
        "granularity": chunk.granularity,
        "continuity": _continuity_to_api(chunk),
        "connectivity": connectivity,
        "importance_score": round(importance_score, 3),
        # Class-2 decision-diagram sidecar presence (session-decision-diagrams
        # plan). A cheap boolean so the Trail/Graph can badge entries that carry
        # an authored reasoning diagram; the diagram source itself is fetched
        # lazily from the chunk endpoint when the badge is engaged (the graph
        # payload stays lean across hundreds of nodes). Legacy /api surface only
        # for now - the v1 GraphNode model strips it until the badge UI is
        # polished, matching the merge-geometry vanilla-first precedent.
        "has_diagram": has_diagram,
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
    """Effective display topics for an entry (topic-neighbourhoods plan Phase 4).

    Prefer the authored controlled-vocabulary ``topics:`` field; fall back to the
    hashtag/heading-derived axes (``tags`` | ``contexts``) only for entries that
    predate the indexed field. The two are never mixed - an entry carrying any
    authored topic shows exactly its authored slugs, so the facet, chips, topic
    chains, and filter all speak the controlled vocabulary once an entry adopts
    it. This single chokepoint feeds facets, nodes, chunk payloads, topic edge
    chains, and the topic filter."""
    if chunk.topics:
        return sorted(set(chunk.topics))
    return sorted(set(chunk.tags) | set(chunk.contexts))


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
