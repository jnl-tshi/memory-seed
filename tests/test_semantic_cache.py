import math
import shutil
import tempfile
import unittest
from datetime import date
from datetime import datetime
from pathlib import Path

from memory_seed.semantic_cache import (
    MemoryChunk,
    extract_memory_chunks,
    rank_memory_chunks,
    rank_session_memory,
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
        sessions = cwd / ".AGENTS" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / filename).write_text(content, encoding="utf-8")

    def test_extracts_heading_bounded_chunks_with_temporal_metadata(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-18.md",
            "# Session Log - 2026-05-18\n\n"
            "Top note #root-tag\n\n"
            "## Context: Ranking Engine\n\n"
            "Build token_harvester around `.AGENTS/context.md` and memory-seed.\n\n"
            "### Target Discovery\n\n"
            "Use #target-discovery for exact matching.\n",
        )

        chunks = extract_memory_chunks(cwd)

        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0].source_file, "2026-05-18.md")
        self.assertEqual(chunks[0].session_date, date(2026, 5, 18))
        self.assertIsNone(chunks[0].entry_datetime)
        self.assertEqual(chunks[0].heading_path, ("Session Log - 2026-05-18",))
        self.assertEqual(chunks[1].heading_path, ("Session Log - 2026-05-18", "Context: Ranking Engine"))
        self.assertEqual(chunks[2].heading_path, ("Session Log - 2026-05-18", "Context: Ranking Engine", "Target Discovery"))
        self.assertEqual(chunks[1].contexts, ("Ranking Engine",))
        self.assertIn("target-discovery", chunks[2].tags)
        self.assertIn("token_harvester", chunks[1].lexical_terms)
        self.assertIn("memory-seed", chunks[1].lexical_terms)
        self.assertIn(".AGENTS/context.md", chunks[1].lexical_terms)
        self.assertGreaterEqual(chunks[2].start_line, chunks[1].end_line)

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

    def test_ignores_non_date_session_files(self):
        cwd = self.make_project()
        self.write_session(cwd, "notes.md", "## Should not index\n\n#tag\n")
        self.write_session(cwd, "2026-05-18.md", "## Valid\n\nUseful content.\n")

        chunks = extract_memory_chunks(cwd)

        self.assertEqual([chunk.source_file for chunk in chunks], ["2026-05-18.md"])

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


if __name__ == "__main__":
    unittest.main()
