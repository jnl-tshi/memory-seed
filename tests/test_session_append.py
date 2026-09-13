"""`session append` (P1): entry authoring with structure enforced.

The tool owns structure (target, timestamp, canonical id, YAML shape,
ref/topic validation, chronological append); the agent owns voice (title,
classification, body prose - passed through verbatim). Nothing is written
when any guard fails, and all failures report together.
"""

import json
import shutil
import subprocess
import tempfile
import time
import unittest
from dataclasses import asdict
from pathlib import Path

from _git_helpers import run_git

from memory_seed.core import (
    MEMORY_DIR_NAME,
    _git_capture,
    check_session_links,
    generate_session_entry_id,
    resolve_runtime,
    session_append_entry,
    _write_session_file,
)
from memory_seed.retrieval import entry_topic_sidecars
from memory_seed import corpus_cache

BODY = (
    "### Summary\n\n- Context for this entry.\n\n### Decisions\n\n"
    "#### D1 - Record the durable choice\n\n"
    "- D: Something durable.\n- R: Because."
)


class SessionAppendTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-append-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        (self.cwd / MEMORY_DIR_NAME / "sessions").mkdir(parents=True, exist_ok=True)

    def _append(self, **overrides):
        kwargs = dict(
            cwd=self.cwd,
            title="First decision",
            body=BODY,
            user_initials="JN",
            agent_type="claude",
            timestamp="2026-06-13 09:00",
            auto_branch=False,
        )
        kwargs.update(overrides)
        return session_append_entry(**kwargs)

    def test_appends_a_valid_entry_with_canonical_id(self):
        result = self._append()

        self.assertTrue(result.ok, result.issues)
        self.assertTrue(result.written)
        expected_id = generate_session_entry_id(
            timestamp="2026-06-13 09:00",
            title="First decision",
            user_initials="JN",
            agent_type="claude",
            project_path=".",
            subproject_path=None,
        )
        self.assertEqual(result.entry_id, expected_id)
        text = result.path.read_text(encoding="utf-8")
        self.assertIn("## 2026-06-13 09:00 - First decision", text)
        self.assertIn(f"entry_id: {expected_id}", text)
        self.assertNotIn("agent_name:", text)
        self.assertIn("- D: Something durable.", text)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_internal_mutation_receipts_include_exact_new_per_user_frontmatter(self):
        receipts = []
        result = self._append(explicit_user="jean", _mutation_observer=receipts.append)
        self.assertTrue(result.ok, result.issues)
        self.assertEqual(len(receipts), 2)
        created, appended = receipts
        self.assertTrue(created.created)
        self.assertIsNone(created.preimage)
        self.assertIn(b"schema_version: 2\n", created.postimage)
        self.assertIn(b"hash_id: msm_", created.postimage)
        self.assertIn(b"user: jean\ncreated_at: ", created.postimage)
        self.assertFalse(appended.created)
        self.assertEqual(appended.preimage, created.postimage)
        self.assertEqual(appended.postimage, result.path.read_bytes())
        self.assertEqual(created.path, result.path)
        self.assertEqual(appended.path, result.path)
        self.assertEqual(appended.postimage.count(b"hash_id:"), 1)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)
        self.assertEqual(set(asdict(result)), {
            "ok", "path", "entry_id", "timestamp", "issues", "written", "rendered",
            "sidecar_paths", "rendered_sidecars", "journal_path",
        })
        self.assertIsNone(result.rendered)

    def test_internal_mutation_receipts_distinguish_new_flat_from_existing_empty(self):
        receipts = []
        result = self._append(_mutation_observer=receipts.append)
        self.assertTrue(result.ok, result.issues)
        self.assertEqual([(item.preimage, item.created) for item in receipts], [(None, True), (b"", False)])
        self.assertEqual(receipts[-1].postimage, result.path.read_bytes())

        empty = result.path.with_name("2026-06-14.md")
        empty.write_bytes(b"")
        receipts.clear()
        result = self._append(timestamp="2026-06-14 09:00", _mutation_observer=receipts.append)
        self.assertTrue(result.ok, result.issues)
        self.assertEqual(result.path, empty)
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0].preimage, b"")
        self.assertFalse(receipts[0].created)

    def test_internal_mutation_receipt_uses_exact_read_snapshot_and_canonical_postimage(self):
        prior = self._append(explicit_user="jean")
        raw = prior.path.read_bytes().replace(b"\n", b"\r\n") + "\r\nCafe\u0301\r\n".encode("utf-8")
        prior.path.write_bytes(raw)
        receipts = []
        result = self._append(title="Second decision", timestamp="2026-06-13 09:01",
                              explicit_user="jean", _mutation_observer=receipts.append)
        self.assertTrue(result.ok, result.issues)
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0].preimage, raw)
        self.assertEqual(receipts[0].postimage, result.path.read_bytes())
        self.assertNotIn(b"\r", receipts[0].postimage)
        self.assertIn("Caf\u00e9\n".encode("utf-8"), receipts[0].postimage)

    def test_internal_mutation_receipt_never_adopts_later_file_bytes(self):
        receipts = []
        marker = b"\nConcurrent after-write content\n"

        def observe(mutation):
            receipts.append(mutation)
            if not mutation.created:
                mutation.path.write_bytes(mutation.postimage + marker)

        result = self._append(explicit_user="jean", _mutation_observer=observe)
        self.assertTrue(result.ok, result.issues)
        self.assertNotIn(marker, receipts[-1].postimage)
        self.assertEqual(result.path.read_bytes(), receipts[-1].postimage + marker)

    def test_internal_mutation_receipts_are_absent_for_dry_run_and_refusal(self):
        receipts = []
        preview = self._append(explicit_user="jean", dry_run=True, _mutation_observer=receipts.append)
        self.assertTrue(preview.ok, preview.issues)
        self.assertFalse(preview.path.exists())
        refused = self._append(timestamp="invalid", explicit_user="jean", _mutation_observer=receipts.append)
        self.assertFalse(refused.ok)
        self.assertEqual(receipts, [])

    def test_internal_session_creation_does_not_claim_a_raced_in_file(self):
        path = self.cwd / MEMORY_DIR_NAME / "sessions" / "concurrent.md"
        path.write_bytes(b"Unowned concurrent content\n")
        receipts = []
        self.assertFalse(_write_session_file(path, "new header", preimage=None, observer=receipts.append))
        self.assertEqual(receipts, [])
        self.assertEqual(path.read_bytes(), b"Unowned concurrent content\n")

    def test_decision_envelope_writes_topics_and_links_only_to_sidecars(self):
        # The entry owns its narrative.  Decision-scoped semantic assertions
        # are published in the existing append-only sidecar formats, where the
        # checker and branch fuse already know how to validate them.
        (self.cwd / MEMORY_DIR_NAME / "topics.yaml").write_text(
            """schema_version: 2
topics:
  - slug: schema
    axis: area
  - slug: feature-build
    axis: activity
""",
            encoding="utf-8",
        )
        older = self._append(title="Earlier decision", timestamp="2026-06-13 08:00")
        result = self._append(
            title="Sidecar decision",
            timestamp="2026-06-13 09:00",
            decisions=[
                {
                    "decision": "d1",
                    "topics": {"area": "schema", "activity": "feature-build", "source": "write-time"},
                    "links": {"evolves": [{"ref": older.entry_id, "type": "refines", "why": "test fixture edge"}]},
                }
            ],
        )

        self.assertTrue(result.ok, result.issues)
        entry = result.path.read_text(encoding="utf-8")
        self.assertNotIn("topics:", entry)
        self.assertNotIn("evolves:", entry)
        self.assertNotIn("decision_origins:", entry)
        self.assertEqual(len(result.sidecar_paths), 2)
        self.assertIsNotNone(result.journal_path)
        journal = json.loads(result.journal_path.read_text(encoding="utf-8"))
        self.assertEqual(journal["status"], "complete")
        self.assertFalse(journal["recovered"])
        self.assertEqual(journal["receipt"]["sidecar_paths"], [str(path) for path in result.sidecar_paths])
        topic_path = self.cwd / MEMORY_DIR_NAME / "sessions" / "topics" / "2026-06" / "2026-06-13.md"
        link_path = self.cwd / MEMORY_DIR_NAME / "sessions" / "links" / "2026-06" / "2026-06-13.md"
        self.assertIn(f"entry_id: {result.entry_id}", topic_path.read_text(encoding="utf-8"))
        self.assertIn("- schema:d1", topic_path.read_text(encoding="utf-8"))
        self.assertIn("- feature-build:d1", topic_path.read_text(encoding="utf-8"))
        self.assertIn(f"- d1 -> {older.entry_id}", link_path.read_text(encoding="utf-8"))
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_lower_level_origins_are_optional_but_render_when_complete(self):
        self._vocabulary()
        result = self._append(
            decisions=[
                {
                    "decision": "d1",
                    "origin": "user",
                    "topics": {"area": "schema", "activity": "feature-build"},
                }
            ]
        )

        self.assertTrue(result.ok, result.issues)
        self.assertIn(
            "decision_origins:\n  d1: user",
            result.path.read_text(encoding="utf-8"),
        )

    def test_lower_level_origin_requires_complete_body_decision_coverage(self):
        self._vocabulary()
        body = (
            "### Summary\n\n- Two choices.\n\n### Decisions\n\n"
            "#### D1 - User choice\n\n- D: Honor it.\n- R: Direct instruction.\n\n"
            "#### D2 - Agent finding\n\n- D: Keep the guard.\n- R: Tests require it.\n"
        )
        incomplete_envelope = self._append(
            body=body,
            decisions=[
                {
                    "decision": "d1",
                    "origin": "user",
                    "topics": {"area": "schema", "activity": "feature-build"},
                }
            ],
        )
        mixed_origins = self._append(
            body=body,
            decisions=[
                {
                    "decision": "d1",
                    "origin": "user",
                    "topics": {"area": "schema", "activity": "feature-build"},
                },
                {
                    "decision": "d2",
                    "topics": {"area": "schema", "activity": "feature-build"},
                },
            ],
        )

        for result in (incomplete_envelope, mixed_origins):
            self.assertFalse(result.ok)
            self.assertFalse(result.written)
            self.assertIn(
                "decision origins must cover every body decision",
                " ".join(result.issues),
            )
        self.assertEqual(list((self.cwd / MEMORY_DIR_NAME / "sessions").rglob("*.md")), [])

    def _vocabulary(self):
        (self.cwd / MEMORY_DIR_NAME / "topics.yaml").write_text(
            """schema_version: 2
topics:
  - slug: schema
    axis: area
  - slug: feature-build
    axis: activity
""",
            encoding="utf-8",
        )

    def test_both_axes_are_mandatory_on_every_decision(self):
        # The MCP schema has required area+activity since 2026-07-31; the CLI
        # path accepted neither, and that asymmetry is what let decision-keyed
        # attribution fall 92% -> 8% while coverage stayed at 100%.
        self._vocabulary()

        missing_activity = self._append(
            title="No activity", decisions=[{"decision": "d1", "topics": {"area": "schema"}}]
        )
        self.assertFalse(missing_activity.ok)
        self.assertIn("needs topics.activity", " ".join(missing_activity.issues))

        missing_area = self._append(
            title="No area", decisions=[{"decision": "d1", "topics": {"activity": "feature-build"}}]
        )
        self.assertFalse(missing_area.ok)
        self.assertIn("needs topics.area", " ".join(missing_area.issues))

    def test_the_sidecar_declares_each_slug_s_axis(self):
        # A flat list leaves the axis to be looked up in topics.yaml, so the
        # sidecar cannot be read on its own terms. The nested shape declares it,
        # and entry_topic_sidecars has read that shape since 2026-07-27.
        self._vocabulary()

        result = self._append(
            title="Axis declared",
            timestamp="2026-06-13 09:00",
            decisions=[{"decision": "d1", "topics": {"area": "schema", "activity": "feature-build"}}],
        )

        self.assertTrue(result.ok, result.issues)
        topics = (self.cwd / MEMORY_DIR_NAME / "sessions" / "topics" / "2026-06" / "2026-06-13.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("topics:\n  area:\n    - schema:d1\n  activity:\n    - feature-build:d1", topics)
        read = entry_topic_sidecars(cwd=self.cwd)[result.entry_id]
        self.assertEqual(read["decision_area"], (("d1", "schema"),))
        self.assertEqual(read["decision_activity"], (("d1", "feature-build"),))

    def test_a_proposed_topic_is_a_request_never_an_attribution(self):
        # It rides ALONGSIDE the mandatory real pair, so the write is never
        # blocked, and it lands under its own key - never in `topics:`, which
        # every reader treats as resolvable vocabulary - carrying the axis it is
        # being requested on, because a request without one cannot be ruled on.
        self._vocabulary()

        result = self._append(
            title="Requests vocabulary",
            timestamp="2026-06-13 09:00",
            decisions=[
                {
                    "decision": "d1",
                    "topics": {
                        "area": "schema",
                        "activity": "feature-build",
                        "proposed_topic": {"slug": "swarm-orchestration", "axis": "activity"},
                    },
                }
            ],
        )

        self.assertTrue(result.ok, result.issues)
        topics = (self.cwd / MEMORY_DIR_NAME / "sessions" / "topics" / "2026-06" / "2026-06-13.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("proposed_topics:\n  activity:\n    - swarm-orchestration:d1", topics)
        self.assertIn("topics:\n  area:\n    - schema:d1", topics)
        # The request is NOT an attribution: the topic reader never returns it.
        read = entry_topic_sidecars(cwd=self.cwd)[result.entry_id]
        self.assertNotIn("swarm-orchestration", read["topics"])
        self.assertNotIn(("d1", "swarm-orchestration"), read["decision_topics"])
        self.assertTrue(check_session_links(cwd=self.cwd).ok, check_session_links(cwd=self.cwd).issues)

    def test_a_proposed_topic_needs_an_axis_and_must_not_already_resolve(self):
        self._vocabulary()

        no_axis = self._append(
            title="No axis",
            decisions=[
                {
                    "decision": "d1",
                    "topics": {
                        "area": "schema",
                        "activity": "feature-build",
                        "proposed_topic": {"slug": "swarm-orchestration"},
                    },
                }
            ],
        )
        self.assertFalse(no_axis.ok)
        self.assertIn("axis must be 'area' or 'activity'", " ".join(no_axis.issues))

        # Requesting vocabulary that exists is a mis-use, not a request: the
        # author should be attributing with it instead.
        existing = self._append(
            title="Already resolves",
            decisions=[
                {
                    "decision": "d1",
                    "topics": {
                        "area": "schema",
                        "activity": "feature-build",
                        "proposed_topic": {"slug": "schema", "axis": "area"},
                    },
                }
            ],
        )
        self.assertFalse(existing.ok)
        self.assertIn("already resolves", " ".join(existing.issues))

    def test_decision_envelope_refuses_legacy_semantic_fields_and_bad_ordinals(self):
        result = self._append(
            topics=["schema"],
            decisions=[{"decision": "d9", "topics": {"area": "schema"}}],
        )

        self.assertFalse(result.ok)
        joined = " ".join(result.issues)
        self.assertIn("one sidecar authority", joined)
        self.assertIn("not recorded in the body", joined)
        self.assertEqual(list((self.cwd / MEMORY_DIR_NAME / "sessions").rglob("*.md")), [])

    def test_pending_journal_recovers_after_sidecar_write_interrupt(self):
        """An interrupted sidecar write keeps the already-published parent valid."""
        from unittest.mock import patch

        (self.cwd / MEMORY_DIR_NAME / "topics.yaml").write_text(
            """schema_version: 2
topics:
  - slug: schema
    axis: area
  - slug: feature-build
    axis: activity
""",
            encoding="utf-8",
        )
        older = self._append(title="Earlier decision", timestamp="2026-06-13 08:00")
        payload = {
            "title": "Interrupted sidecar decision",
            "timestamp": "2026-06-13 09:00",
            "decisions": [{
                "decision": "d1",
                "topics": {"area": "schema", "activity": "feature-build"},
                "links": {"evolves": [{"ref": older.entry_id, "type": "refines", "why": "test fixture edge"}]},
            }],
        }
        from memory_seed.core import _write_chronological_topic_sidecar_file as real_write_topic_sidecar

        def interrupt_topic_write(path, topic_date, records):
            real_write_topic_sidecar(path, topic_date, records)
            raise OSError("simulated interruption after topic sidecar write")

        with patch("memory_seed.core._write_chronological_topic_sidecar_file", side_effect=interrupt_topic_write):
            with self.assertRaisesRegex(OSError, "simulated interruption after topic sidecar write"):
                self._append(**payload)

        journals = list((self.cwd / MEMORY_DIR_NAME / "transactions" / "decision-sidecar").glob("*.json"))
        self.assertEqual(len(journals), 1)
        self.assertEqual(json.loads(journals[0].read_text(encoding="utf-8"))["status"], "pending")
        self.assertTrue(check_session_links(cwd=self.cwd).ok)
        altered = self._append(
            **payload,
            body="### Decision\n\n- D: Alter the retry.\n- R: It must be refused.\n",
        )
        self.assertFalse(altered.ok)
        self.assertTrue(any("conflicts with this write" in issue for issue in altered.issues), altered.issues)
        recovered = self._append(**payload)
        self.assertTrue(recovered.ok, recovered.issues)
        self.assertEqual(json.loads(journals[0].read_text(encoding="utf-8"))["status"], "complete")
        self.assertTrue(json.loads(journals[0].read_text(encoding="utf-8"))["recovered"])
        written = recovered.path.read_text(encoding="utf-8")
        self.assertEqual(written.count("Interrupted sidecar decision"), 1)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def _append_multi_decision_older(self):
        body = (
            "### Summary\n\n- Context.\n\n### Decisions\n\n"
            "#### D1 - First call\n\n- D: alpha\n- R: because\n\n"
            "#### D2 - Second call\n\n- D: beta\n- R: reasons\n"
        )
        result = self._append(title="Older with decisions", body=body, timestamp="2026-06-13 08:00")
        self.assertTrue(result.ok, result.issues)
        return result.entry_id

    def _append_links(self, kind, refs, *, edge_type="builds-on", **overrides):
        """Author lifecycle links the only way that still exists: the envelope.

        Entry YAML stopped accepting them on 2026-08-09, so the grammar rules
        these tests cover are exercised through `decisions[].links` - the rules
        are unchanged, only the surface that carries them moved. Evidence and (on
        evolves) an evolution type are mandatory, so the helper supplies both.
        """
        self._vocabulary()
        items = []
        for ref in refs:
            item = {"ref": ref}
            if kind in {"replaces", "evolves"}:
                item["why"] = "fixture edge"
            if kind == "evolves":
                item["type"] = edge_type
            items.append(item)
        return self._append(
            decisions=[
                {
                    "decision": "d1",
                    "topics": {"area": "schema", "activity": "feature-build"},
                    "links": {kind: items},
                }
            ],
            **overrides,
        )

    def _sidecar_text(self, result):
        return "\n".join(
            Path(path).read_text(encoding="utf-8") for path in result.sidecar_paths
        )

    def test_append_accepts_decision_ref_in_evolves(self):
        # Write-time grammar (2026-07-24): `:dN` on an existing ordinal of an
        # older entry passes the guards and is written verbatim - now into the
        # link sidecar, with the source ordinal the envelope supplies.
        older = self._append_multi_decision_older()
        result = self._append_links("evolves", [f"{older}:d2"])
        self.assertTrue(result.ok, result.issues)
        self.assertIn(f"- d1 -> {older}:d2 (builds-on)", self._sidecar_text(result))
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_append_records_evidence_and_evolution_type_for_a_lifecycle_edge(self):
        # The write-time mandate (JNL 2026-08-09): an evolves edge names WHY it
        # was drawn and WHICH kind of evolution it is. Both are refused when
        # missing, because the author knows each exactly once and append-only
        # makes the omission permanent.
        older = self._append_multi_decision_older()
        ok = self._append_links("evolves", [f"{older}:d2"], edge_type="refines")
        self.assertTrue(ok.ok, ok.issues)
        text = self._sidecar_text(ok)
        self.assertIn(f"- d1 -> {older}:d2 (refines)", text)
        self.assertIn('why: "fixture edge"', text)

        for links, expected in (
            ({"evolves": [{"ref": f"{older}:d2", "why": "reason"}]}, "needs type"),
            ({"evolves": [{"ref": f"{older}:d2", "type": "refines"}]}, "needs 'why'"),
            ({"replaces": [{"ref": f"{older}:d2"}]}, "needs 'why'"),
        ):
            with self.subTest(expected=expected):
                bad = self._append(
                    title="Missing metadata",
                    timestamp="2026-06-13 11:00",
                    decisions=[
                        {
                            "decision": "d1",
                            "topics": {"area": "schema", "activity": "feature-build"},
                            "links": links,
                        }
                    ],
                )
                self.assertFalse(bad.ok)
                self.assertTrue(any(expected in issue for issue in bad.issues), bad.issues)

    def test_a_decision_may_be_refined_only_once(self):
        # The rule that makes a lineage a line rather than a fan. `builds-on` is
        # deliberately unlimited, so the second edge is refused only when it too
        # claims to be the next form.
        older = self._append_multi_decision_older()
        first = self._append_links("evolves", [f"{older}:d2"], edge_type="refines")
        self.assertTrue(first.ok, first.issues)

        rival = self._append_links(
            "evolves",
            [f"{older}:d2"],
            edge_type="refines",
            title="Rival successor",
            timestamp="2026-06-13 11:00",
        )
        self.assertFalse(rival.ok)
        self.assertTrue(any("is already refined by" in issue for issue in rival.issues), rival.issues)

        alongside = self._append_links(
            "evolves",
            [f"{older}:d2"],
            edge_type="builds-on",
            title="Later work",
            timestamp="2026-06-13 12:00",
        )
        self.assertTrue(alongside.ok, alongside.issues)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_append_rejects_decision_ref_to_missing_ordinal(self):
        older = self._append_multi_decision_older()
        result = self._append(evolves=[f"{older}:d9"])
        self.assertFalse(result.ok)
        self.assertTrue(any("has no d9" in issue for issue in result.issues))

    def test_append_accepts_decision_ref_in_related_entries(self):
        # Decision-level related (2026-07-25): related_entries may carry :dN,
        # allowed but never mandated. A valid ordinal on a 2-decision target
        # passes; a nonexistent one is still dangling.
        older = self._append_multi_decision_older()  # has d1, d2
        ok = self._append_links("related_entries", [f"{older}:d2"])
        self.assertTrue(ok.ok, ok.issues)
        self.assertIn(f"- d1 -> {older}:d2", self._sidecar_text(ok))
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

        bad = self._append_links(
            "related_entries", [f"{older}:d9"], title="Bad ord", timestamp="2026-06-13 10:00"
        )
        self.assertFalse(bad.ok)
        self.assertTrue(any("has no d9" in issue for issue in bad.issues), bad.issues)

    def test_append_does_not_mandate_decision_ref_in_related_entries(self):
        # Unlike replaces/evolves, related is NOT required to name the decision
        # on a multi-decision target - it stays casual for hand-authoring. It
        # needs no evidence either, for the same reason.
        older = self._append_multi_decision_older()  # 2 decisions
        ok = self._append_links("related_entries", [older])  # bare, no :dN
        self.assertTrue(ok.ok, ok.issues)

    # --- Grammar v2 (2026-07-24): granularity is mandated at write time ---

    def test_append_mandates_target_ordinal_when_target_has_multiple_decisions(self):
        older = self._append_multi_decision_older()
        result = self._append(evolves=[older])
        self.assertFalse(result.ok)
        self.assertTrue(any("has 2 decisions (d1,d2)" in issue for issue in result.issues), result.issues)

    def test_append_accepts_bare_ref_to_a_decisionless_target(self):
        summary_only = self._append(
            title="Note only", body="### Summary\n\n- a plain note.", timestamp="2026-06-13 08:00"
        )
        self.assertTrue(summary_only.ok, summary_only.issues)
        result = self._append_links("replaces", [summary_only.entry_id])
        self.assertTrue(result.ok, result.issues)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_append_takes_a_single_decision_target_bare_and_rejects_its_d1(self):
        # 2026-07-24 reconciliation: a single-decision target's :d1 and its bare
        # id denote the same edge, so bare is canonical and :d1 is rejected -
        # name a decision only when there is a choice to make.
        single = self._append(title="One call", timestamp="2026-06-13 08:00")  # BODY is singular
        self.assertTrue(single.ok, single.issues)

        bare = self._append_links(
            "evolves", [single.entry_id], title="Refines it", timestamp="2026-06-13 10:00"
        )
        self.assertTrue(bare.ok, bare.issues)
        self.assertIn(f"- d1 -> {single.entry_id} (builds-on)", self._sidecar_text(bare))

        redundant = self._append_links(
            "evolves", [f"{single.entry_id}:d1"], title="Over-specified", timestamp="2026-06-13 11:00"
        )
        self.assertFalse(redundant.ok)
        self.assertTrue(any("single decision" in issue and "bare id" in issue for issue in redundant.issues), redundant.issues)

    def test_append_accepts_comma_multi_ordinal_and_validates_each(self):
        older = self._append_multi_decision_older()
        ok = self._append_links("evolves", [f"{older}:d1,d2"])
        self.assertTrue(ok.ok, ok.issues)
        self.assertIn(f"- d1 -> {older}:d1,d2 (builds-on)", self._sidecar_text(ok))
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

        bad = self._append_links(
            "evolves", [f"{older}:d1,d9"], title="Bad ordinal", timestamp="2026-06-13 10:00"
        )
        self.assertFalse(bad.ok)
        self.assertTrue(any("has no d9" in issue for issue in bad.issues))

    def test_the_envelope_owns_the_source_ordinal_and_refuses_an_inline_one(self):
        # The source side is no longer hand-written: `decisions[].decision` names
        # the authoring ordinal and the renderer prefixes every ref with it. An
        # inline `dN -> ` would be a second, contradictable spelling of the same
        # fact, so it is refused rather than merged.
        older = self._append_multi_decision_older()
        result = self._append_links("evolves", [f"d2 -> {older}:d1"])
        self.assertFalse(result.ok)
        self.assertTrue(
            any("must omit the source prefix" in issue for issue in result.issues), result.issues
        )

        # And an authoring ordinal the body does not have is caught on the
        # envelope's own field, which is where it now lives.
        self._vocabulary()
        missing = self._append(
            title="No such ordinal",
            timestamp="2026-06-13 10:00",
            decisions=[
                {
                    "decision": "d9",
                    "topics": {"area": "schema", "activity": "feature-build"},
                    "links": {"evolves": [{"ref": older, "type": "builds-on", "why": "x"}]},
                }
            ],
        )
        self.assertFalse(missing.ok)
        self.assertTrue(
            any("is not recorded in the body" in issue for issue in missing.issues), missing.issues
        )

    def test_entry_yaml_lifecycle_flags_are_refused(self):
        # Entry YAML stopped accepting lifecycle links on 2026-08-09: a raw ref
        # in an entry's frontmatter tells a human reading the Markdown nothing,
        # and the flags have nowhere to put the evidence and evolution type the
        # envelope now mandates. The refusal has to name the replacement, or it
        # is just a wall.
        older = self._append_multi_decision_older()
        for kind in ("related_entries", "replaces", "evolves"):
            with self.subTest(kind=kind):
                result = self._append(
                    title=f"Flag {kind}",
                    timestamp="2026-06-13 10:00",
                    **{kind: [f"{older}:d1"]},
                )
                self.assertFalse(result.ok)
                self.assertTrue(
                    any(
                        f"{kind} is no longer accepted in entry YAML" in issue
                        and f"decisions[].links.{kind}" in issue
                        for issue in result.issues
                    ),
                    result.issues,
                )

    def test_second_append_separates_blocks_and_stays_clean(self):
        self._append()
        result = self._append(title="Second decision", timestamp="2026-06-13 10:00")

        self.assertTrue(result.ok, result.issues)
        text = result.path.read_text(encoding="utf-8")
        self.assertIn("\n\n## 2026-06-13 10:00 - Second decision", text)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_out_of_order_timestamp_is_refused_loudly(self):
        self._append(timestamp="2026-06-13 11:00")

        result = self._append(title="Late-clock entry", timestamp="2026-06-13 10:30")

        self.assertFalse(result.ok)
        self.assertFalse(result.written)
        self.assertTrue(any("chronology conflict" in issue for issue in result.issues))
        # Nothing was appended.
        self.assertNotIn("Late-clock entry", result.path.read_text(encoding="utf-8"))

    def test_malformed_body_is_refused(self):
        # The tool owns structure: a DRAFT body with bare labels and no section
        # heading is rejected before anything is written, with a fix message.
        result = self._append(body="D: bare, unbulleted label\nR: no heading either")

        self.assertFalse(result.ok)
        self.assertFalse(result.written)
        self.assertTrue(any("body format" in issue for issue in result.issues), result.issues)
        self.assertNotIn("bare, unbulleted", result.path.read_text(encoding="utf-8") if result.path.exists() else "")

    def test_fabricated_ref_is_refused(self):
        result = self._append(related_entries=("mse_" + "9" * 16,))

        self.assertFalse(result.ok)
        self.assertTrue(any("no such entry_id" in issue for issue in result.issues))

    def test_forward_pointing_lifecycle_ref_is_refused(self):
        first = self._append(timestamp="2026-06-13 09:00")
        # A later entry exists...
        later = self._append(title="Later", timestamp="2026-06-13 12:00")
        # ...and a new 10:00 entry may not replace it.
        result = self._append_links(
            "replaces", [later.entry_id], title="Middle", timestamp="2026-06-13 10:00"
        )

        self.assertFalse(result.ok)
        self.assertTrue(any("newer" in issue for issue in result.issues), result.issues)
        # But replacing the older first entry from a NEW newest entry works.
        # `first` is single-decision, so the ref stays BARE - :d1 there is
        # redundant and rejected (2026-07-24: name a decision only on a
        # choice).
        ok = self._append_links(
            "replaces", [first.entry_id], title="Replacement", timestamp="2026-06-13 13:00"
        )
        self.assertTrue(ok.ok, ok.issues)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_unknown_topic_is_refused_and_alias_resolves_to_canonical(self):
        (self.cwd / MEMORY_DIR_NAME / "topics.yaml").write_text(
            "schema_version: 1\ntopics:\n  - slug: memory-trace\n    label: Memory Trace\n    status: active\n    aliases: [trace-ui]\n",
            encoding="utf-8",
        )

        bad = self._append(topics=("nonexistent-topic",))
        self.assertFalse(bad.ok)
        self.assertTrue(any("unknown topic" in issue for issue in bad.issues))

        good = self._append(title="Aliased", topics=("trace-ui",))
        self.assertTrue(good.ok, good.issues)
        self.assertIn("- memory-trace", good.path.read_text(encoding="utf-8"))

    def test_identical_metadata_double_append_is_refused(self):
        self._append()
        result = self._append()

        self.assertFalse(result.ok)
        self.assertTrue(any("double-append" in issue for issue in result.issues))

    def test_all_failures_report_together(self):
        self._append(timestamp="2026-06-13 11:00")
        result = self._append(
            title="Everything wrong",
            timestamp="2026-06-13 09:30",
            related_entries=("mse_" + "9" * 16,),
        )

        self.assertFalse(result.ok)
        kinds = " ".join(result.issues)
        self.assertIn("chronology conflict", kinds)
        self.assertIn("no such entry_id", kinds)

    def test_explicit_branch_is_recorded_verbatim(self):
        result = self._append(branch="feature-x")
        self.assertIn("branch: feature-x", result.path.read_text(encoding="utf-8"))

    def test_dry_run_rendered_is_byte_identical_to_the_real_append(self):
        # The preview is the exact entry block. A fresh flat file also receives
        # the canonical file frontmatter owned by the sanctioned writer.
        preview = self._append(dry_run=True)

        self.assertTrue(preview.ok, preview.issues)
        self.assertFalse(preview.written)
        self.assertIsNotNone(preview.rendered)
        self.assertFalse(preview.path.exists(), "a dry run must not create the file")

        real = self._append()
        self.assertEqual(
            real.path.read_text(encoding="utf-8"),
            "---\ntags:\n  - session-log\n  - memory-seed\n"
            "session_date: 2026-06-13\n---\n\n" + preview.rendered,
        )
        self.assertEqual(real.entry_id, preview.entry_id)

    def test_rendered_is_absent_outside_a_passing_dry_run(self):
        written = self._append()
        self.assertIsNone(written.rendered, "a real write confirms with id/path, not an echo of the body")

        refused = self._append(title="Out of order", timestamp="2026-06-13 08:00", dry_run=True)
        self.assertFalse(refused.ok)
        self.assertIsNone(refused.rendered, "a refused write has no final output to preview")

    def test_decision_density_never_blocks_session_append(self):
        from memory_seed.core import entry_body_advisories, entry_body_format_issues

        body = (
            "### Summary\n\n- Context.\n\n### Decisions\n\n"
            "#### D1 - one\n\n- D: a\n- R: r\n\n"
            "#### D2 - two\n\n- D: b\n- R: r\n\n"
            "#### D3 - three\n\n- D: c\n- R: r\n"
        )

        # The write-time gate must stay silent; only the advisory path speaks.
        # session append calls entry_body_format_issues and refuses on any hit.
        self.assertEqual(entry_body_format_issues(body), [])
        self.assertEqual(len(entry_body_advisories(body)), 1)

    def test_append_requires_a_summary_for_new_entries_only(self):
        refused = self._append(
            body=(
                "### Decisions\n\n#### D1 - Missing summary\n\n"
                "- D: Something durable.\n- R: Because."
            )
        )

        self.assertFalse(refused.ok)
        self.assertTrue(any("no '### Summary'" in issue for issue in refused.issues), refused.issues)
        # The shared corpus lint stays historical/read-only: existing entries
        # lacking a Summary are rendered as legacy records, not rejected data.
        from memory_seed.core import entry_body_format_issues
        self.assertEqual(entry_body_format_issues("### Decision\n\n- D: old.\n- R: because."), [])

    def test_append_rejects_legacy_singular_decision_but_reader_accepts_it(self):
        refused = self._append(
            body=(
                "### Summary\n\n- New write.\n\n### Decision\n\n"
                "- D: Legacy shape.\n- R: It remains readable only."
            )
        )

        self.assertFalse(refused.ok)
        self.assertTrue(any("legacy '### Decision'" in issue for issue in refused.issues))
        from memory_seed.core import entry_body_format_issues
        self.assertEqual(
            entry_body_format_issues("### Decision\n\n- D: old.\n- R: because."),
            [],
        )

    def test_append_refuses_existing_headerless_flat_file(self):
        target = self.cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-13.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        original = "## 2026-06-13 08:00 - Legacy\n"
        target.write_text(original, encoding="utf-8")

        refused = self._append()

        self.assertFalse(refused.ok)
        self.assertTrue(any("headerless" in issue for issue in refused.issues))
        self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_future_timestamp_advisory_grace_window_and_past_are_quiet(self):
        from datetime import datetime, timedelta

        from memory_seed.core import check_entry_timestamp_advisories

        now = datetime(2026, 7, 18, 22, 0)

        def text_at(stamp):
            return (
                f"## {stamp:%Y-%m-%d %H:%M} - Entry\n\n"
                "```yaml\nentry_id: mse_aaaaaaaaaaaaaaaa\n```\n\n"
                "### Summary\n\n- a note\n"
            )

        # Past and present stamps are the normal case.
        self.assertEqual(check_entry_timestamp_advisories(text_at(now - timedelta(hours=2)), now=now), [])
        self.assertEqual(check_entry_timestamp_advisories(text_at(now), now=now), [])
        # Inside (and exactly at) the clock-skew grace window: quiet.
        self.assertEqual(check_entry_timestamp_advisories(text_at(now + timedelta(minutes=10)), now=now), [])
        # Beyond the grace window: flagged, attributed to the entry id.
        flagged = check_entry_timestamp_advisories(text_at(now + timedelta(minutes=11)), now=now)
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0][0], "mse_aaaaaaaaaaaaaaaa")
        self.assertIn("in the future", flagged[0][1])

    def test_future_timestamp_advisory_flags_only_the_drifted_entry(self):
        from datetime import datetime, timedelta

        from memory_seed.core import check_entry_timestamp_advisories

        now = datetime(2026, 7, 18, 22, 0)
        future = now + timedelta(hours=2)
        text = (
            "## 2026-07-18 09:00 - Fine\n\n```yaml\nentry_id: ms-aaaaaaaa\n```\n\n"
            "### Summary\n\n- ok\n\n"
            f"## {future:%Y-%m-%d %H:%M} - Drifted\n\n```yaml\nentry_id: ms-bbbbbbbb\n```\n\n"
            "### Summary\n\n- stamped ahead\n"
        )

        flagged = check_entry_timestamp_advisories(text, now=now)

        self.assertEqual([entry_id for entry_id, _ in flagged], ["ms-bbbbbbbb"])


class BranchProvenanceTests(unittest.TestCase):
    """What `branch:` actually records, per repository layout.

    `branch:` is the ONLY git-derived field on an entry (core.py, the single
    `_git_capture` call in `session_append_entry`); every other YAML key is
    caller-supplied, `read_local_user` is a file read, and the entry id hashes
    timestamp/title/initials/agent/paths. Diagram, topic and link sidecars carry
    no branch at all.

    What it records is the HEAD of the working tree containing
    `runtime.workspace_root`, read at write time. That is a property of a
    *checkout*, not of an agent's session, which is the whole of the
    cross-session contamination question. These tests pin the empirical matrix
    behind docs/2_Todo/branch-field-provenance.md so a future change to
    `resolve_runtime` cannot silently move it.
    """

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="mseed-branch-"))
        self.addCleanup(self._cleanup)
        self._repos = []
        self.primary, self.worktree, self.plain = self._build_repo("tracked", tracked=True)

    def _build_repo(self, name, *, tracked):
        """A primary checkout, a real nested worktree, and a plain nested dir.

        ``tracked`` decides whether `.memory-seed` is committed. That single bit
        is what makes worktree isolation work: a worktree only gets its own
        memory dir if the memory dir is in the tree. `.memory-seed/sessions`
        alone is not enough - git does not track empty directories.
        """
        primary = self.base / name
        (primary / MEMORY_DIR_NAME / "sessions").mkdir(parents=True)
        run_git(primary, "init", "-b", "main", check=True)
        run_git(primary, "config", "user.email", "probe@example.com", check=True)
        run_git(primary, "config", "user.name", "Probe", check=True)
        (primary / MEMORY_DIR_NAME / "agent-rules.md").write_text("# rules\n", encoding="utf-8")
        (primary / MEMORY_DIR_NAME / "sessions" / ".gitkeep").write_text("", encoding="utf-8")
        ignored = ".claude/worktrees/\n" + ("" if tracked else f"{MEMORY_DIR_NAME}/\n")
        (primary / ".gitignore").write_text(ignored, encoding="utf-8")
        run_git(primary, "add", "-A", check=True)
        run_git(primary, "commit", "-m", "init", check=True)
        self._repos.append(primary)

        # A real, nested, gitignored worktree on its own branch - the layout
        # this repo's parallel agents actually run in.
        worktree = primary / ".claude" / "worktrees" / "real-wt"
        worktree.parent.mkdir(parents=True, exist_ok=True)
        run_git(primary, "worktree", "add", "-b", f"feat/{name}", str(worktree), check=True)

        # A plain nested directory: no .git, no .memory-seed of its own.
        plain = primary / ".claude" / "worktrees" / "plain-dir"
        plain.mkdir(parents=True)

        # The primary then moves onto a feature branch, standing in for another
        # agent (or the user) checking one out mid-session.
        run_git(primary, "checkout", "-b", "claude/feature/someone-else", check=True)
        return primary, worktree, plain

    def _cleanup(self):
        for repo in self._repos:
            run_git(repo, "worktree", "prune")
        shutil.rmtree(self.base, ignore_errors=True)

    def _stamped_branch(self, cwd):
        result = session_append_entry(
            cwd,
            title="Probe",
            body=BODY,
            user_initials="JN",
            agent_type="claude",
            timestamp="2026-07-26 01:00",
            dry_run=True,
        )
        self.assertTrue(result.ok, result.issues)
        for line in (result.rendered or "").splitlines():
            if line.startswith("branch:"):
                return line.split(":", 1)[1].strip()
        return None

    def test_tracked_memory_seed_makes_a_worktree_record_its_own_branch(self):
        # THE headline result. When `.memory-seed` is committed - as it is in
        # this repository - a worktree gets its own copy, resolve_runtime stops
        # there, and git reads that worktree's HEAD. A worktree-isolated agent
        # is therefore NOT contaminated by whatever the primary has checked out.
        self.assertEqual(self._stamped_branch(self.worktree), "feat/tracked")
        self.assertEqual(self._stamped_branch(self.primary), "claude/feature/someone-else")

    def test_untracked_memory_seed_worktree_omits_the_branch_rather_than_lying(self):
        # The same worktree layout would silently stamp the PRIMARY's branch
        # when `.memory-seed` is not tracked: nothing stops the walk-up, so the
        # agent writes into the primary's memory dir. Neither HEAD is right -
        # the session is on the worktree's branch, the file lands on the
        # primary's - so the field is omitted, on the same principle as the
        # pre-existing detached-HEAD case. Omission, not refusal: the append
        # still succeeds and reports no issues.
        _, worktree, _ = self._build_repo("untracked", tracked=False)
        result = session_append_entry(
            worktree,
            title="Probe",
            body=BODY,
            user_initials="JN",
            agent_type="claude",
            timestamp="2026-07-26 01:00",
            dry_run=True,
        )
        self.assertTrue(result.ok, result.issues)
        self.assertEqual(result.issues, ())
        self.assertNotIn("branch:", result.rendered)
        self.assertIsNone(self._stamped_branch(worktree))

    def test_shared_checkout_concurrency_is_still_invisible(self):
        # The half that code cannot fix, pinned so nobody mistakes the omission
        # rule above for a complete answer. A plain nested dir and the primary
        # itself are the same working tree with the same HEAD, so an agent
        # working out of either records whatever branch is checked out at write
        # time - including one another's. Undecidable from git; needs a design
        # decision, not a heuristic.
        self.assertEqual(
            self._stamped_branch(self.plain), self._stamped_branch(self.primary)
        )
        self.assertEqual(self._stamped_branch(self.plain), "claude/feature/someone-else")

    def test_toplevels_agree_when_the_memory_dir_is_in_the_callers_own_tree(self):
        # The obvious fix - "resolve git relative to cwd rather than the
        # walked-up workspace_root" - is a NO-OP in every layout that behaves
        # correctly: git's own discovery walks up exactly as resolve_runtime
        # does, so both toplevels name the same working tree. In particular it
        # cannot tell a plain nested dir apart from a legitimate append made
        # from the primary checkout, which is the case that must keep working.
        for cwd in (self.primary, self.worktree, self.plain):
            with self.subTest(cwd=cwd.name):
                runtime = resolve_runtime(cwd)
                self.assertEqual(
                    _git_capture(cwd, "rev-parse", "--show-toplevel"),
                    _git_capture(runtime.workspace_root, "rev-parse", "--show-toplevel"),
                )

    def test_toplevels_disagree_exactly_when_the_stamped_branch_is_foreign(self):
        # ...but they DO disagree in the one layout that produces a wrong value
        # without any concurrency at all: cwd sits in working tree A while the
        # memory dir - and therefore the HEAD that gets stamped - belongs to
        # working tree B. This is the detectable subset, and the only part of
        # item 5 that code could act on. See docs/2_Todo/branch-field-provenance.md.
        _, worktree, _ = self._build_repo("untracked", tracked=False)
        runtime = resolve_runtime(worktree)
        self.assertNotEqual(
            _git_capture(worktree, "rev-parse", "--show-toplevel"),
            _git_capture(runtime.workspace_root, "rev-parse", "--show-toplevel"),
        )

    def test_explicit_branch_overrides_the_checkouts_head(self):
        # The documented mitigation: the caller is the only party that knows
        # which branch its session is really on, so it can say so.
        result = session_append_entry(
            self.plain,
            title="Probe",
            body=BODY,
            user_initials="JN",
            agent_type="claude",
            timestamp="2026-07-26 01:00",
            branch="claude/fix/my-own-task",
            dry_run=True,
        )
        self.assertIn("branch: claude/fix/my-own-task", result.rendered)

    def test_auto_branch_false_omits_the_field_inside_a_repository(self):
        # The other mitigation: record nothing rather than something wrong.
        result = session_append_entry(
            self.plain,
            title="Probe",
            body=BODY,
            user_initials="JN",
            agent_type="claude",
            timestamp="2026-07-26 01:00",
            auto_branch=False,
            dry_run=True,
        )
        self.assertNotIn("branch:", result.rendered)


if __name__ == "__main__":
    unittest.main()


class OneLinkPerChainGuardTests(unittest.TestCase):
    """Within one chain, a decision links its evolution once - at the head.
    Two evolves targets where one is a chain-ancestor of the other restate
    history the chain already carries, and are refused at write time."""

    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-chainguard-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        (self.cwd / MEMORY_DIR_NAME / "sessions").mkdir(parents=True, exist_ok=True)
        (self.cwd / MEMORY_DIR_NAME / "topics.yaml").write_text(
            "schema_version: 2\ntopics:\n  - slug: schema\n    axis: area\n"
            "  - slug: feature-build\n    axis: activity\n",
            encoding="utf-8",
        )

    def _append(self, **overrides):
        kwargs = dict(
            cwd=self.cwd,
            title="A decision",
            body=BODY,
            user_initials="JN",
            agent_type="claude",
            auto_branch=False,
        )
        kwargs.update(overrides)
        return session_append_entry(**kwargs)

    def _decision(self, evolves_items):
        return [
            {
                "decision": "d1",
                "topics": {"area": "schema", "activity": "feature-build", "source": "write-time"},
                "links": {"evolves": evolves_items},
            }
        ]

    def test_two_targets_in_one_chain_are_refused_with_the_fix(self):
        root = self._append(title="Root", timestamp="2026-06-13 08:00")
        mid = self._append(
            title="Mid",
            timestamp="2026-06-13 08:30",
            decisions=self._decision(
                [{"ref": root.entry_id, "type": "refines", "why": "next form"}]
            ),
        )
        self.assertTrue(mid.ok, mid.issues)
        result = self._append(
            title="Restates the chain",
            timestamp="2026-06-13 09:00",
            decisions=self._decision(
                [
                    {"ref": mid.entry_id, "type": "builds-on", "why": "rests on it"},
                    {"ref": root.entry_id, "type": "builds-on", "why": "and its root"},
                ]
            ),
        )
        self.assertFalse(result.ok)
        joined = " ".join(result.issues)
        self.assertIn("ONE chain", joined)
        self.assertIn(f"Keep the edge to d1 -> {mid.entry_id}", joined)
        self.assertIn("related_entries", joined)

    def test_two_targets_in_different_chains_pass(self):
        # Cross-chain multi-evolves is a merge and stays fully legal.
        one = self._append(title="Chain one", timestamp="2026-06-13 08:00")
        two = self._append(title="Chain two", timestamp="2026-06-13 08:30")
        result = self._append(
            title="Merges two concerns",
            timestamp="2026-06-13 09:00",
            decisions=self._decision(
                [
                    {"ref": one.entry_id, "type": "builds-on", "why": "x"},
                    {"ref": two.entry_id, "type": "builds-on", "why": "y"},
                ]
            ),
        )
        self.assertTrue(result.ok, result.issues)

    def test_append_reuses_supplied_snapshot_and_leaves_prewrite_artifact_stale(self):
        # The chain guard needs a corpus; handing it the one pre-write snapshot
        # means the write itself never publishes, repairs or deletes its cache.
        subprocess.run(["git", "init", "-q"], cwd=self.cwd, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.cwd, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.cwd, check=True)
        subprocess.run(["git", "add", "."], cwd=self.cwd, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.cwd, check=True)
        one = self._append(title="Chain one", timestamp="2026-06-13 08:00")
        two = self._append(title="Chain two", timestamp="2026-06-13 08:30")
        cache = self.cwd / "cache"
        builds = []
        snapshot = corpus_cache.get_corpus_snapshot(
            self.cwd, cache_dir=cache,
            source_builder=lambda cwd: (builds.append(cwd) or corpus_cache._default_source_builder(cwd)),
        )
        artifact = next(cache.glob("*.json"))
        before = (artifact.read_bytes(), artifact.stat().st_mtime_ns, sorted(p.name for p in cache.iterdir()))
        started = time.perf_counter()
        result = self._append(
            title="Merges two concerns", timestamp="2026-06-13 09:00",
            decisions=self._decision([
                {"ref": one.entry_id, "type": "builds-on", "why": "x"},
                {"ref": two.entry_id, "type": "builds-on", "why": "y"},
            ]),
            snapshot=snapshot,
        )
        elapsed = time.perf_counter() - started
        after = (artifact.read_bytes(), artifact.stat().st_mtime_ns, sorted(p.name for p in cache.iterdir()))
        print(json.dumps({"measurement": "append_snapshot", "elapsed_seconds": elapsed, "source_builds": len(builds)}))

        self.assertTrue(result.ok, result.issues)
        self.assertEqual(builds, [self.cwd])
        self.assertEqual(before, after)
        stale = corpus_cache.inspect_corpus_cache(self.cwd, cache_dir=cache)
        self.assertEqual(stale.health, "stale")
        rebuilt = corpus_cache.get_corpus_snapshot(
            self.cwd, cache_dir=cache,
            source_builder=lambda cwd: (builds.append(cwd) or corpus_cache._default_source_builder(cwd)),
        )
        self.assertEqual(builds, [self.cwd, self.cwd])
        self.assertEqual(rebuilt.origin, "reconstructed")

    def test_cache_failure_does_not_block_a_valid_multi_target_append(self):
        one = self._append(title="Chain one", timestamp="2026-06-13 08:00")
        two = self._append(title="Chain two", timestamp="2026-06-13 08:30")
        from unittest.mock import patch

        with patch("memory_seed.corpus_cache.get_corpus_snapshot", side_effect=OSError("cache unavailable")):
            result = self._append(
                title="Merges despite cache failure", timestamp="2026-06-13 09:00",
                decisions=self._decision([
                    {"ref": one.entry_id, "type": "builds-on", "why": "x"},
                    {"ref": two.entry_id, "type": "builds-on", "why": "y"},
                ]),
            )
        self.assertTrue(result.ok, result.issues)
