from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from functools import lru_cache
from typing import Any, Callable, Protocol, Sequence

from .core import SessionDocument, iter_session_documents, resolve_runtime


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
TAG_RE = re.compile(r"(?<![\w/.-])#([A-Za-z][A-Za-z0-9_-]*)")
IDENTIFIER_RE = re.compile(
    r"(?<![\w/])(?:`?)([A-Za-z0-9_.-]*[A-Za-z_][A-Za-z0-9_.-]*(?:/[A-Za-z0-9_.-]+)*)(?:`?)"
)
STRUCTURAL_QUERY_TERMS = (
    "architecture",
    "baseline",
    "bootstrap",
    "control plane",
    "spec",
    "design",
)
ENTRY_DATETIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+-\s+.+$")


@dataclass(frozen=True)
class MemoryChunk:
    chunk_id: str
    source_path: str
    source_file: str
    session_date: date
    entry_datetime: datetime | None
    heading_path: tuple[str, ...]
    heading_level: int
    title: str
    text: str
    tags: tuple[str, ...]
    contexts: tuple[str, ...]
    lexical_terms: tuple[str, ...]
    start_line: int
    end_line: int
    entry_id: str | None = None
    user_initials: str | None = None
    agent_type: str | None = None
    agent_name: str | None = None
    project_path: str | None = None
    subproject_path: str | None = None
    user: str | None = None
    file_hash_id: str | None = None
    related_entries: tuple[str, ...] = ()
    supersedes: tuple[str, ...] = ()
    commits: tuple[str, ...] = ()
    entry_title: str | None = None
    entry_line_range: tuple[int, int] | None = None
    sections: tuple[str, ...] = ()
    granularity: str = "legacy"


@dataclass(frozen=True)
class RankedMemoryChunk:
    chunk: MemoryChunk
    final_score: float
    match_score: float
    lexical_score: float
    semantic_score: float | None
    recency_multiplier: float
    age_days: int
    matched_terms: tuple[str, ...]
    matched_fields: tuple[str, ...]


class EmbeddingProvider(Protocol):
    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        ...


class Model2VecEmbeddingProvider:
    default_model_name = "minishlab/potion-base-8M"

    def __init__(
        self,
        model_name: str = default_model_name,
        model_loader: Callable[[str], Any] | None = None,
    ):
        self.model_name = model_name
        self.name = f"model2vec:{model_name}"
        self._model_loader = model_loader or _load_model2vec_model
        self._model: Any | None = None

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        model = self._get_model()
        vectors = model.encode(list(texts))
        return [_vector_to_tuple(vector) for vector in vectors]

    def _get_model(self) -> Any:
        if self._model is None:
            self._model = self._model_loader(self.model_name)
        return self._model


@lru_cache(maxsize=2)
def _load_model2vec_model(model_name: str) -> Any:
    from model2vec import StaticModel

    return StaticModel.from_pretrained(model_name)


def _vector_to_tuple(vector: Any) -> tuple[float, ...]:
    if hasattr(vector, "tolist"):
        vector = vector.tolist()
    return tuple(float(value) for value in vector)


def extract_memory_chunks(cwd: str | Path = ".", *, granularity: str = "entry") -> list[MemoryChunk]:
    if granularity not in ("entry", "section"):
        raise ValueError("granularity must be 'entry' or 'section'")
    runtime = resolve_runtime(cwd)
    target_root = runtime.workspace_root
    sessions_dir = runtime.memory_dir / "sessions"
    if not sessions_dir.is_dir():
        return []

    chunks: list[MemoryChunk] = []
    for doc in iter_session_documents(sessions_dir):
        try:
            session_date = datetime.strptime(doc.session_date, "%Y-%m-%d").date()
        except ValueError:
            continue
        chunks.extend(_extract_chunks_from_file(target_root, doc, session_date, granularity=granularity))
    return chunks


def rank_session_memory(
    query: str,
    cwd: str | Path = ".",
    *,
    top_k: int = 8,
    today: date | None = None,
    lambda_days: float = 0.01,
    recency_enabled: bool = True,
    recency_floor: float = 0.15,
    embedding_provider: EmbeddingProvider | None = None,
    granularity: str = "entry",
    user: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[RankedMemoryChunk]:
    chunks = extract_memory_chunks(cwd, granularity=granularity)
    chunks = _filter_chunks(chunks, user=user, date_from=date_from, date_to=date_to)
    return rank_memory_chunks(
        query,
        chunks,
        top_k=top_k,
        today=today,
        lambda_days=lambda_days,
        recency_enabled=recency_enabled,
        recency_floor=recency_floor,
        embedding_provider=embedding_provider,
    )


def _filter_chunks(
    chunks: Sequence[MemoryChunk],
    *,
    user: str | None,
    date_from: date | None,
    date_to: date | None,
) -> list[MemoryChunk]:
    filtered: list[MemoryChunk] = []
    for chunk in chunks:
        if user is not None and chunk.user != user:
            continue
        if date_from is not None and chunk.session_date < date_from:
            continue
        if date_to is not None and chunk.session_date > date_to:
            continue
        filtered.append(chunk)
    return filtered


@dataclass(frozen=True)
class RelatedEntryNode:
    """One node in the related-entry graph.

    ``outbound`` is the entry's stored ``related_entries`` (the forward edges it
    declared at write time). ``inbound`` is computed at read time from every
    other entry that points here - the backlinks that make traversal
    bidirectional without ever editing a historical entry. Inbound is built only
    from refs that resolve to a known entry_id; ``outbound`` is reported as
    stored (run ``links check`` to surface any dangling outbound ref).

    ``supersedes`` is the entry's stored typed edge marking earlier decisions it
    replaces; ``superseded_by`` is its computed inverse, built the same way as
    ``inbound``. The two edge kinds are never merged: a supersession is a status
    signal (this decision is retired), not a relatedness signal.
    """

    entry_id: str
    title: str
    source_path: str
    session_date: date
    outbound: tuple[str, ...]
    inbound: tuple[str, ...]
    supersedes: tuple[str, ...] = ()
    superseded_by: tuple[str, ...] = ()


def _entry_order_key(chunk: MemoryChunk) -> tuple[date, datetime, int]:
    """Chronological sort key: session date, then within-file append order."""
    return (chunk.session_date, chunk.entry_datetime or datetime.min, chunk.start_line)


def build_related_entry_graph(
    cwd: str | Path = ".",
    *,
    chunks: Sequence[MemoryChunk] | None = None,
) -> dict[str, RelatedEntryNode]:
    """Build the bidirectional related-entry graph over all session entries.

    Stored edges are directed (an entry declares ``related_entries`` to prior
    entries). This inverts them at read time so each node also exposes its
    backlinks, giving MCP and future UI consumers an old<->new view without rewriting
    history. Assumes a ``links check``-clean corpus; on a duplicate ``entry_id``
    the first occurrence wins.

    Pass ``chunks`` to reuse an already-extracted entry-granularity corpus and
    skip re-parsing (e.g. a caller that already called ``extract_memory_chunks``).
    """
    if chunks is None:
        chunks = extract_memory_chunks(cwd, granularity="entry")
    by_id: dict[str, MemoryChunk] = {}
    for chunk in chunks:
        if chunk.entry_id and chunk.entry_id not in by_id:
            by_id[chunk.entry_id] = chunk

    inbound: dict[str, list[str]] = {entry_id: [] for entry_id in by_id}
    superseded_by: dict[str, list[str]] = {entry_id: [] for entry_id in by_id}
    for chunk in chunks:
        if not chunk.entry_id:
            continue
        for ref in chunk.related_entries:
            if ref in by_id and ref != chunk.entry_id:
                inbound[ref].append(chunk.entry_id)
        for ref in chunk.supersedes:
            if ref in by_id and ref != chunk.entry_id:
                superseded_by[ref].append(chunk.entry_id)

    graph: dict[str, RelatedEntryNode] = {}
    for entry_id, chunk in by_id.items():
        graph[entry_id] = RelatedEntryNode(
            entry_id=entry_id,
            title=chunk.title,
            source_path=chunk.source_path,
            session_date=chunk.session_date,
            outbound=tuple(chunk.related_entries),
            inbound=tuple(dict.fromkeys(inbound[entry_id])),
            supersedes=tuple(chunk.supersedes),
            superseded_by=tuple(dict.fromkeys(superseded_by[entry_id])),
        )
    return graph


def suggest_related_entries(
    cwd: str | Path = ".",
    *,
    entry_id: str | None = None,
    top_k: int = 5,
    embedding_provider: EmbeddingProvider | None = None,
) -> tuple[MemoryChunk, list[RankedMemoryChunk]]:
    """Rank candidate prior entries to link from a target entry.

    Forward-only by construction: candidates are restricted to entries *older*
    than the target, so acting on a suggestion only ever adds a backward-in-time
    edge to the target's own ``related_entries`` (the bidirectional model the
    user chose). Self and already-linked entries are excluded. The default
    target is the newest entry - "suggest links for the entry I just wrote".
    Read-only; it never writes. Ranking reuses ``rank_memory_chunks`` with
    recency disabled so similarity, not age, drives the ordering.
    """
    chunks = [chunk for chunk in extract_memory_chunks(cwd, granularity="entry") if chunk.entry_id]
    if not chunks:
        raise LookupError("no session entries with an entry_id were found")

    if entry_id is not None:
        target = next((chunk for chunk in chunks if chunk.entry_id == entry_id), None)
        if target is None:
            raise LookupError(f"entry_id {entry_id} not found")
    else:
        target = max(chunks, key=_entry_order_key)

    target_key = _entry_order_key(target)
    linked = set(target.related_entries)
    candidates = [
        chunk
        for chunk in chunks
        if chunk.entry_id != target.entry_id
        and chunk.entry_id not in linked
        and _entry_order_key(chunk) < target_key
    ]
    if not candidates:
        return target, []

    query = f"{target.title}\n{target.text}".strip()
    ranked = rank_memory_chunks(
        query,
        candidates,
        top_k=top_k,
        recency_enabled=False,
        embedding_provider=embedding_provider,
    )
    return target, ranked


def rank_memory_chunks(
    query: str,
    chunks: Sequence[MemoryChunk],
    *,
    top_k: int = 8,
    today: date | None = None,
    lambda_days: float = 0.01,
    recency_enabled: bool = True,
    recency_floor: float = 0.15,
    embedding_provider: EmbeddingProvider | None = None,
) -> list[RankedMemoryChunk]:
    current_date = today or date.today()
    query_terms = _query_terms(query)
    semantic_scores = _semantic_scores(query, chunks, embedding_provider)
    effective_lambda = _effective_lambda(query, lambda_days)

    ranked: list[RankedMemoryChunk] = []
    for index, chunk in enumerate(chunks):
        lexical_score, matched_terms, matched_fields = _lexical_score(query_terms, chunk)
        semantic_score = semantic_scores[index] if semantic_scores is not None else None
        semantic_component = max(semantic_score or 0.0, 0.0) * 3.0
        match_score = lexical_score + semantic_component
        age_days = max((current_date - chunk.session_date).days, 0)
        recency_multiplier = _recency_multiplier(
            age_days,
            effective_lambda,
            recency_enabled=recency_enabled,
            recency_floor=recency_floor,
        )
        final_score = match_score * recency_multiplier
        ranked.append(
            RankedMemoryChunk(
                chunk=chunk,
                final_score=final_score,
                match_score=match_score,
                lexical_score=lexical_score,
                semantic_score=semantic_score,
                recency_multiplier=recency_multiplier,
                age_days=age_days,
                matched_terms=tuple(sorted(matched_terms)),
                matched_fields=tuple(sorted(matched_fields)),
            )
        )

    ranked.sort(
        key=lambda result: (
            result.final_score,
            result.match_score,
            result.lexical_score,
            -result.age_days,
            result.chunk.source_file,
            result.chunk.start_line,
        ),
        reverse=True,
    )
    return ranked[: max(top_k, 0)]


def _extract_chunks_from_file(
    target_root: Path,
    doc: SessionDocument,
    session_date: date,
    *,
    granularity: str,
) -> list[MemoryChunk]:
    path = doc.path
    lines = path.read_text(encoding="utf-8").splitlines()
    file_metadata = _extract_file_frontmatter(lines)
    file_hash_id = file_metadata.get("hash_id")
    file_user = doc.user
    entries = _find_entry_ranges(lines)
    if entries:
        return _extract_entry_chunks_from_file(
            target_root,
            path,
            session_date,
            lines,
            entries,
            granularity,
            user=file_user,
            file_hash_id=file_hash_id,
        )
    return _extract_legacy_chunks_from_file(
        target_root,
        path,
        session_date,
        lines,
        user=file_user,
        file_hash_id=file_hash_id,
    )


def _find_entry_ranges(lines: Sequence[str]) -> list[tuple[int, int, str]]:
    entries: list[tuple[int, int, str]] = []
    starts: list[tuple[int, str]] = []
    for lineno, line in enumerate(lines, start=1):
        heading = HEADING_RE.match(line)
        if heading and len(heading.group(1)) == 2:
            starts.append((lineno, heading.group(2).strip()))

    for index, (start, title) in enumerate(starts):
        end = starts[index + 1][0] - 1 if index + 1 < len(starts) else len(lines)
        entries.append((start, end, title))
    return entries


def _extract_entry_chunks_from_file(
    target_root: Path,
    path: Path,
    session_date: date,
    lines: Sequence[str],
    entries: Sequence[tuple[int, int, str]],
    granularity: str,
    *,
    user: str | None,
    file_hash_id: str | None,
) -> list[MemoryChunk]:
    chunks: list[MemoryChunk] = []
    source_path = path.relative_to(target_root).as_posix()
    for start_line, end_line, title in entries:
        entry_lines = list(lines[start_line:end_line])
        metadata = _extract_entry_metadata(entry_lines)
        entry_id = _metadata_value(metadata, "entry_id")
        related_entries = _metadata_list(metadata, "related_entries")
        supersedes = _metadata_list(metadata, "supersedes")
        commits = _metadata_list(metadata, "commits")
        sections = _entry_sections(entry_lines)
        heading_path = (title,)
        entry_range = (start_line, end_line)

        if granularity == "entry":
            text = "\n".join(entry_lines).strip()
            payload = "\n".join((title, text)).strip()
            chunk_id = entry_id or _chunk_id(source_path, start_line, heading_path, payload)
            chunks.append(
                MemoryChunk(
                    chunk_id=chunk_id,
                    source_path=source_path,
                    source_file=path.name,
                    session_date=session_date,
                    entry_datetime=_entry_datetime(title),
                    heading_path=heading_path,
                    heading_level=2,
                    title=title,
                    text=text,
                    tags=_extract_tags(entry_lines),
                    contexts=_extract_contexts(heading_path),
                    lexical_terms=_extract_lexical_terms(payload),
                    start_line=start_line,
                    end_line=end_line,
                    entry_id=entry_id,
                    user_initials=_metadata_value(metadata, "user_initials"),
                    agent_type=_metadata_value(metadata, "agent_type"),
                    agent_name=_metadata_value(metadata, "agent_name"),
                    project_path=_metadata_value(metadata, "project_path"),
                    subproject_path=_metadata_value(metadata, "subproject_path"),
                    user=user,
                    file_hash_id=file_hash_id,
                    related_entries=related_entries,
                    supersedes=supersedes,
                    commits=commits,
                    entry_title=title,
                    entry_line_range=entry_range,
                    sections=sections,
                    granularity="entry",
                )
            )
            continue

        section_ranges = _find_section_ranges(entry_lines, start_line)
        if not section_ranges:
            text = "\n".join(entry_lines).strip()
            payload = "\n".join((title, text)).strip()
            chunk_id = entry_id or _chunk_id(source_path, start_line, heading_path, payload)
            chunks.append(
                MemoryChunk(
                    chunk_id=chunk_id,
                    source_path=source_path,
                    source_file=path.name,
                    session_date=session_date,
                    entry_datetime=_entry_datetime(title),
                    heading_path=heading_path,
                    heading_level=2,
                    title=title,
                    text=text,
                    tags=_extract_tags(entry_lines),
                    contexts=_extract_contexts(heading_path),
                    lexical_terms=_extract_lexical_terms(payload),
                    start_line=start_line,
                    end_line=end_line,
                    entry_id=entry_id,
                    user_initials=_metadata_value(metadata, "user_initials"),
                    agent_type=_metadata_value(metadata, "agent_type"),
                    agent_name=_metadata_value(metadata, "agent_name"),
                    project_path=_metadata_value(metadata, "project_path"),
                    subproject_path=_metadata_value(metadata, "subproject_path"),
                    user=user,
                    file_hash_id=file_hash_id,
                    related_entries=related_entries,
                    supersedes=supersedes,
                    commits=commits,
                    entry_title=title,
                    entry_line_range=entry_range,
                    sections=sections,
                    granularity="section",
                )
            )
            continue

        for section_start, section_end, section_title, section_path in section_ranges:
            section_lines = list(lines[section_start:section_end])
            heading_path = (title, *section_path)
            text = "\n".join(section_lines).strip()
            payload = "\n".join((*heading_path, text)).strip()
            section_id = "/".join(_slugify(section) for section in section_path)
            chunk_id = f"{entry_id}#{section_id}" if entry_id else _chunk_id(source_path, section_start, heading_path, payload)
            chunks.append(
                MemoryChunk(
                    chunk_id=chunk_id,
                    source_path=source_path,
                    source_file=path.name,
                    session_date=session_date,
                    entry_datetime=_entry_datetime(title),
                    heading_path=heading_path,
                    heading_level=2 + len(section_path),
                    title=section_title,
                    text=text,
                    tags=_extract_tags(section_lines),
                    contexts=_extract_contexts(heading_path),
                    lexical_terms=_extract_lexical_terms(payload),
                    start_line=section_start,
                    end_line=section_end,
                    entry_id=entry_id,
                    user_initials=_metadata_value(metadata, "user_initials"),
                    agent_type=_metadata_value(metadata, "agent_type"),
                    agent_name=_metadata_value(metadata, "agent_name"),
                    project_path=_metadata_value(metadata, "project_path"),
                    subproject_path=_metadata_value(metadata, "subproject_path"),
                    user=user,
                    file_hash_id=file_hash_id,
                    related_entries=related_entries,
                    supersedes=supersedes,
                    commits=commits,
                    entry_title=title,
                    entry_line_range=entry_range,
                    sections=sections,
                    granularity="section",
                )
            )
    return chunks


def _extract_legacy_chunks_from_file(
    target_root: Path,
    path: Path,
    session_date: date,
    lines: Sequence[str],
    *,
    user: str | None = None,
    file_hash_id: str | None = None,
) -> list[MemoryChunk]:
    chunks: list[MemoryChunk] = []
    source_path = path.relative_to(target_root).as_posix()
    heading_stack: list[str] = []
    current_title: str | None = None
    current_level = 0
    current_start = 1
    current_lines: list[str] = []

    def flush(end_line: int) -> None:
        nonlocal current_title, current_level, current_start, current_lines
        if current_title is None:
            return
        text = "\n".join(current_lines).strip()
        title_path = tuple(heading for heading in heading_stack[:current_level] if heading)
        payload = "\n".join((current_title, text)).strip()
        chunks.append(
            MemoryChunk(
                chunk_id=_chunk_id(source_path, current_start, title_path, payload),
                source_path=source_path,
                source_file=path.name,
                session_date=session_date,
                entry_datetime=_entry_datetime(current_title),
                heading_path=title_path,
                heading_level=current_level,
                title=current_title,
                text=text,
                tags=_extract_tags(current_lines),
                contexts=_extract_contexts(title_path),
                lexical_terms=_extract_lexical_terms(payload),
                start_line=current_start,
                end_line=end_line,
                user=user,
                file_hash_id=file_hash_id,
            )
        )
        current_lines = []

    for lineno, line in enumerate(lines, start=1):
        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            flush(lineno - 1)
            if len(heading_stack) < level:
                heading_stack.extend([""] * (level - len(heading_stack)))
            heading_stack[level - 1] = title
            del heading_stack[level:]
            current_title = title
            current_level = level
            current_start = lineno
            current_lines = []
            continue

        if current_title is None and line.strip():
            current_title = "(preamble)"
            current_level = 1
            heading_stack = [current_title]
            current_start = lineno
        if current_title is not None:
            current_lines.append(line)

    flush(len(lines))
    return chunks


def _extract_file_frontmatter(lines: Sequence[str]) -> dict[str, str]:
    if not lines or lines[0].strip() != "---":
        return {}
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line or line[:1] in (" ", "\t", "-"):
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and value:
            metadata[key] = value
    return metadata


def _extract_entry_metadata(entry_lines: Sequence[str]) -> dict[str, str | tuple[str, ...]]:
    index = 0
    while index < len(entry_lines) and not entry_lines[index].strip():
        index += 1
    if index >= len(entry_lines) or entry_lines[index].strip() not in ("```yaml", "```yml"):
        return {}
    metadata: dict[str, str | tuple[str, ...]] = {}
    yaml_lines: list[str] = []
    for line in entry_lines[index + 1 :]:
        if line.strip() == "```":
            break
        yaml_lines.append(line)

    line_index = 0
    while line_index < len(yaml_lines):
        line = yaml_lines[line_index]
        if ":" not in line or line[:1] in (" ", "\t", "-"):
            line_index += 1
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if not key:
            line_index += 1
            continue
        if not value:
            items: list[str] = []
            probe = line_index + 1
            while probe < len(yaml_lines) and yaml_lines[probe][:1] in (" ", "\t"):
                stripped = yaml_lines[probe].strip()
                if stripped.startswith("- "):
                    items.append(stripped[2:].strip().strip("\"'"))
                probe += 1
            if items:
                metadata[key] = tuple(items)
            line_index = probe
            continue
        if value == "null":
            value = ""
        metadata[key] = value
        line_index += 1
    return metadata


def _metadata_value(metadata: dict[str, str | tuple[str, ...]], key: str) -> str | None:
    value = metadata.get(key)
    if isinstance(value, tuple):
        return None
    return value or None


def _metadata_list(metadata: dict[str, str | tuple[str, ...]], key: str) -> tuple[str, ...]:
    value = metadata.get(key)
    if isinstance(value, tuple):
        return value
    if isinstance(value, str) and value:
        return (value,)
    return ()


def _entry_sections(entry_lines: Sequence[str]) -> tuple[str, ...]:
    sections: list[str] = []
    for line in entry_lines:
        heading = HEADING_RE.match(line)
        if heading and len(heading.group(1)) >= 3:
            sections.append(heading.group(2).strip())
    return tuple(sections)


def _find_section_ranges(
    entry_lines: Sequence[str],
    entry_start_line: int,
) -> list[tuple[int, int, str, tuple[str, ...]]]:
    headings: list[tuple[int, int, str, tuple[str, ...]]] = []
    stack: list[str] = []
    for offset, line in enumerate(entry_lines, start=entry_start_line + 1):
        heading = HEADING_RE.match(line)
        if not heading:
            continue
        level = len(heading.group(1))
        if level < 3:
            continue
        title = heading.group(2).strip()
        stack_index = level - 3
        if len(stack) <= stack_index:
            stack.extend([""] * (stack_index + 1 - len(stack)))
        stack[stack_index] = title
        del stack[stack_index + 1 :]
        headings.append((offset, level, title, tuple(value for value in stack if value)))

    ranges: list[tuple[int, int, str, tuple[str, ...]]] = []
    for index, (start, _level, title, section_path) in enumerate(headings):
        end = headings[index + 1][0] - 1 if index + 1 < len(headings) else entry_start_line + len(entry_lines)
        ranges.append((start, end, title, section_path))
    return ranges


def _extract_tags(lines: Sequence[str]) -> tuple[str, ...]:
    tags: set[str] = set()
    for line in lines:
        if HEADING_RE.match(line):
            continue
        for match in TAG_RE.finditer(line):
            tags.add(match.group(1).lower())
    return tuple(sorted(tags))


def _entry_datetime(title: str) -> datetime | None:
    match = ENTRY_DATETIME_RE.match(title)
    if not match:
        return None
    try:
        return datetime.strptime(" ".join(match.groups()), "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _extract_contexts(heading_path: Sequence[str]) -> tuple[str, ...]:
    contexts: list[str] = []
    for heading in heading_path:
        if heading.lower().startswith("context:"):
            value = heading.split(":", 1)[1].strip()
            if value:
                contexts.append(value)
    return tuple(contexts)


def _extract_lexical_terms(text: str) -> tuple[str, ...]:
    terms: set[str] = set()
    for match in IDENTIFIER_RE.finditer(text):
        value = match.group(1).strip("`,:;()[]{}").rstrip(".,")
        if not value or value.startswith("#"):
            continue
        if _is_notable_identifier(value):
            terms.add(value)
    return tuple(sorted(terms, key=str.lower))


def _is_notable_identifier(value: str) -> bool:
    return (
        "_" in value
        or "-" in value
        or "/" in value
        or "." in value
        or value.startswith(".")
    )


def _query_terms(query: str) -> tuple[str, ...]:
    terms: set[str] = set()
    for tag in TAG_RE.findall(query):
        terms.add(tag.lower())
    for identifier in _extract_lexical_terms(query):
        terms.add(identifier.lower())
    for word in re.findall(r"[A-Za-z0-9]+", query.lower()):
        if len(word) > 1:
            terms.add(word)
    normalized = _normalize(query)
    if normalized:
        terms.add(normalized)
    return tuple(sorted(terms))


def _lexical_score(
    query_terms: Sequence[str],
    chunk: MemoryChunk,
) -> tuple[float, set[str], set[str]]:
    score = 0.0
    matched_terms: set[str] = set()
    matched_fields: set[str] = set()
    field_values = {
        "tags": chunk.tags,
        "contexts": chunk.contexts,
        "heading_path": chunk.heading_path,
        "lexical_terms": chunk.lexical_terms,
    }
    weights = {
        "tags": 12.0,
        "contexts": 8.0,
        "heading_path": 6.0,
        "lexical_terms": 4.0,
    }

    for field, values in field_values.items():
        for term in query_terms:
            if any(_term_matches_value(term, value) for value in values):
                score += weights[field]
                matched_terms.add(term)
                matched_fields.add(field)

    normalized_text = _normalize(chunk.text)
    for term in query_terms:
        if term and term in normalized_text:
            score += 1.0
            matched_terms.add(term)
            matched_fields.add("text")

    return score, matched_terms, matched_fields


def _term_matches_value(term: str, value: str) -> bool:
    normalized_term = _normalize(term)
    normalized_value = _normalize(value)
    return normalized_term == normalized_value or normalized_term in normalized_value


def _semantic_scores(
    query: str,
    chunks: Sequence[MemoryChunk],
    embedding_provider: EmbeddingProvider | None,
) -> list[float] | None:
    if embedding_provider is None or not chunks:
        return None
    try:
        vectors = embedding_provider.embed([query, *(chunk.text for chunk in chunks)])
    except Exception:
        return None
    if len(vectors) != len(chunks) + 1:
        return None
    query_vector = vectors[0]
    return [_cosine_similarity(query_vector, vector) for vector in vectors[1:]]


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _effective_lambda(query: str, lambda_days: float) -> float:
    normalized_query = _normalize(query)
    if any(term in normalized_query for term in STRUCTURAL_QUERY_TERMS):
        return lambda_days / 2.0
    return lambda_days


def _recency_multiplier(
    age_days: int,
    lambda_days: float,
    *,
    recency_enabled: bool,
    recency_floor: float,
) -> float:
    if not recency_enabled:
        return 1.0
    floor = min(max(recency_floor, 0.0), 1.0)
    return max(floor, math.exp(-lambda_days * age_days))


def _chunk_id(
    source_file: str,
    start_line: int,
    heading_path: Sequence[str],
    payload: str,
) -> str:
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]
    path_slug = "/".join(_normalize(heading) for heading in heading_path)
    return f"{source_file}:{start_line}:{path_slug}:{digest}"


def _slugify(value: str) -> str:
    normalized = "-".join(re.findall(r"[a-z0-9]+", value.lower()))
    return normalized or "section"


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))
