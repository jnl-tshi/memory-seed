import re
import unittest
from pathlib import Path


class SessionSchemaTests(unittest.TestCase):
    def test_session_logging_skill_documents_flexible_rationale_aware_entry_shapes(self):
        content = Path(".memory-seed/skills/session_logging.md").read_text(encoding="utf-8")

        for phrase in (
            "Small work entry",
            "Meaningful decision entry",
            "Multi-decision session entry",
            "DRAFT decision record",
            "D = Decision",
            "R = Reason",
            "A = Alternatives considered or rejected",
            "F = Files, artifacts, or behaviors changed",
            "T = Tests or validation",
            "Do not invent reason",
            "Inferred reason",
            "Reason not recorded",
            "Alternatives are optional",
        ):
            self.assertIn(phrase, content)

    def test_history_retrieval_skill_documents_mcp_history_conflict_resolution(self):
        # Guards the load-bearing contract tokens only (section headings, tool
        # names, the recency/topical split, the fallback + authority rules).
        # Incidental JSON-literal snippets and example IDs were intentionally
        # dropped so harmless rewording does not trip the test.
        content = Path(".memory-seed/skills/history_retrieval.md").read_text(encoding="utf-8")

        for phrase in (
            "History Retrieval And Conflict Resolution",
            "Recency vs. Topical Retrieval",
            "When To Search",
            "Tool Mechanics",
            "memory_search",
            "memory_get_chunk",
            'granularity: "entry"',
            'granularity: "section"',
            "If MCP tools are unavailable",
            "Start with the last two session documents",
            "Current files are the active authority",
            "Session history is evidence and reason",
            "ask the user before changing durable design",
        ):
            self.assertIn(phrase, content)

    def test_agent_rules_keep_startup_guardrails_and_lazy_skill_pointers(self):
        content = Path(".memory-seed/agent-rules.md").read_text(encoding="utf-8")

        for phrase in (
            "Also locked unless explicitly requested",
            "Adding new top-level `.memory-seed` files",
            "Recreating obsolete legacy memory files from older layouts",
            "Immediate durable-memory update exception",
            "route an agent to wrong files",
            "For restricted files, the agent must be able to explain why the file's ownership scope was affected",
            "Code Search Trigger",
            "load `.memory-seed/skills/code_search.md` before broad grep sweeps or full-file reads",
            "Memory Doctor Trigger",
            "runtime health, migration integrity, missing files, archive state, seed/live sync, or bootstrap completion",
            "Compact And Consolidation Trigger",
            "Compact output is review input, not an automatic write plan",
            "Public Memory Hygiene",
            "Treat `.memory-seed` files as potentially publishable",
            "Do not write secrets, credentials, tokens, private keys",
            ".memory-seed/skills/memory_hygiene.md",
            "Inside a sub-project runtime, local `index.md`, local `policy.md`, and local skills govern work under that runtime boundary",
            "Bootstrap Boundary",
            "apply bootstrap to that target project or sub-project path",
        ):
            self.assertIn(phrase, content)

    def test_agent_rules_define_deterministic_skill_registry_and_subproject_summary(self):
        content = Path(".memory-seed/agent-rules.md").read_text(encoding="utf-8")
        subproject = Path(".memory-seed/skills/subproject_runtime.md").read_text(encoding="utf-8")

        for phrase in (
            "Read `.memory-seed/skills/index.md` as the deterministic skill trigger registry",
            "Load full `.memory-seed/skills/*.md` runbooks only when the trigger registry matches the current task",
            "Sub-Project Runtime Creation",
            ".memory-seed/skills/subproject_runtime.md",
            "Detailed work logs belong in the nearest active runtime",
            "Do not mirror sub-project logs into root memory",
            "`index.md`: deterministic trigger registry",
            "Evaluate registry rules in listed order",
            "load every matching required skill",
            "use the nearest runtime's registry first",
        ):
            self.assertIn(phrase, content)

        for phrase in (
            "distinct long-lived context, policy, workflows, risks, outputs, or memory needs",
            "Do not create a sub-project runtime just because a folder exists",
            "Record the nested runtime's existence and purpose in the parent or root `index.md`",
            "parent-visible topology, shared design, release behavior, policy inheritance, cross-project dependencies, risks, or active priorities",
        ):
            self.assertIn(phrase, subproject)

    def test_routing_and_bootstrap_reference_skill_registry(self):
        agents = Path("AGENTS.md").read_text(encoding="utf-8")
        bootstrap = Path(".memory-seed/project-bootstrap.md").read_text(encoding="utf-8")

        for phrase in (
            "Read `.memory-seed/skills/index.md` as the deterministic skill trigger registry",
            "Load full files from `.memory-seed/skills/` only when the trigger registry matches the task",
        ):
            self.assertIn(phrase, agents)

        for phrase in (
            "skills/",
            "index.md",
            "skill trigger registry expectations",
            ".memory-seed/skills/index.md`: deterministic trigger registry",
            "Always include `skills/index.md` as the deterministic trigger registry",
            "Generated `index.md` should reference it in `Always Read` and `Lazy Skills`",
            ".memory-seed/skills/index.md` contains the deterministic skill trigger registry",
        ):
            self.assertIn(phrase, bootstrap)

    def test_public_docs_cover_current_v2_routing_and_mcp_contract(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

        for phrase in (
            ".memory-seed/skills/index.md",
            "deterministic trigger registry",
            "Sub-project runtimes keep detailed logs local",
            "Parent/root memory should receive only brief coordination summaries",
            'granularity="entry"',
            'granularity="section"',
            "uses the entry YAML `entry_id` as `chunk_id`",
            "ms-db2d715c#decisions/d1-use-draft-for-compact-decision-records",
            "entry metadata",
            "`entry_id`, `user_initials`, `agent_type`, `project_path`, and `subproject_path`",
            "Use `uvx` for one-off execution",
            "Use `uv tool install memory-seed` when you want Memory Seed installed persistently as a local machine tool",
            "Use `uv add memory-seed` only when the current Python project itself depends on Memory Seed as a package",
            "Use `uv pip install memory-seed` when installing Memory Seed into the active virtual environment",
        ):
            self.assertIn(phrase, readme)

        for phrase in (
            "## Unreleased",
            ".memory-seed/skills/index.md",
            "entry-level chunks using session YAML `entry_id`",
            "optional section granularity",
            "sub-project runtime creation and parent/root coordination summaries",
            "persistent `uv tool install`, project dependencies, and virtual-environment installs",
        ):
            self.assertIn(phrase, changelog)

    def test_skill_trigger_registry_is_deterministic_and_seeded(self):
        live = Path(".memory-seed/skills/index.md")
        seed = Path("memory_seed/seed/.memory-seed/skills/index.md")
        content = live.read_text(encoding="utf-8")

        # skills/index.md is a runtime-local file (skipped by update once it exists).
        # Projects may add persona-specific trigger entries beyond the seed baseline.
        # Verify the seed content is fully contained in the live file instead of exact equality.
        seed_content = seed.read_text(encoding="utf-8")
        for line in seed_content.splitlines():
            self.assertIn(line, content, f"seed line missing from live skills/index.md: {line!r}")
        for phrase in (
            "trigger_registry_version: 1",
            "lazy_load_full_skills: true",
            "evaluate_order: listed",
            "load_every_matching_required_skill: true",
            "ambiguity_policy: ask_when_durable",
            "local_registry_precedence: nearest_runtime_first",
            "inherited_parent_skills: apply_when_not_disabled_or_overridden_locally",
            "skill: code_search.md",
            "skill: data_architecture.md",
            "skill: local_compilation.md",
            "skill: memory_consolidation.md",
            "skill: memory_doctor.md",
            "skill: release_publishing.md",
            "skill: security_triage.md",
            "skill: history_retrieval.md",
            "skill: session_logging.md",
            "skill: compact_mermaid_diagrams.md",
            "skill: end_of_turn.md",
            "skill: memory_hygiene.md",
            "skill: risk_signaling.md",
            "skill: proposal_lifecycle.md",
            "skill: subproject_runtime.md",
        ):
            self.assertIn(phrase, content)

    def test_extracted_lazy_skills_are_registered_seeded_and_standalone(self):
        extracted = {
            "history_retrieval.md": (
                "Default search payload",
                "memory_search",
                "memory_get_chunk",
                "granularity: \"entry\"",
                "Current files are the active authority",
            ),
            "session_logging.md": (
                "Session Log Format",
                "DRAFT decision record",
                "Append-Only Chronology",
                "related_entries",
                "Meaningful decision entry",
            ),
            "compact_mermaid_diagrams.md": (
                "Compact Mermaid Diagrams Skill",
                "compact, rectangular Mermaid diagrams",
                "invisible `~~~` links",
                "No single node sits alone",
            ),
            "end_of_turn.md": (
                "End Of Turn",
                "orphan & artifact sweep",
                "Persona evolution check",
                "Skill evolution check",
                "Baseline-promotion check",
            ),
            "memory_hygiene.md": (
                "Public Memory Hygiene",
                "Treat `.memory-seed` files as potentially publishable",
                "Do not write secrets",
                "Reusable seed files must stay generic",
            ),
            "subproject_runtime.md": (
                "Sub-Project Runtime Creation",
                "nested `.memory-seed/` runtime",
                "Record local inheritance choices",
                "parent/root summary",
            ),
            "risk_signaling.md": (
                "Risk Signaling Skill",
                "Action Tiers",
                "STOP Categories",
                "Proceed-and-flag",
                "Security / trust boundary",
            ),
        }
        live_registry = Path(".memory-seed/skills/index.md").read_text(encoding="utf-8")
        seed_registry = Path("memory_seed/seed/.memory-seed/skills/index.md").read_text(encoding="utf-8")
        runtime_index = Path(".memory-seed/index.md").read_text(encoding="utf-8")

        for skill, phrases in extracted.items():
            live = Path(".memory-seed/skills") / skill
            seed = Path("memory_seed/seed/.memory-seed/skills") / skill
            self.assertTrue(live.exists(), f"missing live skill: {skill}")
            self.assertTrue(seed.exists(), f"missing seed skill: {skill}")
            self.assertEqual(
                live.read_text(encoding="utf-8"),
                seed.read_text(encoding="utf-8"),
                f"{skill} should match seed twin",
            )
            skill_text = live.read_text(encoding="utf-8")
            for phrase in phrases:
                self.assertIn(phrase, skill_text, f"{skill} missing {phrase!r}")
            for registry in (live_registry, seed_registry):
                self.assertIn(f"skill: {skill}", registry)
            self.assertIn(f".memory-seed/skills/{skill}", runtime_index)

    def test_agent_rules_points_to_extracted_skills_without_embedded_runbooks(self):
        content = Path(".memory-seed/agent-rules.md").read_text(encoding="utf-8")

        for phrase in (
            ".memory-seed/skills/history_retrieval.md",
            ".memory-seed/skills/session_logging.md",
            ".memory-seed/skills/end_of_turn.md",
            ".memory-seed/skills/memory_hygiene.md",
            ".memory-seed/skills/risk_signaling.md",
            ".memory-seed/skills/subproject_runtime.md",
        ):
            self.assertIn(phrase, content)

        for moved_detail in (
            "Default search payload:",
            "Useful optional search fields:",
            "Search results include `chunk_id`",
            "#### Meaningful decision entry",
            "#### Small work entry",
            "#### Multi-decision session entry",
            "Also check for unregistered `.agents/*.md`",
            "Reusable seed files must stay generic. Do not write project-specific",
        ):
            self.assertNotIn(moved_detail, content)

    def test_universal_registry_entries_have_live_and_seed_skill_files(self):
        live_registry = Path(".memory-seed/skills/index.md").read_text(encoding="utf-8")
        seed_registry = Path("memory_seed/seed/.memory-seed/skills/index.md").read_text(encoding="utf-8")
        entry_re = re.compile(r"^  - skill: (?P<skill>[^\n]+)\n(?P<body>.*?)(?=^  - skill: |\Z)", re.MULTILINE | re.DOTALL)

        for registry_text, root in (
            (live_registry, Path(".memory-seed/skills")),
            (seed_registry, Path("memory_seed/seed/.memory-seed/skills")),
        ):
            for match in entry_re.finditer(registry_text):
                skill = match.group("skill").strip()
                body = match.group("body")
                if "persona:" in body:
                    continue
                self.assertTrue((root / skill).exists(), f"{root / skill} is registered but missing")

    def test_esr_commands_point_to_end_of_turn_skill(self):
        claude_live = Path(".claude/commands/esr.md").read_text(encoding="utf-8")
        claude_seed = Path("memory_seed/seed/.claude/commands/esr.md").read_text(encoding="utf-8")
        gemini_seed = Path("memory_seed/seed/.gemini/commands/esr.toml").read_text(encoding="utf-8")

        self.assertEqual(claude_live, claude_seed)
        for content in (claude_live, claude_seed, gemini_seed):
            self.assertIn(".memory-seed/skills/end_of_turn.md", content)
            self.assertIn("Append a session entry", content)
            self.assertIn("full checklist", content)

    def test_agent_collaboration_skill_is_registered_and_agent_rules_stay_lean(self):
        live_skill = Path(".memory-seed/skills/agent_collaboration.md")
        seed_skill = Path("memory_seed/seed/.memory-seed/skills/agent_collaboration.md")
        live_registry = Path(".memory-seed/skills/index.md").read_text(encoding="utf-8")
        seed_registry = Path("memory_seed/seed/.memory-seed/skills/index.md").read_text(encoding="utf-8")
        runtime_index = Path(".memory-seed/index.md").read_text(encoding="utf-8")
        agent_rules = Path(".memory-seed/agent-rules.md").read_text(encoding="utf-8")

        self.assertTrue(live_skill.exists(), "live collaboration skill missing")
        self.assertTrue(seed_skill.exists(), "seed collaboration skill missing")
        self.assertEqual(
            live_skill.read_text(encoding="utf-8"),
            seed_skill.read_text(encoding="utf-8"),
            "seed collaboration skill should match live skill",
        )

        skill_text = live_skill.read_text(encoding="utf-8")
        for phrase in (
            "Git-first collaboration",
            "<owner>/<kind>/<topic>",
            "feature|fix|refactor|test|docs",
            "parallel code-writing agents use separate worktrees",
            "Task Packet",
            "allowed_files",
            "forbidden_files",
            "Conflict Escalation",
            "orchestrator owns durable session logging",
            "per-user session targets",
        ):
            self.assertIn(phrase, skill_text)

        for registry in (live_registry, seed_registry):
            self.assertIn("skill: agent_collaboration.md", registry)
            self.assertIn("subagents, branch/worktree coordination, or multi-developer agent workflows", registry)
        self.assertIn(".memory-seed/skills/agent_collaboration.md", runtime_index)
        self.assertIn("agent_collaboration.md", agent_rules)
        self.assertNotIn("merge queue is required", agent_rules)

    def test_agent_rules_lazy_loading_recommendations_doc_exists(self):
        path = Path("docs/2_Todo/completed/agent-rules-lazy-loading-recommendations.md")
        self.assertTrue(path.exists(), "agent-rules lazy-loading recommendations doc missing")
        content = path.read_text(encoding="utf-8")

        for phrase in (
            "# Agent Rules Lazy-Loading Recommendations",
            "Recommendations only",
            "keep always-on",
            "shorten and point to existing skill",
            "move to proposed future skill",
            "leave unchanged for now",
            "History Retrieval And Conflict Resolution",
            "Session Log Format",
            "End Of Turn",
            "Public Memory Hygiene",
            "Sub-Project Runtime Creation",
            "Suggested Target Flow",
        ):
            self.assertIn(phrase, content)

    def test_bootstrap_requires_rationale_for_behavior_shaping_choices(self):
        content = Path(".memory-seed/project-bootstrap.md").read_text(encoding="utf-8")

        for phrase in (
            "project classification",
            "policy and risk posture",
            "inheritance model",
            "active skill selection",
            "major assumptions",
            "DRAFT decision records",
            "Do not require reason for obvious file discoveries",
        ):
            self.assertIn(phrase, content)

    def test_bootstrap_documents_mcp_history_expectations(self):
        content = Path(".memory-seed/project-bootstrap.md").read_text(encoding="utf-8")

        for phrase in (
            "MCP history retrieval expectations",
            "memory_search",
            "memory_get_chunk",
            "entry granularity by default",
            "section granularity for narrow searches",
            "direct session-file fallback when MCP is unavailable",
        ):
            self.assertIn(phrase, content)

    def test_memory_consolidation_preserves_rationale_boundary(self):
        content = Path(".memory-seed/skills/memory_consolidation.md").read_text(encoding="utf-8")

        for phrase in (
            "sessions preserve reason and tradeoffs",
            "index.md receives only durable current conclusions",
            "policy.md receives only durable behavioral constraints",
            "Preserve DRAFT decision records",
            "Do not copy full reason into index.md",
        ):
            self.assertIn(phrase, content)

    def test_seed_control_plane_matches_live_rationale_guidance(self):
        pairs = (
            (
                Path(".memory-seed/agent-rules.md"),
                Path("memory_seed/seed/.memory-seed/agent-rules.md"),
            ),
            (
                Path(".memory-seed/project-bootstrap.md"),
                Path("memory_seed/seed/.memory-seed/project-bootstrap.md"),
            ),
            (
                Path(".memory-seed/skills/memory_consolidation.md"),
                Path("memory_seed/seed/.memory-seed/skills/memory_consolidation.md"),
            ),
            # skills/index.md is runtime-local: projects add persona-specific trigger entries
            # beyond the seed baseline. Exact equality is checked per-line in
            # test_skill_trigger_registry_is_deterministic_and_seeded instead.
        )

        for live, seed in pairs:
            self.assertEqual(
                live.read_text(encoding="utf-8"),
                seed.read_text(encoding="utf-8"),
                f"{seed} should match {live}",
            )

    def test_current_session_files_have_frontmatter_and_entry_metadata(self):
        # Validate EVERY schema-era session file (those with frontmatter), so a
        # malformed new entry fails CI. Pre-schema legacy logs (no frontmatter)
        # are skipped rather than pinning two frozen dates.
        session_files = sorted(Path(".memory-seed/sessions").glob("*.md"))
        self.assertTrue(session_files, "no session files found")

        checked = 0
        for path in session_files:
            content = path.read_text(encoding="utf-8")
            if not content.startswith("---\n"):
                continue  # legacy pre-schema session log; not version-tracked
            if "session_date:" not in content:
                continue  # legacy pre-schema frontmatter
            checked += 1
            entries = re.findall(r"^## .+$", content, flags=re.MULTILINE)
            self.assertGreater(entries, [], f"{path} should contain session entries")
            for heading in entries:
                start = content.index(heading)
                next_heading = content.find("\n## ", start + 1)
                block = content[start:] if next_heading == -1 else content[start:next_heading]
                self.assertIn("```yaml\n", block, f"{path} entry {heading} needs metadata YAML")
                for field in (
                    "entry_id:",
                    "user_initials:",
                    "agent_type:",
                    "project_path:",
                    "subproject_path:",
                ):
                    self.assertIn(field, block, f"{path} entry {heading} missing {field}")

        self.assertGreater(checked, 0, "expected at least one schema-era session file")


if __name__ == "__main__":
    unittest.main()
