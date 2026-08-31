import re
import unittest
from pathlib import Path

from memory_seed.core import SEED_FILES, iter_session_documents

SEED_SKILLS_DIR = Path("memory_seed/seed/.memory-seed/skills")


def _seed_registry_skill_names():
    """Every `- skill: <name>` token in the seed trigger registry.

    Deliberately includes `persona:` entries: an optional/persona skill is still
    shipped by the seed, and skipping them is what let a registry entry point at
    a skill that was never installed.
    """
    registry_text = (SEED_SKILLS_DIR / "index.md").read_text(encoding="utf-8")
    return re.findall(r"^\s*- skill:\s*(\S+)", registry_text, re.MULTILINE)


def _seed_files_skill_names():
    """Skill runbook filenames shipped by SEED_FILES (index.md is the registry, not a skill)."""
    prefix = ".memory-seed/skills/"
    return [
        seed_file.destination[len(prefix):]
        for seed_file in SEED_FILES
        if seed_file.destination.startswith(prefix)
        and seed_file.destination != f"{prefix}index.md"
    ]


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
            "Generated `index.md` should reference it in `Startup And On-Demand Read` and `Lazy Skills`",
            ".memory-seed/skills/index.md` contains the deterministic skill trigger registry",
        ):
            self.assertIn(phrase, bootstrap)

    def test_bootstrap_requires_tree_first_runtime_indexes(self):
        bootstrap = Path(".memory-seed/project-bootstrap.md").read_text(encoding="utf-8")
        runtime_index = Path(".memory-seed/index.md").read_text(encoding="utf-8")

        for phrase in (
            "`Repository Structure` and `Memory Runtime Structure` are mandatory",
            "They are the primary navigation surface",
            "fenced `text` tree",
            "short inline `# purpose` comments",
            "It supplements the trees and must never replace them",
            "Tailor both trees to evidence found in the target",
            "its file trees match paths that actually exist",
        ):
            self.assertIn(phrase, bootstrap)

        self.assertLess(
            bootstrap.index("## Repository Structure"),
            bootstrap.index("## Fast Orientation"),
        )
        self.assertLess(
            runtime_index.index("## Repository Structure"),
            runtime_index.index("## Runtime Boundary"),
        )
        self.assertLess(
            runtime_index.index("## Memory Runtime Structure"),
            runtime_index.index("### Key Entry Points"),
        )
        self.assertIn("```text\nmemory-seed/", runtime_index)
        self.assertIn("```text\n.memory-seed/", runtime_index)

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
            # Re-anchored when sidecars moved to full Mermaid rendering. The
            # previous anchors pinned the subset restriction ("`subgraph` Is Not
            # Parsed In Sidecars", "is the only arrow that works") which this
            # change deletes. These pin the two claims that now carry the skill,
            # so quietly reinstating the subset rule, or dropping the ADR
            # diagram expectation, trips the test.
            "compact_mermaid_diagrams.md": (
                "Compact Mermaid Diagrams Skill",
                "Sidecars Are Full Mermaid",
                "Choosing A Diagram Type",
                "should normally carry a diagram",
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
            "skill_architecture.md": (
                "Skill Architecture",
                "Startup Contract Boundary",
                "Existing Skill Homes",
                "Trigger Registry Discipline",
                "Seed / Live Parity",
            ),
            "adr_sweep.md": (
                "ADR Sweep Skill",
                "Recommendation Contract",
                "Level 1 — single orchestrator",
                "Level 2 — bounded read-only fan-out",
                "review-for-adr-promotion",
                "architectural-review-before-promotion",
                "review-membership-or-split",
            ),
            # Anchored on the claims that carry the skill rather than on the
            # measured corpus counts, which the skill itself tells the reader to
            # re-measure before every campaign. What must not silently vanish:
            # the judgment unit is the ADDRESSABLE ordinal (not the D:-bullet
            # count), the pilot is a gate with a pass line, the cap is
            # per-decision, and writes are filed under the ENTRY's date.
            "topic_swarm.md": (
                "Decision-Level Topic Judgment Swarm Skill",
                "The unit is the addressable ordinal, never the decision count",
                "entry_body_decisions",
                "this is the gate",
                "MAX_TOPICS_PER_DECISION = 3",
                "topic-sidecar-date-mismatch",
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
            ".memory-seed/skills/skill_architecture.md",
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

    def test_agent_rules_remain_a_startup_contract_not_an_embedded_runbook(self):
        content = Path(".memory-seed/agent-rules.md").read_text(encoding="utf-8")

        self.assertLessEqual(
            len(content.splitlines()),
            280,
            "agent-rules.md should stay compact enough for startup loading",
        )
        for phrase in (
            "non-deferrable startup contract",
            "Keep procedural details in skills",
            "Change Permission Model",
            "Use the lowest orchestration level",
            "Load `.memory-seed/skills/agent_collaboration.md` for the detailed workflow",
            "Load `.memory-seed/skills/risk_signaling.md` for STOP categories",
            "Load `.memory-seed/skills/skill_architecture.md`",
        ):
            self.assertIn(phrase, content)

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

    def test_seed_registry_entries_are_installed_by_seed_files(self):
        # A registry entry with no shipped file makes `memory-seed init` write a
        # trigger map pointing at a skill it never installs (the 2.19
        # developer-rendered-ui-debugging.md defect). Unlike the live-runtime check
        # above, persona entries are NOT skipped here: the seed ships every skill
        # unconditionally, and skipping them is what hid that defect.
        seed_file_names = set(_seed_files_skill_names())

        for skill in _seed_registry_skill_names():
            self.assertTrue(
                (SEED_SKILLS_DIR / skill).exists(),
                f"{skill} is registered in the seed trigger registry but no file "
                f"exists at {SEED_SKILLS_DIR / skill}",
            )
            self.assertIn(
                skill,
                seed_file_names,
                f"{skill} is registered in the seed trigger registry but has no "
                f"SeedFile entry for '.memory-seed/skills/{skill}' in core.SEED_FILES, "
                "so `memory-seed init` would not install it",
            )

    def test_seed_files_skills_are_registered_in_seed_registry(self):
        # Reverse direction: an installed skill nothing triggers is dead weight —
        # agents lazy-load only what the registry names.
        registry_names = set(_seed_registry_skill_names())

        for skill in _seed_files_skill_names():
            self.assertIn(
                skill,
                registry_names,
                f".memory-seed/skills/{skill} is installed by core.SEED_FILES but has "
                f"no '- skill: {skill}' entry in the seed trigger registry, so no agent "
                "will ever load it",
            )

    def test_every_seeded_skill_runbook_matches_its_live_twin(self):
        # Generic seed/live parity over every shipped skill runbook. The
        # registration checks above prove a skill EXISTS and is TRIGGERED; nothing
        # proved the two copies still say the same thing. Byte parity was asserted
        # only for the skills hand-listed in
        # test_extracted_lazy_skills_are_registered_seeded_and_standalone and the
        # explicit pairs in test_seed_control_plane_matches_live_rationale_guidance,
        # so a skill outside both lists could drift silently — link_swarm.md was in
        # exactly that gap on 2026-07-26 (its twins happened to be identical, but
        # nothing enforced it). Keep this test even though the hand-listed ones
        # overlap it: those pin CONTENT anchors per skill, this pins COVERAGE.
        #
        # Compares seed_file.source rather than re-deriving SEED_SKILLS_DIR / name,
        # so a SeedFile wired to the wrong source file fails here too. Bytes, not
        # text: read_text() applies universal-newline translation, which would let
        # a CRLF/LF divergence pass as equal.
        #
        # .agents/ persona templates are excluded structurally, not by special
        # case — they never match the .memory-seed/skills/ prefix. That is also
        # correct on the merits: they are project-local, evolve with user approval,
        # and are already skipped by test_control_plane_files_report_current_version.
        # Measured 2026-07-26: 4 of 7 live personas already differ from their seed.
        prefix = ".memory-seed/skills/"
        # Runtime-local: projects extend the trigger registry with persona entries,
        # so exact equality is wrong. Seed content is checked for per-line
        # containment in test_skill_trigger_registry_is_deterministic_and_seeded.
        registry = f"{prefix}index.md"
        checked = []
        skipped = []

        for seed_file in SEED_FILES:
            if not seed_file.destination.startswith(prefix):
                continue
            if seed_file.destination == registry:
                skipped.append(seed_file.destination)
                continue
            live = Path(seed_file.destination)
            self.assertTrue(live.exists(), f"missing live skill runbook: {live}")
            self.assertTrue(seed_file.source.exists(), f"missing seed source: {seed_file.source}")
            self.assertEqual(
                live.read_bytes(),
                seed_file.source.read_bytes(),
                f"{seed_file.destination} has drifted from its seed twin "
                f"({seed_file.source}); the two must stay byte-identical",
            )
            checked.append(seed_file.destination)

        # Without a floor this test passes vacuously if the prefix or the
        # SEED_FILES layout changes and the filter stops matching anything.
        self.assertEqual(
            skipped,
            [registry],
            f"{registry} should be the only skill destination exempt from byte parity",
        )
        self.assertGreaterEqual(
            len(checked),
            25,
            f"expected every seeded skill runbook to be checked, only saw {len(checked)}: {checked}",
        )

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
            "<agent>/<kind>/<topic>",
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

    def test_agent_collaboration_documents_clean_session_task_packet_convention(self):
        """Keep the high-signal worker packet anchors explicit and seed-compatible."""
        live_skill = Path(".memory-seed/skills/agent_collaboration.md")
        seed_skill = Path("memory_seed/seed/.memory-seed/skills/agent_collaboration.md")
        content = live_skill.read_text(encoding="utf-8")

        self.assertEqual(content, seed_skill.read_text(encoding="utf-8"))
        for phrase in (
            "Clean-session, high-signal packet convention",
            "documentation-only interoperability conventions",
            "not validated public API",
            "context_load: packet",
            "project_context:",
            "retrieval:",
            "evidence_pack:",
            "materialized_evidence:",
            "context_budget:",
            "memory_update_policy:",
            "100–250-token project",
            "task_fit",
            "downstream_use",
            "relevant accepted or proposed ADR heads",
            "inline Retrieval Specification",
            "ADR current views and decision slices",
            "corpus revision",
            "token_estimate` from the resolver is evidence content only",
            "all-inclusive prepared-context",
            "orchestrator-only searches",
            "debit its actual token cost",
            "including the fetched evidence content",
            "does not replace that all-inclusive debit",
            "Return `NEEDS_CONTEXT` only",
            "memory_update_policy: orchestrator",
            "worker_checkpoint",
            "guarded branch-local append mechanics",
            "Duration alone never changes context, authority, or memory ownership",
            "context_load: full` is reserved",
        ):
            self.assertIn(phrase, content)

    def test_agent_rules_lazy_loading_recommendations_doc_exists(self):
        path = Path("docs/5_Completed/agent-rules-lazy-loading-recommendations.md")
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

    def test_bootstrap_builds_a_thin_durable_authority_chain(self):
        content = Path(".memory-seed/project-bootstrap.md").read_text(encoding="utf-8")

        for phrase in (
            "Durable Decision Classification",
            "--founding-source bootstrap",
            "Unconfirmed assumptions remain proposed",
            "Authority Map",
            "Constitution: none declared",
            "policy thin",
            "may link only accepted ADRs as governing",
        ):
            self.assertIn(phrase, content)

    def test_operating_start_resolves_declared_authority_and_relevant_adrs(self):
        content = Path(".memory-seed/agent-rules.md").read_text(encoding="utf-8")

        for phrase in (
            "declares a ratified Constitution",
            "memory-seed adr list --json",
            "Do not preload the whole ADR corpus",
            "accepted ADR heads",
            "Proposed ADRs and draft Constitutions are evidence",
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

    def test_orientation_carries_the_operating_mode_gate(self):
        # The gate is a routine, not enforcement - its teeth are in the tooling
        # (worktree guard, merge_trigger). Pin the claims that carry it so the
        # routine cannot be gutted into prose while the switches keep firing.
        content = Path(".memory-seed/skills/orientation.md").read_text(encoding="utf-8")

        for phrase in (
            "First message: the operating-mode gate",
            "enforcement class",
            "Tooling-enforced",
            "Config-toggled",
            "Advisory",
            "`--user-approved`, which an agent must never self-supply",
            "Read-only work stops after step 3",
            "None of this is persisted",
        ):
            self.assertIn(phrase, content)

        # Every variable named in the schema must actually appear.
        for variable in (
            "checkout_posture",
            "worktree_decision",
            "integration_mode",
            "merge_trigger",
            "write_intent",
            "risk_tier",
            "orchestration_level",
            "skills_to_load",
            "governing_persona",
            "version_state",
        ):
            self.assertIn(variable, content, f"{variable} missing from the gate schema")

    def test_agent_rules_route_to_the_gate_without_inlining_it(self):
        # agent-rules.md is the startup contract and sits at its line cap, so it
        # points at the gate rather than carrying it (skill_architecture.md:
        # procedural detail lives in skills). Pin both halves of that split.
        rules = Path(".memory-seed/agent-rules.md").read_text(encoding="utf-8")

        self.assertIn("operating-mode gate", rules)
        self.assertIn("first substantive message", rules)
        # The schema tables belong to the skill, not the startup contract.
        self.assertNotIn("Tooling-enforced", rules)
        self.assertNotIn("Config-toggled", rules)

    def test_current_session_files_have_frontmatter_and_entry_metadata(self):
        # Validate EVERY schema-era session file (those with frontmatter), so a
        # malformed new entry fails CI. Pre-schema legacy logs (no frontmatter)
        # are skipped rather than pinning two frozen dates.
        session_files = [doc.path for doc in iter_session_documents(Path(".memory-seed/sessions"))]
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
