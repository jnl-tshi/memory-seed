"""Controlled topic vocabulary: load, resolve, and validate `.memory-seed/topics.yaml`.

Topics are neighbourhood *membership*, not a graph edge kind
(docs/3_Spec/graph-edge-contract.md groups them with the derived display axes), so their
vocabulary validation deliberately lives in a separate ``memory-seed topics check`` command
rather than overloading the graph/link validator (`links check`). Parsing is stdlib-only and
fail-open, matching the other control-plane readers: a missing or malformed ``topics.yaml``
never breaks retrieval - it only limits what ``topics check`` can validate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .core import resolve_runtime
from .semantic_cache import extract_memory_chunks

# Same pattern family as user slugs (SESSION_USER_SLUG_RE precedent): one convention to
# maintain. Underscores permitted; observed corpus convention is hyphen-only.
TOPIC_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

# Soft ceiling from the topics plan: meaningful entries carry 1-3 topics. Exceeding it is a
# warning, never an error - old and over-target entries stay valid.
TOPIC_COUNT_TARGET = 3


@dataclass(frozen=True)
class TopicRecord:
    slug: str
    label: str = ""
    description: str = ""
    status: str = "active"
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class TopicIndex:
    path: str
    exists: bool
    schema_version: str | None
    topics: tuple[TopicRecord, ...]

    def resolution(self) -> dict[str, str]:
        """slug -> canonical slug for every canonical and alias name."""
        mapping: dict[str, str] = {}
        for record in self.topics:
            mapping.setdefault(record.slug, record.slug)
            for alias in record.aliases:
                mapping.setdefault(alias, record.slug)
        return mapping


@dataclass(frozen=True)
class TopicIssue:
    severity: str  # "error" | "warning" | "info"
    kind: str
    detail: str
    source: str = ""


@dataclass(frozen=True)
class TopicsCheckResult:
    ok: bool
    issues: tuple[TopicIssue, ...]
    entries_checked: int
    topics_defined: int


def _parse_alias_value(value: str) -> tuple[str, ...]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1]
        return tuple(part.strip().strip("'\"") for part in inner.split(",") if part.strip())
    if value:
        return (value.strip("'\""),)
    return ()


def load_topic_index(cwd: str | Path = ".") -> TopicIndex:
    """Read ``.memory-seed/topics.yaml`` fail-open with the stdlib line scanner."""
    runtime = resolve_runtime(cwd)
    path = runtime.memory_dir / "topics.yaml"
    rel = f"{runtime.memory_dir.name}/topics.yaml"
    if not path.exists():
        return TopicIndex(path=rel, exists=False, schema_version=None, topics=())
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return TopicIndex(path=rel, exists=False, schema_version=None, topics=())

    schema_version: str | None = None
    records: list[TopicRecord] = []
    current: dict[str, object] | None = None
    in_topics = False
    in_alias_block = False

    def flush() -> None:
        nonlocal current
        if current is not None:
            records.append(
                TopicRecord(
                    slug=str(current.get("slug", "")),
                    label=str(current.get("label", "")),
                    description=str(current.get("description", "")),
                    status=str(current.get("status", "active")) or "active",
                    aliases=tuple(current.get("aliases", ()) or ()),
                )
            )
        current = None

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line[:1].isspace():
            in_topics = False
            in_alias_block = False
            if ":" not in stripped:
                continue
            key, value = stripped.split(":", 1)
            key, value = key.strip(), value.strip().strip("'\"")
            if key == "schema_version" and value:
                schema_version = value
            elif key == "topics":
                flush()
                in_topics = True
            continue
        if not in_topics:
            continue
        if stripped.startswith("- ") and ":" in stripped[2:]:
            flush()
            current = {"aliases": []}
            in_alias_block = False
            stripped = stripped[2:].strip()
        elif stripped.startswith("- "):
            # bare list item: only legal inside a block-style aliases list
            if in_alias_block and current is not None:
                current["aliases"] = list(current.get("aliases", ())) + [stripped[2:].strip().strip("'\"")]
            continue
        if current is None or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key, value = key.strip(), value.strip()
        if key == "aliases":
            in_alias_block = not value
            if value:
                current["aliases"] = list(_parse_alias_value(value))
        else:
            in_alias_block = False
            current[key] = value.strip("'\"")
    flush()

    return TopicIndex(path=rel, exists=True, schema_version=schema_version, topics=tuple(records))


def check_topics(cwd: str | Path = ".") -> TopicsCheckResult:
    """Validate the vocabulary and every entry's stored ``topics:`` against it.

    Errors (exit non-zero): missing index while entries carry topics, malformed or duplicate
    slugs, alias collisions, and entry topics found in neither the canonical nor alias column.
    Warnings: deprecated-topic use and per-entry counts above ``TOPIC_COUNT_TARGET``.
    Info: defined topics no entry uses yet.
    """
    index = load_topic_index(cwd)
    issues: list[TopicIssue] = []

    seen: dict[str, str] = {}
    for record in index.topics:
        for name, role in ((record.slug, "slug"), *((alias, f"alias of {record.slug}") for alias in record.aliases)):
            if not TOPIC_SLUG_RE.match(name or ""):
                issues.append(TopicIssue("error", "malformed-slug", f"{role} '{name}' does not match {TOPIC_SLUG_RE.pattern}", index.path))
                continue
            if name in seen:
                kind = "duplicate-slug" if role == "slug" and seen[name] == "slug" else "alias-collision"
                issues.append(TopicIssue("error", kind, f"'{name}' appears as both {seen[name]} and {role}", index.path))
            else:
                seen[name] = role

    resolution = index.resolution()
    statuses = {record.slug: record.status for record in index.topics}
    used: set[str] = set()
    entries_checked = 0
    chunks = [chunk for chunk in extract_memory_chunks(cwd, granularity="entry") if chunk.topics]
    for chunk in chunks:
        entries_checked += 1
        source = f"{chunk.source_path}:{chunk.entry_id or chunk.title}"
        if not index.exists:
            continue
        for slug in chunk.topics:
            canonical = resolution.get(slug)
            if canonical is None:
                issues.append(TopicIssue("error", "unknown-entry-topic", f"topics -> {slug} (not a canonical slug or alias)", source))
                continue
            used.add(canonical)
            if statuses.get(canonical) == "deprecated":
                issues.append(TopicIssue("warning", "deprecated-topic-use", f"topics -> {slug} resolves to deprecated '{canonical}'", source))
        if len(chunk.topics) > TOPIC_COUNT_TARGET:
            issues.append(
                TopicIssue("warning", "topic-count", f"{len(chunk.topics)} topics on one entry (target is 1-{TOPIC_COUNT_TARGET})", source)
            )

    if not index.exists and entries_checked:
        issues.append(
            TopicIssue("error", "missing-index", f"{entries_checked} entries carry topics: but {index.path} does not exist", index.path)
        )

    for record in index.topics:
        if record.slug not in used and record.status == "active":
            issues.append(TopicIssue("info", "unused-topic", f"'{record.slug}' is defined but no entry uses it", index.path))

    ok = not any(issue.severity == "error" for issue in issues)
    return TopicsCheckResult(ok=ok, issues=tuple(issues), entries_checked=entries_checked, topics_defined=len(index.topics))


def expand_topic_filter(cwd: str | Path, requested: list[str] | tuple[str, ...]) -> set[str]:
    """Expand requested topic slugs to the full match set for filtering.

    Each requested name resolves to its canonical topic; the match set contains that canonical
    plus every alias of it, so stored entries using either form match. Unknown names pass
    through as-is (fail-open - filtering never errors on vocabulary drift).
    """
    index = load_topic_index(cwd)
    resolution = index.resolution()
    by_canonical: dict[str, set[str]] = {}
    for name, canonical in resolution.items():
        by_canonical.setdefault(canonical, set()).add(name)
    expanded: set[str] = set()
    for name in requested:
        canonical = resolution.get(name)
        if canonical is None:
            expanded.add(name)
        else:
            expanded.update(by_canonical.get(canonical, {canonical}))
    return expanded
