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

# Task Packet usage telemetry (task-packet-handoff-integration-plan.md, T1).
# These kinds share the log so one gitignored, rebuildable file carries all
# retrieval-side operational state, but they never score: load_attention folds
# only FETCH_TOOL. Compaction keeps their counts in the summary.
TASK_PACKET_EVENT_KINDS = frozenset(
    {
        "task_packet_compile",
        "task_packet_preview",
        "task_packet_render",
        "task_packet_activate",
        "task_packet_governance_load",
    }
)
# Where in the workflow a packet crossed a handoff (plan handoff points 3-6).
HANDOFF_LABELS = frozenset({"implementation", "sdd", "review", "spawned-session", "other"})

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


def record_task_packet_event(
    memory_dir: str | Path,
    kind: str,
    packet: Any,
    *,
    handoff: str | None = None,
    ts: datetime | None = None,
) -> None:
    """Append one Task Packet usage event. Fail-open by contract.

    ``entry_id`` carries the packet fingerprint so existing log readers keep a
    uniform shape; the packet's version, profile, write intent and the caller's
    handoff label ride alongside for the ESR coverage report.
    """
    try:
        memory_dir = Path(memory_dir)
        if kind not in TASK_PACKET_EVENT_KINDS or not memory_dir.is_dir() or not isinstance(packet, dict):
            return
        fingerprint = packet.get("fingerprint")
        if not isinstance(fingerprint, str) or not fingerprint:
            return
        dispatch = packet.get("dispatch") if isinstance(packet.get("dispatch"), dict) else {}
        execution = dispatch.get("execution") if isinstance(dispatch.get("execution"), dict) else {}
        profile = packet.get("retrieval_profile") if isinstance(packet.get("retrieval_profile"), dict) else {}
        log_path = _log_path(memory_dir)
        # Unlike retrieval events, packet events must never change the working
        # tree: registering the log in .gitignore would alter the very commit
        # cadence a packet measures and break deterministic compilation. So
        # they are recorded only once the log is already ignored.
        if not _log_is_ignored(memory_dir):
            return
        line = json.dumps(
            {
                "schema": 1,
                "ts": (ts or _now()).isoformat(timespec="seconds"),
                "tool": kind,
                "entry_id": fingerprint,
                "packet_version": packet.get("packet_version"),
                "profile": (
                    f"{profile.get('id')}:v{profile.get('profile_version')}" if profile.get("id") else None
                ),
                "write_intent": execution.get("write_intent"),
                "handoff": handoff if handoff in HANDOFF_LABELS else "unspecified",
            },
            ensure_ascii=False,
        )
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        return


def _log_is_ignored(memory_dir: Path) -> bool:
    import subprocess

    relative = f"{memory_dir.name}/{LOG_NAME}"
    try:
        probe = subprocess.run(
            ["git", "-C", str(memory_dir.parent), "check-ignore", "-q", "--no-index", relative],
            capture_output=True, timeout=10,
        )
        if probe.returncode in (0, 1):
            return probe.returncode == 0
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        lines = (memory_dir.parent / ".gitignore").read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return False
    return any(line.strip().lstrip("/") == relative for line in lines)


def _usage_counts(events: list[dict[str, Any]]) -> dict[str, Any]:
    totals: dict[str, int] = {}
    by_handoff: dict[str, int] = {}
    by_day: dict[str, dict[str, dict[str, int]]] = {}
    for event in events:
        kind = event.get("tool")
        if kind not in TASK_PACKET_EVENT_KINDS:
            continue
        label = str(event.get("handoff") or "unspecified")
        totals[kind] = totals.get(kind, 0) + 1
        by_handoff[label] = by_handoff.get(label, 0) + 1
        moment = _parse_ts(event.get("ts"))
        if moment is not None:
            day = by_day.setdefault(moment.astimezone().date().isoformat(), {"totals": {}, "by_handoff": {}})
            day["totals"][kind] = day["totals"].get(kind, 0) + 1
            day["by_handoff"][label] = day["by_handoff"].get(label, 0) + 1
    return {"totals": totals, "by_handoff": by_handoff, "by_day": by_day}


def _add_counts(target: dict[str, int], source: Any) -> None:
    for key, value in (source or {}).items():
        if isinstance(value, int):
            target[key] = target.get(key, 0) + value


def _merge_counts(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {"totals": {}, "by_handoff": {}, "by_day": {}}
    for source in (left, right):
        _add_counts(merged["totals"], source.get("totals"))
        _add_counts(merged["by_handoff"], source.get("by_handoff"))
        for day, counts in (source.get("by_day") or {}).items():
            target = merged["by_day"].setdefault(day, {"totals": {}, "by_handoff": {}})
            _add_counts(target["totals"], (counts or {}).get("totals"))
            _add_counts(target["by_handoff"], (counts or {}).get("by_handoff"))
    return merged


def load_task_packet_usage(
    memory_dir: str | Path, since: datetime | None = None
) -> dict[str, Any]:
    """Lifetime Task Packet usage counts plus the log's events since ``since``.

    Counts survive compaction (folded into the summary); individual events are
    available only while still in the log. Returns empty structures on failure.
    """
    try:
        memory_dir = Path(memory_dir)
        events = [event for event in _iter_log_events(memory_dir) if event.get("tool") in TASK_PACKET_EVENT_KINDS]
        counts = _merge_counts(_read_summary(memory_dir).get("task_packet_usage") or {}, _usage_counts(events))
        recent = []
        for event in events:
            moment = _parse_ts(event.get("ts"))
            if moment is not None and (since is None or moment >= since):
                recent.append(event)
        return {**counts, "events": recent}
    except Exception:
        return {"totals": {}, "by_handoff": {}, "by_day": {}, "events": []}


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
        # Task Packet usage is telemetry, not attention: keep its counts across
        # truncation so the ESR coverage report never loses history.
        usage = _merge_counts(
            _read_summary(memory_dir).get("task_packet_usage") or {},
            _usage_counts(_iter_log_events(memory_dir)),
        )
        summary = {
            "schema": 1,
            "as_of": moment.isoformat(timespec="seconds"),
            "task_packet_usage": usage,
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
