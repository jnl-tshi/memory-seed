"""Contract extension (2026-08-06): constitution bindings in the ledger, founding sources.

Two additive, omit-empty fields on `AdrEvent` - `constitution_refs` and
`founding_source`/`founding_quote` - so that (a) an ADR references the Constitution directly
(JNL: no separate bindings sidecar) and (b) an ADR can be founded from a control-file line or by
bootstrap on a project that has no session corpus yet.

The invariant these tests exist to hold: **every ADR written before the fields existed stays
byte-canonical.** The three live ADRs are additionally sha256-pinned by the codex fixtures, so a
render change here breaks two suites, not one.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.adr import (
    add_context,
    adr_membership,
    revise_adr,
    ConstitutionRef,
    check_adrs,
    parse_adr,
    parse_adr_text,
    promote_decision,
    render_adr,
    transition_adr,
    validate_adr,
)
from memory_seed.core import read_text_file

REPO = Path(__file__).resolve().parents[1]
LIVE_ADRS = sorted((REPO / ".memory-seed" / "decisions").glob("adr_*.md"))
# The three pre-extension records the codex fixtures pin by sha256. Every OTHER live ADR may (and
# after the 2026-08-06 campaign does) carry the extension fields; these three must not, because
# any change to their bytes is "frozen source drift" to test_context_derivation_*.
PINNED_ADRS = sorted(
    REPO / ".memory-seed" / "decisions" / f"{name}.md"
    for name in (
        "adr_mcp_decision_envelope_review",
        "adr_parent_first_sidecar_transaction",
        "adr_session_decision_authority",
    )
)

CONSTITUTION = """# Constitution

## 2. Invariants

<!-- constitution-ref: constitution:v1#append-only -->
1. The past is append-only.

<!-- constitution-ref: constitution:v1#authority -->
2. Files are authority for now; memory for why.
"""

ENTRY = """## 2026-08-06 10:00 - Seed entry

```yaml
entry_id: mse_extension0000001
user_initials: JNL
agent_type: claude
project_path: .
subproject_path: null
```

### Decisions

#### D1 - A decision to promote

- D: Decide the thing.
- R: Because measured.
"""


class ProjectFixture(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="memory-seed-adrext-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        sessions = root / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True)
        (sessions / "2026-08-06.md").write_text(ENTRY, encoding="utf-8")
        (root / "docs").mkdir()
        (root / "docs" / "CONSTITUTION.md").write_text(CONSTITUTION, encoding="utf-8")
        (root / ".memory-seed" / "topics.yaml").write_text(
            "schema_version: 2\ntopics:\n  - slug: retrieval\n    description: Retrieval.\n    axis: area\n",
            encoding="utf-8",
        )
        return root


class PinnedAdrByteCanonicalTests(unittest.TestCase):
    """The reason the fields are omit-empty."""

    def test_live_adrs_round_trip_byte_identical(self):
        """Every ADR in the live corpus renders back to its own bytes - extended or not."""
        self.assertGreaterEqual(len(LIVE_ADRS), 3, "expected at least the three pinned ADRs")
        for path in LIVE_ADRS:
            source = read_text_file(path)
            record = parse_adr(path)
            self.assertEqual(render_adr(record), source, f"{path.name} no longer byte-canonical")

    def test_pinned_adrs_have_no_extension_fields(self):
        """The omit-empty guarantee, checked where it actually binds."""
        for path in PINNED_ADRS:
            record = parse_adr(path)
            for event in record.events:
                self.assertEqual(event.constitution_refs, (), path.name)
                self.assertIsNone(event.founding_source, path.name)


class ConstitutionBindingTests(ProjectFixture):
    def test_binding_resolves_against_anchor(self):
        root = self.make_project()
        result = promote_decision(
            root, adr_id="adr_bound", source_entry_id="mse_extension0000001",
            source_decision="d1", title="Bound concern", topics=("retrieval",),
            user_initials="JNL", agent_type="claude", source="derived",
            decision="D.", why="W.",
            constitution_refs=(ConstitutionRef("constitution:v1#append-only", "governing"),),
            timestamp="2026-08-06T10:05:00Z",
        )
        self.assertTrue(result.ok, result.issues)
        record = parse_adr(result.path)
        self.assertEqual(record.events[0].constitution_refs[0].ref, "constitution:v1#append-only")
        # The binding survives the round trip and appears in the Current view.
        rendered = read_text_file(result.path)
        self.assertIn("### Constitution", rendered)
        self.assertIn("`constitution:v1#append-only` (governing)", rendered)
        self.assertEqual(render_adr(parse_adr_text(rendered)), rendered)

    def test_unresolvable_or_malformed_bindings_are_refused(self):
        root = self.make_project()
        for ref, role, expect in (
            ("constitution:v1#nonexistent", "governing", "does not resolve"),
            ("Invariant #2", "governing", "must match"),
            ("constitution:v1#append-only", "decorative", "role must be"),
        ):
            result = promote_decision(
                root, adr_id="adr_bad", source_entry_id="mse_extension0000001",
                source_decision="d1", title="Bad binding", topics=(),
                user_initials="JNL", agent_type="claude", source="derived",
                decision="D.", why="W.",
                constitution_refs=(ConstitutionRef(ref, role),),
                timestamp="2026-08-06T10:05:00Z", dry_run=True,
            )
            self.assertFalse(result.ok)
            self.assertTrue(any(expect in issue for issue in result.issues), result.issues)


class FoundingSourceTests(ProjectFixture):
    def test_founding_promotion_and_acceptance_round_trip(self):
        root = self.make_project()
        result = promote_decision(
            root, adr_id="adr_founded", title="Founded concern", topics=(),
            user_initials="JNL", agent_type="claude", source="derived",
            decision="Runtime discovery walks upward to the nearest runtime.",
            why="Lifted from the index during the S1 campaign.",
            founding_source=".memory-seed/index.md#L120",
            founding_quote="Runtime discovery walks upward from `cwd`",
            constitution_refs=(ConstitutionRef("constitution:v1#authority", "governing"),),
            timestamp="2026-08-06T10:06:00Z",
        )
        self.assertTrue(result.ok, result.issues)
        self.assertEqual(result.current_status, "proposed")
        accepted = transition_adr(
            root, adr_id="adr_founded", status="accepted",
            update_entry_id="mse_extension0000001", source="derived",
            timestamp="2026-08-06T10:07:00Z",
        )
        self.assertTrue(accepted.ok, accepted.issues)
        self.assertEqual(accepted.current_status, "accepted")
        self.assertEqual(accepted.authoritative_decision, "founding:.memory-seed/index.md#L120")
        record = parse_adr(accepted.path)
        self.assertEqual(validate_adr(record, root), [])
        self.assertEqual(render_adr(record), read_text_file(accepted.path))

    def test_bootstrap_founding_needs_no_session_corpus(self):
        """S3's requirement: a fresh project has no entries at all."""
        root = Path(tempfile.mkdtemp(prefix="memory-seed-adrboot-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        (root / ".memory-seed" / "sessions").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / "docs" / "CONSTITUTION.md").write_text(CONSTITUTION, encoding="utf-8")
        result = promote_decision(
            root, adr_id="adr_boot", title="Founding frame", topics=(),
            user_initials="JNL", agent_type="claude", source="derived",
            decision="D.", why="W.",
            founding_source="bootstrap", founding_quote="Project inspection, 2026-08-06.",
            timestamp="2026-08-06T10:08:00Z",
        )
        self.assertTrue(result.ok, result.issues)

    def test_founding_guards(self):
        root = self.make_project()
        base = dict(
            title="Guarded", topics=(), user_initials="JNL", agent_type="claude",
            source="derived", decision="D.", why="W.",
            timestamp="2026-08-06T10:09:00Z", dry_run=True,
        )
        both = promote_decision(
            root, adr_id="adr_g1", source_entry_id="mse_extension0000001",
            source_decision="d1", founding_source="bootstrap", founding_quote="q", **base,
        )
        self.assertFalse(both.ok)
        no_quote = promote_decision(root, adr_id="adr_g2", founding_source="bootstrap", **base)
        self.assertFalse(no_quote.ok)
        self.assertTrue(any("founding_quote" in issue for issue in no_quote.issues), no_quote.issues)
        bad_source = promote_decision(
            root, adr_id="adr_g3", founding_source="somewhere vague", founding_quote="q", **base,
        )
        self.assertFalse(bad_source.ok)
        neither = promote_decision(root, adr_id="adr_g4", **base)
        self.assertFalse(neither.ok)

    def test_a_real_decision_supersedes_a_founding_head(self):
        """Convergence: a founded ADR must be able to accept a real decision as its head.

        No real decision can descend from a `founding:` placeholder, so requiring lineage descent
        would strand every founded ADR at its founding head forever.
        """
        root = self.make_project()
        promote_decision(
            root, adr_id="adr_converge", title="Converging concern", topics=(),
            user_initials="JNL", agent_type="claude", source="derived",
            decision="D.", why="W.",
            founding_source=".memory-seed/index.md#L120", founding_quote="Runtime discovery",
            timestamp="2026-08-07T01:00:00Z",
        )
        accepted = transition_adr(
            root, adr_id="adr_converge", status="accepted", update_entry_id=None,
            source="derived", timestamp="2026-08-07T01:01:00Z",
        )
        self.assertTrue(accepted.ok, accepted.issues)
        revised = revise_adr(
            root, adr_id="adr_converge", decision_ref="mse_extension0000001:d1",
            decision="Now anchored on a real decision.", why="A session decision landed.",
            evolution="Converged from the control-file founding onto its session decision.",
            update_entry_id="mse_extension0000001", source="derived", predecessors=(),
            timestamp="2026-08-07T01:02:00Z",
        )
        self.assertTrue(revised.ok, revised.issues)
        head = transition_adr(
            root, adr_id="adr_converge", status="accepted",
            decision_ref="mse_extension0000001:d1",
            update_entry_id="mse_extension0000001", source="derived",
            expected_authoritative_decision="founding:.memory-seed/index.md#L120",
            timestamp="2026-08-07T01:03:00Z",
        )
        self.assertTrue(head.ok, head.issues)
        self.assertEqual(head.authoritative_decision, "mse_extension0000001:d1")

    def test_descent_is_still_required_between_two_real_decisions(self):
        """The founding carve-out must not become a general bypass."""
        root = self.make_project()
        (root / ".memory-seed" / "sessions" / "2026-08-06.md").write_text(
            ENTRY + "\n#### D2 - An unrelated decision\n\n- D: Elsewhere.\n- R: Unrelated.\n",
            encoding="utf-8",
        )
        promote_decision(
            root, adr_id="adr_strict", source_entry_id="mse_extension0000001",
            source_decision="d1", title="Strict", topics=(), user_initials="JNL",
            agent_type="claude", source="derived", decision="D.", why="W.",
            timestamp="2026-08-07T01:00:00Z",
        )
        transition_adr(
            root, adr_id="adr_strict", status="accepted",
            update_entry_id="mse_extension0000001", source="derived",
            timestamp="2026-08-07T01:01:00Z",
        )
        revise_adr(
            root, adr_id="adr_strict", decision_ref="mse_extension0000001:d2",
            decision="Unlinked successor.", why="No lineage asserted.", evolution="None.",
            update_entry_id="mse_extension0000001", source="derived", predecessors=(),
            timestamp="2026-08-07T01:02:00Z",
        )
        blocked = transition_adr(
            root, adr_id="adr_strict", status="accepted",
            decision_ref="mse_extension0000001:d2",
            update_entry_id="mse_extension0000001", source="derived",
            expected_authoritative_decision="mse_extension0000001:d1",
            timestamp="2026-08-07T01:03:00Z",
        )
        self.assertFalse(blocked.ok)
        self.assertTrue(any("does not descend" in i for i in blocked.issues), blocked.issues)

    def test_corpus_check_stays_green_with_extended_records(self):
        root = self.make_project()
        promote_decision(
            root, adr_id="adr_founded", title="Founded", topics=(),
            user_initials="JNL", agent_type="claude", source="derived",
            decision="D.", why="W.",
            founding_source=".memory-seed/index.md#L120", founding_quote="Runtime discovery",
            timestamp="2026-08-06T10:06:00Z",
        )
        ok, issues = check_adrs(root)
        self.assertTrue(ok, issues)


if __name__ == "__main__":
    unittest.main()


class SoftContextTests(ProjectFixture):
    """`context-added`: attach evidence without moving a head or a status."""

    def _founded(self, root, adr_id="adr_ctx", status=None):
        promote_decision(
            root, adr_id=adr_id, title="Concern", topics=(), user_initials="JNL",
            agent_type="claude", source="derived", decision="D.", why="W.",
            founding_source=".memory-seed/index.md#L1", founding_quote="A founding line quote.",
            timestamp="2026-08-07T04:00:00Z",
        )
        if status:
            transition_adr(
                root, adr_id=adr_id, status=status, update_entry_id=None, source="derived",
                reason="Recorded as decided-against.", timestamp="2026-08-07T04:01:00Z",
            )

    def test_context_leaves_head_and_status_untouched(self):
        root = self.make_project()
        self._founded(root)
        before = parse_adr(root / ".memory-seed" / "decisions" / "adr_ctx.md")
        result = add_context(
            root, adr_id="adr_ctx", supporting_decisions=("mse_extension0000001:d1",),
            reason="Informs the concern without moving it.",
            update_entry_id="mse_extension0000001", source="derived",
            timestamp="2026-08-07T04:02:00Z",
        )
        self.assertTrue(result.ok, result.issues)
        after = parse_adr(result.path)
        self.assertEqual(after.current_status, before.current_status)
        self.assertEqual(after.authoritative_decision, before.authoritative_decision)
        # The whole point: soft refs stay OUT of membership, so they never arm the review gate.
        self.assertNotIn("mse_extension0000001:d1", adr_membership(after))
        self.assertEqual(render_adr(after), read_text_file(result.path))

    def test_context_can_attach_to_a_rejected_adr(self):
        root = self.make_project()
        self._founded(root, adr_id="adr_rej", status="rejected")
        result = add_context(
            root, adr_id="adr_rej", supporting_decisions=("mse_extension0000001:d1",),
            reason="Evidence for a decision we declined.",
            update_entry_id="mse_extension0000001", source="derived",
            timestamp="2026-08-07T04:03:00Z",
        )
        self.assertTrue(result.ok, result.issues)
        self.assertEqual(parse_adr(result.path).current_status, "rejected")

    def test_context_refuses_unresolvable_or_empty_evidence(self):
        root = self.make_project()
        self._founded(root, adr_id="adr_bad2")
        missing = add_context(
            root, adr_id="adr_bad2", supporting_decisions=("mse_nope00000000000:d1",),
            reason="r", update_entry_id="mse_extension0000001", source="derived",
            timestamp="2026-08-07T04:04:00Z", dry_run=True,
        )
        self.assertFalse(missing.ok)
        empty = add_context(
            root, adr_id="adr_bad2", supporting_decisions=(), reason="r",
            update_entry_id="mse_extension0000001", source="derived",
            timestamp="2026-08-07T04:05:00Z", dry_run=True,
        )
        self.assertFalse(empty.ok)
        no_reason = add_context(
            root, adr_id="adr_bad2", supporting_decisions=("mse_extension0000001:d1",), reason="",
            update_entry_id="mse_extension0000001", source="derived",
            timestamp="2026-08-07T04:06:00Z", dry_run=True,
        )
        self.assertFalse(no_reason.ok)
