"""Attention signal tests (attention-retrieval-signal-proposal.md).

Covers the full contract: decay math, fetch-vs-impression weighting, compaction
round-trip, fail-open behaviour, dispatch instrumentation at the MCP choke
point, read-only exposure on both retrieval surfaces, and - the load-bearing
guarantee - that default ranking stays byte-for-byte identical while the boost
is off, however much attention data exists.
"""

import json
import shutil
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from memory_seed import attention
from memory_seed.attention import (
    compact_if_needed,
    load_attention,
    record_event,
)
from memory_seed.mcp_server import handle_jsonrpc_message
from memory_seed.retrieval import get_chunk, search_memory
from memory_seed.semantic_cache import rank_session_memory


def _utc(days_ago: float = 0.0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


class AttentionModuleTests(unittest.TestCase):
    def make_memory_dir(self):
        root = Path(tempfile.mkdtemp(prefix="memory-seed-attention-test-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        memory_dir = root / ".memory-seed"
        memory_dir.mkdir()
        return memory_dir

    def test_decay_math(self):
        memory_dir = self.make_memory_dir()
        now = _utc()
        record_event(memory_dir, "memory_get_chunk", "mse_a", ts=now)
        record_event(memory_dir, "memory_get_chunk", "mse_a", ts=_utc(attention.HALF_LIFE_DAYS))
        folded = load_attention(memory_dir, now)
        self.assertIn("mse_a", folded)
        self.assertAlmostEqual(folded["mse_a"]["attention_score"], 1.5, places=3)
        self.assertEqual(folded["mse_a"]["fetch_count"], 2)
        self.assertEqual(
            folded["mse_a"]["last_fetch"], now.isoformat(timespec="seconds")
        )

    def test_impressions_are_logged_but_weigh_zero(self):
        memory_dir = self.make_memory_dir()
        now = _utc()
        record_event(memory_dir, "memory_search", "mse_a", ts=now)
        record_event(memory_dir, "memory_search", "mse_a", ts=now)
        record_event(memory_dir, "memory_get_chunk", "mse_a", ts=now)
        log_lines = (memory_dir / attention.LOG_NAME).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(log_lines), 3)
        folded = load_attention(memory_dir, now)
        self.assertAlmostEqual(folded["mse_a"]["attention_score"], 1.0, places=6)
        self.assertEqual(folded["mse_a"]["fetch_count"], 1)

    def test_compact_round_trip_preserves_scores(self):
        memory_dir = self.make_memory_dir()
        now = _utc()
        for days_ago in (0, 10, 45):
            record_event(memory_dir, "memory_get_chunk", "mse_a", ts=_utc(days_ago))
        record_event(memory_dir, "memory_get_chunk", "mse_b", ts=_utc(3))
        before = load_attention(memory_dir, now)
        with mock.patch.object(attention, "COMPACT_THRESHOLD", 2):
            self.assertTrue(compact_if_needed(memory_dir, now))
        self.assertEqual(
            (memory_dir / attention.LOG_NAME).read_text(encoding="utf-8"), ""
        )
        self.assertTrue((memory_dir / attention.SUMMARY_NAME).exists())
        after = load_attention(memory_dir, now)
        for entry_id in ("mse_a", "mse_b"):
            # places=4, not tighter: the summary's as_of is truncated to whole
            # seconds, so the reload legitimately decays scores by up to one
            # second's worth (~3e-7 relative at the 30d half-life).
            self.assertAlmostEqual(
                after[entry_id]["attention_score"],
                before[entry_id]["attention_score"],
                places=4,
            )
            self.assertEqual(after[entry_id]["fetch_count"], before[entry_id]["fetch_count"])
        # New events keep folding on top of the compacted summary.
        record_event(memory_dir, "memory_get_chunk", "mse_a", ts=now)
        self.assertEqual(load_attention(memory_dir, now)["mse_a"]["fetch_count"], 4)

    def test_fail_open(self):
        missing = Path(tempfile.gettempdir()) / "memory-seed-attention-nonexistent" / ".memory-seed"
        record_event(missing, "memory_get_chunk", "mse_a")  # must not raise
        self.assertEqual(load_attention(missing), {})
        self.assertFalse(compact_if_needed(missing))

    def test_gitignore_self_registration(self):
        memory_dir = self.make_memory_dir()
        record_event(memory_dir, "memory_get_chunk", "mse_a")
        gitignore = (memory_dir.parent / ".gitignore").read_text(encoding="utf-8")
        for entry in attention.GITIGNORE_ENTRIES:
            self.assertIn(entry, gitignore)


class AttentionRetrievalSurfaceTests(unittest.TestCase):
    """Instrumentation and exposure over a real (tiny) session store."""

    def make_store(self):
        root = Path(tempfile.mkdtemp(prefix="memory-seed-attention-store-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        sessions = root / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True)
        (sessions / "2026-05-17.md").write_text(
            "## 2026-05-17 09:15 - Bootstrap mode check fix\n\n"
            "```yaml\n"
            "entry_id: ms-bootstrap\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "Updated AGENTS.md to require checking for initialized memory files.\n",
            encoding="utf-8",
        )
        (sessions / "2026-05-18.md").write_text(
            "## 2026-05-18 09:15 - Compact command agent routine\n\n"
            "```yaml\n"
            "entry_id: ms-compact\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "Added compact behavior for agents to run memory-seed compact.\n",
            encoding="utf-8",
        )
        return root

    def rpc(self, name, arguments):
        return handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )

    def test_dispatch_instruments_search_and_fetch(self):
        cwd = self.make_store()
        memory_dir = cwd / ".memory-seed"
        self.rpc(
            "memory_search",
            {"query": "bootstrap mode", "cwd": str(cwd), "semantic_enabled": False},
        )
        log_path = memory_dir / attention.LOG_NAME
        self.assertTrue(log_path.exists())
        events = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertTrue(events)
        self.assertTrue(all(event["tool"] == "memory_search" for event in events))
        # Impressions alone score nothing.
        self.assertEqual(load_attention(memory_dir), {})

        payload = search_memory(
            "bootstrap mode", cwd, semantic_enabled=False, today=date(2026, 5, 19)
        )
        chunk_id = payload["results"][0]["chunk_id"]
        self.rpc("memory_get_chunk", {"chunk_id": chunk_id, "cwd": str(cwd)})
        folded = load_attention(memory_dir)
        self.assertEqual(folded["ms-bootstrap"]["fetch_count"], 1)
        self.assertGreater(folded["ms-bootstrap"]["attention_score"], 0.9)

    def test_search_rows_and_get_chunk_expose_attention_fields(self):
        cwd = self.make_store()
        memory_dir = cwd / ".memory-seed"
        record_event(memory_dir, "memory_get_chunk", "ms-bootstrap", ts=_utc())
        payload = search_memory(
            "bootstrap mode", cwd, semantic_enabled=False, today=date(2026, 5, 19)
        )
        rows = {row["entry_id"]: row for row in payload["results"]}
        self.assertEqual(rows["ms-bootstrap"]["fetch_count"], 1)
        self.assertGreater(rows["ms-bootstrap"]["attention_score"], 0.9)
        self.assertIsNotNone(rows["ms-bootstrap"]["last_fetch"])
        for row in payload["results"]:
            self.assertIn("attention_score", row)
            self.assertIn("fetch_count", row)
            self.assertIn("last_fetch", row)
        chunk = get_chunk(rows["ms-bootstrap"]["chunk_id"], cwd)
        self.assertEqual(chunk["fetch_count"], 1)
        self.assertGreater(chunk["attention_score"], 0.9)

    def test_default_ranking_identical_with_boost_off(self):
        cwd = self.make_store()
        memory_dir = cwd / ".memory-seed"
        baseline = rank_session_memory(
            "agent routine", cwd, today=date(2026, 5, 19), embedding_provider=None
        )
        # Pile attention onto the entry the baseline ranks lower.
        for _ in range(25):
            record_event(memory_dir, "memory_get_chunk", baseline[-1].chunk.entry_id, ts=_utc())
        unboosted = rank_session_memory(
            "agent routine", cwd, today=date(2026, 5, 19), embedding_provider=None
        )
        self.assertEqual(
            [(r.chunk.chunk_id, r.final_score) for r in baseline],
            [(r.chunk.chunk_id, r.final_score) for r in unboosted],
        )

    def test_boost_on_lifts_fetched_entry(self):
        cwd = self.make_store()
        memory_dir = cwd / ".memory-seed"
        baseline = rank_session_memory(
            "agent routine", cwd, today=date(2026, 5, 19), embedding_provider=None
        )
        target = baseline[-1].chunk.entry_id
        for _ in range(25):
            record_event(memory_dir, "memory_get_chunk", target, ts=_utc())
        boosted = rank_session_memory(
            "agent routine",
            cwd,
            today=date(2026, 5, 19),
            embedding_provider=None,
            attention_boost=True,
        )
        by_id = {r.chunk.entry_id: r for r in boosted}
        baseline_by_id = {r.chunk.entry_id: r for r in baseline}
        self.assertGreater(by_id[target].final_score, baseline_by_id[target].final_score)


if __name__ == "__main__":
    unittest.main()
