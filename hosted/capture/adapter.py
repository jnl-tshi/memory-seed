from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
from typing import Iterable

from .codex_rollout import parse_complete_line
from .models import ParserState, SourceCoordinate, SourceCursor
from .store import CaptureStore


MAX_LINE_BYTES = 1024 * 1024


def _rollout_id(path: Path) -> str:
    return path.stem.rsplit("-", 5)[-1] if "-" not in path.stem else path.stem[-36:]


def _identity(path: Path) -> str:
    stat = path.stat()
    device = getattr(stat, "st_dev", 0)
    inode = getattr(stat, "st_ino", 0)
    if device or inode:
        return f"{device}:{inode}"
    return f"ctime:{stat.st_ctime_ns}"


def _same_file_identity(recorded: str, current: str) -> bool:
    if recorded == current:
        return True
    current_parts = current.split(":")
    recorded_parts = recorded.split(":")
    return (
        len(current_parts) == 2
        and len(recorded_parts) == 3
        and recorded_parts[:2] == current_parts
    )


def _head(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.sha256(stream.read(4096)).hexdigest()


class CaptureAdapter:
    def __init__(self, store: CaptureStore):
        self.store = store

    def poll(self, paths: Iterable[Path | str]) -> dict[str, int | bool]:
        if self.store.paused:
            return self.store.status()
        for value in sorted((Path(path).resolve() for path in paths), key=str):
            if value.is_file():
                self._poll_one(value)
        return self.store.status()

    def _initial_cursor(self, path: Path) -> SourceCursor:
        key = str(path)
        return SourceCursor(key, key, 0, _identity(path), _head(path), 0, 0, ParserState())

    def _poll_one(self, path: Path) -> None:
        key = str(path)
        cursor = self.store.cursor_for(key) or self._initial_cursor(path)
        identity = _identity(path)
        head = _head(path)
        size = path.stat().st_size
        rotated = size < cursor.byte_offset or not _same_file_identity(
            cursor.file_identity,
            identity,
        )
        if not rotated and cursor.byte_offset > 0 and cursor.head_sha256 != head:
            with path.open("rb") as stream:
                prefix = stream.read(min(cursor.byte_offset, 4096))
            rotated = hashlib.sha256(prefix).hexdigest() != cursor.head_sha256
        if rotated:
            cursor = SourceCursor(key, key, cursor.generation + 1, identity, head, 0, 0, ParserState())

        with path.open("rb") as stream:
            stream.seek(cursor.byte_offset)
            data = stream.read()
        completed = data.rsplit(b"\n", 1)
        if len(completed) == 1:
            return
        complete_bytes = completed[0] + b"\n"
        lines = complete_bytes.splitlines(keepends=True)
        offset = cursor.byte_offset
        ordinal = cursor.source_ordinal
        state = cursor.parser_state
        events = []
        diagnostics = []
        discard = cursor.discard_until_newline
        for raw_with_newline in lines:
            line = raw_with_newline[:-1]
            line_offset = offset
            offset += len(raw_with_newline)
            if discard:
                discard = False
                ordinal += 1
                continue
            coordinate = SourceCoordinate(_rollout_id(path), key, ordinal, line_offset, cursor.generation)
            if len(line) > MAX_LINE_BYTES:
                from .models import Diagnostic
                diagnostics.append(Diagnostic("line_too_large", "complete line exceeded 1 MiB", hashlib.sha256(line).hexdigest(), {
                    "path": key, "source_ordinal": ordinal, "byte_offset": line_offset, "generation": cursor.generation
                }))
            else:
                state, event, diagnostic = parse_complete_line(state, line, coordinate)
                if event is not None:
                    events.append(event)
                if diagnostic is not None:
                    diagnostics.append(diagnostic)
            ordinal += 1
        next_cursor = replace(
            cursor, file_identity=identity, head_sha256=head, byte_offset=offset,
            source_ordinal=ordinal, parser_state=state, discard_until_newline=discard,
        )
        self.store.ingest_batch(next_cursor, events, diagnostics)

    def _boundary(self, paths: Iterable[Path | str], reason: str) -> None:
        for value in sorted((Path(path).resolve() for path in paths), key=str):
            if not value.is_file():
                continue
            existing = self.store.cursor_for(str(value)) or self._initial_cursor(value)
            size = value.stat().st_size
            with value.open("rb") as stream:
                stream.seek(max(size - 1, 0))
                final = stream.read(1)
            state, ordinal = self._state_at_eof(value, existing.generation)
            cursor = replace(
                existing, file_identity=_identity(value), head_sha256=_head(value), byte_offset=size,
                source_ordinal=ordinal, parser_state=state,
                discard_until_newline=bool(size and final != b"\n"),
            )
            self.store.set_boundary(cursor, reason, existing.byte_offset)

    def _state_at_eof(self, path: Path, generation: int) -> tuple[ParserState, int]:
        """Rebuild parser context without emitting/backfilling any event."""
        state = ParserState()
        ordinal = 0
        offset = 0
        with path.open("rb") as stream:
            for raw in stream:
                if not raw.endswith(b"\n"):
                    break
                coordinate = SourceCoordinate(_rollout_id(path), str(path), ordinal, offset, generation)
                state, _, _ = parse_complete_line(state, raw[:-1], coordinate)
                offset += len(raw)
                ordinal += 1
        return state, ordinal

    def pause(self, paths: Iterable[Path | str]) -> None:
        self._boundary(paths, "paused_interval")
        self.store.pause_control()

    def resume(self, paths: Iterable[Path | str], *, backfill: bool = False) -> None:
        if backfill:
            raise NotImplementedError("explicit paused-period backfill is not implemented in P0.2")
        self._boundary(paths, "paused_interval")
        self.store.resume_control()
