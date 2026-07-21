from __future__ import annotations

import argparse
import hashlib
import re
import json
import os
import shutil
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
# v2: sha-keyed git-derivation tables (fork_points, commit_parents,
# changed_paths, file_entries) + trunk watermark meta + lazy file index.
PROJECTION_SCHEMA_VERSION = 2


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


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    """True iff ``ancestor`` is an ancestor of ``descendant`` - the test that
    separates a normal forward move (reconcilable) from a rebase/rewrite/gc
    (full rebuild). Any git failure counts as not-an-ancestor, failing toward
    the full rebuild."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, descendant],
            capture_output=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def _changed_names(root: Path, old: str, new: str, pathspec: str) -> list[str] | None:
    """Paths under ``pathspec`` that differ between two commits. ``--no-renames``
    keeps a rename visible as delete+add so BOTH paths invalidate. None on git
    failure (caller falls back to a full rebuild)."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "diff", "--name-only", "--no-renames", f"{old}..{new}", "--", pathspec],
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return [line.strip() for line in proc.stdout.decode("utf-8", errors="replace").splitlines() if line.strip()]


def _signature_paths(signature: str) -> set[str]:
    """The dirty paths recorded in a working-tree signature (see
    _working_tree_signature: a JSON list of (path, mtime, size) triples)."""
    if not signature:
        return set()
    try:
        entries = json.loads(signature)
    except (ValueError, TypeError):
        return set()
    paths: set[str] = set()
    for item in entries:
        if isinstance(item, (list, tuple)) and item and isinstance(item[0], str):
            paths.add(item[0])
    return paths


def _session_documents_for(
    root: Path, sessions_dir: Path, sessions_pathspec: str, changed: set[str]
) -> tuple[set[str], list[Path]]:
    """Classify changed repo-relative paths into (affected session dates,
    session documents to reparse).

    Layout knowledge is delegated to the canonical ``iter_session_documents``
    (flat, month-dir and per-user-day layouts all exist), never re-derived
    from path patterns. A changed path that is a current session document maps
    to its own date; a deleted path recovers its date from the filename or
    parent directory. Every affected date then reparses ALL of its current
    documents - chunks are deleted per date, and a date can span several
    documents (per-user layout) or lose one (deletion) without the others
    having changed. Sidecars (links/, diagrams/) are not session documents:
    they produce no chunk rows and are excluded by the canonical iterator."""
    prefix = sessions_pathspec.rstrip("/") + "/"
    current = {doc.path.resolve(): doc for doc in iter_session_documents(sessions_dir)}
    dates: set[str] = set()
    for rel in changed:
        posix = rel.replace("\\", "/")
        if not posix.startswith(prefix) or not posix.endswith(".md"):
            continue
        absolute = root / posix
        doc = current.get(absolute.resolve())
        if doc is not None:
            dates.add(doc.session_date)
            continue
        if absolute.exists():
            continue  # exists but is not a session document (e.g. a sidecar)
        # Deleted: recover the session date from the path shape - the stem
        # (flat/month layouts) or the parent directory (per-user-day layout).
        for candidate in (Path(posix).stem, Path(posix).parent.name):
            try:
                datetime.strptime(candidate, "%Y-%m-%d")
            except ValueError:
                continue
            dates.add(candidate)
            break
    reparse = [doc.path for doc in current.values() if doc.session_date in dates]
    return dates, reparse


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

    def _carryover_derivations(self) -> dict[str, Any]:
        """Immutable sha-keyed derivations from the previous projection, read
        before a full rebuild replaces it. A commit's parents, its changed
        paths and a merge's fork point never change for a given sha, so they
        survive rebuilds (including history rewrites - rewritten history mints
        NEW shas; stale keys are harmless, bounded garbage). Every value here
        is recomputable from git, so a missing/corrupt table just costs
        recomputation (contract G2)."""
        carry: dict[str, Any] = {
            "fork_points": {},
            "commit_parents": [],
            "changed_paths": [],
            "file_entries": [],
            "file_index_watermark": None,
        }
        if not self.db_path.exists():
            return carry
        try:
            with sqlite3.connect(self.db_path) as conn:
                for key, sql in (
                    ("fork_points", "select merge_sha, fork_json from fork_points"),
                    ("commit_parents", "select sha, short, date, parents from commit_parents"),
                    ("changed_paths", "select sha, path from changed_paths"),
                    ("file_entries", "select path, entry_id from file_entries"),
                ):
                    try:
                        rows = conn.execute(sql).fetchall()
                    except sqlite3.Error:
                        continue  # pre-v2 cache: table absent, nothing to carry
                    if key == "fork_points":
                        carry[key] = {sha: json.loads(blob) for sha, blob in rows}
                    else:
                        carry[key] = rows
                try:
                    row = conn.execute("select value from meta where key='file_index_watermark'").fetchone()
                    carry["file_index_watermark"] = row[0] if row else None
                except sqlite3.Error:
                    pass
        except sqlite3.Error:
            return carry
        return carry

    def _rebuild_locked(self) -> None:
        self._ensure_cache_parent()
        carry = self._carryover_derivations()
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
            root = self.runtime.workspace_root
            file_rows = [
                _file_row(root, path)
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
                [_chunk_row(chunk) for chunk in chunks],
            )
            conn.execute(
                "insert into meta(key, value) values('rebuilt_at', ?)",
                (str(time.time_ns()),),
            )
            conn.execute(
                "insert into meta(key, value) values('runtime_root', ?)",
                (str(root),),
            )
            commit_map = _entry_commit_map(root)
            conn.execute(
                "insert into meta(key, value) values('entry_commits', ?)",
                (json.dumps(commit_map),),
            )
            # Evidence-based main attribution: an entry with no recorded
            # branch whose capturing commit sits on the trunk's first-parent
            # history was committed directly on main - proven, not assumed.
            main_shas = _first_parent_main_shas(root)
            conn.execute(
                "insert into meta(key, value) values('main_commit_entries', ?)",
                (json.dumps(sorted(eid for eid, info in commit_map.items() if info.get("sha") in main_shas)),),
            )
            # Merge-commit ground truth for the Trail: Memory-Entry trailers on
            # trunk first-parent commits. Fork points come from the carryover
            # table first, then ONE bulk commit-graph pass for whatever is
            # genuinely new - never a merge-base/show subprocess per merge.
            trunk = _trunk_ref_and_sha(root)
            trunk_ref, trunk_sha = trunk if trunk else ("", "")
            raw_events = _trailer_walk(root, trunk_ref or None) if trunk else None
            commit_graph: dict[str, dict[str, Any]] = {}
            merge_events: list[dict[str, Any]] = []
            if raw_events:
                commit_graph = _commit_graph(root, trunk_ref)
                merge_events, _new_forks = _resolve_event_forks(
                    root,
                    raw_events,
                    known_fork_points=carry["fork_points"],
                    commit_graph=commit_graph,
                    trunk_ref=trunk_ref,
                )
            conn.execute(
                "insert into meta(key, value) values('trailer_merges', ?)",
                (json.dumps(merge_events),),
            )
            # Persist the immutable derivations: carryover plus everything this
            # build resolved or harvested. Unresolvable (None) fork points are
            # deliberately NOT persisted so a later deepened clone can recover
            # them without deleting the cache.
            fork_rows = {sha: fork for sha, fork in carry["fork_points"].items() if fork is not None}
            fork_rows.update({sha: fork for sha, fork in _FORK_POINT_MEMO.items() if fork is not None})
            conn.executemany(
                "insert or replace into fork_points(merge_sha, fork_json) values(?, ?)",
                [(sha, json.dumps(fork)) for sha, fork in fork_rows.items()],
            )
            parent_rows = {row[0]: tuple(row) for row in carry["commit_parents"]}
            parent_rows.update(
                {
                    sha: (sha, info["short"], info["date"], " ".join(info["parents"]))
                    for sha, info in commit_graph.items()
                }
            )
            conn.executemany(
                "insert or replace into commit_parents(sha, short, date, parents) values(?, ?, ?, ?)",
                list(parent_rows.values()),
            )
            conn.executemany(
                "insert or ignore into changed_paths(sha, path) values(?, ?)",
                carry["changed_paths"],
            )
            # The file-entry index is LAZY: a full rebuild never computes it.
            # Prior rows carry over with their watermark; the accessor
            # revalidates against the current trunk and advances or rebuilds
            # on the first File-mode request that actually needs it.
            conn.executemany(
                "insert or ignore into file_entries(path, entry_id) values(?, ?)",
                carry["file_entries"],
            )
            if carry["file_index_watermark"]:
                conn.execute(
                    "insert into meta(key, value) values('file_index_watermark', ?)",
                    (carry["file_index_watermark"],),
                )
            conn.execute("insert into meta(key, value) values('trunk_ref', ?)", (trunk_ref,))
            conn.execute("insert into meta(key, value) values('trunk_watermark', ?)", (trunk_sha,))
            # Derived-projection provenance (contract G4/G5): the schema version
            # (rebuild on bump) and the build watermark (HEAD) + dirty-file
            # signature, so a warm start proves "nothing changed" from git in
            # O(changes) instead of scanning the whole corpus. Empty watermark =
            # built without git; ensure_current then uses the mtime fallback.
            head = _git_head(root)
            conn.execute(
                "insert into meta(key, value) values('schema_version', ?)",
                (str(PROJECTION_SCHEMA_VERSION),),
            )
            conn.execute(
                "insert into meta(key, value) values('build_watermark', ?)",
                (head or "",),
            )
            signature = (
                _working_tree_signature(root, self._sessions_pathspec())
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
        if not self._atomic_swap(tmp):
            # Swap denied even after retries: fall back to an isolated
            # temporary cache and rebuild there (never against the shared
            # file another process may hold open).
            if self._is_temporary_cache():
                raise PermissionError(f"cannot replace projection at {self.db_path}")
            self._use_temporary_cache()
            self._rebuild_locked()
            return
        # The swap succeeded: the parsed-chunk memo now describes the previous
        # projection, so drop it and bump the generation so the derived-bundle
        # memo invalidates too.
        self._chunks_memo = {}
        self._generation += 1

    def _atomic_swap(self, tmp: Path) -> bool:
        """Atomically publish ``tmp`` as the projection (contract G4). Windows:
        a reader connection that has not finished closing can hold the
        destination briefly; retry instead of failing, and never leave the tmp
        file behind. False when every retry was denied."""
        try:
            for attempt in range(5):
                try:
                    os.replace(tmp, self.db_path)
                    return True
                except PermissionError:
                    if attempt == 4:
                        return False
                    time.sleep(0.1 * (attempt + 1))
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
        return False

    def _reconcile_locked(self) -> bool:
        """Incrementally advance the existing projection to the current repo
        state. True when the projection was brought current; False when
        incremental reconciliation does not apply and the caller must fall
        back to a full rebuild. Every ambiguity - rewritten history, a moved
        trunk that is not a fast-forward, a failed git read, a re-added entry
        id - fails toward the full rebuild, never toward serving stale or
        partial state. The update is built on a COPY of the projection and
        published with the same atomic swap as a full rebuild, so concurrent
        readers only ever observe the old or the new state."""
        if not self.db_path.exists() or self._is_temporary_cache():
            return False
        root = self.runtime.workspace_root
        try:
            with sqlite3.connect(self.db_path) as conn:
                meta = dict(
                    conn.execute(
                        "select key, value from meta where key in "
                        "('schema_version', 'build_watermark', 'dirty_signature', "
                        "'trunk_ref', 'trunk_watermark', 'entry_commits', 'file_index_watermark')"
                    ).fetchall()
                )
                has_merges = conn.execute("select 1 from meta where key='trailer_merges'").fetchone()
                known_forks = {
                    sha: json.loads(blob)
                    for sha, blob in conn.execute("select merge_sha, fork_json from fork_points")
                }
        except sqlite3.Error:
            return False
        if meta.get("schema_version") != str(PROJECTION_SCHEMA_VERSION) or not has_merges:
            return False
        old_head = meta.get("build_watermark") or ""
        if not old_head:
            return False  # built without git: the mtime world rebuilds fully
        head = _git_head(root)
        if head is None:
            return False
        if head != old_head and not _is_ancestor(root, old_head, head):
            return False  # rebase/rewrite/gc: reconcile cannot trust the range
        trunk = _trunk_ref_and_sha(root)
        if trunk is None:
            return False
        trunk_ref, trunk_sha = trunk
        old_trunk = meta.get("trunk_watermark") or ""
        if not old_trunk or meta.get("trunk_ref") != trunk_ref:
            return False
        if trunk_sha != old_trunk and not _is_ancestor(root, old_trunk, trunk_sha):
            return False
        signature = _working_tree_signature(root, self._sessions_pathspec())
        if signature is None:
            return False
        try:
            # -- Which source documents changed? Committed delta + files dirty
            # now + files dirty at the previous build (committing or reverting
            # a previously dirty file changes its content without appearing in
            # the new dirty set).
            changed_docs: set[str] = set()
            if head != old_head:
                names = _changed_names(root, old_head, head, self._sessions_pathspec())
                if names is None:
                    return False
                changed_docs.update(names)
            changed_docs.update(_signature_paths(signature))
            changed_docs.update(_signature_paths(meta.get("dirty_signature") or ""))

            # -- Entry attribution: advance over the new range only. A commit
            # in the range that re-adds an already-attributed entry id would
            # need the oldest-commit-wins comparison over full history, so
            # that exact (rare) case recomputes the whole map - still one
            # bounded git pass, never per-commit work.
            entry_map: dict[str, dict[str, str]] = json.loads(meta.get("entry_commits") or "{}")
            if head != old_head:
                range_map = _entry_commit_map(root, rev_range=f"{old_head}..{head}")
                if set(range_map) & set(entry_map):
                    entry_map = _entry_commit_map(root)
                else:
                    entry_map = {**entry_map, **range_map}
            main_shas = _first_parent_main_shas(root)
            main_entries = sorted(eid for eid, info in entry_map.items() if info.get("sha") in main_shas)

            # -- Trailer merges: the walk itself is one cheap git pass; fork
            # points come from the persisted table, so only merges new since
            # the last build cost anything (one shared commit-graph pass).
            raw_events = _trailer_walk(root, trunk_ref)
            if raw_events is None:
                return False
            merge_events, new_forks = _resolve_event_forks(
                root, raw_events, known_fork_points=known_forks, trunk_ref=trunk_ref
            )

            # -- Reparse only the changed session documents' chunks.
            affected_dates, reparse_paths = _session_documents_for(
                root, self.runtime.memory_dir / "sessions", self._sessions_pathspec(), changed_docs
            )
            new_chunks: list[MemoryChunk] = []
            if reparse_paths:
                new_chunks = [*extract_memory_chunks(self.cwd, granularity="entry", paths=reparse_paths)]
                reparse_ranges = {(c.chunk_id, c.start_line, c.end_line) for c in new_chunks}
                new_chunks.extend(
                    chunk
                    for chunk in extract_memory_chunks(self.cwd, granularity="section", paths=reparse_paths)
                    if (chunk.chunk_id, chunk.start_line, chunk.end_line) not in reparse_ranges
                )

            # -- File-entry index: only advanced when it was already built.
            file_index_update: dict[str, Any] | None = None
            fi_watermark = meta.get("file_index_watermark") or ""
            if fi_watermark and fi_watermark != trunk_sha:
                if not _is_ancestor(root, fi_watermark, trunk_sha):
                    return False
                range_expr = f"{fi_watermark}..{trunk_sha}"
                range_graph = _commit_graph(root, range_expr)
                range_changed = _changed_paths_bulk(root, range_expr)
                if range_changed is None:
                    return False
                file_index_update = {"graph": range_graph, "changed": range_changed}

            file_rows = [
                _file_row(root, path)
                for path in _tracked_document_paths(self.runtime)
            ]
        except (OSError, ValueError, KeyError, TypeError):
            return False

        # -- Publish: copy the projection, apply the delta in one transaction,
        # swap atomically. Same G4 guarantee as a full rebuild: readers only
        # ever see the old file or the new file, never a half-applied delta.
        tmp = self.db_path.with_name(f"{self.db_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            shutil.copyfile(self.db_path, tmp)
            conn = sqlite3.connect(tmp)
            try:
                if affected_dates:
                    conn.executemany(
                        "delete from chunks where session_date = ?",
                        [(date_text,) for date_text in sorted(affected_dates)],
                    )
                if new_chunks:
                    conn.executemany(
                        "insert or replace into chunks(chunk_id, granularity, entry_id, session_date, entry_datetime, json) values(?, ?, ?, ?, ?, ?)",
                        [_chunk_row(chunk) for chunk in new_chunks],
                    )
                conn.execute("delete from files")
                conn.executemany(
                    "insert into files(path, mtime_ns, size) values(?, ?, ?)",
                    file_rows,
                )
                conn.executemany(
                    "insert or replace into fork_points(merge_sha, fork_json) values(?, ?)",
                    [(sha, json.dumps(fork)) for sha, fork in new_forks.items() if fork is not None],
                )
                if file_index_update is not None:
                    conn.executemany(
                        "insert or replace into commit_parents(sha, short, date, parents) values(?, ?, ?, ?)",
                        [
                            (sha, info["short"], info["date"], " ".join(info["parents"]))
                            for sha, info in file_index_update["graph"].items()
                        ],
                    )
                    conn.executemany(
                        "insert or ignore into changed_paths(sha, path) values(?, ?)",
                        [
                            (sha, path)
                            for sha, paths in file_index_update["changed"].items()
                            for path in paths
                        ],
                    )
                    parents_of = {
                        sha: parents.split()
                        for sha, parents in conn.execute("select sha, parents from commit_parents")
                    }
                    changed_map: dict[str, list[str]] = {}
                    for sha, path in conn.execute("select sha, path from changed_paths"):
                        changed_map.setdefault(sha, []).append(path)
                    index = _file_entry_index_from_parts(entry_map, parents_of, changed_map)
                    conn.execute("delete from file_entries")
                    conn.executemany(
                        "insert into file_entries(path, entry_id) values(?, ?)",
                        [(path, eid) for path, ids in index.items() for eid in ids],
                    )
                    conn.execute(
                        "insert or replace into meta(key, value) values('file_index_watermark', ?)",
                        (trunk_sha,),
                    )
                for key, value in (
                    ("rebuilt_at", str(time.time_ns())),
                    ("entry_commits", json.dumps(entry_map)),
                    ("main_commit_entries", json.dumps(main_entries)),
                    ("trailer_merges", json.dumps(merge_events)),
                    ("trunk_ref", trunk_ref),
                    ("trunk_watermark", trunk_sha),
                    ("build_watermark", head),
                    ("dirty_signature", signature),
                ):
                    conn.execute("insert or replace into meta(key, value) values(?, ?)", (key, value))
                conn.commit()
            finally:
                conn.close()
            gc.collect()
            if not self._atomic_swap(tmp):
                return False
        except (OSError, sqlite3.Error):
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            return False
        self._chunks_memo = {}
        self._generation += 1
        return True

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
            # Normal freshness-driven updates reconcile incrementally when the
            # change is a plain forward move; an explicit rebuild() (the repair
            # path) and every reconcile-inapplicable case do the full build.
            if not force and self._reconcile_locked():
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

    def file_entry_index(self) -> dict[str, list[str]]:
        """path -> entry_ids, built LAZILY: ordinary Trail/Graph startup never
        pays for it. The first File-mode request harvests the two bulk git
        passes (commit graph + first-parent changed paths), persists the
        result keyed by the trunk watermark, and every later request - or
        process - reads the table. Concurrent first requests serialize on the
        rebuild lock, so exactly one of them builds."""
        self.ensure_current()
        index = self._read_file_entry_index()
        if index is not None:
            return index
        with self._rebuild_lock:
            index = self._read_file_entry_index()
            if index is not None:
                return index
            built = self._build_file_index_locked()
        return built if built is not None else {}

    def _read_file_entry_index(self) -> dict[str, list[str]] | None:
        """The persisted file-entry index, or None when it has not been built
        for the current trunk position (the caller then builds it)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                meta = dict(
                    conn.execute(
                        "select key, value from meta where key in ('file_index_watermark', 'trunk_watermark')"
                    ).fetchall()
                )
                if not meta.get("trunk_watermark"):
                    return {}  # built without git: no index exists or ever will
                if meta.get("file_index_watermark") != meta.get("trunk_watermark"):
                    return None
                rows = conn.execute("select path, entry_id from file_entries").fetchall()
        except sqlite3.Error:
            return None
        index: dict[str, list[str]] = {}
        for path, entry_id in rows:
            index.setdefault(path, []).append(entry_id)
        return {path: sorted(ids) for path, ids in index.items()}

    def _build_file_index_locked(self) -> dict[str, list[str]] | None:
        """Build (or advance) the file-entry index under the rebuild lock and
        persist it with the same copy-apply-swap pattern as reconciliation.
        Harvests reuse whatever commit_parents/changed_paths rows are already
        persisted - only genuinely unseen commits cost git work."""
        root = self.runtime.workspace_root
        trunk = _trunk_ref_and_sha(root)
        if trunk is None:
            return {}
        trunk_ref, trunk_sha = trunk
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("select value from meta where key='entry_commits'").fetchone()
                entry_map = json.loads(row[0]) if row else {}
                parents_of = {
                    sha: parents.split()
                    for sha, parents in conn.execute("select sha, parents from commit_parents")
                }
                changed_map: dict[str, list[str]] = {}
                for sha, path in conn.execute("select sha, path from changed_paths"):
                    changed_map.setdefault(sha, []).append(path)
        except sqlite3.Error:
            return None
        graph_harvest: dict[str, dict[str, Any]] = {}
        if not parents_of:
            graph_harvest = _commit_graph(root, trunk_ref)
            parents_of = {sha: info["parents"] for sha, info in graph_harvest.items()}
        changed_harvest = _changed_paths_bulk(root, trunk_ref) if not changed_map else None
        if changed_harvest is not None:
            changed_map = changed_harvest
        elif changed_map and trunk_sha not in parents_of:
            # Persisted rows exist but predate the current trunk tip (e.g. the
            # index was never built and reconciles never harvested): refresh
            # both maps fully rather than serve a partial index.
            graph_harvest = _commit_graph(root, trunk_ref)
            parents_of = {sha: info["parents"] for sha, info in graph_harvest.items()}
            changed_harvest = _changed_paths_bulk(root, trunk_ref)
            if changed_harvest is None:
                return None
            changed_map = changed_harvest
        index = _file_entry_index_from_parts(entry_map, parents_of, changed_map)
        tmp = self.db_path.with_name(f"{self.db_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            shutil.copyfile(self.db_path, tmp)
            conn = sqlite3.connect(tmp)
            try:
                if graph_harvest:
                    conn.executemany(
                        "insert or replace into commit_parents(sha, short, date, parents) values(?, ?, ?, ?)",
                        [
                            (sha, info["short"], info["date"], " ".join(info["parents"]))
                            for sha, info in graph_harvest.items()
                        ],
                    )
                if changed_harvest is not None:
                    conn.executemany(
                        "insert or ignore into changed_paths(sha, path) values(?, ?)",
                        [(sha, path) for sha, paths in changed_map.items() for path in paths],
                    )
                conn.execute("delete from file_entries")
                conn.executemany(
                    "insert into file_entries(path, entry_id) values(?, ?)",
                    [(path, eid) for path, ids in index.items() for eid in ids],
                )
                conn.execute(
                    "insert or replace into meta(key, value) values('file_index_watermark', ?)",
                    (trunk_sha,),
                )
                conn.commit()
            finally:
                conn.close()
            gc.collect()
            if not self._atomic_swap(tmp):
                return index  # serve the computed index even if persisting failed
        except (OSError, sqlite3.Error):
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            return index
        return index

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
                # Caches from before commit tracking lack these keys; rebuild
                # once. The file-entry index is deliberately NOT required: it
                # is lazy (built on first File-mode request), so its absence is
                # the normal state, not staleness.
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
        # The sha-keyed tables persist immutable git derivations (a commit's
        # parents, its first-parent changed paths, a merge's fork point) so
        # they are computed once per commit EVER, not once per process launch
        # or rebuild. All of it stays derived and rebuildable (contract G2):
        # deleting the cache only costs recomputation, never data.
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
            create table fork_points(merge_sha text primary key, fork_json text not null);
            create table commit_parents(sha text primary key, short text not null, date text not null, parents text not null);
            create table changed_paths(sha text not null, path text not null, primary key(sha, path));
            create table file_entries(path text not null, entry_id text not null, primary key(path, entry_id));
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
        entry_ids: Sequence[str] | None = None,
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
        if entry_ids is not None:
            # File mode: an exact, pre-resolved membership set (every entry
            # whose landing commit touched a given file), not a neighborhood
            # expansion from one focus entry. An empty list is a real answer
            # (an unrecognized or untouched path), not "no filter requested" -
            # it must not fall through to the overview branch below.
            visible_ids = [item_id for item_id in entry_ids if item_id in by_id]
            limited_ids = set(visible_ids[: _limit(limit, maximum=1000)])
        elif entry_id and entry_id in by_id:
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
                # ensure_current, not rebuild: a worktree whose persisted
                # projection matches its git watermark warm-starts in
                # milliseconds; only genuinely changed corpora rebuild (and the
                # fork-point memo makes that rebuild pay only for the
                # worktree's own divergence from the shared trunk).
                wt_cache.ensure_current()
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
    from .models import ChunkResponse, Facets, GraphResponse, RendererGraphResponse, RuntimeInfo, SearchResponse, TrailResponse, WorktreesResponse

    @app.get("/api/v1/worktrees", response_model=WorktreesResponse)
    def v1_worktrees() -> dict[str, Any]:
        # Same enumeration as the legacy surface, typed: every git worktree of
        # the launch repository is a switchable corpus view.
        return api_worktrees()

    @app.get("/api/v1/runtime", response_model=RuntimeInfo)
    def v1_runtime(worktree: str | None = None) -> dict[str, Any]:
        return service_for(worktree).runtime()

    @app.get("/api/v1/facets", response_model=Facets)
    def v1_facets(worktree: str | None = None) -> dict[str, Any]:
        return service_for(worktree).facets()

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

    @app.get("/api/v1/chunks/{chunk_id:path}", response_model=ChunkResponse)
    def v1_chunk(chunk_id: str, worktree: str | None = None) -> dict[str, Any]:
        try:
            return service_for(worktree).chunk(chunk_id)
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
        path: str | None = None,
        worktree: str | None = None,
    ) -> dict[str, Any]:
        svc = service_for(worktree)
        # File mode: pre-resolve the exact entry membership set for `path`
        # from the file->entries index rather than a neighborhood expansion.
        # An unknown path resolves to an empty graph, not an error.
        file_entry_ids = svc.cache.file_entry_index().get(path, []) if path else None
        return project_trace_graph(
            svc.graph(
                entry_id=entry_id,
                entry_ids=file_entry_ids,
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
        worktree: str | None = None,
    ) -> dict[str, Any]:
        # Fixed to the Trail's own edge set (app.js TRAIL_EDGE_TYPES) - the
        # Trail is a dedicated product surface, not a parameterization of the
        # general graph, so its contract doesn't expose edge_types at all.
        return service_for(worktree).graph(
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


def _chunk_row(chunk: MemoryChunk) -> tuple[Any, ...]:
    """One chunks-table row - shared by the full rebuild and the incremental
    reconcile so the stored shape can never drift between the two paths."""
    return (
        chunk.chunk_id,
        chunk.granularity,
        chunk.entry_id,
        chunk.session_date.isoformat(),
        chunk.entry_datetime.isoformat() if chunk.entry_datetime else None,
        json.dumps(_chunk_to_storage(chunk), sort_keys=True),
    )


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


def _entry_commit_map(root: Path, *, rev_range: str | None = None) -> dict[str, dict[str, str]]:
    """entry_id -> the oldest commit whose diff added that entry's id line.

    One ``git log -p`` pass over the session tree, newest-first; assignment
    overwrites on every sighting, so the final value is the OLDEST commit -
    migrations and fuse rewrites that re-add an entry never steal attribution
    from the commit that first captured it. This is what makes "work done on
    main with no commit rides the next commit that occurs" true by
    construction, including pre-branching history. Fails open to an empty map
    when git or a repository is unavailable.

    ``rev_range`` (an ``old..new`` expression) bounds the walk to newly
    reachable commits for incremental reconciliation; the caller is
    responsible for re-add detection (an entry sighted in the range that is
    already attributed) and falls back to the unbounded pass in that case.
    """
    try:
        proc = subprocess.run(
            [
                "git", "-C", str(root), "log", "-p",
                "--format=%x01%H%x1f%h%x1f%aI%x1f%s",
                *([rev_range] if rev_range else []),
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


# A merge commit's fork point (merge-base of its parents) is an immutable fact
# of the object database, and every worktree of a repository shares that
# database - so fork points computed for the shared trunk are valid for every
# checkout. This in-process memo is the L1 over the persisted fork_points
# table (schema v2): a fresh process warm-starts from SQLite, and within a
# process, worktree switches only compute the merges unique to their own
# divergence.
_FORK_POINT_MEMO: dict[str, dict[str, str] | None] = {}


def _trunk_ref_and_sha(root: Path) -> tuple[str, str] | None:
    """Resolve which trunk ref exists (main, then master, then HEAD) and its
    current sha. The trunk is the ref the trailer/merge and file-index walks
    run over, independent of which branch this checkout has checked out.
    None when git is unavailable."""
    for ref in ("main", "master", "HEAD"):
        try:
            proc = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "--verify", "--quiet", ref],
                capture_output=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if proc.returncode == 0:
            sha = proc.stdout.decode("utf-8", errors="replace").strip()
            if sha:
                return ref, sha
    return None


def _commit_graph(root: Path, ref: str) -> dict[str, dict[str, Any]]:
    """Every commit reachable from ``ref`` in ONE git process:
    sha -> {short, date, parents}. This is the bulk read that replaces
    per-merge ``git merge-base``/``git show`` and per-commit metadata spawns -
    fork points and commit facts are then resolved in-process against this
    map. Fails open to an empty dict without git."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "log", "--format=%H%x1f%h%x1f%cI%x1f%P", ref],
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if proc.returncode != 0:
        return {}
    graph: dict[str, dict[str, Any]] = {}
    for line in proc.stdout.decode("utf-8", errors="replace").splitlines():
        if "\x1f" not in line:
            continue
        sha, short, date, parents = (line.split("\x1f", 3) + ["", "", ""])[:4]
        graph[sha] = {"short": short, "date": date, "parents": parents.split()}
    return graph


def _graph_ancestors(graph: Mapping[str, dict[str, Any]], start: str) -> set[str]:
    """All commits reachable from ``start`` (inclusive) via parent edges,
    restricted to commits present in ``graph``."""
    seen: set[str] = set()
    frontier = [start]
    while frontier:
        sha = frontier.pop()
        if sha in seen or sha not in graph:
            continue
        seen.add(sha)
        frontier.extend(graph[sha]["parents"])
    return seen


def _bulk_fork_points(
    root: Path,
    graph: Mapping[str, dict[str, Any]],
    merges: Mapping[str, list[str]],
) -> dict[str, dict[str, str] | None]:
    """Fork points (merge-base of a merge's first two parents) for every merge
    in ``merges`` (sha -> parent list), resolved in-process from the commit
    graph instead of one ``git merge-base`` + ``git show`` pair per merge.

    The merge-base is the maximal common ancestor of the two parents. Ancestor
    sets are downward-closed, so their intersection is too - which means a
    common ancestor is maximal iff none of its immediate children is also a
    common ancestor. When that leaves exactly one candidate (every normal
    branch-off-trunk merge), it IS git's answer; the rare ambiguous case
    (criss-cross merges) falls back to git itself so the published fork point
    never diverges from ``git merge-base``.
    """
    children: dict[str, list[str]] = {}
    for sha, info in graph.items():
        for parent in info["parents"]:
            children.setdefault(parent, []).append(sha)
    results: dict[str, dict[str, str] | None] = {}
    for merge_sha, parents in merges.items():
        if len(parents) < 2 or parents[0] not in graph or parents[1] not in graph:
            results[merge_sha] = None
            continue
        common = _graph_ancestors(graph, parents[0]) & _graph_ancestors(graph, parents[1])
        if not common:
            results[merge_sha] = None
            continue
        maximal = [
            sha for sha in common
            if not any(child in common for child in children.get(sha, ()))
        ]
        if len(maximal) == 1:
            info = graph[maximal[0]]
            results[merge_sha] = {"sha": maximal[0], "short": info["short"], "date": info["date"]}
        else:
            # Criss-cross history: multiple best common ancestors. Delegate the
            # choice to git for exactness; this is per-ambiguous-merge, not
            # per-merge, and effectively never fires on this project's shape.
            results[merge_sha] = _merge_fork_point(root, parents[0], parents[1])
    return results


def _trailer_walk(root: Path, ref: str | None = None) -> list[dict[str, Any]] | None:
    """Raw trunk first-parent commits carrying ``Memory-Entry:`` trailers,
    newest-first, WITHOUT fork resolution (each event keeps its ``parents``
    list for the caller to resolve). None when git is unavailable so callers
    can distinguish "no git" from "no merges"."""
    refs = (ref,) if ref else ("main", "master", "HEAD")
    for candidate in refs:
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
                    "git", "-C", str(root), "log", "--first-parent", candidate, "-z",
                    "--format=%H%x1f%h%x1f%cI%x1f%P%x1f%s%x1f%B",
                ],
                capture_output=True,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
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
            events.append(
                {
                    "sha": sha,
                    "short": short,
                    "date": date,
                    "subject": subject,
                    "entry_ids": entry_ids,
                    "parents": parents.split(),
                }
            )
        return events
    return None


def _resolve_event_forks(
    root: Path,
    events: list[dict[str, Any]],
    *,
    known_fork_points: Mapping[str, dict[str, str] | None] | None = None,
    commit_graph: Mapping[str, dict[str, Any]] | None = None,
    trunk_ref: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str] | None]]:
    """Attach ``fork`` to raw trailer-walk events, spending git work only on
    merges whose fork point is not already known.

    Resolution order per merge sha: caller-provided ``known_fork_points`` (the
    persisted table) -> the process-wide memo -> one bulk commit-graph pass
    shared by every remaining merge. Returns the finished events plus the
    newly resolved fork points for the caller to persist. Strips the internal
    ``parents`` field so the event shape matches the published contract.
    """
    known = dict(known_fork_points or {})
    missing: dict[str, list[str]] = {}
    for event in events:
        sha = event["sha"]
        if len(event.get("parents", ())) < 2:
            continue
        if sha in known or sha in _FORK_POINT_MEMO:
            continue
        missing[sha] = event["parents"]
    newly_resolved: dict[str, dict[str, str] | None] = {}
    if missing:
        graph = commit_graph if commit_graph is not None else _commit_graph(root, trunk_ref or "HEAD")
        newly_resolved = _bulk_fork_points(root, graph, missing)
        _FORK_POINT_MEMO.update(newly_resolved)
    finished: list[dict[str, Any]] = []
    for event in events:
        sha = event["sha"]
        parents = event.get("parents", [])
        if len(parents) >= 2:
            if sha in known:
                fork = known[sha]
                _FORK_POINT_MEMO.setdefault(sha, fork)
            elif sha in newly_resolved:
                fork = newly_resolved[sha]
            else:
                fork = _FORK_POINT_MEMO.get(sha)
        else:
            fork = None
        finished.append({key: value for key, value in event.items() if key != "parents"} | {"fork": fork})
    return finished, newly_resolved


def _first_parent_trailer_commits(root: Path) -> list[dict[str, Any]]:
    """Merge-commit ground truth for the Trail: trunk first-parent commits
    carrying ``Memory-Entry:`` trailers, newest-first.

    ``session merge-branch`` stamps one trailer per merged entry on the merge
    commit - the only place the entry/commit join can be recorded atomically,
    since an entry cannot contain the SHA of a commit that hashes over it. For
    true merge commits (>=2 parents) ``fork`` is the parents' merge-base
    (resolved in bulk from one commit-graph pass, never one subprocess per
    merge); a non-merge commit carrying a trailer keeps ``fork: None``. Fails
    open to an empty list without git.
    """
    events = _trailer_walk(root)
    if not events:
        return []
    finished, _ = _resolve_event_forks(root, events)
    return finished


def _memoized_fork_point(root: Path, sha: str, parent_list: list[str]) -> dict[str, str] | None:
    if sha in _FORK_POINT_MEMO:
        return _FORK_POINT_MEMO[sha]
    fork = _merge_fork_point(root, parent_list[0], parent_list[1])
    _FORK_POINT_MEMO[sha] = fork
    return fork


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


def _changed_paths_bulk(root: Path, rev_or_range: str) -> dict[str, list[str]] | None:
    """First-parent changed paths for every commit reachable via
    ``rev_or_range`` (a ref name or an ``old..new`` range), in ONE git
    process: sha -> [paths]. ``--diff-merges=first-parent`` makes a merge
    commit report its diff against its first parent - exactly the
    ``work_sha^1`` base the per-work-commit ``git diff`` used to compute -
    while a plain commit reports its diff against its sole parent. None when
    git fails so callers can fail toward a full recompute."""
    try:
        proc = subprocess.run(
            [
                "git", "-C", str(root), "log", "--diff-merges=first-parent",
                "--name-only", "--format=%x01%H", rev_or_range,
            ],
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    changed: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in proc.stdout.decode("utf-8", errors="replace").splitlines():
        if line.startswith("\x01"):
            sha = line[1:].strip()
            current = changed.setdefault(sha, []) if sha else None
        elif current is not None:
            path = line.strip()
            if path and path not in current:
                current.append(path)
    return changed


def _file_entry_index_from_parts(
    entry_commit_map: Mapping[str, dict[str, str]],
    parents_of: Mapping[str, list[str]],
    changed_paths: Mapping[str, list[str]],
) -> dict[str, list[str]]:
    """Pure derivation of path -> sorted entry_ids from already-harvested git
    facts. Groups entries by their shared "work commit" (the authoring
    commit's first parent), then attributes that work commit's first-parent
    changed paths to every entry in the group. Root commits (no parents) are
    skipped, matching the historical per-commit ``git diff`` behavior whose
    ``work_sha^`` base did not resolve for them."""
    entries_by_work_sha: dict[str, list[str]] = {}
    for entry_id, info in entry_commit_map.items():
        authoring_sha = info.get("sha")
        authoring_parents = parents_of.get(authoring_sha) if authoring_sha else None
        if not authoring_parents:
            continue
        entries_by_work_sha.setdefault(authoring_parents[0], []).append(entry_id)
    index: dict[str, set[str]] = {}
    for work_sha, entry_ids in entries_by_work_sha.items():
        if not parents_of.get(work_sha):
            continue
        for path in changed_paths.get(work_sha, ()):  # missing sha -> no paths
            index.setdefault(path, set()).update(entry_ids)
    return {path: sorted(ids) for path, ids in index.items()}


def _file_entry_index(root: Path, entry_commit_map: dict[str, dict[str, str]]) -> dict[str, list[str]]:
    """path -> sorted entry_ids whose real work touched that file.

    An entry's own authoring commit (``_entry_commit_map``) is very often a
    ``docs(session): log X`` commit landed on main immediately AFTER the
    merge that actually carried the feature's files - this project's
    convention logs the session entry on main after merging, not on the
    feature branch, so the authoring commit's own diff is almost always just
    the session file, and the entry's recorded ``branch:`` field is "main"
    (where it was logged), not the feature branch it documents. Neither is a
    usable file signal on its own.

    The real file changes sit on the authoring commit's PARENT: empirically,
    for this project's actual history, that parent is the merge commit for
    the feature the entry documents. Diffing that parent against ITS OWN
    first parent (if it is a merge) - or its sole parent otherwise, for
    entries logged right after a plain non-merge commit - recovers the files
    the work introduced. Both harvests are single bulk git passes (commit
    graph + first-parent changed paths), never one diff per work commit.
    Fails open to an empty dict without git.
    """
    trunk = _trunk_ref_and_sha(root)
    if trunk is None:
        return {}
    graph = _commit_graph(root, trunk[0])
    if not graph:
        return {}
    changed = _changed_paths_bulk(root, trunk[0])
    if changed is None:
        return {}
    parents_of = {sha: info["parents"] for sha, info in graph.items()}
    return _file_entry_index_from_parts(entry_commit_map, parents_of, changed)


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
