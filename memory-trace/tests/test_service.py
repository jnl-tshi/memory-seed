import argparse
import io
import json
import os
import sqlite3
import subprocess
import shutil
import sys
import tempfile
import unittest
from contextlib import nullcontext, redirect_stderr
from pathlib import Path
from urllib.parse import quote
from unittest import mock

from memory_trace.cli import build_parser, main
from memory_trace.service import (
    _CacheRebuildLease,
    TraceCache,
    TraceService,
    create_app,
    missing_optional_dependency_hint,
    run_server,
)


def _entry(
    title,
    entry_id,
    body,
    *,
    agent="codex",
    related=None,
    branch=None,
    supersedes=None,
    evolves=None,
    continuity=None,
    topics=None,
):
    lines = [
        f"## {title}",
        "",
        "```yaml",
        f"entry_id: {entry_id}",
        "user_initials: JN",
        f"agent_type: {agent}",
        "project_path: .",
        "subproject_path: null",
    ]
    if branch:
        lines.append(f"branch: {branch}")
    if topics:
        lines.append("topics:")
        lines.extend(f"  - {topic}" for topic in topics)
    if related:
        lines.append("related_entries:")
        lines.extend(f"  - {ref}" for ref in related)
    if supersedes:
        lines.append("supersedes:")
        lines.extend(f"  - {ref}" for ref in supersedes)
    if evolves:
        lines.append("evolves:")
        lines.extend(f"  - {ref}" for ref in evolves)
    if continuity:
        lines.append("continuity:")
        for block in continuity:
            lines.append(f"  - kind: {block['kind']}")
            lines.append(f"    from: {block['from']}")
            if "to" in block and block["to"] is not None:
                lines.append(f"    to: {block['to']}")
    lines += ["```", "", body, ""]
    return "\n".join(lines)


class TraceServiceTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="memory-seed-lense-test-"))
        self.cache_root = Path(tempfile.mkdtemp(prefix="memory-seed-lense-cache-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(self.cache_root, ignore_errors=True))
        self.write_session(
            "2026-06-01.md",
            "\n".join(
                [
                    _entry(
                        "2026-06-01 09:00 - Bootstrap cache",
                        "mse_bootstrap",
                        "Built #cache support for bootstrap runtime discovery.",
                    ),
                    _entry(
                        "2026-06-01 12:00 - UI shell",
                        "mse_ui",
                        "Designed #ui filters and Memory Lense panes.",
                        related=["mse_bootstrap"],
                    ),
                ]
            ),
        )
        self.write_session(
            "2026-06-03.md",
            _entry(
                "2026-06-03 15:00 - Graph view",
                "mse_graph",
                "Graph neighborhood uses #ui and #graph edges.",
                agent="claude",
                related=["mse_ui"],
            ),
        )

    def write_session(self, filename, content):
        sessions = self.cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        path = sessions / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\ntags:\n  - session-log\n---\n\n" + content,
            encoding="utf-8",
        )

    def service(self):
        cache = TraceCache(self.cwd, cache_root=self.cache_root)
        cache.rebuild()
        return TraceService(cache)

    def test_cache_builds_facets_and_search_is_paged(self):
        service = self.service()

        facets = service.facets()
        page = service.search(q="Memory Lense ui", limit=1)

        self.assertEqual(facets["runtime"]["entry_count"], 3)
        self.assertEqual(facets["runtime"]["chunk_count"], 3)
        self.assertEqual(facets["runtime"]["date_bounds"], ["2026-06-01", "2026-06-03"])
        self.assertEqual(facets["agents"]["codex"], 2)
        self.assertEqual(facets["topics"]["ui"], 2)
        self.assertEqual(len(page["results"]), 1)
        self.assertEqual(page["results"][0]["chunk_id"], "mse_ui")
        self.assertIsNotNone(page["next_cursor"])

    def test_cache_rebuild_falls_back_when_sqlite_cannot_open_default_path(self):
        primary = self.cwd / "restricted" / "trace.sqlite3"
        fallback_temp = self.cache_root / "temporary-cache"
        cache = TraceCache(self.cwd, db_path=primary)
        real_connect = sqlite3.connect
        attempts = iter([sqlite3.OperationalError("unable to open database file")])

        def fail_once_then_connect(*args, **kwargs):
            try:
                raise next(attempts)
            except StopIteration:
                return real_connect(*args, **kwargs)

        with (
            mock.patch("memory_trace.service.tempfile.gettempdir", return_value=str(fallback_temp)),
            mock.patch("memory_trace.service.sqlite3.connect", side_effect=fail_once_then_connect),
        ):
            cache.rebuild()

        self.assertEqual(cache.db_path.parent, fallback_temp / "memory-seed" / "lense")
        self.assertTrue(cache.db_path.is_file())

    def test_cache_rebuild_falls_back_when_atomic_swap_is_denied(self):
        primary = self.cwd / "restricted" / "trace.sqlite3"
        fallback_temp = self.cache_root / "temporary-cache"
        cache = TraceCache(self.cwd, db_path=primary)
        real_replace = os.replace
        blocked_swaps = 0

        def deny_primary_swap(source, destination):
            nonlocal blocked_swaps
            if Path(destination) == primary:
                blocked_swaps += 1
                raise PermissionError("access denied")
            return real_replace(source, destination)

        with (
            mock.patch("memory_trace.service.tempfile.gettempdir", return_value=str(fallback_temp)),
            mock.patch("memory_trace.service.os.replace", side_effect=deny_primary_swap),
        ):
            cache.rebuild()

        self.assertEqual(blocked_swaps, 5)
        self.assertEqual(cache.db_path.parent, fallback_temp / "memory-seed" / "lense")
        self.assertTrue(cache.db_path.is_file())

    def test_cache_rebuild_lease_blocks_an_independent_process(self):
        lock_path = self.cache_root / "trace.sqlite3.lock"
        script = "\n".join(
            [
                "import sys",
                "from pathlib import Path",
                "from memory_trace.service import _CacheRebuildLease",
                "with _CacheRebuildLease(Path(sys.argv[1])).hold(timeout_seconds=0.1, retry_seconds=0.01) as acquired:",
                "    print('acquired' if acquired else 'busy')",
            ]
        )

        with _CacheRebuildLease(lock_path).hold(timeout_seconds=1, retry_seconds=0.01) as acquired:
            self.assertTrue(acquired)
            proc = subprocess.run(
                [sys.executable, "-c", script, str(lock_path)],
                capture_output=True,
                text=True,
                timeout=5,
            )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "busy")

    def test_cache_rebuild_uses_isolated_temp_cache_when_rebuild_lease_is_busy(self):
        primary = self.cwd / "shared" / "trace.sqlite3"
        fallback_temp = self.cache_root / "temporary-cache"
        first = TraceCache(self.cwd, db_path=primary)
        second = TraceCache(self.cwd, db_path=primary)

        with mock.patch("memory_trace.service.tempfile.gettempdir", return_value=str(fallback_temp)):
            with mock.patch.object(first, "_rebuild_lease", return_value=nullcontext(False)):
                first.rebuild()
            with mock.patch.object(second, "_rebuild_lease", return_value=nullcontext(False)):
                second.rebuild()

        self.assertEqual(first.db_path.parent, fallback_temp / "memory-seed" / "lense")
        self.assertEqual(second.db_path.parent, fallback_temp / "memory-seed" / "lense")
        self.assertNotEqual(first.db_path, second.db_path)
        self.assertTrue(first.db_path.is_file())
        self.assertTrue(second.db_path.is_file())

    def test_cache_reuses_snapshot_when_another_process_refreshed_under_lease(self):
        cache = TraceCache(self.cwd, cache_root=self.cache_root)
        cache.db_path.parent.mkdir(parents=True, exist_ok=True)
        cache.db_path.touch()

        with (
            mock.patch.object(cache, "_is_current", side_effect=[False, False, True]),
            mock.patch.object(cache, "_rebuild_locked") as rebuild,
        ):
            cache.ensure_current()

        rebuild.assert_not_called()

    def test_empty_entry_search_returns_recent_entries(self):
        service = self.service()

        page = service.search(q="", granularity="entry", limit=10)

        self.assertEqual(page["total"], 3)
        self.assertEqual(
            [item["entry_id"] for item in page["results"]],
            ["mse_graph", "mse_ui", "mse_bootstrap"],
        )
        self.assertTrue(all(item["score"] == 0.0 for item in page["results"]))

    def test_entry_search_rolls_up_section_matches(self):
        # Entry-level UI results plan: one selectable result per session entry,
        # even when section chunks drive the best score; matched sections ride
        # along as highlight metadata via the shared retrieval-service rollup.
        self.write_session(
            "2026-06-05.md",
            "\n".join(
                [
                    "## 2026-06-05 09:00 - Zanzibar cache keys",
                    "",
                    "```yaml",
                    "entry_id: mse_zanzibar",
                    "user_initials: JN",
                    "agent_type: codex",
                    "project_path: .",
                    "subproject_path: null",
                    "```",
                    "",
                    "Reworked cache key generation.",
                    "",
                    "### Decision",
                    "",
                    "- D: Use zanzibar tokens for cache keys.",
                    "",
                    "### Tests",
                    "",
                    "- T: zanzibar token round-trip coverage added.",
                    "",
                ]
            ),
        )
        service = self.service()

        page = service.search(q="zanzibar tokens", granularity="entry")

        top = page["results"][0]
        self.assertEqual(top["entry_id"], "mse_zanzibar")
        self.assertEqual(top["granularity"], "entry")
        self.assertEqual(top["chunk_id"], "mse_zanzibar")
        # No separate selectable record for any section of the same entry.
        zanzibar_records = [r for r in page["results"] if r["entry_id"] == "mse_zanzibar"]
        self.assertEqual(len(zanzibar_records), 1)
        # Highlight metadata survives the rollup.
        self.assertIn("matched_sections", top)
        self.assertIn(top["score_source"], {"entry", "section-rollup"})
        for section in top["matched_sections"]:
            self.assertTrue(section["chunk_id"].startswith("mse_zanzibar#"))
        # Section granularity remains available and un-rolled for debug views.
        raw = service.search(q="zanzibar tokens", granularity="section")
        self.assertTrue(any(r["chunk_id"].startswith("mse_zanzibar#") for r in raw["results"]))
        self.assertNotIn("matched_sections", raw["results"][0])

    def test_chunk_view_carries_diagram_sidecar_metadata(self):
        # mse_bootstrap's real entry date (from setUp) is 2026-06-01 - the
        # diagrams file is dated to match, one file per day like session logs.
        diagrams = self.cwd / ".memory-seed" / "sessions" / "diagrams"
        diagrams.mkdir(parents=True, exist_ok=True)
        (diagrams / "2026-06-01.md").write_text(
            "## 2026-06-01 09:00 - Bootstrap flow\n\n"
            "```yaml\nentry_id: mse_bootstrap\n```\n\n"
            "```mermaid\nflowchart TD\n  A --> B\n```\n",
            encoding="utf-8",
        )
        service = self.service()

        with_diagram = service.chunk("mse_bootstrap")
        self.assertEqual(len(with_diagram["diagrams"]), 1)
        self.assertEqual(with_diagram["diagrams"][0]["title"], "Bootstrap flow")
        without_diagram = service.chunk("mse_ui")
        self.assertEqual(without_diagram["diagrams"], [])

    def test_cache_and_chunk_view_use_grouped_sessions_and_diagrams(self):
        self.write_session(
            "2026-06/2026-06-04.md",
            _entry(
                "2026-06-04 09:00 - Grouped flat entry",
                "mse_grouped_flat",
                "Grouped month session files are parsed through memory_seed.core.",
            ),
        )
        diagrams = self.cwd / ".memory-seed" / "sessions" / "diagrams" / "2026-06"
        diagrams.mkdir(parents=True, exist_ok=True)
        (diagrams / "2026-06-04.md").write_text(
            "## 2026-06-04 09:00 - Grouped diagram\n\n"
            "```yaml\nentry_id: mse_grouped_flat\n```\n\n"
            "```mermaid\nflowchart TD\n  A --> B\n```\n",
            encoding="utf-8",
        )

        service = self.service()

        page = service.search(q="grouped month", granularity="entry")
        self.assertEqual(page["results"][0]["entry_id"], "mse_grouped_flat")
        chunk = service.chunk("mse_grouped_flat")
        self.assertEqual(chunk["path"], ".memory-seed/sessions/2026-06/2026-06-04.md")
        self.assertEqual(chunk["diagrams"][0]["path"], ".memory-seed/sessions/diagrams/2026-06/2026-06-04.md")

    def test_cache_rebuilds_when_session_file_metadata_changes(self):
        cache = TraceCache(self.cwd, cache_root=self.cache_root)
        # Disable the freshness memo window so a change made immediately after a
        # build is re-checked (rather than trusted for the TTL); this test pins
        # the change-detection, not the memoization.
        cache._FRESHNESS_TTL_SECONDS = 0
        cache.rebuild()
        first = cache.status()

        session_file = self.cwd / ".memory-seed" / "sessions" / "2026-06-03.md"
        session_file.write_text(session_file.read_text(encoding="utf-8") + "\nExtra #cache text.\n", encoding="utf-8")
        cache.ensure_current()

        second = cache.status()
        self.assertGreater(second["rebuilt_at"], first["rebuilt_at"])
        self.assertEqual(second["file_count"], 2)

    def test_timeline_includes_inactive_buckets_for_zoom_levels(self):
        service = self.service()

        timeline = service.timeline(date_from="2026-06-01", date_to="2026-06-03", zoom="day")
        zoomed = service.timeline(date_from="2026-06-01", date_to="2026-06-01", zoom="3h")

        self.assertEqual([bucket["date"] for bucket in timeline["buckets"]], ["2026-06-01", "2026-06-02", "2026-06-03"])
        self.assertEqual([bucket["count"] for bucket in timeline["buckets"]], [2, 0, 1])
        self.assertEqual(len(zoomed["buckets"]), 8)
        self.assertEqual(sum(bucket["count"] for bucket in zoomed["buckets"]), 2)

    def test_timeline_can_omit_empty_buckets(self):
        service = self.service()

        timeline = service.timeline(date_from="2026-06-01", date_to="2026-06-03", zoom="day", include_empty=False)
        zoomed = service.timeline(date_from="2026-06-01", date_to="2026-06-01", zoom="3h", include_empty=False)

        self.assertEqual([bucket["date"] for bucket in timeline["buckets"]], ["2026-06-01", "2026-06-03"])
        self.assertEqual([bucket["count"] for bucket in timeline["buckets"]], [2, 1])
        self.assertEqual(len(zoomed["buckets"]), 2)
        self.assertEqual(sum(bucket["count"] for bucket in zoomed["buckets"]), 2)

    def test_timeline_respects_agent_user_and_topic_filters(self):
        service = self.service()

        agent_filtered = service.timeline(date_from="2026-06-01", date_to="2026-06-03", agent="claude")
        topic_filtered = service.timeline(date_from="2026-06-01", date_to="2026-06-03", topic="ui")

        self.assertEqual(sum(bucket["count"] for bucket in agent_filtered["buckets"]), 1)
        self.assertEqual([item["entry_id"] for item in agent_filtered["stream"]], ["mse_graph"])
        self.assertEqual(sum(bucket["count"] for bucket in topic_filtered["buckets"]), 2)
        self.assertEqual({item["entry_id"] for item in topic_filtered["stream"]}, {"mse_ui", "mse_graph"})

    def test_graph_uses_explicit_edges_and_respects_type_limits(self):
        service = self.service()

        graph = service.graph(entry_id="mse_ui", edge_types=("related",), limit=2)

        self.assertLessEqual(len(graph["nodes"]), 2)
        self.assertEqual(graph["edges"][0]["source"], "mse_ui")
        self.assertEqual(graph["edges"][0]["target"], "mse_bootstrap")
        self.assertEqual(graph["edges"][0]["type"], "related")

    def test_trail_view_renders_supersedes_edge_and_branch_axis(self):
        # Trail view (Arc 2c): a later decision supersedes an earlier one on the
        # same branch. supersedes is a directed status edge; branch is a
        # time-ordered lineage axis. Both are additive to the same graph engine.
        self.write_session(
            "2026-06-10.md",
            "\n".join(
                [
                    _entry("2026-06-10 09:00 - First take", "mse_old", "First.", branch="feature/x"),
                    _entry("2026-06-10 12:00 - Revised take", "mse_revised", "Revised.",
                           branch="feature/x", supersedes=["mse_old"]),
                ]
            ),
        )
        service = self.service()

        graph = service.graph(edge_types=("branch", "supersedes", "related"))
        by_type = {}
        for edge in graph["edges"]:
            by_type.setdefault(edge["type"], []).append((edge["source"], edge["target"]))
        # Directed supersession: the edge runs source -> target where source
        # supersedes (replaces) target. mse_revised (newer, carries supersedes:)
        # points at mse_old (older) - and never the reverse, which would tell a
        # reader the stale decision is the current one.
        self.assertIn(("mse_revised", "mse_old"), by_type.get("supersedes", []))
        self.assertNotIn(("mse_old", "mse_revised"), by_type.get("supersedes", []))
        # Intra-branch lineage runs in time order along the shared branch.
        self.assertIn(("mse_old", "mse_revised"), by_type.get("branch", []))
        # Asking for only related must not surface the trail edge types.
        related_only = service.graph(edge_types=("related",))
        self.assertNotIn("supersedes", {edge["type"] for edge in related_only["edges"]})
        self.assertNotIn("branch", {edge["type"] for edge in related_only["edges"]})

    def test_graph_emits_evolves_edges_and_node_lineage_fields(self):
        # evolves is the freshness-without-retirement lifecycle edge; the Trail
        # renderer also needs branch + datetime on every node to lay out lanes
        # and rows without a second fetch.
        self.write_session(
            "2026-06-11.md",
            "\n".join(
                [
                    _entry("2026-06-11 09:00 - Original approach", "mse_ev_base", "Base.",
                           branch="feature/y"),
                    _entry("2026-06-11 12:00 - Refined approach", "mse_ev_next", "Refined.",
                           branch="feature/y", evolves=["mse_ev_base"]),
                ]
            ),
        )
        service = self.service()

        graph = service.graph(edge_types=("branch", "evolves"))
        by_type = {}
        for edge in graph["edges"]:
            by_type.setdefault(edge["type"], []).append((edge["source"], edge["target"]))
        # Directed: the newer entry (carrying evolves:) points at the older one.
        self.assertIn(("mse_ev_next", "mse_ev_base"), by_type.get("evolves", []))
        self.assertNotIn(("mse_ev_base", "mse_ev_next"), by_type.get("evolves", []))
        nodes = {node["id"]: node for node in graph["nodes"]}
        self.assertEqual(nodes["mse_ev_base"]["branch"], "feature/y")
        self.assertEqual(nodes["mse_ev_base"]["datetime"], "2026-06-11T09:00:00")
        # Asking for evolves alone must not leak other edge kinds.
        evolves_only = service.graph(edge_types=("evolves",))
        self.assertEqual({edge["type"] for edge in evolves_only["edges"]}, {"evolves"})

    def test_graph_and_chunk_expose_authored_continuity_in_order(self):
        self.write_session(
            "2026-06-12.md",
            "\n".join(
                [
                    _entry("2026-06-12 09:00 - Baseline", "mse_plain", "Plain.", branch="main"),
                    _entry(
                        "2026-06-12 11:00 - Rename and migrate",
                        "mse_cont",
                        "Moved the product and runtime.",
                        branch="main",
                        continuity=[
                            {"kind": "rename", "from": "Memory Lense", "to": "Memory Trace"},
                            {"kind": "migration", "from": ".AGENTS/", "to": ".memory-seed/"},
                            {"kind": "removal", "from": "memory-seed lense command"},
                        ],
                    ),
                ]
            ),
        )
        service = self.service()

        graph = service.graph(edge_types=("branch",), granularity="entry", limit=100)
        nodes = {node["id"]: node for node in graph["nodes"]}
        self.assertEqual(
            nodes["mse_cont"]["continuity"],
            [
                {"kind": "rename", "from": "Memory Lense", "to": "Memory Trace"},
                {"kind": "migration", "from": ".AGENTS/", "to": ".memory-seed/"},
                {"kind": "removal", "from": "memory-seed lense command", "to": None},
            ],
        )
        self.assertEqual(nodes["mse_plain"]["continuity"], [])

        chunk = service.chunk("mse_cont")
        self.assertEqual(chunk["continuity"], nodes["mse_cont"]["continuity"])
        self.assertEqual(service.chunk("mse_plain")["continuity"], [])

    def test_facets_and_filters_include_indexed_topics(self):
        # Indexed topics (entry YAML `topics:`) must feed the topics facet and
        # the topic filter, not just inline #tags.
        self.write_session(
            "2026-06-12.md",
            _entry("2026-06-12 09:00 - Topic-carrying entry", "mse_topical", "Body.",
                   topics=["retrieval", "graph"]),
        )
        service = self.service()

        facets = service.facets()
        self.assertIn("retrieval", facets["topics"])
        self.assertIn("graph", facets["topics"])
        page = service.search(q="", topic="retrieval", granularity="entry")
        self.assertEqual({item["entry_id"] for item in page["results"]}, {"mse_topical"})

    def test_indexed_topics_preferred_over_derived_tags(self):
        # topics P4: an entry carrying authored `topics:` shows exactly those in
        # the facet and node - its inline #hashtags no longer leak in. An entry
        # with no authored topics still falls back to hashtag/context derivation.
        self.write_session(
            "2026-06-20.md",
            _entry("2026-06-20 09:00 - Authored", "mse_auth",
                   "Body carrying a #legacyhash inline tag.", topics=["retrieval"])
            + _entry("2026-06-20 10:00 - Derived", "mse_deriv",
                     "Body carrying only a #fallbackhash inline tag."),
        )
        service = self.service()

        facets = service.facets()
        self.assertIn("retrieval", facets["topics"])       # authored slug surfaces
        self.assertNotIn("legacyhash", facets["topics"])   # its hashtag is suppressed
        self.assertIn("fallbackhash", facets["topics"])    # old-style entry keeps the fallback

        graph = service.graph(granularity="entry", limit=50)
        by_id = {node["entry_id"]: node for node in graph["nodes"]}
        self.assertEqual(by_id["mse_auth"]["topics"], ["retrieval"])
        self.assertEqual(by_id["mse_deriv"]["topics"], ["fallbackhash"])

    def test_topic_filter_is_vocabulary_aware(self):
        # topics P4: filtering by a canonical slug matches entries that stored an
        # alias of it and vice versa - the Trace filter now expands through
        # topics.yaml the way the core retrieval path does. Date-scoped to the
        # test entries so setUp's #graph-derived entries don't confound it.
        (self.cwd / ".memory-seed").mkdir(parents=True, exist_ok=True)
        (self.cwd / ".memory-seed" / "topics.yaml").write_text(
            "schema_version: 1\ntopics:\n  - slug: graph\n    aliases: [related-entries, supersession]\n",
            encoding="utf-8",
        )
        self.write_session(
            "2026-06-21.md",
            _entry("2026-06-21 09:00 - Canonical", "mse_canon", "Body.", topics=["graph"])
            + _entry("2026-06-21 10:00 - Alias", "mse_alias", "Body.", topics=["related-entries"])
            + _entry("2026-06-21 11:00 - Unrelated", "mse_other", "Body.", topics=["retrieval"]),
        )
        service = self.service()

        # Filter by the canonical slug -> canonical AND alias-stored entries.
        by_canon = service.timeline(date_from="2026-06-21", date_to="2026-06-21", topic="graph")
        self.assertEqual({item["entry_id"] for item in by_canon["stream"]}, {"mse_canon", "mse_alias"})

        # Filter by the alias -> resolves to the same canonical match set.
        by_alias = service.graph(
            granularity="entry", topic="related-entries", date_from="2026-06-21", date_to="2026-06-21", limit=50
        )
        self.assertEqual({node["entry_id"] for node in by_alias["nodes"]}, {"mse_canon", "mse_alias"})

    def test_graph_nodes_flag_entries_with_decision_diagram_sidecars(self):
        # session-decision-diagrams plan: the Trail/Graph badge is driven by a
        # has_diagram flag on graph nodes - true for entries carrying a Class-2
        # sidecar, false otherwise (the diagram source is fetched lazily, so the
        # node payload stays a boolean).
        self.write_session(
            "2026-06-25.md",
            _entry("2026-06-25 09:00 - With diagram", "mse_diag", "Body.")
            + _entry("2026-06-25 10:00 - Without diagram", "mse_nodiag", "Body."),
        )
        diagrams = self.cwd / ".memory-seed" / "sessions" / "diagrams"
        diagrams.mkdir(parents=True, exist_ok=True)
        (diagrams / "2026-06-25.md").write_text(
            "---\ntags:\n  - session-log-diagrams\ndiagram_date: 2026-06-25\n---\n\n"
            "## 2026-06-25 09:00 - With diagram\n\n"
            "```yaml\nentry_id: mse_diag\n```\n\n"
            "```mermaid\nflowchart TD\n  A --> B\n```\n",
            encoding="utf-8",
        )
        service = self.service()

        graph = service.graph(granularity="entry", limit=50)
        by_id = {node["entry_id"]: node for node in graph["nodes"]}
        self.assertTrue(by_id["mse_diag"]["has_diagram"])
        self.assertFalse(by_id["mse_nodiag"]["has_diagram"])

    def test_chunk_reports_commit_and_batch_siblings(self):
        # Commit packaging: each entry maps to the oldest commit whose diff
        # added it, so main-era work with no immediate commit rides "the next
        # commit that occurred" (batch commits, pre-branching history). An
        # appended-but-uncommitted entry reports commit None with tracking on.
        def git(*args):
            subprocess.run(["git", "-C", str(self.cwd), *args], check=True, capture_output=True)

        git("init")
        git("config", "user.email", "test@example.com")
        git("config", "user.name", "Test")
        git("config", "commit.gpgsign", "false")
        git("add", "-A")
        git("commit", "-m", "batch: seed sessions")
        self.write_session("2026-06-05.md", _entry("2026-06-05 09:00 - Later work", "mse_later", "Later."))
        git("add", "-A")
        git("commit", "-m", "second commit")
        service = self.service()

        detail = service.chunk("mse_bootstrap")
        self.assertEqual(detail["commit"]["subject"], "batch: seed sessions")
        self.assertTrue(detail["commit_tracking"])
        # The whole seeded batch shares the commit; later work does not.
        self.assertIn("mse_ui", detail["commit_entry_ids"])
        self.assertIn("mse_graph", detail["commit_entry_ids"])
        self.assertNotIn("mse_later", detail["commit_entry_ids"])
        sibling_ids = {item["entry_id"] for item in detail["commit_entries"]}
        self.assertIn("mse_ui", sibling_ids)
        self.assertNotIn("mse_bootstrap", sibling_ids)  # never lists itself

        later = service.chunk("mse_later")
        self.assertEqual(later["commit"]["subject"], "second commit")

        self.write_session("2026-06-06.md", _entry("2026-06-06 09:00 - Uncommitted", "mse_uncommitted", "Pending."))
        pending = self.service().chunk("mse_uncommitted")
        self.assertIsNone(pending["commit"])
        self.assertTrue(pending["commit_tracking"])

        # Evidence-based main attribution: no-branch entries captured by a
        # first-parent trunk commit join main (inferred); the uncommitted one
        # has no evidence and stays unattached.
        nodes = {node["id"]: node for node in self.service().graph(edge_types=("branch",))["nodes"]}
        self.assertEqual(nodes["mse_bootstrap"]["branch"], "main")
        self.assertTrue(nodes["mse_bootstrap"]["branch_inferred"])
        self.assertIsNone(nodes["mse_uncommitted"]["branch"])
        self.assertFalse(nodes["mse_uncommitted"]["branch_inferred"])

    def test_graph_is_entry_level_and_reports_connectivity(self):
        self.write_session(
            "2026-06-04.md",
            _entry(
                "2026-06-04 09:00 - Sectioned graph entry",
                "mse_sectioned",
                "### Summary\n\nGraph should include sections.\n\n### Decision\n\nUse chunk-level nodes.\n\n### Validation\n\nCheck graph count.",
            ),
        )
        service = self.service()

        graph = service.graph(granularity="all", edge_types=("related", "agent", "day"), limit=20)
        by_id = {node["entry_id"]: node for node in graph["nodes"]}

        self.assertEqual(graph["granularity"], "entry")
        self.assertEqual(len(graph["nodes"]), 4)
        self.assertEqual({node["granularity"] for node in graph["nodes"]}, {"entry"})
        self.assertEqual(by_id["mse_ui"]["connectivity"], 2)
        self.assertEqual(by_id["mse_bootstrap"]["connectivity"], 1)
        self.assertEqual(by_id["mse_graph"]["connectivity"], 1)
        self.assertEqual(by_id["mse_sectioned"]["connectivity"], 0)
        self.assertIn("topics", by_id["mse_ui"])
        self.assertIn("date", by_id["mse_ui"])
        self.assertIn("agent", by_id["mse_ui"])
        self.assertGreaterEqual(len(graph["edges"]), 1)

    def test_graph_reports_importance_score_distinct_from_connectivity(self):
        service = self.service()

        graph = service.graph(edge_types=("related",), limit=20)
        by_id = {node["entry_id"]: node for node in graph["nodes"]}

        # mse_ui is cited by mse_graph (inbound 1) and cites mse_bootstrap
        # (outbound 1): connectivity counts both directions (2), importance_score
        # counts inbound only (1.0). Same node, two deliberately different numbers.
        self.assertEqual(by_id["mse_ui"]["connectivity"], 2)
        self.assertEqual(by_id["mse_ui"]["importance_score"], 1.0)
        self.assertEqual(by_id["mse_bootstrap"]["importance_score"], 1.0)
        self.assertEqual(by_id["mse_graph"]["importance_score"], 0.0)

    def test_graph_connectivity_ignores_derived_edges(self):
        service = self.service()

        derived = service.graph(edge_types=("topic", "agent", "day"), limit=20)
        by_id = {node["entry_id"]: node for node in derived["nodes"]}

        self.assertGreaterEqual(len(derived["edges"]), 1)
        self.assertEqual(by_id["mse_bootstrap"]["connectivity"], 1)
        self.assertEqual(by_id["mse_ui"]["connectivity"], 2)
        self.assertEqual(by_id["mse_graph"]["connectivity"], 1)

    def test_graph_respects_active_filters(self):
        service = self.service()

        agent_graph = service.graph(granularity="all", agent="claude", edge_types=("agent", "day"), limit=20)
        topic_graph = service.graph(granularity="all", topic="ui", edge_types=("agent", "day"), limit=20)

        self.assertEqual([node["entry_id"] for node in agent_graph["nodes"]], ["mse_graph"])
        self.assertEqual({node["entry_id"] for node in topic_graph["nodes"]}, {"mse_ui", "mse_graph"})

    def test_graph_overview_slice_prefers_connected_subgraph(self):
        # Regression: the all-dates overview (no entry_id, no date filter) used
        # to truncate nodes in corpus order, so a limit smaller than the corpus
        # kept the oldest - edgeless - entries and rendered a disconnected map.
        self.write_session(
            "2026-05-01.md",
            "\n".join(
                _entry(
                    f"2026-05-01 0{index}:00 - Isolated note {index}",
                    f"mse_iso{index}",
                    "Standalone note without lifecycle links.",
                    topics=[f"iso{index}"],
                )
                for index in range(1, 9)
            ),
        )
        self.write_session(
            "2026-06-05.md",
            "\n".join(
                _entry(
                    f"2026-06-05 1{index}:00 - Cluster step {index}",
                    f"mse_cluster{index}",
                    "Connected lineage work.",
                    related=[f"mse_cluster{index - 1}"] if index else None,
                    topics=["cluster"],
                )
                for index in range(5)
            ),
        )
        service = self.service()
        edge_types = ("related", "supersedes", "evolves", "topic")

        overview = service.graph(edge_types=edge_types, limit=6)
        repeat = service.graph(edge_types=edge_types, limit=6)

        node_ids = [node["id"] for node in overview["nodes"]]
        self.assertEqual(len(node_ids), 6)
        # The slice keeps the connected cluster instead of the oldest rows, so
        # the intra-slice edge set is non-trivial on a corpus that has edges.
        self.assertGreaterEqual(len(overview["edges"]), 4)
        self.assertTrue({f"mse_cluster{index}" for index in range(5)}.issubset(set(node_ids)))
        # Deterministic: the same request always selects the same slice.
        self.assertEqual(node_ids, [node["id"] for node in repeat["nodes"]])
        self.assertEqual(overview["edges"], repeat["edges"])

        from memory_trace.graph_projection import project_trace_graph

        projection = project_trace_graph(overview)
        self.assertEqual(len(projection["nodes"]), 6)
        self.assertEqual(len(projection["edges"]), len(overview["edges"]))

    def test_chunk_api_accepts_encoded_path_chunk_ids(self):
        self.write_session(
            "2026-06-05.md",
            "## 2026-06-05 10:00 - Heading without metadata\n\nPath-style chunk id body.\n",
        )
        cache = TraceCache(self.cwd, cache_root=self.cache_root)
        cache.rebuild()
        chunk_id = next(chunk.chunk_id for chunk in cache.chunks() if "/" in chunk.chunk_id)

        from fastapi.testclient import TestClient

        with mock.patch.dict(os.environ, {"MEMORY_SEED_LENSE_CACHE_ROOT": str(self.cache_root)}):
            client = TestClient(create_app(self.cwd))
        response = client.get(f"/api/chunks/{quote(chunk_id, safe='')}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["chunk_id"], chunk_id)

    def test_chunk_details_include_related_backlinks_and_metadata(self):
        service = self.service()

        chunk = service.chunk("mse_ui")

        self.assertEqual(chunk["chunk_id"], "mse_ui")
        self.assertEqual(chunk["related_entries"], ["mse_bootstrap"])
        self.assertEqual(chunk["backlinks"], ["mse_graph"])
        self.assertEqual(chunk["line_range"], [18, 30])
        self.assertIn("source", chunk["metadata"])


class MemoryTraceCliAndVanillaUiTests(unittest.TestCase):
    def test_open_both_flag_is_available_and_excludes_no_open(self):
        args = build_parser().parse_args(["--open-both"])

        self.assertTrue(args.open_both)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            build_parser().parse_args(["--open-both", "--no-open"])

    def test_run_server_opens_vanilla_and_react_tabs_when_requested(self):
        app = object()
        uvicorn = mock.Mock()
        args = argparse.Namespace(
            cwd=".",
            host="127.0.0.1",
            port=8765,
            no_open=False,
            open_both=True,
            rebuild_cache=False,
            static_root=None,
        )

        with (
            mock.patch.dict(sys.modules, {"uvicorn": uvicorn}),
            mock.patch("memory_trace.service.create_app", return_value=app),
            mock.patch("memory_trace.service.webbrowser.open") as open_browser,
        ):
            code = run_server(args)

        self.assertEqual(code, 0)
        self.assertEqual(
            open_browser.call_args_list,
            [
                mock.call("http://127.0.0.1:8765", new=2),
                mock.call("http://127.0.0.1:8765/next", new=2),
            ],
        )
        uvicorn.run.assert_called_once_with(app, host="127.0.0.1", port=8765, log_level="info")

    def test_source_checkout_launcher_opens_both_views(self):
        launcher = Path(__file__).resolve().parents[2] / "scripts" / "launch-memory-trace.ps1"
        script = launcher.read_text(encoding="utf-8")

        self.assertIn("--open-both", script)
        self.assertIn('"$baseUrl/next"', script)
        self.assertIn("/api/runtime", script)

    def test_missing_optional_dependency_hint_is_explicit(self):
        self.assertEqual(
            missing_optional_dependency_hint(),
            'Install with: pip install "memory-seed[trace]"',
        )

    def test_memory_trace_command_prints_install_hint_when_fastapi_missing(self):
        real_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "fastapi":
                raise ModuleNotFoundError("No module named 'fastapi'")
            return real_import(name, *args, **kwargs)

        stderr = io.StringIO()
        with mock.patch.dict(os.environ, {"MEMORY_SEED_LENSE_SKIP_BROWSER": "1"}), mock.patch(
            "builtins.__import__", side_effect=fake_import
        ), redirect_stderr(stderr):
            code = main(["--cwd", ".", "--host", "127.0.0.1", "--port", "0", "--no-open"])

        self.assertEqual(code, 1)
        self.assertIn('Install with: pip install "memory-seed[trace]"', stderr.getvalue())

    def test_static_manifest_is_packaged(self):
        import importlib.resources as resources

        manifest = resources.files("memory_trace").joinpath("static/manifest.json")
        data = json.loads(manifest.read_text(encoding="utf-8"))

        self.assertEqual(data["name"], "Memory Trace")
        self.assertIn("index.html", data["files"])
        self.assertIn("benchmark.html", data["files"])
        self.assertIn("renderer-benchmark.js", data["files"])
        self.assertIn("react/index.html", data["files"])

    def test_frontend_defines_design_token_baseline_and_uses_color_tokens(self):
        # Arc 2b: a small reusable token set (spacing/type/color roles), with the
        # graph edge-type + status color semantics as tokens - one job per color.
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")
        styles = resources.files("memory_trace").joinpath("static/styles.css").read_text(encoding="utf-8")

        for token in ("--space-md:", "--fs-body:", "--radius-md:", "--edge-supersedes:", "--edge-branch:", "--status-superseded:"):
            self.assertIn(token, styles)
        # edgeColor() is the single JS reference and reads the tokens, not hex.
        self.assertIn("var(--edge-supersedes)", script)
        self.assertIn("var(--edge-branch)", script)
        self.assertNotIn('supersedes: "#d94b63"', script)

    def test_frontend_has_builtin_diagram_renderer_with_source_fallback(self):
        # Arc 2d: a minimal offline renderer for the flowchart/sequence subset,
        # degrading unsupported diagrams to their raw source (never a blank frame).
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")
        styles = resources.files("memory_trace").joinpath("static/styles.css").read_text(encoding="utf-8")

        self.assertIn("function renderDiagramBlock(", script)
        self.assertIn("function renderFlowchart(", script)
        self.assertIn("function renderSequenceDiagram(", script)
        self.assertIn("function diagramsSection(", script)
        self.assertIn("mermaid_blocks", script)
        self.assertIn("diagram-source", script)  # source fallback
        self.assertIn("Decision diagrams", script)  # reader section
        self.assertIn(".diagram-svg", styles)

    def test_frontend_flowchart_lr_renderer_uses_horizontal_geometry(self):
        import importlib.resources as resources

        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not available")
        script_path = resources.files("memory_trace").joinpath("static/app.js")
        probe = r"""
const fs = require("fs");
const src = fs.readFileSync(process.argv[1], "utf8");
function pick(name, nextName) {
  const start = src.indexOf(`function ${name}(`);
  const end = src.indexOf(`\nfunction ${nextName}`, start);
  if (start < 0 || end < 0) throw new Error(`missing ${name}`);
  return src.slice(start, end);
}
eval([
        pick("_diagramNode", "_diagramLabelLines"),
        pick("_diagramLabelLines", "_diagramNodeSize"),
        pick("_diagramNodeSize", "_diagramFlowLayout"),
        pick("_diagramFlowLayout", "_diagramEdgePath"),
        pick("_diagramEdgePath", "renderFlowchart"),
        pick("renderFlowchart", "renderSequenceDiagram"),
        pick("_diagramArrowDefs", "markdown"),
        pick("esc", "escAttr"),
        "function escAttr(value) { return esc(value); }",
].join("\n"));
const svg = renderFlowchart("flowchart LR\n  A[Alpha] --> B[Beta]");
const rects = [...svg.matchAll(/<rect x="([^"]+)" y="([^"]+)" width="([^"]+)" height="([^"]+)"/g)]
  .map((match) => match.slice(1).map(Number));
const path = svg.match(/<path class="diagram-edge" d="M ([^ ]+) ([^ ]+) C ([^ ]+) ([^,]+), ([^ ]+) ([^,]+), ([^ ]+) ([^"]+)"/);
if (rects.length !== 2 || !path) throw new Error(svg);
const [a, b] = rects;
const coords = path.slice(1).map(Number);
const horizontalOverlap = Math.max(0, Math.min(a[0] + a[2], b[0] + b[2]) - Math.max(a[0], b[0]));
if (horizontalOverlap > 0) {
  throw new Error(`LR nodes overlap by ${horizontalOverlap}px`);
}
const endpoints = [coords[0], coords[1], coords[6], coords[7]];
const expected = [a[0] + a[2], a[1] + a[3] / 2, b[0], b[1] + b[3] / 2];
if (endpoints.some((value, index) => value !== expected[index])) {
  throw new Error(`LR path ${endpoints.join(",")} should be ${expected.join(",")}`);
}
"""
        result = subprocess.run([node, "-e", probe, str(script_path)], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_frontend_flowchart_centres_merge_nodes_and_routes_curves(self):
        import importlib.resources as resources

        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not available")
        script_path = resources.files("memory_trace").joinpath("static/app.js")
        probe = r"""
const fs = require("fs");
const src = fs.readFileSync(process.argv[1], "utf8");
function pick(name, nextName) {
  const start = src.indexOf(`function ${name}(`);
  const end = src.indexOf(`\nfunction ${nextName}`, start);
  if (start < 0 || end < 0) throw new Error(`missing ${name}`);
  return src.slice(start, end);
}
eval([
  pick("_diagramNode", "_diagramLabelLines"),
  pick("_diagramLabelLines", "_diagramNodeSize"),
  pick("_diagramNodeSize", "_diagramFlowLayout"),
  pick("_diagramFlowLayout", "_diagramEdgePath"),
  pick("_diagramEdgePath", "renderFlowchart"),
  pick("renderFlowchart", "renderSequenceDiagram"),
  pick("_diagramArrowDefs", "markdown"),
  pick("esc", "escAttr"),
  "function escAttr(value) { return esc(value); }",
].join("\n"));
const source = `flowchart LR
  H["Malformed main session headings"] --> R["Structural heading repair"]
  R --> B["Rebase B0a branch"]
  B --> F["Session-aware fuse"]
  F --> M["B0a merge on main"]
  E["Completed renderer evidence"] --> S["Select Cytoscape.js"]
  S --> M
  M --> P["Approved push to origin/main"]`;
const svg = renderFlowchart(source);
const nodes = new Map([...svg.matchAll(/data-diagram-node="([^"]+)"[^>]*><rect x="([^"]+)" y="([^"]+)" width="([^"]+)" height="([^"]+)"/g)]
  .map((match) => [match[1], match.slice(2).map(Number)]));
const paths = [...svg.matchAll(/<path class="diagram-edge"[^>]+marker-end=/g)];
if (nodes.size !== 8 || paths.length !== 7) throw new Error(svg);
const centerY = (id) => nodes.get(id)[1] + nodes.get(id)[3] / 2;
const expectedMergeY = (centerY("F") + centerY("S")) / 2;
if (centerY("M") !== expectedMergeY || centerY("P") !== expectedMergeY) {
  throw new Error(`merge chain ${centerY("M")},${centerY("P")} should be ${expectedMergeY}`);
}
if (new Set([...nodes.values()].map((rect) => rect[2])).size < 2) {
  throw new Error("node widths should reflect their labels");
}
"""
        result = subprocess.run([node, "-e", probe, str(script_path)], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_frontend_flowchart_centres_single_node_vertical_ranks(self):
        import importlib.resources as resources

        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not available")
        script_path = resources.files("memory_trace").joinpath("static/app.js")
        probe = r"""
const fs = require("fs");
const src = fs.readFileSync(process.argv[1], "utf8");
function pick(name, nextName) {
  const start = src.indexOf(`function ${name}(`);
  const end = src.indexOf(`\nfunction ${nextName}`, start);
  if (start < 0 || end < 0) throw new Error(`missing ${name}`);
  return src.slice(start, end);
}
eval([
  pick("_diagramNode", "_diagramLabelLines"),
  pick("_diagramLabelLines", "_diagramNodeSize"),
  pick("_diagramNodeSize", "_diagramFlowLayout"),
  pick("_diagramFlowLayout", "_diagramEdgePath"),
  pick("_diagramEdgePath", "renderFlowchart"),
  pick("renderFlowchart", "renderSequenceDiagram"),
  pick("_diagramArrowDefs", "markdown"),
  pick("esc", "escAttr"),
  "function escAttr(value) { return esc(value); }",
].join("\n"));
const source = `graph TD
  W["OneDrive worktree<br>write denied"] --> R["Root-branch fallback"]
  R --> H["Packaged B0a harness"]
  H --> V["vis-network<br>blank canvas"]
  H --> C["Cytoscape.js<br>initial pass"]
  V ~~~ C
  V --> G["Decision remains open"]
  C --> G`;
const svg = renderFlowchart(source);
const nodes = new Map([...svg.matchAll(/data-diagram-node="([^"]+)"[^>]*><rect x="([^"]+)" y="([^"]+)" width="([^"]+)" height="([^"]+)"/g)]
  .map((match) => [match[1], match.slice(2).map(Number)]));
const centerX = (id) => nodes.get(id)[0] + nodes.get(id)[2] / 2;
const branchMidpoint = (centerX("V") + centerX("C")) / 2;
for (const id of ["W", "R", "H", "G"]) {
  if (Math.abs(centerX(id) - branchMidpoint) > 0.001) {
    throw new Error(`${id} should share the branch midpoint: ${centerX(id)} vs ${branchMidpoint}`);
  }
}
"""
        result = subprocess.run([node, "-e", probe, str(script_path)], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_frontend_diagram_fit_scales_and_centres_tall_content(self):
        import importlib.resources as resources

        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not available")
        script_path = resources.files("memory_trace").joinpath("static/app.js")
        probe = r"""
const fs = require("fs");
const src = fs.readFileSync(process.argv[1], "utf8");
function pick(name, nextName) {
  const start = src.indexOf(`function ${name}(`);
  const end = src.indexOf(`\nfunction ${nextName}`, start);
  if (start < 0 || end < 0) throw new Error(`missing ${name}`);
  return src.slice(start, end);
}
eval(pick("_diagramFitTransform", "initDiagramPanZoom"));
const fit = _diagramFitTransform(1115, 584, 1113, 2064);
if (!(fit.scale < 0.3 && fit.scale > 0.2)) throw new Error(`unexpected scale ${fit.scale}`);
if (Math.abs((1115 - 1113 * fit.scale) / 2 - fit.x) > 0.001) throw new Error(`x is not centred: ${fit.x}`);
if (Math.abs((584 - 2064 * fit.scale) / 2 - fit.y) > 0.001) throw new Error(`y is not centred: ${fit.y}`);
"""
        result = subprocess.run([node, "-e", probe, str(script_path)], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_frontend_brands_as_memory_trace(self):
        # Arc 2b microcopy: the UI self-identifies as Memory Trace, not the old
        # in-package "Lense" name.
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")
        index = resources.files("memory_trace").joinpath("static/index.html").read_text(encoding="utf-8")

        self.assertIn("Memory Trace", script)
        self.assertNotIn("Memory Lense", script)
        self.assertIn("<title>Memory Trace</title>", index)

    def test_frontend_uses_stable_delegated_interaction_handlers(self):
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")

        self.assertIn("function installDelegatedEvents()", script)
        self.assertIn('app.addEventListener("click"', script)
        self.assertIn('app.addEventListener("change"', script)
        self.assertIn('app.addEventListener("input"', script)
        self.assertIn("loadSeq", script)
        self.assertNotIn("function bindEvents()", script)
        self.assertIn('type="button"', script)

    def test_frontend_graph_defaults_to_all_entries_with_legend_and_layout_forces(self):
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")
        styles = resources.files("memory_trace").joinpath("static/styles.css").read_text(encoding="utf-8")

        self.assertIn('graphScope: "all"', script)
        self.assertIn("graphTransform", script)
        self.assertIn("graphHover", script)
        self.assertIn("hashString", script)
        # Force-directed layout (FR repulsion + weighted attraction + collision),
        # deterministic and cached - replaces the attraction-only hash scatter.
        self.assertIn("graphForceLayout", script)
        self.assertIn("repulsion", script)
        self.assertIn("graphLayoutCache", script)
        self.assertIn("graphTitle", script)
        self.assertIn("clearGraphHover", script)
        self.assertIn("graph-hit", script)
        self.assertIn("data-graph-label", script)
        self.assertNotIn("node.title.slice(0, 28)", script)
        self.assertIn('granularity: "entry"', script)
        self.assertNotIn('granularity: state.graphScope === "all" ? "all" : "entry"', script)
        self.assertIn('entry_id: !trail && state.graphScope === "neighborhood"', script)
        self.assertIn("agent: state.agent", script)
        self.assertIn("user: state.user", script)
        self.assertIn("topic: state.topic", script)
        self.assertIn("date_from: state.dateFrom", script)
        self.assertIn("date_to: state.dateTo", script)
        self.assertIn("data-graph-scope", script)
        self.assertIn("data-graph-canvas", script)
        self.assertIn("data-node-id", script)
        self.assertIn("const graphNode = event.target.closest(\"[data-node-id][data-chunk]\")", script)
        self.assertIn("openGraphChunk(graphNode.dataset.chunk)", script)
        self.assertIn("findGraphNodeFromPoint", script)
        self.assertIn("suppressGraphClick", script)
        self.assertIn('app.addEventListener("pointerup"', script)
        self.assertIn("state.graphHover = \"\";", script)
        self.assertIn("data-graph-reset", script)
        self.assertIn("data-graph-fit", script)
        self.assertIn("resetGraphView", script)
        self.assertIn("fitGraphView", script)
        self.assertIn("graph-layer", script)
        self.assertIn("graph-related", script)
        self.assertIn("graph-dim", script)
        self.assertIn("All entries", script)
        self.assertNotIn("All chunks", script)
        self.assertIn("Neighborhood", script)
        # De-crowding pass: the floating legend is gone; the edge-type toggle
        # chips carry their edge color directly (dual-encoded control).
        self.assertNotIn("graphLegend", script)
        self.assertIn("edge-chip", script)
        self.assertIn('style="border-color:${edgeColor(type)}"', script)
        self.assertIn("Size: ", script)
        self.assertIn("graph-stage", script)
        self.assertIn("node.connectivity", script)
        self.assertIn("node.importance_score", script)
        self.assertIn("data-graph-size", script)
        self.assertIn("agentColor(node.agent)", script)
        self.assertIn("layoutSimilarityLinks", script)
        self.assertIn("sharedTopicScore", script)
        self.assertIn("dateProximityScore", script)
        self.assertIn("pointerdown", script)
        self.assertIn("wheel", script)
        self.assertIn("mouseenter", script)
        self.assertIn("mouseout", script)
        self.assertIn(".graph-node.graph-dim", styles)
        self.assertIn(".graph-hit", styles)
        self.assertIn("pointer-events: all;", styles)
        self.assertIn("cursor: pointer;", styles)
        self.assertIn(".graph-edge.graph-related", styles)
        self.assertNotIn(".graph-legend", styles)
        self.assertIn(".graph-node:not(.graph-dim)", styles)
        self.assertIn("paint-order: stroke;", styles)
        self.assertIn("pointer-events: none;", styles)

    def test_trail_hides_related_and_evolves_connectors_until_selected(self):
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")

        self.assertIn('if (!touched) return "";', script)
        self.assertIn('if ((edge.type === "related" || edge.type === "evolves") && !touched) return [];', script)
        self.assertIn("evolves · on select", script)

    def test_frontend_preserves_center_scroll_when_selecting_entries(self):
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")

        self.assertIn("captureCenterScroll", script)
        self.assertIn("restoreCenterScroll", script)
        self.assertIn("const scrollState = captureCenterScroll();", script)
        self.assertIn("restoreCenterScroll(scrollState);", script)
        # Scroll preservation must cover every scrollable pane, not just the
        # center views - a missing selector is the "left pane resets on facet
        # click" bug class.
        self.assertIn('[".pane.left", ".pane.right", ".scroll", ".trail-scroll"]', script)

    def test_frontend_exposes_phase0_debug_hook(self):
        # Phase 0 golden fixtures and future React-parity harnesses call the
        # module-scoped Trail model through this read-only window hook.
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")

        self.assertIn("window.memoryTraceDebug = { trailModel, trailOrderedNodes };", script)

    def test_frontend_highlights_and_scrolls_to_matched_subsection(self):
        # Entry-level UI results plan (Arc 2a): a subsection match highlights and
        # scrolls inside the parent entry reader, never as a separate record.
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")
        styles = resources.files("memory_trace").joinpath("static/styles.css").read_text(encoding="utf-8")

        self.assertIn("function matchHintFor(", script)
        self.assertIn("function applyMatchHighlight(", script)
        self.assertIn("best_match_chunk_id", script)
        self.assertIn("matched_sections", script)
        self.assertIn('scrollIntoView({ block: "center" })', script)
        self.assertIn("match-highlight", script)
        self.assertIn("applyMatchHighlight();", script)  # wired into render()
        self.assertIn("Best match:", script)  # consistent microcopy
        self.assertIn(".markdown h4.match-highlight", styles)
        self.assertIn(".match-note", styles)

    def test_frontend_has_trail_view_with_distinct_supersedes_and_branch_edges(self):
        # Trail is a dedicated git-graph timeline renderer: lane-per-branch
        # (interval coloring), lifecycle arcs, recent window with load-older.
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")
        styles = resources.files("memory_trace").joinpath("static/styles.css").read_text(encoding="utf-8")

        self.assertIn('["trail", "Trail"]', script)
        # Trail is the primary surface: first tab and the default view.
        self.assertIn('[["trail", "Trail"], ["graph", "Graph"]', script)
        self.assertIn('view: storedView() || "trail"', script)
        self.assertIn('state.view === "trail"', script)
        self.assertIn('TRAIL_EDGE_TYPES = "branch,supersedes,evolves,related"', script)
        # Relationship lanes left of main (always dotted): replaces | evolves |
        # related - related innermost since its routes are pure branch hops.
        # Branch lanes right of main are the solid git branches.
        self.assertIn('TRAIL_REL_LANES = ["supersedes", "evolves", "related"]', script)
        self.assertIn("function trailView(", script)
        self.assertIn("function trailModel(", script)
        # Lane occupancy runs fork-to-merge (not just entry rows), so branches
        # converging on one merge point hold parallel lanes; shortest-lived
        # allocates first, putting the longest branch outermost.
        self.assertIn("laneIntervals", script)
        self.assertIn("const occupancy", script)
        self.assertIn("data-trail-more", script)  # bounded window, load older
        self.assertIn("trail-link", script)  # fork/merge connectors to main
        # Two-rule related model (user-finalised): routes draw only for
        # cross-branch pairs; same-branch context brackets the rows (full =
        # outbound citations, pastel = inbound mentions + second-order).
        self.assertIn("chainPrimary", script)
        self.assertIn("chainSecondary", script)
        self.assertNotIn("TRAIL_MAIN_GAP", script)
        self.assertIn("stripTitleStamp", script)
        # Distinct edge-type color semantics (supersedes never == related).
        self.assertIn("supersedes:", script)
        self.assertIn("branch:", script)
        self.assertIn("var(--edge-evolves)", script)
        self.assertIn("--edge-evolves:", styles)
        self.assertIn('const TRAIL_CONTINUITY_KINDS = ["rename", "migration", "removal"]', script)
        self.assertIn("trail-cont-zone", script)
        self.assertIn("trail-cont-event", script)
        self.assertIn("--trail-cont-rename:", styles)
        self.assertIn("--trail-cont-migration:", styles)
        self.assertIn("--trail-cont-removal:", styles)
        # Directed lifecycle edges: dashed replaces, dotted refines, arrowed.
        self.assertIn("trail-arrow-supersedes", script)
        self.assertIn("trail-arrow-evolves", script)
        self.assertIn('stroke-dasharray="6 4"', script)
        # Labels must agree with edge direction (source replaces target).
        # "replaced by" would invert the meaning of the arrow. The evolves edge
        # is labelled with its entry-field name, not a synonym.
        self.assertIn("replaces", script)
        self.assertIn("evolves", script)
        self.assertNotIn("refines", script)
        self.assertNotIn("replaced by", script)
        self.assertIn(".trail-rail", styles)
        self.assertIn(".trail-row", styles)

    def test_frontend_center_view_bounds_scroll_region(self):
        import importlib.resources as resources

        styles = resources.files("memory_trace").joinpath("static/styles.css").read_text(encoding="utf-8")

        self.assertIn(".center > section", styles)
        self.assertIn("grid-template-rows: 44px minmax(0, 1fr);", styles)
        self.assertIn("height: 100%;", styles)
        self.assertIn("overflow: hidden;", styles)

    def test_frontend_workspace_controls_keep_selection_independent(self):
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")

        self.assertIn('id="trace-navigation-pane"', script)
        self.assertIn('id="trace-workspace"', script)
        self.assertIn('id="trace-inspector"', script)
        self.assertIn('aria-controls="trace-navigation-pane"', script)
        self.assertIn('aria-controls="trace-inspector"', script)
        self.assertIn("function toggleLeftPane()", script)
        self.assertIn("function toggleInspector()", script)
        self.assertIn('event.key.toLowerCase() === "b"', script)
        self.assertIn('event.key.toLowerCase() === "i"', script)
        self.assertNotIn('if (state.rightCollapsed) {\n        state.rightCollapsed = false;', script)
        self.assertIn("A hidden Inspector remains hidden", script)

    def test_frontend_worktree_refresh_keeps_current_project_state_fresh(self):
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")

        self.assertIn("const prior = state.worktree;", script)
        self.assertIn("const retained = state.worktrees.find((w) => w.id === prior);", script)
        self.assertIn('fetch(withWorktree(path), { cache: "no-store" })', script)
        self.assertIn('w.is_primary ? " · current project" : " · worktree"', script)
        refresh_body = script[script.index("async function refreshData()"):script.index("async function openGraphChunk")]
        self.assertIn("await loadWorktrees();", refresh_body)

    def test_frontend_worktree_switch_recovers_from_a_failed_branch_load(self):
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")
        styles = resources.files("memory_trace").joinpath("static/styles.css").read_text(encoding="utf-8")

        switch_body = script[script.index("async function switchWorktree("):script.index("// The default upper date bound")]
        self.assertIn("const priorWorktree = state.worktree;", switch_body)
        self.assertIn("} catch (error) {", switch_body)
        self.assertIn("state.worktree = priorWorktree;", switch_body)
        self.assertIn("state.worktreeLoading = false;", switch_body)
        self.assertIn("state.worktreeError", switch_body)
        self.assertIn('class="worktree-error"', script)
        self.assertIn(".worktree-error", styles)

    def test_frontend_timeline_and_search_tabs_are_retired(self):
        # Timeline retired 2026-07-11: the Trail (git-graph timeline) is its
        # chronological successor. Search retired as a destination the same
        # day: it became a function over the Trail and Graph. The
        # /api/timeline endpoint intentionally remains server-side; only the
        # frontend surfaces are gone. Stored "timeline"/"search" view
        # preferences must migrate to Trail, not a dead tab.
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")
        styles = resources.files("memory_trace").joinpath("static/styles.css").read_text(encoding="utf-8")

        self.assertNotIn('["timeline", "Timeline"]', script)
        self.assertNotIn("timelineView", script)
        self.assertNotIn("/api/timeline", script)
        self.assertNotIn("timelineZoom", script)
        self.assertNotIn("timelineSelectedBucket", script)
        self.assertNotIn('["search", "Search"]', script)
        self.assertNotIn("function searchView(", script)
        self.assertNotIn("function resultList(", script)
        self.assertIn('stored === "timeline" || stored === "search" ? "trail" : stored', script)
        self.assertNotIn(".timeline-overview", styles)
        self.assertNotIn(".timeline-stream", styles)
        self.assertNotIn(".bucket", styles)

    def test_frontend_search_is_a_function_over_trail_and_graph(self):
        # Search-as-a-function contract (user decision 2026-07-11): the box is
        # always in the topbar, server-ranked results feed a ranked dropdown
        # (the roadmap's "ranked results drawer"), and the match set
        # highlights in place - Trail rows get a marker dot with misses
        # dimmed, Graph nodes dim the same way. Matches cycle in Trail order.
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")
        styles = resources.files("memory_trace").joinpath("static/styles.css").read_text(encoding="utf-8")

        self.assertIn("function refreshSearch(", script)
        self.assertIn("matchEntries", script)
        self.assertIn("function searchDropdown(", script)
        self.assertIn("data-search-jump", script)
        self.assertIn("function searchStatus(", script)
        self.assertIn("data-match-next", script)
        self.assertIn("data-match-prev", script)
        self.assertIn("data-search-clear", script)
        self.assertIn("function jumpToMatch(", script)
        self.assertIn("function entryIdFromQuery(", script)
        self.assertIn("function jumpToEntryIdQuery(", script)
        self.assertIn("if (await jumpToEntryIdQuery(value)) return;", script)
        self.assertIn("if (await jumpToEntryIdQuery(event.target.value)) return;", script)
        self.assertIn('No entry found for', script)
        self.assertIn("function ensureTrailVisible(", script)
        self.assertIn("applyTrailScroll();", script)  # wired into render()
        # In-place highlighting, never removal: the Trail keeps its structure.
        self.assertIn("search-match", script)
        self.assertIn("search-miss", script)
        self.assertIn("trail-match-dot", script)
        self.assertIn(".trail-row.search-miss", styles)
        self.assertIn(".trail-match-dot", styles)
        self.assertIn(".search-dropdown", styles)
        # Regression (found 2026-07-11 while building the Playwright recording
        # harness): render()'s caret-preservation refocus of #query re-fired
        # the box's own "refocus reopens the dropdown" listener, so
        # jumpToMatch/Escape's close never stuck while the box kept focus.
        # restoringFocus distinguishes the internal restore from a genuine
        # user refocus so a deliberate close survives its own re-render.
        self.assertIn("let restoringFocus = false;", script)
        self.assertIn("restoringFocus = true;\n  el.focus();\n  restoringFocus = false;", script)
        self.assertIn("if (restoringFocus) return;", script)
        # Ranked text typing must never select the first result (the old
        # focus-steal bug class); exact entry IDs have a separate identity path.
        self.assertNotIn("await selectChunk(state.results[0]", script)


if __name__ == "__main__":
    unittest.main()
