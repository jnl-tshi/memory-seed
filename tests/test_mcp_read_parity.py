"""Read-only MCP twins must replay the canonical CLI/core evidence exactly."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME
from memory_seed.adr import promote_decision, transition_adr
from memory_seed.cli import main as cli_main
from memory_seed.esr import esr_report
from memory_seed.mcp_server import TOOLS, call_tool, handle_jsonrpc_message
from memory_seed.retrieval import audit_link_gaps, describe_refines_chain, link_audit_payload


ROOT = "mse_aaaaaaaaaaaaaaaa"
HEAD = "mse_bbbbbbbbbbbbbbbb"
GAP = "mse_cccccccccccccccc"


def _entry(timestamp: str, entry_id: str, title: str, *, evolves: str | None = None) -> str:
    lines = [
        f"## {timestamp} - {title}",
        "",
        "```yaml",
        f"entry_id: {entry_id}",
    ]
    if evolves:
        lines.extend(["evolves:", f"  - {evolves} (refines)"])
    lines.extend(
        [
            "```",
            "",
            "### Decision",
            "",
            f"- D: {title} decision.",
            "- R: Shared lifecycle evidence.",
            "",
            "- F: `memory_seed/shared.py`",
            "",
        ]
    )
    return "\n".join(lines)


class McpReadParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-mcp-read-parity-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        sessions = self.cwd / MEMORY_DIR_NAME / "sessions" / "2026-06"
        sessions.mkdir(parents=True)
        (sessions / "2026-06-01.md").write_text(
            _entry("2026-06-01 09:00", ROOT, "Root"), encoding="utf-8"
        )
        (sessions / "2026-06-02.md").write_text(
            _entry("2026-06-02 09:00", HEAD, "Head", evolves=ROOT)
            + _entry("2026-06-02 10:00", GAP, "Gap"),
            encoding="utf-8",
        )
        proposed = promote_decision(
            self.cwd,
            adr_id="adr_mcp_read_parity",
            source_entry_id=HEAD,
            source_decision="d1",
            title="MCP chain parity",
            topics=(),
            user_initials="JN",
            agent_type="codex",
            source="write-time",
            timestamp="2026-06-02T11:00:00Z",
        )
        self.assertTrue(proposed.ok, proposed.issues)
        accepted = transition_adr(
            self.cwd,
            adr_id="adr_mcp_read_parity",
            status="accepted",
            decision_ref=f"{HEAD}:d1",
            update_entry_id=HEAD,
            expected_authoritative_decision=None,
            source="write-time",
            timestamp="2026-06-02T11:01:00Z",
        )
        self.assertTrue(accepted.ok, accepted.issues)

    def _snapshot(self) -> dict[str, bytes]:
        return {
            path.relative_to(self.cwd).as_posix(): path.read_bytes()
            for path in sorted(self.cwd.rglob("*"))
            if path.is_file()
        }

    def _cli_json(self, arguments: list[str]) -> dict[str, object]:
        stdout, stderr = io.StringIO(), io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(self.cwd)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = cli_main(arguments)
        finally:
            os.chdir(previous)
        self.assertEqual(exit_code, 0, stderr.getvalue())
        return json.loads(stdout.getvalue())

    def test_chain_payload_is_the_canonical_chain_view_and_is_read_only(self) -> None:
        before = self._snapshot()
        expected = describe_refines_chain(self.cwd, HEAD)

        actual = call_tool("memory_links_chain", {"ref": HEAD, "cwd": str(self.cwd)})
        self.assertEqual(actual, expected)
        self.assertEqual(self._cli_json(["links", "chain", HEAD, "--json"]), actual)
        self.assertEqual(self._snapshot(), before)
        self.assertEqual(expected["root"], f"{ROOT}:d1")
        self.assertEqual(expected["head"], f"{HEAD}:d1")
        self.assertEqual([member["ref"] for member in expected["members"]], [f"{ROOT}:d1", f"{HEAD}:d1"])
        self.assertEqual(expected["adrs"], [{"adr_id": "adr_mcp_read_parity", "member": f"{HEAD}:d1"}])

    def test_chain_empty_and_unknown_refs_follow_mcp_error_conventions(self) -> None:
        self.assertIsNone(call_tool("memory_links_chain", {"ref": GAP, "cwd": str(self.cwd)}))
        with self.assertRaises(ValueError):
            call_tool("memory_links_chain", {"ref": "mse_zzzzzzzzzzzzzzzz", "cwd": str(self.cwd)})
        response = handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "memory_links_chain", "arguments": {"ref": 3, "cwd": str(self.cwd)}},
            }
        )
        self.assertEqual(response["error"]["code"], -32603)

    def test_audit_payload_reuses_canonical_json_evidence_and_never_applies(self) -> None:
        before = self._snapshot()
        status: dict[str, object] = {}
        gaps = audit_link_gaps(
            cwd=self.cwd,
            entry_id=GAP,
            session_date="2026-06-02",
            top_k=3,
            semantic_enabled=False,
            semantic_status=status,
        )
        expected = link_audit_payload(gaps, status)

        actual = call_tool(
            "memory_link_audit",
            {
                "cwd": str(self.cwd),
                "entry_id": GAP,
                "session_date": "2026-06-02",
                "top_k": 3,
                "semantic_enabled": False,
            },
        )
        self.assertEqual(actual, expected)
        self.assertEqual(
            self._cli_json(
                ["link", "audit", "--for", GAP, "--date", "2026-06-02", "--top-k", "3", "--no-semantic", "--json"]
            ),
            actual,
        )
        self.assertEqual(self._snapshot(), before)
        self.assertEqual(actual["gaps"][0]["entry_id"], GAP)
        self.assertIn("shared_files", actual["gaps"][0]["candidates"][0])

    def test_audit_rejects_bad_filters_and_unknown_targets(self) -> None:
        with self.assertRaises(ValueError):
            call_tool("memory_link_audit", {"cwd": str(self.cwd), "top_k": 0})
        with self.assertRaises(ValueError):
            call_tool("memory_link_audit", {"cwd": str(self.cwd), "session_date": "not-a-date"})
        with self.assertRaises(LookupError):
            call_tool("memory_link_audit", {"cwd": str(self.cwd), "entry_id": "mse_zzzzzzzzzzzzzzzz"})
        with self.assertRaises(ValueError):
            call_tool("memory_link_audit", {"cwd": str(self.cwd), "apply": True})

    def test_esr_payload_is_to_dict_and_read_only(self) -> None:
        before = self._snapshot()
        expected = esr_report(cwd=self.cwd, session_date="2026-06-02").to_dict()
        actual = call_tool("memory_esr", {"cwd": str(self.cwd), "session_date": "2026-06-02"})

        self.assertEqual(actual, expected)
        self.assertEqual(self._cli_json(["esr", "--date", "2026-06-02", "--json"]), actual)
        self.assertEqual(self._snapshot(), before)
        json.dumps(actual, sort_keys=True)

    def test_registry_adds_exactly_three_read_tools_without_changing_writes(self) -> None:
        names = [tool["name"] for tool in TOOLS]
        self.assertEqual(len(names), 23)
        self.assertEqual(
            {tool["name"] for tool in TOOLS if "dry_run" in tool["inputSchema"]["properties"]},
            {
                "memory_session_append",
                "memory_session_integrate",
                "memory_adr_reviewed",
                "memory_link_retract",
            },
        )
        for name in ("memory_links_chain", "memory_link_audit", "memory_esr"):
            tool = next(tool for tool in TOOLS if tool["name"] == name)
            self.assertNotIn("dry_run", tool["inputSchema"]["properties"])
            self.assertTrue(tool["inputSchema"].get("additionalProperties") is False)


if __name__ == "__main__":
    unittest.main()
