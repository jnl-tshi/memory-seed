"""Public CLI/MCP adapters for reference-only progressive provenance."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
import contextlib
import io
import json
import os
from pathlib import Path

from memory_seed.cli import provenance_audit_all, provenance_surface
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
        with self.assertRaisesRegex(ValueError, "measured nested"):
            provenance_surface("bind", cwd=self.root, binding=self.binding, owner=descendant, apply=True)
        shown = provenance_surface("show", cwd=self.root, decision_ref=DECISION, owner=retired)
        self.assertEqual(shown["projections"], [])

    def test_context_bound_is_shared_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "0 through 20"):
            provenance_surface("show", cwd=self.root, decision_ref=DECISION, context_lines=21)
        with self.assertRaisesRegex(ValueError, "0 through 20"):
            call_tool("memory_decision_provenance", {"cwd": str(self.root), "decision_ref": DECISION, "context_lines": 21})

    def test_cli_and_mcp_check_report_unavailable_git_without_raising(self) -> None:
        provenance_surface("bind", cwd=self.root, binding=self.binding, apply=True)
        nowhere = Path(tempfile.mkdtemp(prefix="memory-seed-provenance-no-git-"))
        self.addCleanup(lambda: shutil.rmtree(nowhere, ignore_errors=True))
        shutil.copytree(self.root / ".memory-seed", nowhere / ".memory-seed")
        for result in (provenance_surface("check", cwd=nowhere), call_tool("memory_decision_provenance_check", {"cwd": str(nowhere)})):
            self.assertFalse(result["ok"])
            self.assertEqual(result["append_only"]["status"], "unverifiable")
            self.assertEqual(result["append_only"]["anchor"], "git-unavailable")
            self.assertEqual(result["reference_audit"][0]["evidence_state"], "git-unavailable")


class MeasuredProvenanceTopologyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="mseed-provenance-topology-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.pod = self.root / "pods" / "pod-a"
        for place, entry_id in ((self.root, "mse_abcd1234"), (self.pod, "mse_dcba4321")):
            path = place / ".memory-seed/sessions/2026-09/2026-09-06.md"
            path.parent.mkdir(parents=True)
            path.write_text(f"## 2026-09-06 10:00 - pod\n\n```yaml\nentry_id: {entry_id}\n```\n\n### Decision\n\n- D: Local decision.\n- R: Local authority.\n", encoding="utf-8")
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        target = self.root / "pkg/example.py"
        target.parent.mkdir(parents=True)
        target.write_text("one\n", encoding="utf-8")
        self.git("add", "-A"); self.git("commit", "-q", "-m", "initial")
        target.write_text("TWO\n", encoding="utf-8")
        self.git("add", "-A"); self.git("commit", "-q", "-m", "implementation")
        self.binding = derive_commit_bindings(self.root, self.git("rev-parse", "HEAD"), [{"decision_ref": "mse_dcba4321:d1", "files": ["pkg/example.py"]}], authorship=AUTHORSHIP)["bindings"][0]
        self.runtime = build_runtime_ownership(runtime_path="pods/pod-a", owner_kind="pod", owner_id="pod-a", owner_state="active")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True, text=True).stdout.strip()

    def test_measurement_missing_decision_and_cli_runtime_file(self) -> None:
        forged = build_runtime_ownership(runtime_path=".", owner_kind="pod", owner_id="pod-a", owner_state="active")
        with self.assertRaisesRegex(ValueError, "measured nested"):
            provenance_surface("bind", cwd=self.root, binding=self.binding, owner=forged, apply=True)
        with self.assertRaisesRegex(ValueError, "cannot append"):
            provenance_surface("bind", cwd=self.root, binding=self.binding, owner=self.runtime, apply=True)
        self.assertTrue(provenance_surface("bind", cwd=self.pod, binding=self.binding, owner=self.runtime, apply=True)["written"])
        missing = derive_commit_bindings(self.root, self.git("rev-parse", "HEAD"), [{"decision_ref": "mse_eeeeeeee:d1", "files": ["pkg/example.py"]}], authorship=AUTHORSHIP)["bindings"][0]
        with self.assertRaisesRegex(ValueError, "does not exist"):
            provenance_surface("bind", cwd=self.pod, binding=missing, owner=self.runtime, apply=True)
        runtime_file = self.root / "runtime.json"; runtime_file.write_text(json.dumps(self.runtime), encoding="utf-8")
        from memory_seed.cli import main
        old_cwd = Path.cwd()
        try:
            os.chdir(self.root)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["provenance", "show", "mse_dcba4321:d1", "--runtime-file", str(runtime_file), "--json"]), 0)
        finally:
            os.chdir(old_cwd)

    def test_committed_tamper_is_violated(self) -> None:
        sidecar = Path(provenance_surface("bind", cwd=self.pod, binding=self.binding, owner=self.runtime, apply=True)["path"])
        self.git("add", sidecar.relative_to(self.root).as_posix()); self.git("commit", "-q", "-m", "anchor")
        sidecar.write_text("", encoding="utf-8")
        check = provenance_surface("check", cwd=self.root, owner=self.runtime)
        self.assertEqual(check["append_only"]["status"], "violated")
        self.assertFalse(provenance_audit_all(self.root)["ok"])
