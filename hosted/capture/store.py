from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .models import CaptureEvent, Diagnostic, ParserState, SourceCursor


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CaptureStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA busy_timeout=5000")
        self._create_schema()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "CaptureStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS capture_control (
              singleton INTEGER PRIMARY KEY CHECK(singleton=1),
              capture_paused INTEGER NOT NULL DEFAULT 0,
              pause_epoch INTEGER NOT NULL DEFAULT 0,
              paused_at TEXT,
              resumed_at TEXT
            );
            INSERT OR IGNORE INTO capture_control(singleton) VALUES(1);
            CREATE TABLE IF NOT EXISTS source_cursors (
              source_key TEXT PRIMARY KEY,
              path TEXT NOT NULL,
              generation INTEGER NOT NULL,
              file_identity TEXT NOT NULL,
              head_sha256 TEXT NOT NULL,
              byte_offset INTEGER NOT NULL,
              source_ordinal INTEGER NOT NULL,
              parser_state_json TEXT NOT NULL,
              discard_until_newline INTEGER NOT NULL DEFAULT 0,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS event_queue (
              event_id TEXT PRIMARY KEY,
              rollout_id TEXT NOT NULL,
              source_key TEXT NOT NULL,
              source_generation INTEGER NOT NULL,
              source_ordinal INTEGER NOT NULL,
              category TEXT NOT NULL,
              occurred_at TEXT,
              payload_json TEXT NOT NULL,
              raw_sha256 TEXT NOT NULL,
              state TEXT NOT NULL DEFAULT 'queued',
              attempts INTEGER NOT NULL DEFAULT 0,
              available_at TEXT NOT NULL,
              lease_owner TEXT,
              lease_until TEXT,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS capture_gaps (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source_key TEXT NOT NULL,
              generation INTEGER NOT NULL,
              from_offset INTEGER NOT NULL,
              to_offset INTEGER NOT NULL,
              reason TEXT NOT NULL,
              opened_at TEXT NOT NULL,
              closed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS parser_diagnostics (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source_key TEXT NOT NULL,
              generation INTEGER NOT NULL,
              byte_offset INTEGER NOT NULL,
              code TEXT NOT NULL,
              raw_sha256 TEXT NOT NULL,
              detail TEXT NOT NULL,
              UNIQUE(source_key, generation, byte_offset, code, raw_sha256)
            );
            """
        )

    @property
    def paused(self) -> bool:
        return bool(self.connection.execute("SELECT capture_paused FROM capture_control WHERE singleton=1").fetchone()[0])

    def cursor_for(self, source_key: str) -> SourceCursor | None:
        row = self.connection.execute("SELECT * FROM source_cursors WHERE source_key=?", (source_key,)).fetchone()
        if row is None:
            return None
        return SourceCursor(
            source_key=row["source_key"], path=row["path"], generation=row["generation"],
            file_identity=row["file_identity"], head_sha256=row["head_sha256"],
            byte_offset=row["byte_offset"], source_ordinal=row["source_ordinal"],
            parser_state=ParserState.from_dict(json.loads(row["parser_state_json"])),
            discard_until_newline=bool(row["discard_until_newline"]),
        )

    def ingest_batch(
        self,
        cursor: SourceCursor,
        events: Iterable[CaptureEvent],
        diagnostics: Iterable[Diagnostic],
    ) -> None:
        now = _now()
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            for event in events:
                self.connection.execute(
                    """INSERT OR IGNORE INTO event_queue(
                       event_id, rollout_id, source_key, source_generation, source_ordinal, category,
                       occurred_at, payload_json, raw_sha256, available_at, created_at
                       ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (event.event_id, event.rollout_id, cursor.source_key, cursor.generation,
                     event.source_ordinal, event.category, event.timestamp,
                     json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":")),
                     event.raw_sha256, now, now),
                )
            for diagnostic in diagnostics:
                self.connection.execute(
                    """INSERT OR IGNORE INTO parser_diagnostics(
                       source_key, generation, byte_offset, code, raw_sha256, detail
                       ) VALUES(?,?,?,?,?,?)""",
                    (cursor.source_key, cursor.generation, diagnostic.source["byte_offset"],
                     diagnostic.code, diagnostic.raw_sha256, diagnostic.detail),
                )
            self.connection.execute(
                """INSERT INTO source_cursors(
                   source_key,path,generation,file_identity,head_sha256,byte_offset,source_ordinal,
                   parser_state_json,discard_until_newline,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(source_key) DO UPDATE SET
                     path=excluded.path,generation=excluded.generation,file_identity=excluded.file_identity,
                     head_sha256=excluded.head_sha256,byte_offset=excluded.byte_offset,
                     source_ordinal=excluded.source_ordinal,parser_state_json=excluded.parser_state_json,
                     discard_until_newline=excluded.discard_until_newline,updated_at=excluded.updated_at""",
                (cursor.source_key, cursor.path, cursor.generation, cursor.file_identity,
                 cursor.head_sha256, cursor.byte_offset, cursor.source_ordinal,
                 json.dumps(cursor.parser_state.to_dict(), sort_keys=True),
                 int(cursor.discard_until_newline), now),
            )
            self.connection.execute("COMMIT")
        except Exception:
            self.connection.execute("ROLLBACK")
            raise

    def set_boundary(self, cursor: SourceCursor, reason: str, previous_offset: int) -> None:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            if cursor.byte_offset > previous_offset:
                self.connection.execute(
                    "INSERT INTO capture_gaps(source_key,generation,from_offset,to_offset,reason,opened_at,closed_at) VALUES(?,?,?,?,?,?,?)",
                    (cursor.source_key, cursor.generation, previous_offset, cursor.byte_offset, reason, _now(), _now()),
                )
            self.connection.execute(
                """INSERT INTO source_cursors(source_key,path,generation,file_identity,head_sha256,byte_offset,
                   source_ordinal,parser_state_json,discard_until_newline,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(source_key) DO UPDATE SET path=excluded.path,generation=excluded.generation,
                   file_identity=excluded.file_identity,head_sha256=excluded.head_sha256,
                   byte_offset=excluded.byte_offset,source_ordinal=excluded.source_ordinal,
                   parser_state_json=excluded.parser_state_json,discard_until_newline=excluded.discard_until_newline,
                   updated_at=excluded.updated_at""",
                (cursor.source_key, cursor.path, cursor.generation, cursor.file_identity, cursor.head_sha256,
                 cursor.byte_offset, cursor.source_ordinal, json.dumps(cursor.parser_state.to_dict(), sort_keys=True),
                 int(cursor.discard_until_newline), _now()),
            )
            self.connection.execute("COMMIT")
        except Exception:
            self.connection.execute("ROLLBACK")
            raise

    def pause_control(self) -> None:
        self.connection.execute(
            "UPDATE capture_control SET capture_paused=1,pause_epoch=pause_epoch+1,paused_at=? WHERE singleton=1", (_now(),)
        )

    def resume_control(self) -> None:
        self.connection.execute(
            "UPDATE capture_control SET capture_paused=0,resumed_at=? WHERE singleton=1", (_now(),)
        )

    def claim(self, limit: int, owner: str, lease_seconds: int) -> list[dict]:
        now = datetime.now(timezone.utc)
        until = (now + timedelta(seconds=lease_seconds)).isoformat()
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            rows = self.connection.execute(
                """SELECT event_id FROM event_queue
                   WHERE state='queued' AND available_at<=? AND (lease_until IS NULL OR lease_until<?)
                   ORDER BY created_at,event_id LIMIT ?""", (now.isoformat(), now.isoformat(), limit)
            ).fetchall()
            ids = [row[0] for row in rows]
            for event_id in ids:
                self.connection.execute(
                    "UPDATE event_queue SET lease_owner=?,lease_until=?,attempts=attempts+1 WHERE event_id=?",
                    (owner, until, event_id),
                )
            result = [dict(row) for row in self.connection.execute(
                f"SELECT * FROM event_queue WHERE event_id IN ({','.join('?' for _ in ids)}) ORDER BY created_at,event_id", ids
            ).fetchall()] if ids else []
            self.connection.execute("COMMIT")
            return result
        except Exception:
            self.connection.execute("ROLLBACK")
            raise

    def ack(self, event_ids: Iterable[str], owner: str) -> None:
        for event_id in event_ids:
            self.connection.execute(
                "DELETE FROM event_queue WHERE event_id=? AND lease_owner=?", (event_id, owner)
            )

    def nack(self, event_ids: Iterable[str], owner: str, retry_at: str) -> None:
        for event_id in event_ids:
            self.connection.execute(
                "UPDATE event_queue SET lease_owner=NULL,lease_until=NULL,available_at=? WHERE event_id=? AND lease_owner=?",
                (retry_at, event_id, owner),
            )

    def status(self) -> dict[str, int | bool]:
        return {
            "paused": self.paused,
            "queued": self.connection.execute("SELECT COUNT(*) FROM event_queue").fetchone()[0],
            "gaps": self.connection.execute("SELECT COUNT(*) FROM capture_gaps").fetchone()[0],
            "diagnostics": self.connection.execute("SELECT COUNT(*) FROM parser_diagnostics").fetchone()[0],
            "sources": self.connection.execute("SELECT COUNT(*) FROM source_cursors").fetchone()[0],
        }
