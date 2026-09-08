"""Read-only MCP twins must replay the canonical CLI/core evidence exactly."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory_seed.adr import promote_decision, transition_adr
from memory_seed.cli import main as cli_main
from memory_seed.core import MEMORY_DIR_NAME
from memory_seed.corpus_cache import get_corpus_snapshot
from memory_seed.esr import esr_report
from memory_seed.mcp_server import MUTATING_TOOL_NAMES, TOOLS, call_tool, handle_jsonrpc_message
from memory_seed.retrieval import audit_link_gaps, describe_refines_chain, link_audit_payload


ROOT = "mse_aaaaaaaaaaaaaaaa"
HEAD = "mse_bbbbbbbbbbbbbbbb"
GAP = "mse_cccccccccccccccc"
MULTI = "mse_dddddddddddddddd"


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


def _multi_entry(timestamp: str, entry_id: str) -> str:
    return "\n".join(
        [
            f"## {timestamp} - Multiple decisions",
            "",
            "```yaml",
            f"entry_id: {entry_id}",
            "```",
            "",
            "### Decisions",
            "",
            "#### D1 - First",
            "",
            "- D: First decision.",
            "- R: First reason.",
            "",
            "#### D2 - Second",
            "",
            "- D: Second decision.",
            "- R: Second reason.",
            "",
        ]
    )


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
            + _entry("2026-06-02 10:00", GAP, "Gap")
            + _multi_entry("2026-06-02 11:00", MULTI),
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
        self.cache_dir = self.cwd.parent / f"{self.cwd.name}-cache"
        self._cache_env = patch.dict(
            os.environ, {"MEMORY_SEED_CORPUS_CACHE_DIR": str(self.cache_dir)}, clear=False
        )
        self._cache_env.start()
        self.addCleanup(self._cache_env.stop)
        self._git("init", "-q")
        self._git("config", "user.name", "Test User")
        self._git("config", "user.email", "test@example.com")
        self._git("add", ".")
        self._git("commit", "-qm", "fixture")

    def _git(self, *arguments: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.cwd), *arguments], check=True, capture_output=True, text=True
        ).stdout.strip()

    def _snapshot(self) -> dict[str, bytes]:
        return {
            path.relative_to(self.cwd).as_posix(): path.read_bytes()
            for path in sorted(self.cwd.rglob("*"))
            if path.is_file()
        }

    @staticmethod
    def _tree_snapshot(root: Path) -> tuple[tuple[object, ...], ...]:
        if not root.exists():
            return (("missing",),)
        result: list[tuple[object, ...]] = []
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            stat = path.stat()
            if path.is_dir():
                result.append(("dir", relative, stat.st_mtime_ns))
            else:
                result.append(("file", relative, path.read_bytes(), stat.st_mtime_ns))
        return tuple(result)

    def _git_snapshot(self) -> tuple[str, str]:
        return self._git("rev-parse", "HEAD"), self._git("status", "--porcelain")

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

    def _cli_result(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(self.cwd)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = cli_main(arguments)
        finally:
            os.chdir(previous)
        return exit_code, stdout.getvalue(), stderr.getvalue()

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

    def test_chain_empty_unknown_and_invalid_refs_match_cli_semantics(self) -> None:
        for ref in (GAP, "mse_zzzzzzzzzzzzzzzz", f"{HEAD}:d99", f"{HEAD}:invalid", MULTI, f"{MULTI}:d99"):
            self.assertIsNone(call_tool("memory_links_chain", {"ref": ref, "cwd": str(self.cwd)}), ref)
            exit_code, stdout, stderr = self._cli_result(["links", "chain", ref, "--json"])
            self.assertEqual(exit_code, 0, stderr)
            self.assertEqual(stdout, f"{ref}: not part of any refines chain (no refines predecessor or successor).\n")
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
        cli_payload = self._cli_json(
            ["link", "audit", "--for", GAP, "--date", "2026-06-02", "--top-k", "3", "--no-semantic", "--json"]
        )
        self.assertEqual(cli_payload, actual)
        self.assertEqual(
            actual["criteria"]["none"],
            "no genuine lifecycle or relatedness link — a shared file or topic is not itself a link",
        )
        self.assertEqual(
            cli_payload["criteria"]["none"].encode("utf-8"),
            b"no genuine lifecycle or relatedness link \xe2\x80\x94 a shared file or topic is not itself a link",
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

    def test_audit_empty_and_semantic_fallback_status_match_core_and_cli(self) -> None:
        empty_status: dict[str, object] = {}
        expected_empty = link_audit_payload(
            audit_link_gaps(self.cwd, entry_id=ROOT, semantic_enabled=False, semantic_status=empty_status),
            empty_status,
        )
        self.assertEqual(
            call_tool("memory_link_audit", {"cwd": str(self.cwd), "entry_id": ROOT, "semantic_enabled": False}),
            expected_empty,
        )
        with patch("memory_seed.retrieval.resolve_semantic_provider", return_value=(None, None, "offline")):
            status: dict[str, object] = {}
            expected = link_audit_payload(
                audit_link_gaps(self.cwd, entry_id=GAP, semantic_status=status), status
            )
            actual = call_tool("memory_link_audit", {"cwd": str(self.cwd), "entry_id": GAP})
        self.assertEqual(actual, expected)
        self.assertTrue(actual["semantic"]["requested"])
        self.assertFalse(actual["semantic"]["active"])
        self.assertEqual(actual["semantic"]["fallback_reason"], "offline")

    def test_esr_payload_is_to_dict_and_preserves_current_and_corrupt_cache(self) -> None:
        get_corpus_snapshot(self.cwd)
        artifact = next(self.cache_dir.glob("*.json"))
        for expected_health in ("current", "corrupt"):
            if expected_health == "corrupt":
                artifact.write_text("{bad json", encoding="utf-8")
            before_source, before_git, before_cache = self._snapshot(), self._git_snapshot(), self._tree_snapshot(self.cache_dir)
            expected = esr_report(cwd=self.cwd, session_date="2026-06-02").to_dict()
            actual = call_tool("memory_esr", {"cwd": str(self.cwd), "session_date": "2026-06-02"})

            self.assertEqual(actual, expected)
            self.assertEqual(actual["corpus_cache"]["health"], expected_health)
            self.assertEqual(self._snapshot(), before_source)
            self.assertEqual(self._git_snapshot(), before_git)
            self.assertEqual(self._tree_snapshot(self.cache_dir), before_cache)
            json.dumps(actual, sort_keys=True)

    def test_esr_missing_cache_does_not_create_its_external_cache_directory(self) -> None:
        missing = self.cwd.parent / "missing-cache"
        with patch.dict(os.environ, {"MEMORY_SEED_CORPUS_CACHE_DIR": str(missing)}, clear=False):
            payload = call_tool("memory_esr", {"cwd": str(self.cwd), "session_date": "2026-06-02"})
        self.assertEqual(payload["corpus_cache"]["health"], "missing")
        self.assertFalse(missing.exists())

    def test_registry_preserves_read_write_classification(self) -> None:
        names = [tool["name"] for tool in TOOLS]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(
            MUTATING_TOOL_NAMES,
            {
                "memory_session_append",
                "memory_session_integrate",
                "memory_adr_reviewed",
                "memory_link_retract",
                "memory_decision_provenance_bind",
                "memory_reflection_ledger_init",
                "memory_reflection_ledger_append",
                "memory_reflection_ledger_close",
                "memory_reflection_ledger_rebind",
                "memory_reflection_ledger_finalize",
                "memory_reflection_ledger_expire",
            },
        )
        self.assertTrue(MUTATING_TOOL_NAMES <= set(names))
        for name in (
            "memory_links_chain",
            "memory_link_audit",
            "memory_esr",
            "memory_task_packet_preview",
            "memory_task_packet_compile",
            "memory_reflection_board_view",
            "memory_reflection_ledger_view",
            "memory_reflection_ledger_check",
        ):
            self.assertNotIn(name, MUTATING_TOOL_NAMES)
            tool = next(tool for tool in TOOLS if tool["name"] == name)
            self.assertNotIn("dry_run", tool["inputSchema"]["properties"])
            self.assertTrue(tool["inputSchema"].get("additionalProperties") is False)


if __name__ == "__main__":
    unittest.main()
