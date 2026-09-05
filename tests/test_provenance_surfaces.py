"""Public CLI/MCP adapters for reference-only progressive provenance."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from memory_seed.cli import provenance_surface
from memory_seed.mcp_server import MUTATING_TOOL_NAMES, call_tool
from memory_seed.provenance import build_runtime_ownership
from memory_seed.provenance_git import derive_commit_bindings


DECISION = "mse_abcd1234:d1"
AUTHORSHIP = {"provenance": "first-hand", "actor": {"kind": "agent", "id": "codex"}}


class ProvenanceSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="memory-seed-provenance-surface-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        (self.root / ".memory-seed" / "sessions" / "2026-09").mkdir(parents=True)
        (self.root / ".memory-seed" / "sessions" / "2026-09" / "2026-09-06.md").write_text(
            "## 2026-09-06 10:00 - provenance surface\n\n```yaml\nentry_id: mse_abcd1234\n```\n\n"
            "### Decision\n\n- D: Bind reference-only code evidence.\n- R: Git owns historical source.\n",
            encoding="utf-8",
        )
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.write_commit("pkg/example.py", "one\ntwo\n", "initial")
        self.head = self.write_commit("pkg/example.py", "one\nTWO\n", "implement")
        self.binding = derive_commit_bindings(
            self.root, self.head, [{"decision_ref": DECISION, "files": ["pkg/example.py"]}], authorship=AUTHORSHIP,
        )["bindings"][0]

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True, text=True).stdout.strip()

    def write_commit(self, path: str, text: str, message: str) -> str:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def test_bind_dry_run_apply_and_show_projection(self) -> None:
        dry = provenance_surface("bind", cwd=self.root, binding=self.binding)
        self.assertTrue(dry["dry_run"])
        self.assertFalse(Path(dry["path"]).exists())
        applied = provenance_surface("bind", cwd=self.root, binding=self.binding, apply=True)
        self.assertTrue(applied["written"])
        text = Path(applied["path"]).read_text(encoding="utf-8")
        self.assertIn("memory-seed-provenance:runtime", text)
        self.assertNotIn("TWO", text)
        shown = provenance_surface("show", cwd=self.root, decision_ref=DECISION, context_lines=0)
        self.assertEqual(shown["decision"]["reason"], "Git owns historical source.")
        self.assertTrue(shown["code_available"])
        self.assertEqual(shown["projections"][0]["context"], {"before": 0, "after": 0})
        self.assertTrue(provenance_surface("check", cwd=self.root)["ok"])

    def test_mcp_bind_dry_run_has_cli_parity_and_exposes_show(self) -> None:
        cli = provenance_surface("bind", cwd=self.root, binding=self.binding)
        mcp = call_tool("memory_decision_provenance_bind", {"cwd": str(self.root), "binding": self.binding})
        self.assertEqual(mcp["binding"], cli["binding"])
        self.assertTrue(mcp["dry_run"])
        call_tool("memory_decision_provenance_bind", {"cwd": str(self.root), "binding": self.binding, "apply": True})
        shown = call_tool("memory_decision_provenance", {"cwd": str(self.root), "decision_ref": DECISION, "context_lines": 1})
        self.assertEqual(shown["context_lines"], 1)
        self.assertTrue(shown["code_available"])
        self.assertIn("memory_decision_provenance_bind", MUTATING_TOOL_NAMES)

    def test_retired_owner_and_descendant_write_are_refused_but_readable(self) -> None:
        retired = build_runtime_ownership(runtime_path=".", owner_kind="pod", owner_id="pod-a", owner_state="retired")
        with self.assertRaisesRegex(ValueError, "retired"):
            provenance_surface("bind", cwd=self.root, binding=self.binding, owner=retired, apply=True)
        descendant = build_runtime_ownership(runtime_path="child", owner_kind="pod", owner_id="pod-a", owner_state="active")
        with self.assertRaisesRegex(ValueError, "descendant"):
            provenance_surface("bind", cwd=self.root, binding=self.binding, owner=descendant, apply=True)
        shown = provenance_surface("show", cwd=self.root, decision_ref=DECISION, owner=retired)
        self.assertEqual(shown["projections"], [])

    def test_context_bound_is_shared_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "0 through 20"):
            provenance_surface("show", cwd=self.root, decision_ref=DECISION, context_lines=21)
        with self.assertRaisesRegex(ValueError, "0 through 20"):
            call_tool("memory_decision_provenance", {"cwd": str(self.root), "decision_ref": DECISION, "context_lines": 21})

