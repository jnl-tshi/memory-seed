"""Derived temporal-lineage cache checks."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from memory_seed.temporal_lineage import (
    TEMPORAL_LINEAGE_SCHEMA,
    refresh_temporal_lineage,
    temporal_lineage_cache_path,
)


DECISION = "mse_abcd1234:d1"
DIGEST = "sha256:" + "1" * 64


class TemporalLineageTests(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="memory-seed-temporal-lineage-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        self.git(root, "init", "-q")
        self.git(root, "config", "user.name", "Test")
        self.git(root, "config", "user.email", "test@example.invalid")
        return root

    def git(self, cwd: Path, *args: str) -> str:
        return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True).stdout.strip()

    def commit(self, cwd: Path, path: str, text: str, message: str = "entry") -> str:
        target = cwd / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        self.git(cwd, "add", "-A")
        self.git(cwd, "commit", "-qm", message)
        return self.git(cwd, "rev-parse", "HEAD")

    def decision(self, *, digest: str = DIGEST, timestamp: str = "2000-01-01T00:00:00+00:00") -> dict[str, str]:
        return {
            "decision_ref": DECISION,
            "source_digest": digest,
            "claimed_timestamp": timestamp,
            "source_path": ".memory-seed/sessions/entry.md",
        }

    def test_cold_then_incremental_reuse_and_checkpoint_classification(self):
        repo = self.make_repo()
        introduced = self.commit(repo, ".memory-seed/sessions/entry.md", "#### D1\n" + DECISION + "\n")
        first = refresh_temporal_lineage(
            repo,
            [self.decision()],
            trusted_checkpoints=[{"commit": introduced, "witnessed_at": "2026-01-01T00:00:00+00:00"}],
            now=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        record = first["decisions"][DECISION]
        self.assertEqual(record["first_introducing_commit"], introduced)
        self.assertEqual(record["relative_order"], "verified-reachable-order")
        self.assertEqual(record["calendar_time"], "independently-witnessed")
        self.assertEqual(record["claimed_timestamp_relation"], "backdated-relative-to-commit-clock")
        self.assertTrue(temporal_lineage_cache_path(repo).exists())

        self.commit(repo, "unrelated.txt", "later\n")
        second = refresh_temporal_lineage(
            repo,
            [self.decision()],
            trusted_checkpoints=[{"commit": introduced, "witnessed_at": "2026-01-01T00:00:00+00:00"}],
        )
        self.assertEqual(second["reused"], [DECISION])
        self.assertEqual(second["recomputed"], [])

        changed = refresh_temporal_lineage(repo, [self.decision(digest="sha256:" + "2" * 64)])
        self.assertEqual(changed["recomputed"], [DECISION])
        self.assertEqual(changed["decisions"][DECISION]["calendar_time"], "unwitnessed")

    def test_rewritten_ancestry_and_future_claim_invalidate_and_rebuild(self):
        repo = self.make_repo()
        self.commit(repo, ".memory-seed/sessions/entry.md", DECISION + "\n")
        cache = temporal_lineage_cache_path(repo)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({
            "schema": TEMPORAL_LINEAGE_SCHEMA,
            "version": 1,
            "head": "f" * 40,
            "decisions": {},
        }), encoding="utf-8")
        result = refresh_temporal_lineage(
            repo, [self.decision(timestamp="2999-01-01T00:00:00+00:00")],
            now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        self.assertTrue(result["invalidated"])
        self.assertEqual(result["cache_status"], "rewritten-ancestry")
        self.assertEqual(result["decisions"][DECISION]["claimed_timestamp_relation"], "future-dated")

    def test_non_git_directory_returns_no_persistent_authority_claim(self):
        root = Path(tempfile.mkdtemp(prefix="memory-seed-temporal-no-git-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        result = refresh_temporal_lineage(root, [self.decision()])
        self.assertFalse(result["git_available"])
        self.assertEqual(result["cache_status"], "git-unavailable")
        self.assertFalse(temporal_lineage_cache_path(root).exists())


if __name__ == "__main__":
    unittest.main()
