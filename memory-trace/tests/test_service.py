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
    replaces=None,
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
    if replaces:
        lines.append("replaces:")
        lines.extend(f"  - {ref}" for ref in replaces)
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

    def test_trail_view_renders_replaces_edge_and_branch_axis(self):
        # Trail view (Arc 2c): a later decision replaces an earlier one on the
        # same branch. replaces is a directed status edge; branch is a
        # time-ordered lineage axis. Both are additive to the same graph engine.
        self.write_session(
            "2026-06-10.md",
            "\n".join(
                [
                    _entry("2026-06-10 09:00 - First take", "mse_old", "First.", branch="feature/x"),
                    _entry("2026-06-10 12:00 - Revised take", "mse_revised", "Revised.",
                           branch="feature/x", replaces=["mse_old"]),
                ]
            ),
        )
        service = self.service()

        graph = service.graph(edge_types=("branch", "replaces", "related"))
        by_type = {}
        for edge in graph["edges"]:
            by_type.setdefault(edge["type"], []).append((edge["source"], edge["target"]))
        # Directed supersession: the edge runs source -> target where source
        # replaces (replaces) target. mse_revised (newer, carries replaces:)
        # points at mse_old (older) - and never the reverse, which would tell a
        # reader the stale decision is the current one.
        self.assertIn(("mse_revised", "mse_old"), by_type.get("replaces", []))
        self.assertNotIn(("mse_old", "mse_revised"), by_type.get("replaces", []))
        # Intra-branch lineage runs in time order along the shared branch.
        self.assertIn(("mse_old", "mse_revised"), by_type.get("branch", []))
        # Asking for only related must not surface the trail edge types.
        related_only = service.graph(edge_types=("related",))
        self.assertNotIn("replaces", {edge["type"] for edge in related_only["edges"]})
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

    def test_graph_overview_slice_is_a_chronological_spine_plus_what_it_references(self):
        # The overview grows along the SAME axis the Trail pages along, so
        # "Show more" walks back through time instead of moving around a
        # connectivity ranking. An old entry enters only when the spine
        # references it - which is what makes the Graph show relationships the
        # purely chronological Trail cannot.
        self.write_session(
            "2026-05-01.md",
            "\n".join(
                _entry(
                    f"2026-05-01 0{index}:00 - Ancient note {index}",
                    f"mse_old{index}",
                    "Old, unreferenced.",
                    topics=[f"iso{index}"],
                )
                for index in range(1, 5)
            ),
        )
        self.write_session(
            "2026-05-02.md",
            _entry("2026-05-02 09:00 - Ancient but referenced", "mse_oldlinked", "Referenced later.", topics=["c"]),
        )
        self.write_session(
            "2026-06-05.md",
            "\n".join(
                _entry(
                    f"2026-06-05 1{index}:00 - Recent step {index}",
                    f"mse_recent{index}",
                    "Recent work.",
                    related=["mse_oldlinked"] if index == 0 else [f"mse_recent{index - 1}"],
                    topics=["cluster"],
                )
                for index in range(3)
            ),
        )
        service = self.service()
        edge_types = ("related", "replaces", "evolves", "topic")

        overview = service.graph(edge_types=edge_types, limit=3)

        node_ids = {node["id"] for node in overview["nodes"]}
        # The three newest entries are the spine...
        self.assertTrue({"mse_recent0", "mse_recent1", "mse_recent2"}.issubset(node_ids))
        # ...the old entry the spine REFERENCES is pulled in despite its date...
        self.assertIn("mse_oldlinked", node_ids)
        # ...and old entries nothing references stay out, even though they would
        # have been first under plain corpus order.
        self.assertFalse({f"mse_old{index}" for index in range(1, 5)} & node_ids)

    def test_local_scope_and_contextual_ontology_ignore_display_edge_types(self):
        # The topic edge joins the focus to a third entry with a distinct
        # Activity. It is display-only: choosing the topic chip must not pull
        # that entry into Local scope or make its Activity available.
        memory = self.cwd / ".memory-seed"
        (memory / "topics.yaml").write_text(
            """schema_version: 2
topics:
  - slug: area-one
    axis: area
  - slug: area-two
    axis: area
  - slug: activity-x
    axis: activity
  - slug: activity-y
    axis: activity
""",
            encoding="utf-8",
        )
        self.write_session(
            "2026-07-01.md",
            "\n".join(
                [
                    _entry("2026-07-01 09:00 - Local focus", "mse_scope_focus", "Focus node."),
                    _entry(
                        "2026-07-01 10:00 - Lifecycle neighbour",
                        "mse_scope_lifecycle",
                        "Lifecycle node.",
                        related=["mse_scope_focus"],
                    ),
                    _entry("2026-07-01 11:00 - Topic-only neighbour", "mse_scope_topic", "Topic node."),
                ]
            ),
        )
        sidecar = memory / "sessions" / "topics" / "2026-07" / "2026-07-01.md"
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar.write_text(
            """---
tags:
  - session-log-topics
topic_date: 2026-07-01
---

## 2026-07-01 09:00 - Local focus

```yaml
entry_id: mse_scope_focus
topics:
  area:
    - area-one:d1
  activity:
    - activity-x:d1
```

## 2026-07-01 10:00 - Lifecycle neighbour

```yaml
entry_id: mse_scope_lifecycle
topics:
  area:
    - area-one:d1
  activity:
    - activity-x:d1
```

## 2026-07-01 11:00 - Topic-only neighbour

```yaml
entry_id: mse_scope_topic
topics:
  area:
    - area-one:d1
  activity:
    - activity-y:d1
```
""",
            encoding="utf-8",
        )
        service = self.service()

        hidden = service.graph(entry_id="mse_scope_focus", edge_types=("related",), limit=100)
        shown = service.graph(entry_id="mse_scope_focus", edge_types=("related", "topic"), limit=100)

        expected_ids = {"mse_scope_focus", "mse_scope_lifecycle"}
        self.assertEqual({node["id"] for node in hidden["nodes"]}, expected_ids)
        self.assertEqual({node["id"] for node in shown["nodes"]}, expected_ids)
        self.assertEqual(hidden["ontology"], shown["ontology"])
        self.assertNotIn("activity-y", json.dumps(shown["ontology"]))
        self.assertEqual({edge["type"] for edge in hidden["edges"]}, {"related"})
        self.assertEqual({edge["type"] for edge in shown["edges"]}, {"related", "topic"})

    def test_graph_overview_slice_prefers_connected_subgraph(self):
        # Regression: the all-dates overview (no entry_id, no date filter) used
        # to truncate nodes in corpus order, so a limit smaller than the corpus
        # kept the oldest - edgeless - entries and rendered a disconnected map.
        # Still true under the chronological spine, by a different route: the
        # newest entries are the linked ones, so newest-first is connected.
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
        edge_types = ("related", "replaces", "evolves", "topic")

        overview = service.graph(edge_types=edge_types, limit=6)
        repeat = service.graph(edge_types=edge_types, limit=6)

        node_ids = [node["id"] for node in overview["nodes"]]
        # `limit` sizes the SPINE, not the payload: depth-1 expansion is additive
        # on top of it, so the node count is at least the limit and may exceed it
        # by whatever the spine references.
        self.assertGreaterEqual(len(node_ids), 6)
        # The slice keeps the connected cluster instead of the oldest rows, so
        # the intra-slice edge set is non-trivial on a corpus that has edges.
        self.assertGreaterEqual(len(overview["edges"]), 4)
        self.assertTrue({f"mse_cluster{index}" for index in range(5)}.issubset(set(node_ids)))
        # Deterministic: the same request always selects the same slice.
        self.assertEqual(node_ids, [node["id"] for node in repeat["nodes"]])
        self.assertEqual(overview["edges"], repeat["edges"])

        from memory_trace.graph_projection import project_trace_graph

        projection = project_trace_graph(overview)
        self.assertEqual(len(projection["nodes"]), len(overview["nodes"]))
        self.assertEqual(len(projection["edges"]), len(overview["edges"]))

    def test_pinned_ids_survive_the_limit_and_bring_their_lifecycle_neighbours(self):
        # The Trail's loaded window is pinned into the Graph: an entry the user
        # can already see in one view must exist in the other. `limit` ranks
        # what to VOLUNTEER; it was never a cap on what may be shown.
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
        edge_types = ("related", "replaces", "evolves", "topic")

        # Baseline: the ranked slice excludes the edgeless notes entirely.
        baseline = service.graph(edge_types=edge_types, limit=6)
        baseline_ids = {node["id"] for node in baseline["nodes"]}
        self.assertNotIn("mse_iso3", baseline_ids)

        pinned = service.graph(edge_types=edge_types, limit=6, pinned_ids=["mse_iso3"])
        pinned_ids = {node["id"] for node in pinned["nodes"]}
        self.assertIn("mse_iso3", pinned_ids)
        # Additive, not a swap: pinning displaces nothing the ranking chose.
        self.assertTrue(baseline_ids.issubset(pinned_ids))
        self.assertEqual(len(pinned["nodes"]), len(baseline["nodes"]) + 1)

        # A pinned entry arrives with its most relevant relationships rather
        # than as a lone dot: depth-1 over the rendered lifecycle edges.
        tight = service.graph(edge_types=edge_types, limit=1, pinned_ids=["mse_cluster4"])
        tight_ids = {node["id"] for node in tight["nodes"]}
        self.assertIn("mse_cluster4", tight_ids)
        self.assertIn("mse_cluster3", tight_ids)
        self.assertTrue(
            any(
                {edge["source"], edge["target"]} == {"mse_cluster4", "mse_cluster3"}
                for edge in tight["edges"]
            ),
            "the edge that justifies pulling the neighbour in must itself render",
        )

        # An unknown id is ignored, not an error, and pinning nothing is the
        # untouched ranked slice.
        self.assertEqual(
            {node["id"] for node in service.graph(edge_types=edge_types, limit=6, pinned_ids=["mse_nope"])["nodes"]},
            baseline_ids,
        )
        self.assertEqual(
            {node["id"] for node in service.graph(edge_types=edge_types, limit=6, pinned_ids=[])["nodes"]},
            baseline_ids,
        )

    def test_pinned_expansion_uses_stable_lifecycle_scope_not_display_edge_types(self):
        # Pinned entries legitimately expand the logical response, but the
        # lifecycle neighbour they add is independent of the display chips.
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

        with_related = service.graph(edge_types=("related",), limit=1, pinned_ids=["mse_cluster4"])
        without_related = service.graph(edge_types=("replaces", "evolves"), limit=1, pinned_ids=["mse_cluster4"])

        self.assertEqual(
            {node["id"] for node in without_related["nodes"]},
            {node["id"] for node in with_related["nodes"]},
        )
        self.assertIn("mse_cluster4", {node["id"] for node in without_related["nodes"]})
        self.assertIn("mse_cluster3", {node["id"] for node in without_related["nodes"]})
        self.assertEqual({edge["type"] for edge in without_related["edges"]}, set())
        self.assertEqual({edge["type"] for edge in with_related["edges"]}, {"related"})

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


class MemoryTraceCliAndPackageTests(unittest.TestCase):
    def test_run_server_opens_the_supported_ui(self):
        app = object()
        uvicorn = mock.Mock()
        args = argparse.Namespace(
            cwd=".",
            host="127.0.0.1",
            port=8765,
            no_open=False,
            rebuild_cache=False,
            static_root=None,
        )

        with (
            mock.patch.dict(sys.modules, {"uvicorn": uvicorn}),
            mock.patch("memory_trace.service.create_app", return_value=app) as create,
            mock.patch("memory_trace.service.webbrowser.open") as open_browser,
        ):
            code = run_server(args)

        self.assertEqual(code, 0)
        open_browser.assert_called_once_with("http://127.0.0.1:8765")
        create.assert_called_once_with(
            ".",
            rebuild_cache=False,
            static_root=None,
            allow_external_project_access=True,
        )
        uvicorn.run.assert_called_once_with(app, host="127.0.0.1", port=8765, log_level="info")

    def test_run_server_disables_external_project_access_for_non_loopback_host(self):
        app = object()
        uvicorn = mock.Mock()
        args = argparse.Namespace(
            cwd=".",
            host="0.0.0.0",
            port=8765,
            no_open=True,
            rebuild_cache=False,
            static_root=None,
        )

        with (
            mock.patch.dict(sys.modules, {"uvicorn": uvicorn}),
            mock.patch("memory_trace.service.create_app", return_value=app) as create,
        ):
            code = run_server(args)

        self.assertEqual(code, 0)
        create.assert_called_once_with(
            ".",
            rebuild_cache=False,
            static_root=None,
            allow_external_project_access=False,
        )

    def test_source_checkout_launcher_opens_the_supported_ui(self):
        launcher = Path(__file__).resolve().parents[2] / "scripts" / "launch-memory-trace.ps1"
        script = launcher.read_text(encoding="utf-8")

        self.assertNotIn("--open-both", script)
        self.assertNotIn('"$baseUrl/next"', script)
        self.assertIn('"$baseUrl/"', script)
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
        self.assertNotIn("index.html", data["files"])
        self.assertNotIn("app.js", data["files"])
        self.assertNotIn("styles.css", data["files"])
        self.assertIn("benchmark.html", data["files"])
        self.assertIn("renderer-benchmark.js", data["files"])
        self.assertIn("react/index.html", data["files"])



if __name__ == "__main__":
    unittest.main()
