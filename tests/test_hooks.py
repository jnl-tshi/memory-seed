"""Task Packet commit-hook provenance and ordinary-entry cadence contracts."""

import shutil
import subprocess
import tempfile
import unittest
import hashlib
import json
from pathlib import Path

from memory_seed.core import MEMORY_DIR_NAME, PACKAGE_ROOT, install_git_hooks
from memory_seed.task_packet import activate_task_packet, compile_task_packet


HOOK_SCRIPT = PACKAGE_ROOT / "seed" / MEMORY_DIR_NAME / "hooks" / "prepare-commit-msg.py"


def _entry(index: int) -> str:
    entry_id = f"mse_{index:016x}"
    return (
        f"## 2026-09-05 {index % 24:02d}:00 - entry {index}\n\n"
        f"```yaml\nentry_id: {entry_id}\n```\n\n- authored now\n\n"
    )


class CommitHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="mseed-provenance-hook-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Hook Test")
        self.git("config", "user.email", "hook@example.com")
        (self.root / "docs").mkdir()
        (self.root / "docs" / "CONSTITUTION.md").write_text(
            "# Constitution\n\n**Version:** 1.0 — **RATIFIED 2026-09-05**\n\n"
            "## Invariant\n\nMarkdown is authoritative.\n",
            encoding="utf-8",
        )
        (self.root / "docs" / "evidence.md").write_text("# Evidence\n\nExact slice.\n", encoding="utf-8")
        agent_rules = self.root / MEMORY_DIR_NAME / "agent-rules.md"
        agent_rules.parent.mkdir(parents=True)
        agent_rules.write_text(
            "# Active agent rules\n\nGovern every worker.\n", encoding="utf-8"
        )
        profile = self.root / MEMORY_DIR_NAME / "retrieval-profiles" / "implementation"
        profile.mkdir(parents=True)
        (profile / "v1.yaml").write_text(
            "schema: memory-seed/retrieval-profile\n"
            "schema_version: 1\nid: implementation\nprofile_version: 1\nextends: []\n"
            "spec:\n  selectors:\n    path_references: true\n  filters:\n    paths:\n      - docs/evidence.md\n"
            "  output:\n    include_excerpts: true\n  limits:\n    max_entries: 20\n    max_tokens: 12000\n",
            encoding="utf-8",
        )
        session = self.root / MEMORY_DIR_NAME / "sessions" / "2026-09" / "2026-09-04.md"
        session.parent.mkdir(parents=True)
        session.write_text(
            "## 2026-09-04 09:00 - Packet decision\n\n"
            "```yaml\nentry_id: mse_aaaaaaaaaaaaaaaa\nuser_initials: JN\n"
            "agent_type: codex\nproject_path: .\nsubproject_path: null\n```\n\n"
            "### Decision\n\n- D: Stamp exact refs.\n- R: Packet evidence is explicit.\n"
            "- F: `docs/evidence.md`.\n",
            encoding="utf-8",
        )
        hook_dir = self.root / MEMORY_DIR_NAME / "hooks"
        hook_dir.mkdir(parents=True)
        shutil.copyfile(HOOK_SCRIPT, hook_dir / "prepare-commit-msg.py")
        install_git_hooks(self.root)
        (self.root / "base.txt").write_text("base\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "base")

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=check,
            text=True,
            capture_output=True,
        )

    def last_message(self) -> str:
        return self.git("log", "-1", "--format=%B").stdout

    def activate_compiled_packet(
        self, *, allowed_files: list[str], implements: list[str], packet_version: int = 1
    ) -> dict:
        base = self.git("rev-parse", "HEAD").stdout.strip()
        context = " ".join(["grounded"] * 15)
        dispatch = {
            "schema": "memory-seed/task-dispatch",
            "version": 1,
            "objective": "Create a hook activation test packet.",
            "constitution_refs": [],
            "project_context": {
                "project_type_and_purpose": context,
                "relevant_subsystem": context,
                "task_fit": context,
                "downstream_use": context,
                "non_goals": ["Do not expand test authority."],
            },
            "execution": {
                "role": "worker",
                "persona": None,
                "capability_tier": "balanced",
                "write_intent": "writing",
                "allowed_files": allowed_files,
                "forbidden_files": [".memory-seed/policy.md"],
                "validation": ["python -m unittest tests.test_hooks"],
                "output_contract": ["Return hook validation."],
                "expected_absent": [],
                "acceptance_observables": [
                    {"name": "hook-tests", "command": "python -m unittest tests.test_hooks", "expected_exit_code": 0}
                ],
                "implements": implements,
            },
            "retrieval": {"profile": "implementation", "profile_version": 1, "overrides": {}},
            "budget": {
                "supplemental_input_tokens": 1000,
                "output_tokens": 2000,
                "over_soft_cap": "fail",
                "over_soft_cap_reason": None,
            },
        }
        binding = {
            "owner": "hook-test",
            "agent_type": "codex",
            "base_branch": "main",
            "base_sha": base,
            "working_branch": "main",
            "worktree": str(self.root),
            "expected_directory": str(self.root),
            "integration_artifact": "branch",
        }
        if packet_version == 2:
            dispatch["packet_version"] = 2
            orientation = self.root / MEMORY_DIR_NAME / "skills" / "subagent_orientation.md"
            orientation.parent.mkdir(parents=True, exist_ok=True)
            orientation.write_text("# Subagent Orientation (Lite)\n\nVerify scope.\n", encoding="utf-8")
        packet = compile_task_packet(dispatch, binding, self.root)
        return activate_task_packet(packet, self.root)

    def write_skeletal_artifact(self, *, allowed_files: list[str], implements: list[str]) -> None:
        """A self-hashed hand-authored artifact must never earn trailers."""
        base = self.git("rev-parse", "HEAD").stdout.strip()
        packet = {"packet_schema": "memory-seed/task-packet", "packet_version": 1, "dispatch": {"execution": {"write_intent": "writing", "implements": implements, "allowed_files": allowed_files}}, "runtime_binding": {"working_branch": "main", "worktree": str(self.root), "base_sha": base}, "materialized_evidence": [{"id": reference, "kind": "decision"} for reference in implements]}
        packet["fingerprint"] = "sha256:" + hashlib.sha256(json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
        payload = {"schema": "memory-seed/task-packet-activation", "version": 1, "packet": packet}
        token = hashlib.sha256(b"main").hexdigest()
        target = self.root / ".git" / "memory-seed" / "task-packets" / f"{token}.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")

    def test_config_alone_cannot_masquerade_as_packet_activation(self) -> None:
        key = "branch.main.memory-seed-task-packet-implements"
        self.git("config", "--local", "--add", key, "mse_aaaaaaaaaaaaaaaa:d2")
        (self.root / "change.txt").write_text("implementation\n", encoding="utf-8")
        self.git("add", "change.txt")
        self.git("commit", "-m", "feat: packet implementation")

        message = self.last_message()
        self.assertNotIn("Memory-Implements:", message)
        self.assertNotIn("Memory-Entry:", message)

    def test_compiler_activated_packet_stamps_exact_implements_without_history_lookup(self) -> None:
        reference = "mse_aaaaaaaaaaaaaaaa:d1"
        self.activate_compiled_packet(allowed_files=["change.txt"], implements=[reference])
        (self.root / "change.txt").write_text("implementation\n", encoding="utf-8")
        self.git("add", "change.txt")
        self.git("commit", "-m", "feat: packet implementation")

        self.assertIn(f"Memory-Implements: {reference}", self.last_message())

    def test_packet_v2_activation_stamps_exact_implements(self) -> None:
        reference = "mse_aaaaaaaaaaaaaaaa:d1"
        self.activate_compiled_packet(allowed_files=["change.txt"], implements=[reference], packet_version=2)
        (self.root / "change.txt").write_text("implementation\n", encoding="utf-8")
        self.git("add", "change.txt")
        self.git("commit", "-m", "feat: packet v2 implementation")

        self.assertIn(f"Memory-Implements: {reference}", self.last_message())

    def test_explicit_packet_version_one_in_dispatch_cannot_stamp_implements(self) -> None:
        reference = "mse_aaaaaaaaaaaaaaaa:d1"
        activation = self.activate_compiled_packet(allowed_files=["change.txt"], implements=[reference])
        artifact = Path(activation["activation_artifact"])
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        packet = payload["packet"]
        packet["dispatch"]["packet_version"] = 1
        packet["dispatch_fingerprint"] = "sha256:" + hashlib.sha256(json.dumps(
            packet["dispatch"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
        identity = {key: value for key, value in packet.items() if key != "fingerprint"}
        packet["fingerprint"] = "sha256:" + hashlib.sha256(json.dumps(
            identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
        payload["receipt"]["packet_fingerprint"] = packet["fingerprint"]
        payload["receipt"]["dispatch_fingerprint"] = packet["dispatch_fingerprint"]
        artifact.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
        (self.root / "change.txt").write_text("implementation\n", encoding="utf-8")
        self.git("add", "change.txt")
        self.git("commit", "-m", "feat: explicit v1 dispatch")

        self.assertNotIn("Memory-Implements:", self.last_message())

    def test_packet_v2_with_tampered_orientation_cannot_stamp_implements(self) -> None:
        reference = "mse_aaaaaaaaaaaaaaaa:d1"
        activation = self.activate_compiled_packet(
            allowed_files=["change.txt"], implements=[reference], packet_version=2)
        artifact = Path(activation["activation_artifact"])
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        packet = payload["packet"]
        packet["worker_orientation"]["content"] = "# Rewritten rules\n"
        identity = {key: value for key, value in packet.items() if key != "fingerprint"}
        packet["fingerprint"] = "sha256:" + hashlib.sha256(json.dumps(
            identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
        payload["receipt"]["packet_fingerprint"] = packet["fingerprint"]
        artifact.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
        (self.root / "change.txt").write_text("implementation\n", encoding="utf-8")
        self.git("add", "change.txt")
        self.git("commit", "-m", "feat: tampered orientation")

        self.assertNotIn("Memory-Implements:", self.last_message())

    def test_skeletal_self_hashed_artifact_cannot_stamp_implements(self) -> None:
        reference = "mse_aaaaaaaaaaaaaaaa:d1"
        self.write_skeletal_artifact(allowed_files=["change.txt"], implements=[reference])
        (self.root / "change.txt").write_text("implementation\n", encoding="utf-8")
        self.git("add", "change.txt")
        self.git("commit", "-m", "feat: skeletal artifact")

        self.assertNotIn("Memory-Implements:", self.last_message())

    def test_tampered_compiler_receipt_cannot_stamp_implements(self) -> None:
        reference = "mse_aaaaaaaaaaaaaaaa:d1"
        activation = self.activate_compiled_packet(allowed_files=["change.txt"], implements=[reference])
        artifact = Path(activation["activation_artifact"])
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        payload["receipt"]["objective"] = "tampered"
        artifact.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
        (self.root / "change.txt").write_text("implementation\n", encoding="utf-8")
        self.git("add", "change.txt")
        self.git("commit", "-m", "feat: tampered artifact")

        self.assertNotIn("Memory-Implements:", self.last_message())

    def test_eleventh_new_entry_refuses_without_a_durable_bulk_reason(self) -> None:
        sessions = self.root / MEMORY_DIR_NAME / "sessions" / "2026-09"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-09-05.md").write_text(
            "".join(_entry(index) for index in range(11)), encoding="utf-8"
        )
        self.git("add", "-A")

        rejected = self.git("commit", "-m", "docs: bulk entries", check=False)

        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("more than 10 newly authored", rejected.stderr)
        self.git(
            "commit",
            "-m",
            "docs: approved bulk entries\n\nMemory-Bulk-Reason: User approved migration checkpoint.",
        )
        message = self.last_message()
        self.assertEqual(message.count("Memory-Entry:"), 11)
        self.assertIn("Memory-Bulk-Reason: User approved migration checkpoint.", message)

    def test_duplicate_new_entry_records_still_count_toward_the_cap(self) -> None:
        sessions = self.root / MEMORY_DIR_NAME / "sessions" / "2026-09"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-09-05.md").write_text(_entry(0) * 11, encoding="utf-8")
        self.git("add", "-A")

        rejected = self.git("commit", "-m", "docs: duplicate bulk entries", check=False)

        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("more than 10 newly authored", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
