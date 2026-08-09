import copy
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from memory_seed.adr import (
    AdrEvent,
    AdrPredecessor,
    adr_membership,
    adr_review_context,
    canonical_decision_refs,
    check_adrs,
    parse_adr,
    parse_adr_text,
    promote_decision,
    reconcile_adr_records,
    render_adr,
    revise_adr,
    transition_adr,
    validate_adr,
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

## 2026-07-30 12:00 - Branch A decision

```yaml
entry_id: mse_brancha
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
```

### Decision

- D: Explore branch A.
- R: It exercises independent ADR lineage.

## 2026-07-30 12:01 - Branch B decision

```yaml
entry_id: mse_branchb
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
```

### Decision

- D: Explore branch B.
- R: It exercises independent ADR lineage.

## 2026-07-30 12:02 - Converged decision

```yaml
entry_id: mse_converge
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
```

### Decision

- D: Converge the branches.
- R: The accepted root remains an ancestor.

## 2026-07-30 12:03 - Outside lineage decision

```yaml
entry_id: mse_outside1
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
```

### Decision

- D: Keep an unrelated decision.
- R: It must not trigger unrelated ADR review.
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

    def _promote_accepted(self, adr_id="adr_decision_sidecar_transaction"):
        promoted = promote_decision(
            self.root,
            adr_id=adr_id,
            source_entry_id="mse_12345678",
            source_decision="d1",
            title="Decision sidecar transaction",
            topics=(),
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
            adr_id=adr_id,
            status="accepted",
            decision_ref="mse_12345678:d1",
            update_entry_id="mse_update",
            expected_authoritative_decision=None,
            source="write-time",
            timestamp="2026-07-30T11:00:00",
        )
        self.assertTrue(accepted.ok, accepted.issues)
        return promoted

    def _review_payload(self, *, title="Review lineage", timestamp="2026-07-30 12:10"):
        return {
            "cwd": str(self.root),
            "title": title,
            "body": "### Summary\n\n- Review.\n\n### Decision\n\n- D: Evolve it.\n- R: New evidence.",
            "user_initials": "JNL",
            "agent_type": "codex",
            "timestamp": timestamp,
            "auto_branch": False,
            "decisions": [{
                "decision": "d1",
                "topics": {"area": "schema", "activity": "feature-build"},
                "links": {"evolves": [{"ref": "mse_12345678", "type": "refines", "why": "test fixture edge"}]},
            }],
        }

    @staticmethod
    def _no_change(adr_id="adr_decision_sidecar_transaction", reason="No change is needed."):
        return {"adr_id": adr_id, "outcome": "no-change", "reason": reason}

    @staticmethod
    def _workspace_snapshot(root: Path):
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

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
            topics=("schema",),
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

    def test_integrity_rejects_malformed_timestamps_event_ids_topics_and_missing_provenance(self):
        promoted = self._promote_accepted()
        base = parse_adr(promoted.path)

        malformed_created = copy.deepcopy(base)
        malformed_created.created_at = "not-a-timestamp"
        self.assertTrue(any("created_at" in issue for issue in validate_adr(malformed_created, self.root)))

        malformed_event = copy.deepcopy(base)
        malformed_event.events[0] = replace(
            malformed_event.events[0], event_id="x", timestamp="not-a-timestamp", update_entry_id=None
        )
        event_issues = "\n".join(validate_adr(malformed_event, self.root))
        self.assertIn("malformed event_id", event_issues)
        self.assertIn("timestamp must be ISO-8601", event_issues)
        self.assertIn("requires update_entry_id", event_issues)

        unknown_topic = copy.deepcopy(base)
        unknown_topic.topics = ("not-controlled",)
        self.assertTrue(any("not a canonical slug" in issue for issue in validate_adr(unknown_topic, self.root)))

    def test_lifecycle_writers_refuse_noncanonical_or_unrecognized_existing_bytes(self):
        promoted = self._promote_accepted()
        path = promoted.path
        canonical = path.read_text(encoding="utf-8")

        noncanonical = canonical.replace("## Event ledger", "Authored note.\n\n## Event ledger", 1)
        path.write_text(noncanonical, encoding="utf-8")
        revised = revise_adr(
            self.root,
            adr_id="adr_decision_sidecar_transaction",
            decision_ref="mse_current:d2",
            decision="Do not normalize existing bytes.",
            why="Append-only history must fail closed.",
            evolution="It would follow the accepted head.",
            update_entry_id="mse_update",
            source="write-time",
            predecessors=(AdrPredecessor(
                "mse_12345678:d1", "link:mse_current:d2:evolves:mse_12345678:d1",
            ),),
            timestamp="2026-07-30T12:00:00",
        )
        self.assertFalse(revised.ok)
        self.assertTrue(any("not canonical" in issue for issue in revised.issues), revised.issues)
        self.assertEqual(path.read_text(encoding="utf-8"), noncanonical)

        unknown_event = canonical + "\n### revision-withdrawn - 2026-07-30T12:00:00\n\nAuthored bytes.\n"
        path.write_text(unknown_event, encoding="utf-8")
        transitioned = transition_adr(
            self.root,
            adr_id="adr_decision_sidecar_transaction",
            status="superseded",
            update_entry_id="mse_update",
            expected_authoritative_decision="mse_12345678:d1",
            replacement_adr="adr_replacement",
            source="write-time",
            timestamp="2026-07-30T12:00:00",
        )
        self.assertFalse(transitioned.ok)
        self.assertTrue(any("not canonical" in issue for issue in transitioned.issues), transitioned.issues)
        self.assertEqual(path.read_text(encoding="utf-8"), unknown_event)

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
            topics=("schema",),
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
            "timestamp": "2026-07-30 12:10",
            "auto_branch": False,
            "decisions": [{
                "decision": "d1",
                "topics": {"area": "schema", "activity": "feature-build", "source": "write-time"},
                "links": {"evolves": [{"ref": "mse_12345678", "type": "refines", "why": "test fixture edge"}]},
            }],
        }
        before_gate = self._workspace_snapshot(self.root)
        gated = call_tool("memory_session_append", payload)
        self.assertFalse(gated["ok"])
        self.assertTrue(gated["review_required"])
        self.assertFalse(gated["written"])
        self.assertEqual(self._workspace_snapshot(self.root), before_gate)
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

    def test_mcp_review_retry_refuses_to_normalize_noncanonical_adr_bytes(self):
        promoted = self._promote_accepted()
        payload = self._review_payload()
        gated = call_tool("memory_session_append", payload)
        self.assertTrue(gated["review_required"])

        source = promoted.path.read_text(encoding="utf-8")
        noncanonical = source.replace("## Event ledger", "Authored note.\n\n## Event ledger", 1)
        promoted.path.write_text(noncanonical, encoding="utf-8")
        before_retry = self._workspace_snapshot(self.root)
        payload["adr_review_receipt"] = gated["adr_review_receipt"]
        payload["decisions"][0]["adrs"] = [self._no_change()]
        refused = call_tool("memory_session_append", payload)
        self.assertFalse(refused["ok"])
        self.assertTrue(any("not canonical" in issue for issue in refused["issues"]), refused["issues"])
        self.assertEqual(self._workspace_snapshot(self.root), before_retry)

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
            "decisions": [{"decision": "d1", "topics": {"area": "schema", "activity": "feature-build"}, "links": {"evolves": [{"ref": "mse_12345678", "type": "refines", "why": "test fixture edge"}]}}],
        }
        first = call_tool("memory_session_append", payload)
        payload["adr_review_receipt"] = first["adr_review_receipt"]
        payload["body"] = payload["body"].replace("New evidence.", "Different evidence.")
        payload["decisions"][0]["adrs"] = [{"adr_id": "adr_decision_sidecar_transaction", "outcome": "no-change", "reason": "Another aspect."}]
        stale = call_tool("memory_session_append", payload)
        self.assertFalse(stale["ok"])
        self.assertTrue(stale["review_required"])
        self.assertIn("stale", "\n".join(stale["issues"]))

    def test_replay_preserves_accepted_head_for_pending_rejected_and_no_change_events(self):
        promoted = self._promote_accepted()
        revised = revise_adr(
            self.root,
            adr_id="adr_decision_sidecar_transaction",
            decision_ref="mse_current:d2",
            decision="Keep ranking unchanged.",
            why="The ranking gate is still separate.",
            evolution="Propose a constrained refinement.",
            update_entry_id="mse_update",
            source="write-time",
            predecessors=(AdrPredecessor(
                "mse_12345678:d1",
                "link:mse_current:d2:evolves:mse_12345678:d1",
            ),),
            timestamp="2026-07-30T12:00:00",
        )
        self.assertTrue(revised.ok, revised.issues)
        pending = parse_adr(promoted.path)
        self.assertEqual(pending.authoritative_decision, "mse_12345678:d1")
        self.assertEqual(pending.state.pending_decisions, ("mse_current:d2",))

        rejected = transition_adr(
            self.root,
            adr_id="adr_decision_sidecar_transaction",
            status="rejected",
            decision_ref="mse_current:d2",
            update_entry_id="mse_update",
            expected_authoritative_decision="mse_12345678:d1",
            source="write-time",
            reason="The refinement is premature.",
            timestamp="2026-07-30T12:30:00",
        )
        self.assertTrue(rejected.ok, rejected.issues)
        record = parse_adr(promoted.path)
        self.assertEqual(record.authoritative_decision, "mse_12345678:d1")
        self.assertEqual(record.state.rejected_decisions, ("mse_current:d2",))

        before_membership = adr_membership(record)
        record.events.append(AdrEvent(
            "reviewed-no-change", "adre_auditable_no_change", "2026-07-30T13:00:00", "write-time",
            "mse_current:d2", "mse_update", matched_decisions=("mse_12345678:d1",),
            reason="The accepted head remains appropriate.",
        ))
        self.assertEqual(validate_adr(record, self.root), [])
        self.assertEqual(record.authoritative_decision, "mse_12345678:d1")
        self.assertEqual(adr_membership(record), before_membership)
        self.assertEqual(record.events[-1].kind, "reviewed-no-change")

    def test_supersession_retains_authoritative_history_and_names_replacement(self):
        promoted = self._promote_accepted()
        superseded = transition_adr(
            self.root,
            adr_id="adr_decision_sidecar_transaction",
            status="superseded",
            update_entry_id="mse_update",
            expected_authoritative_decision="mse_12345678:d1",
            replacement_adr="adr_replacement",
            source="write-time",
            reason="A narrower concern replaces this one.",
            timestamp="2026-07-30T12:00:00",
        )
        self.assertTrue(superseded.ok, superseded.issues)
        record = parse_adr(promoted.path)
        self.assertEqual(record.current_status, "superseded")
        self.assertEqual(record.state.superseded_by, "adr_replacement")
        self.assertEqual(record.authoritative_decision, "mse_12345678:d1")

    def test_lineage_validation_requires_accepted_convergence_and_rejects_cycles_and_competing_heads(self):
        promoted = self._promote_accepted()
        record = parse_adr(promoted.path)
        branch_a = AdrEvent(
            "revision-proposed", "adre_branch_a", "2026-07-30T12:00:00", "write-time",
            "mse_brancha:d1", "mse_update", predecessors=(AdrPredecessor(
                "mse_12345678:d1", "link:mse_brancha:d1:evolves:mse_12345678:d1",
            ),), decision="Explore branch A.", why="It descends from the accepted root.",
        )
        branch_b = AdrEvent(
            "revision-proposed", "adre_branch_b", "2026-07-30T12:01:00", "write-time",
            "mse_branchb:d1", "mse_update", predecessors=(AdrPredecessor(
                "mse_12345678:d1", "link:mse_branchb:d1:evolves:mse_12345678:d1",
            ),), decision="Explore branch B.", why="It descends from the accepted root.",
        )
        converging = AdrEvent(
            "revision-proposed", "adre_converging", "2026-07-30T12:02:00", "write-time",
            "mse_converge:d1", "mse_update", predecessors=(
                AdrPredecessor("mse_brancha:d1", "link:mse_converge:d1:evolves:mse_brancha:d1"),
                AdrPredecessor("mse_branchb:d1", "link:mse_converge:d1:evolves:mse_branchb:d1"),
            ), decision="Converge both branches.", why="Their common root remains accepted.",
        )
        record.events.extend([branch_a, branch_b, converging, AdrEvent(
            "revision-accepted", "adre_converging_accept", "2026-07-30T12:03:00", "write-time",
            "mse_converge:d1", "mse_update", "mse_12345678:d1",
        )])
        self.assertEqual(validate_adr(record, self.root), [])
        self.assertEqual(record.authoritative_decision, "mse_converge:d1")

        divergent = copy.deepcopy(parse_adr(promoted.path))
        divergent.events.extend([
            replace(branch_a, predecessors=(AdrPredecessor(
                "mse_prior:d1", "link:mse_brancha:d1:evolves:mse_prior:d1",
            ),)),
            replace(branch_b, predecessors=(AdrPredecessor(
                "mse_prior:d1", "link:mse_branchb:d1:evolves:mse_prior:d1",
            ),)),
            converging,
            AdrEvent("revision-accepted", "adre_bad_convergence_accept", "2026-07-30T12:03:00", "write-time",
                     "mse_converge:d1", "mse_update", "mse_12345678:d1"),
        ])
        divergent_issues = validate_adr(divergent, self.root)
        self.assertTrue(any("does not descend from authoritative decision" in issue for issue in divergent_issues), divergent_issues)

        cycle = copy.deepcopy(parse_adr(promoted.path))
        cycle.events.append(AdrEvent(
            "revision-proposed", "adre_cycle", "2026-07-30T12:00:00", "write-time",
            "mse_current:d2", "mse_update", predecessors=(AdrPredecessor(
                "mse_current:d2", "link:mse_current:d2:evolves:mse_current:d2",
            ),), decision="Cycle.", why="It must be rejected.",
        ))
        cycle_issues = validate_adr(cycle, self.root)
        self.assertTrue(any("creates a lineage cycle" in issue for issue in cycle_issues), cycle_issues)

        competing = copy.deepcopy(parse_adr(promoted.path))
        competing.events.extend([
            AdrEvent("revision-proposed", "adre_stale_head", "2026-07-30T12:00:00", "write-time",
                     "mse_current:d2", "mse_update", decision="Compete.", why="Test stale head."),
            AdrEvent("revision-accepted", "adre_stale_head_accept", "2026-07-30T12:30:00", "write-time",
                     "mse_current:d2", "mse_update", None),
        ])
        competing_issues = validate_adr(competing, self.root)
        self.assertTrue(any("stale expected_authoritative_decision" in issue for issue in competing_issues), competing_issues)

    def test_review_matching_covers_all_adr_members_and_normalizes_single_decisions(self):
        accepted = self._promote_accepted("adr_accepted")
        historical = self._promote_accepted("adr_historical")
        revised = revise_adr(
            self.root, adr_id="adr_historical", decision_ref="mse_current:d2", decision="Historical revision.",
            why="Retain it as a review target.", evolution="It becomes the accepted successor.", update_entry_id="mse_update",
            source="write-time", predecessors=(AdrPredecessor("mse_12345678:d1", "link:mse_current:d2:evolves:mse_12345678:d1"),),
            timestamp="2026-07-30T12:00:00",
        )
        self.assertTrue(revised.ok, revised.issues)
        self.assertTrue(transition_adr(
            self.root, adr_id="adr_historical", status="accepted", decision_ref="mse_current:d2",
            update_entry_id="mse_update", expected_authoritative_decision="mse_12345678:d1", source="write-time",
            timestamp="2026-07-30T12:30:00",
        ).ok)
        pending = promote_decision(
            self.root, adr_id="adr_pending", source_entry_id="mse_current", source_decision="d1",
            title="Pending concern", topics=(), user_initials="JNL", agent_type="codex", source="write-time",
            timestamp="2026-07-30T10:00:00",
        )
        self.assertTrue(pending.ok, pending.issues)
        rejected = promote_decision(
            self.root, adr_id="adr_rejected", source_entry_id="mse_current", source_decision="d2",
            title="Rejected concern", topics=(), user_initials="JNL", agent_type="codex", source="write-time",
            timestamp="2026-07-30T10:00:00",
        )
        self.assertTrue(rejected.ok, rejected.issues)
        self.assertTrue(transition_adr(
            self.root, adr_id="adr_rejected", status="rejected", decision_ref="mse_current:d2",
            update_entry_id="mse_update", expected_previous_status="proposed", source="write-time",
            reason="Rejected proposal.", timestamp="2026-07-30T11:00:00",
        ).ok)
        predecessor = promote_decision(
            self.root, adr_id="adr_predecessor", source_entry_id="mse_current", source_decision="d2",
            title="Curated predecessor", topics=(), user_initials="JNL", agent_type="codex", source="write-time",
            direct_predecessors=(AdrPredecessor("mse_prior:d1", "link:mse_current:d2:evolves:mse_prior:d1"),),
            timestamp="2026-07-30T10:00:00",
        )
        self.assertTrue(predecessor.ok, predecessor.issues)
        targets = ("mse_12345678:d1", "mse_current:d2", "mse_current:d1", "mse_prior:d1")
        contexts = adr_review_context(self.root, targets)
        self.assertEqual({context["adr_id"] for context in contexts}, {
            "adr_accepted", "adr_historical", "adr_pending", "adr_rejected", "adr_predecessor",
        })
        self.assertEqual(canonical_decision_refs(self.root, "mse_12345678"), ("mse_12345678:d1",))
        historical_context = next(
            context for context in adr_review_context(self.root, ("mse_12345678:d1",))
            if context["adr_id"] == "adr_historical"
        )
        self.assertEqual(historical_context["matched_decisions"], ["mse_12345678:d1"])
        self.assertEqual(historical_context["authoritative_decision"], "mse_current:d2")
        gate = call_tool("memory_session_append", self._review_payload())
        self.assertFalse(gate["ok"])
        self.assertTrue(gate["review_required"])
        historical_gate_context = next(
            context for context in gate["matched_adrs"] if context["adr_id"] == "adr_historical"
        )
        self.assertEqual(historical_gate_context["matched_decisions"], ["mse_12345678:d1"])
        self.assertEqual(historical_gate_context["authoritative_decision"], "mse_current:d2")
        self.assertEqual(accepted.path.name, "adr_accepted.md")
        self.assertEqual(historical.path.name, "adr_historical.md")

    def test_related_entries_and_outside_lineage_lifecycle_links_do_not_trigger_review_gate(self):
        self._promote_accepted()
        payload = self._review_payload()
        payload["decisions"][0]["links"] = {"related_entries": ["mse_12345678"]}
        result = call_tool("memory_session_append", payload)
        self.assertTrue(result["ok"], result["issues"])
        self.assertNotIn("review_required", result)
        for index, kind in enumerate(("evolves", "replaces"), start=1):
            with self.subTest(kind=kind):
                outside = self._review_payload(
                    title=f"Outside lineage {kind}", timestamp=f"2026-07-30 12:1{index}"
                )
                outside["decisions"][0]["links"] = {kind: [dict({"ref": "mse_outside1", "why": "test fixture edge"}, **({"type": "builds-on"} if kind == "evolves" else {}))]}
                result = call_tool("memory_session_append", outside)
                self.assertTrue(result["ok"], result["issues"])
                self.assertNotIn("review_required", result)

    def test_receipts_bind_all_proposal_fields_workspace_and_adr_ledger(self):
        promoted = self._promote_accepted()
        payload = self._review_payload()
        gated = call_tool("memory_session_append", payload)
        receipt = gated["adr_review_receipt"]
        for field, replacement in (
            ("body", payload["body"].replace("New evidence.", "Different evidence.")),
            ("title", "Different title"),
            ("timestamp", "2026-07-30 12:01"),
        ):
            changed = copy.deepcopy(payload)
            changed[field] = replacement
            changed["adr_review_receipt"] = receipt
            changed["decisions"][0]["adrs"] = [self._no_change()]
            refused = call_tool("memory_session_append", changed)
            self.assertFalse(refused["ok"])
            self.assertFalse(refused["written"])
            self.assertIn("stale", "\n".join(refused["issues"]))

        with tempfile.TemporaryDirectory() as alternate_temp:
            alternate = Path(alternate_temp) / "complete-runtime"
            shutil.copytree(self.root, alternate)
            alternate_payload = copy.deepcopy(payload)
            alternate_payload["cwd"] = str(alternate)
            alternate_payload["adr_review_receipt"] = receipt
            alternate_payload["decisions"][0]["adrs"] = [self._no_change()]
            before_alternate = self._workspace_snapshot(alternate)
            refused = call_tool("memory_session_append", alternate_payload)
            self.assertFalse(refused["ok"])
            self.assertFalse(refused["written"])
            self.assertIn("adr_review_receipt is stale", "\n".join(refused["issues"]))
            self.assertEqual(self._workspace_snapshot(alternate), before_alternate)

        changed_link = copy.deepcopy(payload)
        changed_link["decisions"][0]["links"] = {"replaces": [{"ref": "mse_12345678", "why": "test fixture edge"}]}
        changed_link["adr_review_receipt"] = receipt
        changed_link["decisions"][0]["adrs"] = [self._no_change()]
        before_link = self._workspace_snapshot(self.root)
        refused_link = call_tool("memory_session_append", changed_link)
        self.assertFalse(refused_link["ok"])
        self.assertFalse(refused_link["written"])
        self.assertIn("stale", "\n".join(refused_link["issues"]))
        self.assertEqual(self._workspace_snapshot(self.root), before_link)

        revised = revise_adr(
            self.root, adr_id="adr_decision_sidecar_transaction", decision_ref="mse_current:d2",
            decision="Ledger changed.", why="Invalidate the review receipt.", evolution="It is pending.",
            update_entry_id="mse_update", source="write-time", predecessors=(AdrPredecessor(
                "mse_12345678:d1", "link:mse_current:d2:evolves:mse_12345678:d1",
            ),), timestamp="2026-07-30T12:00:00",
        )
        self.assertTrue(revised.ok, revised.issues)
        changed_ledger = copy.deepcopy(payload)
        changed_ledger["adr_review_receipt"] = receipt
        changed_ledger["decisions"][0]["adrs"] = [self._no_change()]
        before_ledger = self._workspace_snapshot(self.root)
        refused_ledger = call_tool("memory_session_append", changed_ledger)
        self.assertFalse(refused_ledger["ok"])
        self.assertFalse(refused_ledger["written"])
        self.assertIn("stale", "\n".join(refused_ledger["issues"]))
        self.assertEqual(self._workspace_snapshot(self.root), before_ledger)
        self.assertTrue(promoted.path.exists())

    def test_review_outcomes_must_be_exact_unique_and_well_formed(self):
        self._promote_accepted()
        for label, actions, expected in (
            ("missing", [], "missing ADR review outcome"),
            ("extra", [self._no_change(), self._no_change("adr_extra")], "unexpected ADR review outcome"),
            ("duplicate", [self._no_change(), self._no_change()], "duplicated ADR review outcome"),
            ("malformed", [self._no_change(reason="")], "requires a non-empty reason"),
        ):
            with self.subTest(label=label):
                payload = self._review_payload()
                gated = call_tool("memory_session_append", payload)
                payload["adr_review_receipt"] = gated["adr_review_receipt"]
                payload["decisions"][0]["adrs"] = actions
                refused = call_tool("memory_session_append", payload)
                self.assertFalse(refused["ok"])
                self.assertIn(expected, "\n".join(refused["issues"]))

    def test_no_change_is_idempotent_only_during_recovery_and_receipt_replay_is_noop(self):
        promoted = self._promote_accepted()
        payload = self._review_payload()
        gated = call_tool("memory_session_append", payload)
        payload["adr_review_receipt"] = gated["adr_review_receipt"]
        payload["decisions"][0]["adrs"] = [self._no_change()]
        before_membership = adr_membership(parse_adr(promoted.path))
        written = call_tool("memory_session_append", payload)
        self.assertTrue(written["ok"], written["issues"])
        record = parse_adr(promoted.path)
        self.assertEqual(record.authoritative_decision, "mse_12345678:d1")
        self.assertEqual(record.events[-1].kind, "reviewed-no-change")
        self.assertEqual(adr_membership(record), before_membership)
        before = self._workspace_snapshot(self.root)
        replay = call_tool("memory_session_append", payload)
        self.assertFalse(replay["ok"])
        self.assertFalse(replay["written"])
        self.assertIn("stale", "\n".join(replay["issues"]))
        self.assertEqual(self._workspace_snapshot(self.root), before)

    def test_interrupted_adr_transaction_recovers_parent_first_once(self):
        promoted = self._promote_accepted()
        payload = self._review_payload()
        gated = call_tool("memory_session_append", payload)
        payload["adr_review_receipt"] = gated["adr_review_receipt"]
        payload["decisions"][0]["adrs"] = [self._no_change()]

        from memory_seed import core
        original_write = core.write_text_file

        def interrupt_adr_write(path, text):
            if Path(path) == promoted.path:
                raise OSError("simulated ADR publication interruption")
            return original_write(path, text)

        with patch("memory_seed.core.write_text_file", side_effect=interrupt_adr_write):
            with self.assertRaisesRegex(OSError, "simulated ADR publication interruption"):
                call_tool("memory_session_append", payload)
        session_path = self.root / ".memory-seed" / "sessions" / "2026-07" / "2026-07-30.md"
        self.assertIn("Review lineage", session_path.read_text(encoding="utf-8"))
        self.assertEqual(parse_adr(promoted.path).events[-1].kind, "revision-accepted")
        recovered = call_tool("memory_session_append", payload)
        self.assertTrue(recovered["ok"], recovered["issues"])
        events = parse_adr(promoted.path).events
        self.assertEqual([event.kind for event in events].count("reviewed-no-change"), 1)

    def test_adr_reconciliation_is_idempotent_orders_events_and_refuses_conflicts(self):
        promoted = self._promote_accepted()
        base = parse_adr(promoted.path)
        duplicate, duplicate_issues = reconcile_adr_records(base, copy.deepcopy(base))
        self.assertEqual(duplicate_issues, [])
        self.assertEqual(duplicate.events, base.events)

        branch_a = AdrEvent(
            "revision-proposed", "adre_merge_branch_a", "2026-07-30T12:00:00", "write-time",
            "mse_brancha:d1", "mse_update", predecessors=(AdrPredecessor(
                "mse_12345678:d1", "link:mse_brancha:d1:evolves:mse_12345678:d1",
            ),), decision="Branch A proposal.", why="It is independent branch-local work.",
        )
        branch_b = AdrEvent(
            "revision-proposed", "adre_merge_branch_b", "2026-07-30T12:01:00", "write-time",
            "mse_branchb:d1", "mse_update", predecessors=(AdrPredecessor(
                "mse_12345678:d1", "link:mse_branchb:d1:evolves:mse_12345678:d1",
            ),), decision="Branch B proposal.", why="It is independent branch-local work.",
        )
        left = copy.deepcopy(base)
        left.events.append(branch_a)
        right = copy.deepcopy(base)
        right.events.append(branch_b)
        self.assertEqual(validate_adr(left, self.root), [])
        self.assertEqual(validate_adr(right, self.root), [])
        merged, issues = reconcile_adr_records(left, right)
        self.assertEqual(issues, [])
        self.assertEqual([event.timestamp for event in merged.events], sorted(event.timestamp for event in merged.events))
        self.assertEqual({event.event_id for event in merged.events}, {
            *(event.event_id for event in base.events), "adre_merge_branch_a", "adre_merge_branch_b",
        })
        self.assertEqual(merged.authoritative_decision, "mse_12345678:d1")
        self.assertEqual(merged.state.pending_decisions, ("mse_brancha:d1", "mse_branchb:d1"))
        current_view = render_adr(merged)
        self.assertIn("Status: **Accepted**", current_view)
        self.assertIn("Authoritative decision: `mse_12345678:d1`", current_view)
        self.assertIn("### Decision\n\nUse the composite writer.", current_view)
        self.assertIn("### Why\n\nIt preserves a single validation boundary.", current_view)
        self.assertIn("### How it evolved\n\nThis is the first revision of this architectural concern.", current_view)
        replayed = parse_adr_text(render_adr(merged))
        self.assertEqual(replayed.authoritative_decision, "mse_12345678:d1")
        self.assertEqual(render_adr(replayed), render_adr(merged))

        divergent = copy.deepcopy(base)
        divergent.events[0] = replace(divergent.events[0], why="Different same-id content.")
        _, divergent_issues = reconcile_adr_records(base, divergent)
        self.assertTrue(any("diverges across branches" in issue for issue in divergent_issues), divergent_issues)

        left_accepted = copy.deepcopy(base)
        left_accepted.events.extend([branch_a, AdrEvent(
            "revision-accepted", "adre_merge_branch_a_accept", "2026-07-30T12:02:00", "write-time",
            "mse_brancha:d1", "mse_update", "mse_12345678:d1",
        )])
        right_accepted = copy.deepcopy(base)
        right_accepted.events.extend([branch_b, AdrEvent(
            "revision-accepted", "adre_merge_branch_b_accept", "2026-07-30T12:03:00", "write-time",
            "mse_branchb:d1", "mse_update", "mse_12345678:d1",
        )])
        self.assertEqual(validate_adr(left_accepted, self.root), [])
        self.assertEqual(validate_adr(right_accepted, self.root), [])
        _, competing_issues = reconcile_adr_records(left_accepted, right_accepted)
        self.assertTrue(any("competing acceptance" in issue for issue in competing_issues), competing_issues)


if __name__ == "__main__":
    unittest.main()
