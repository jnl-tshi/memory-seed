import math
import shutil
import tempfile
import unittest
from datetime import date
from datetime import datetime
from pathlib import Path

from memory_seed.semantic_cache import (
    REPLACED_IMPORTANCE_DAMPING,
    REPLACED_RANK_DAMPING,
    MemoryChunk,
    add_related_entry,
    build_related_entry_graph,
    evolves_lineage_heads,
    extract_memory_chunks,
    rank_memory_chunks,
    rank_session_memory,
    suggest_related_entries,
    replacing_lineage_heads,
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


def _entry(title, entry_id, body, related=None, replaces=None, evolves=None, continuity=None, files=None):
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
    if replaces:
        lines.append("replaces:")
        lines.extend(f"  - {ref}" for ref in replaces)
    if evolves:
        lines.append("evolves:")
        lines.extend(f"  - {ref}" for ref in evolves)
    if continuity:
        lines.append("continuity:")
        for kind, from_ref, to_ref in continuity:
            lines.append(f"  - kind: {kind}")
            lines.append(f"    from: {from_ref}")
            if to_ref is not None:
                lines.append(f"    to: {to_ref}")
    lines += ["```", "", body, ""]
    if files:
        quoted = ", ".join(f"`{ref}`" for ref in files)
        lines += [f"- F: {quoted}.", ""]
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

    def read_day(self, cwd):
        return (cwd / ".memory-seed" / "sessions" / "2026-05-10.md").read_text(encoding="utf-8")

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

    def test_add_appends_edge_to_newest_entry_and_leaves_prose_intact(self):
        cwd = self.make_project()
        self.seed_three(cwd)
        before = self.read_day(cwd)

        result = add_related_entry(cwd, target_entry_id="ms-c0000000")

        self.assertTrue(result.added)
        self.assertEqual(result.source.entry_id, "ms-a0000000")  # newest by default
        graph = build_related_entry_graph(cwd)
        # The new edge joins the existing one; order is preserved, not replaced.
        self.assertEqual(graph["ms-a0000000"].outbound, ("ms-b0000000", "ms-c0000000"))
        # Only YAML metadata changed: every prose line survives byte-for-byte.
        after = self.read_day(cwd)
        self.assertEqual(
            [line for line in before.splitlines() if not line.startswith("  - ms-")],
            [line for line in after.splitlines() if not line.startswith("  - ms-")],
        )

    def test_add_creates_related_entries_key_when_absent(self):
        cwd = self.make_project()
        # Newest entry carries no related_entries: key at all, so the writer
        # has to create it rather than extend an existing list.
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - Oldest C", "ms-c0000000", "caching notes."),
            _entry("2026-05-10 11:00 - Newest A", "ms-a0000000", "caching follow-up."),
        )

        result = add_related_entry(cwd, target_entry_id="ms-c0000000")

        self.assertTrue(result.added)
        self.assertEqual(build_related_entry_graph(cwd)["ms-a0000000"].outbound, ("ms-c0000000",))

    def test_add_is_idempotent(self):
        cwd = self.make_project()
        self.seed_three(cwd)

        first = add_related_entry(cwd, target_entry_id="ms-c0000000")
        text_after_first = self.read_day(cwd)
        second = add_related_entry(cwd, target_entry_id="ms-c0000000")

        self.assertTrue(first.added)
        self.assertFalse(second.added)  # reported as a no-op...
        self.assertEqual(text_after_first, self.read_day(cwd))  # ...and wrote nothing

    def test_add_refuses_to_edit_an_older_entry(self):
        cwd = self.make_project()
        self.seed_three(cwd)

        # B is real but not the newest, so editing it is historical curation,
        # which Invariant #2 (append-only) forbids. This is the guard that keeps
        # `link add` from quietly becoming the unratified `link backfill`.
        with self.assertRaises(ValueError) as ctx:
            add_related_entry(cwd, target_entry_id="ms-c0000000", from_entry_id="ms-b0000000")
        self.assertIn("not the newest entry", str(ctx.exception))

    def test_add_refuses_self_link_and_forward_edge(self):
        cwd = self.make_project()
        self.seed_three(cwd)
        before = self.read_day(cwd)

        with self.assertRaises(ValueError):
            add_related_entry(cwd, target_entry_id="ms-a0000000")  # self
        with self.assertRaises(ValueError):
            # C is older than A, so C -> A would point forward in time.
            add_related_entry(cwd, target_entry_id="ms-a0000000", from_entry_id="ms-c0000000")
        self.assertEqual(before, self.read_day(cwd))

    def test_add_preserves_file_ending_and_adds_exactly_one_line(self):
        cwd = self.make_project()
        self.seed_three(cwd)
        before = self.read_day(cwd)

        add_related_entry(cwd, target_entry_id="ms-c0000000")

        after = self.read_day(cwd)
        # Exactly one line added, and the file's ending is unchanged (no
        # doubled or stripped trailing newline).
        self.assertEqual(len(after.split("\n")), len(before.split("\n")) + 1)
        self.assertEqual(before.endswith("\n"), after.endswith("\n"))

    def test_add_refuses_unterminated_yaml_block_without_crashing(self):
        cwd = self.make_project()
        sessions = cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        # Newest entry's yaml fence is never closed and runs to EOF. Scanning
        # for the close beyond the entry would walk off the end of the file.
        (sessions / "2026-05-10.md").write_text(
            "# Session Log\n\n"
            + _entry("2026-05-10 09:00 - Oldest C", "ms-c0000000", "caching notes.")
            + "\n## 2026-05-10 11:00 - Newest A\n\n```yaml\nentry_id: ms-a0000000\n",
            encoding="utf-8",
        )
        before = self.read_day(cwd)

        with self.assertRaises(ValueError) as ctx:
            add_related_entry(cwd, target_entry_id="ms-c0000000")

        self.assertIn("unterminated", str(ctx.exception))
        self.assertEqual(before, self.read_day(cwd))

    def test_add_unknown_ids_raise_and_write_nothing(self):
        cwd = self.make_project()
        self.seed_three(cwd)
        before = self.read_day(cwd)

        with self.assertRaises(LookupError):
            add_related_entry(cwd, target_entry_id="ms-99999999")
        with self.assertRaises(LookupError):
            add_related_entry(cwd, target_entry_id="ms-c0000000", from_entry_id="ms-99999999")
        self.assertEqual(before, self.read_day(cwd))

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

    def test_graph_computes_replaced_by_inverse_separately_from_inbound(self):
        cwd = self.make_project()
        # A (11:00) replaces C (09:00) and separately relates to B (10:00).
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - Oldest C", "ms-c0000000", "original decision."),
            _entry("2026-05-10 10:00 - Middle B", "ms-b0000000", "adjacent work."),
            _entry(
                "2026-05-10 11:00 - Newest A",
                "ms-a0000000",
                "replacement decision.",
                related=["ms-b0000000"],
                replaces=["ms-c0000000"],
            ),
        )

        graph = build_related_entry_graph(cwd)

        self.assertEqual(graph["ms-a0000000"].replaces, ("ms-c0000000",))
        self.assertEqual(graph["ms-c0000000"].replaced_by, ("ms-a0000000",))
        # The two edge kinds never bleed into each other: replacing C adds
        # nothing to C's relatedness backlinks, and relating to B adds nothing
        # to B's supersession status.
        self.assertEqual(graph["ms-c0000000"].inbound, ())
        self.assertEqual(graph["ms-b0000000"].replaced_by, ())
        self.assertEqual(graph["ms-b0000000"].inbound, ("ms-a0000000",))

    def test_importance_score_is_inbound_count_undampened_when_not_replaced(self):
        cwd = self.make_project()
        # B and C both cite A; A is never replaced.
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - Cited A", "ms-a0000000", "the decision."),
            _entry("2026-05-10 10:00 - Citer B", "ms-b0000000", "cites A.", related=["ms-a0000000"]),
            _entry("2026-05-10 11:00 - Citer C", "ms-c0000000", "cites A too.", related=["ms-a0000000"]),
        )

        graph = build_related_entry_graph(cwd)

        self.assertEqual(graph["ms-a0000000"].importance_score, 2.0)

    def test_importance_score_dampened_for_replaced_entry_below_live_entry(self):
        # The harmony-contract fixture the DoD requires: a heavily-cited but
        # replaced entry must score below a live, moderately-cited one.
        # OLD (ms-aaaa0000): cited by 4, replaced. LIVE (ms-bbbb0000): cited by 2.
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
            _entry("2026-05-10 11:00 - Replacement", "ms-dddd0000", "replaces old.", replaces=["ms-aaaa0000"]),
        )

        graph = build_related_entry_graph(cwd)

        old_score = graph["ms-aaaa0000"].importance_score
        live_score = graph["ms-bbbb0000"].importance_score
        # Raw: old=4 (dampened to 4*0.25=1.0), live=2 (undampened=2.0).
        self.assertEqual(old_score, 4 * REPLACED_IMPORTANCE_DAMPING)
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

    def test_graph_ignores_dangling_replaces_for_inverse(self):
        cwd = self.make_project()
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - Only", "ms-only0000", "text.", replaces=["ms-missing0"]),
        )

        graph = build_related_entry_graph(cwd)

        self.assertEqual(graph["ms-only0000"].replaces, ("ms-missing0",))
        self.assertNotIn("ms-missing0", graph)


class EvolutionEdgeTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-evolves-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def write_file(self, cwd, filename, *entries):
        sessions = cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        path = sessions / filename
        path.write_text("# Session Log\n\n" + "\n".join(entries), encoding="utf-8")
        return path

    def test_graph_computes_evolved_by_inverse_without_dampening(self):
        cwd = self.make_project()
        # OLD is cited by two entries and evolved by NEW: the inverse must be
        # computed, and importance must stay the full undampened inbound count
        # - evolution is freshness, not retirement.
        self.write_file(
            cwd,
            "2026-05-10.md",
            _entry("2026-05-10 09:00 - Old decision", "ms-old00000", "the base decision."),
            _entry("2026-05-10 10:00 - Citer 1", "ms-cite0001", "x", related=["ms-old00000"]),
            _entry("2026-05-10 10:01 - Citer 2", "ms-cite0002", "x", related=["ms-old00000"]),
            _entry("2026-05-10 11:00 - Refinement", "ms-new00000", "extends the base.", evolves=["ms-old00000"]),
        )

        graph = build_related_entry_graph(cwd)

        self.assertEqual(graph["ms-new00000"].evolves, ("ms-old00000",))
        self.assertEqual(graph["ms-old00000"].evolved_by, ("ms-new00000",))
        # No status bleed: evolution is not supersession and not relatedness.
        self.assertEqual(graph["ms-old00000"].replaced_by, ())
        self.assertEqual(graph["ms-old00000"].inbound, ("ms-cite0001", "ms-cite0002"))
        self.assertEqual(graph["ms-old00000"].importance_score, 2.0)

    def test_declaring_evolves_changes_zero_bytes_of_target_file(self):
        cwd = self.make_project()
        target_path = self.write_file(
            cwd,
            "2026-05-09.md",
            _entry("2026-05-09 09:00 - Old decision", "ms-old00000", "the base decision."),
        )
        before = target_path.read_bytes()
        self.write_file(
            cwd,
            "2026-05-10.md",
            _entry("2026-05-10 09:00 - Refinement", "ms-new00000", "extends it.", evolves=["ms-old00000"]),
        )

        graph = build_related_entry_graph(cwd)

        self.assertEqual(graph["ms-old00000"].evolved_by, ("ms-new00000",))
        # Append-only: the inverse exists only in the derived read layer.
        self.assertEqual(target_path.read_bytes(), before)

    def test_continuity_blocks_parse_from_entry_yaml(self):
        cwd = self.make_project()
        self.write_file(
            cwd,
            "2026-05-10.md",
            _entry(
                "2026-05-10 09:00 - Lineage",
                "ms-lineage00",
                "renamed and removed things.",
                continuity=[
                    ("rename", "old/path.py", "new/path.py"),
                    ("removal", "old-command", None),
                ],
            ),
        )

        chunks = extract_memory_chunks(cwd, granularity="entry")

        blocks = chunks[0].continuity
        self.assertEqual(len(blocks), 2)
        self.assertEqual((blocks[0].kind, blocks[0].from_ref, blocks[0].to_ref), ("rename", "old/path.py", "new/path.py"))
        self.assertEqual((blocks[1].kind, blocks[1].from_ref, blocks[1].to_ref), ("removal", "old-command", None))


class SupersessionRankDampingTests(unittest.TestCase):
    """Primitive-level guardrails for the default-off supersession rank-dampener
    (freshness-aware-memory-ranking-proposal.md item 1) and the evolves
    successor-surfacing helper (item 2)."""

    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-damp-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def write_day(self, cwd, *entries):
        sessions = cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-05-10.md").write_text(
            "# Session Log\n\n" + "\n".join(entries), encoding="utf-8"
        )

    def test_rank_memory_chunks_damps_only_replaced_ids(self):
        cwd = self.make_project()
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - Retired", "ms-old00000", "shared ranking topic."),
            _entry("2026-05-10 10:00 - Live", "ms-new00000", "shared ranking topic."),
        )
        chunks = extract_memory_chunks(cwd, granularity="entry")
        today = date(2026, 5, 10)  # both age 0 -> recency identical, isolates the damper

        baseline = {r.chunk.entry_id: r.final_score for r in rank_memory_chunks("ranking", chunks, today=today)}
        damped = {
            r.chunk.entry_id: r.final_score
            for r in rank_memory_chunks("ranking", chunks, today=today, replaced_ids={"ms-old00000"})
        }
        # The live entry is untouched; the replaced one is scaled by the damper.
        self.assertEqual(damped["ms-new00000"], baseline["ms-new00000"])
        self.assertAlmostEqual(damped["ms-old00000"], baseline["ms-old00000"] * REPLACED_RANK_DAMPING)
        # Default (no replaced_ids) leaves every score byte-for-byte identical.
        default = {r.chunk.entry_id: r.final_score for r in rank_memory_chunks("ranking", chunks, today=today)}
        self.assertEqual(default, baseline)

    def test_rank_session_memory_supersession_damping_flag(self):
        cwd = self.make_project()
        # Newer entry replaces the older one; both match the query.
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - Retired decision", "ms-old00000", "cache eviction ranking."),
            _entry(
                "2026-05-10 10:00 - Live decision",
                "ms-new00000",
                "cache eviction ranking.",
                replaces=["ms-old00000"],
            ),
        )
        today = date(2026, 5, 10)
        off = {r.chunk.entry_id: r.final_score for r in rank_session_memory("ranking", cwd, today=today)}
        on = {
            r.chunk.entry_id: r.final_score
            for r in rank_session_memory("ranking", cwd, today=today, supersession_damping=True)
        }
        # Default off is unchanged; opting in damps only the replaced entry.
        self.assertEqual(on["ms-new00000"], off["ms-new00000"])
        self.assertAlmostEqual(on["ms-old00000"], off["ms-old00000"] * REPLACED_RANK_DAMPING)
        # Down-rank only: the replaced entry is still returned, never dropped
        # (that stays exclude_replaced).
        self.assertIn("ms-old00000", on)

    def test_rank_memory_chunks_boosts_only_matching_terminal_replacement(self):
        today = date(2026, 5, 10)
        old = MemoryChunk(
            chunk_id="ms-old00000",
            source_path=".memory-seed/sessions/2026-05/2026-05-10.md",
            source_file="2026-05-10.md",
            session_date=today,
            entry_datetime=None,
            heading_path=("Retired",),
            heading_level=2,
            title="Retired",
            text="cache ttl invalidation strategy",
            tags=(),
            contexts=(),
            lexical_terms=(),
            start_line=1,
            end_line=2,
            entry_id="ms-old00000",
        )
        new = MemoryChunk(
            chunk_id="ms-new00000",
            source_path=".memory-seed/sessions/2026-05/2026-05-10.md",
            source_file="2026-05-10.md",
            session_date=today,
            entry_datetime=None,
            heading_path=("Live",),
            heading_level=2,
            title="Live",
            text="cache ttl plan",
            tags=(),
            contexts=(),
            lexical_terms=(),
            start_line=3,
            end_line=4,
            entry_id="ms-new00000",
        )
        baseline = {
            r.chunk.entry_id: r.final_score
            for r in rank_memory_chunks(
                "cache ttl invalidation strategy",
                [old, new],
                today=today,
                replaced_ids={"ms-old00000"},
            )
        }
        boosted = {
            r.chunk.entry_id: r.final_score
            for r in rank_memory_chunks(
                "cache ttl invalidation strategy",
                [old, new],
                today=today,
                replaced_ids={"ms-old00000"},
                replacing_heads_by_id={"ms-old00000": ("ms-new00000",)},
            )
        }

        self.assertEqual(boosted["ms-old00000"], baseline["ms-old00000"])
        self.assertGreater(boosted["ms-new00000"], baseline["ms-new00000"])

    def test_rank_memory_chunks_never_boosts_zero_match_successor(self):
        today = date(2026, 5, 10)
        old = MemoryChunk(
            chunk_id="ms-old00000",
            source_path=".memory-seed/sessions/2026-05/2026-05-10.md",
            source_file="2026-05-10.md",
            session_date=today,
            entry_datetime=None,
            heading_path=("Retired",),
            heading_level=2,
            title="Retired",
            text="cache ttl invalidation strategy",
            tags=(),
            contexts=(),
            lexical_terms=(),
            start_line=1,
            end_line=2,
            entry_id="ms-old00000",
        )
        new = MemoryChunk(
            chunk_id="ms-new00000",
            source_path=".memory-seed/sessions/2026-05/2026-05-10.md",
            source_file="2026-05-10.md",
            session_date=today,
            entry_datetime=None,
            heading_path=("Live",),
            heading_level=2,
            title="Live",
            text="unrelated future work",
            tags=(),
            contexts=(),
            lexical_terms=(),
            start_line=3,
            end_line=4,
            entry_id="ms-new00000",
        )
        baseline = {
            r.chunk.entry_id: r.final_score
            for r in rank_memory_chunks(
                "cache ttl invalidation strategy",
                [old, new],
                today=today,
                replaced_ids={"ms-old00000"},
            )
        }
        boosted = {
            r.chunk.entry_id: r.final_score
            for r in rank_memory_chunks(
                "cache ttl invalidation strategy",
                [old, new],
                today=today,
                replaced_ids={"ms-old00000"},
                replacing_heads_by_id={"ms-old00000": ("ms-new00000",)},
            )
        }

        self.assertEqual(boosted, baseline)

    def test_evolves_lineage_heads_follows_chain_to_head(self):
        cwd = self.make_project()
        # C evolves B, B evolves A. A/B are valid; C is the head of the lineage.
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - Base A", "ms-a0000000", "base decision."),
            _entry("2026-05-10 10:00 - Refined B", "ms-b0000000", "refined.", evolves=["ms-a0000000"]),
            _entry("2026-05-10 11:00 - Final C", "ms-c0000000", "final.", evolves=["ms-b0000000"]),
        )
        graph = build_related_entry_graph(cwd)
        # Base and middle resolve transitively to the head; the head resolves to
        # nothing further; an unknown id is empty.
        self.assertEqual(evolves_lineage_heads(graph, "ms-a0000000"), ("ms-c0000000",))
        self.assertEqual(evolves_lineage_heads(graph, "ms-b0000000"), ("ms-c0000000",))
        self.assertEqual(evolves_lineage_heads(graph, "ms-c0000000"), ())
        self.assertEqual(evolves_lineage_heads(graph, "ms-missing0"), ())

    def test_replacing_lineage_heads_follows_chain_to_terminal_live_replacement(self):
        cwd = self.make_project()
        # C replaces B, B replaces A. A and B should both resolve to the
        # terminal live replacement C, while C resolves to nothing further.
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - Base A", "ms-a0000000", "base decision."),
            _entry(
                "2026-05-10 10:00 - Replacement B",
                "ms-b0000000",
                "replacement.",
                replaces=["ms-a0000000"],
            ),
            _entry(
                "2026-05-10 11:00 - Final C",
                "ms-c0000000",
                "final replacement.",
                replaces=["ms-b0000000"],
            ),
        )
        graph = build_related_entry_graph(cwd)

        self.assertEqual(replacing_lineage_heads(graph, "ms-a0000000"), ("ms-c0000000",))
        self.assertEqual(replacing_lineage_heads(graph, "ms-b0000000"), ("ms-c0000000",))
        self.assertEqual(replacing_lineage_heads(graph, "ms-c0000000"), ())
        self.assertEqual(replacing_lineage_heads(graph, "ms-missing0"), ())


class FileOverlapSuggestTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-overlap-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def write_day(self, cwd, *entries):
        sessions = cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-05-10.md").write_text(
            "# Session Log\n\n" + "\n".join(entries),
            encoding="utf-8",
        )

    def test_rare_file_overlap_outranks_identical_candidate(self):
        cwd = self.make_project()
        # X and Y have identical bodies (identical base similarity); X shares
        # the rare file with the target. Without the boost, the tiebreak
        # (higher start_line first) would put Y ahead; the boost must flip it.
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - X", "ms-x0000000", "ranking work.", files=["src/rare_module.py"]),
            _entry("2026-05-10 09:30 - Y", "ms-y0000000", "ranking work.", files=["src/other_module.py"]),
            _entry("2026-05-10 11:00 - Target", "ms-t0000000", "ranking work.", files=["src/rare_module.py"]),
        )

        target, suggestions = suggest_related_entries(cwd, entry_id="ms-t0000000")

        self.assertEqual([s.chunk.entry_id for s in suggestions], ["ms-x0000000", "ms-y0000000"])
        self.assertEqual(suggestions[0].shared_files, ("src/rare_module.py",))
        self.assertGreater(suggestions[0].file_overlap_bonus, 0.0)
        self.assertEqual(suggestions[1].shared_files, ())
        self.assertEqual(suggestions[1].file_overlap_bonus, 0.0)

    def test_hub_file_overlap_contributes_no_boost(self):
        cwd = self.make_project()
        # CHANGELOG.md appears in every entry's F: its idf is log(N/N) = 0, so
        # sharing it is evidence-listed but score-neutral.
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - X", "ms-x0000000", "audit work.", files=["CHANGELOG.md"]),
            _entry("2026-05-10 10:00 - Y", "ms-y0000000", "audit work.", files=["CHANGELOG.md"]),
            _entry("2026-05-10 11:00 - Target", "ms-t0000000", "audit work.", files=["CHANGELOG.md"]),
        )

        target, suggestions = suggest_related_entries(cwd, entry_id="ms-t0000000")

        for suggestion in suggestions:
            self.assertEqual(suggestion.shared_files, ("CHANGELOG.md",))
            self.assertEqual(suggestion.file_overlap_bonus, 0.0)
            self.assertEqual(suggestion.adjusted_score, suggestion.result.final_score)

    def test_entry_without_f_lines_suffers_no_penalty(self):
        cwd = self.make_project()
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - NoF", "ms-nof00000", "encoding work."),
            _entry("2026-05-10 11:00 - Target", "ms-t0000000", "encoding work.", files=["src/rare_module.py"]),
        )

        target, suggestions = suggest_related_entries(cwd, entry_id="ms-t0000000")

        self.assertEqual([s.chunk.entry_id for s in suggestions], ["ms-nof00000"])
        self.assertEqual(suggestions[0].file_overlap_bonus, 0.0)
        self.assertEqual(suggestions[0].adjusted_score, suggestions[0].result.final_score)

    def test_alias_table_bridges_recorded_renames_transitively(self):
        cwd = self.make_project()
        # OLD touched explorer.py; two rename entries chain explorer -> lense
        # -> trace; the target touches trace.py. The alias table must resolve
        # the old path to the terminal name so the pair genuinely overlaps.
        self.write_day(
            cwd,
            _entry("2026-05-10 08:00 - Old work", "ms-old00000", "graph view work.", files=["ui/explorer.py"]),
            _entry(
                "2026-05-10 09:00 - Rename 1",
                "ms-ren00001",
                "explorer becomes lense.",
                continuity=[("rename", "ui/explorer.py", "ui/lense.py")],
            ),
            _entry(
                "2026-05-10 10:00 - Rename 2",
                "ms-ren00002",
                "lense becomes trace.",
                continuity=[("rename", "ui/lense.py", "ui/trace.py")],
            ),
            _entry("2026-05-10 11:00 - Target", "ms-t0000000", "graph view work.", files=["ui/trace.py"]),
        )

        target, suggestions = suggest_related_entries(cwd, entry_id="ms-t0000000", top_k=3)

        old = next(s for s in suggestions if s.chunk.entry_id == "ms-old00000")
        self.assertEqual(old.shared_files, ("ui/trace.py",))
        self.assertGreater(old.file_overlap_bonus, 0.0)

    def test_consulted_axis_surfaces_and_ranks_first_over_file_overlap(self):
        cwd = self.make_project()
        # A shares the target's file and topic (a strong structural candidate);
        # C shares neither - a pure decision-lineage parent that file overlap
        # cannot see. Without `consulted`, A leads and C trails; naming C as
        # consulted must lift it to the front and flag its provenance, while A
        # stays present, unflagged, below it.
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - A", "ms-a0000000", "trail lane rendering.", files=["ui/trail.py"]),
            _entry("2026-05-10 10:00 - C", "ms-c0000000", "database index migration.", files=["db/index.py"]),
            _entry("2026-05-10 11:00 - Target", "ms-t0000000", "trail lane rendering.", files=["ui/trail.py"]),
        )

        _, plain = suggest_related_entries(cwd, entry_id="ms-t0000000")
        self.assertEqual(plain[0].chunk.entry_id, "ms-a0000000")
        self.assertFalse(any(s.consulted for s in plain))

        _, consulted = suggest_related_entries(cwd, entry_id="ms-t0000000", consulted=["ms-c0000000"])
        self.assertEqual(consulted[0].chunk.entry_id, "ms-c0000000")
        self.assertTrue(consulted[0].consulted)
        order = [s.chunk.entry_id for s in consulted]
        self.assertLess(order.index("ms-c0000000"), order.index("ms-a0000000"))
        a = next(s for s in consulted if s.chunk.entry_id == "ms-a0000000")
        self.assertFalse(a.consulted)

    def test_empty_consulted_is_byte_identical_to_file_only(self):
        cwd = self.make_project()
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - A", "ms-a0000000", "trail lane rendering.", files=["ui/trail.py"]),
            _entry("2026-05-10 10:00 - B", "ms-b0000000", "trail lane rendering.", files=["ui/other.py"]),
            _entry("2026-05-10 11:00 - Target", "ms-t0000000", "trail lane rendering.", files=["ui/trail.py"]),
        )
        shape = lambda ss: [(s.chunk.entry_id, s.adjusted_score, s.consulted) for s in ss]
        _, baseline = suggest_related_entries(cwd, entry_id="ms-t0000000")
        _, none_arg = suggest_related_entries(cwd, entry_id="ms-t0000000", consulted=None)
        _, empty_arg = suggest_related_entries(cwd, entry_id="ms-t0000000", consulted=[])
        self.assertEqual(shape(baseline), shape(none_arg))
        self.assertEqual(shape(baseline), shape(empty_arg))
        self.assertTrue(all(not s.consulted for s in baseline))


if __name__ == "__main__":
    unittest.main()
