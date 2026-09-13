"""Derived temporal-lineage cache checks."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from memory_seed import temporal_lineage
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

    def test_checkpoint_is_only_an_upper_bound_without_claim_attestation(self):
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
        self.assertEqual(record["calendar_time"], "upper-bound-only")
        self.assertEqual(record["trusted_checkpoint_evidence"][0]["relationship"], "exists-no-later-than")
        self.assertEqual(record["claimed_timestamp_evidence"], [])
        self.assertEqual(record["claimed_timestamp_relation"], "backdated-relative-to-commit-clock")
        self.assertTrue(temporal_lineage_cache_path(repo).exists())
        self.assertEqual(first["cache_ignore_status"], "registered")
        self.assertIn(".memory-seed/.temporal-lineage.json", (repo / ".gitignore").read_text(encoding="utf-8"))

        direct = refresh_temporal_lineage(
            repo,
            [self.decision()],
            trusted_checkpoints=[{
                "commit": introduced,
                "witnessed_at": "2026-01-01T00:00:00+00:00",
                "evidence_kind": "claimed-timestamp-attestation",
                "attested_claimed_timestamp": "2000-01-01T00:00:00+00:00",
            }],
        )
        self.assertEqual(direct["decisions"][DECISION]["calendar_time"], "independently-witnessed")
        self.assertEqual(len(direct["decisions"][DECISION]["claimed_timestamp_evidence"]), 1)

    def test_incremental_changed_decision_searches_only_cached_head_delta(self):
        repo = self.make_repo()
        introduced = self.commit(repo, ".memory-seed/sessions/entry.md", DECISION + "\n")
        refresh_temporal_lineage(repo, [self.decision()])
        changed_head = self.commit(repo, ".memory-seed/sessions/entry.md", DECISION + "\nchanged\n")
        original = temporal_lineage._first_introducing_commit
        with mock.patch.object(temporal_lineage, "_first_introducing_commit", wraps=original) as scan:
            result = refresh_temporal_lineage(repo, [self.decision(digest="sha256:" + "2" * 64)])
        self.assertEqual(result["recomputed"], [DECISION])
        self.assertEqual(result["decisions"][DECISION]["first_introducing_commit"], introduced)
        self.assertEqual(result["decisions"][DECISION]["history_scope"], "git-delta")
        self.assertEqual(scan.call_args.kwargs["revision"], f"{introduced}..{changed_head}")

    def test_incremental_reuse_needs_no_history_scan(self):
        repo = self.make_repo()
        introduced = self.commit(repo, ".memory-seed/sessions/entry.md", "#### D1\n" + DECISION + "\n")
        refresh_temporal_lineage(repo, [self.decision()])
        self.commit(repo, "unrelated.txt", "later\n")
        with mock.patch.object(temporal_lineage, "_first_introducing_commit", side_effect=AssertionError("unexpected scan")):
            second = refresh_temporal_lineage(repo, [self.decision()])
        self.assertEqual(second["reused"], [DECISION])
        self.assertEqual(second["recomputed"], [])

    def test_unignored_cache_is_not_published(self):
        repo = self.make_repo()
        self.commit(repo, ".memory-seed/sessions/entry.md", DECISION + "\n")
        path = repo / ".memory-seed" / "refused.json"
        with mock.patch.object(temporal_lineage, "_ensure_ignored", return_value=(False, "ignore-registration-failed")):
            result = refresh_temporal_lineage(repo, [self.decision()], cache_path=path)
        self.assertFalse(result["cache_published"])
        self.assertEqual(result["cache_status"], "cache-unignored")
        self.assertEqual(result["cache_ignore_status"], "ignore-registration-failed")
        self.assertFalse(path.exists())

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
