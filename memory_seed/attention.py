"""Attention signal: which decisions do agents actually open, decayed over time.

Un-defers P2 of docs/5_Completed/interaction-frequency-ranking-plan.md ("real
access-frequency telemetry"); design ratified in
docs/2_Todo/attention-retrieval-signal-proposal.md. Two files, both operational
retrieval state - NOT memory content, so Invariant #2 (append-only past) does not
bind them and both are gitignored:

  .memory-seed/.retrieval-log.jsonl      one JSON line per MCP retrieval event
  .memory-seed/.retrieval-attention.json compacted decayed summary (rebuildable)

The load-bearing distinction is fetch vs impression. ``memory_search`` returning
an entry is the *ranker's* choice (an impression); the agent then calling
``memory_get_chunk`` on it is the *agent's* choice (a click). Only fetches score:
counting impressions would feed the ranker its own output and popular entries
would snowball. Impressions are still logged, source-tagged, so the weighting can
be revisited with evidence.

Everything here is fail-open: a logging failure must never break the tool call it
rides on, and unreadable state degrades to "no attention data", never an error.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_NAME = ".retrieval-log.jsonl"
SUMMARY_NAME = ".retrieval-attention.json"

# Exponential decay half-life for the attention score. 30 days means a fetch
# today counts 1.0, a fetch a month ago 0.5, a quarter ago ~0.13 - "recent
# attention", per the forgetting-curve framing in the origin doc.
HALF_LIFE_DAYS = 30.0

# Compact (fold log into summary, truncate log) past this many log lines. The
# log is operational state, not memory - truncation is deliberate and ratified.
COMPACT_THRESHOLD = 5000

# The only event source that scores in v1. Impressions ("memory_search") and any
# future sources (file-touch trigger, Trace views) are logged but weigh zero.
FETCH_TOOL = "memory_get_chunk"

GITIGNORE_ENTRIES = (
    f".memory-seed/{LOG_NAME}",
    f".memory-seed/{SUMMARY_NAME}",
)


def _log_path(memory_dir: Path) -> Path:
    return memory_dir / LOG_NAME


def _summary_path(memory_dir: Path) -> Path:
    return memory_dir / SUMMARY_NAME


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _decay(weight: float, age_days: float) -> float:
    return weight * math.pow(0.5, max(age_days, 0.0) / HALF_LIFE_DAYS)


def record_event(
    memory_dir: str | Path,
    tool: str,
    entry_id: str,
    ts: datetime | None = None,
) -> None:
    """Append one retrieval event. Fail-open by contract."""
    try:
        memory_dir = Path(memory_dir)
        if not memory_dir.is_dir() or not entry_id:
            return
        log_path = _log_path(memory_dir)
        if not log_path.exists():
            _ensure_ignored(memory_dir)
        line = json.dumps(
            {
                "schema": 1,
                "ts": (ts or _now()).isoformat(timespec="seconds"),
                "tool": tool,
                "entry_id": entry_id,
            },
            ensure_ascii=False,
        )
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        return


def _ensure_ignored(memory_dir: Path) -> None:
    """Register both state files in the workspace .gitignore on first write.

    Mirrors the local.yaml self-registration pattern (core.LOCAL_CONFIG_IGNORE_ENTRY)
    so any project that receives attention data also ignores it, without touching
    init_project. Lazy import: core never imports this module.
    """
    try:
        from .core import _ensure_gitignore_entry

        for entry in GITIGNORE_ENTRIES:
            _ensure_gitignore_entry(memory_dir.parent, entry)
    except Exception:
        return


def _read_summary(memory_dir: Path) -> dict[str, Any]:
    try:
        payload = json.loads(_summary_path(memory_dir).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _iter_log_events(memory_dir: Path) -> list[dict[str, Any]]:
    try:
        text = _log_path(memory_dir).read_text(encoding="utf-8")
    except OSError:
        return []
    events = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def load_attention(
    memory_dir: str | Path,
    now: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    """Fold summary + log into ``{entry_id: {attention_score, fetch_count, last_fetch}}``.

    ``attention_score`` is the decayed fetch weight (impressions weigh zero);
    ``fetch_count`` is the undecayed lifetime count - the plain counter surfaced
    to users; ``last_fetch`` an ISO timestamp or None. Returns {} when no data
    or on any read failure.
    """
    try:
        memory_dir = Path(memory_dir)
        moment = now or _now()
        folded: dict[str, dict[str, Any]] = {}

        summary = _read_summary(memory_dir)
        as_of = _parse_ts(summary.get("as_of"))
        for entry_id, record in (summary.get("entries") or {}).items():
            if not isinstance(record, dict):
                continue
            score = float(record.get("score") or 0.0)
            if as_of is not None:
                score = _decay(score, (moment - as_of).total_seconds() / 86400.0)
            folded[entry_id] = {
                "attention_score": score,
                "fetch_count": int(record.get("fetch_count") or 0),
                "last_fetch": record.get("last_fetch"),
            }

        for event in _iter_log_events(memory_dir):
            if event.get("tool") != FETCH_TOOL:
                continue
            entry_id = event.get("entry_id")
            ts = _parse_ts(event.get("ts"))
            if not entry_id or ts is None:
                continue
            record = folded.setdefault(
                entry_id,
                {"attention_score": 0.0, "fetch_count": 0, "last_fetch": None},
            )
            record["attention_score"] += _decay(
                1.0, (moment - ts).total_seconds() / 86400.0
            )
            record["fetch_count"] += 1
            previous = _parse_ts(record.get("last_fetch"))
            if previous is None or ts > previous:
                record["last_fetch"] = ts.isoformat(timespec="seconds")
        return folded
    except Exception:
        return {}


def attention_scores(memory_dir: str | Path, now: datetime | None = None) -> dict[str, float]:
    """Just the decayed scores, for ranking callers."""
    return {
        entry_id: record["attention_score"]
        for entry_id, record in load_attention(memory_dir, now).items()
        if record["attention_score"] > 0.0
    }


def compact_if_needed(memory_dir: str | Path, now: datetime | None = None) -> bool:
    """Fold the log into the summary and truncate it once it exceeds COMPACT_THRESHOLD.

    The summary is a freely-rewritable derived projection; the truncation is the
    deliberate non-append-only step ratified in the proposal (the log is a
    retrieval mechanism, not memory). Returns True if a compaction ran.
    """
    try:
        memory_dir = Path(memory_dir)
        log_path = _log_path(memory_dir)
        if not log_path.exists():
            return False
        line_count = sum(1 for _ in open(log_path, encoding="utf-8"))
        if line_count <= COMPACT_THRESHOLD:
            return False
        moment = now or _now()
        folded = load_attention(memory_dir, moment)
        summary = {
            "schema": 1,
            "as_of": moment.isoformat(timespec="seconds"),
            "entries": {
                entry_id: {
                    "score": record["attention_score"],
                    "fetch_count": record["fetch_count"],
                    "last_fetch": record["last_fetch"],
                }
                for entry_id, record in folded.items()
            },
        }
        _summary_path(memory_dir).write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        log_path.write_text("", encoding="utf-8")
        return True
    except Exception:
        return False
