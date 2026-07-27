"""Topic sidecars reaching the Trace read path (2026-07-27).

A topic sidecar attributes a controlled-vocabulary slug to an entry *after* it
was written, because append-only forbids reopening the entry. Memory Seed has
read them since the family shipped; Memory Trace did not - `service.py` never
called `augment_chunks_with_topic_sidecars`, so 166 attributions landed in the
corpus and changed nothing a user could see.

These tests pin the three things that wiring had to get right:

1. `_topics()` UNIONS the inferred channel with the authored one, so a filter,
   facet, chip and community colour all find a late-attributed entry.
2. The union happens at that one chokepoint. Every consumer reads it, which is
   what stops a legend coloured from one channel and a chip list rendered from
   the other from disagreeing.
3. Topic sidecars are tracked as projection inputs. Without that, editing an
   attribution leaves the no-git mtime scan serving the old topics forever.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from memory_seed.core import resolve_runtime
from memory_seed.semantic_cache import MemoryChunk
from memory_trace.service import _topics, _tracked_document_paths, create_app

ENTRY = "mse_" + "d" * 16
OTHER = "mse_" + "e" * 16


def _entry(dt, entry_id, title, topics=()):
    lines = [
        f"## {dt} - {title}",
        "",
        "```yaml",
        f"entry_id: {entry_id}",
        "user_initials: JN",
        "agent_type: claude",
        "project_path: .",
        "subproject_path: null",
    ]
    if topics:
        lines.append("topics:")
        lines.extend(f"  - {t}" for t in topics)
    lines += ["```", "", "Body text.", ""]
    return "\n".join(lines)


class TopicUnionTests(unittest.TestCase):
    """`_topics()` in isolation - the chokepoint every consumer reads."""

    def _chunk(self, **kwargs):
        from datetime import date, datetime

        base = dict(
            chunk_id="c1",
            granularity="entry",
            entry_id=ENTRY,
            source_path=".memory-seed/sessions/2026-06-01.md",
            source_file="2026-06-01.md",
            session_date=date(2026, 6, 1),
            entry_datetime=datetime(2026, 6, 1, 9, 0),
            heading_path=(),
            heading_level=2,
            title="Coarsely tagged",
            tags=(),
            contexts=(),
            lexical_terms=(),
            start_line=1,
            end_line=10,
            text="body",
        )
        base.update(kwargs)
        return MemoryChunk(**base)

    def test_authored_only_is_unchanged(self):
        chunk = self._chunk(topics=("memory-trace",))
        self.assertEqual(_topics(chunk), ["memory-trace"])

    def test_the_sidecar_wins_over_the_authored_field(self):
        # THE AUTHORITY RULE. This asserted a union until 2026-07-27, when the
        # two-axis campaign gave every entry a complete sidecar reading. A union
        # then re-admits the coarse pre-axis label the sweep exists to supersede.
        chunk = self._chunk(topics=("memory-trace",), inferred_topics=("trail",))
        self.assertEqual(_topics(chunk), ["trail"])

    def test_authored_topics_still_serve_entries_no_sweep_reached(self):
        chunk = self._chunk(topics=("memory-trace",))
        self.assertEqual(_topics(chunk), ["memory-trace"])

    def test_a_sidecar_restating_the_authored_slug_is_stable(self):
        chunk = self._chunk(topics=("trail",), inferred_topics=("trail",))
        self.assertEqual(_topics(chunk), ["trail"])

    def test_inferred_alone_still_wins_over_the_hashtag_fallback(self):
        # An entry with no authored topics but a sidecar attribution speaks the
        # controlled vocabulary - it must NOT fall back to tags/contexts, or the
        # facet would show a hashtag beside real slugs.
        chunk = self._chunk(inferred_topics=("trail",), tags=("#ui",), contexts=("misc",))
        self.assertEqual(_topics(chunk), ["trail"])

    def test_fallback_survives_when_neither_channel_has_slugs(self):
        chunk = self._chunk(tags=("#ui",), contexts=("misc",))
        self.assertEqual(_topics(chunk), ["#ui", "misc"])

    def test_a_sidecar_narrows_without_the_parent_leaking_back(self):
        # The case the authority rule exists for: the sweep says `trail`, the
        # author said `memory-trace`. Both true, but only one is the corpus's
        # current reading, and `memory-trace` is still reachable by derivation.
        chunk = self._chunk(topics=("memory-trace", "ui-design"), inferred_topics=("trail", "graph"))
        self.assertEqual(_topics(chunk), ["graph", "trail"])


class TopicSidecarReadPathTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-topicsidecar-"))
        self.cache_root = Path(tempfile.mkdtemp(prefix="mseed-topicsidecar-cache-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(self.cache_root, ignore_errors=True))
        self.sessions = self.cwd / ".memory-seed" / "sessions"
        self.sessions.mkdir(parents=True, exist_ok=True)
        (self.sessions / "2026-06-01.md").write_text(
            "---\ntags:\n  - session-log\n---\n\n"
            + _entry("2026-06-01 09:00", ENTRY, "Coarsely tagged", topics=["memory-trace"])
            + _entry("2026-06-01 10:00", OTHER, "Untouched", topics=["memory-trace"]),
            encoding="utf-8",
        )

    def _write_sidecar(self, entry_id, slugs, *, dt="2026-06-01 09:00", title="Coarsely tagged"):
        topics_dir = self.sessions / "topics" / "2026-06"
        topics_dir.mkdir(parents=True, exist_ok=True)
        body = [
            "---",
            "tags:",
            "  - session-log-topics",
            "topic_date: 2026-06-01",
            "---",
            "",
            f"## {dt} - {title}",
            "",
            "```yaml",
            f"entry_id: {entry_id}",
            "topics:",
        ]
        body += [f"  - {s}" for s in slugs]
        body += ["```", ""]
        (topics_dir / "2026-06-01.md").write_text("\n".join(body), encoding="utf-8")

    def _entry_topics(self, entry_id, *, rebuild=True):
        from fastapi.testclient import TestClient

        with mock.patch.dict(os.environ, {"MEMORY_SEED_LENSE_CACHE_ROOT": str(self.cache_root)}):
            app = create_app(self.cwd, rebuild_cache=rebuild)
            payload = TestClient(app).get("/api/graph", params={"granularity": "entry"}).json()
        for node in payload["nodes"]:
            if node.get("entry_id") == entry_id or node.get("id") == entry_id:
                return set(node.get("topics") or ())
        return None

    def test_attributed_slug_reaches_the_graph_node(self):
        # The walking skeleton: a slug that exists ONLY in a sidecar has to show
        # up on the node, or nothing downstream - filter, facet, colour - can
        # ever see it.
        self._write_sidecar(ENTRY, ["trail"])
        # The sidecar is the authority: `memory-trace` was authored and is now
        # superseded on the read path, not unioned with.
        self.assertEqual(self._entry_topics(ENTRY), {"trail"})

    def test_unattributed_entry_is_untouched(self):
        self._write_sidecar(ENTRY, ["trail"])
        self.assertEqual(self._entry_topics(OTHER), {"memory-trace"})

    def test_attribution_added_after_the_cache_was_built_is_picked_up(self):
        """The regression that decided WHERE the merge lives.

        Building the attribution into the stored chunk fails exactly here.
        `_session_documents_for` excludes sidecars from the incremental reparse
        - by design, because until now they produced no chunk rows - so a new
        attribution changes no session document, reparses nothing, and the
        stored chunk keeps its old topics until someone forces a full rebuild.
        Merging at read time off the cache generation has no such hole.
        """
        self.assertEqual(self._entry_topics(ENTRY), {"memory-trace"})  # cache now built, no sidecar
        self._write_sidecar(ENTRY, ["trail"])
        # NOT rebuilt: the attribution must surface on the existing cache.
        self.assertEqual(self._entry_topics(ENTRY, rebuild=False), {"trail"})

    def test_attributed_slug_reaches_the_facet_too(self):
        # The graph and the facet read different accessors. A slug the graph can
        # colour but the facet cannot list is a filter that offers no way to
        # reach what it shows - measured exactly that way round before
        # `_entry_chunks` did the merge.
        from fastapi.testclient import TestClient

        self._write_sidecar(ENTRY, ["trail"])
        with mock.patch.dict(os.environ, {"MEMORY_SEED_LENSE_CACHE_ROOT": str(self.cache_root)}):
            app = create_app(self.cwd, rebuild_cache=True)
            facets = TestClient(app).get("/api/facets").json()
        topics = facets["topics"]
        names = set(topics) if isinstance(topics, dict) else {t.get("value", t) for t in topics}
        self.assertIn("trail", names)

    def test_topic_sidecars_are_tracked_projection_inputs(self):
        # The freshness half. Without the sidecar in this list, a no-git corpus
        # serves stale topics after an attribution is edited, with nothing to
        # signal it.
        self._write_sidecar(ENTRY, ["trail"])
        tracked = {p.name for p in _tracked_document_paths(resolve_runtime(self.cwd))}
        self.assertIn("2026-06-01.md", tracked)
        paths = [str(p).replace(os.sep, "/") for p in _tracked_document_paths(resolve_runtime(self.cwd))]
        self.assertTrue(
            any("sessions/topics/" in p for p in paths),
            f"topic sidecars missing from the tracked inputs: {paths}",
        )


if __name__ == "__main__":
    unittest.main()
