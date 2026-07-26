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
TOPIC_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[_-][a-z0-9]+)*")

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
    # Which of the two axes this slug belongs to: "area" (WHAT you are working
    # on) or "activity" (what KIND of work it is). Empty means undeclared, which
    # is what every schema_version 1 vocabulary looks like - the field is
    # additive and nothing may require it until a vocabulary declares it.
    # Deliberately NOT named "subsystem": the vocabulary ships to projects that
    # are not software, and an area translates where a subsystem does not.
    axis: str = ""
    # Optional parent slug, forming a hierarchy WITHIN an axis. Empty means this
    # slug is a root. Depth is earned by concentration rather than capped - a
    # slug carrying too much of its scope earns children, a thin one stays a
    # leaf - so this can nest arbitrarily deep where the corpus paid for it.
    parent: str = ""


@dataclass(frozen=True)
class TopicIndex:
    path: str
    exists: bool
    schema_version: str | None
    topics: tuple[TopicRecord, ...]

    def resolution(self) -> dict[str, str]:
        """slug -> canonical slug for every canonical and alias name.

        Aliases are SPELLING variants only. A narrower concept belongs in
        ``parent:`` instead - resolution collapses an alias into its canonical
        and discards it, so filing a child here destroys the specificity the
        author recorded.
        """
        mapping: dict[str, str] = {}
        for record in self.topics:
            mapping.setdefault(record.slug, record.slug)
            for alias in record.aliases:
                mapping.setdefault(alias, record.slug)
        return mapping

    def ancestors(self, slug: str) -> tuple[str, ...]:
        """Every parent above ``slug``, nearest first; empty for a root.

        A stored slug implies its ancestors - an entry tagged with a child is
        also about the child's parent - but only the child is ever stored, so
        the cap counts one slug and the parent costs no budget.
        """
        by_slug = {record.slug: record for record in self.topics}
        out: list[str] = []
        seen = {slug}
        current = by_slug.get(slug)
        while current is not None and current.parent:
            if current.parent in seen:  # a cycle is a vocabulary defect; stop rather than hang
                break
            out.append(current.parent)
            seen.add(current.parent)
            current = by_slug.get(current.parent)
        return tuple(out)

    def descendants(self, slug: str) -> tuple[str, ...]:
        """Every slug beneath ``slug`` at any depth. Filters expand DOWNWARD:
        asking for a parent must match entries tagged with its children."""
        children: dict[str, list[str]] = {}
        for record in self.topics:
            if record.parent:
                children.setdefault(record.parent, []).append(record.slug)
        out: list[str] = []
        stack = list(children.get(slug, ()))
        seen: set[str] = set()
        while stack:
            item = stack.pop()
            if item in seen:
                continue
            seen.add(item)
            out.append(item)
            stack.extend(children.get(item, ()))
        return tuple(out)

    def axis_of(self, slug: str) -> str:
        """The declared axis, inherited from the nearest ancestor that declares
        one. Empty when nothing in the chain declares an axis."""
        by_slug = {record.slug: record for record in self.topics}
        record = by_slug.get(slug)
        if record is None:
            return ""
        if record.axis:
            return record.axis
        for parent in self.ancestors(slug):
            parent_record = by_slug.get(parent)
            if parent_record is not None and parent_record.axis:
                return parent_record.axis
        return ""


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
    # Entries whose topics come only from a sidecar. Reported ALONGSIDE
    # entries_checked (authored) rather than folded into it: coverage that
    # silently counted inferred attribution as authorship would overstate what
    # a human has actually vouched for. Their slugs are NOT validated here -
    # `links check` already validates sidecar vocabulary, ordinals, and caps,
    # and a second validator would only drift from the first.
    entries_with_inferred_topics_only: int = 0


@dataclass(frozen=True)
class TopicSuggestion:
    topic: TopicRecord
    score: float
    matched_terms: tuple[str, ...]
    matched_fields: tuple[str, ...]
    evidence: tuple[tuple[str, tuple[str, ...]], ...]


class TopicSuggestError(ValueError):
    def __init__(self, kind: str, detail: str):
        super().__init__(detail)
        self.kind = kind
        self.detail = detail


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
                    axis=str(current.get("axis", "") or ""),
                    parent=str(current.get("parent", "") or ""),
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


def _parent_cycles(index: TopicIndex) -> tuple[tuple[str, ...], ...]:
    """Every cycle in the ``parent:`` graph, each reported once.

    ``ancestors()`` deliberately BREAKS on a repeat rather than raising, because
    it sits on read-time hot paths where a vocabulary defect must never hang or
    crash retrieval. That termination is what makes a cycle silent, so the
    detection belongs here in validation instead - the one place whose job is
    to say a vocabulary is wrong.

    A cycle is reported once per cycle, not once per member: three slugs in a
    three-cycle are one defect, and three identical issues would only bury it.
    The rotation-independent frozenset of members is the dedupe key.
    """
    by_slug = {record.slug: record for record in index.topics}
    found: dict[frozenset[str], tuple[str, ...]] = {}
    for record in index.topics:
        path: list[str] = []
        seen: set[str] = set()
        current: str | None = record.slug
        while current is not None and current not in seen:
            seen.add(current)
            path.append(current)
            parent = by_slug[current].parent if current in by_slug else ""
            current = parent or None
        if current is None:
            continue  # walked off a root or an undefined parent: no cycle
        cycle = tuple(path[path.index(current) :])
        found.setdefault(frozenset(cycle), cycle)
    return tuple(found.values())


def _validate_topic_index(index: TopicIndex) -> tuple[TopicIssue, ...]:
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
    for cycle in _parent_cycles(index):
        loop = " -> ".join((*cycle, cycle[0]))
        issues.append(
            TopicIssue(
                "error",
                "parent-cycle",
                f"parent: forms a cycle ({loop}); a slug cannot be its own ancestor, "
                "so neither its axis nor its ancestors are derivable",
                index.path,
            )
        )
    return tuple(issues)


def _topic_index_text(cwd: str | Path = ".") -> tuple[TopicIndex, str]:
    runtime = resolve_runtime(cwd)
    path = runtime.memory_dir / "topics.yaml"
    rel = f"{runtime.memory_dir.name}/topics.yaml"
    if not path.exists():
        raise TopicSuggestError("missing-topic-index", f"{rel} does not exist")
    if path.is_dir():
        raise TopicSuggestError("invalid-topic-index-path", f"{rel} is a directory, not a file")
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise TopicSuggestError("malformed-topic-index", f"{rel} is not valid UTF-8: {exc}") from exc
    except OSError as exc:
        raise TopicSuggestError("unreadable-topic-index", f"could not read {rel}: {exc}") from exc
    index = load_topic_index(cwd)
    if not raw.strip():
        raise TopicSuggestError("empty-topic-index", f"{rel} is empty")
    if not index.topics:
        if re.search(r"(?m)^\s*topics\s*:\s*(?:\[\s*\])?\s*$", raw):
            raise TopicSuggestError("empty-topic-index", f"{rel} defines no topics")
        raise TopicSuggestError("malformed-topic-index", f"{rel} could not be parsed into any topics")
    issues = [issue for issue in _validate_topic_index(index) if issue.severity == "error"]
    if issues:
        detail = "; ".join(f"{issue.kind}: {issue.detail}" for issue in issues)
        raise TopicSuggestError("malformed-topic-index", detail)
    return index, raw


def _read_suggestion_source(path: str | Path) -> tuple[Path, str]:
    source = Path(path)
    if not source.exists():
        raise TopicSuggestError("missing-input-file", f"{source} does not exist")
    if source.is_dir():
        raise TopicSuggestError("input-is-directory", f"{source} is a directory; pass a file path")
    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise TopicSuggestError("unreadable-input-file", f"could not read {source}: {exc}") from exc
    if b"\x00" in raw:
        raise TopicSuggestError("binary-input-file", f"{source} looks like a binary file")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TopicSuggestError("invalid-input-utf8", f"{source} is not valid UTF-8: {exc}") from exc
    return source, text


def _normalized_topic_tokens(text: str) -> tuple[str, ...]:
    tokens: set[str] = set()
    for match in TOPIC_TOKEN_RE.finditer(text.lower()):
        token = match.group(0).replace("_", "-")
        tokens.add(token)
        if "-" in token:
            tokens.update(part for part in token.split("-") if part)
    return tuple(sorted(tokens))


def suggest_topics_from_file(
    source_path: str | Path,
    *,
    cwd: str | Path = ".",
    top_k: int = TOPIC_COUNT_TARGET,
) -> tuple[Path, tuple[TopicSuggestion, ...]]:
    """Suggest active controlled topics for a file using deterministic lexical overlap."""
    index, _ = _topic_index_text(cwd)
    source, text = _read_suggestion_source(source_path)
    source_terms = tuple(term for term in _normalized_topic_tokens(f"{source.name}\n{text}") if len(term) >= 4)
    if not source_terms:
        return source, ()

    weights = {
        "slug": 12.0,
        "aliases": 10.0,
        "label": 8.0,
        "description": 3.0,
    }
    suggestions: list[TopicSuggestion] = []
    for record in index.topics:
        if record.status != "active":
            continue
        field_values = {
            "slug": (record.slug,),
            "aliases": record.aliases,
            "label": (record.label,) if record.label else (),
            "description": (record.description,) if record.description else (),
        }
        field_tokens = {
            field: tuple(sorted({token for value in values for token in _normalized_topic_tokens(value)}))
            for field, values in field_values.items()
        }
        score = 0.0
        matched_terms: set[str] = set()
        matched_fields: set[str] = set()
        evidence: list[tuple[str, tuple[str, ...]]] = []
        for field in ("slug", "aliases", "label", "description"):
            tokens = field_tokens[field]
            if not tokens:
                continue
            field_terms = tuple(sorted(set(source_terms) & set(tokens)))
            if not field_terms:
                continue
            score += weights[field] * len(field_terms)
            matched_terms.update(field_terms)
            matched_fields.add(field)
            evidence.append((field, field_terms))
        if score <= 0:
            continue
        suggestions.append(
            TopicSuggestion(
                topic=record,
                score=score,
                matched_terms=tuple(sorted(matched_terms)),
                matched_fields=tuple(sorted(matched_fields)),
                evidence=tuple(evidence),
            )
        )
    suggestions.sort(
        key=lambda item: (
            -item.score,
            -len(item.matched_fields),
            -len(item.matched_terms),
            item.topic.slug,
        )
    )
    limit = min(max(top_k, 0), TOPIC_COUNT_TARGET)
    return source, tuple(suggestions[:limit])


def check_topics(cwd: str | Path = ".") -> TopicsCheckResult:
    """Validate the vocabulary and every entry's stored ``topics:`` against it.

    Errors (exit non-zero): missing index while entries carry topics, malformed or duplicate
    slugs, alias collisions, and entry topics found in neither the canonical nor alias column.
    Warnings: deprecated-topic use and per-entry counts above ``TOPIC_COUNT_TARGET``.
    Info: defined topics no entry uses yet.
    """
    index = load_topic_index(cwd)
    issues: list[TopicIssue] = []

    issues.extend(_validate_topic_index(index))

    resolution = index.resolution()
    statuses = {record.slug: record.status for record in index.topics}
    used: set[str] = set()
    entries_checked = 0
    # Sidecar-attributed topics widen COVERAGE reporting but not validation:
    # every chunk below is still filtered on authored `chunk.topics`, so the
    # vocabulary checks, the deprecation warning, and TOPIC_COUNT_TARGET all
    # continue to judge only what a human wrote. TOPIC_COUNT_TARGET in
    # particular must never see the rolled-up union - 3 per decision across a
    # multi-decision entry is legitimate, and warning on it would flag exactly
    # the entries decision keying exists to serve.
    from .retrieval import augment_chunks_with_topic_sidecars

    all_chunks = augment_chunks_with_topic_sidecars(extract_memory_chunks(cwd, granularity="entry"), cwd)
    entries_with_inferred_topics_only = sum(
        1 for chunk in all_chunks if chunk.inferred_topics and not chunk.topics
    )
    chunks = [chunk for chunk in all_chunks if chunk.topics]
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
    return TopicsCheckResult(
        ok=ok,
        issues=tuple(issues),
        entries_checked=entries_checked,
        topics_defined=len(index.topics),
        entries_with_inferred_topics_only=entries_with_inferred_topics_only,
    )


def expand_topic_filter(cwd: str | Path, requested: list[str] | tuple[str, ...]) -> set[str]:
    """Expand requested topic slugs to the full match set for filtering.

    Each requested name resolves to its canonical topic; the match set contains that canonical
    plus every alias of it, so stored entries using either form match. Unknown names pass
    through as-is (fail-open - filtering never errors on vocabulary drift).

    Expansion also runs DOWNWARD through the hierarchy: asking for a parent matches entries tagged
    with any descendant, because only the most specific slug is ever stored. Without this, filtering
    on a parent would silently miss every entry that answered more precisely - the opposite of what
    the hierarchy is for. Expansion never runs upward: asking for a child must not drag in the
    parent's broader population.
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
            continue
        expanded.update(by_canonical.get(canonical, {canonical}))
        for descendant in index.descendants(canonical):
            expanded.update(by_canonical.get(descendant, {descendant}))
    return expanded
