import re
import unittest
from pathlib import Path


class SessionSchemaTests(unittest.TestCase):
    def test_agent_rules_document_flexible_rationale_aware_entry_shapes(self):
        content = Path(".memory-seed/agent-rules.md").read_text(encoding="utf-8")

        for phrase in (
            "Small work entry",
            "Meaningful decision entry",
            "Multi-decision session entry",
            "DRAFT decision record",
            "D = Decision",
            "R = Rationale",
            "A = Alternatives considered or rejected",
            "F = Files, artifacts, or behaviors changed",
            "T = Tests or validation",
            "Do not invent rationale",
            "Inferred rationale",
            "Rationale not recorded",
            "Alternatives are optional",
        ):
            self.assertIn(phrase, content)

    def test_agent_rules_document_mcp_history_conflict_resolution(self):
        content = Path(".memory-seed/agent-rules.md").read_text(encoding="utf-8")

        for phrase in (
            "History Retrieval And Conflict Resolution",
            "When To Search",
            "Tool Mechanics",
            "memory_search",
            "memory_get_chunk",
            '"query": "short natural-language description of what you need to know"',
            '"cwd": "."',
            '"top_k": 5',
            'granularity: "entry"',
            'granularity: "section"',
            "`chunk_id` is normally the entry YAML `entry_id`",
            "ms-db2d715c#decisions/d1-use-draft-for-compact-decision-records",
            "Search results include `chunk_id`, `entry_id`, `source`, `line_range`, `heading_path`, `excerpt`",
            "Treat excerpts as previews only",
            "Use the fetched chunk text, not just the excerpt",
            "If MCP tools are unavailable",
            "Start with the last two session files",
            "Current files are the active authority",
            "clear supersession criteria",
            "newer dated session entry or current authority file",
            "no later reversal or unresolved disagreement is found",
            "Session history is evidence and rationale",
            "ask the user before changing durable design",
        ):
            self.assertIn(phrase, content)

    def test_agent_rules_restore_v14_operational_guardrails(self):
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
            "Reusable seed files must stay generic",
            "Inside a sub-project runtime, local `index.md`, local `policy.md`, and local skills govern work under that runtime boundary",
            "Bootstrap Boundary",
            "apply bootstrap to that target project or sub-project path",
        ):
            self.assertIn(phrase, content)

    def test_agent_rules_define_deterministic_skill_registry_and_subproject_summary(self):
        content = Path(".memory-seed/agent-rules.md").read_text(encoding="utf-8")

        for phrase in (
            "Read `.memory-seed/skills/index.md` as the deterministic skill trigger registry",
            "Load full `.memory-seed/skills/*.md` runbooks only when the trigger registry matches the current task",
            "Sub-Project Runtime Creation",
            "distinct long-lived context, policy, workflows, risks, outputs, or memory needs",
            "Do not create a sub-project runtime just because a folder exists",
            "Record the nested runtime's existence and purpose in the parent or root `index.md`",
            "Detailed work logs belong in the nearest active runtime",
            "parent-visible topology, shared design, release behavior, policy inheritance, cross-project dependencies, risks, or active priorities",
            "Do not mirror sub-project logs into root memory",
            "`index.md`: deterministic trigger registry",
            "Evaluate registry rules in listed order",
            "load every matching required skill",
            "use the nearest runtime's registry first",
        ):
            self.assertIn(phrase, content)

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

        self.assertEqual(content, seed.read_text(encoding="utf-8"))
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
            "Do not require rationale for obvious file discoveries",
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
            "sessions preserve rationale and tradeoffs",
            "index.md receives only durable current conclusions",
            "policy.md receives only durable behavioral constraints",
            "Preserve DRAFT decision records",
            "Do not copy full rationale into index.md",
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
            (
                Path(".memory-seed/skills/index.md"),
                Path("memory_seed/seed/.memory-seed/skills/index.md"),
            ),
        )

        for live, seed in pairs:
            self.assertEqual(
                live.read_text(encoding="utf-8"),
                seed.read_text(encoding="utf-8"),
                f"{seed} should match {live}",
            )

    def test_current_session_files_have_frontmatter_and_entry_metadata(self):
        for path in (
            Path(".memory-seed/sessions/2026-05-25.md"),
            Path(".memory-seed/sessions/2026-05-26.md"),
        ):
            content = path.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---\n"), f"{path} needs file frontmatter")
            self.assertIn("session_date:", content, f"{path} needs session_date")
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


if __name__ == "__main__":
    unittest.main()
