import tempfile
import unittest
from pathlib import Path

from memory_seed.adr import (
    AdrPredecessor,
    check_adrs,
    parse_adr,
    promote_decision,
    transition_adr,
)
from memory_seed.mcp_server import TOOLS, call_tool


class AdrSidecarTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        sessions = self.root / ".memory-seed" / "sessions" / "2026-07"
        sessions.mkdir(parents=True)
        (sessions / "2026-07-30.md").write_text(
            """---
tags:
  - session-log
session_date: 2026-07-30
---

## 2026-07-30 09:00 - Earlier decision

```yaml
entry_id: mse_prior
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
```

### Decision

- D: Keep the earlier design.
- R: It was the smallest useful design.

## 2026-07-30 10:00 - Current decision

```yaml
entry_id: mse_current
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
```

### Decisions

#### D1 - Adopt the transaction

- D: Use a composite writer.
- R: It preserves one validated boundary.

#### D2 - Keep ranking unchanged

- D: Expose the signal first.
- R: Ranking needs a separate gate.

## 2026-07-30 11:00 - Accept the ADR

```yaml
entry_id: mse_update
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
```

### Decision

- D: Accept the ADR.
- R: The walking skeleton passed.

## 2026-07-30 11:30 - Canonical source decision

```yaml
entry_id: mse_12345678
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
```

### Decision

- D: Use the composite writer.
- R: It preserves one validated boundary.
""",
            encoding="utf-8",
        )
        (self.root / ".memory-seed" / "topics.yaml").write_text(
            """schema_version: 2
topics:
  - slug: schema
    axis: area
  - slug: feature-build
    axis: activity
""",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_promote_replays_proposed_status_without_editing_source(self):
        source = (self.root / ".memory-seed" / "sessions" / "2026-07" / "2026-07-30.md").read_text(
            encoding="utf-8"
        )
        result = promote_decision(
            self.root,
            adr_id="adr_decision_sidecar_transaction",
            source_entry_id="mse_current",
            source_decision="d1",
            title="Decision sidecar transaction",
            topics=("seed-core",),
            user_initials="JNL",
            agent_type="codex",
            source="write-time",
            timestamp="2026-07-30T10:00:00Z",
        )
        self.assertTrue(result.ok, result.issues)
        self.assertTrue(result.written)
        record = parse_adr(result.path)
        self.assertEqual(record.current_decision, "mse_current:d1")
        self.assertEqual(record.current_status, "proposed")
        self.assertEqual(
            source,
            (self.root / ".memory-seed" / "sessions" / "2026-07" / "2026-07-30.md").read_text(
                encoding="utf-8"
            ),
        )

    def test_transition_requires_expected_state_and_update_entry(self):
        promoted = promote_decision(
            self.root,
            adr_id="adr_decision_sidecar_transaction",
            source_entry_id="mse_current",
            source_decision="d1",
            title="Decision sidecar transaction",
            topics=(),
            user_initials="JNL",
            agent_type="codex",
            source="write-time",
            timestamp="2026-07-30T10:00:00Z",
        )
        self.assertTrue(promoted.ok, promoted.issues)
        refused = transition_adr(
            self.root,
            adr_id="adr_decision_sidecar_transaction",
            status="accepted",
            update_entry_id="mse_update",
            expected_previous_status="accepted",
            source="write-time",
            timestamp="2026-07-30T11:00:00Z",
        )
        self.assertFalse(refused.ok)
        self.assertIn("current status is proposed", refused.issues[0])
        accepted = transition_adr(
            self.root,
            adr_id="adr_decision_sidecar_transaction",
            status="accepted",
            update_entry_id="mse_update",
            expected_previous_status="proposed",
            source="write-time",
            timestamp="2026-07-30T11:00:00Z",
        )
        self.assertTrue(accepted.ok, accepted.issues)
        self.assertEqual(parse_adr(accepted.path).current_status, "accepted")

    def test_promotion_validates_decision_identity_and_provenance(self):
        result = promote_decision(
            self.root,
            adr_id="ADR bad",
            source_entry_id="mse_current",
            source_decision="d9",
            title="Bad ADR",
            topics=(),
            user_initials="JNL",
            agent_type="codex",
            source="implicit",
            timestamp="2026-07-30T10:00:00Z",
            dry_run=True,
        )
        self.assertFalse(result.ok)
        joined = "\n".join(result.issues)
        self.assertIn("adr_id", joined)
        self.assertIn("source must be", joined)
        self.assertIn("missing decision", joined)

    def test_direct_predecessor_round_trips(self):
        result = promote_decision(
            self.root,
            adr_id="adr_decision_sidecar_transaction",
            source_entry_id="mse_current",
            source_decision="d1",
            title="Decision sidecar transaction",
            topics=(),
            user_initials="JNL",
            agent_type="codex",
            source="write-time",
            direct_predecessors=(
                AdrPredecessor(
                    "mse_prior:d1",
                    "link:mse_current:d1:evolves:mse_prior:d1",
                ),
            ),
            timestamp="2026-07-30T10:00:00Z",
        )
        self.assertTrue(result.ok, result.issues)
        record = parse_adr(result.path)
        self.assertEqual(record.direct_predecessors[0].decision, "mse_prior:d1")
        self.assertEqual(check_adrs(self.root), (True, []))

    def test_mcp_show_and_check_are_read_only_views_over_the_shared_core(self):
        promoted = promote_decision(
            self.root,
            adr_id="adr_decision_sidecar_transaction",
            source_entry_id="mse_current",
            source_decision="d1",
            title="Decision sidecar transaction",
            topics=("seed-core",),
            user_initials="JNL",
            agent_type="codex",
            source="write-time",
            timestamp="2026-07-30T10:00:00Z",
        )
        self.assertTrue(promoted.ok, promoted.issues)
        shown = call_tool(
            "memory_adr_show",
            {"cwd": str(self.root), "adr_id": "adr_decision_sidecar_transaction"},
        )
        self.assertEqual(shown["current_status"], "proposed")
        self.assertTrue(call_tool("memory_adrs_check", {"cwd": str(self.root)})["ok"])

    def test_mcp_registers_adr_surfaces(self):
        names = {tool["name"] for tool in TOOLS}
        self.assertTrue(
            {
                "memory_adr_show",
                "memory_adrs_check",
            }.issubset(names)
        )

    def test_mcp_review_gate_writes_zero_then_appends_a_revision_proposal(self):
        promoted = promote_decision(
            self.root,
            adr_id="adr_decision_sidecar_transaction",
            source_entry_id="mse_12345678",
            source_decision="d1",
            title="Decision sidecar transaction",
            topics=("schema",),
            user_initials="JNL",
            agent_type="codex",
            source="write-time",
            decision="Use the composite writer.",
            why="It preserves a single validation boundary.",
            timestamp="2026-07-30T10:00:00",
        )
        self.assertTrue(promoted.ok, promoted.issues)
        accepted = transition_adr(
            self.root,
            adr_id="adr_decision_sidecar_transaction",
            status="accepted",
            decision_ref="mse_12345678:d1",
            update_entry_id="mse_update",
            expected_authoritative_decision=None,
            source="write-time",
            timestamp="2026-07-30T11:00:00",
        )
        self.assertTrue(accepted.ok, accepted.issues)
        payload = {
            "cwd": str(self.root),
            "title": "Evolve the sidecar transaction",
            "body": "### Summary\n\n- Evolve the writer.\n\n### Decision\n\n- D: Add the ADR ledger to the transaction.\n- R: Review and mutation must remain atomic.",
            "user_initials": "JNL",
            "agent_type": "codex",
            "timestamp": "2026-07-30 12:00",
            "auto_branch": False,
            "decisions": [{
                "decision": "d1",
                "topics": {"area": "schema", "activity": "feature-build", "source": "write-time"},
                "links": {"evolves": ["mse_12345678"]},
            }],
        }
        session_file = self.root / ".memory-seed" / "sessions" / "2026-07" / "2026-07-30.md"
        before_session = session_file.read_bytes()
        before_adr = promoted.path.read_bytes()
        gated = call_tool("memory_session_append", payload)
        self.assertFalse(gated["ok"])
        self.assertTrue(gated["review_required"])
        self.assertFalse(gated["written"])
        self.assertEqual(session_file.read_bytes(), before_session)
        self.assertEqual(promoted.path.read_bytes(), before_adr)
        self.assertEqual(gated["matched_adrs"][0]["authoritative_decision"], "mse_12345678:d1")

        payload["adr_review_receipt"] = gated["adr_review_receipt"]
        payload["decisions"][0]["adrs"] = [{
            "adr_id": "adr_decision_sidecar_transaction",
            "outcome": "revise",
            "decision": "Include ADR events in the composite writer.",
            "why": "The review result and its source decision publish together.",
            "evolution": "Extends the transaction from topic/link sidecars to living ADR ledgers.",
        }]
        written = call_tool("memory_session_append", payload)
        self.assertTrue(written["ok"], written["issues"])
        self.assertTrue(written["written"])
        record = parse_adr(promoted.path)
        self.assertEqual(record.authoritative_decision, "mse_12345678:d1")
        self.assertEqual(record.current_status, "accepted")
        self.assertIn(written["entry_id"] + ":d1", record.state.pending_decisions)
        self.assertTrue(call_tool("memory_adrs_check", {"cwd": str(self.root)})["ok"])

    def test_changed_reviewed_draft_invalidates_receipt(self):
        promoted = promote_decision(
            self.root,
            adr_id="adr_decision_sidecar_transaction",
            source_entry_id="mse_12345678",
            source_decision="d1",
            title="Decision sidecar transaction",
            topics=(),
            user_initials="JNL",
            agent_type="codex",
            source="write-time",
            timestamp="2026-07-30T10:00:00",
        )
        self.assertTrue(promoted.ok, promoted.issues)
        payload = {
            "cwd": str(self.root),
            "title": "Review lineage",
            "body": "### Summary\n\n- Review.\n\n### Decision\n\n- D: Evolve it.\n- R: New evidence.",
            "user_initials": "JNL",
            "agent_type": "codex",
            "timestamp": "2026-07-30 12:00",
            "auto_branch": False,
            "decisions": [{"decision": "d1", "topics": {"area": "schema", "activity": "feature-build"}, "links": {"evolves": ["mse_12345678"]}}],
        }
        first = call_tool("memory_session_append", payload)
        payload["adr_review_receipt"] = first["adr_review_receipt"]
        payload["body"] = payload["body"].replace("New evidence.", "Different evidence.")
        payload["decisions"][0]["adrs"] = [{"adr_id": "adr_decision_sidecar_transaction", "outcome": "no-change", "reason": "Another aspect."}]
        stale = call_tool("memory_session_append", payload)
        self.assertFalse(stale["ok"])
        self.assertTrue(stale["review_required"])
        self.assertIn("stale", "\n".join(stale["issues"]))


if __name__ == "__main__":
    unittest.main()
