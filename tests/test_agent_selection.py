import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

from memory_seed.core import (
    doctor,
    init_project,
    update_project,
)


class AgentSelectionTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-agents-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    # --- resolve_agents ---
    def test_resolve_agents_flag_parsing_and_validation(self):
        from memory_seed.core import resolve_agents, KNOWN_AGENTS

        self.assertEqual(resolve_agents("claude,codex", isatty=False), {"claude", "codex"})
        self.assertEqual(resolve_agents("claude codex", isatty=False), {"claude", "codex"})
        self.assertEqual(resolve_agents("all", isatty=False), set(KNOWN_AGENTS))
        self.assertEqual(resolve_agents("none", isatty=False), set())
        # No flag, non-TTY -> all (backward-compatible default).
        self.assertEqual(resolve_agents(None, isatty=False), set(KNOWN_AGENTS))
        # Interactive empty response -> all.
        self.assertEqual(resolve_agents(None, isatty=True, prompt_response=""), set(KNOWN_AGENTS))
        self.assertEqual(resolve_agents(None, isatty=True, prompt_response="none"), set())
        self.assertEqual(resolve_agents(None, isatty=True, prompt_response="gemini"), {"gemini"})
        with self.assertRaises(ValueError):
            resolve_agents("claude,bogus", isatty=False)

    # --- selective init ---
    def test_init_with_subset_installs_only_selected(self):
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude", "codex"})

        self.assertTrue((cwd / "AGENTS.md").exists())
        self.assertTrue((cwd / "CLAUDE.md").exists())
        self.assertTrue((cwd / ".claude" / "settings.json").exists())
        self.assertTrue((cwd / ".codex" / "hooks.json").exists())
        self.assertTrue((cwd / ".mcp.json").exists())
        # Deselected agents leave no trace.
        self.assertFalse((cwd / "GEMINI.md").exists())
        self.assertFalse((cwd / ".gemini").exists())
        self.assertFalse((cwd / ".github").exists())
        self.assertFalse((cwd / ".cursor").exists())
        # Agent-agnostic core always present.
        self.assertTrue((cwd / ".memory-seed" / "agent-rules.md").exists())
        self.assertTrue((cwd / ".agents" / "developer.md").exists())
        # Selection persisted.
        from memory_seed.core import selected_agents
        self.assertEqual(selected_agents(cwd), {"claude", "codex"})
        self.assertTrue((cwd / ".memory-seed" / "project.yaml").exists())

    def test_init_all_agents_writes_skill_state_project_yaml(self):
        # Default all-agent selection stays dynamic, but new init writes skill
        # selection state so ignored optional skills are not re-added on update.
        cwd = self.make_project()
        init_project(cwd=cwd)
        self.assertTrue((cwd / ".memory-seed" / "project.yaml").exists())
        from memory_seed.core import read_project_agents, KNOWN_AGENTS, selected_agents
        self.assertIsNone(read_project_agents(cwd))
        self.assertEqual(selected_agents(cwd), set(KNOWN_AGENTS))

    def test_doctor_ignores_deselected_agent_files(self):
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude", "codex"})
        result = doctor(cwd=cwd)
        # GEMINI.md is intentionally absent; doctor must not flag it.
        self.assertNotIn("GEMINI.md", result.missing)
        self.assertEqual(result.missing, [])
        self.assertFalse(any("Codex" in w for w in result.warnings))

    def test_update_does_not_readd_deselected_agents(self):
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude", "codex"})
        update_project(cwd=cwd)
        self.assertFalse((cwd / "GEMINI.md").exists())
        self.assertFalse((cwd / ".gemini").exists())
        self.assertFalse((cwd / ".github").exists())

    # --- add / remove ---
    def test_add_agent_installs_and_persists(self):
        from memory_seed.core import add_agent, selected_agents

        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude"})
        res = add_agent(cwd=cwd, agent="gemini")
        self.assertTrue(res["changed"])
        self.assertTrue((cwd / "GEMINI.md").exists())
        self.assertTrue((cwd / ".gemini" / "settings.json").exists())
        self.assertEqual(selected_agents(cwd), {"claude", "gemini"})
        # Adding an already-installed agent is a no-op.
        self.assertFalse(add_agent(cwd=cwd, agent="gemini")["changed"])

    def test_remove_agent_strips_ours_preserves_foreign_and_backs_up(self):
        import json
        from memory_seed.core import remove_agent, selected_agents

        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude", "codex"})
        # Inject foreign content into Claude's settings.
        settings = cwd / ".claude" / "settings.json"
        data = json.loads(settings.read_text())
        data["permissions"] = {"allow": ["Bash"]}
        settings.write_text(json.dumps(data))

        res = remove_agent(cwd=cwd, agent="claude")
        self.assertTrue(res["changed"])
        self.assertTrue(res["backed_up"])  # something was backed up
        # Routing file + ours-only .mcp.json gone.
        self.assertFalse((cwd / "CLAUDE.md").exists())
        self.assertFalse((cwd / ".mcp.json").exists())
        # Foreign content preserved; file NOT deleted.
        self.assertTrue(settings.exists())
        self.assertEqual(list(json.loads(settings.read_text()).keys()), ["permissions"])
        self.assertEqual(selected_agents(cwd), {"codex"})

    def test_remove_not_installed_is_noop(self):
        from memory_seed.core import remove_agent
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude"})
        res = remove_agent(cwd=cwd, agent="gemini")
        self.assertFalse(res["changed"])

    def test_remove_last_agent_warns_and_is_zero_state(self):
        from memory_seed.core import remove_agent, selected_agents, read_project_agents
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"codex"})
        res = remove_agent(cwd=cwd, agent="codex")
        self.assertTrue(res["warning"])
        # Zero-agents is a real state (empty set), distinct from unconfigured (None).
        self.assertEqual(read_project_agents(cwd), set())
        self.assertEqual(selected_agents(cwd), set())
        # doctor expects no agent files and is clean.
        self.assertEqual(doctor(cwd=cwd).missing, [])

    def test_remove_codex_preserves_foreign_toml(self):
        import tomllib
        from memory_seed.core import remove_agent

        cwd = self.make_project()
        init_project(cwd=cwd, agents={"codex"})
        cfg = cwd / ".codex" / "config.toml"
        # Surround our block with foreign TOML: a top-level key before, a foreign
        # MCP table after. Exercises the line-based stripper's "delete to next [".
        cfg.write_text(
            'model = "gpt-x"\n\n'
            + cfg.read_text(encoding="utf-8")
            + '\n[mcp_servers.other]\ncommand = "foo"\nargs = []\n',
            encoding="utf-8",
        )

        remove_agent(cwd=cwd, agent="codex")

        self.assertTrue(cfg.exists())
        text = cfg.read_text(encoding="utf-8")
        self.assertNotIn("[mcp_servers.memory-seed]", text)
        self.assertIn('model = "gpt-x"', text)
        self.assertIn("[mcp_servers.other]", text)
        parsed = tomllib.loads(text)  # still valid TOML
        self.assertNotIn("memory-seed", parsed.get("mcp_servers", {}))
        self.assertIn("other", parsed.get("mcp_servers", {}))

    def test_remove_from_unconfigured_project_writes_remaining(self):
        from memory_seed.core import remove_agent, selected_agents, KNOWN_AGENTS

        cwd = self.make_project()
        init_project(cwd=cwd)  # all agents, project.yaml contains skill state only
        self.assertTrue((cwd / ".memory-seed" / "project.yaml").exists())

        res = remove_agent(cwd=cwd, agent="gemini")
        self.assertTrue(res["changed"])
        self.assertEqual(selected_agents(cwd), set(KNOWN_AGENTS) - {"gemini"})
        self.assertTrue((cwd / ".memory-seed" / "project.yaml").exists())
        self.assertFalse((cwd / "GEMINI.md").exists())

    def test_project_yaml_parser_fails_open(self):
        from memory_seed.core import read_project_agents
        cwd = self.make_project()
        (cwd / ".memory-seed").mkdir(parents=True)
        cfg = cwd / ".memory-seed" / "project.yaml"
        # Malformed / unrelated content with no agents: key -> None (treated as all).
        cfg.write_text("schema_version: 1\nusers:\n  - jean\n", encoding="utf-8")
        self.assertIsNone(read_project_agents(cwd))
        # Inline list form is parsed; unknown slugs ignored.
        cfg.write_text("agents: [claude, bogus, codex]\n", encoding="utf-8")
        self.assertEqual(read_project_agents(cwd), {"claude", "codex"})

    def test_project_yaml_participants_coexist_with_agent_selection(self):
        from memory_seed.core import read_project_participants, selected_agents
        cwd = self.make_project()
        (cwd / ".memory-seed").mkdir(parents=True)
        (cwd / ".memory-seed" / "project.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "project_id: memory-seed",
                    "agents:",
                    "  - claude",
                    "  - codex",
                    "participants:",
                    "  - slug: jean",
                    "    initials: JN",
                    "    display_name: Jean",
                    "  - slug: amina",
                    "    initials: AM",
                    "    display_name: Amina",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        participants = read_project_participants(cwd)

        self.assertEqual(selected_agents(cwd), {"claude", "codex"})
        self.assertEqual([p.slug for p in participants], ["jean", "amina"])
        self.assertEqual([p.initials for p in participants], ["JN", "AM"])
        self.assertEqual(participants[0].display_name, "Jean")

    def test_write_project_agents_preserves_participants_block(self):
        from memory_seed.core import read_project_participants, selected_agents, write_project_agents
        cwd = self.make_project()
        (cwd / ".memory-seed").mkdir(parents=True)
        cfg = cwd / ".memory-seed" / "project.yaml"
        cfg.write_text(
            "schema_version: 1\n"
            "project_id: memory-seed\n"
            "participants:\n"
            "  - slug: jean\n"
            "    initials: JN\n"
            "    display_name: Jean\n"
            "agents:\n"
            "  - claude\n",
            encoding="utf-8",
        )

        write_project_agents(cwd, {"codex"})

        self.assertEqual(selected_agents(cwd), {"codex"})
        self.assertEqual([(p.slug, p.initials, p.display_name) for p in read_project_participants(cwd)], [("jean", "JN", "Jean")])
        text = cfg.read_text(encoding="utf-8")
        self.assertIn("participants:\n  - slug: jean\n    initials: JN\n    display_name: Jean", text)

    def test_project_yaml_participants_fail_open(self):
        from memory_seed.core import read_project_participants
        cwd = self.make_project()
        (cwd / ".memory-seed").mkdir(parents=True)
        (cwd / ".memory-seed" / "project.yaml").write_text(
            "participants:\n"
            "  - slug: Jean\n"
            "    initials: JN\n"
            "  - initials: AM\n",
            encoding="utf-8",
        )

        self.assertEqual(read_project_participants(cwd), [])
