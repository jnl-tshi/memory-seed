import shutil
import tempfile
import tomllib
import unittest
import pytest
from pathlib import Path

from memory_seed.core import (
    MEMORY_DIR_NAME,
    doctor,
    init_project,
)


class McpMergeTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-mcp-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_init_installs_mcp_for_claude(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        # Claude Code reads project-scope MCP servers from .mcp.json, not settings.json.
        data = json.loads((cwd / ".mcp.json").read_text())
        self.assertIn("memory-seed", data["mcpServers"])
        entry = data["mcpServers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])
        self.assertNotIn("type", entry)

        # The dead settings.json mcpServers block must not be created.
        settings = json.loads((cwd / ".claude" / "settings.json").read_text())
        self.assertNotIn("mcpServers", settings)

    def test_init_installs_mcp_for_cursor(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        data = json.loads((cwd / ".cursor" / "mcp.json").read_text())
        self.assertIn("memory-seed", data["mcpServers"])
        entry = data["mcpServers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])
        self.assertNotIn("type", entry)

    def test_init_installs_mcp_for_gemini(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        data = json.loads((cwd / ".gemini" / "settings.json").read_text())
        self.assertIn("memory-seed", data["mcpServers"])
        entry = data["mcpServers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])

    def test_mcp_merges_are_idempotent(self):
        from memory_seed.core import (
            _merge_claude_mcp,
            _merge_cursor_mcp,
            _merge_gemini_mcp,
            _merge_codex_mcp,
        )

        cwd = self.make_project()
        self.assertTrue(_merge_claude_mcp(cwd))
        self.assertFalse(_merge_claude_mcp(cwd))
        self.assertTrue(_merge_cursor_mcp(cwd))
        self.assertFalse(_merge_cursor_mcp(cwd))
        self.assertTrue(_merge_gemini_mcp(cwd))
        self.assertFalse(_merge_gemini_mcp(cwd))
        self.assertTrue(_merge_codex_mcp(cwd))
        self.assertFalse(_merge_codex_mcp(cwd))

    def test_mcp_merge_updates_stale_args(self):
        import json

        cwd = self.make_project()
        mcp_path = cwd / ".mcp.json"
        # Legacy bare-command form (pre-uvx) under our key must migrate forward.
        mcp_path.write_text(
            json.dumps({"mcpServers": {"memory-seed": {"command": "memory-seed-mcp", "args": ["--old"]}}}),
            encoding="utf-8",
        )

        from memory_seed.core import _merge_claude_mcp
        result = _merge_claude_mcp(cwd)
        self.assertTrue(result)

        data = json.loads(mcp_path.read_text())
        entry = data["mcpServers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])

    def test_mcp_merge_preserves_unrelated_mcp_server(self):
        import json

        cwd = self.make_project()
        mcp_path = cwd / ".mcp.json"
        mcp_path.write_text(
            json.dumps({"mcpServers": {"other-server": {"command": "other-cmd", "args": []}}}),
            encoding="utf-8",
        )

        from memory_seed.core import _merge_claude_mcp
        _merge_claude_mcp(cwd)

        data = json.loads(mcp_path.read_text())
        self.assertIn("other-server", data["mcpServers"])
        self.assertEqual(data["mcpServers"]["other-server"]["command"], "other-cmd")
        self.assertIn("memory-seed", data["mcpServers"])

    def test_mcp_merge_preserves_foreign_server_on_our_key(self):
        # Distinct from test_mcp_merge_preserves_unrelated_mcp_server above: here a
        # *foreign* server squats memory-seed's own key, not an unrelated key. The
        # is_ours guard must leave it untouched rather than overwriting it -
        # _merge_vscode_mcp is deliberately not covered here (different container
        # key, "servers" not "mcpServers"; copilot/codex already prove the pattern
        # generalizes via their own dedicated tests).
        import json

        from memory_seed.core import _merge_claude_mcp, _merge_cursor_mcp, _merge_gemini_mcp

        cases = [
            (_merge_claude_mcp, Path(".mcp.json")),
            (_merge_cursor_mcp, Path(".cursor/mcp.json")),
            (_merge_gemini_mcp, Path(".gemini/settings.json")),
        ]
        for merge_fn, rel_path in cases:
            with self.subTest(fn=merge_fn.__name__):
                cwd = self.make_project()
                mcp_path = cwd / rel_path
                mcp_path.parent.mkdir(parents=True, exist_ok=True)
                mcp_path.write_text(
                    json.dumps({"mcpServers": {"memory-seed": {"command": "some-other-server", "args": []}}}),
                    encoding="utf-8",
                )

                self.assertFalse(merge_fn(cwd))

                data = json.loads(mcp_path.read_text())
                self.assertEqual(data["mcpServers"]["memory-seed"]["command"], "some-other-server")

    def test_strip_removes_legacy_claude_settings_mcp(self):
        import json

        cwd = self.make_project()
        settings = cwd / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        # A project seeded by 2.2.0-2.3.0: dead mcpServers block alongside a real hook.
        settings.write_text(
            json.dumps(
                {
                    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "keep-me"}]}]},
                    "mcpServers": {
                        "memory-seed": {
                            "command": "uvx",
                            "args": ["--from", "memory-seed", "memory-seed-mcp", "--stdio"],
                            "type": "stdio",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        from memory_seed.core import _strip_claude_settings_mcp
        self.assertTrue(_strip_claude_settings_mcp(cwd))

        data = json.loads(settings.read_text())
        self.assertNotIn("mcpServers", data)  # dead block removed, empty parent pruned
        self.assertEqual(data["hooks"]["Stop"][0]["hooks"][0]["command"], "keep-me")  # rest preserved
        self.assertFalse(_strip_claude_settings_mcp(cwd))  # idempotent

    def test_strip_preserves_foreign_settings_mcp(self):
        import json

        cwd = self.make_project()
        settings = cwd / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        # A different server squatting our key must not be deleted.
        settings.write_text(
            json.dumps({"mcpServers": {"memory-seed": {"command": "some-other-server", "args": []}}}),
            encoding="utf-8",
        )

        from memory_seed.core import _strip_claude_settings_mcp
        self.assertFalse(_strip_claude_settings_mcp(cwd))
        data = json.loads(settings.read_text())
        self.assertEqual(data["mcpServers"]["memory-seed"]["command"], "some-other-server")

    def test_gemini_mcp_merge_preserves_existing_hooks(self):
        import json

        cwd = self.make_project()
        gemini_path = cwd / ".gemini" / "settings.json"
        gemini_path.parent.mkdir(parents=True, exist_ok=True)
        gemini_path.write_text(
            json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "existing"}]}]}}),
            encoding="utf-8",
        )

        from memory_seed.core import _merge_gemini_mcp
        _merge_gemini_mcp(cwd)

        data = json.loads(gemini_path.read_text())
        self.assertIn("memory-seed", data["mcpServers"])
        self.assertIn("Stop", data["hooks"])
        self.assertEqual(data["hooks"]["Stop"][0]["hooks"][0]["command"], "existing")

    def test_init_installs_mcp_for_codex(self):
        import tomllib

        cwd = self.make_project()
        init_project(cwd=cwd)

        # Codex reads project-scope MCP servers from .codex/config.toml.
        data = tomllib.loads((cwd / ".codex" / "config.toml").read_text(encoding="utf-8"))
        self.assertIn("memory-seed", data["mcp_servers"])
        entry = data["mcp_servers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])

    def test_codex_mcp_merge_updates_stale_args(self):
        import tomllib

        cwd = self.make_project()
        config_path = cwd / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # Legacy bare-command form (pre-uvx) under our key must migrate forward.
        config_path.write_text(
            '[mcp_servers.memory-seed]\n'
            'command = "memory-seed-mcp"\n'
            'args = ["--old"]\n',
            encoding="utf-8",
        )

        from memory_seed.core import _merge_codex_mcp
        self.assertTrue(_merge_codex_mcp(cwd))

        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        entry = data["mcp_servers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])

    def test_codex_mcp_merge_preserves_existing_config(self):
        import tomllib

        cwd = self.make_project()
        config_path = cwd / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # Unrelated setting + comment + a foreign MCP server must all survive.
        config_path.write_text(
            "# my codex config\n"
            'model = "gpt-5-codex"\n'
            "\n"
            "[mcp_servers.other]\n"
            'command = "other-cmd"\n'
            'args = []\n',
            encoding="utf-8",
        )

        from memory_seed.core import _merge_codex_mcp
        self.assertTrue(_merge_codex_mcp(cwd))

        text = config_path.read_text(encoding="utf-8")
        self.assertIn("# my codex config", text)  # comment preserved
        data = tomllib.loads(text)
        self.assertEqual(data["model"], "gpt-5-codex")  # unrelated setting preserved
        self.assertEqual(data["mcp_servers"]["other"]["command"], "other-cmd")  # foreign server kept
        self.assertIn("memory-seed", data["mcp_servers"])  # ours appended

    def test_codex_mcp_merge_preserves_foreign_server_on_our_key(self):
        import tomllib

        cwd = self.make_project()
        config_path = cwd / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # A different server squatting our key must not be overwritten.
        config_path.write_text(
            "[mcp_servers.memory-seed]\n"
            'command = "some-other-server"\n'
            "args = []\n",
            encoding="utf-8",
        )

        from memory_seed.core import _merge_codex_mcp
        self.assertFalse(_merge_codex_mcp(cwd))
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(data["mcp_servers"]["memory-seed"]["command"], "some-other-server")

    def test_doctor_warns_when_codex_hooks_without_mcp(self):
        from memory_seed.core import doctor, _merge_codex_mcp

        cwd = self.make_project()
        init_project(cwd=cwd)
        # Simulate a project that has Codex hooks but no MCP registration yet.
        (cwd / ".codex" / "config.toml").unlink()

        result = doctor(cwd=cwd)
        self.assertTrue(any("Codex" in w for w in result.warnings))
        self.assertTrue(result.control_plane_ok)  # warning is non-fatal

        # After re-registering, the warning clears.
        _merge_codex_mcp(cwd)
        self.assertFalse(any("Codex" in w for w in doctor(cwd=cwd).warnings))

    def test_doctor_warns_on_stale_manual_codex_mcp(self):
        from memory_seed.core import doctor, _merge_codex_mcp, _codex_mcp_status

        cwd = self.make_project()
        init_project(cwd=cwd)  # healthy control plane, so the non-fatal check is meaningful
        config_path = cwd / ".codex" / "config.toml"
        # Ours but stale, written as dotted keys -> no standard header to anchor a
        # rewrite. Update must no-op, and doctor must NOT stay silent about it.
        config_path.write_text(
            'mcp_servers.memory-seed.command = "memory-seed-mcp"\n'
            'mcp_servers.memory-seed.args = ["--old"]\n',
            encoding="utf-8",
        )

        self.assertEqual(_codex_mcp_status(cwd), "stale-manual")
        self.assertFalse(_merge_codex_mcp(cwd))  # safe no-op, not a corruption

        result = doctor(cwd=cwd)
        self.assertTrue(any("non-standard TOML form" in w for w in result.warnings))
        self.assertTrue(result.control_plane_ok)  # non-fatal

    def test_doctor_warns_on_stale_fixable_codex_mcp(self):
        from memory_seed.core import doctor, _merge_codex_mcp, _codex_mcp_status

        cwd = self.make_project()
        config_path = cwd / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # Ours but stale, standard header form -> update can migrate it.
        config_path.write_text(
            "[mcp_servers.memory-seed]\n"
            'command = "memory-seed-mcp"\n'
            'args = ["--old"]\n',
            encoding="utf-8",
        )

        self.assertEqual(_codex_mcp_status(cwd), "stale-fixable")
        result = doctor(cwd=cwd)
        self.assertTrue(any("outdated memory-seed MCP entry" in w for w in result.warnings))

        # update migrates it; warning then clears and status is current.
        self.assertTrue(_merge_codex_mcp(cwd))
        self.assertEqual(_codex_mcp_status(cwd), "current")
        self.assertFalse(any("Codex" in w for w in doctor(cwd=cwd).warnings))

    def test_codex_mcp_status_current_and_foreign_are_quiet(self):
        from memory_seed.core import doctor, _merge_codex_mcp, _codex_mcp_status

        cwd = self.make_project()
        # current
        _merge_codex_mcp(cwd)
        self.assertEqual(_codex_mcp_status(cwd), "current")
        self.assertFalse(any("Codex" in w for w in doctor(cwd=cwd).warnings))

        # foreign: a different server squatting our key
        (cwd / ".codex" / "config.toml").write_text(
            "[mcp_servers.memory-seed]\n"
            'command = "some-other-server"\n'
            "args = []\n",
            encoding="utf-8",
        )
        self.assertEqual(_codex_mcp_status(cwd), "foreign")
        self.assertFalse(any("Codex" in w for w in doctor(cwd=cwd).warnings))

    @pytest.mark.integration
    def test_doctor_warns_on_orphan_skill_not_in_registry(self):
        from memory_seed.core import doctor

        cwd = self.make_project()
        init_project(cwd=cwd)

        # A freshly seeded project's skills are all registered: no orphan warning.
        self.assertFalse(
            any("orphan skill" in w for w in doctor(cwd=cwd).warnings)
        )

        # Drop a skill runbook that is not referenced by skills/index.md.
        orphan = cwd / ".memory-seed" / "skills" / "ghost_skill.md"
        orphan.write_text(
            "---\nmemory-system-version: 2.7\n---\n\n# Ghost Skill\n",
            encoding="utf-8",
        )

        result = doctor(cwd=cwd)
        self.assertTrue(
            any("ghost_skill.md" in w and "orphan skill" in w for w in result.warnings)
        )
        self.assertTrue(result.control_plane_ok)  # warning is non-fatal

        # Registering it in the trigger registry clears the warning.
        registry = cwd / ".memory-seed" / "skills" / "index.md"
        registry.write_text(
            registry.read_text(encoding="utf-8")
            + "\n  - skill: ghost_skill.md\n    required: false\n",
            encoding="utf-8",
        )
        self.assertFalse(
            any("ghost_skill.md" in w for w in doctor(cwd=cwd).warnings)
        )

    @pytest.mark.integration
    def test_doctor_warns_on_local_user_with_no_matching_participant(self):
        from memory_seed.core import doctor

        cwd = self.make_project()
        init_project(cwd=cwd)

        # No local user configured at all: no warning (that's the SessionStart
        # hook's job, not doctor's).
        self.assertFalse(any("participants:" in w for w in doctor(cwd=cwd).warnings))

        (cwd / MEMORY_DIR_NAME / "local.yaml").write_text("user: jean\n", encoding="utf-8")

        # Local user configured but project.yaml has no participants: entry
        # for it at all -> warn.
        result = doctor(cwd=cwd)
        self.assertTrue(any("jean" in w and "participants:" in w for w in result.warnings))
        self.assertTrue(result.control_plane_ok)  # warning is non-fatal

        # A participants: entry for a *different* slug still leaves jean
        # unmatched -> still warns.
        (cwd / MEMORY_DIR_NAME / "project.yaml").write_text(
            "participants:\n  - slug: amina\n    initials: AM\n", encoding="utf-8"
        )
        result = doctor(cwd=cwd)
        self.assertTrue(any("jean" in w and "participants:" in w for w in result.warnings))

        # Adding the matching participant entry clears the warning.
        (cwd / MEMORY_DIR_NAME / "project.yaml").write_text(
            "participants:\n"
            "  - slug: amina\n    initials: AM\n"
            "  - slug: jean\n    initials: JN\n",
            encoding="utf-8",
        )
        self.assertFalse(any("participants:" in w for w in doctor(cwd=cwd).warnings))

    @pytest.mark.integration
    def test_doctor_warns_when_runtime_exists_but_routing_file_is_foreign(self):
        from memory_seed.core import doctor, _merge_routing_stanza

        cwd = self.make_project()
        init_project(cwd=cwd)

        # Fresh project: our AGENTS.md routes into the runtime, no route warning.
        self.assertFalse(any("route into" in w for w in doctor(cwd=cwd).warnings))

        # Replace it with a foreign file: neither our frontmatter nor our block.
        (cwd / "AGENTS.md").write_text("# Foreign Tool\n\nhost only\n", encoding="utf-8")
        result = doctor(cwd=cwd)
        self.assertTrue(
            any("AGENTS.md" in w and "route into" in w for w in result.warnings)
        )
        # Non-fatal, and not counted as a version mismatch (host owns the file).
        self.assertTrue(result.control_plane_ok)
        self.assertFalse(any(m["file"] == "AGENTS.md" for m in result.version_mismatches))

        # Injecting our managed block clears the warning.
        _merge_routing_stanza(cwd / "AGENTS.md")
        self.assertFalse(
            any("AGENTS.md" in w and "route into" in w for w in doctor(cwd=cwd).warnings)
        )
