import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import (
    init_project,
)


class HookMergeTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-hooks-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_init_installs_retrieval_hooks_for_all_agents(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        claude = json.loads((cwd / ".claude" / "settings.json").read_text())
        self.assertIn("UserPromptSubmit", claude["hooks"])
        self.assertIn(
            "memory-retrieval-check.py",
            claude["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"],
        )

        codex = json.loads((cwd / ".codex" / "hooks.json").read_text())
        self.assertIn("UserPromptSubmit", codex["hooks"])

        # Gemini's prompt-submit event is BeforeAgent; it has no UserPromptSubmit.
        gemini = json.loads((cwd / ".gemini" / "settings.json").read_text())
        self.assertIn("BeforeAgent", gemini["hooks"])
        self.assertNotIn("UserPromptSubmit", gemini["hooks"])
        self.assertIn(
            "memory-retrieval-check.py",
            gemini["hooks"]["BeforeAgent"][0]["hooks"][0]["command"],
        )

        cursor = json.loads((cwd / ".cursor" / "hooks.json").read_text())
        self.assertIn("sessionStart", cursor["hooks"])
        self.assertIn(
            "memory-retrieval-check.py",
            cursor["hooks"]["sessionStart"][0]["command"],
        )

    def test_gemini_session_log_hook_uses_afteragent_not_stop(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        gemini = json.loads((cwd / ".gemini" / "settings.json").read_text())
        self.assertIn("AfterAgent", gemini["hooks"])
        self.assertNotIn("Stop", gemini["hooks"])
        self.assertIn(
            "session-log-check.py",
            gemini["hooks"]["AfterAgent"][0]["hooks"][0]["command"],
        )

    def test_strip_gemini_dead_hooks_removes_ours_preserves_foreign(self):
        import json
        from memory_seed.core import _strip_gemini_dead_hooks

        cwd = self.make_project()
        settings = cwd / ".gemini" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            json.dumps({
                "hooks": {
                    "Stop": [
                        {"hooks": [{"type": "command", "command": "python3 .memory-seed/hooks/session-log-check.py --gemini"}]},
                        {"hooks": [{"type": "command", "command": "some-foreign-tool"}]},
                    ],
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": "python3 .memory-seed/hooks/memory-retrieval-check.py --gemini"}]},
                    ],
                }
            }),
            encoding="utf-8",
        )

        self.assertTrue(_strip_gemini_dead_hooks(cwd))
        data = json.loads(settings.read_text())
        # Our UserPromptSubmit entry was the only one -> event removed entirely.
        self.assertNotIn("UserPromptSubmit", data["hooks"])
        # Foreign Stop entry preserved; our Stop entry removed.
        stop_cmds = [h["command"] for g in data["hooks"]["Stop"] for h in g["hooks"]]
        self.assertEqual(stop_cmds, ["some-foreign-tool"])
        # Idempotent: nothing of ours left to strip.
        self.assertFalse(_strip_gemini_dead_hooks(cwd))

    def test_retrieval_hook_merges_are_idempotent(self):
        from memory_seed.core import (
            _merge_claude_retrieval_hook,
            _merge_cursor_retrieval_hook,
        )

        cwd = self.make_project()
        self.assertTrue(_merge_claude_retrieval_hook(cwd))
        self.assertFalse(_merge_claude_retrieval_hook(cwd))
        self.assertTrue(_merge_cursor_retrieval_hook(cwd))
        self.assertFalse(_merge_cursor_retrieval_hook(cwd))

    def test_grouped_hook_updates_stale_command(self):
        import json
        from memory_seed.core import _merge_grouped_hook

        cwd = self.make_project()
        config = cwd / ".claude" / "settings.json"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            json.dumps({
                "hooks": {
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": "python3 .memory-seed/hooks/memory-retrieval-check.py --old-flag"}]}
                    ]
                }
            }),
            encoding="utf-8",
        )

        new_command = "python3 .memory-seed/hooks/memory-retrieval-check.py"
        result = _merge_grouped_hook(config, "UserPromptSubmit", new_command, "memory-retrieval-check.py")
        self.assertTrue(result)

        data = json.loads(config.read_text())
        commands = [
            h["command"]
            for g in data["hooks"]["UserPromptSubmit"]
            for h in g.get("hooks", [])
        ]
        self.assertEqual(commands, [new_command])  # updated in place, no duplicate

    def test_cursor_event_hook_updates_stale_command(self):
        import json
        from memory_seed.core import _merge_cursor_event_hook

        cwd = self.make_project()
        config = cwd / ".cursor" / "hooks.json"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            json.dumps({
                "version": 1,
                "hooks": {
                    "sessionStart": [
                        {"command": "python3 .memory-seed/hooks/memory-retrieval-check.py --cursor --old-flag"}
                    ]
                }
            }),
            encoding="utf-8",
        )

        new_command = "python3 .memory-seed/hooks/memory-retrieval-check.py --cursor"
        result = _merge_cursor_event_hook(config, "sessionStart", new_command, "memory-retrieval-check.py")
        self.assertTrue(result)

        data = json.loads(config.read_text())
        commands = [e["command"] for e in data["hooks"]["sessionStart"]]
        self.assertEqual(commands, [new_command])  # updated in place, no duplicate

    def test_init_installs_session_start_hooks_for_all_agents(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        claude = json.loads((cwd / ".claude" / "settings.json").read_text())
        self.assertIn("SessionStart", claude["hooks"])
        self.assertIn(
            "session-start-context.py",
            claude["hooks"]["SessionStart"][0]["hooks"][0]["command"],
        )

        codex = json.loads((cwd / ".codex" / "hooks.json").read_text())
        self.assertIn("SessionStart", codex["hooks"])
        self.assertIn(
            "--codex",
            codex["hooks"]["SessionStart"][0]["hooks"][0]["command"],
        )

        gemini = json.loads((cwd / ".gemini" / "settings.json").read_text())
        self.assertIn("SessionStart", gemini["hooks"])

        # Cursor fires both reminders at sessionStart; both scripts must be present.
        cursor = json.loads((cwd / ".cursor" / "hooks.json").read_text())
        cursor_cmds = [e["command"] for e in cursor["hooks"]["sessionStart"]]
        self.assertTrue(any("session-start-context.py" in c for c in cursor_cmds))
        self.assertTrue(any("memory-retrieval-check.py" in c for c in cursor_cmds))

    def test_init_installs_copilot_mcp_and_command_hooks(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        mcp = json.loads((cwd / ".github" / "mcp.json").read_text())
        server = mcp["mcpServers"]["memory-seed"]
        self.assertEqual(server["type"], "stdio")
        self.assertEqual(server["command"], "uvx")
        self.assertIn("memory-seed-mcp", server["args"])
        self.assertEqual(server["tools"], ["*"])

        hook = json.loads((cwd / ".github" / "hooks" / "memory-seed.json").read_text())
        self.assertEqual(hook["version"], 1)
        startup = hook["hooks"]["sessionStart"]
        self.assertEqual(len(startup), 1)
        self.assertEqual(startup[0]["type"], "command")
        self.assertIn("session-start-context.py --copilot", startup[0]["command"])
        self.assertIn("session-log-check.py --copilot", hook["hooks"]["agentStop"][0]["command"])
        self.assertIn("file-touch-decisions.py --copilot", hook["hooks"]["postToolUse"][0]["command"])

    def test_copilot_hook_upgrade_replaces_our_prompt_and_preserves_foreign_entries(self):
        import json
        from memory_seed.core import _merge_copilot_startup_hook

        cwd = self.make_project()
        path = cwd / ".github" / "hooks" / "memory-seed.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps({
                "version": 1,
                "hooks": {
                    "sessionStart": [
                        {"type": "prompt", "prompt": "memory-seed: old prompt"},
                        {"type": "command", "command": "foreign-start"},
                    ],
                    "agentStop": [{"type": "command", "command": "foreign-stop"}],
                },
            }),
            encoding="utf-8",
        )

        self.assertTrue(_merge_copilot_startup_hook(cwd))
        data = json.loads(path.read_text(encoding="utf-8"))
        startup_commands = [entry.get("command") for entry in data["hooks"]["sessionStart"]]
        self.assertIn("foreign-start", startup_commands)
        self.assertTrue(any("session-start-context.py --copilot" in (cmd or "") for cmd in startup_commands))
        self.assertFalse(any(entry.get("type") == "prompt" and entry.get("prompt", "").startswith("memory-seed:") for entry in data["hooks"]["sessionStart"]))
        self.assertTrue(any(entry.get("command") == "foreign-stop" for entry in data["hooks"]["agentStop"]))

    def test_copilot_hook_uninstall_removes_ours_and_preserves_foreign_entries(self):
        import json
        from memory_seed.core import _merge_copilot_startup_hook, _strip_copilot_startup

        cwd = self.make_project()
        self.assertTrue(_merge_copilot_startup_hook(cwd))
        path = cwd / ".github" / "hooks" / "memory-seed.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["hooks"]["agentStop"].append({"type": "command", "command": "foreign-stop"})
        path.write_text(json.dumps(data), encoding="utf-8")

        self.assertTrue(_strip_copilot_startup(cwd))
        remaining = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            remaining,
            {"version": 1, "hooks": {"agentStop": [{"type": "command", "command": "foreign-stop"}]}},
        )

    def test_copilot_merges_are_idempotent(self):
        from memory_seed.core import _merge_copilot_mcp, _merge_copilot_startup_hook

        cwd = self.make_project()
        self.assertTrue(_merge_copilot_mcp(cwd))
        self.assertFalse(_merge_copilot_mcp(cwd))
        self.assertTrue(_merge_copilot_startup_hook(cwd))
        self.assertFalse(_merge_copilot_startup_hook(cwd))

    def test_copilot_mcp_preserves_foreign_server(self):
        import json
        from memory_seed.core import _merge_copilot_mcp

        cwd = self.make_project()
        mcp_path = cwd / ".github" / "mcp.json"
        mcp_path.parent.mkdir(parents=True, exist_ok=True)
        mcp_path.write_text(
            json.dumps({"mcpServers": {"memory-seed": {"command": "other-tool"}}}),
            encoding="utf-8",
        )

        self.assertFalse(_merge_copilot_mcp(cwd))  # foreign entry left untouched
        data = json.loads(mcp_path.read_text())
        self.assertEqual(data["mcpServers"]["memory-seed"]["command"], "other-tool")

    def test_init_installs_vscode_mcp_under_servers_key(self):
        import json
        from memory_seed.core import _merge_vscode_mcp

        cwd = self.make_project()
        init_project(cwd=cwd)

        mcp = json.loads((cwd / ".vscode" / "mcp.json").read_text())
        # VS Code uses the "servers" key, not "mcpServers".
        self.assertIn("servers", mcp)
        self.assertNotIn("mcpServers", mcp)
        server = mcp["servers"]["memory-seed"]
        self.assertEqual(server["type"], "stdio")
        self.assertEqual(server["command"], "uvx")
        self.assertIn("memory-seed-mcp", server["args"])
        # Idempotent.
        self.assertFalse(_merge_vscode_mcp(cwd))

    def test_init_installs_copilot_instructions_router(self):
        cwd = self.make_project()
        init_project(cwd=cwd)

        router = cwd / ".github" / "copilot-instructions.md"
        self.assertTrue(router.exists())
        text = router.read_text(encoding="utf-8")
        self.assertIn("GitHub Copilot Instructions", text)
        self.assertIn("AGENTS.md", text)
