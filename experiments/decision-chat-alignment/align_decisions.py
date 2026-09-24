"""Align a reproducible sample of Memory Seed decisions to local Codex rollout windows.

The source stores are read-only. Public outputs omit raw chat text; a separately named private output
directory receives the full review windows requested for manual audit.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import subprocess
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence
from zoneinfo import ZoneInfo

from memory_seed.retrieval import load_corpus


SEED = 20260924
SAMPLE_SIZE = 50
TIME_WINDOW_HOURS = 72
POSITIVE_CLOCK_DRIFT_HOURS = 2
WINDOW_RADIUS_TURNS = 2
PLAN_MODE_BONUS = 0.03
REASONING_SUMMARY_BONUS = 0.06
CODEX_ONLY_SAMPLE_SHA256 = "73b2dc2de7967859c9b138a6fbd56b9b10774a453bc5d3ba7b76c6c7795179a6"
LOCAL_TIMEZONE = ZoneInfo("Europe/London")
TOKEN_RE = re.compile(r"[A-Za-z0-9_./\\:-]{2,}")
IDENTIFIER_RE = re.compile(r"(?:[A-Za-z0-9_-]+[./\\:][A-Za-z0-9_./\\:-]+|[A-Za-z]+_[A-Za-z0-9_]+)")
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
STOPWORDS = {
    "about", "after", "again", "also", "because", "before", "being", "between", "both",
    "could", "decision", "from", "have", "into", "more", "only", "other", "should", "than",
    "that", "their", "there", "these", "they", "this", "through", "using", "were", "what",
    "when", "where", "which", "while", "will", "with", "would", "your", "memory", "seed",
}
CONFIDENCE_RULES = {
    "high": "score>=0.48, cosine>=0.24 or shared phrase>=6, and margin>=0.06",
    "medium": "score>=0.34, cosine>=0.14, and at least two supporting signal families",
    "low": "score>=0.22",
    "no_match": "score<0.22 or no candidate turn",
}


@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    entry_id: str
    ordinal: str
    title: str
    text: str
    entry_title: str | None
    source_path: str
    start_line: int
    end_line: int
    session_date: str
    decision_timestamp: str
    agent_type: str | None
    project_path: str | None
    branch: str | None
    commits: tuple[str, ...]
    source_refs: tuple[str, ...]

    @property
    def match_text(self) -> str:
        return "\n".join(filter(None, (self.entry_title, self.title, self.text, *self.source_refs)))


@dataclass(frozen=True)
class SessionMeta:
    rollout_id: str
    session_id: str
    legacy_session_id: str | None
    timestamp: str
    timestamp_utc: datetime
    cwd: str
    source_path: str
    originator: str | None
    source: str
    cli_version: str | None
    repository_url: str | None
    git_branch: str | None
    git_commit: str | None
    thread_source: str | None
    parent_thread_id: str | None
    agent_nickname: str | None
    agent_path: str | None
    agent_depth: int | None


@dataclass(frozen=True)
class NormalizedItem:
    session_id: str
    timestamp: str | None
    turn_number: int
    turn_id: str | None
    role: str
    text: str
    source_path: str
    source_ordinal: int | None


@dataclass
class TurnBlock:
    session: SessionMeta
    turn_number: int
    turn_id: str | None
    start_timestamp: str | None = None
    end_timestamp: str | None = None
    collaboration_mode: str | None = None
    mode_source: str | None = None
    mode_conflict: bool = False
    items: list[NormalizedItem] = field(default_factory=list)
    reasoning_summaries: list[str] = field(default_factory=list, repr=False)
    reasoning_summary_ordinals: list[int] = field(default_factory=list)
    reasoning_summary_timestamps: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(f"{item.role}: {item.text}" for item in self.items if item.text.strip())

    @property
    def reasoning_summary_text(self) -> str:
        return "\n".join(text for text in self.reasoning_summaries if text.strip())

    @property
    def start_utc(self) -> datetime | None:
        return parse_iso_timestamp(self.start_timestamp)

    @property
    def end_utc(self) -> datetime | None:
        return parse_iso_timestamp(self.end_timestamp)


def parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def decision_datetime_utc(value: datetime | None, fallback: date) -> datetime:
    local = value or datetime.combine(fallback, time(12, 0))
    if local.tzinfo is None:
        local = local.replace(tzinfo=LOCAL_TIMEZONE)
    return local.astimezone(timezone.utc)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def public_session_path(value: str) -> str:
    """Keep stable provenance without publishing the local user-profile path."""
    path = Path(value)
    parts = path.parts
    for index, part in enumerate(parts):
        if part.casefold() == ".codex":
            return Path(*parts[index:]).as_posix()
    return path.name


def normalize_path(value: str | Path) -> str:
    return os.path.normcase(os.path.normpath(str(value))).rstrip("\\/")


def normalize_remote(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip().lower().replace("\\", "/")
    if text.endswith(".git"):
        text = text[:-4]
    if text.startswith("git@github.com:"):
        text = "https://github.com/" + text.removeprefix("git@github.com:")
    return text.rstrip("/")


def repository_remote(repo_root: Path) -> str | None:
    result = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return normalize_remote(result.stdout) if result.returncode == 0 else None


def repository_worktree_roots(repo_root: Path) -> tuple[Path, ...]:
    """Return every currently registered checkout root for this repository."""
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    roots = [
        Path(line.removeprefix("worktree ")).resolve()
        for line in result.stdout.splitlines()
        if line.startswith("worktree ")
    ]
    if repo_root.resolve() not in roots:
        roots.append(repo_root.resolve())
    return tuple(roots)


def extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict):
            value = item.get("text") or item.get("input_text") or item.get("output_text")
            if isinstance(value, str):
                parts.append(value)
    return "\n".join(part.strip() for part in parts if part.strip())


def extract_reasoning_summaries(summary: Any) -> list[str]:
    """Return readable summaries without touching encrypted or raw reasoning fields."""
    if not isinstance(summary, list):
        return []
    return [
        str(item["text"]).strip()
        for item in summary
        if isinstance(item, dict)
        and item.get("type") == "summary_text"
        and isinstance(item.get("text"), str)
        and item["text"].strip()
    ]


def iter_rollout_paths(codex_home: Path) -> Iterator[Path]:
    for base in (codex_home / "sessions", codex_home / "archived_sessions"):
        if base.is_dir():
            yield from sorted(path for path in base.rglob("*.jsonl") if path.is_file())


def read_session_meta(path: Path) -> SessionMeta | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            line = next((line for line in handle if line.strip()), "")
        row = json.loads(line)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if row.get("type") != "session_meta" or not isinstance(row.get("payload"), dict):
        return None
    payload = row["payload"]
    stamp = parse_iso_timestamp(str(payload.get("timestamp") or row.get("timestamp") or ""))
    # ``id`` is the logical task identity. Continuation files can repeat it, while
    # spawned-agent ``session_id`` values can point back to the parent task. The
    # last UUID in the rollout filename is the storage identity of this file.
    session_id = str(payload.get("id") or "")
    filename_ids = UUID_RE.findall(path.stem)
    rollout_id = filename_ids[-1].lower() if filename_ids else session_id
    if not stamp or not session_id or not rollout_id:
        return None
    git = payload.get("git") if isinstance(payload.get("git"), dict) else {}
    source = payload.get("source")
    source_text = json.dumps(source, sort_keys=True) if isinstance(source, dict) else str(source or "")
    subagent = source.get("subagent") if isinstance(source, dict) else None
    thread_spawn = subagent.get("thread_spawn") if isinstance(subagent, dict) else None
    if not isinstance(thread_spawn, dict):
        thread_spawn = {}
    parent_thread_id = thread_spawn.get("parent_thread_id") or payload.get("parent_thread_id")
    agent_nickname = thread_spawn.get("agent_nickname") or payload.get("agent_nickname")
    agent_path = thread_spawn.get("agent_path")
    raw_depth = thread_spawn.get("depth")
    try:
        agent_depth = int(raw_depth) if raw_depth is not None else None
    except (TypeError, ValueError):
        agent_depth = None
    return SessionMeta(
        rollout_id=rollout_id,
        session_id=session_id,
        legacy_session_id=str(payload.get("session_id")) if payload.get("session_id") else None,
        timestamp=stamp.isoformat(),
        timestamp_utc=stamp,
        cwd=str(payload.get("cwd") or ""),
        source_path=str(path.resolve()),
        originator=str(payload.get("originator")) if payload.get("originator") is not None else None,
        source=source_text,
        cli_version=str(payload.get("cli_version")) if payload.get("cli_version") is not None else None,
        repository_url=normalize_remote(str(git.get("repository_url"))) if git.get("repository_url") else None,
        git_branch=str(git.get("branch")) if git.get("branch") else None,
        git_commit=str(git.get("commit_hash")) if git.get("commit_hash") else None,
        thread_source=str(payload.get("thread_source")) if payload.get("thread_source") else None,
        parent_thread_id=str(parent_thread_id) if parent_thread_id else None,
        agent_nickname=str(agent_nickname) if agent_nickname else None,
        agent_path=str(agent_path) if agent_path else None,
        agent_depth=agent_depth,
    )


def session_belongs_to_repo(meta: SessionMeta, repo_roots: Sequence[Path], remote: str | None) -> bool:
    cwd = normalize_path(meta.cwd)
    normalized_roots = [normalize_path(root) for root in repo_roots]
    cwd_match = any(cwd == root or cwd.startswith(root + os.sep) for root in normalized_roots)
    remote_match = bool(remote and meta.repository_url and normalize_remote(meta.repository_url) == remote)
    return cwd_match or remote_match


def repository_rollout_ids(
    metas: Sequence[SessionMeta], repo_roots: Sequence[Path], remote: str | None
) -> set[str]:
    """Return direct repository rollouts plus descendants linked through parent lineage."""
    eligible = {
        meta.rollout_id for meta in metas if session_belongs_to_repo(meta, repo_roots, remote)
    }
    changed = True
    while changed:
        changed = False
        eligible_task_ids = {
            meta.session_id for meta in metas if meta.rollout_id in eligible
        }
        for meta in metas:
            if (
                meta.rollout_id not in eligible
                and meta.parent_thread_id
                and meta.parent_thread_id in eligible_task_ids
            ):
                eligible.add(meta.rollout_id)
                changed = True
    return eligible


def validate_unique_rollouts(metas: Sequence[SessionMeta]) -> None:
    rollout_ids = [meta.rollout_id for meta in metas]
    source_paths = [meta.source_path for meta in metas]
    if len(rollout_ids) != len(set(rollout_ids)):
        raise RuntimeError("Rollout IDs are not unique; parent/child identities were collapsed")
    if len(source_paths) != len(set(source_paths)):
        raise RuntimeError("Rollout source paths are not unique")


def validate_unique_candidate_items(blocks: Sequence[TurnBlock]) -> None:
    coordinates = [
        (item.source_path, item.source_ordinal)
        for block in blocks
        for item in block.items
        if item.source_ordinal is not None
    ]
    if len(coordinates) != len(set(coordinates)):
        raise RuntimeError("Candidate corpus contains duplicate source path/ordinal coordinates")


def is_derived_review_session(meta: SessionMeta) -> bool:
    """Guardian/approval sessions replay another conversation and cannot be its origin."""
    return "guardian" in meta.source.casefold()


def is_replayed_transcript(text: str) -> bool:
    folded = " ".join(text.casefold().split())
    return folded.startswith("the following is the codex agent history")


def compact_tool_text(name: str, raw_input: str) -> str:
    """Keep provenance-bearing identifiers without indexing full authoring payloads."""
    found: list[str] = []
    for value in IDENTIFIER_RE.findall(raw_input):
        cleaned = value.strip("`.,;()[]{}\"'")
        folded = cleaned.casefold()
        if folded.startswith(("mse_", "ms-")) or ".memory-seed/sessions" in folded.replace("\\", "/"):
            continue
        if cleaned not in found:
            found.append(cleaned)
        if len(found) >= 20:
            break
    return " ".join([name, *found])


def parse_rollout(path: Path, meta: SessionMeta) -> list[TurnBlock]:
    blocks: dict[int, TurnBlock] = {}
    turn_number = 0
    current_turn_id: str | None = None
    last_timestamp: str | None = None

    def block() -> TurnBlock:
        nonlocal turn_number
        if turn_number == 0:
            turn_number = 1
        return blocks.setdefault(
            turn_number,
            TurnBlock(meta, turn_number, current_turn_id, start_timestamp=last_timestamp),
        )

    try:
        handle = path.open("r", encoding="utf-8")
    except OSError:
        return []
    with handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            row_timestamp = str(row.get("timestamp")) if row.get("timestamp") else None
            if row_timestamp:
                last_timestamp = row_timestamp
            if row.get("type") == "event_msg" and payload.get("type") == "task_started":
                if turn_number in blocks and row_timestamp:
                    blocks[turn_number].end_timestamp = row_timestamp
                turn_number += 1
                current_turn_id = str(payload.get("turn_id")) if payload.get("turn_id") else None
                mode = str(payload.get("collaboration_mode_kind") or "").strip().casefold() or None
                blocks[turn_number] = TurnBlock(
                    meta,
                    turn_number,
                    current_turn_id,
                    start_timestamp=row_timestamp,
                    collaboration_mode=mode,
                    mode_source="task_started" if mode else None,
                )
                continue
            if row.get("type") == "turn_context":
                collaboration = payload.get("collaboration_mode")
                context_mode = (
                    str(collaboration.get("mode") or "").strip().casefold()
                    if isinstance(collaboration, dict)
                    else ""
                )
                if context_mode:
                    current = block()
                    if current.collaboration_mode and current.collaboration_mode != context_mode:
                        current.mode_conflict = True
                    current.collaboration_mode = context_mode
                    current.mode_source = "turn_context"
                continue
            if row.get("type") != "response_item":
                continue
            payload_type = payload.get("type")
            if payload_type == "reasoning":
                summaries = extract_reasoning_summaries(payload.get("summary"))
                if summaries:
                    current = block()
                    current.reasoning_summaries.extend(summaries)
                    if isinstance(row.get("ordinal"), int):
                        current.reasoning_summary_ordinals.append(int(row["ordinal"]))
                    if row_timestamp:
                        current.reasoning_summary_timestamps.append(row_timestamp)
                continue
            role: str | None = None
            text = ""
            if payload_type == "message":
                raw_role = str(payload.get("role") or "").lower()
                if raw_role in {"user", "assistant"}:
                    role = raw_role
                    text = extract_text(payload.get("content"))
            elif payload_type == "agent_message":
                role = "assistant"
                text = extract_text(payload.get("content"))
            elif payload_type in {"custom_tool_call", "function_call"}:
                role = "tool"
                name = str(payload.get("name") or payload_type)
                raw_input = payload.get("input") or payload.get("arguments") or ""
                if not isinstance(raw_input, str):
                    raw_input = json.dumps(raw_input, ensure_ascii=False, sort_keys=True)
                text = compact_tool_text(name, raw_input)
            if role == "user" and is_replayed_transcript(text):
                continue
            if not role or not text.strip():
                continue
            block().items.append(
                NormalizedItem(
                    session_id=meta.session_id,
                    timestamp=str(row.get("timestamp")) if row.get("timestamp") else None,
                    turn_number=turn_number,
                    turn_id=current_turn_id,
                    role=role,
                    text=text.strip(),
                    source_path=meta.source_path,
                    source_ordinal=int(row["ordinal"]) if isinstance(row.get("ordinal"), int) else None,
                )
            )
    ordered = [blocks[key] for key in sorted(blocks)]
    if ordered and ordered[-1].end_timestamp is None:
        ordered[-1].end_timestamp = last_timestamp or ordered[-1].start_timestamp
    return ordered


def anchor_turn(blocks: Sequence[TurnBlock], decision_time: datetime) -> TurnBlock | None:
    """Find the active decision-minute turn, then the nearest temporal fallback."""
    minute_end = decision_time + timedelta(minutes=1)
    timestamped = [candidate for candidate in blocks if candidate.start_utc]
    containing = [
        candidate for candidate in timestamped
        if candidate.start_utc <= decision_time
        and (candidate.end_utc is None or decision_time < candidate.end_utc)
    ]
    if containing:
        return max(containing, key=lambda candidate: candidate.start_utc)
    intersecting = [
        candidate for candidate in timestamped
        if candidate.start_utc < minute_end
        and (candidate.end_utc is None or candidate.end_utc > decision_time)
    ]
    if intersecting:
        return min(
            intersecting,
            key=lambda candidate: abs((decision_time - candidate.start_utc).total_seconds()),
        )
    preceding = [candidate for candidate in timestamped if candidate.start_utc <= decision_time]
    if preceding:
        return max(preceding, key=lambda candidate: candidate.start_utc)
    return min(timestamped, key=lambda candidate: candidate.start_utc) if timestamped else None


def load_decisions(repo_root: Path) -> list[DecisionRecord]:
    records: list[DecisionRecord] = []
    for chunk in load_corpus(repo_root, "decision"):
        # Persistent corpus projections created before typed records may deserialize
        # without the later additive attribute. Absence means legacy Decision.
        record_kind = getattr(chunk, "record_kind", None)
        if chunk.granularity != "decision" or record_kind not in {None, "decision"}:
            continue
        if not chunk.entry_id or ":d" not in chunk.chunk_id:
            continue
        stamp = decision_datetime_utc(chunk.entry_datetime, chunk.session_date)
        refs = tuple(
            f"{ref.path}#{ref.anchor}" if ref.anchor else ref.path
            for ref in getattr(chunk, "source_refs", ())
        )
        records.append(
            DecisionRecord(
                decision_id=chunk.chunk_id,
                entry_id=chunk.entry_id,
                ordinal=chunk.chunk_id.rsplit(":", 1)[-1],
                title=chunk.title,
                text=chunk.text,
                entry_title=chunk.entry_title,
                source_path=chunk.source_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                session_date=chunk.session_date.isoformat(),
                decision_timestamp=stamp.isoformat(),
                agent_type=chunk.agent_type,
                project_path=chunk.project_path,
                branch=chunk.branch,
                commits=tuple(getattr(chunk, "commits", ())),
                source_refs=refs,
            )
        )
    return sorted(records, key=lambda record: record.decision_id)


def deterministic_sample(records: Sequence[DecisionRecord], size: int, seed: int) -> list[DecisionRecord]:
    if len(records) < size:
        raise ValueError(f"sample size {size} exceeds decision population {len(records)}")
    rng = random.Random(seed)
    population = sorted(records, key=lambda record: record.decision_id)
    return sorted(rng.sample(population, size), key=lambda record: record.decision_id)


def validate_sample_identity(
    *, decision_agent: str | None, sample_size: int, seed: int, sample_hash: str
) -> None:
    if (
        (decision_agent or "").casefold() == "codex"
        and sample_size == SAMPLE_SIZE
        and seed == SEED
        and sample_hash != CODEX_ONLY_SAMPLE_SHA256
    ):
        raise RuntimeError(
            "Codex-only default sample hash changed: "
            f"expected {CODEX_ONLY_SAMPLE_SHA256}, got {sample_hash}"
        )


def fixed_sample(records: Sequence[DecisionRecord], decision_ids: Sequence[str]) -> list[DecisionRecord]:
    by_id = {record.decision_id: record for record in records}
    missing = [decision_id for decision_id in decision_ids if decision_id not in by_id]
    if missing:
        raise RuntimeError(
            "Fixed sample decisions are missing from the current corpus: " + ", ".join(missing)
        )
    return [by_id[decision_id] for decision_id in decision_ids]


def read_sample_ids(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    metadata = payload.get("metadata") if isinstance(payload, dict) else None
    decision_ids = metadata.get("sample_ids") if isinstance(metadata, dict) else None
    if not isinstance(decision_ids, list) or not all(isinstance(value, str) for value in decision_ids):
        raise RuntimeError(f"Sample source {path} has no valid metadata.sample_ids list")
    return decision_ids


def filter_decisions(
    records: Sequence[DecisionRecord], agent_type: str | None
) -> list[DecisionRecord]:
    """Apply an exact, case-insensitive author tag filter before sampling."""
    if not agent_type:
        return sorted(records, key=lambda record: record.decision_id)
    expected = agent_type.casefold()
    return sorted(
        (record for record in records if (record.agent_type or "").casefold() == expected),
        key=lambda record: record.decision_id,
    )


def tokens(text: str) -> list[str]:
    return [token.casefold() for token in TOKEN_RE.findall(text)]


def distinctive_tokens(text: str) -> set[str]:
    return {token for token in tokens(text) if len(token) >= 4 and token not in STOPWORDS}


def identifiers(text: str) -> set[str]:
    return {value.casefold().strip("`.,;()[]{}") for value in IDENTIFIER_RE.findall(text)}


def longest_shared_phrase(left: str, right: str) -> int:
    from difflib import SequenceMatcher

    left_tokens = tokens(left)
    right_tokens = tokens(right)
    if not left_tokens or not right_tokens:
        return 0
    return SequenceMatcher(None, left_tokens, right_tokens, autojunk=False).find_longest_match().size


def actor_compatible(decision: DecisionRecord, session: SessionMeta) -> bool:
    agent = (decision.agent_type or "").casefold()
    origin = (session.originator or "").casefold()
    if agent.startswith("claude"):
        agent = "claude"
    elif agent.startswith("codex"):
        agent = "codex"
    return bool(agent and agent in origin)


def signal_score(
    decision: DecisionRecord,
    block: TurnBlock,
    cosine: float,
) -> dict[str, Any]:
    d_tokens = distinctive_tokens(decision.match_text)
    b_tokens = distinctive_tokens(block.text)
    overlap = d_tokens & b_tokens
    token_overlap = len(overlap) / max(1, min(len(d_tokens), 30))
    d_ids = identifiers(decision.match_text)
    b_ids = identifiers(block.text)
    id_overlap = d_ids & b_ids
    identifier_overlap = len(id_overlap) / max(1, min(len(d_ids), 10)) if d_ids else 0.0
    phrase = longest_shared_phrase(decision.match_text, block.text)
    phrase_score = min(1.0, phrase / 10.0)
    decision_time = parse_iso_timestamp(decision.decision_timestamp) or block.session.timestamp_utc
    candidate_time = block.start_utc or block.session.timestamp_utc
    hours = abs((decision_time - candidate_time).total_seconds()) / 3600.0
    temporal = math.exp(-hours / 36.0)
    branch_match = bool(
        decision.branch and block.session.git_branch
        and decision.branch.casefold() == block.session.git_branch.casefold()
    )
    commit_match = bool(
        block.session.git_commit
        and any(
            commit.startswith(block.session.git_commit) or block.session.git_commit.startswith(commit)
            for commit in decision.commits
        )
    )
    actor = actor_compatible(decision, block.session)
    score = (
        0.60 * cosine
        + 0.12 * min(1.0, token_overlap)
        + 0.10 * phrase_score
        + 0.08 * min(1.0, identifier_overlap)
        + 0.06 * temporal
        + 0.04 * float(actor)
        + 0.08 * float(branch_match)
        + 0.10 * float(commit_match)
    )
    return {
        "score": min(1.0, score),
        "cosine": cosine,
        "token_overlap": token_overlap,
        "shared_tokens": sorted(overlap, key=lambda value: (-len(value), value))[:12],
        "longest_shared_phrase_tokens": phrase,
        "identifier_overlap": identifier_overlap,
        "shared_identifiers": sorted(id_overlap)[:12],
        "time_distance_hours": hours,
        "temporal_score": temporal,
        "actor_compatible": actor,
        "branch_match": branch_match,
        "commit_match": commit_match,
    }


def auxiliary_ranking_signals(
    *,
    collaboration_mode: str | None,
    visible_supported: bool,
    summary_cosine: float,
) -> dict[str, float]:
    plan_bonus = PLAN_MODE_BONUS if collaboration_mode == "plan" and visible_supported else 0.0
    summary_bonus = REASONING_SUMMARY_BONUS * max(0.0, min(1.0, summary_cosine))
    return {
        "plan_bonus": plan_bonus,
        "reasoning_summary_bonus": summary_bonus,
        "ranking_bonus": plan_bonus + summary_bonus,
    }


def confidence_for(best: dict[str, Any] | None, margin: float) -> str:
    if not best:
        return "No match"
    score = best["score"]
    cosine = best["cosine"]
    phrase = best["longest_shared_phrase_tokens"]
    supporting = sum(
        (
            best["token_overlap"] >= 0.10,
            phrase >= 4,
            best["identifier_overlap"] > 0,
            best["actor_compatible"],
            best["branch_match"],
            best["commit_match"],
        )
    )
    if score >= 0.48 and (cosine >= 0.24 or phrase >= 6) and margin >= 0.06:
        return "High"
    if score >= 0.34 and cosine >= 0.14 and supporting >= 2:
        return "Medium"
    if score >= 0.22:
        return "Low"
    return "No match"


def bounded_window(blocks: Sequence[TurnBlock], winning_index: int) -> list[TurnBlock]:
    winning_turn = blocks[winning_index].turn_number
    return [
        block for block in blocks
        if winning_turn - WINDOW_RADIUS_TURNS <= block.turn_number <= winning_turn + WINDOW_RADIUS_TURNS
    ]


def public_window(window: Sequence[TurnBlock]) -> dict[str, Any]:
    items = [item for block in window for item in block.items]
    raw = "\n".join(f"{item.role}: {item.text}" for item in items)
    return {
        "turn_start": min((block.turn_number for block in window), default=None),
        "turn_end": max((block.turn_number for block in window), default=None),
        "message_count": len(items),
        "roles": sorted({item.role for item in items}),
        "source_ordinals": [item.source_ordinal for item in items if item.source_ordinal is not None],
        "sha256": sha256_text(raw),
    }


def private_window(window: Sequence[TurnBlock]) -> list[dict[str, Any]]:
    return [asdict(item) for block in window for item in block.items]


def failure_mode(decision: DecisionRecord, confidence: str, ambiguous: bool, has_actor_session: bool) -> str | None:
    if confidence == "High" or confidence == "Medium":
        return "multiple plausible source windows" if ambiguous else None
    if not has_actor_session and (decision.agent_type or "").casefold() != "codex":
        return "decision appears to have been created outside retained Codex conversation history"
    if ambiguous:
        return "multiple conversations discuss similar material"
    if confidence == "No match":
        return "no sufficiently similar conversation window in the temporal candidate set"
    return "decision wording may be rewritten, synthesized across turns, or weakly distinctive"


def turn_temporal_relation(block: TurnBlock, decision_time: datetime) -> str:
    if block.start_utc and block.start_utc <= decision_time and (
        block.end_utc is None or decision_time < block.end_utc
    ):
        return "active_at_decision_time"
    if block.start_utc and block.start_utc < decision_time + timedelta(minutes=1) and (
        block.end_utc is None or block.end_utc > decision_time
    ):
        return "intersects_decision_minute"
    if block.start_utc and block.start_utc <= decision_time:
        return "nearest_preceding_turn"
    return "nearest_following_turn"


def align(
    decisions: Sequence[DecisionRecord],
    sessions: Sequence[SessionMeta],
    blocks_by_session: dict[str, list[TurnBlock]],
) -> list[dict[str, Any]]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    all_blocks = [block for session in sessions for block in blocks_by_session.get(session.rollout_id, [])]
    validate_unique_candidate_items(all_blocks)
    if not all_blocks:
        return []
    decision_texts = [decision.match_text for decision in decisions]
    visible_texts = [block.text for block in all_blocks]
    summary_texts = [block.reasoning_summary_text for block in all_blocks]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        analyzer="word",
        ngram_range=(1, 2),
        sublinear_tf=True,
        max_features=150_000,
        token_pattern=r"(?u)\b[A-Za-z0-9_./\\:-]{2,}\b",
    )
    vectorizer.fit([*decision_texts, *visible_texts, *summary_texts])
    decision_matrix = vectorizer.transform(decision_texts)
    visible_similarities = cosine_similarity(decision_matrix, vectorizer.transform(visible_texts))
    summary_similarities = cosine_similarity(decision_matrix, vectorizer.transform(summary_texts))
    session_blocks: dict[str, list[tuple[int, TurnBlock]]] = defaultdict(list)
    for index, block in enumerate(all_blocks):
        session_blocks[block.session.rollout_id].append((index, block))

    output: list[dict[str, Any]] = []
    for decision_index, decision in enumerate(decisions):
        decision_time = parse_iso_timestamp(decision.decision_timestamp)
        eligible_session_ids: set[str] = set()
        eligible_rollout_ids: set[str] = set()
        scored_candidates: list[dict[str, Any]] = []
        if decision_time:
            for session in sessions:
                if not actor_compatible(decision, session):
                    continue
                indexed_blocks = session_blocks.get(session.rollout_id, [])
                blocks = [block for _global_index, block in indexed_blocks]
                anchor = anchor_turn(blocks, decision_time)
                if not anchor or not anchor.start_utc:
                    continue
                anchor_delta_hours = (decision_time - anchor.start_utc).total_seconds() / 3600.0
                if not -POSITIVE_CLOCK_DRIFT_HOURS <= anchor_delta_hours <= TIME_WINDOW_HOURS:
                    continue
                eligible_session_ids.add(session.session_id)
                eligible_rollout_ids.add(session.rollout_id)
                anchor_index = blocks.index(anchor)
                predecessor_rows: list[tuple[int, int, TurnBlock]] = []
                for local_index, (global_index, candidate) in enumerate(indexed_blocks[: anchor_index + 1]):
                    if not candidate.start_utc:
                        continue
                    candidate_delta_hours = (
                        decision_time - candidate.start_utc
                    ).total_seconds() / 3600.0
                    if not -POSITIVE_CLOCK_DRIFT_HOURS <= candidate_delta_hours <= TIME_WINDOW_HOURS:
                        continue
                    source_text = candidate.text + "\n" + candidate.reasoning_summary_text
                    if decision.entry_id.casefold() in source_text.casefold():
                        continue
                    predecessor_rows.append((local_index, global_index, candidate))
                visible_top = {
                    global_index
                    for _local_index, global_index, _candidate in sorted(
                        predecessor_rows,
                        key=lambda row: float(visible_similarities[decision_index, row[1]]),
                        reverse=True,
                    )[:3]
                }
                selected_indices = set(visible_top)
                selected_indices.update(
                    global_index
                    for _local_index, global_index, candidate in predecessor_rows
                    if candidate is anchor
                    or candidate.collaboration_mode == "plan"
                    or float(summary_similarities[decision_index, global_index]) > 0.0
                )
                for local_index, global_index, candidate in predecessor_rows:
                    if global_index not in selected_indices:
                        continue
                    cosine = float(visible_similarities[decision_index, global_index])
                    summary_cosine = float(summary_similarities[decision_index, global_index])
                    signals = signal_score(decision, candidate, cosine)
                    visible_supported = bool(
                        cosine >= 0.08
                        or signals["token_overlap"] >= 0.10
                        or signals["identifier_overlap"] > 0
                        or signals["longest_shared_phrase_tokens"] >= 4
                        or signals["branch_match"]
                        or signals["commit_match"]
                    )
                    auxiliary = auxiliary_ranking_signals(
                        collaboration_mode=candidate.collaboration_mode,
                        visible_supported=visible_supported,
                        summary_cosine=summary_cosine,
                    )
                    signals.update(auxiliary)
                    signals.update(
                        {
                            "ranking_score": min(1.0, signals["score"] + auxiliary["ranking_bonus"]),
                            "reasoning_summary_cosine": summary_cosine,
                            "reasoning_summary_used": bool(
                                candidate.reasoning_summaries and summary_cosine > 0.0
                            ),
                            "plan_mode_used": auxiliary["plan_bonus"] > 0.0,
                        }
                    )
                    sources = []
                    if candidate is anchor:
                        sources.append("temporal_anchor")
                    if global_index in visible_top:
                        sources.append("visible_top_three")
                    if candidate.collaboration_mode == "plan":
                        sources.append("plan_mode")
                    if candidate.reasoning_summaries and summary_cosine > 0.0:
                        sources.append("reasoning_summary")
                    scored_candidates.append(
                        {
                            "session": session,
                            "best_block": candidate,
                            "anchor": anchor,
                            "signals": signals,
                            "window": bounded_window(blocks, local_index),
                            "candidate_sources": sources,
                            "predecessor_turns_searched": len(predecessor_rows),
                        }
                    )
        scored_candidates.sort(key=lambda item: item["signals"]["ranking_score"], reverse=True)
        best = scored_candidates[0] if scored_candidates else None
        second = scored_candidates[1] if len(scored_candidates) > 1 else None
        best_score = best["signals"]["score"] if best else 0.0
        base_runners = [candidate["signals"]["score"] for candidate in scored_candidates[1:]]
        second_score = max(base_runners, default=0.0)
        margin = best_score - second_score
        ranking_score = best["signals"]["ranking_score"] if best else 0.0
        second_ranking_score = second["signals"]["ranking_score"] if second else 0.0
        ranking_margin = ranking_score - second_ranking_score
        confidence = confidence_for(best["signals"] if best else None, margin)
        ambiguous = bool(
            second
            and (
                (second_score >= 0.22 and (second_score >= 0.85 * best_score or margin < 0.06))
                or (
                    second_ranking_score >= 0.22
                    and (second_ranking_score >= 0.85 * ranking_score or ranking_margin < 0.06)
                )
            )
        )
        has_actor_session = bool(eligible_session_ids)
        base_best = max(scored_candidates, key=lambda item: item["signals"]["score"], default=None)
        plan_best = max(
            scored_candidates,
            key=lambda item: item["signals"]["score"] + item["signals"]["plan_bonus"],
            default=None,
        )

        def candidate_identity(candidate: dict[str, Any] | None) -> tuple[str, int] | None:
            if not candidate:
                return None
            return candidate["session"].rollout_id, candidate["best_block"].turn_number

        def candidate_payload(candidate: dict[str, Any] | None, private: bool = False) -> dict[str, Any] | None:
            if not candidate:
                return None
            session = candidate["session"]
            block = candidate["best_block"]
            anchor = candidate["anchor"]
            summary_text = block.reasoning_summary_text
            payload = {
                "session_id": session.session_id,
                "rollout_id": session.rollout_id,
                "conversation_timestamp": session.timestamp,
                "source_path": session.source_path if private else public_session_path(session.source_path),
                "cwd": session.cwd if private else "repository checkout/worktree",
                "originator": session.originator,
                "source": session.source,
                "git_branch": session.git_branch,
                "git_commit": session.git_commit,
                "winning_turn": block.turn_number,
                "winning_turn_id": block.turn_id,
                "anchor_turn": anchor.turn_number,
                "anchor_turn_id": anchor.turn_id,
                "turn_start_timestamp": block.start_timestamp,
                "turn_end_timestamp": block.end_timestamp,
                "anchor_start_timestamp": anchor.start_timestamp,
                "anchor_end_timestamp": anchor.end_timestamp,
                "temporal_relation": turn_temporal_relation(block, decision_time),
                "collaboration_mode": block.collaboration_mode,
                "mode_source": block.mode_source,
                "mode_conflict": block.mode_conflict,
                "predecessor_turns_searched": candidate["predecessor_turns_searched"],
                "candidate_sources": candidate["candidate_sources"],
                "reasoning_summary": {
                    "used": candidate["signals"]["reasoning_summary_used"],
                    "record_count": len(block.reasoning_summaries),
                    "source_ordinals": block.reasoning_summary_ordinals,
                    "timestamps": block.reasoning_summary_timestamps,
                    "sha256": sha256_text(summary_text) if summary_text else None,
                },
                "signals": candidate["signals"],
                "window": private_window(candidate["window"]) if private else public_window(candidate["window"]),
            }
            return payload

        public = {
            "decision": asdict(decision),
            "candidate_session_count": len(eligible_session_ids),
            "candidate_rollout_count": len(eligible_rollout_ids),
            "best_candidate": candidate_payload(best),
            "second_best_candidate": candidate_payload(second),
            "confidence": confidence,
            "score_margin": margin,
            "ranking_score_margin": ranking_margin,
            "plan_changed_winner": candidate_identity(plan_best) != candidate_identity(base_best),
            "reasoning_summary_changed_winner": candidate_identity(best) != candidate_identity(plan_best),
            "reasoning_summary_surfaced_outside_visible_top_three": bool(
                best
                and best["signals"]["reasoning_summary_used"]
                and "visible_top_three" not in best["candidate_sources"]
            ),
            "appears_unique": not ambiguous,
            "ambiguity": "competitive second source window" if ambiguous else None,
            "diagnostic_failure_mode": failure_mode(decision, confidence, ambiguous, has_actor_session),
        }
        public["_private_best_candidate"] = candidate_payload(best, private=True)
        public["_private_second_candidate"] = candidate_payload(second, private=True)
        output.append(public)
    return output


def evidence_lines(candidate: dict[str, Any] | None) -> str:
    if not candidate:
        return "no candidate"
    signal = candidate["signals"]
    parts = [
        f"base score {signal['score']:.3f}",
        f"ranking score {signal['ranking_score']:.3f}",
        f"TF-IDF {signal['cosine']:.3f}",
        f"phrase {signal['longest_shared_phrase_tokens']} tokens",
        f"time {signal['time_distance_hours']:.1f}h",
    ]
    if signal["shared_identifiers"]:
        parts.append("identifiers " + ", ".join(signal["shared_identifiers"][:5]))
    if signal["branch_match"]:
        parts.append("branch match")
    if signal["commit_match"]:
        parts.append("commit match")
    if signal["actor_compatible"]:
        parts.append("actor compatible")
    if signal["plan_mode_used"]:
        parts.append(f"Plan bonus {signal['plan_bonus']:.3f}")
    if signal["reasoning_summary_used"]:
        parts.append(
            f"summary TF-IDF {signal['reasoning_summary_cosine']:.3f} "
            f"(+{signal['reasoning_summary_bonus']:.3f})"
        )
    return "; ".join(parts)


def render_review(rows: Sequence[dict[str, Any]], *, include_raw: bool) -> str:
    lines = [
        "# Decision-to-chat alignment review",
        "",
        f"Sample: {len(rows)} decisions; seed `{SEED}`; candidate turns start within "
        f"{TIME_WINDOW_HOURS}h before the decision (plus {POSITIVE_CLOCK_DRIFT_HOURS}h clock drift);",
        f"source window `+/-{WINDOW_RADIUS_TURNS}` turns around the strongest turn.",
        "",
    ]
    for index, row in enumerate(rows, 1):
        decision = row["decision"]
        best = row.get("_private_best_candidate") if include_raw else row.get("best_candidate")
        second = row.get("_private_second_candidate") if include_raw else row.get("second_best_candidate")
        lines.extend(
            [
                f"## {index}. {decision['decision_id']} - {row['confidence']}",
                "",
                f"- Decision timestamp: `{decision['decision_timestamp']}`",
                f"- Decision source: `{decision['source_path']}:{decision['start_line']}`",
                f"- Candidate session: `{best['session_id'] if best else 'none'}`",
                f"- Conversation timestamp: `{best['conversation_timestamp'] if best else 'unknown'}`",
                f"- Source: `{best['source_path'] if best else 'none'}`",
                f"- Anchor turn: `{best['anchor_turn'] if best else 'none'}`",
                f"- Winning turn interval: `{best['turn_start_timestamp'] if best else 'unknown'}` to "
                f"`{best['turn_end_timestamp'] if best else 'unknown'}`",
                f"- Collaboration mode: `{best['collaboration_mode'] if best else 'unknown'}`",
                f"- Evidence: {evidence_lines(best)}",
                f"- Unique: `{row['appears_unique']}`",
                f"- Ambiguity: {row['ambiguity'] or 'none recorded'}",
                f"- Diagnostic failure mode: {row['diagnostic_failure_mode'] or 'none recorded'}",
                f"- Second best: `{second['session_id'] if second else 'none'}`"
                + (f" ({evidence_lines(second)})" if second else ""),
                "",
                "Decision record:",
                "",
                "```text",
                decision["text"].strip(),
                "```",
                "",
            ]
        )
        if include_raw and best:
            lines.extend(["Candidate source window:", "", "```text"])
            for item in best["window"]:
                lines.append(
                    f"[turn {item['turn_number']} | {item['role']} | ordinal {item['source_ordinal']}] "
                    f"{item['text']}"
                )
            lines.extend(["```", ""])
        elif best:
            window = best["window"]
            lines.extend(
                [
                    "Candidate source window (coordinates only; raw text is in the private audit):",
                    "",
                    f"- turns `{window['turn_start']}..{window['turn_end']}`",
                    f"- JSONL ordinals `{window['source_ordinals']}`",
                    f"- messages `{window['message_count']}`; SHA-256 `{window['sha256']}`",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def summarize(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    counts = {name: sum(row["confidence"] == name for row in rows) for name in ("High", "Medium", "Low", "No match")}
    aligned = counts["High"] + counts["Medium"]
    competitive = sum(not row["appears_unique"] for row in rows)
    modes: dict[str, int] = defaultdict(int)
    for row in rows:
        if row["diagnostic_failure_mode"]:
            modes[row["diagnostic_failure_mode"]] += 1
    return {
        "sample_size": len(rows),
        "confidence_counts": counts,
        "automatically_aligned_high_or_medium": aligned,
        "automatically_aligned_percent": 100.0 * aligned / len(rows) if rows else 0.0,
        "multiple_plausible_windows": competitive,
        "multiple_plausible_percent": 100.0 * competitive / len(rows) if rows else 0.0,
        "plan_changed_winner": sum(bool(row.get("plan_changed_winner")) for row in rows),
        "reasoning_summary_changed_winner": sum(
            bool(row.get("reasoning_summary_changed_winner")) for row in rows
        ),
        "reasoning_summary_surfaced_outside_visible_top_three": sum(
            bool(row.get("reasoning_summary_surfaced_outside_visible_top_three")) for row in rows
        ),
        "diagnostic_failure_modes": dict(sorted(modes.items())),
    }


def write_outputs(
    output_dir: Path,
    private_dir: Path,
    rows: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    private_dir.mkdir(parents=True, exist_ok=True)
    public_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    for row in rows:
        public = {key: value for key, value in row.items() if not key.startswith("_private_")}
        public_rows.append(public)
        private = dict(public)
        private["best_candidate"] = row.get("_private_best_candidate")
        private["second_best_candidate"] = row.get("_private_second_candidate")
        private_rows.append(private)
    public_metadata = {
        key: value
        for key, value in metadata.items()
        if key not in {"analysis_checkout", "repository_worktree_roots", "codex_home"}
    }
    public_metadata.update(
        {
            "analysis_checkout": "local owned worktree",
            "repository_worktree_root_count": len(metadata["repository_worktree_roots"]),
            "codex_home": ".codex (local user data store)",
        }
    )
    result = {"metadata": public_metadata, "summary": summarize(rows), "alignments": public_rows}
    private_result = {"metadata": metadata, "summary": summarize(rows), "alignments": private_rows}
    (output_dir / "alignments.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "review.md").write_text(render_review(rows, include_raw=False), encoding="utf-8")
    (private_dir / "alignments-private.json").write_text(
        json.dumps(private_result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (private_dir / "review-private.md").write_text(render_review(rows, include_raw=True), encoding="utf-8")
    with (output_dir / "alignments.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "decision_id", "decision_timestamp", "agent_type", "confidence", "session_id",
                "conversation_timestamp", "source_path", "anchor_turn", "winning_turn",
                "turn_start_timestamp", "turn_end_timestamp", "collaboration_mode", "score",
                "ranking_score", "plan_bonus", "reasoning_summary_bonus", "score_margin",
                "ranking_score_margin", "plan_changed_winner", "reasoning_summary_changed_winner",
                "appears_unique", "ambiguity", "diagnostic_failure_mode",
            ),
        )
        writer.writeheader()
        for row in public_rows:
            decision = row["decision"]
            best = row["best_candidate"] or {}
            writer.writerow(
                {
                    "decision_id": decision["decision_id"],
                    "decision_timestamp": decision["decision_timestamp"],
                    "agent_type": decision["agent_type"],
                    "confidence": row["confidence"],
                    "session_id": best.get("session_id"),
                    "conversation_timestamp": best.get("conversation_timestamp"),
                    "source_path": best.get("source_path"),
                    "anchor_turn": best.get("anchor_turn"),
                    "winning_turn": best.get("winning_turn"),
                    "turn_start_timestamp": best.get("turn_start_timestamp"),
                    "turn_end_timestamp": best.get("turn_end_timestamp"),
                    "collaboration_mode": best.get("collaboration_mode"),
                    "score": (best.get("signals") or {}).get("score"),
                    "ranking_score": (best.get("signals") or {}).get("ranking_score"),
                    "plan_bonus": (best.get("signals") or {}).get("plan_bonus"),
                    "reasoning_summary_bonus": (best.get("signals") or {}).get(
                        "reasoning_summary_bonus"
                    ),
                    "score_margin": row["score_margin"],
                    "ranking_score_margin": row["ranking_score_margin"],
                    "plan_changed_winner": row["plan_changed_winner"],
                    "reasoning_summary_changed_winner": row["reasoning_summary_changed_winner"],
                    "appears_unique": row["appears_unique"],
                    "ambiguity": row["ambiguity"],
                    "diagnostic_failure_mode": row["diagnostic_failure_mode"],
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument(
        "--decision-agent",
        help="sample only decisions whose agent_type exactly matches this value (case-insensitive)",
    )
    parser.add_argument(
        "--sample-ids-from",
        type=Path,
        help="reuse metadata.sample_ids from an earlier alignment JSON instead of resampling",
    )
    args = parser.parse_args()

    repo_root = args.repo.resolve()
    remote = repository_remote(repo_root)
    repo_roots = repository_worktree_roots(repo_root)
    unfiltered_population = load_decisions(repo_root)
    population = filter_decisions(unfiltered_population, args.decision_agent)
    if args.sample_ids_from:
        fixed_ids = read_sample_ids(args.sample_ids_from.resolve())
        if len(fixed_ids) != args.sample_size:
            raise RuntimeError(
                f"Fixed sample contains {len(fixed_ids)} decisions, expected {args.sample_size}"
            )
        sample = fixed_sample(population, fixed_ids)
    else:
        sample = deterministic_sample(population, args.sample_size, args.seed)
    sample_hash = sha256_text("\n".join(decision.decision_id for decision in sample))
    validate_sample_identity(
        decision_agent=args.decision_agent,
        sample_size=args.sample_size,
        seed=args.seed,
        sample_hash=sample_hash,
    )

    all_paths = list(iter_rollout_paths(args.codex_home.resolve()))
    metas = [meta for path in all_paths if (meta := read_session_meta(path)) is not None]
    validate_unique_rollouts(metas)
    eligible_rollout_ids = repository_rollout_ids(metas, repo_roots, remote)
    repo_metas = [
        meta for meta in metas
        if meta.rollout_id in eligible_rollout_ids and not is_derived_review_session(meta)
    ]
    # Turn timestamps, not session starts, determine temporal eligibility. Parse
    # every actor-compatible repository rollout so long-running sessions are not
    # falsely excluded before their individual turns are inspected.
    selected_metas = [
        meta for meta in repo_metas if any(actor_compatible(decision, meta) for decision in sample)
    ]
    blocks_by_session: dict[str, list[TurnBlock]] = {}
    for index, meta in enumerate(selected_metas, 1):
        blocks_by_session[meta.rollout_id] = parse_rollout(Path(meta.source_path), meta)
        if index % 100 == 0:
            print(f"parsed {index}/{len(selected_metas)} candidate rollouts", flush=True)

    rows = align(sample, selected_metas, blocks_by_session)
    metadata = {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_checkout": str(repo_root),
        "repository_worktree_roots": [str(root) for root in repo_roots],
        "repository_remote": remote,
        "codex_home": str(args.codex_home.resolve()),
        "unfiltered_population_size": len(unfiltered_population),
        "population_size": len(population),
        "decision_agent_filter": args.decision_agent,
        "sample_size": len(sample),
        "sample_seed": args.seed,
        "sample_method": (
            (
                f"fixed decision IDs from {args.sample_ids_from.as_posix()}"
                if args.sample_ids_from
                else "uniform without replacement from decision_id-sorted canonical Decision chunks"
            )
            + (f" filtered to agent_type={args.decision_agent!r}" if args.decision_agent else "")
        ),
        "sample_ids": [decision.decision_id for decision in sample],
        "sample_ids_sha256": sample_hash,
        "rollout_files_discovered": len(all_paths),
        "rollout_metadata_parsed": len(metas),
        "repository_rollouts": len(repo_metas),
        "lineage_inherited_repository_rollouts": sum(
            1 for meta in repo_metas
            if not session_belongs_to_repo(meta, repo_roots, remote)
        ),
        "temporal_candidate_rollouts": len(selected_metas),
        "normalized_turn_blocks": sum(len(blocks) for blocks in blocks_by_session.values()),
        "time_window_hours": TIME_WINDOW_HOURS,
        "window_radius_turns": WINDOW_RADIUS_TURNS,
        "positive_clock_drift_hours": POSITIVE_CLOCK_DRIFT_HOURS,
        "plan_mode_bonus_max": PLAN_MODE_BONUS,
        "reasoning_summary_bonus_max": REASONING_SUMMARY_BONUS,
        "reasoning_summary_policy": (
            "ranking-only; text is transient and absent from public/private serialized outputs"
        ),
        "confidence_rules": CONFIDENCE_RULES,
        "assumptions": [
            "Memory Seed heading timestamps are Europe/London local time.",
            "A decision timestamp represents the half-open minute beginning at that timestamp.",
            "Codex task_started timestamps define turn starts; the next start defines the prior turn end.",
            "Plan mode and readable reasoning summaries affect ranking but cannot establish confidence alone.",
            "Encrypted and raw plaintext reasoning are ignored.",
            "Matching Git remote or cwd containment identifies repository-related rollouts.",
            "Confidence categories are heuristic triage labels and require manual audit.",
        ],
    }
    write_outputs(args.output.resolve(), args.private_output.resolve(), rows, metadata)
    print(json.dumps({"summary": summarize(rows), "metadata": metadata}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
