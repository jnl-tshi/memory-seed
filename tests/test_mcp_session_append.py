"""`memory_session_append`: the gated MCP write surface.

Most structural guards live in `session_append_entry`; these tests also cover
the stricter authored-topic contract at the MCP boundary, a caller-supplied
`cwd`, and refusals that must arrive as data rather than as a JSON-RPC error.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME
from memory_seed.mcp_server import TOOLS, call_tool

BODY = (
    "### Decision\n\n"
    "- D: Ship the gated append path.\n"
    "- R: The ungated one skipped every guard.\n\n"
    "### Summary\n\n"
    "The MCP writer records this decision with authored topics.\n"
)
MULTI_DECISION_BODY = (
    "### Decisions\n\n"
    "#### D1 - Gate authoring\n\n"
    "- D: Require an authored topic envelope.\n"
    "- R: Every decision needs durable topic coverage.\n\n"
    "#### D2 - Keep imports compatible\n\n"
    "- D: Keep the core append interface permissive.\n"
    "- R: Historical repair must remain possible.\n\n"
    "### Summary\n\n"
    "The MCP boundary is stricter than lower-level repair paths.\n"
)


class MemorySessionAppendTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-mcp-append-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        (self.cwd / MEMORY_DIR_NAME / "sessions").mkdir(parents=True, exist_ok=True)
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

    def _append(self, **overrides):
        args = {
            "cwd": str(self.cwd),
            "title": "Gated append",
            "body": BODY,
            "user_initials": "JNL",
            "agent_type": "claude",
            "auto_branch": False,
            "decisions": [
                {
                    "decision": "d1",
                    "topics": {"area": "schema", "activity": "feature-build"},
                }
            ],
        }
        args.update(overrides)
        return call_tool("memory_session_append", args)

    def _session_files(self):
        return sorted((self.cwd / MEMORY_DIR_NAME / "sessions").rglob("*.md"))

    # --- the happy path -------------------------------------------------

    def test_appends_and_reports_the_canonical_id_and_stamp(self):
        result = self._append(_now="2026-06-13 09:00")

        self.assertTrue(result["ok"])
        self.assertTrue(result["written"])
        self.assertEqual(result["timestamp"], "2026-06-13 09:00")
        self.assertTrue(result["entry_id"].startswith("mse_"))
        self.assertEqual(result["issues"], [])
        written = Path(result["path"]).read_text(encoding="utf-8")
        self.assertIn("## 2026-06-13 09:00 - Gated append", written)
        self.assertIn(result["entry_id"], written)
        self.assertIn("- D: Ship the gated append path.", written)

    def test_lifecycle_edges_arrive_as_arrays_not_csv(self):
        # The target (BODY) is single-decision, so the evolves ref stays BARE -
        # :d1 there is redundant (2026-07-24). related_entries is entry-level
        # by contract regardless.
        first = self._append(title="First", _now="2026-06-13 09:00")
        second = self._append(
            title="Second",
            _now="2026-06-13 10:00",
            decisions=[
                {
                    "decision": "d1",
                    "topics": {"area": "schema", "activity": "feature-build"},
                    "links": {
                        "related_entries": [first["entry_id"]],
                        "evolves": [first["entry_id"]],
                    },
                }
            ],
        )
        self.assertTrue(second["ok"], second["issues"])
        written = "\n".join(
            Path(path).read_text(encoding="utf-8") for path in second["sidecar_paths"]
        )
        self.assertIn(f"related_entries:\n  - d1 -> {first['entry_id']}", written)
        self.assertIn(f"evolves:\n  - d1 -> {first['entry_id']}", written)

    def test_decision_envelope_returns_sidecar_receipt_and_preview(self):
        older = self._append(title="Earlier", _now="2026-06-13 08:00")
        payload = {
            "decisions": [
                {
                    "decision": "d1",
                    "topics": {"area": "schema", "activity": "feature-build"},
                    "links": {"evolves": [older["entry_id"]]},
                }
            ]
        }
        preview = self._append(_now="2026-06-13 09:00", dry_run=True, **payload)

        self.assertTrue(preview["ok"], preview["issues"])
        self.assertEqual(len(preview["sidecar_paths"]), 2)
        self.assertIn("topics", preview["rendered_sidecars"])
        self.assertIn("links", preview["rendered_sidecars"])
        written = self._append(_now="2026-06-13 09:00", **payload)
        self.assertTrue(written["ok"], written["issues"])
        self.assertEqual(len(written["sidecar_paths"]), 2)
        entry = Path(written["path"]).read_text(encoding="utf-8")
        self.assertNotIn("topics:", entry)
        self.assertNotIn("evolves:", entry)

    # --- refusals are data, not transport errors ------------------------

    def test_guard_refusals_come_back_as_issues_not_exceptions(self):
        self._append(title="First", _now="2026-06-13 12:00")
        result = self._append(title="Out of order", _now="2026-06-13 08:00")

        self.assertFalse(result["ok"])
        self.assertFalse(result["written"])
        self.assertTrue(any("chronology conflict" in issue for issue in result["issues"]))

    def test_every_failing_guard_is_reported_together(self):
        # Several independently-fixable problems must all arrive at once; a
        # JSON-RPC error would flatten them into a single unactionable string.
        self._append(title="First", _now="2026-06-13 12:00")
        result = self._append(
            title="Multiply broken",
            _now="2026-06-13 08:00",
            related_entries=["mse_" + "z" * 16],
            body="### Decision\n\n- D: no reason given\n\n### Summary\n\nStill malformed.\n",
        )
        self.assertFalse(result["ok"])
        joined = " ".join(result["issues"])
        self.assertIn("chronology conflict", joined)
        self.assertIn("no such entry_id", joined)
        self.assertIn("body format", joined)

    def test_fabricated_refs_are_refused(self):
        result = self._append(related_entries=["mse_" + "q" * 16])
        self.assertFalse(result["ok"])
        self.assertTrue(any("refs must never be invented" in issue for issue in result["issues"]))

    def test_empty_body_is_refused_before_reaching_core(self):
        # core has no empty-body guard and the format lint passes a blank body,
        # so the surface has to catch it - as the CLI does.
        result = self._append(body="   ")
        self.assertFalse(result["ok"])
        self.assertFalse(result["written"])
        self.assertEqual(self._session_files(), [])

    def test_missing_decisions_are_refused_before_any_write(self):
        args = {
            "cwd": str(self.cwd),
            "title": "Missing envelope",
            "body": BODY,
            "user_initials": "JNL",
            "agent_type": "claude",
            "auto_branch": False,
            "_now": "2026-06-13 09:00",
        }
        result = call_tool("memory_session_append", args)

        self.assertFalse(result["ok"])
        self.assertFalse(result["written"])
        self.assertTrue(any("decisions is required" in issue for issue in result["issues"]))
        self.assertEqual(self._session_files(), [])

    def test_empty_decisions_are_refused_before_any_write(self):
        result = self._append(decisions=[])

        self.assertFalse(result["ok"])
        self.assertFalse(result["written"])
        self.assertTrue(any("decisions is required" in issue for issue in result["issues"]))
        self.assertEqual(self._session_files(), [])

    def test_missing_area_is_refused_before_any_write(self):
        result = self._append(
            decisions=[{"decision": "d1", "topics": {"activity": "feature-build"}}]
        )

        self.assertFalse(result["ok"])
        self.assertFalse(result["written"])
        self.assertTrue(any("topics.area" in issue for issue in result["issues"]))
        self.assertEqual(self._session_files(), [])

    def test_missing_activity_is_refused_before_any_write(self):
        result = self._append(
            decisions=[{"decision": "d1", "topics": {"area": "schema"}}]
        )

        self.assertFalse(result["ok"])
        self.assertFalse(result["written"])
        self.assertTrue(any("topics.activity" in issue for issue in result["issues"]))
        self.assertEqual(self._session_files(), [])

    def test_partial_multi_decision_coverage_is_refused_before_any_write(self):
        result = self._append(
            body=MULTI_DECISION_BODY,
            decisions=[
                {
                    "decision": "d1",
                    "topics": {"area": "schema", "activity": "feature-build"},
                }
            ],
        )

        self.assertFalse(result["ok"])
        self.assertFalse(result["written"])
        self.assertTrue(any("missing d2" in issue for issue in result["issues"]))
        self.assertEqual(self._session_files(), [])

    # --- dry run --------------------------------------------------------

    def test_dry_run_reports_everything_and_writes_nothing(self):
        result = self._append(dry_run=True, _now="2026-06-13 09:00")

        self.assertTrue(result["ok"])
        self.assertFalse(result["written"])
        self.assertTrue(result["entry_id"].startswith("mse_"))
        self.assertEqual(result["timestamp"], "2026-06-13 09:00")
        self.assertTrue(result["path"].endswith("2026-06-13.md"))
        self.assertEqual(self._session_files(), [], "a dry run must not create a session file")
        # The dummy write shows the final output: heading, YAML and body exactly
        # as a real call would append them.
        rendered = result["rendered"]
        self.assertIn("## 2026-06-13 09:00 - Gated append", rendered)
        self.assertIn(f"entry_id: {result['entry_id']}", rendered)
        self.assertIn("- D: Ship the gated append path.", rendered)

    def test_rendered_is_only_returned_on_a_passing_dry_run(self):
        written = self._append(_now="2026-06-13 09:00")
        self.assertNotIn("rendered", written, "a real write must not echo the body back")

        refused = self._append(title="Second", _now="2026-06-13 08:00", dry_run=True)
        self.assertFalse(refused["ok"])
        self.assertNotIn("rendered", refused, "a refused write has no final output to preview")

    def test_dry_run_still_reports_guard_failures(self):
        self._append(title="First", _now="2026-06-13 12:00")
        result = self._append(title="Out of order", _now="2026-06-13 08:00", dry_run=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("chronology conflict" in issue for issue in result["issues"]))

    def test_dry_run_predicts_the_id_the_real_write_produces(self):
        planned = self._append(dry_run=True, _now="2026-06-13 09:00")
        actual = self._append(_now="2026-06-13 09:00")
        self.assertEqual(planned["entry_id"], actual["entry_id"])
        self.assertEqual(planned["path"], actual["path"])

    def test_echoing_the_previewed_timestamp_survives_a_minute_tick(self):
        # The id hashes the timestamp, so a preview at :59 and a write at :01
        # get different server stamps — and would mint different ids. The
        # sanctioned pattern is echoing the previewed timestamp back on the
        # real call, which pins preview and write to the same bytes and earns
        # no drift warning (it is the server's own stamp, one call older).
        planned = self._append(dry_run=True, _now="2026-06-13 09:00")

        committed = self._append(timestamp=planned["timestamp"], _now="2026-06-13 09:01")
        self.assertTrue(committed["ok"], committed["issues"])
        self.assertEqual(committed["entry_id"], planned["entry_id"])
        self.assertEqual(committed["timestamp"], planned["timestamp"])
        self.assertNotIn("clock_drift_warning", committed)
        self.assertIn(planned["entry_id"], Path(committed["path"]).read_text(encoding="utf-8"))

    def test_without_the_echo_a_minute_tick_mints_a_different_id(self):
        # The race the echo exists for, pinned so it stays documented: letting
        # the server stamp afresh across a minute boundary silently diverges
        # from the preview. Nothing corrupts — the write is valid — but the
        # inspected bytes are not the written bytes.
        planned = self._append(dry_run=True, _now="2026-06-13 09:00")
        drifted = self._append(_now="2026-06-13 09:01")
        self.assertTrue(drifted["ok"], drifted["issues"])
        self.assertNotEqual(drifted["entry_id"], planned["entry_id"])

    def test_a_stale_echo_is_refused_when_the_file_moved_on(self):
        # The failure mode of echoing fails LOUDLY, not silently: inspect too
        # long, another entry lands, and the chronology guard refuses the now
        # backdated write instead of slotting it out of order.
        planned = self._append(dry_run=True, _now="2026-06-13 09:00")
        self._append(title="Someone else landed first", _now="2026-06-13 09:02")

        stale = self._append(timestamp=planned["timestamp"], _now="2026-06-13 09:03")
        self.assertFalse(stale["ok"])
        self.assertTrue(any("chronology conflict" in issue for issue in stale["issues"]))

    # --- the cwd hazard MCP introduces ----------------------------------

    def test_a_cwd_with_no_runtime_is_refused_rather_than_created(self):
        # resolve_runtime fails open and the writer mkdirs, so without this
        # guard a wrong cwd would silently grow a phantom corpus - and the
        # id-collision and ref guards would pass vacuously against its empty
        # id set, making the entry look clean.
        empty = Path(tempfile.mkdtemp(prefix="mseed-no-runtime-"))
        self.addCleanup(lambda: shutil.rmtree(empty, ignore_errors=True))

        result = self._append(cwd=str(empty))

        self.assertFalse(result["ok"])
        self.assertFalse(result["written"])
        self.assertTrue(any("no Memory Seed runtime" in issue for issue in result["issues"]))
        self.assertFalse((empty / MEMORY_DIR_NAME).exists(), "must not create a phantom runtime")

    # --- clock discipline inherited from the retired id tool -------------

    def test_the_server_stamps_when_no_timestamp_is_supplied(self):
        result = self._append(_now="2026-06-13 09:00")
        self.assertEqual(result["timestamp"], "2026-06-13 09:00")
        self.assertNotIn("clock_drift_warning", result)

    def test_a_far_off_supplied_timestamp_earns_a_drift_warning(self):
        result = self._append(timestamp="2026-06-13 15:00", _now="2026-06-13 09:00")
        self.assertTrue(result["ok"], result["issues"])
        self.assertIn("clock_drift_warning", result)
        self.assertIn("360 minutes", result["clock_drift_warning"])

    def test_a_close_supplied_timestamp_passes_without_warning(self):
        result = self._append(timestamp="2026-06-13 09:05", _now="2026-06-13 09:00")
        self.assertNotIn("clock_drift_warning", result)

    def test_an_unparseable_supplied_timestamp_is_flagged(self):
        result = self._append(timestamp="sometime this morning", _now="2026-06-13 09:00")
        self.assertFalse(result["ok"])
        self.assertIn("clock_drift_warning", result)


class McpWriteSurfaceTests(unittest.TestCase):
    """The bypass is closed: no tool hands out a target path or a bare id."""

    def test_the_ungated_authoring_tools_are_gone(self):
        names = {tool["name"] for tool in TOOLS}
        self.assertNotIn("memory_session_target", names)
        self.assertNotIn("memory_entry_id", names)
        self.assertIn("memory_session_append", names)

    def test_the_retired_tools_are_not_merely_unlisted(self):
        for name in ("memory_session_target", "memory_entry_id"):
            with self.assertRaises(ValueError):
                call_tool(name, {"cwd": ".", "entry_id": "x", "title": "t", "user_initials": "J", "agent_type": "c"})

    def test_exactly_two_tools_can_write(self):
        # Pins the write surface: authoring an entry, and integrating a branch.
        # Anything else gaining a dry_run flag means a tool grew a write path
        # that this change did not sanction.
        writers = sorted(tool["name"] for tool in TOOLS if "dry_run" in tool["inputSchema"]["properties"])
        self.assertEqual(writers, ["memory_session_append", "memory_session_integrate"])

    def test_append_schema_advertises_the_required_authored_topic_envelope(self):
        append_tool = next(tool for tool in TOOLS if tool["name"] == "memory_session_append")
        schema = append_tool["inputSchema"]
        decision = schema["properties"]["decisions"]
        topics = decision["items"]["properties"]["topics"]

        self.assertIn("decisions", schema["required"])
        self.assertEqual(decision["minItems"], 1)
        self.assertEqual(decision["items"]["required"], ["decision", "topics"])
        self.assertEqual(topics["required"], ["area", "activity"])
        self.assertEqual(topics["properties"]["activity"]["oneOf"][1]["minItems"], 1)


if __name__ == "__main__":
    unittest.main()
