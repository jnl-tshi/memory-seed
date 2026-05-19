from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Protocol, Sequence


SESSION_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*#*\s*$")
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


def extract_memory_chunks(cwd: str | Path = ".") -> list[MemoryChunk]:
    target_root = Path(cwd).resolve()
    sessions_dir = target_root / ".AGENTS" / "sessions"
    if not sessions_dir.is_dir():
        return []

    chunks: list[MemoryChunk] = []
    for path in sorted(sessions_dir.iterdir()):
        match = SESSION_FILE_RE.match(path.name)
        if not match:
            continue
        try:
            session_date = datetime.strptime(match.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        chunks.extend(_extract_chunks_from_file(target_root, path, session_date))
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
) -> list[RankedMemoryChunk]:
    return rank_memory_chunks(
        query,
        extract_memory_chunks(cwd),
        top_k=top_k,
        today=today,
        lambda_days=lambda_days,
        recency_enabled=recency_enabled,
        recency_floor=recency_floor,
        embedding_provider=embedding_provider,
    )


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
    path: Path,
    session_date: date,
) -> list[MemoryChunk]:
    lines = path.read_text(encoding="utf-8").splitlines()
    chunks: list[MemoryChunk] = []
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
                chunk_id=_chunk_id(path.name, current_start, title_path, payload),
                source_path=path.relative_to(target_root).as_posix(),
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


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))
