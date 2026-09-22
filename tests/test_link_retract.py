"""`link retract` / `memory_link_retract`: the writer for the append-only fix.

Retract-and-retype is the mandated correction for three `links check` errors
(`multiple-refines-successors`, `unknown-evolution-type`, `untyped-evolves`) and
every block of it was hand-formatted markdown until this writer existed. The
tests here go THROUGH the command, so they assert what a caller gets: the
refusals that fire before a byte is written, the exact block that lands, and the
effective graph afterwards.
"""

import contextlib
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory_seed.core import (
    MEMORY_DIR_NAME,
    Runtime,
    apply_link_retract,
    check_session_links,
)

OLD = "mse_aaaaaaaaaaaaaaaa"
NEW = "mse_bbbbbbbbbbbbbbbb"
OTHER = "mse_cccccccccccccccc"


class _Fixture:
    """Project scaffolding shared by the core, CLI and MCP suites.

    Deliberately NOT a TestCase: subclassing one would re-run every core test
    inside the CLI and MCP classes.
    """

    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-link-retract-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        (self.cwd / MEMORY_DIR_NAME / "sessions").mkdir(parents=True, exist_ok=True)

    # -- fixtures ---------------------------------------------------------

    def _entry(self, entry_id, ts, *, edges="", decisions=1):
        """One session entry, optionally carrying lifecycle edges in its own YAML."""
        path = self.cwd / MEMORY_DIR_NAME / "sessions" / "2026-06-13.md"
        if decisions == 1:
            body = "### Decision\n\n- D: a call.\n- R: a reason.\n"
        else:
            body = "### Decisions\n\n" + "\n".join(
                f"#### D{n} - call {n}\n\n- D: a call.\n- R: a reason.\n"
                for n in range(1, decisions + 1)
            )
        block = f"## {ts} - entry {entry_id}\n\n```yaml\nentry_id: {entry_id}{edges}\n```\n\n{body}\n"
        path.write_text(
            (path.read_text(encoding="utf-8") if path.exists() else "") + block, encoding="utf-8"
        )

    def _sidecar_path(self, date_str="2026-06-13"):
        return self.cwd / MEMORY_DIR_NAME / "sessions" / "links" / date_str[:7] / f"{date_str}.md"

    def _write_sidecar(self, text, date_str="2026-06-13"):
        path = self._sidecar_path(date_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def _chunks(self):
        from memory_seed.retrieval import augment_chunks_with_link_sidecars
        from memory_seed.semantic_cache import extract_memory_chunks

        return {
            chunk.entry_id: chunk
            for chunk in augment_chunks_with_link_sidecars(
                extract_memory_chunks(self.cwd, granularity="entry"), self.cwd
            )
        }

    def _graph(self):
        from memory_seed.retrieval import augment_chunks_with_link_sidecars
        from memory_seed.semantic_cache import build_related_entry_graph, extract_memory_chunks

        chunks = augment_chunks_with_link_sidecars(
            extract_memory_chunks(self.cwd, granularity="entry"), self.cwd
        )
        return build_related_entry_graph(self.cwd, chunks=chunks)


class LinkRetractTests(_Fixture, unittest.TestCase):
    def test_retract_only_removes_the_edge_from_the_effective_graph(self):
        self._entry(OLD, "2026-06-13 09:00")
        self._entry(NEW, "2026-06-13 10:00", edges=f"\nevolves:\n  - {OLD}")
        self.assertEqual(self._chunks()[NEW].evolves, (OLD,))

        result = apply_link_retract(
            self.cwd, from_entry=NEW, kind="evolves", ref=OLD, timestamp="2026-08-10 12:00"
        )

        self.assertTrue(result.ok, result.issues)
        self.assertTrue(result.written)
        self.assertEqual(result.path, self._sidecar_path())
        self.assertEqual(result.retracted, (f"evolves {OLD}",))
        self.assertIsNone(result.reauthored)
        self.assertEqual(self._chunks()[NEW].evolves, ())
        self.assertEqual(self._graph()[OLD].evolved_by, ())
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_retract_and_retype_keeps_the_edge_and_makes_the_spine_walkable(self):
        # Same guarantee as the hand-written backfill shape, THROUGH the command:
        # the untyped edge goes, the typed one survives, and the lineage walks.
        from memory_seed.semantic_cache import refines_lineage_head

        self._entry(OLD, "2026-06-13 09:00")
        self._entry(NEW, "2026-06-13 10:00", edges=f"\nevolves:\n  - {OLD}")
        before = self._graph()
        self.assertEqual(before[OLD].refined_by, ())
        self.assertEqual(refines_lineage_head(before, OLD), ())

        result = apply_link_retract(
            self.cwd,
            from_entry=NEW,
            kind="evolves",
            ref=OLD,
            retype="refines",
            timestamp="2026-08-10 12:00",
        )

        self.assertTrue(result.ok, result.issues)
        self.assertEqual(result.reauthored, f"{OLD} (refines)")
        self.assertEqual(result.reauthored_key, "evolves")
        after = self._graph()
        self.assertEqual(after[OLD].evolved_by, (NEW,), "retype must not delete the edge")
        self.assertEqual(after[OLD].refined_by, (NEW,))
        self.assertEqual(refines_lineage_head(after, OLD), (NEW,))
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_comma_multi_ordinal_fans_out_to_one_retract_line_per_ordinal(self):
        # `_parse_retract` refuses a retract naming more than one edge, so the
        # comma form MUST fan out - while the re-authored line, which the
        # ordinary ref grammar governs, keeps it.
        self._entry(OLD, "2026-06-13 09:00", decisions=3)
        self._entry(NEW, "2026-06-13 10:00", edges=f"\nevolves:\n  - {OLD}:d1\n  - {OLD}:d3")

        result = apply_link_retract(
            self.cwd,
            from_entry=NEW,
            kind="evolves",
            ref=f"{OLD}:d1,d3",
            retype="refines",
            timestamp="2026-08-10 12:00",
        )

        self.assertTrue(result.ok, result.issues)
        self.assertEqual(result.retracted, (f"evolves {OLD}:d1", f"evolves {OLD}:d3"))
        self.assertEqual(result.reauthored, f"{OLD}:d1,d3 (refines)")
        text = self._sidecar_path().read_text(encoding="utf-8")
        self.assertIn(f"  - evolves {OLD}:d1\n  - evolves {OLD}:d3\n", text)
        self.assertIn(f"  - {OLD}:d1,d3 (refines)\n", text)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_retracting_an_undeclared_edge_is_refused_before_writing(self):
        self._entry(OLD, "2026-06-13 09:00")
        self._entry(NEW, "2026-06-13 10:00", edges=f"\nevolves:\n  - {OLD}")

        result = apply_link_retract(
            self.cwd, from_entry=NEW, kind="replaces", ref=OLD, timestamp="2026-08-10 12:00"
        )

        self.assertFalse(result.ok)
        self.assertFalse(result.written)
        self.assertIsNone(result.path)
        self.assertIn("nothing to retract", result.issues[0])
        self.assertFalse(self._sidecar_path().exists(), "a refusal must not create the sidecar")

    def test_retype_to_refines_is_refused_when_another_entry_holds_the_slot(self):
        # The one-refines-successor cap is what makes a lineage a line. The
        # message must name the holder, or the caller cannot tell what to do.
        self._entry(OLD, "2026-06-13 09:00")
        self._entry(NEW, "2026-06-13 10:00", edges=f"\nevolves:\n  - {OLD}")
        self._entry(OTHER, "2026-06-13 11:00", edges=f"\nevolves:\n  - {OLD} (refines)")

        result = apply_link_retract(
            self.cwd,
            from_entry=NEW,
            kind="evolves",
            ref=OLD,
            retype="refines",
            timestamp="2026-08-10 12:00",
        )

        self.assertFalse(result.ok)
        self.assertFalse(result.written)
        self.assertIn(OTHER, result.issues[0])
        self.assertIn("already refined by", result.issues[0])

    def test_retype_to_refines_is_allowed_when_this_entry_holds_the_slot(self):
        # The holder is the very edge being retracted: this call IS the retype,
        # not a conflict. Refusing here would block every legitimate re-typing.
        self._entry(OLD, "2026-06-13 09:00")
        self._entry(NEW, "2026-06-13 10:00", edges=f"\nevolves:\n  - {OLD} (refines)")

        result = apply_link_retract(
            self.cwd,
            from_entry=NEW,
            kind="evolves",
            ref=f"{OLD} (refines)",
            retype="builds-on",
            timestamp="2026-08-10 12:00",
        )

        self.assertTrue(result.ok, result.issues)
        self.assertEqual(result.retracted, (f"evolves {OLD} (refines)",))
        self.assertEqual(result.reauthored, f"{OLD} (builds-on)")

    def test_appending_preserves_existing_blocks_and_lands_a_fresh_stamp(self):
        # Block identity is (entry_id, heading timestamp), and the writer sorts
        # the whole region stably - so an existing block keeps its position and
        # the correction lands after it, in the same file.
        self._entry(OLD, "2026-06-13 09:00")
        self._entry(NEW, "2026-06-13 10:00")
        self._write_sidecar(
            "---\ntags:\n  - session-log-links\nlink_date: 2026-06-13\n---\n\n"
            f"## 2026-06-13 10:05 - declare\n\n```yaml\nentry_id: {NEW}\nevolves:\n  - {OLD}\n```\n"
        )

        result = apply_link_retract(
            self.cwd,
            from_entry=NEW,
            kind="evolves",
            ref=OLD,
            retype="builds-on",
            timestamp="2026-08-10 12:00",
        )

        self.assertTrue(result.ok, result.issues)
        text = self._sidecar_path().read_text(encoding="utf-8")
        self.assertLess(
            text.index("2026-06-13 10:05 - declare"),
            text.index("2026-08-10 12:00 - edge retracted and retyped"),
            "the existing block keeps its place; the correction appends after it",
        )
        self.assertIn("link_date: 2026-06-13", text)
        self.assertEqual(self._chunks()[NEW].evolves, (OLD,))
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_a_colliding_heading_stamp_is_refused(self):
        # Two blocks for one entry at one minute are indistinguishable to every
        # reader that keys on (entry_id, heading timestamp).
        self._entry(OLD, "2026-06-13 09:00")
        self._entry(NEW, "2026-06-13 10:00", edges=f"\nevolves:\n  - {OLD}")
        apply_link_retract(
            self.cwd, from_entry=NEW, kind="evolves", ref=OLD, timestamp="2026-08-10 12:00"
        )

        again = apply_link_retract(
            self.cwd, from_entry=NEW, kind="evolves", ref=OLD, timestamp="2026-08-10 12:00"
        )

        self.assertFalse(again.ok)
        self.assertIn("heading timestamp", again.issues[0])

    def test_dry_run_renders_the_block_and_writes_nothing(self):
        self._entry(OLD, "2026-06-13 09:00")
        self._entry(NEW, "2026-06-13 10:00", edges=f"\nevolves:\n  - {OLD}")

        result = apply_link_retract(
            self.cwd,
            from_entry=NEW,
            kind="evolves",
            ref=OLD,
            retype="refines",
            note="backfilling the evolution type",
            timestamp="2026-08-10 12:00",
            dry_run=True,
        )

        self.assertTrue(result.ok, result.issues)
        self.assertFalse(result.written)
        self.assertIn("## 2026-08-10 12:00 - edge retracted and retyped", result.rendered)
        self.assertIn(f"entry_id: {NEW}", result.rendered)
        self.assertIn("note: backfilling the evolution type", result.rendered)
        self.assertFalse(self._sidecar_path().exists())
        self.assertEqual(self._chunks()[NEW].evolves, (OLD,), "nothing changed")

    def test_date_pin_must_be_the_declaration_date(self):
        self._entry(OLD, "2026-06-13 09:00")
        self._entry(NEW, "2026-06-13 10:00", edges=f"\nevolves:\n  - {OLD}")

        wrong = apply_link_retract(
            self.cwd,
            from_entry=NEW,
            kind="evolves",
            ref=OLD,
            date_pin="2026-06-01",
            timestamp="2026-08-10 12:00",
        )
        self.assertFalse(wrong.ok)
        self.assertIn("2026-06-13", wrong.issues[0])

        right = apply_link_retract(
            self.cwd,
            from_entry=NEW,
            kind="evolves",
            ref=OLD,
            date_pin="2026-06-13",
            timestamp="2026-08-10 12:00",
        )
        self.assertTrue(right.ok, right.issues)
        self.assertEqual(right.retracted, (f"evolves {OLD} (2026-06-13)",))

    def test_unknown_source_entry_and_malformed_ref_are_refused(self):
        self._entry(OLD, "2026-06-13 09:00")

        missing = apply_link_retract(
            self.cwd, from_entry="mse_dddddddddddddddd", kind="evolves", ref=OLD
        )
        self.assertFalse(missing.ok)
        self.assertIn("no such entry_id", missing.issues[0])

        malformed = apply_link_retract(
            self.cwd, from_entry=OLD, kind="evolves", ref="not a ref at all"
        )
        self.assertFalse(malformed.ok)
        self.assertIn("not an entry id", malformed.issues[0])

        bad_retype = apply_link_retract(
            self.cwd, from_entry=OLD, kind="evolves", ref=OLD, retype="refined"
        )
        self.assertFalse(bad_retype.ok)
        self.assertIn("neither an edge kind", bad_retype.issues[0])


class LinkRetractCliTests(_Fixture, unittest.TestCase):
    def _run(self, argv):
        from memory_seed.cli import main

        out, err = io.StringIO(), io.StringIO()
        previous = os.getcwd()
        os.chdir(self.cwd)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(argv)
        finally:
            os.chdir(previous)
        return code, out.getvalue(), err.getvalue()

    def test_cli_retract_writes_and_reports(self):
        self._entry(OLD, "2026-06-13 09:00")
        self._entry(NEW, "2026-06-13 10:00", edges=f"\nevolves:\n  - {OLD}")

        code, out, err = self._run(
            ["link", "retract", "evolves", OLD, "--from", NEW, "--retype", "refines"]
        )

        self.assertEqual(code, 0, err)
        self.assertIn(f"Retracted {NEW}: evolves {OLD}", out)
        self.assertIn(f"Re-authored under evolves: {OLD} (refines)", out)
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

    def test_cli_refusal_exits_nonzero_and_writes_nothing(self):
        self._entry(OLD, "2026-06-13 09:00")
        self._entry(NEW, "2026-06-13 10:00", edges=f"\nevolves:\n  - {OLD}")

        code, _out, err = self._run(["link", "retract", "replaces", OLD, "--from", NEW])

        self.assertEqual(code, 1)
        self.assertIn("nothing was written", err)
        self.assertFalse(self._sidecar_path().exists())

    def test_cli_dry_run_prints_the_block(self):
        self._entry(OLD, "2026-06-13 09:00")
        self._entry(NEW, "2026-06-13 10:00", edges=f"\nevolves:\n  - {OLD}")

        code, out, err = self._run(
            ["link", "retract", "evolves", OLD, "--from", NEW, "--dry-run"]
        )

        self.assertEqual(code, 0, err)
        self.assertIn("Would append to", out)
        self.assertIn("retracts:", out)
        self.assertFalse(self._sidecar_path().exists())


class LinkRetractMcpTests(_Fixture, unittest.TestCase):
    def test_the_tool_is_registered_with_the_write_shape(self):
        from memory_seed.mcp_server import TOOLS

        tool = next(item for item in TOOLS if item["name"] == "memory_link_retract")
        schema = tool["inputSchema"]
        self.assertEqual(schema["required"], ["from_entry", "kind", "ref"])
        for key in ("retype", "note", "date_pin", "timestamp", "dry_run", "cwd"):
            self.assertIn(key, schema["properties"])
        self.assertIn("evolves", schema["properties"]["kind"]["enum"])

    def test_dispatch_writes_and_reports_the_append_shape(self):
        from memory_seed.mcp_server import call_tool

        self._entry(OLD, "2026-06-13 09:00")
        self._entry(NEW, "2026-06-13 10:00", edges=f"\nevolves:\n  - {OLD}")

        result = call_tool(
            "memory_link_retract",
            {
                "cwd": str(self.cwd),
                "from_entry": NEW,
                "kind": "evolves",
                "ref": OLD,
                "retype": "refines",
                "timestamp": "2026-08-10 12:00",
            },
        )

        self.assertTrue(result["ok"], result["issues"])
        self.assertTrue(result["written"])
        self.assertEqual(result["entry_id"], NEW)
        self.assertEqual(result["retracted"], [f"evolves {OLD}"])
        self.assertEqual(result["reauthored"], f"{OLD} (refines)")
        self.assertEqual(result["reauthored_key"], "evolves")
        self.assertEqual(Path(result["path"]), self._sidecar_path())
        self.assertEqual(self._graph()[OLD].refined_by, (NEW,))

    def test_dispatch_dry_run_and_refusal_write_nothing(self):
        from memory_seed.mcp_server import call_tool

        self._entry(OLD, "2026-06-13 09:00")
        self._entry(NEW, "2026-06-13 10:00", edges=f"\nevolves:\n  - {OLD}")

        preview = call_tool(
            "memory_link_retract",
            {"cwd": str(self.cwd), "from_entry": NEW, "kind": "evolves", "ref": OLD, "dry_run": True},
        )
        self.assertTrue(preview["ok"])
        self.assertFalse(preview["written"])
        self.assertIn("retracts:", preview["rendered"])

        refused = call_tool(
            "memory_link_retract",
            {"cwd": str(self.cwd), "from_entry": NEW, "kind": "replaces", "ref": OLD},
        )
        self.assertFalse(refused["ok"])
        self.assertFalse(refused["written"])
        self.assertTrue(refused["issues"])
        self.assertFalse(self._sidecar_path().exists())

    def test_dispatch_refuses_a_cwd_with_no_runtime(self):
        from memory_seed.mcp_server import call_tool

        empty = Path(tempfile.mkdtemp(prefix="mseed-no-runtime-"))
        self.addCleanup(lambda: shutil.rmtree(empty, ignore_errors=True))

        # Keep this guard test independent of legacy runtimes in a developer's
        # home directory (which can be an ancestor of the system temp dir).
        runtime = Runtime(workspace_root=empty, memory_dir=empty / MEMORY_DIR_NAME)
        with patch("memory_seed.mcp_server.resolve_runtime", return_value=runtime):
            result = call_tool(
                "memory_link_retract",
                {"cwd": str(empty), "from_entry": NEW, "kind": "evolves", "ref": OLD},
            )

        self.assertFalse(result["ok"])
        self.assertIn("no Memory Seed runtime", result["issues"][0])
        self.assertFalse((empty / MEMORY_DIR_NAME).exists())


if __name__ == "__main__":
    unittest.main()
