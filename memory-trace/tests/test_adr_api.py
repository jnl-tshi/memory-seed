"""Contract coverage for the typed Living ADR Trace endpoints."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from memory_seed.adr import promote_decision, transition_adr
from memory_trace.service import create_app


class AdrApiTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="memory-trace-adr-api-"))
        self.cache_root = Path(tempfile.mkdtemp(prefix="memory-trace-adr-cache-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(self.cache_root, ignore_errors=True))
        sessions = self.cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True)
        # An ADR carrying topics requires a canonical vocabulary to validate them against
        # (`validate_adr`: "ADR topics require .memory-seed/topics.yaml", 2026-08-03). The rule is
        # deliberate - a topic outside the vocabulary is an error, not a free-text label - so the
        # fixture supplies one rather than the ADR dropping its topic.
        (self.cwd / ".memory-seed" / "topics.yaml").write_text(
            "schema_version: 2\ntopics:\n"
            "  - slug: cache\n    description: Caching and projections.\n    axis: area\n",
            encoding="utf-8",
        )
        (sessions / "2026-08-03.md").write_text(
            """---
tags:
  - session-log
---

## 2026-08-03 10:00 - Choose the cache format

```yaml
entry_id: mse_adrsrc
user_initials: JN
agent_type: codex
project_path: .
subproject_path: null
```

### Decision

- D: Use a typed cache format.
- R: Trace clients need a stable contract.

## 2026-08-03 11:00 - Accept the cache format

```yaml
entry_id: mse_adraccept
user_initials: JN
agent_type: codex
project_path: .
subproject_path: null
```

### Decision

- D: Accept the cache format.
- R: The API contract validates it.
""",
            encoding="utf-8",
        )
        promoted = promote_decision(
            self.cwd,
            adr_id="adr_cache_format",
            source_entry_id="mse_adrsrc",
            source_decision="d1",
            title="Cache format",
            topics=("cache",),
            user_initials="JN",
            agent_type="codex",
            source="write-time",
            decision="Use a typed cache format.",
            why="Trace clients need a stable contract.",
            evolution="Initial proposal.",
            timestamp="2026-08-03T10:00:00Z",
        )
        self.assertTrue(promoted.ok, promoted.issues)
        accepted = transition_adr(
            self.cwd,
            adr_id="adr_cache_format",
            status="accepted",
            decision_ref="mse_adrsrc:d1",
            update_entry_id="mse_adraccept",
            expected_previous_status="proposed",
            source="write-time",
            timestamp="2026-08-03T11:00:00Z",
        )
        self.assertTrue(accepted.ok, accepted.issues)
        with mock.patch.dict(os.environ, {"MEMORY_SEED_LENSE_CACHE_ROOT": str(self.cache_root)}):
            self.app = create_app(self.cwd, rebuild_cache=True)

    def client(self):
        from fastapi.testclient import TestClient

        return TestClient(self.app)

    def test_adr_index_is_concise_and_detail_is_a_complete_living_ledger(self):
        client = self.client()

        index = client.get("/api/v1/adrs")
        self.assertEqual(index.status_code, 200)
        summary = index.json()["adrs"][0]
        self.assertEqual(summary["adr_id"], "adr_cache_format")
        self.assertEqual(summary["current_status"], "accepted")
        self.assertEqual(summary["authoritative_decision"], "mse_adrsrc:d1")
        self.assertEqual(summary["events"], [])
        self.assertEqual(summary["source_excerpts"], {})

        detail = client.get("/api/v1/adrs/adr_cache_format")
        self.assertEqual(detail.status_code, 200)
        record = detail.json()
        self.assertEqual(record["current"]["decision"], "Use a typed cache format.")
        self.assertEqual(record["current"]["reason"], "Trace clients need a stable contract.")
        self.assertEqual(record["current"]["impact"], "Initial proposal.")
        self.assertEqual(record["current"]["why"], "Trace clients need a stable contract.")
        self.assertEqual(len(record["events"]), 2)
        self.assertIn("mse_adrsrc:d1", record["membership"])
        self.assertIn("mse_adrsrc:d1", record["source_excerpts"])

    def test_missing_adr_is_a_404(self):
        self.assertEqual(self.client().get("/api/v1/adrs/adr_missing").status_code, 404)


if __name__ == "__main__":
    unittest.main()
