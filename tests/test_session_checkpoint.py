import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path


class SessionCheckpointTests(unittest.TestCase):
    def make_project(self, *, initial_text="alpha\n"):
        root = Path(tempfile.mkdtemp(prefix="memory-seed-checkpoint-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        (root / ".memory-seed" / "sessions").mkdir(parents=True)
        (root / "tracked.txt").write_text(initial_text, encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=root, check=True)
        return root

    @staticmethod
    def write_entry(
        root,
        now,
        entry_id="mse_0123456789abcdef",
        title="checkpoint",
        *,
        target_day=None,
    ):
        day = (target_day or now).strftime("%Y-%m-%d")
        target = root / ".memory-seed" / "sessions" / day[:7] / f"{day}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        prior = target.read_text(encoding="utf-8") if target.exists() else ""
        target.write_text(
            prior
            + f"## {now.strftime('%Y-%m-%d %H:%M')} - {title}\n\n"
            + "```yaml\n"
            + f"entry_id: {entry_id}\n"
            + "user_initials: JNL\nagent_type: codex\nproject_path: .\nsubproject_path: null\n"
            + "```\n\n### Summary\n\n- Test entry.\n\n### Validation\n\n- Test.\n",
            encoding="utf-8",
        )
        return target

    @staticmethod
    def commit(root, message):
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, check=True)

    def inspect(self, root, now, *, deliver_clean_advisory=False):
        from memory_seed.session_checkpoint import inspect_checkpoint

        return inspect_checkpoint(
            root,
            now=now,
            deliver_clean_advisory=deliver_clean_advisory,
        )

    def test_clean_initial_baseline_has_no_debt(self):
        now = datetime(2026, 9, 28, 10, 0)
        root = self.make_project()
        self.write_entry(root, now)

        result = self.inspect(root, now)

        self.assertTrue(result["ok"])
        self.assertFalse(result["pending"])
        self.assertEqual(result["evidence_kinds"], [])
        self.assertEqual(result["required_action"], "none")
        state = json.loads((root / ".memory-seed" / ".session-log-check-state").read_text(encoding="utf-8"))
        self.assertEqual(state["schema_version"], 2)
        self.assertTrue(state["baseline_head"])
        self.assertEqual(state["baseline_diff_fingerprint"], "")
        self.assertIsNone(state["pending_checkpoint"])

    def test_init_registers_checkpoint_state_as_ignored_operational_json(self):
        from memory_seed.core import init_project

        root = Path(tempfile.mkdtemp(prefix="memory-seed-checkpoint-init-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))

        init_project(root)

        ignores = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".memory-seed/.session-log-check-state", ignores)

    def test_changed_tracked_and_untracked_work_create_stable_immediate_debt(self):
        now = datetime(2026, 9, 28, 10, 0)
        root = self.make_project()
        self.write_entry(root, now)
        self.inspect(root, now)
        (root / "tracked.txt").write_text("beta\n", encoding="utf-8")
        (root / "new.txt").write_text("new\n", encoding="utf-8")

        first = self.inspect(root, now + timedelta(minutes=1))
        second = self.inspect(root, now + timedelta(minutes=2))

        self.assertTrue(first["pending"])
        self.assertEqual(first["checkpoint_id"], second["checkpoint_id"])
        self.assertEqual(first["evidence_kinds"], ["worktree"])
        self.assertEqual(first["required_action"], "record-session-entry")
        self.assertEqual(first["first_seen"], second["first_seen"])

    def test_changed_head_creates_debt_even_with_clean_tree(self):
        now = datetime(2026, 9, 28, 10, 0)
        root = self.make_project()
        self.write_entry(root, now)
        self.inspect(root, now)
        (root / "tracked.txt").write_text("beta\n", encoding="utf-8")
        self.commit(root, "change head")

        result = self.inspect(root, now + timedelta(minutes=1))

        self.assertTrue(result["pending"])
        self.assertEqual(result["evidence_kinds"], ["head"])

    def test_new_valid_entry_clears_debt_and_rebaselines(self):
        now = datetime(2026, 9, 28, 10, 0)
        root = self.make_project()
        self.write_entry(root, now)
        self.inspect(root, now)
        (root / "tracked.txt").write_text("beta\n", encoding="utf-8")
        pending = self.inspect(root, now + timedelta(minutes=1))
        self.assertTrue(pending["pending"])

        self.write_entry(root, now + timedelta(minutes=2), "mse_fedcba9876543210", "recorded")
        cleared = self.inspect(root, now + timedelta(minutes=2))

        self.assertFalse(cleared["pending"])
        self.assertEqual(cleared["resolution_status"], "cleared-by-new-entry")
        self.assertEqual(cleared["latest_entry_id"], "mse_fedcba9876543210")

    def test_reverting_evidence_does_not_silently_erase_pending_debt(self):
        from memory_seed.session_checkpoint import resolve_checkpoint

        now = datetime(2026, 9, 28, 10, 0)
        root = self.make_project(initial_text="alpha beta\n")
        self.write_entry(root, now)
        self.inspect(root, now)
        (root / "tracked.txt").write_text("semantic change\n", encoding="utf-8")
        first = self.inspect(root, now + timedelta(minutes=1))

        (root / "tracked.txt").write_text("alpha beta\n", encoding="utf-8")
        reverted = self.inspect(root, now + timedelta(minutes=2))

        self.assertTrue(reverted["pending"])
        self.assertEqual(reverted["checkpoint_id"], first["checkpoint_id"])
        resolved = resolve_checkpoint(
            root,
            checkpoint_id=first["checkpoint_id"],
            proof="whitespace-only",
            now=now + timedelta(minutes=3),
        )
        self.assertTrue(resolved["ok"])
        self.assertFalse(resolved["pending"])

    def test_clean_read_only_advisory_is_due_once_per_latest_entry(self):
        now = datetime(2026, 9, 28, 10, 0)
        root = self.make_project()
        self.write_entry(root, now)
        self.inspect(root, now)

        first = self.inspect(root, now + timedelta(minutes=16), deliver_clean_advisory=True)
        second = self.inspect(root, now + timedelta(minutes=17), deliver_clean_advisory=True)

        self.assertFalse(first["pending"])
        self.assertTrue(first["clean_advisory"])
        self.assertEqual(first["required_action"], "self-check-only")
        self.assertFalse(second["clean_advisory"])
        self.assertEqual(second["required_action"], "none")

    def test_corrupt_state_fails_open_without_debt(self):
        now = datetime(2026, 9, 28, 10, 0)
        root = self.make_project()
        self.write_entry(root, now)
        state = root / ".memory-seed" / ".session-log-check-state"
        state.write_text("not json", encoding="utf-8")
        (root / "tracked.txt").write_text("beta\n", encoding="utf-8")

        result = self.inspect(root, now + timedelta(minutes=1))

        self.assertFalse(result["ok"])
        self.assertFalse(result["pending"])
        self.assertIn("state", " ".join(result["issues"]).lower())

    def test_whitespace_only_proof_resolves_from_clean_baseline(self):
        from memory_seed.session_checkpoint import resolve_checkpoint

        now = datetime(2026, 9, 28, 10, 0)
        root = self.make_project(initial_text="alpha beta\n")
        self.write_entry(root, now)
        self.inspect(root, now)
        (root / "tracked.txt").write_text("alpha   beta\n\n", encoding="utf-8")
        pending = self.inspect(root, now + timedelta(minutes=1))

        resolved = resolve_checkpoint(
            root,
            checkpoint_id=pending["checkpoint_id"],
            proof="whitespace-only",
            now=now + timedelta(minutes=2),
        )

        self.assertTrue(resolved["ok"])
        self.assertFalse(resolved["pending"])
        self.assertEqual(resolved["resolution_status"], "mechanical-whitespace-only")
        state = json.loads((root / ".memory-seed" / ".session-log-check-state").read_text(encoding="utf-8"))
        self.assertEqual(state["last_mechanical_resolution"]["checkpoint_id"], pending["checkpoint_id"])

    def test_whitespace_proof_refuses_stale_id_untracked_semantic_and_dirty_baseline(self):
        from memory_seed.session_checkpoint import resolve_checkpoint

        now = datetime(2026, 9, 28, 10, 0)

        stale_root = self.make_project(initial_text="alpha beta\n")
        self.write_entry(stale_root, now)
        self.inspect(stale_root, now)
        (stale_root / "tracked.txt").write_text("alpha  beta\n", encoding="utf-8")
        pending = self.inspect(stale_root, now + timedelta(minutes=1))
        stale = resolve_checkpoint(stale_root, checkpoint_id="msc_stale", proof="whitespace-only", now=now)
        self.assertFalse(stale["ok"])
        self.assertIn("stale", " ".join(stale["issues"]).lower())

        (stale_root / "new.txt").write_text("new\n", encoding="utf-8")
        untracked = self.inspect(stale_root, now + timedelta(minutes=2))
        refused = resolve_checkpoint(
            stale_root, checkpoint_id=untracked["checkpoint_id"], proof="whitespace-only", now=now
        )
        self.assertFalse(refused["ok"])
        self.assertIn("untracked", " ".join(refused["issues"]).lower())

        semantic_root = self.make_project(initial_text="alpha beta\n")
        self.write_entry(semantic_root, now)
        self.inspect(semantic_root, now)
        (semantic_root / "tracked.txt").write_text("gamma\n", encoding="utf-8")
        semantic_pending = self.inspect(semantic_root, now + timedelta(minutes=1))
        semantic = resolve_checkpoint(
            semantic_root,
            checkpoint_id=semantic_pending["checkpoint_id"],
            proof="whitespace-only",
            now=now,
        )
        self.assertFalse(semantic["ok"])
        self.assertIn("semantic", " ".join(semantic["issues"]).lower())

        dirty_root = self.make_project(initial_text="alpha beta\n")
        (dirty_root / "tracked.txt").write_text("alpha  beta\n", encoding="utf-8")
        self.write_entry(dirty_root, now)
        self.inspect(dirty_root, now)
        (dirty_root / "tracked.txt").write_text("alpha   beta\n", encoding="utf-8")
        dirty_pending = self.inspect(dirty_root, now + timedelta(minutes=1))
        dirty = resolve_checkpoint(
            dirty_root, checkpoint_id=dirty_pending["checkpoint_id"], proof="whitespace-only", now=now
        )
        self.assertFalse(dirty["ok"])
        self.assertIn("baseline", " ".join(dirty["issues"]).lower())

    def test_whitespace_proof_refuses_added_deleted_renamed_binary_and_changed_head(self):
        from memory_seed.session_checkpoint import resolve_checkpoint

        now = datetime(2026, 9, 28, 10, 0)

        def refusal(mutate, expected):
            root = self.make_project(initial_text="alpha beta\n")
            self.write_entry(root, now)
            self.inspect(root, now)
            mutate(root)
            pending = self.inspect(root, now + timedelta(minutes=1))
            result = resolve_checkpoint(
                root,
                checkpoint_id=pending["checkpoint_id"],
                proof="whitespace-only",
                now=now + timedelta(minutes=2),
            )
            self.assertFalse(result["ok"])
            self.assertIn(expected, " ".join(result["issues"]).lower())

        refusal(
            lambda root: (
                (root / "added.txt").write_text("added\n", encoding="utf-8"),
                subprocess.run(["git", "add", "added.txt"], cwd=root, check=True),
            ),
            "added",
        )
        refusal(lambda root: (root / "tracked.txt").unlink(), "deleted")
        refusal(
            lambda root: subprocess.run(
                ["git", "mv", "tracked.txt", "renamed.txt"], cwd=root, check=True
            ),
            "renamed",
        )

        binary_root = self.make_project()
        (binary_root / "binary.dat").write_bytes(b"\x00\x01\x02")
        self.commit(binary_root, "add binary")
        self.write_entry(binary_root, now)
        self.inspect(binary_root, now)
        (binary_root / "binary.dat").write_bytes(b"\x00\x03\x04")
        binary_pending = self.inspect(binary_root, now + timedelta(minutes=1))
        binary = resolve_checkpoint(
            binary_root,
            checkpoint_id=binary_pending["checkpoint_id"],
            proof="whitespace-only",
            now=now + timedelta(minutes=2),
        )
        self.assertFalse(binary["ok"])
        self.assertIn("binary", " ".join(binary["issues"]).lower())

        head_root = self.make_project()
        self.write_entry(head_root, now)
        self.inspect(head_root, now)
        (head_root / "tracked.txt").write_text("beta\n", encoding="utf-8")
        self.commit(head_root, "changed head")
        head_pending = self.inspect(head_root, now + timedelta(minutes=1))
        head = resolve_checkpoint(
            head_root,
            checkpoint_id=head_pending["checkpoint_id"],
            proof="whitespace-only",
            now=now + timedelta(minutes=2),
        )
        self.assertFalse(head["ok"])
        self.assertIn("changed head", " ".join(head["issues"]).lower())

    def test_legacy_state_is_migrated_without_inventing_debt(self):
        now = datetime(2026, 9, 28, 10, 0)
        root = self.make_project()
        self.write_entry(root, now)
        state = root / ".memory-seed" / ".session-log-check-state"
        state.write_text(
            json.dumps(
                {
                    "target": ".memory-seed/sessions/2026-09/2026-09-28.md",
                    "last_seen_entry": "2026-09-28 10:00",
                    "consecutive_misses": 4,
                    "baseline_diff_fingerprint": "",
                }
            ),
            encoding="utf-8",
        )

        result = self.inspect(root, now + timedelta(minutes=1))

        self.assertTrue(result["ok"])
        self.assertFalse(result["pending"])
        migrated = json.loads(state.read_text(encoding="utf-8"))
        self.assertEqual(migrated["schema_version"], 2)
        self.assertNotIn("consecutive_misses", migrated)

    def test_cli_and_mcp_share_inspect_and_resolve_shapes(self):
        from memory_seed.cli import main
        from memory_seed.mcp_server import call_tool

        now = datetime.now().replace(second=0, microsecond=0)
        root = self.make_project(initial_text="alpha beta\n")
        self.write_entry(root, now)
        cwd = Path.cwd()
        try:
            os.chdir(root)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["session", "checkpoint", "--json"])
            cli_inspect = json.loads(out.getvalue())
            self.assertEqual(code, 0)
            self.assertFalse(cli_inspect["pending"])

            (root / "tracked.txt").write_text("alpha   beta\n", encoding="utf-8")
            mcp_inspect = call_tool("memory_session_checkpoint", {"cwd": str(root), "mode": "inspect"})
            self.assertTrue(mcp_inspect["pending"])
            checkpoint_id = mcp_inspect["checkpoint_id"]

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(
                    [
                        "session", "checkpoint", "resolve", "--checkpoint-id", checkpoint_id,
                        "--proof", "whitespace-only", "--json",
                    ]
                )
            cli_resolve = json.loads(out.getvalue())
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertTrue(cli_resolve["ok"])
        self.assertEqual(cli_resolve["resolution_status"], "mechanical-whitespace-only")

    def test_mcp_descriptor_exposes_closed_inspect_resolve_contract(self):
        from memory_seed.mcp_server import MUTATING_TOOL_NAMES, TOOLS

        descriptor = next(tool for tool in TOOLS if tool["name"] == "memory_session_checkpoint")
        properties = descriptor["inputSchema"]["properties"]

        self.assertEqual(properties["mode"]["enum"], ["inspect", "resolve"])
        self.assertEqual(properties["proof"]["enum"], ["whitespace-only"])
        self.assertFalse(descriptor["inputSchema"]["additionalProperties"])
        self.assertIn("memory_session_checkpoint", MUTATING_TOOL_NAMES)


class SessionCheckpointHookContractTests(unittest.TestCase):
    SCRIPT = Path("memory_seed/seed/.memory-seed/hooks/session-log-check.py").resolve()
    make_project = SessionCheckpointTests.make_project
    write_entry = staticmethod(SessionCheckpointTests.write_entry)

    def run_hook(self, root, agent, payload=None):
        args = [os.sys.executable, str(self.SCRIPT)]
        if agent != "claude":
            args.append(f"--{agent}")
        completed = subprocess.run(
            args,
            cwd=root,
            input=json.dumps(payload or {}),
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(completed.stdout) if completed.stdout.strip() else None

    def test_pending_debt_uses_every_supported_host_shape(self):
        now = datetime.now().replace(second=0, microsecond=0)
        root = self.make_project()
        self.write_entry(root, now)
        self.run_hook(root, "codex")
        (root / "tracked.txt").write_text("beta\n", encoding="utf-8")

        claude = self.run_hook(root, "claude", {"hook_event_name": "Stop"})
        vscode = self.run_hook(root, "vscode", {"hook_event_name": "Stop"})
        codex = self.run_hook(root, "codex")
        gemini = self.run_hook(root, "gemini")
        cursor = self.run_hook(root, "cursor")
        copilot = self.run_hook(root, "copilot")

        self.assertEqual(claude["decision"], "block")
        self.assertEqual(vscode["hookSpecificOutput"]["decision"], "block")
        self.assertTrue(codex["continue"])
        self.assertIn("SESSION RECORD CHECKPOINT", codex["systemMessage"])
        self.assertIn("additionalContext", gemini["hookSpecificOutput"])
        self.assertIn("agentMessage", cursor)
        self.assertEqual(copilot["decision"], "block")

    def test_clean_advisory_is_non_escalating_and_one_time(self):
        from memory_seed.session_checkpoint import inspect_checkpoint

        moment = datetime.now().replace(second=0, microsecond=0)
        now = moment - timedelta(minutes=16)
        root = self.make_project()
        self.write_entry(root, now, target_day=moment)
        inspect_checkpoint(root, now=moment)

        first = self.run_hook(root, "codex")
        second = self.run_hook(root, "codex")

        self.assertIn("SELF-CHECK", first["systemMessage"])
        self.assertNotIn("debt", first["systemMessage"].lower())
        self.assertIsNone(second)

    def test_clean_advisory_uses_supported_shape_for_every_host(self):
        from memory_seed.session_checkpoint import inspect_checkpoint

        for agent in ("claude", "vscode", "codex", "gemini", "cursor", "copilot"):
            with self.subTest(agent=agent):
                moment = datetime.now().replace(second=0, microsecond=0)
                now = moment - timedelta(minutes=16)
                root = self.make_project()
                self.write_entry(root, now, target_day=moment)
                inspect_checkpoint(root, now=moment)

                data = self.run_hook(root, agent, {"hook_event_name": "Stop"} if agent in {"claude", "vscode"} else {})

                if agent in {"claude", "vscode"}:
                    self.assertEqual(data["decision"], "block")
                    self.assertIn("SELF-CHECK", data["reason"])
                elif agent == "codex":
                    self.assertTrue(data["continue"])
                    self.assertIn("SELF-CHECK", data["systemMessage"])
                elif agent == "gemini":
                    self.assertIn("SELF-CHECK", data["hookSpecificOutput"]["additionalContext"])
                elif agent == "cursor":
                    self.assertIn("SELF-CHECK", data["agentMessage"])
                else:
                    self.assertEqual(data["decision"], "block")
                    self.assertIn("SELF-CHECK", data["reason"])

    def test_live_and_seed_hooks_are_byte_identical(self):
        live = Path(".memory-seed/hooks/session-log-check.py")
        self.assertEqual(live.read_bytes(), self.SCRIPT.read_bytes())


if __name__ == "__main__":
    unittest.main()
