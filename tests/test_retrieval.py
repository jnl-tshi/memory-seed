import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from memory_seed.core import check_session_links
from memory_seed.mcp_server import call_tool
from memory_seed.retrieval import (
    entry_diagram_sidecars,
    get_chunk,
    rollup_entry_matches,
    rollup_entry_results,
    search_memory,
)
from memory_seed.semantic_cache import (
    SUPERSEDED_RANK_DAMPING,
    extract_memory_chunks,
    rank_memory_chunks,
)


class RetrievalServiceParityTests(unittest.TestCase):
    """Distribution-plan Phase 1 gate: the MCP tools and the public retrieval
    service must return identical answers for the same corpus and arguments -
    the extraction is a refactor, not a behavior change."""

    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-retrieval-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def write_session(self, cwd, filename, content):
        sessions = cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        path = sessions / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def make_memory_fixture(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:15 - Bootstrap mode check fix\n\n"
            "```yaml\n"
            "entry_id: ms-bootstrap\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "Updated AGENTS.md and agent-rules.md to require checking for initialized memory files.\n\n"
            "### Decision\n\n"
            "- D: Require the bootstrap mode check before operating mode.\n"
            "- R: Agents were skipping bootstrap and operating on an unseeded runtime.\n\n"
            "### Follow-up\n\n"
            "- Watch for bootstrap regressions in agent-rules.\n",
        )
        self.write_session(
            cwd,
            "2026-05-18.md",
            "## 2026-05-18 10:00 - Semble integration\n\n"
            "```yaml\n"
            "entry_id: ms-semble\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "related_entries:\n"
            "  - ms-bootstrap\n"
            "```\n\n"
            "Added Semble guidance for code search routing.\n",
        )
        return cwd

    def test_search_parity_with_mcp_tool(self):
        cwd = self.make_memory_fixture()
        for kwargs in (
            {},
            {"granularity": "section"},
            {"top_k": 1},
            {"recency_enabled": False},
        ):
            with self.subTest(kwargs=kwargs):
                tool_result = call_tool(
                    "memory_search",
                    {"query": "bootstrap mode check", "cwd": str(cwd), "semantic_enabled": False, **kwargs},
                    today=date(2026, 5, 20),
                )
                service_result = search_memory(
                    "bootstrap mode check",
                    str(cwd),
                    semantic_enabled=False,
                    today=date(2026, 5, 20),
                    **kwargs,
                )
                self.assertEqual(tool_result, service_result)
                self.assertTrue(service_result["results"])

    def test_get_chunk_parity_with_mcp_tool(self):
        cwd = self.make_memory_fixture()
        tool_result = call_tool("memory_get_chunk", {"chunk_id": "ms-bootstrap", "cwd": str(cwd)})
        service_result = get_chunk("ms-bootstrap", str(cwd))
        self.assertEqual(tool_result, {"chunk": service_result})
        # Graph metrics from the edge contract ride along identically.
        self.assertEqual(service_result["inbound_relation_count"], 1)
        self.assertIn("importance_score", service_result)
        self.assertIn("superseded_by", service_result)
        self.assertIn("commit_reference_count", service_result)

    def test_get_chunk_unknown_id_raises(self):
        cwd = self.make_memory_fixture()
        with self.assertRaises(ValueError):
            get_chunk("ms-nonexistent", str(cwd))

    def test_branch_field_parses_and_surfaces_read_only(self):
        """The optional record-time `branch:` scalar flows through the parser and
        is surfaced read-only by the shared service (and thus MCP), while an entry
        without it reads as None. `links check` never touches git for it."""
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:15 - Work on a feature branch\n\n"
            "```yaml\n"
            "entry_id: ms-branchful\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "branch: feature/trail-view\n"
            "```\n\n"
            "Did the branch work.\n",
        )
        self.write_session(
            cwd,
            "2026-05-18.md",
            "## 2026-05-18 10:00 - Work with no branch recorded\n\n"
            "```yaml\n"
            "entry_id: ms-branchless\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "Did some work.\n",
        )
        by_id = {c.entry_id: c for c in extract_memory_chunks(str(cwd), granularity="entry")}
        self.assertEqual(by_id["ms-branchful"].branch, "feature/trail-view")
        self.assertIsNone(by_id["ms-branchless"].branch)

        # Surfaced read-only through the shared service (== MCP get_chunk).
        with_branch = get_chunk("ms-branchful", str(cwd))
        self.assertEqual(with_branch["branch"], "feature/trail-view")
        without_branch = get_chunk("ms-branchless", str(cwd))
        self.assertIsNone(without_branch["branch"])
        self.assertEqual(
            call_tool("memory_get_chunk", {"chunk_id": "ms-branchful", "cwd": str(cwd)}),
            {"chunk": with_branch},
        )

        # search_memory result records carry it too.
        results = search_memory("branch work", str(cwd), semantic_enabled=False, today=date(2026, 5, 20))
        branches = {r["entry_id"]: r.get("branch") for r in results["results"]}
        self.assertEqual(branches.get("ms-branchful"), "feature/trail-view")

        # links check stays green and never queries git for branch existence.
        result = check_session_links(str(cwd))
        self.assertEqual([i for i in result.issues if "branch" in i.kind], [])

    def make_sectioned_fixture(self):
        """One entry with two distinct matching subsections + one unrelated entry."""
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-06-01.md",
            "## 2026-06-01 09:00 - Cache invalidation rework\n\n"
            "```yaml\n"
            "entry_id: ms-cache01\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "Reworked the cache layer.\n\n"
            "### Decision\n\n"
            "- D: Use zanzibar tokens for cache keys.\n\n"
            "### Tests\n\n"
            "- T: Added zanzibar token round-trip coverage.\n",
        )
        self.write_session(
            cwd,
            "2026-06-02.md",
            "## 2026-06-02 10:00 - Unrelated docs pass\n\n"
            "```yaml\n"
            "entry_id: ms-docs02\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "Refreshed the README wording.\n",
        )
        return cwd

    def test_rollup_collapses_section_matches_into_one_entry_result(self):
        cwd = self.make_sectioned_fixture()
        pool = [
            *extract_memory_chunks(str(cwd), granularity="entry"),
            *extract_memory_chunks(str(cwd), granularity="section"),
        ]
        ranked = rank_memory_chunks("zanzibar tokens", pool, top_k=len(pool), embedding_provider=None)
        # Multiple chunks from the same entry match ("Decision" + "Tests"
        # sections both mention zanzibar) ...
        matching_ids = {r.chunk.chunk_id for r in ranked if r.matched_fields}
        self.assertGreater(len({cid for cid in matching_ids if cid.startswith("ms-cache01")}), 1)
        # ... but they collapse into ONE visible entry-level record.
        records = rollup_entry_results(ranked, top_k=8)
        cache_records = [r for r in records if r["entry_id"] == "ms-cache01"]
        self.assertEqual(len(cache_records), 1)
        record = cache_records[0]
        # The visible record is the entry, not a section.
        self.assertEqual(record["chunk_id"], "ms-cache01")
        self.assertEqual(record["granularity"], "entry")
        # Best-match/highlight metadata is preserved.
        self.assertIn("best_match_chunk_id", record)
        self.assertIn(record["score_source"], {"entry", "section-rollup"})
        matched_headings = {
            tuple(section["heading_path"]) for section in record["matched_sections"]
        }
        self.assertTrue(matched_headings)
        for section in record["matched_sections"]:
            self.assertTrue(section["chunk_id"].startswith("ms-cache01#"))
            self.assertIn("excerpt", section)
            self.assertIn("line_range", section)

    def test_rollup_representative_prefers_entry_chunk(self):
        cwd = self.make_sectioned_fixture()
        pool = [
            *extract_memory_chunks(str(cwd), granularity="entry"),
            *extract_memory_chunks(str(cwd), granularity="section"),
        ]
        ranked = rank_memory_chunks("zanzibar tokens", pool, top_k=len(pool), embedding_provider=None)
        rollups = rollup_entry_matches(ranked)
        cache_rollup = next(r for r in rollups if r.entry_key == "ms-cache01")
        self.assertEqual(cache_rollup.representative.chunk.granularity, "entry")
        # Only genuinely-matching sections ride along as highlight metadata.
        for section in cache_rollup.sections:
            self.assertTrue(section.matched_fields)

    def test_mcp_section_granularity_is_unchanged_by_rollup(self):
        cwd = self.make_sectioned_fixture()
        result = call_tool(
            "memory_search",
            {
                "query": "zanzibar tokens",
                "cwd": str(cwd),
                "semantic_enabled": False,
                "granularity": "section",
            },
        )
        # Section granularity still returns raw section chunks - no rollup
        # fields leak into the MCP contract.
        section_results = [r for r in result["results"] if r["granularity"] == "section"]
        self.assertTrue(section_results)
        for record in result["results"]:
            self.assertNotIn("matched_sections", record)
            self.assertNotIn("best_match_chunk_id", record)
            self.assertNotIn("score_source", record)

    def write_diagram(self, cwd, filename, content):
        diagrams = cwd / ".memory-seed" / "sessions" / "diagrams"
        diagrams.mkdir(parents=True, exist_ok=True)
        path = diagrams / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def valid_sidecar(self, entry_id, heading_ts, title="Decision flow"):
        return (
            f"## {heading_ts} - {title}\n\n"
            "```yaml\n"
            f"entry_id: {entry_id}\n"
            "```\n\n"
            "```mermaid\n"
            "flowchart TD\n"
            "  A --> B\n"
            "```\n"
        )

    def test_diagram_sidecars_surface_through_the_service(self):
        cwd = self.make_memory_fixture()
        # ms-bootstrap's real entry date (from make_memory_fixture) is
        # 2026-05-17 - the diagrams file is dated to match, mirroring how a
        # human would find the day's diagrams next to that day's session log.
        self.write_diagram(cwd, "2026-05-17.md", self.valid_sidecar("ms-bootstrap", "2026-05-17 09:15"))

        sidecars = entry_diagram_sidecars(str(cwd))
        self.assertIn("ms-bootstrap", sidecars)
        sidecar = sidecars["ms-bootstrap"]
        self.assertEqual(sidecar["title"], "Decision flow")
        self.assertEqual(sidecar["heading_datetime"], "2026-05-17 09:15")
        self.assertEqual(sidecar["mermaid_block_count"], 1)
        # Raw Mermaid source is surfaced for client-side rendering (Arc 2d),
        # fenced text only - no Mermaid semantics parsed here.
        self.assertEqual(sidecar["mermaid_blocks"], ["flowchart TD\n  A --> B"])
        self.assertTrue(sidecar["path"].endswith(".memory-seed/sessions/diagrams/2026-05-17.md"))

        # get_chunk attaches sidecar metadata only when asked - the MCP tool
        # contract (no include_diagrams) stays byte-identical.
        enriched = get_chunk("ms-bootstrap", str(cwd), include_diagrams=True)
        self.assertEqual(len(enriched["diagrams"]), 1)
        self.assertEqual(enriched["diagrams"][0]["entry_id"], "ms-bootstrap")
        plain = get_chunk("ms-bootstrap", str(cwd))
        self.assertNotIn("diagrams", plain)
        mcp = call_tool("memory_get_chunk", {"chunk_id": "ms-bootstrap", "cwd": str(cwd)})
        self.assertNotIn("diagrams", mcp["chunk"])

        # Entries without a sidecar surface an empty list when asked.
        other = get_chunk("ms-semble", str(cwd), include_diagrams=True)
        self.assertEqual(other["diagrams"], [])

    def test_grouped_diagram_sidecars_surface_through_the_service(self):
        cwd = self.make_memory_fixture()
        self.write_diagram(cwd, "2026-05/2026-05-17.md", self.valid_sidecar("ms-bootstrap", "2026-05-17 09:15"))

        sidecars = entry_diagram_sidecars(str(cwd))

        self.assertIn("ms-bootstrap", sidecars)
        self.assertTrue(sidecars["ms-bootstrap"]["path"].endswith(".memory-seed/sessions/diagrams/2026-05/2026-05-17.md"))
        enriched = get_chunk("ms-bootstrap", str(cwd), include_diagrams=True)
        self.assertEqual(enriched["diagrams"][0]["entry_id"], "ms-bootstrap")

    def test_diagram_sidecars_multiple_entries_append_to_one_date_file(self):
        # Two decisions logged the same day append to the same dated file,
        # exactly like session logs - each block keyed by its own entry_id.
        cwd = self.make_memory_fixture()
        combined = (
            self.valid_sidecar("ms-bootstrap", "2026-05-17 09:15", title="Bootstrap flow")
            + "\n"
            + self.valid_sidecar("ms-semble", "2026-05-18 10:00", title="Semble routing")
        )
        # File dated to ms-bootstrap; ms-semble's block will mismatch below.
        self.write_diagram(cwd, "2026-05-17.md", combined)
        sidecars = entry_diagram_sidecars(str(cwd))
        self.assertEqual(sidecars["ms-bootstrap"]["title"], "Bootstrap flow")
        self.assertEqual(sidecars["ms-semble"]["title"], "Semble routing")

    def test_links_check_validates_diagram_sidecars(self):
        cwd = self.make_memory_fixture()
        # Valid: filed under the entry's actual date, entry_id resolves.
        self.write_diagram(cwd, "2026-05-17.md", self.valid_sidecar("ms-bootstrap", "2026-05-17 09:15"))
        result = check_session_links(str(cwd))
        self.assertTrue(result.ok, [i.detail for i in result.issues])

        # orphan-diagram: entry_id resolves to no known entry.
        self.write_diagram(cwd, "2026-05-17.md", self.valid_sidecar("ms-ghost", "2026-05-17 09:15"))
        kinds = {i.kind for i in check_session_links(str(cwd)).issues}
        self.assertIn("orphan-diagram", kinds)

        # diagram-date-mismatch: entry_id is real (ms-semble, logged 2026-05-18)
        # but filed under the wrong dated file.
        self.write_diagram(cwd, "2026-05-17.md", self.valid_sidecar("ms-semble", "2026-05-18 10:00"))
        kinds = {i.kind for i in check_session_links(str(cwd)).issues}
        self.assertIn("diagram-date-mismatch", kinds)

        # The same validation contract applies to grouped sidecars.
        grouped_cwd = self.make_memory_fixture()
        self.write_diagram(grouped_cwd, "2026-05/2026-05-17.md", self.valid_sidecar("ms-bootstrap", "2026-05-17 09:15"))
        self.assertTrue(check_session_links(str(grouped_cwd)).ok)
        self.write_diagram(grouped_cwd, "2026-05/2026-05-17.md", self.valid_sidecar("ms-semble", "2026-05-18 10:00"))
        kinds = {i.kind for i in check_session_links(str(grouped_cwd)).issues}
        self.assertIn("diagram-date-mismatch", kinds)

    def test_links_check_flags_malformed_diagrams(self):
        cwd = self.make_memory_fixture()
        # Filename isn't a YYYY-MM-DD.md date.
        self.write_diagram(cwd, "notes.md", "some content\n")
        self.assertIn("malformed-diagram", {i.kind for i in check_session_links(str(cwd)).issues})

        # Grouped filename must live under the matching YYYY-MM month folder.
        self.write_diagram(cwd, "2026-06/2026-05-17.md", self.valid_sidecar("ms-bootstrap", "2026-05-17 09:15"))
        self.assertIn("malformed-diagram", {i.kind for i in check_session_links(str(cwd)).issues})

        # Valid date filename but no '## <ts> - <title>' + yaml block at all.
        self.write_diagram(cwd, "2026-05-17.md", "```mermaid\nflowchart TD\n  A --> B\n```\n")
        self.assertIn("malformed-diagram", {i.kind for i in check_session_links(str(cwd)).issues})

        # Heading + yaml block present, but yaml block has no entry_id.
        self.write_diagram(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:15 - No id\n\n```yaml\ntitle: no id\n```\n\n```mermaid\nA --> B\n```\n",
        )
        self.assertIn("malformed-diagram", {i.kind for i in check_session_links(str(cwd)).issues})

        # entry_id present but no mermaid block.
        self.write_diagram(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:15 - No diagram\n\n```yaml\nentry_id: ms-bootstrap\n```\n\nJust prose.\n",
        )
        self.assertIn("malformed-diagram", {i.kind for i in check_session_links(str(cwd)).issues})

        # Unbalanced fence.
        self.write_diagram(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:15 - Unbalanced\n\n```yaml\nentry_id: ms-bootstrap\n```\n\n"
            "```mermaid\nflowchart TD\n  A --> B\n",
        )
        self.assertIn("malformed-diagram", {i.kind for i in check_session_links(str(cwd)).issues})

    def test_links_check_ok_without_diagrams_dir(self):
        cwd = self.make_memory_fixture()
        result = check_session_links(str(cwd))
        self.assertTrue(result.ok)
        # Sidecars are optional: entries without diagrams are never an issue.
        self.assertEqual(entry_diagram_sidecars(str(cwd)), {})

    def test_service_is_mcp_independent(self):
        # The service must not import the MCP layer: the dependency points
        # from mcp_server to retrieval, never back (distribution-plan gate).
        import ast

        import memory_seed.retrieval as retrieval_module

        tree = ast.parse(Path(retrieval_module.__file__).read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        self.assertFalse([name for name in imported if "mcp_server" in name], imported)


class FreshnessRankingTests(unittest.TestCase):
    """Freshness-aware ranking guardrails (freshness-aware-memory-ranking-proposal.md).

    The default-off supersession rank-dampener must let a live replacement
    out-rank the decision it supersedes when opted in, source the signal from the
    sidecar-augmented graph, never bury an evolved-but-valid entry, and leave the
    default order byte-for-byte unchanged when the flag is off. The fixture is
    deliberately built so recency does NOT decide it: the superseded (older) entry
    has the stronger textual match, so without the damper it out-ranks its
    replacement (the very bug the proposal fixes) - the damper is what flips it.
    """

    TODAY = date(2026, 5, 20)
    OLD = "mse_0123456789abcdef"  # superseded decision (older, strong match)
    NEW = "mse_ffffffffffffffff"  # live replacement (newer, weaker match)
    QUERY = "redis cache ttl invalidation strategy"

    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-freshness-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def write_session(self, cwd, filename, content):
        path = cwd / ".memory-seed" / "sessions" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def make_supersession_fixture(self, *, sidecar=False):
        """OLD (strong match) is superseded by NEW (weaker match). The supersedes
        edge lives in NEW's entry YAML, or - when ``sidecar=True`` - only in an
        append-only link sidecar keyed to NEW."""
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:15 - Redis cache TTL invalidation strategy\n\n"
            "```yaml\n"
            f"entry_id: {self.OLD}\n"
            "user_initials: JN\nagent_type: codex\nproject_path: .\nsubproject_path: null\n"
            "```\n\n"
            "### Decision\n\n"
            "- D: Use a Redis cache TTL invalidation strategy.\n"
            "- R: Needed a cache eviction approach.\n",
        )
        supersedes_yaml = "" if sidecar else f"supersedes:\n  - {self.OLD}\n"
        self.write_session(
            cwd,
            "2026-05-18.md",
            "## 2026-05-18 10:00 - Cache TTL rework\n\n"
            "```yaml\n"
            f"entry_id: {self.NEW}\n"
            "user_initials: JN\nagent_type: codex\nproject_path: .\nsubproject_path: null\n"
            f"{supersedes_yaml}"
            "```\n\n"
            "### Decision\n\n"
            "- D: Replace it; redis cache ttl invalidation strategy revisited.\n"
            "- R: Superseded the earlier cache decision.\n",
        )
        if sidecar:
            links_dir = cwd / ".memory-seed" / "sessions" / "links" / "2026-05"
            links_dir.mkdir(parents=True, exist_ok=True)
            (links_dir / "2026-05-18.md").write_text(
                "## 2026-05-18 10:05 - late supersedes edge\n\n"
                "```yaml\n"
                f"entry_id: {self.NEW}\n"
                f"supersedes:\n  - {self.OLD}\n"
                "```\n",
                encoding="utf-8",
            )
        return cwd

    def make_superseding_chain_fixture(self):
        """OLD is superseded by MID in YAML, and MID is superseded by NEW only
        through a late link sidecar. The effective graph should surface NEW as
        the terminal live replacement for both retired entries."""
        cwd = self.make_project()
        old_id = "mse_oldchain000000"
        mid_id = "mse_midchain000000"
        new_id = "mse_newchain000000"
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-05-17 09:15 - Redis cache TTL invalidation strategy\n\n"
            "```yaml\n"
            f"entry_id: {old_id}\n"
            "user_initials: JN\nagent_type: codex\nproject_path: .\nsubproject_path: null\n"
            "```\n\n"
            "### Decision\n\n"
            "- D: Use the first cache ttl invalidation strategy.\n",
        )
        self.write_session(
            cwd,
            "2026-05-18.md",
            "## 2026-05-18 10:00 - Cache TTL rework\n\n"
            "```yaml\n"
            f"entry_id: {mid_id}\n"
            "user_initials: JN\nagent_type: codex\nproject_path: .\nsubproject_path: null\n"
            f"supersedes:\n  - {old_id}\n"
            "```\n\n"
            "### Decision\n\n"
            "- D: Replace the first cache ttl invalidation strategy.\n",
        )
        self.write_session(
            cwd,
            "2026-05-19.md",
            "## 2026-05-19 11:00 - Final cache TTL plan\n\n"
            "```yaml\n"
            f"entry_id: {new_id}\n"
            "user_initials: JN\nagent_type: codex\nproject_path: .\nsubproject_path: null\n"
            "```\n\n"
            "### Decision\n\n"
            "- D: Final cache ttl invalidation strategy.\n",
        )
        links_dir = cwd / ".memory-seed" / "sessions" / "links" / "2026-05"
        links_dir.mkdir(parents=True, exist_ok=True)
        (links_dir / "2026-05-19.md").write_text(
            "## 2026-05-19 11:05 - late supersedes edge\n\n"
            "```yaml\n"
            f"entry_id: {new_id}\n"
            f"supersedes:\n  - {mid_id}\n"
            "```\n",
            encoding="utf-8",
        )
        return cwd, old_id, mid_id, new_id

    def make_independent_lineage_fixture(self):
        cwd = self.make_project()
        old_a = "mse_lineagea_old00"
        new_a = "mse_lineagea_new00"
        old_b = "mse_lineageb_old00"
        new_b = "mse_lineageb_new00"
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## 2026-06-15 02:15 - Updated 3.0 plan decisions\n\n"
            "```yaml\n"
            f"entry_id: {old_a}\n"
            "user_initials: JN\nagent_type: codex\nproject_path: .\nsubproject_path: null\n"
            "```\n\n"
            "Lineage A retired plan decisions.\n\n"
            "## 2026-07-15 17:46 - Sense-check roadmap plan decisions\n\n"
            "```yaml\n"
            f"entry_id: {old_b}\n"
            "user_initials: JN\nagent_type: codex\nproject_path: .\nsubproject_path: null\n"
            "```\n\n"
            "Lineage B also shares plan decisions wording.\n\n"
            "## 2026-07-10 15:36 - Retirement record: lineage A plan decisions\n\n"
            "```yaml\n"
            f"entry_id: {new_a}\n"
            "user_initials: JN\nagent_type: codex\nproject_path: .\nsubproject_path: null\n"
            f"supersedes:\n  - {old_a}\n"
            "```\n\n"
            "Terminal replacement for lineage A plan decisions.\n\n"
            "## 2026-07-15 18:05 - Constitution-harden lineage B plan decisions\n\n"
            "```yaml\n"
            f"entry_id: {new_b}\n"
            "user_initials: JN\nagent_type: codex\nproject_path: .\nsubproject_path: null\n"
            f"supersedes:\n  - {old_b}\n"
            "```\n\n"
            "Terminal replacement for lineage B plan decisions.\n",
        )
        for i in range(1, 9):
            self.write_session(
                cwd,
                f"2026-05-{17+i}.md",
                f"## 2026-05-{17+i:02d} 09:00 - Distractor {i}\n\n"
                "```yaml\n"
                f"entry_id: mse_distractor_{i:02d}\n"
                "user_initials: JN\nagent_type: codex\nproject_path: .\nsubproject_path: null\n"
                "```\n\n"
                "Plan decisions distractor text.\n",
            )
        return cwd, old_a, new_a, old_b, new_b

    def search(self, cwd, **kwargs):
        return search_memory(
            self.QUERY, str(cwd), semantic_enabled=False, today=self.TODAY, **kwargs
        )

    def test_supersession_damping_ranks_replacement_above_retired(self):
        """(a) With the flag ON, the live replacement out-ranks the decision it
        supersedes, while the retired entry stays fully retrievable (down-rank
        only, never hidden)."""
        cwd = self.make_supersession_fixture()
        # Opting out (supersession_damping=False) is the pre-change baseline: the
        # retired-but-strongly-matching decision out-ranks its replacement.
        off = self.search(cwd, supersession_damping=False, superseding_successor_boost=False)
        self.assertEqual([r["entry_id"] for r in off["results"]][0], self.OLD)
        by_off = {r["entry_id"]: r for r in off["results"]}

        on = self.search(cwd, supersession_damping=True, superseding_successor_boost=False)
        on_order = [r["entry_id"] for r in on["results"]]
        by_on = {r["entry_id"]: r for r in on["results"]}
        # The replacement now ranks above the decision it supersedes...
        self.assertEqual(on_order[0], self.NEW)
        # ...and the superseded entry is still present - never a hard exclusion.
        self.assertIn(self.OLD, on_order)
        # Only the superseded entry is damped; the replacement's score is untouched.
        self.assertEqual(by_on[self.NEW]["score"], by_off[self.NEW]["score"])
        self.assertLess(by_on[self.OLD]["score"], by_off[self.OLD]["score"])
        self.assertAlmostEqual(
            by_on[self.OLD]["score"],
            by_off[self.OLD]["score"] * SUPERSEDED_RANK_DAMPING,
            places=6,
        )

    def test_supersession_damping_from_link_sidecar(self):
        """(b) The SAME flip when the supersedes edge lives ONLY in a link
        sidecar - proving the dampener is sourced from the sidecar-augmented
        graph, not just entry YAML."""
        cwd = self.make_supersession_fixture(sidecar=True)
        # The replacement's entry YAML carries no supersedes edge; it exists only
        # in the sidecar.
        raw = {c.entry_id: c for c in extract_memory_chunks(str(cwd), granularity="entry")}
        self.assertEqual(raw[self.NEW].supersedes, ())

        off = self.search(cwd, supersession_damping=False, superseding_successor_boost=False)
        self.assertEqual([r["entry_id"] for r in off["results"]][0], self.OLD)

        on = self.search(cwd, supersession_damping=True, superseding_successor_boost=False)
        on_order = [r["entry_id"] for r in on["results"]]
        by_on = {r["entry_id"]: r for r in on["results"]}
        self.assertEqual(on_order[0], self.NEW)
        self.assertIn(self.OLD, on_order)
        # The sidecar-authored supersession reached the ranker (and the exposed field).
        self.assertEqual(by_on[self.OLD]["superseded_by"], [self.NEW])

    def test_superseding_head_surfaces_terminal_live_replacement(self):
        cwd, old_id, mid_id, new_id = self.make_superseding_chain_fixture()

        payload = search_memory(
            "cache ttl invalidation strategy",
            str(cwd),
            semantic_enabled=False,
            today=self.TODAY,
            superseding_successor_boost=False,
        )
        by_id = {result["entry_id"]: result for result in payload["results"]}
        old_chunk = get_chunk(old_id, str(cwd))
        mid_chunk = get_chunk(mid_id, str(cwd))
        new_chunk = get_chunk(new_id, str(cwd))

        self.assertEqual(by_id[old_id]["superseded_by"], [mid_id])
        self.assertEqual(by_id[old_id]["superseding_head"], [new_id])
        self.assertEqual(by_id[mid_id]["superseded_by"], [new_id])
        self.assertEqual(by_id[mid_id]["superseding_head"], [new_id])
        self.assertEqual(by_id[new_id]["superseding_head"], [])
        self.assertEqual(old_chunk["superseding_head"], [new_id])
        self.assertEqual(mid_chunk["superseding_head"], [new_id])
        self.assertEqual(new_chunk["superseding_head"], [])

    def test_superseding_successor_boost_is_explicit_and_bounded(self):
        cwd = self.make_supersession_fixture()

        without = self.search(cwd, supersession_damping=True, superseding_successor_boost=False)
        with_boost = self.search(cwd, supersession_damping=True, superseding_successor_boost=True)
        by_without = {r["entry_id"]: r for r in without["results"]}
        by_with = {r["entry_id"]: r for r in with_boost["results"]}

        # The retired entry stays damped exactly as before; only the already-
        # matching live replacement gets a lift.
        self.assertEqual(by_with[self.OLD]["score"], by_without[self.OLD]["score"])
        self.assertGreater(by_with[self.NEW]["score"], by_without[self.NEW]["score"])

    def test_superseding_successor_boost_is_now_on_by_default_with_opt_out(self):
        cwd = self.make_supersession_fixture()

        default = self.search(cwd)
        explicit_on = self.search(cwd, superseding_successor_boost=True)
        explicit_off = self.search(cwd, superseding_successor_boost=False)
        by_default = {r["entry_id"]: r for r in default["results"]}
        by_off = {r["entry_id"]: r for r in explicit_off["results"]}

        self.assertEqual(default["results"], explicit_on["results"])
        self.assertGreater(by_default[self.NEW]["score"], by_off[self.NEW]["score"])

    def test_query_for_one_lineage_does_not_boost_independent_lineage_head(self):
        cwd, old_a, new_a, old_b, new_b = self.make_independent_lineage_fixture()
        query = "2026-06-15 02:15 - Updated 3.0 plan decisions"

        without = search_memory(
            query,
            str(cwd),
            semantic_enabled=False,
            today=self.TODAY,
            supersession_damping=True,
            superseding_successor_boost=False,
            top_k=8,
        )
        with_boost = search_memory(
            query,
            str(cwd),
            semantic_enabled=False,
            today=self.TODAY,
            supersession_damping=True,
            superseding_successor_boost=True,
            top_k=8,
        )
        by_without = {r["entry_id"]: r for r in without["results"]}
        by_with = {r["entry_id"]: r for r in with_boost["results"]}
        order_without = [r["entry_id"] for r in without["results"]]
        order_with = [r["entry_id"] for r in with_boost["results"]]

        self.assertIn(new_a, order_with)
        self.assertGreater(by_with[new_a]["score"], by_without.get(new_a, {"score": 0})["score"])
        if new_b in by_without:
            self.assertEqual(by_with[new_b]["score"], by_without[new_b]["score"])
            self.assertGreaterEqual(order_with.index(new_b), order_without.index(new_b))

    def make_evolves_fixture(self):
        """A three-entry evolves chain: C evolves B, B evolves A. All still
        valid; A is the base, C is the current fuller form (head of lineage)."""
        cwd = self.make_project()
        chain = [
            ("2026-05-15.md", "2026-05-15 09:00 - Session logging cadence", self.A, None),
            ("2026-05-16.md", "2026-05-16 09:00 - Session logging cadence refined", self.B, self.A),
            ("2026-05-17.md", "2026-05-17 09:00 - Session logging cadence finalized", self.C, self.B),
        ]
        for filename, heading, entry_id, evolves in chain:
            evolves_yaml = f"evolves:\n  - {evolves}\n" if evolves else ""
            self.write_session(
                cwd,
                filename,
                f"## {heading}\n\n"
                "```yaml\n"
                f"entry_id: {entry_id}\n"
                "user_initials: JN\nagent_type: codex\nproject_path: .\nsubproject_path: null\n"
                f"{evolves_yaml}"
                "```\n\n"
                "### Decision\n\n"
                "- D: Session logging cadence approach.\n"
                "- R: Keep a consistent session logging cadence.\n",
            )
        return cwd

    A = "mse_aaaaaaaaaaaaaaaa"
    B = "mse_bbbbbbbbbbbbbbbb"
    C = "mse_cccccccccccccccc"

    def test_evolves_chain_not_buried_and_successor_surfaced(self):
        """(c) An evolved-but-valid entry is NOT down-ranked (evolves is exempt
        from the dampener) and its successor / head-of-lineage is surfaced so the
        current fuller form is reachable."""
        cwd = self.make_evolves_fixture()
        off = self.search(cwd, supersession_damping=False)
        on = self.search(cwd, supersession_damping=True)
        by_off = {r["entry_id"]: r for r in off["results"]}
        by_on = {r["entry_id"]: r for r in on["results"]}

        # Evolves never dampens: every score is identical with the flag on or off,
        # even under supersession_damping=True.
        for eid in (self.A, self.B, self.C):
            self.assertIn(eid, by_on)
            self.assertEqual(by_on[eid]["score"], by_off[eid]["score"])
            self.assertEqual(by_on[eid]["superseded_by"], [])

        # The successor is surfaced: the base and the middle point to the head of
        # the lineage (C), followed transitively; the head points nowhere further.
        self.assertEqual(by_on[self.A]["evolved_head"], [self.C])
        self.assertEqual(by_on[self.B]["evolved_head"], [self.C])
        self.assertEqual(by_on[self.C]["evolved_head"], [])
        # The immediate successor stays exposed too (unchanged behavior).
        self.assertEqual(by_on[self.A]["evolved_by"], [self.B])

    def test_default_now_damps_and_opt_out_restores_order(self):
        """(d) The dampener is ON by default: a bare search - and the MCP
        `memory_search` tool with no flag - demotes the superseded entry beneath
        its live replacement, and supersession_damping=False restores the
        pre-change full-weight order. The default agent-facing behavior is damped."""
        cwd = self.make_supersession_fixture()
        default = self.search(cwd)
        on = self.search(cwd, supersession_damping=True)
        # The default now equals the (damped) opted-in behavior, byte for byte.
        self.assertEqual(default["results"], on["results"])
        self.assertEqual([r["entry_id"] for r in default["results"]][0], self.NEW)
        # The MCP tool default (no flag supplied) damps too - the agent-facing surface.
        tool_default = call_tool(
            "memory_search",
            {"query": self.QUERY, "cwd": str(cwd), "semantic_enabled": False},
            today=self.TODAY,
        )
        self.assertEqual([r["entry_id"] for r in tool_default["results"]][0], self.NEW)
        # Opting out restores the pre-change order: the superseded entry on top.
        explicit_off = self.search(cwd, supersession_damping=False)
        order_off = [r["entry_id"] for r in explicit_off["results"]]
        self.assertEqual(order_off, [self.OLD, self.NEW])
        self.assertNotEqual([r["entry_id"] for r in default["results"]], order_off)


if __name__ == "__main__":
    unittest.main()
