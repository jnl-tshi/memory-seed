"""Attention signal: which decisions do agents actually open, decayed over time.

Un-defers P2 of docs/5_Completed/interaction-frequency-ranking-plan.md ("real
access-frequency telemetry"); design ratified in
docs/2_Todo/attention-retrieval-signal-proposal.md. Two files, both operational
retrieval state - NOT memory content, so Invariant #2 (append-only past) does not
bind them and both are gitignored:

  <git-common-dir>/memory-seed/telemetry/v2/events/*.jsonl
      append-only, per-writer lifetime retrieval and workflow events
  .memory-seed/.retrieval-log.jsonl
      preserved legacy worktree-local source, imported additively
  .memory-seed/.retrieval-attention.json
      legacy compacted decayed summary (rebuildable)

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
import hashlib
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

LOG_NAME = ".retrieval-log.jsonl"
SUMMARY_NAME = ".retrieval-attention.json"

# Exponential decay half-life for the attention score. 30 days means a fetch
# today counts 1.0, a fetch a month ago 0.5, a quarter ago ~0.13 - "recent
# attention", per the forgetting-curve framing in the origin doc.
HALF_LIFE_DAYS = 30.0

# Legacy non-Git fallback compaction threshold. Git repositories migrate to
# the lifetime common store and never truncate either source or destination.
COMPACT_THRESHOLD = 5000

# The only event source that scores in v1. Impressions ("memory_search") and any
# future sources (file-touch trigger, Trace views) are logged but weigh zero.
FETCH_TOOL = "memory_get_chunk"

# Task Packet usage telemetry (task-packet-handoff-integration-plan.md, T1).
# These kinds share the durable operational store, but they never score:
# load_attention folds only FETCH_TOOL.
TASK_PACKET_EVENT_KINDS = frozenset(
    {
        "task_packet_compile",
        "task_packet_preview",
        "task_packet_render",
        "task_packet_activate",
        "task_packet_governance_load",
    }
)
DISCOVERY_EVENT_KINDS = frozenset({"discovery_evidence", "discovery_assess"})
TELEMETRY_SCHEMA = 2
TELEMETRY_DIR = Path("memory-seed") / "telemetry" / "v2"
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


def _git_path(memory_dir: Path, argument: str) -> Path | None:
    try:
        probe = subprocess.run(
            ["git", "-C", str(memory_dir.parent), "rev-parse", argument],
            check=False, capture_output=True, text=True, timeout=10,
        )
        if probe.returncode != 0 or not probe.stdout.strip():
            return None
        path = Path(probe.stdout.strip())
        return path.resolve() if path.is_absolute() else (memory_dir.parent / path).resolve()
    except (OSError, subprocess.SubprocessError):
        return None


def telemetry_root(memory_dir: str | Path) -> Path | None:
    """Repository-scoped operational store shared by every linked worktree."""
    common = _git_path(Path(memory_dir), "--git-common-dir")
    return common / TELEMETRY_DIR if common is not None else None


def _writer_id(memory_dir: Path) -> str:
    git_dir = _git_path(memory_dir, "--git-dir")
    identity = str(git_dir or memory_dir.resolve()).replace("\\", "/").casefold()
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]


def _common_event_paths(memory_dir: Path) -> tuple[Path, Path] | None:
    root = telemetry_root(memory_dir)
    if root is None:
        return None
    return root / "events" / f"{_writer_id(memory_dir)}.jsonl", root / "migrations.json"


def _event_id() -> str:
    return "mste_" + uuid.uuid4().hex


def _append_common_event(memory_dir: Path, event: Mapping[str, Any]) -> bool:
    paths = _common_event_paths(memory_dir)
    if paths is None:
        return False
    event_path, _ = paths
    event_path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(event)
    payload.setdefault("schema", TELEMETRY_SCHEMA)
    payload.setdefault("event_id", _event_id())
    payload.setdefault("writer_id", _writer_id(memory_dir))
    with event_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return True


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
        migrate_legacy_telemetry(memory_dir)
        event = {
            "schema": TELEMETRY_SCHEMA,
            "event_id": _event_id(),
            "ts": (ts or _now()).isoformat(timespec="seconds"),
            "tool": tool,
            "entry_id": entry_id,
        }
        if _append_common_event(memory_dir, event):
            return
        log_path = _log_path(memory_dir)
        if not log_path.exists():
            _ensure_ignored(memory_dir)
        line = json.dumps(event, ensure_ascii=False)
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
        discovery = dispatch.get("design_discovery") if isinstance(dispatch.get("design_discovery"), dict) else {}
        discovery_receipt = discovery.get("receipt") if isinstance(discovery.get("receipt"), dict) else {}
        migrate_legacy_telemetry(memory_dir)
        event = {
                "schema": TELEMETRY_SCHEMA,
                "event_id": _event_id(),
                "ts": (ts or _now()).isoformat(timespec="seconds"),
                "tool": kind,
                "entry_id": fingerprint,
                "packet_version": packet.get("packet_version"),
                "profile": (
                    f"{profile.get('id')}:v{profile.get('profile_version')}" if profile.get("id") else None
                ),
                "write_intent": execution.get("write_intent"),
                "handoff": handoff if handoff in HANDOFF_LABELS else "unspecified",
                "discovery_required": discovery.get("required"),
                "discovery_pack_fingerprint": discovery_receipt.get("pack_fingerprint"),
                "discovery_bypass": bool(discovery) and discovery.get("required") is False,
            }
        if _append_common_event(memory_dir, event):
            return
        # Non-Git fallback retains the legacy ignored-file behavior.
        if not _log_is_ignored(memory_dir):
            return
        line = json.dumps(event, ensure_ascii=False)
        log_path = _log_path(memory_dir)
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        return


def record_discovery_event(
    memory_dir: str | Path,
    kind: str,
    result: Mapping[str, Any],
    *,
    ts: datetime | None = None,
) -> None:
    """Record privacy-minimal Design Discovery workflow telemetry."""
    try:
        memory_dir = Path(memory_dir)
        if kind not in DISCOVERY_EVENT_KINDS or not memory_dir.is_dir():
            return
        receipt = result.get("discovery_receipt") if isinstance(result.get("discovery_receipt"), Mapping) else {}
        profile = result.get("profile") if isinstance(result.get("profile"), Mapping) else receipt.get("profile", {})
        event = {
            "schema": TELEMETRY_SCHEMA,
            "event_id": _event_id(),
            "ts": (ts or _now()).isoformat(timespec="seconds"),
            "tool": kind,
            "entry_id": str(result.get("pack_fingerprint") or receipt.get("pack_fingerprint") or ""),
            "profile": f"{profile.get('id')}:v{profile.get('profile_version')}" if profile.get("id") else None,
            "required_count": int(result.get("required_review_count") or receipt.get("required_count") or 0),
            "assessed_count": int(receipt.get("assessed_count") or 0),
            "optional_assessed_count": int(receipt.get("optional_assessed_count") or 0),
            "conflict_count": len(receipt.get("conflict_refs") or []),
            "complete": bool(receipt.get("complete")) if kind == "discovery_assess" else None,
        }
        migrate_legacy_telemetry(memory_dir)
        _append_common_event(memory_dir, event)
    except Exception:
        return


def _legacy_events(memory_dir: Path) -> list[dict[str, Any]]:
    try:
        text = _log_path(memory_dir).read_text(encoding="utf-8")
    except OSError:
        return []
    events: list[dict[str, Any]] = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def migrate_legacy_telemetry(memory_dir: str | Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Copy legacy worktree-local telemetry into the Git-common lifetime log."""
    try:
        memory_dir = Path(memory_dir)
        paths = _common_event_paths(memory_dir)
        legacy = _log_path(memory_dir)
        if paths is None or not legacy.exists():
            return {"ok": True, "needed": False, "imported": 0, "baseline": False}
        raw = legacy.read_bytes()
        digest = "sha256:" + hashlib.sha256(raw).hexdigest()
        source_id = hashlib.sha256(str(legacy.resolve()).replace("\\", "/").casefold().encode("utf-8")).hexdigest()
        _, manifest_path = paths
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            manifest = {"schema": TELEMETRY_SCHEMA, "sources": {}}
        sources = manifest.setdefault("sources", {})
        if (sources.get(source_id) or {}).get("digest") == digest:
            return {"ok": True, "needed": False, "imported": 0, "baseline": False}
        events = _legacy_events(memory_dir)
        summary = _read_summary(memory_dir)
        baseline = bool(summary.get("entries") or summary.get("task_packet_usage"))
        if dry_run:
            return {"ok": True, "needed": True, "imported": len(events), "baseline": baseline}
        event_path = telemetry_root(memory_dir) / "events" / f"legacy-{source_id[:20]}.jsonl"
        event_path.parent.mkdir(parents=True, exist_ok=True)
        existing_ids = {event.get("event_id") for event in _common_events(memory_dir)}
        imported = 0
        with event_path.open("a", encoding="utf-8", newline="\n") as handle:
            for index, legacy_event in enumerate(events):
                event = dict(legacy_event)
                stable = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                event_id = "mste_legacy_" + hashlib.sha256(f"{source_id}:{index}:{stable}".encode("utf-8")).hexdigest()[:32]
                if event_id in existing_ids:
                    continue
                event.update(schema=TELEMETRY_SCHEMA, event_id=event_id, writer_id=f"legacy-{source_id[:20]}", migrated=True)
                handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
                imported += 1
            if baseline:
                baseline_id = "mste_baseline_" + hashlib.sha256((source_id + json.dumps(summary, sort_keys=True)).encode("utf-8")).hexdigest()[:32]
                if baseline_id not in existing_ids:
                    task_usage = summary.get("task_packet_usage") if isinstance(summary.get("task_packet_usage"), dict) else {}
                    entry_records = summary.get("entries") if isinstance(summary.get("entries"), dict) else {}
                    handle.write(json.dumps({
                        "schema": TELEMETRY_SCHEMA, "event_id": baseline_id,
                        "ts": summary.get("as_of") or _now().isoformat(timespec="seconds"),
                        "tool": "legacy_summary_baseline", "entry_id": source_id,
                        "writer_id": f"legacy-{source_id[:20]}", "migrated": True,
                        "aggregate_only": True,
                        "summary": {
                            "attention_entry_count": len(entry_records),
                            "attention_fetch_count": sum(
                                int(record.get("fetch_count") or 0)
                                for record in entry_records.values() if isinstance(record, dict)
                            ),
                            "task_packet_usage": task_usage,
                        },
                    }, ensure_ascii=False, sort_keys=True) + "\n")
        sources[source_id] = {"digest": digest, "event_count": len(events), "aggregate_baseline": baseline}
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = manifest_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(manifest_path)
        return {"ok": True, "needed": True, "imported": imported, "baseline": baseline}
    except Exception as exc:
        return {"ok": False, "needed": False, "imported": 0, "baseline": False, "error": exc.__class__.__name__}


def _registered_memory_dirs(cwd: str | Path) -> tuple[list[Path], list[str]]:
    try:
        probe = subprocess.run(
            ["git", "-C", str(cwd), "worktree", "list", "--porcelain"],
            check=False, capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return [], [exc.__class__.__name__]
    if probe.returncode != 0:
        return [], ["git_worktree_list_failed"]
    result: list[Path] = []
    issues: list[str] = []
    for line in probe.stdout.splitlines():
        if not line.startswith("worktree "):
            continue
        root = Path(line.removeprefix("worktree ").strip())
        memory_dir = root / ".memory-seed"
        if memory_dir.is_dir():
            result.append(memory_dir)
        elif root.exists():
            issues.append("runtime_missing:" + hashlib.sha256(str(root).casefold().encode("utf-8")).hexdigest()[:12])
    return result, issues


def migrate_repository_telemetry(cwd: str | Path = ".", *, dry_run: bool = False) -> dict[str, Any]:
    """Import every registered worktree's legacy telemetry without changing sources."""
    memory_dirs, issues = _registered_memory_dirs(cwd)
    results = [migrate_legacy_telemetry(path, dry_run=dry_run) for path in memory_dirs]
    return {
        "ok": all(result.get("ok") for result in results) and not issues,
        "dry_run": dry_run,
        "registered_worktrees": len(memory_dirs),
        "sources_needing_import": sum(bool(result.get("needed")) for result in results),
        "events_imported": sum(int(result.get("imported") or 0) for result in results),
        "aggregate_baselines": sum(bool(result.get("baseline")) for result in results),
        "issues": [*issues, *(result.get("error") for result in results if result.get("error"))],
    }


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
        all_events = _iter_log_events(memory_dir)
        events = [event for event in all_events if event.get("tool") in TASK_PACKET_EVENT_KINDS]
        baselines: dict[str, dict[str, Any]] = {}
        for event in all_events:
            if event.get("tool") != "legacy_summary_baseline":
                continue
            summary = event.get("summary") if isinstance(event.get("summary"), dict) else {}
            baselines[str(event.get("entry_id") or event.get("event_id"))] = summary.get("task_packet_usage") or {}
        baseline: dict[str, Any] = {}
        for counts in baselines.values():
            baseline = _merge_counts(baseline, counts)
        local = {} if _legacy_is_imported(memory_dir) else (_read_summary(memory_dir).get("task_packet_usage") or {})
        counts = _merge_counts(_merge_counts(local, baseline), _usage_counts(events))
        recent = []
        for event in events:
            moment = _parse_ts(event.get("ts"))
            if moment is not None and (since is None or moment >= since):
                recent.append(event)
        return {**counts, "events": recent}
    except Exception:
        return {"totals": {}, "by_handoff": {}, "by_day": {}, "events": []}


def load_workflow_telemetry(memory_dir: str | Path) -> dict[str, Any]:
    """Return rebuildable lifetime workflow counts and raw durable events."""
    try:
        memory_dir = Path(memory_dir)
        events = _iter_log_events(memory_dir)
        totals: dict[str, int] = {}
        by_day: dict[str, dict[str, int]] = {}
        for event in events:
            kind = str(event.get("tool") or "unknown")
            totals[kind] = totals.get(kind, 0) + 1
            moment = _parse_ts(event.get("ts"))
            if moment is not None:
                day = moment.astimezone().date().isoformat()
                bucket = by_day.setdefault(day, {})
                bucket[kind] = bucket.get(kind, 0) + 1
        return {"totals": totals, "by_day": by_day, "events": events}
    except Exception:
        return {"totals": {}, "by_day": {}, "events": []}


def telemetry_health(memory_dir: str | Path) -> dict[str, Any]:
    memory_dir = Path(memory_dir)
    root = telemetry_root(memory_dir)
    legacy = _log_path(memory_dir)
    events = _common_events(memory_dir)
    repository = migrate_repository_telemetry(memory_dir.parent, dry_run=True)
    return {
        "ok": root is not None,
        "schema": TELEMETRY_SCHEMA,
        "durable_store": str(root) if root is not None else None,
        "writer_id": _writer_id(memory_dir) if root is not None else None,
        "event_shards": len(list((root / "events").glob("*.jsonl"))) if root is not None else 0,
        "durable_event_count": len(events),
        "legacy_present": legacy.exists(),
        "legacy_imported": _legacy_is_imported(memory_dir),
        "registered_worktrees": repository["registered_worktrees"],
        "unimported_legacy_sources": repository["sources_needing_import"],
        "issues": (["active runtime is not inside a Git repository"] if root is None else []) + repository["issues"],
    }


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


def _common_events(memory_dir: Path) -> list[dict[str, Any]]:
    root = telemetry_root(memory_dir)
    if root is None:
        return []
    events: list[dict[str, Any]] = []
    for path in sorted((root / "events").glob("*.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)
    return events


def _legacy_is_imported(memory_dir: Path) -> bool:
    paths = _common_event_paths(memory_dir)
    legacy = _log_path(memory_dir)
    if paths is None or not legacy.exists():
        return False
    _, manifest_path = paths
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_id = hashlib.sha256(str(legacy.resolve()).replace("\\", "/").casefold().encode("utf-8")).hexdigest()
        digest = "sha256:" + hashlib.sha256(legacy.read_bytes()).hexdigest()
        return (manifest.get("sources", {}).get(source_id) or {}).get("digest") == digest
    except (OSError, json.JSONDecodeError, ValueError, AttributeError):
        return False


def _iter_log_events(memory_dir: Path) -> list[dict[str, Any]]:
    events = _common_events(memory_dir)
    if not _legacy_is_imported(memory_dir):
        events.extend(_legacy_events(memory_dir))
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for event in events:
        identity = event.get("event_id")
        if isinstance(identity, str) and identity:
            if identity in seen:
                continue
            seen.add(identity)
        result.append(event)
    return result


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
        # Git-common v2 is lifetime, append-only telemetry. Import the legacy
        # source additively and preserve the original file; no destructive
        # compaction is permitted once the durable store is available.
        if telemetry_root(memory_dir) is not None:
            migrate_legacy_telemetry(memory_dir)
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
