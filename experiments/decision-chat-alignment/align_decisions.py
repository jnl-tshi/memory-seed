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
LOCAL_TIMEZONE = ZoneInfo("Europe/London")
TOKEN_RE = re.compile(r"[A-Za-z0-9_./\\:-]{2,}")
IDENTIFIER_RE = re.compile(r"(?:[A-Za-z0-9_-]+[./\\:][A-Za-z0-9_./\\:-]+|[A-Za-z]+_[A-Za-z0-9_]+)")
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
    session_id: str
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
    items: list[NormalizedItem] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(f"{item.role}: {item.text}" for item in self.items if item.text.strip())


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
    session_id = str(payload.get("session_id") or payload.get("id") or "")
    if not stamp or not session_id:
        return None
    git = payload.get("git") if isinstance(payload.get("git"), dict) else {}
    source = payload.get("source")
    source_text = json.dumps(source, sort_keys=True) if isinstance(source, dict) else str(source or "")
    return SessionMeta(
        session_id=session_id,
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
        parent_thread_id=str(payload.get("parent_thread_id")) if payload.get("parent_thread_id") else None,
        agent_nickname=str(payload.get("agent_nickname")) if payload.get("agent_nickname") else None,
    )


def session_belongs_to_repo(meta: SessionMeta, repo_roots: Sequence[Path], remote: str | None) -> bool:
    cwd = normalize_path(meta.cwd)
    normalized_roots = [normalize_path(root) for root in repo_roots]
    cwd_match = any(cwd == root or cwd.startswith(root + os.sep) for root in normalized_roots)
    remote_match = bool(remote and meta.repository_url and normalize_remote(meta.repository_url) == remote)
    return cwd_match or remote_match


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

    def block() -> TurnBlock:
        nonlocal turn_number
        if turn_number == 0:
            turn_number = 1
        return blocks.setdefault(turn_number, TurnBlock(meta, turn_number, current_turn_id))

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
            if row.get("type") == "event_msg" and payload.get("type") == "task_started":
                turn_number += 1
                current_turn_id = str(payload.get("turn_id")) if payload.get("turn_id") else None
                continue
            if row.get("type") != "response_item":
                continue
            payload_type = payload.get("type")
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
    return [blocks[key] for key in sorted(blocks) if blocks[key].text.strip()]


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
    hours = abs((decision_time - block.session.timestamp_utc).total_seconds()) / 3600.0
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


def align(
    decisions: Sequence[DecisionRecord],
    sessions: Sequence[SessionMeta],
    blocks_by_session: dict[str, list[TurnBlock]],
) -> list[dict[str, Any]]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    all_blocks = [block for session in sessions for block in blocks_by_session.get(session.session_id, [])]
    texts = [decision.match_text for decision in decisions] + [block.text for block in all_blocks]
    if not all_blocks:
        return []
    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        analyzer="word",
        ngram_range=(1, 2),
        sublinear_tf=True,
        max_features=150_000,
        token_pattern=r"(?u)\b[A-Za-z0-9_./\\:-]{2,}\b",
    )
    matrix = vectorizer.fit_transform(texts)
    similarities = cosine_similarity(matrix[: len(decisions)], matrix[len(decisions) :])
    session_blocks: dict[str, list[tuple[int, TurnBlock]]] = defaultdict(list)
    for index, block in enumerate(all_blocks):
        session_blocks[block.session.session_id].append((index, block))

    output: list[dict[str, Any]] = []
    for decision_index, decision in enumerate(decisions):
        decision_time = parse_iso_timestamp(decision.decision_timestamp)
        eligible_sessions = [
            session for session in sessions
            if decision_time
            and actor_compatible(decision, session)
            and -POSITIVE_CLOCK_DRIFT_HOURS
            <= (decision_time - session.timestamp_utc).total_seconds() / 3600.0
            <= TIME_WINDOW_HOURS
        ]
        scored_sessions: list[dict[str, Any]] = []
        for session in eligible_sessions:
            # TF-IDF is the cheap high-recall shortlist. Phrase matching is much
            # more expensive on long chat turns, so apply it only to the three
            # strongest lexical candidates in each session.
            lexical_candidates: list[tuple[float, int, TurnBlock]] = []
            for global_index, block in session_blocks.get(session.session_id, []):
                # A turn that already cites the minted Memory Seed identity is a
                # retrieval/review copy, not the source from which the record arose.
                if decision.entry_id.casefold() in block.text.casefold():
                    continue
                cosine = float(similarities[decision_index, global_index])
                lexical_candidates.append((cosine, global_index, block))
            candidates = [
                (signal_score(decision, block, cosine), global_index, block)
                for cosine, global_index, block in sorted(
                    lexical_candidates, key=lambda item: item[0], reverse=True
                )[:3]
            ]
            if not candidates:
                continue
            best_signal, _global_index, best_block = max(candidates, key=lambda item: item[0]["score"])
            blocks = blocks_by_session[session.session_id]
            local_index = next(index for index, block in enumerate(blocks) if block is best_block)
            window = bounded_window(blocks, local_index)
            scored_sessions.append(
                {
                    "session": session,
                    "best_block": best_block,
                    "signals": best_signal,
                    "window": window,
                }
            )
        scored_sessions.sort(key=lambda item: item["signals"]["score"], reverse=True)
        best = scored_sessions[0] if scored_sessions else None
        second = scored_sessions[1] if len(scored_sessions) > 1 else None
        best_score = best["signals"]["score"] if best else 0.0
        second_score = second["signals"]["score"] if second else 0.0
        margin = best_score - second_score
        confidence = confidence_for(best["signals"] if best else None, margin)
        ambiguous = bool(
            second
            and second_score >= 0.22
            and (second_score >= 0.85 * best_score or margin < 0.06)
        )
        has_actor_session = any(actor_compatible(decision, session) for session in eligible_sessions)

        def candidate_payload(candidate: dict[str, Any] | None, private: bool = False) -> dict[str, Any] | None:
            if not candidate:
                return None
            session = candidate["session"]
            block = candidate["best_block"]
            payload = {
                "session_id": session.session_id,
                "conversation_timestamp": session.timestamp,
                "source_path": session.source_path if private else public_session_path(session.source_path),
                "cwd": session.cwd if private else "repository checkout/worktree",
                "originator": session.originator,
                "source": session.source,
                "git_branch": session.git_branch,
                "git_commit": session.git_commit,
                "winning_turn": block.turn_number,
                "winning_turn_id": block.turn_id,
                "signals": candidate["signals"],
                "window": private_window(candidate["window"]) if private else public_window(candidate["window"]),
            }
            return payload

        public = {
            "decision": asdict(decision),
            "candidate_session_count": len(eligible_sessions),
            "best_candidate": candidate_payload(best),
            "second_best_candidate": candidate_payload(second),
            "confidence": confidence,
            "score_margin": margin,
            "appears_unique": not ambiguous,
            "ambiguity": "competitive second session" if ambiguous else None,
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
        f"score {signal['score']:.3f}",
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
    return "; ".join(parts)


def render_review(rows: Sequence[dict[str, Any]], *, include_raw: bool) -> str:
    lines = [
        "# Decision-to-chat alignment review",
        "",
        f"Sample: {len(rows)} decisions; seed `{SEED}`; candidate sessions start within "
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
                "conversation_timestamp", "source_path", "winning_turn", "score", "score_margin",
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
                    "winning_turn": best.get("winning_turn"),
                    "score": (best.get("signals") or {}).get("score"),
                    "score_margin": row["score_margin"],
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
    args = parser.parse_args()

    repo_root = args.repo.resolve()
    remote = repository_remote(repo_root)
    repo_roots = repository_worktree_roots(repo_root)
    population = load_decisions(repo_root)
    sample = deterministic_sample(population, args.sample_size, args.seed)
    sample_times = [parse_iso_timestamp(decision.decision_timestamp) for decision in sample]
    sample_times = [value for value in sample_times if value is not None]

    all_paths = list(iter_rollout_paths(args.codex_home.resolve()))
    metas = [meta for path in all_paths if (meta := read_session_meta(path)) is not None]
    repo_metas = [
        meta for meta in metas
        if session_belongs_to_repo(meta, repo_roots, remote) and not is_derived_review_session(meta)
    ]
    selected_metas = [
        meta for meta in repo_metas
        if any(
            actor_compatible(decision, meta)
            and -POSITIVE_CLOCK_DRIFT_HOURS
            <= (stamp - meta.timestamp_utc).total_seconds() / 3600.0
            <= TIME_WINDOW_HOURS
            for decision, stamp in zip(sample, sample_times)
        )
    ]
    blocks_by_session: dict[str, list[TurnBlock]] = {}
    for index, meta in enumerate(selected_metas, 1):
        blocks_by_session[meta.session_id] = parse_rollout(Path(meta.source_path), meta)
        if index % 100 == 0:
            print(f"parsed {index}/{len(selected_metas)} candidate rollouts", flush=True)

    rows = align(sample, selected_metas, blocks_by_session)
    metadata = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_checkout": str(repo_root),
        "repository_worktree_roots": [str(root) for root in repo_roots],
        "repository_remote": remote,
        "codex_home": str(args.codex_home.resolve()),
        "population_size": len(population),
        "sample_size": len(sample),
        "sample_seed": args.seed,
        "sample_method": "uniform without replacement from decision_id-sorted canonical Decision chunks",
        "sample_ids": [decision.decision_id for decision in sample],
        "sample_ids_sha256": sha256_text("\n".join(decision.decision_id for decision in sample)),
        "rollout_files_discovered": len(all_paths),
        "rollout_metadata_parsed": len(metas),
        "repository_rollouts": len(repo_metas),
        "temporal_candidate_rollouts": len(selected_metas),
        "normalized_turn_blocks": sum(len(blocks) for blocks in blocks_by_session.values()),
        "time_window_hours": TIME_WINDOW_HOURS,
        "window_radius_turns": WINDOW_RADIUS_TURNS,
        "positive_clock_drift_hours": POSITIVE_CLOCK_DRIFT_HOURS,
        "confidence_rules": CONFIDENCE_RULES,
        "assumptions": [
            "Memory Seed heading timestamps are Europe/London local time.",
            "Codex session_meta timestamp is a sufficient directional temporal prefilter for bounded rollouts.",
            "Matching Git remote or cwd containment identifies repository-related rollouts.",
            "Confidence categories are heuristic triage labels and require manual audit.",
        ],
    }
    write_outputs(args.output.resolve(), args.private_output.resolve(), rows, metadata)
    print(json.dumps({"summary": summarize(rows), "metadata": metadata}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
