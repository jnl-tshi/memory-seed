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

import contextlib
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.adr import (
    frontmatter_issues,
    unknown_event_kinds,
    reconcile_adr_records,
    replay_adr,
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
from memory_seed.cli import main as cli_main

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


class FoundingSourceCliTests(ProjectFixture):
    def run_cli(self, root: Path, arguments: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(root)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = cli_main(arguments)
        finally:
            os.chdir(previous)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_cli_promotes_founding_source_with_bindings_and_support(self):
        root = self.make_project()
        code, _stdout, stderr = self.run_cli(
            root,
            [
                "adr", "promote", "--adr-id", "adr_cli_founded",
                "--founding-source", "bootstrap",
                "--founding-quote", "Project inspection established the boundary.",
                "--title", "CLI founding source", "--topics", "retrieval",
                "--user-initials", "JNL", "--agent-type", "codex",
                "--source", "derived", "--summary-decision", "Keep the boundary.",
                "--why", "Bootstrap evidence requires a durable home.",
                "--constitution-ref", "constitution:v1#authority=governing",
                "--supporting-decision", "mse_extension0000001:d1",
                "--timestamp", "2026-08-06T10:10:00Z",
            ],
        )
        self.assertEqual(code, 0, stderr)
        record = parse_adr(root / ".memory-seed" / "decisions" / "adr_cli_founded.md")
        event = record.events[0]
        self.assertEqual(event.founding_source, "bootstrap")
        self.assertEqual(event.supporting_decisions, ("mse_extension0000001:d1",))
        self.assertEqual(event.constitution_refs[0].role, "governing")

    def test_cli_keeps_session_decision_source_compatible(self):
        root = self.make_project()
        code, _stdout, stderr = self.run_cli(
            root,
            [
                "adr", "promote", "--adr-id", "adr_cli_session",
                "--entry-id", "mse_extension0000001", "--decision", "d1",
                "--title", "CLI session source", "--user-initials", "JNL",
                "--agent-type", "codex", "--source", "derived",
                "--timestamp", "2026-08-06T10:11:00Z",
            ],
        )
        self.assertEqual(code, 0, stderr)
        record = parse_adr(root / ".memory-seed" / "decisions" / "adr_cli_session.md")
        self.assertEqual(record.events[0].decision_ref, "mse_extension0000001:d1")

    def test_cli_rejects_malformed_constitution_binding(self):
        root = self.make_project()
        code, _stdout, stderr = self.run_cli(
            root,
            [
                "adr", "promote", "--adr-id", "adr_cli_bad",
                "--founding-source", "bootstrap", "--founding-quote", "Evidence.",
                "--title", "Bad binding", "--user-initials", "JNL",
                "--agent-type", "codex", "--source", "derived",
                "--constitution-ref", "constitution:v1#authority",
            ],
        )
        self.assertEqual(code, 1)
        self.assertIn("--constitution-ref must be ref=role", stderr)


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


class ReconcileFoundingTests(ProjectFixture):
    """The fuse must accept a branch that appends events to a FOUNDED ADR.

    Regression: `reconcile_adr_records` keyed its replay on `decision_ref`, which a founding
    revision does not have - so the founding revision never entered `states`, its acceptance read
    as a transition against a non-pending revision, and every later acceptance read as competing.
    Every branch touching a founded ADR was unmergeable.
    """

    def _founded_then_revised(self, root):
        promote_decision(
            root, adr_id="adr_rec", title="Concern", topics=(), user_initials="JNL",
            agent_type="claude", source="derived", decision="D.", why="W.",
            founding_source=".memory-seed/index.md#L1", founding_quote="A founding line quote.",
            timestamp="2026-08-07T06:00:00Z",
        )
        transition_adr(
            root, adr_id="adr_rec", status="accepted", update_entry_id=None, source="derived",
            timestamp="2026-08-07T06:01:00Z",
        )
        base = parse_adr(root / ".memory-seed" / "decisions" / "adr_rec.md")
        revise_adr(
            root, adr_id="adr_rec", decision_ref="mse_extension0000001:d1",
            decision="Now anchored on a real decision.", why="A session decision landed.",
            evolution="Converged off the founding placeholder.",
            update_entry_id="mse_extension0000001", source="derived", predecessors=(),
            timestamp="2026-08-07T06:02:00Z",
        )
        transition_adr(
            root, adr_id="adr_rec", status="accepted", decision_ref="mse_extension0000001:d1",
            update_entry_id="mse_extension0000001", source="derived",
            expected_authoritative_decision=".memory-seed/index.md#L1".join(("founding:", "")),
            timestamp="2026-08-07T06:03:00Z",
        )
        return base, parse_adr(root / ".memory-seed" / "decisions" / "adr_rec.md")

    def test_appending_to_a_founded_adr_reconciles(self):
        root = self.make_project()
        base, incoming = self._founded_then_revised(root)
        merged, issues = reconcile_adr_records(base, incoming)
        self.assertEqual(issues, [])
        self.assertIsNotNone(merged)
        self.assertEqual(replay_adr(merged).authoritative_decision, "mse_extension0000001:d1")

    def test_reconcile_is_idempotent_for_a_founded_adr(self):
        root = self.make_project()
        _, incoming = self._founded_then_revised(root)
        merged, issues = reconcile_adr_records(incoming, incoming)
        self.assertEqual(issues, [])
        self.assertEqual(len(merged.events), len(incoming.events))


class UnknownEventKindGuardTests(unittest.TestCase):
    """A newer ledger must read as 'newer', not as 'corrupt'."""

    def test_detects_kinds_this_build_cannot_parse(self):
        text = (
            "## Event ledger\n\n"
            "### revision-proposed - 2026-08-07T01:00:00Z\n\n"
            "### some-future-kind - 2026-08-07T02:00:00Z\n\n"
            "### another-new-kind - 2026-08-07T03:00:00Z\n"
        )
        self.assertEqual(
            unknown_event_kinds(text), ("another-new-kind", "some-future-kind")
        )

    def test_known_kinds_and_current_view_headings_are_not_flagged(self):
        text = read_text_file(PINNED_ADRS[0])
        self.assertEqual(unknown_event_kinds(text), ())
        # Current-view sections are capitalised and carry no " - <stamp>", so they must not match.
        self.assertEqual(
            unknown_event_kinds("### Decision\n\n### Why\n\n### How it evolved\n\n### Constitution\n"),
            (),
        )

    def test_every_live_adr_parses_under_this_build(self):
        for path in LIVE_ADRS:
            self.assertEqual(unknown_event_kinds(read_text_file(path)), (), path.name)


class FrontmatterLintTests(ProjectFixture):
    """A title containing ': ' is valid to our regex reader and invalid to every YAML parser.

    Five ADRs sat in the corpus that way until the Trace UI, which parses properly, failed on them.
    """

    def test_a_risky_title_is_quoted_on_write_and_round_trips(self):
        root = self.make_project()
        title = "MCP integration: placement, upsert, and a gated surface"
        result = promote_decision(
            root, adr_id="adr_colon", source_entry_id="mse_extension0000001",
            source_decision="d1", title=title, topics=(), user_initials="JNL",
            agent_type="claude", source="derived", decision="D.", why="W.",
            timestamp="2026-08-08T01:00:00Z",
        )
        self.assertTrue(result.ok, result.issues)
        rendered = read_text_file(result.path)
        self.assertIn(f'title: "{title}"', rendered)
        self.assertEqual(parse_adr(result.path).title, title)      # quotes stripped on read
        self.assertEqual(render_adr(parse_adr(result.path)), rendered)  # byte-stable
        self.assertEqual(frontmatter_issues(rendered), [])

    def test_titles_that_need_no_quoting_stay_bare(self):
        """The reason the corpus written before this fix is byte-unchanged."""
        root = self.make_project()
        result = promote_decision(
            root, adr_id="adr_plain", source_entry_id="mse_extension0000001",
            source_decision="d1", title="Parent-first recoverable sidecar transaction",
            topics=(), user_initials="JNL", agent_type="claude", source="derived",
            decision="D.", why="W.", timestamp="2026-08-08T01:01:00Z",
        )
        self.assertIn("title: Parent-first recoverable sidecar transaction\n", read_text_file(result.path))

    def test_the_linter_names_the_cause(self):
        for raw, expect in (
            ("---\ntitle: A: B\n---\n", "nested mapping"),
            ("---\ntitle: trailing:\n---\n", "mapping key"),
            ("---\ntitle: has # a comment\n---\n", "comment"),
            ("---\ntitle: -leading\n---\n", "indicator"),
            ("---\ntitle: a\ntitle: b\n---\n", "more than once"),
        ):
            found = frontmatter_issues(raw)
            self.assertTrue(found, raw)
            self.assertTrue(any(expect in i for i in found), (raw, found))

    def test_every_live_adr_passes_the_linter(self):
        for path in LIVE_ADRS:
            self.assertEqual(frontmatter_issues(read_text_file(path)), [], path.name)


class AwaitingReviewViewTests(ProjectFixture):
    """The summary must show revisions waiting, or two branches can update an ADR invisibly."""

    def test_two_branches_proposing_both_appear_in_the_current_view(self):
        import copy
        from memory_seed.adr import AdrEvent, _event_id

        root = self.make_project()
        (root / ".memory-seed" / "sessions" / "2026-08-06.md").write_text(
            ENTRY + "\n#### D2 - A second decision\n\n- D: Elsewhere.\n- R: Because.\n",
            encoding="utf-8",
        )
        promote_decision(
            root, adr_id="adr_two_branches", title="Concern", topics=(), user_initials="JNL",
            agent_type="claude", source="derived", decision="Founding position.", why="W.",
            founding_source=".memory-seed/index.md#L1", founding_quote="A founding line.",
            timestamp="2026-08-08T10:00:00Z",
        )
        transition_adr(
            root, adr_id="adr_two_branches", status="accepted", update_entry_id=None,
            source="derived", timestamp="2026-08-08T10:01:00Z",
        )
        base = parse_adr(root / ".memory-seed" / "decisions" / "adr_two_branches.md")

        def branch(ref, stamp, decision):
            record = copy.deepcopy(base)
            record.events.append(AdrEvent(
                "revision-proposed", _event_id("t", ref, stamp), stamp, "derived", ref,
                "mse_extension0000001", decision=decision, why="W.", evolution="E.",
            ))
            return record

        left = branch("mse_extension0000001:d1", "2026-08-08T11:00:00Z", "Branch A position.")
        right = branch("mse_extension0000001:d2", "2026-08-08T11:05:00Z", "Branch B position.")
        merged, issues = reconcile_adr_records(left, right)
        self.assertEqual(issues, [])

        view = render_adr(merged).split("## Event ledger")[0]
        # The head is unchanged - neither branch was accepted - but BOTH are visible as waiting.
        self.assertIn("Authoritative decision: `founding:.memory-seed/index.md#L1`", view)
        self.assertIn("### Awaiting review", view)
        self.assertIn("mse_extension0000001:d1", view)
        self.assertIn("mse_extension0000001:d2", view)
        self.assertIn("Branch A position.", view)
        self.assertIn("Branch B position.", view)

    def test_the_section_is_omitted_when_the_only_pending_revision_is_the_one_displayed(self):
        """Why the whole live corpus renders byte-identically after this change."""
        root = self.make_project()
        result = promote_decision(
            root, adr_id="adr_single", source_entry_id="mse_extension0000001",
            source_decision="d1", title="Single", topics=(), user_initials="JNL",
            agent_type="claude", source="derived", decision="D.", why="W.",
            timestamp="2026-08-08T10:00:00Z",
        )
        self.assertTrue(result.ok, result.issues)
        self.assertNotIn("### Awaiting review", read_text_file(result.path))

    def test_every_live_adr_is_unchanged_by_this_view(self):
        for path in LIVE_ADRS:
            self.assertEqual(render_adr(parse_adr(path)), read_text_file(path), path.name)


class SingleReplayTests(unittest.TestCase):
    """The three callers of the replay rules must agree, because history says they drift.

    `replay_adr`, `validate_adr` and `reconcile_adr_records` each kept their own copy of the ADR
    state machine. The divergence bit twice with the same signature: a rule changed in one copy,
    the checks that run it went green, and the copy nobody remembered refused the work later. The
    founding extension missed the reconciler; so did the 2026-08-08 re-proposal relaxation, which
    is how `adr check` passed 30 ADRs that `session merge-branch` then refused all at once.

    They now share `_replay_step`. This asserts the agreement over the live corpus rather than
    trusting a comment to hold - the comment was there both times, and correctly predicted its own
    recurrence, which is what made the shared copy worth the churn.
    """

    def test_every_live_adr_validates_reconciles_and_replays_consistently(self):
        import copy

        for path in LIVE_ADRS:
            record = parse_adr(path)
            self.assertEqual(validate_adr(record, REPO), [], path.name)
            # Reconciling a record with itself is the merge the fuse performs when one side moved;
            # it must reach the same head the validator and the replay agree on.
            merged, issues = reconcile_adr_records(copy.deepcopy(record), copy.deepcopy(record))
            self.assertEqual(issues, [], path.name)
            self.assertIsNotNone(merged, path.name)
            self.assertEqual(
                replay_adr(merged).authoritative_decision,
                replay_adr(record).authoritative_decision,
                path.name,
            )


class StaleAnchorTests(ProjectFixture):
    """An ADR anchored behind its own live chain is stale, and `links check` says so.

    The rule: a summary synthesises every live chain member, so when the most recent authoritative
    decision that evolves the concern shifts, the summary owes a regeneration. Without this check
    that condition is invisible - the record simply keeps stating an older position, and the only
    way to notice is for a reader to compare the head against the chain by hand.

    Warning, never a gate: the live corpus had two ADRs in this state the moment the check landed,
    and a rule that reddens existing records on its own commit cannot land.
    """

    def test_the_live_corpus_reports_only_genuinely_stale_anchors(self):
        from memory_seed.core import stale_adr_anchors

        stale = {adr_id for adr_id, _head, _newest in stale_adr_anchors(REPO)}
        heads = {}
        for path in LIVE_ADRS:
            record = parse_adr(path)
            heads[record.adr_id] = replay_adr(record).authoritative_decision or ""
        for adr_id in stale:
            # Never flags a founding placeholder - it has no position in the chain to fall behind.
            self.assertFalse(heads[adr_id].startswith("founding:"), adr_id)
            self.assertTrue(heads[adr_id], adr_id)

    def test_an_adr_on_its_newest_live_member_is_not_stale(self):
        from memory_seed.core import stale_adr_anchors

        root = self.make_project()
        result = promote_decision(
            root, adr_id="adr_anchor", source_entry_id="mse_extension0000001",
            source_decision="d1", title="Anchored", topics=(), user_initials="JNL",
            agent_type="claude", source="derived", decision="D.", why="W.",
            timestamp="2026-08-08T10:00:00Z",
        )
        self.assertTrue(result.ok, result.issues)
        transition_adr(
            root, adr_id="adr_anchor", status="accepted",
            decision_ref="mse_extension0000001:d1", update_entry_id="mse_extension0000001",
            source="derived", timestamp="2026-08-08T10:01:00Z",
        )
        self.assertEqual(stale_adr_anchors(root), [])


class ReproposeAfterRejectTests(ProjectFixture):
    """A revision's text is fixed at proposal time, so a rejected ref must be re-proposable.

    Without this, a summary written from bad evidence can never be corrected: the ledger is
    append-only, `revise_adr` keys on `decision_ref`, and the same decision is the only honest
    thing to key a correction on. Inventing a different ref to carry the fix would put a false
    head on an authority record.

    What stays forbidden is duplicating a LIVE ref - proposed or accepted - which would leave two
    competing texts with no way to tell which the ADR rests on.
    """

    def _founded(self, root, adr_id="adr_repropose"):
        result = promote_decision(
            root, adr_id=adr_id, title="Concern", topics=(), user_initials="JNL",
            agent_type="claude", source="derived", decision="Founding position.", why="W.",
            founding_source=".memory-seed/index.md#L1", founding_quote="A founding line.",
            timestamp="2026-08-08T10:00:00Z",
        )
        self.assertTrue(result.ok, result.issues)
        transition_adr(
            root, adr_id=adr_id, status="accepted", update_entry_id=None,
            source="derived", timestamp="2026-08-08T10:01:00Z",
        )
        return root / ".memory-seed" / "decisions" / f"{adr_id}.md"

    def _propose(self, root, decision, stamp, adr_id="adr_repropose", dry_run=False):
        return revise_adr(
            root, adr_id=adr_id, decision_ref="mse_extension0000001:d1", decision=decision,
            why="W.", evolution="E.", update_entry_id="mse_extension0000001", source="derived",
            predecessors=(), timestamp=stamp, dry_run=dry_run,
        )

    def test_a_rejected_ref_may_be_proposed_again_with_corrected_text(self):
        root = self.make_project()
        path = self._founded(root)
        self.assertTrue(self._propose(root, "First wording.", "2026-08-08T11:00:00Z").ok)
        rejected = transition_adr(
            root, adr_id="adr_repropose", status="rejected",
            decision_ref="mse_extension0000001:d1", update_entry_id="mse_extension0000001",
            source="derived", reason="Summary did not synthesise the live chain.",
            timestamp="2026-08-08T11:01:00Z",
        )
        self.assertTrue(rejected.ok, rejected.issues)

        again = self._propose(root, "Corrected wording.", "2026-08-08T11:02:00Z")
        self.assertTrue(again.ok, again.issues)

        record = parse_adr(path)
        state = replay_adr(record)
        # The re-proposal is live again, and the head has not moved - acceptance is still the gate.
        self.assertEqual(state.pending_decisions, ("mse_extension0000001:d1",))
        self.assertEqual(state.authoritative_decision, "founding:.memory-seed/index.md#L1")
        # The CORRECTED text is what the view shows, not the wording that was rejected.
        view = render_adr(record).split("## Event ledger")[0]
        self.assertIn("Corrected wording.", view)
        self.assertNotIn("First wording.", view)

    def test_a_live_ref_still_cannot_be_duplicated(self):
        root = self.make_project()
        self._founded(root)
        self.assertTrue(self._propose(root, "First wording.", "2026-08-08T11:00:00Z").ok)
        # Still PROPOSED: a second text on the same decision is refused.
        clash = self._propose(root, "Competing wording.", "2026-08-08T11:02:00Z", dry_run=True)
        self.assertFalse(clash.ok)
        self.assertTrue(any("duplicates revision" in issue for issue in clash.issues), clash.issues)

        accepted = transition_adr(
            root, adr_id="adr_repropose", status="accepted",
            decision_ref="mse_extension0000001:d1", update_entry_id="mse_extension0000001",
            source="derived",
            expected_authoritative_decision="founding:.memory-seed/index.md#L1",
            timestamp="2026-08-08T11:03:00Z",
        )
        self.assertTrue(accepted.ok, accepted.issues)
        # ACCEPTED: still refused. Only rejection reopens the ref.
        after = self._propose(root, "Post-acceptance wording.", "2026-08-08T11:04:00Z", dry_run=True)
        self.assertFalse(after.ok)
        self.assertTrue(any("duplicates revision" in issue for issue in after.issues), after.issues)

    def test_reconcile_accepts_a_reproposal_the_same_way_validate_does(self):
        """The third copy of the replay rules must agree with the other two.

        `reconcile_adr_records` keeps its own replay loop, and its own comment records that the
        founding extension updated `replay_adr` and `validate_adr` and missed it. The 2026-08-08
        relaxation did exactly that again: `adr check` passed on the branch while `session
        merge-branch` - which validates with main's reconciler - refused 25 ADRs for duplicate
        revisions. This pins the two together.
        """
        import copy

        root = self.make_project()
        path = self._founded(root, adr_id="adr_reconcile")
        self.assertTrue(self._propose(root, "First wording.", "2026-08-08T11:00:00Z",
                                      adr_id="adr_reconcile").ok)
        transition_adr(
            root, adr_id="adr_reconcile", status="rejected",
            decision_ref="mse_extension0000001:d1", update_entry_id="mse_extension0000001",
            source="derived", reason="Superseded wording.", timestamp="2026-08-08T11:01:00Z",
        )
        self.assertTrue(self._propose(root, "Corrected wording.", "2026-08-08T11:02:00Z",
                                      adr_id="adr_reconcile").ok)
        record = parse_adr(path)
        # Reconciling a record against itself is the merge the fuse performs when only one side
        # moved - it must not invent a conflict.
        merged, issues = reconcile_adr_records(copy.deepcopy(record), copy.deepcopy(record))
        self.assertEqual(issues, [])
        self.assertIsNotNone(merged)
        self.assertEqual(replay_adr(merged).pending_decisions, ("mse_extension0000001:d1",))

    def test_the_live_corpus_is_untouched_by_this_relaxation(self):
        """No live ADR has two proposals for one ref, so first-match and last-match agree."""
        for path in LIVE_ADRS:
            self.assertEqual(validate_adr(parse_adr(path), REPO), [], path.name)
            self.assertEqual(render_adr(parse_adr(path)), read_text_file(path), path.name)
