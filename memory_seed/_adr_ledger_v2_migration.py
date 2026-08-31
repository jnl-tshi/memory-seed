"""The exhausted, corpus-locked ADR ledger v1 -> v2 migration.

This module is intentionally private: it is not registered with the CLI or MCP.  The constant below
binds it to the one ratified historical corpus.  It is retained only so the archival proof and its
deterministic conversion remain inspectable and testable; it must never be generalized into a writer.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from .adr import AdrEvent, AdrRecord, check_adrs, parse_adr, render_adr, validate_adr
from .core import read_text_file, resolve_runtime, write_text_file


ARCHIVE_RELATIVE = Path("archive") / "2.21" / "adr-ledger-v1-preimage"
MANIFEST_NAME = "manifest.json"
# SHA-256 of sorted ``path<TAB>byte-count<TAB>sha256`` v1 corpus rows, ending in LF.
EXPECTED_V1_CORPUS_SHA256 = "240e1b65ee3629e1580815aa18d703089363bf13d074cd828db97bb7aeb9438f"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _preimage_rows(root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted((root / ".memory-seed" / "decisions").glob("adr_*.md")):
        raw = path.read_bytes()
        rows.append({
            "path": path.relative_to(root).as_posix(),
            "bytes": len(raw),
            "sha256": _sha256(raw),
        })
    return rows


def _corpus_digest(rows: list[dict[str, object]]) -> str:
    text = "".join(f"{row['path']}\t{row['bytes']}\t{row['sha256']}\n" for row in rows)
    return _sha256(text.encode("utf-8"))


def _not_recorded() -> str:
    return "Impact was not recorded in the schema-v1 event."


def _reason_not_recorded() -> str:
    return "Reason was not recorded in the schema-v1 event."


def _lifecycle_impact(event: AdrEvent) -> str:
    ref = event.decision_ref or (f"founding:{event.founding_source}" if event.founding_source else "the selected revision")
    if event.kind == "revision-accepted":
        return f"{ref} becomes the authoritative decision; later contrary evidence requires a successor revision."
    if event.kind == "revision-rejected":
        return f"{ref} is not adopted and the current authoritative decision remains unchanged."
    if event.kind == "reviewed-no-change":
        return "The review retained the governing decision; the original impact was not otherwise recorded."
    if event.kind == "adr-superseded":
        return f"Authority for this concern moves to {event.replacement_adr or 'the replacement ADR'} while this ledger remains historical evidence."
    if event.kind == "context-added":
        return "This adds supporting context only; it does not change ADR membership, status, or authority."
    return _not_recorded()


def _lifecycle_decision(event: AdrEvent) -> str:
    ref = event.decision_ref or (f"founding:{event.founding_source}" if event.founding_source else "the selected revision")
    if event.kind == "revision-accepted":
        return f"Accept {ref}."
    if event.kind == "revision-rejected":
        return f"Reject {ref}."
    if event.kind == "reviewed-no-change":
        return f"Retain {ref} as the governing decision."
    if event.kind == "adr-superseded":
        return f"Supersede this ADR with {event.replacement_adr or 'the replacement ADR'}."
    if event.kind == "context-added":
        return "Record the supplied decisions as context for this ADR."
    return "Record this ADR lifecycle event."


def convert_record(record: AdrRecord) -> AdrRecord:
    """Pure v1 conversion: preserve authored fields; derive only explicit lifecycle effects."""
    if record.schema_version != 1:
        raise ValueError("ADR ledger v2 migration accepts schema-v1 records only")
    converted: list[AdrEvent] = []
    for event in record.events:
        if event.kind == "revision-proposed":
            impact = event.evolution.strip() or _not_recorded()
            provenance = "preserved" if event.evolution.strip() else "not-recorded"
            converted.append(replace(
                event, why="", evolution="", reason=event.why, impact=impact,
                impact_provenance=provenance, impact_evidence=(), body_issues=None,
            ))
            continue
        # The old envelope explicitly establishes each lifecycle transition.  These two fields are
        # mechanical renderings of that recorded state, not reconstructed historical claims.
        converted.append(replace(
            event, decision=_lifecycle_decision(event), why="", evolution="",
            reason=event.reason.strip() or _reason_not_recorded(),
            impact=_lifecycle_impact(event), impact_provenance="preserved",
            impact_evidence=(), body_issues=None,
        ))
    return AdrRecord(
        2, record.adr_id, record.title, record.topics, record.created_at, record.user_initials,
        record.agent_type, record.source, converted, record.path, 2,
    )


def migrate_once(cwd: str | Path = ".") -> dict[str, object]:
    """Archive and convert the exact ratified corpus, or fail before source writes."""
    runtime = resolve_runtime(cwd)
    root = runtime.workspace_root
    archive = runtime.memory_dir / ARCHIVE_RELATIVE
    manifest_path = archive / MANIFEST_NAME
    if archive.exists() or manifest_path.exists():
        raise RuntimeError("ADR ledger v2 migration has already run or its archive is present")

    rows = _preimage_rows(root)
    corpus_digest = _corpus_digest(rows)
    if corpus_digest != EXPECTED_V1_CORPUS_SHA256:
        raise RuntimeError("ADR ledger v2 migration refuses this unfamiliar preimage corpus")

    # Convert and validate all exact output bytes before creating the archive or touching source.
    outputs: list[tuple[Path, bytes]] = []
    for row in rows:
        source = root / str(row["path"])
        converted = convert_record(parse_adr(source))
        rendered = render_adr(converted)
        reparsed = parse_adr_text_v2(rendered, source)
        issues = validate_adr(reparsed, root)
        if issues:
            raise RuntimeError(f"ADR ledger v2 migration validation failed for {row['path']}: {'; '.join(issues)}")
        outputs.append((source, rendered.encode("utf-8")))

    manifest = {
        "kind": "memory-seed-adr-ledger-v2-preimage",
        "version": 1,
        "corpus_sha256": corpus_digest,
        "files": rows,
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    # Archive bytes and manifest are fully prepared before writes. The source corpus is only written
    # after every preimage has been copied and its archive digest rechecked.
    archive.mkdir(parents=True, exist_ok=False)
    for row in rows:
        source = root / str(row["path"])
        target = archive / Path(str(row["path"])).name
        target.write_bytes(source.read_bytes())
        raw = target.read_bytes()
        if len(raw) != row["bytes"] or _sha256(raw) != row["sha256"]:
            raise RuntimeError(f"ADR ledger v2 archive verification failed for {row['path']}")
    (archive / MANIFEST_NAME).write_bytes(manifest_bytes)
    if json.loads((archive / MANIFEST_NAME).read_text(encoding="utf-8")) != manifest:
        raise RuntimeError("ADR ledger v2 archive manifest verification failed")
    for source, rendered in outputs:
        write_text_file(source, rendered.decode("utf-8"))
    ok, issues = check_adrs(root)
    if not ok:
        raise RuntimeError("ADR ledger v2 post-write validation failed: " + "; ".join(issues))
    return {"ok": True, "archive": str(archive), "corpus_sha256": corpus_digest, "files": len(rows)}


def parse_adr_text_v2(rendered: str, path: Path) -> AdrRecord:
    # Local import avoids expanding the migration module's public surface.
    from .adr import parse_adr_text
    return parse_adr_text(rendered, path=path)
