import math
import shutil
import tempfile
import unittest
from datetime import date
from datetime import datetime
from pathlib import Path

from memory_seed.semantic_cache import (
    SUPERSEDED_IMPORTANCE_DAMPING,
    MemoryChunk,
    build_related_entry_graph,
    extract_memory_chunks,
    rank_memory_chunks,
    rank_session_memory,
    suggest_related_entries,
)


class StaticEmbeddingProvider:
    def __init__(self, vectors):
        self.vectors = vectors

    def embed(self, texts):
        return [self.vectors[text] for text in texts]


class FailingEmbeddingProvider:
    def embed(self, texts):
        raise RuntimeError("embedding unavailable")


class SemanticCacheTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-semantic-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def write_session(self, cwd, filename, content):
        sessions = cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        path = sessions / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_extracts_entry_bounded_chunks_with_yaml_metadata_by_default(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-18.md",
            "# Session Log - 2026-05-18\n\n"
            "## 2026-05-18 10:30 - Ranking Engine\n\n"
            "```yaml\n"
            "entry_id: ms-ranking1\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "Build token_harvester around `.AGENTS/context.md` and memory-seed.\n\n"
            "### Target Discovery\n\n"
            "Use #target-discovery for exact matching.\n",
        )

        chunks = extract_memory_chunks(cwd)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].source_file, "2026-05-18.md")
        self.assertEqual(chunks[0].session_date, date(2026, 5, 18))
        self.assertEqual(chunks[0].entry_datetime, datetime(2026, 5, 18, 10, 30))
        self.assertEqual(chunks[0].chunk_id, "ms-ranking1")
        self.assertEqual(chunks[0].entry_id, "ms-ranking1")
        self.assertEqual(chunks[0].user_initials, "JN")
        self.assertEqual(chunks[0].agent_type, "codex")
        self.assertEqual(chunks[0].project_path, ".")
        self.assertIsNone(chunks[0].subproject_path)
        self.assertEqual(chunks[0].heading_path, ("2026-05-18 10:30 - Ranking Engine",))
        self.assertEqual(chunks[0].sections, ("Target Discovery",))
        self.assertEqual(chunks[0].granularity, "entry")
        self.assertIn("target-discovery", chunks[0].tags)
        self.assertIn("token_harvester", chunks[0].lexical_terms)
        self.assertIn("memory-seed", chunks[0].lexical_terms)
        self.assertIn(".AGENTS/context.md", chunks[0].lexical_terms)

    def test_extracts_section_chunks_with_entry_id_parent_metadata(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-18.md",
            "## 2026-05-18 10:30 - Ranking Engine\n\n"
            "```yaml\n"
            "entry_id: ms-ranking1\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: packages/core\n"
            "```\n\n"
            "### Summary\n\n"
            "Build token_harvester around `.memory-seed/index.md`.\n\n"
            "### Decisions\n\n"
            "#### D1 - Preserve entry chunks\n\n"
            "- D: Use entry chunks by default.\n",
        )

        chunks = extract_memory_chunks(cwd, granularity="section")

        self.assertEqual(
            [chunk.chunk_id for chunk in chunks],
            [
                "ms-ranking1#summary",
                "ms-ranking1#decisions",
                "ms-ranking1#decisions/d1-preserve-entry-chunks",
            ],
        )
        self.assertTrue(all(chunk.entry_id == "ms-ranking1" for chunk in chunks))
        self.assertTrue(all(chunk.entry_title == "2026-05-18 10:30 - Ranking Engine" for chunk in chunks))
        self.assertTrue(all(chunk.subproject_path == "packages/core" for chunk in chunks))
        self.assertEqual(chunks[2].heading_path, ("2026-05-18 10:30 - Ranking Engine", "Decisions", "D1 - Preserve entry chunks"))
        self.assertEqual(chunks[2].granularity, "section")

    def test_extracts_optional_entry_datetime_from_session_heading(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-19.md",
            "## 2026-05-19 20:42 - Durable memory consolidation\n\n"
            "Promoted durable facts.\n",
        )

        chunks = extract_memory_chunks(cwd)

        self.assertEqual(chunks[0].entry_datetime, datetime(2026, 5, 19, 20, 42))
        self.assertEqual(chunks[0].title, "2026-05-19 20:42 - Durable memory consolidation")
        self.assertIsNone(chunks[0].entry_id)
        self.assertNotEqual(chunks[0].chunk_id, "")

    def test_ignores_non_date_session_files(self):
        cwd = self.make_project()
        self.write_session(cwd, "notes.md", "## Should not index\n\n#tag\n")
        self.write_session(cwd, "2026-05-18.md", "## Valid\n\nUseful content.\n")

        chunks = extract_memory_chunks(cwd)

        self.assertEqual([chunk.source_file for chunk in chunks], ["2026-05-18.md"])

    def test_extracts_per_user_session_file_with_date_from_directory(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-06-21/jean.md",
            "---\n"
            "schema_version: 2\n"
            "session_date: 2026-06-21\n"
            "hash_id: msm_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
            "user: jean\n"
            "created_at: 2026-06-21T00:00:00Z\n"
            "---\n\n"
            "## 2026-06-21 09:30 - Per-user memory\n\n"
            "```yaml\n"
            "entry_id: ms-jean1\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "Dual-read discovery works.\n",
        )

        chunks = extract_memory_chunks(cwd)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].chunk_id, "ms-jean1")
        self.assertEqual(chunks[0].session_date, date(2026, 6, 21))
        self.assertEqual(chunks[0].source_file, "jean.md")
        self.assertEqual(chunks[0].source_path, ".memory-seed/sessions/2026-06-21/jean.md")
        self.assertEqual(chunks[0].user, "jean")
        self.assertEqual(chunks[0].file_hash_id, "msm_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

    def test_extracts_month_grouped_flat_and_per_user_sessions(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-06/2026-06-21.md",
            "## 2026-06-21 09:00 - Month flat memory\n\n"
            "```yaml\n"
            "entry_id: ms-monthflat\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "Grouped flat discovery works.\n",
        )
        self.write_session(
            cwd,
            "2026-06/2026-06-22/jean.md",
            "---\n"
            "schema_version: 2\n"
            "session_date: 2026-06-22\n"
            "hash_id: msm_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n"
            "user: jean\n"
            "---\n\n"
            "## 2026-06-22 09:30 - Month per-user memory\n\n"
            "```yaml\n"
            "entry_id: ms-monthuser\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "Grouped per-user discovery works.\n",
        )

        chunks = extract_memory_chunks(cwd)
        by_id = {chunk.entry_id: chunk for chunk in chunks}

        self.assertEqual(by_id["ms-monthflat"].source_path, ".memory-seed/sessions/2026-06/2026-06-21.md")
        self.assertIsNone(by_id["ms-monthflat"].user)
        self.assertEqual(by_id["ms-monthuser"].source_path, ".memory-seed/sessions/2026-06/2026-06-22/jean.md")
        self.assertEqual(by_id["ms-monthuser"].source_file, "jean.md")
        self.assertEqual(by_id["ms-monthuser"].user, "jean")
        self.assertEqual(by_id["ms-monthuser"].file_hash_id, "msm_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")

    def test_extracts_entry_level_related_entries(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-06-21/jean.md",
            "---\n"
            "schema_version: 2\n"
            "session_date: 2026-06-21\n"
            "hash_id: msm_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
            "user: jean\n"
            "---\n\n"
            "## 2026-06-21 09:30 - Linked memory\n\n"
            "```yaml\n"
            "entry_id: mse_0123456789abcdef\n"
            "related_entries:\n"
            "  - ms-11111111\n"
            "  - mse_fedcba9876543210\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            "Linked search text.\n",
        )

        chunks = extract_memory_chunks(cwd)

        self.assertEqual(chunks[0].related_entries, ("ms-11111111", "mse_fedcba9876543210"))

    def test_fallback_chunk_ids_include_date_qualified_source_path(self):
        cwd = self.make_project()
        self.write_session(cwd, "2026-06-21/jean.md", "## Same title\n\nFirst text.\n")
        self.write_session(cwd, "2026-06-22/jean.md", "## Same title\n\nSecond text.\n")

        chunks = extract_memory_chunks(cwd)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(len({chunk.chunk_id for chunk in chunks}), 2)
        self.assertTrue(all(chunk.chunk_id.startswith(".memory-seed/sessions/") for chunk in chunks))

    def test_lexical_metadata_match_outranks_body_only_match(self):
        today = date(2026, 5, 19)
        metadata_chunk = MemoryChunk(
            chunk_id="a",
            source_path=".AGENTS/sessions/2026-05-18.md",
            source_file="2026-05-18.md",
            session_date=date(2026, 5, 18),
            entry_datetime=None,
            heading_path=("Target Discovery",),
            heading_level=2,
            title="Target Discovery",
            text="Short note.",
            tags=("target-discovery",),
            contexts=(),
            lexical_terms=(),
            start_line=1,
            end_line=3,
        )
        body_chunk = MemoryChunk(
            chunk_id="b",
            source_path=".AGENTS/sessions/2026-05-18.md",
            source_file="2026-05-18.md",
            session_date=date(2026, 5, 18),
            entry_datetime=None,
            heading_path=("Other",),
            heading_level=2,
            title="Other",
            text="target discovery target discovery target discovery",
            tags=(),
            contexts=(),
            lexical_terms=(),
            start_line=4,
            end_line=6,
        )

        ranked = rank_memory_chunks("#target-discovery", [body_chunk, metadata_chunk], today=today)

        self.assertEqual(ranked[0].chunk.chunk_id, "a")
        self.assertIn("tags", ranked[0].matched_fields)

    def test_semantic_provider_contributes_cosine_similarity(self):
        today = date(2026, 5, 19)
        chunk = MemoryChunk(
            chunk_id="semantic",
            source_path=".AGENTS/sessions/2026-05-19.md",
            source_file="2026-05-19.md",
            session_date=today,
            entry_datetime=None,
            heading_path=("Embedding",),
            heading_level=2,
            title="Embedding",
            text="semantic payload",
            tags=(),
            contexts=(),
            lexical_terms=(),
            start_line=1,
            end_line=2,
        )
        provider = StaticEmbeddingProvider(
            {
                "architecture query": (1.0, 0.0),
                "semantic payload": (1.0, 0.0),
            }
        )

        ranked = rank_memory_chunks(
            "architecture query",
            [chunk],
            today=today,
            embedding_provider=provider,
        )

        self.assertIsNotNone(ranked[0].semantic_score)
        self.assertTrue(math.isclose(ranked[0].semantic_score, 1.0))

    def test_embedding_failures_fall_back_to_lexical_scoring(self):
        today = date(2026, 5, 19)
        chunk = MemoryChunk(
            chunk_id="lexical",
            source_path=".AGENTS/sessions/2026-05-19.md",
            source_file="2026-05-19.md",
            session_date=today,
            entry_datetime=None,
            heading_path=("Control Plane",),
            heading_level=2,
            title="Control Plane",
            text="control plane note",
            tags=(),
            contexts=(),
            lexical_terms=("control-plane",),
            start_line=1,
            end_line=2,
        )

        ranked = rank_memory_chunks(
            "control plane",
            [chunk],
            today=today,
            embedding_provider=FailingEmbeddingProvider(),
        )

        self.assertEqual(ranked[0].chunk.chunk_id, "lexical")
        self.assertIsNone(ranked[0].semantic_score)
        self.assertGreater(ranked[0].lexical_score, 0)

    def test_recency_decay_and_floor_are_applied(self):
        today = date(2026, 5, 19)
        fresh = MemoryChunk(
            chunk_id="fresh",
            source_path=".AGENTS/sessions/2026-05-19.md",
            source_file="2026-05-19.md",
            session_date=today,
            entry_datetime=None,
            heading_path=("Topic",),
            heading_level=2,
            title="Topic",
            text="ranking note",
            tags=("ranking",),
            contexts=(),
            lexical_terms=(),
            start_line=1,
            end_line=2,
        )
        old = MemoryChunk(
            chunk_id="old",
            source_path=".AGENTS/sessions/2025-01-01.md",
            source_file="2025-01-01.md",
            session_date=date(2025, 1, 1),
            entry_datetime=None,
            heading_path=("Topic",),
            heading_level=2,
            title="Topic",
            text="ranking note",
            tags=("ranking",),
            contexts=(),
            lexical_terms=(),
            start_line=1,
            end_line=2,
        )

        ranked = rank_memory_chunks(
            "#ranking",
            [old, fresh],
            today=today,
            lambda_days=1.0,
            recency_floor=0.15,
        )

        self.assertEqual(ranked[0].chunk.chunk_id, "fresh")
        old_result = next(result for result in ranked if result.chunk.chunk_id == "old")
        self.assertEqual(old_result.recency_multiplier, 0.15)
        self.assertGreater(old_result.final_score, 0)

    def test_structural_queries_reduce_recency_decay(self):
        today = date(2026, 5, 19)
        chunk = MemoryChunk(
            chunk_id="baseline",
            source_path=".AGENTS/sessions/2026-02-18.md",
            source_file="2026-02-18.md",
            session_date=date(2026, 2, 18),
            entry_datetime=None,
            heading_path=("Architecture Baseline",),
            heading_level=2,
            title="Architecture Baseline",
            text="control plane architecture",
            tags=(),
            contexts=(),
            lexical_terms=("control-plane",),
            start_line=1,
            end_line=2,
        )

        structural = rank_memory_chunks("architecture baseline", [chunk], today=today, lambda_days=0.02)
        normal = rank_memory_chunks("recent note", [chunk], today=today, lambda_days=0.02)

        self.assertGreater(structural[0].recency_multiplier, normal[0].recency_multiplier)

    def test_rank_session_memory_extracts_and_ranks_project_sessions(self):
        cwd = self.make_project()
        self.write_session(cwd, "2026-05-19.md", "## Context: CLI\n\nAdded #compact support.\n")

        ranked = rank_session_memory("#compact", cwd, today=date(2026, 5, 19))

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0].chunk.contexts, ("CLI",))
        self.assertEqual(ranked[0].chunk.granularity, "entry")

    def test_extract_memory_chunks_uses_nearest_memory_seed_runtime(self):
        cwd = self.make_project()
        root_sessions = cwd / ".memory-seed" / "sessions"
        root_sessions.mkdir(parents=True, exist_ok=True)
        (root_sessions / "2026-05-19.md").write_text(
            "## Root entry\n\nRoot policy work.\n",
            encoding="utf-8",
        )
        subproject = cwd / "packages" / "core"
        sub_sessions = subproject / ".memory-seed" / "sessions"
        sub_sessions.mkdir(parents=True, exist_ok=True)
        (sub_sessions / "2026-05-20.md").write_text(
            "## Subproject entry\n\nLocal compilation runbook.\n",
            encoding="utf-8",
        )

        chunks = extract_memory_chunks(subproject / "src")

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].source_path, ".memory-seed/sessions/2026-05-20.md")
        self.assertEqual(chunks[0].title, "Subproject entry")

    def test_extract_memory_chunks_falls_back_to_legacy_agents_sessions(self):
        cwd = self.make_project()
        sessions = cwd / ".AGENTS" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-05-19.md").write_text(
            "## Legacy entry\n\nOld memory system.\n",
            encoding="utf-8",
        )

        chunks = extract_memory_chunks(cwd / "src")

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].source_path, ".AGENTS/sessions/2026-05-19.md")


def _entry(title, entry_id, body, related=None, supersedes=None):
    lines = [
        f"## {title}",
        "",
        "```yaml",
        f"entry_id: {entry_id}",
        "user_initials: JN",
        "agent_type: codex",
        "project_path: .",
        "subproject_path: null",
    ]
    if related:
        lines.append("related_entries:")
        lines.extend(f"  - {ref}" for ref in related)
    if supersedes:
        lines.append("supersedes:")
        lines.extend(f"  - {ref}" for ref in supersedes)
    lines += ["```", "", body, ""]
    return "\n".join(lines)


class RelatedEntryGraphTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-link-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def write_day(self, cwd, *entries):
        sessions = cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        # One day file, entries in append (chronological) order: oldest first.
        (sessions / "2026-05-10.md").write_text(
            "# Session Log\n\n" + "\n".join(entries),
            encoding="utf-8",
        )

    def seed_three(self, cwd):
        # C (09:00) oldest, B (10:00), A (11:00) newest; A links back to B.
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - Oldest C", "ms-c0000000", "caching and ranking notes."),
            _entry("2026-05-10 10:00 - Middle B", "ms-b0000000", "migration command work."),
            _entry(
                "2026-05-10 11:00 - Newest A",
                "ms-a0000000",
                "caching and ranking follow-up.",
                related=["ms-b0000000"],
            ),
        )

    def test_graph_computes_inbound_backlinks_from_forward_edges(self):
        cwd = self.make_project()
        self.seed_three(cwd)

        graph = build_related_entry_graph(cwd)

        self.assertEqual(graph["ms-a0000000"].outbound, ("ms-b0000000",))
        self.assertEqual(graph["ms-a0000000"].inbound, ())
        # B's backlink is computed at read time without B's file being edited.
        self.assertEqual(graph["ms-b0000000"].inbound, ("ms-a0000000",))
        self.assertEqual(graph["ms-b0000000"].outbound, ())
        self.assertEqual(graph["ms-c0000000"].inbound, ())

    def test_graph_ignores_dangling_outbound_for_inbound(self):
        cwd = self.make_project()
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - Only", "ms-only0000", "text.", related=["ms-missing0"]),
        )

        graph = build_related_entry_graph(cwd)

        # Outbound is reported as stored (links check flags the dangling ref)...
        self.assertEqual(graph["ms-only0000"].outbound, ("ms-missing0",))
        # ...but the unresolved target never becomes a node or an inbound edge.
        self.assertNotIn("ms-missing0", graph)

    def test_suggest_excludes_self_linked_and_newer_entries(self):
        cwd = self.make_project()
        self.seed_three(cwd)

        target, ranked = suggest_related_entries(cwd, entry_id="ms-b0000000")

        # Target B: only C is eligible (A is newer -> excluded; B is self).
        self.assertEqual(target.entry_id, "ms-b0000000")
        self.assertEqual([item.chunk.entry_id for item in ranked], ["ms-c0000000"])

    def test_suggest_defaults_to_newest_entry_and_drops_already_linked(self):
        cwd = self.make_project()
        self.seed_three(cwd)

        target, ranked = suggest_related_entries(cwd)

        # Default target is the newest entry A; B is already linked, leaving C.
        self.assertEqual(target.entry_id, "ms-a0000000")
        candidate_ids = [item.chunk.entry_id for item in ranked]
        self.assertEqual(candidate_ids, ["ms-c0000000"])
        self.assertNotIn("ms-b0000000", candidate_ids)

    def test_suggest_unknown_entry_raises(self):
        cwd = self.make_project()
        self.seed_three(cwd)

        with self.assertRaises(LookupError):
            suggest_related_entries(cwd, entry_id="ms-99999999")

    def test_graph_accepts_preextracted_chunks(self):
        cwd = self.make_project()
        self.seed_three(cwd)
        chunks = extract_memory_chunks(cwd, granularity="entry")

        # Passing an already-extracted corpus must yield an identical graph
        # without re-parsing the session files.
        self.assertEqual(
            build_related_entry_graph(cwd, chunks=chunks),
            build_related_entry_graph(cwd),
        )

    def test_graph_computes_superseded_by_inverse_separately_from_inbound(self):
        cwd = self.make_project()
        # A (11:00) supersedes C (09:00) and separately relates to B (10:00).
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - Oldest C", "ms-c0000000", "original decision."),
            _entry("2026-05-10 10:00 - Middle B", "ms-b0000000", "adjacent work."),
            _entry(
                "2026-05-10 11:00 - Newest A",
                "ms-a0000000",
                "replacement decision.",
                related=["ms-b0000000"],
                supersedes=["ms-c0000000"],
            ),
        )

        graph = build_related_entry_graph(cwd)

        self.assertEqual(graph["ms-a0000000"].supersedes, ("ms-c0000000",))
        self.assertEqual(graph["ms-c0000000"].superseded_by, ("ms-a0000000",))
        # The two edge kinds never bleed into each other: superseding C adds
        # nothing to C's relatedness backlinks, and relating to B adds nothing
        # to B's supersession status.
        self.assertEqual(graph["ms-c0000000"].inbound, ())
        self.assertEqual(graph["ms-b0000000"].superseded_by, ())
        self.assertEqual(graph["ms-b0000000"].inbound, ("ms-a0000000",))

    def test_importance_score_is_inbound_count_undampened_when_not_superseded(self):
        cwd = self.make_project()
        # B and C both cite A; A is never superseded.
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - Cited A", "ms-a0000000", "the decision."),
            _entry("2026-05-10 10:00 - Citer B", "ms-b0000000", "cites A.", related=["ms-a0000000"]),
            _entry("2026-05-10 11:00 - Citer C", "ms-c0000000", "cites A too.", related=["ms-a0000000"]),
        )

        graph = build_related_entry_graph(cwd)

        self.assertEqual(graph["ms-a0000000"].importance_score, 2.0)

    def test_importance_score_dampened_for_superseded_entry_below_live_entry(self):
        # The harmony-contract fixture the DoD requires: a heavily-cited but
        # superseded entry must score below a live, moderately-cited one.
        # OLD (ms-aaaa0000): cited by 4, superseded. LIVE (ms-bbbb0000): cited by 2.
        cwd = self.make_project()
        self.write_day(
            cwd,
            _entry("2026-05-10 08:00 - Old heavily-cited", "ms-aaaa0000", "retired but popular."),
            _entry("2026-05-10 09:00 - Live moderately-cited", "ms-bbbb0000", "current decision."),
            _entry("2026-05-10 10:00 - c1", "ms-cccc0001", "x", related=["ms-aaaa0000"]),
            _entry("2026-05-10 10:01 - c2", "ms-cccc0002", "x", related=["ms-aaaa0000"]),
            _entry("2026-05-10 10:02 - c3", "ms-cccc0003", "x", related=["ms-aaaa0000"]),
            _entry("2026-05-10 10:03 - c4", "ms-cccc0004", "x", related=["ms-aaaa0000"]),
            _entry("2026-05-10 10:04 - c5", "ms-cccc0005", "x", related=["ms-bbbb0000"]),
            _entry("2026-05-10 10:05 - c6", "ms-cccc0006", "x", related=["ms-bbbb0000"]),
            _entry("2026-05-10 11:00 - Replacement", "ms-dddd0000", "replaces old.", supersedes=["ms-aaaa0000"]),
        )

        graph = build_related_entry_graph(cwd)

        old_score = graph["ms-aaaa0000"].importance_score
        live_score = graph["ms-bbbb0000"].importance_score
        # Raw: old=4 (dampened to 4*0.25=1.0), live=2 (undampened=2.0).
        self.assertEqual(old_score, 4 * SUPERSEDED_IMPORTANCE_DAMPING)
        self.assertEqual(live_score, 2.0)
        self.assertLess(old_score, live_score)
        # Supersession never inflated the count itself - it's a post-hoc dampener.
        self.assertEqual(len(graph["ms-aaaa0000"].inbound), 4)

    def test_entry_chunks_parse_commits_field(self):
        cwd = self.make_project()
        sessions = cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-05-10.md").write_text(
            "## 2026-05-10 09:00 - Implemented\n\n"
            "```yaml\n"
            "entry_id: ms-implemented\n"
            "commits:\n"
            "  - " + "a" * 40 + "\n"
            "```\n\n"
            "text.\n",
            encoding="utf-8",
        )

        chunks = extract_memory_chunks(cwd, granularity="entry")

        self.assertEqual(chunks[0].commits, ("a" * 40,))

    def test_graph_ignores_dangling_supersedes_for_inverse(self):
        cwd = self.make_project()
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - Only", "ms-only0000", "text.", supersedes=["ms-missing0"]),
        )

        graph = build_related_entry_graph(cwd)

        self.assertEqual(graph["ms-only0000"].supersedes, ("ms-missing0",))
        self.assertNotIn("ms-missing0", graph)


if __name__ == "__main__":
    unittest.main()
