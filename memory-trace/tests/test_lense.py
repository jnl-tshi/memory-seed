import io
import json
import os
import subprocess
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from urllib.parse import quote
from unittest import mock

from memory_trace.cli import main
from memory_trace.lense import LenseCache, LenseService, create_app, missing_optional_dependency_hint


def _entry(title, entry_id, body, *, agent="codex", related=None, branch=None, supersedes=None):
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
    if related:
        lines.append("related_entries:")
        lines.extend(f"  - {ref}" for ref in related)
    if supersedes:
        lines.append("supersedes:")
        lines.extend(f"  - {ref}" for ref in supersedes)
    lines += ["```", "", body, ""]
    return "\n".join(lines)


class LenseServiceTests(unittest.TestCase):
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
        cache = LenseCache(self.cwd, cache_root=self.cache_root)
        cache.rebuild()
        return LenseService(cache)

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
        cache = LenseCache(self.cwd, cache_root=self.cache_root)
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

    def test_chunk_api_accepts_encoded_path_chunk_ids(self):
        self.write_session(
            "2026-06-05.md",
            "## 2026-06-05 10:00 - Heading without metadata\n\nPath-style chunk id body.\n",
        )
        cache = LenseCache(self.cwd, cache_root=self.cache_root)
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


class LenseCliTests(unittest.TestCase):
    def test_missing_optional_dependency_hint_is_explicit(self):
        self.assertEqual(
            missing_optional_dependency_hint(),
            'Install with: pip install memory-trace',
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
        self.assertIn('Install with: pip install memory-trace', stderr.getvalue())

    def test_static_manifest_is_packaged(self):
        import importlib.resources as resources

        manifest = resources.files("memory_trace").joinpath("static/manifest.json")
        data = json.loads(manifest.read_text(encoding="utf-8"))

        self.assertEqual(data["name"], "Memory Trace")
        self.assertIn("index.html", data["files"])

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
  pick("_diagramNode", "renderFlowchart"),
  pick("renderFlowchart", "renderSequenceDiagram"),
  pick("_diagramArrowDefs", "markdown"),
  pick("esc", "escAttr"),
].join("\n"));
const svg = renderFlowchart("flowchart LR\n  A[Alpha] --> B[Beta]");
const rects = [...svg.matchAll(/<rect x="([^"]+)" y="([^"]+)" width="([^"]+)" height="([^"]+)"/g)]
  .map((match) => match.slice(1).map(Number));
const line = svg.match(/<line x1="([^"]+)" y1="([^"]+)" x2="([^"]+)" y2="([^"]+)"/);
if (rects.length !== 2 || !line) throw new Error(svg);
const [a, b] = rects;
const coords = line.slice(1).map(Number);
const horizontalOverlap = Math.max(0, Math.min(a[0] + a[2], b[0] + b[2]) - Math.max(a[0], b[0]));
if (horizontalOverlap > 0) {
  throw new Error(`LR nodes overlap by ${horizontalOverlap}px`);
}
const expected = [a[0] + a[2], a[1] + a[3] / 2, b[0], b[1] + b[3] / 2];
if (coords.some((value, index) => value !== expected[index])) {
  throw new Error(`LR edge ${coords.join(",")} should be ${expected.join(",")}`);
}
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
        self.assertIn("degreePull", script)
        self.assertIn("graphTitle", script)
        self.assertIn("clearGraphHover", script)
        self.assertIn("graph-hit", script)
        self.assertIn("data-graph-label", script)
        self.assertNotIn("node.title.slice(0, 28)", script)
        self.assertIn('granularity: "entry"', script)
        self.assertNotIn('granularity: state.graphScope === "all" ? "all" : "entry"', script)
        self.assertIn('entry_id: state.graphScope === "neighborhood"', script)
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
        self.assertIn("graphLegend", script)
        self.assertIn("graphLegendLabel", script)
        self.assertIn("Size: ", script)
        self.assertIn("Near: links/topics/dates", script)
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
        self.assertIn(".graph-legend", styles)
        self.assertIn("position: absolute;", styles)
        self.assertIn("bottom: 12px;", styles)
        self.assertIn(".legend-swatch", styles)
        self.assertIn(".graph-node:not(.graph-dim)", styles)
        self.assertIn("paint-order: stroke;", styles)
        self.assertIn("pointer-events: none;", styles)

    def test_frontend_preserves_center_scroll_when_selecting_entries(self):
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")

        self.assertIn("captureCenterScroll", script)
        self.assertIn("restoreCenterScroll", script)
        self.assertIn("const scrollState = captureCenterScroll();", script)
        self.assertIn("restoreCenterScroll(scrollState);", script)
        self.assertIn('[".scroll", ".timeline-stream", ".overview-scroll"]', script)

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
        # Trail view (Arc 2c): a dedicated tab rendering the branch + supersedes
        # axes with distinct color semantics and a directed supersession edge.
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")

        self.assertIn('["trail", "Trail"]', script)
        self.assertIn('state.view === "trail"', script)
        self.assertIn('TRAIL_EDGE_TYPES = "branch,supersedes,related"', script)
        # Distinct edge-type color semantics (supersedes never == related).
        self.assertIn("supersedes:", script)
        self.assertIn("branch:", script)
        # Directed, dashed supersession edge with an arrow marker.
        self.assertIn("arrow-supersedes", script)
        self.assertIn('stroke-dasharray="6 4"', script)
        # Legend label must agree with edge direction (source replaces target).
        # "replaced by" would invert the meaning of the arrow.
        self.assertIn('["supersedes", "replaces"]', script)
        self.assertNotIn("replaced by", script)

    def test_frontend_center_view_bounds_scroll_region(self):
        import importlib.resources as resources

        styles = resources.files("memory_trace").joinpath("static/styles.css").read_text(encoding="utf-8")

        self.assertIn(".center > section", styles)
        self.assertIn("grid-template-rows: 44px minmax(0, 1fr);", styles)
        self.assertIn("height: 100%;", styles)
        self.assertIn("overflow: hidden;", styles)

    def test_timeline_overview_can_scroll_horizontally_at_all_zooms(self):
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")
        styles = resources.files("memory_trace").joinpath("static/styles.css").read_text(encoding="utf-8")

        self.assertIn("overview-scroll", script)
        self.assertIn("--bucket-count", script)
        self.assertIn("--bucket-min", script)
        self.assertIn("data-timeline-zoom", script)
        self.assertIn("scrollTimelineToBucket", script)
        self.assertIn("findTimelineBucketTarget", script)
        self.assertIn("timelineItemDatetime", script)
        self.assertIn("data-entry-datetime", script)
        # Timeline scrolls via its own bucket mechanism (scrollTimelineToBucket,
        # asserted above). scrollIntoView now exists in app.js but only for the
        # reader's matched-subsection jump - it is never wired to the timeline.
        self.assertIn("scrollTimelineToBucket", script)
        self.assertIn(".overview-scroll", styles)
        self.assertIn("overflow-x: scroll;", styles)
        self.assertIn("grid-template-columns: repeat(var(--bucket-count, 1), minmax(var(--bucket-min, 12px), 1fr));", styles)
        self.assertIn("calc(var(--bucket-count, 1) * var(--bucket-min, 12px))", styles)
        self.assertIn("width: max(100%, calc(var(--bucket-count, 1) * var(--bucket-min, 12px)));", styles)
        self.assertIn("background: transparent;", styles)
        self.assertIn("const bucketMin = 44;", script)
        self.assertNotIn('"3h": 30', script)
        self.assertIn("bucket-label", script)
        self.assertIn(".bucket-label", styles)
        self.assertIn("bottom: 7px;", styles)
        self.assertIn("top: 5px;", styles)
        self.assertIn("max-width: calc(100% - 6px);", styles)

    def test_timeline_overview_stays_visible_above_stream_and_receives_filters(self):
        import importlib.resources as resources

        script = resources.files("memory_trace").joinpath("static/app.js").read_text(encoding="utf-8")
        styles = resources.files("memory_trace").joinpath("static/styles.css").read_text(encoding="utf-8")

        self.assertIn('agent: state.agent', script)
        self.assertIn('user: state.user', script)
        self.assertIn('topic: state.topic', script)
        self.assertIn("timelineHideEmpty", script)
        self.assertIn("include_empty", script)
        self.assertIn("limit: 500", script)
        self.assertIn("data-timeline-empty", script)
        self.assertIn("timelineSelectedBucket", script)
        self.assertIn("data-bucket-date", script)
        self.assertIn("data-bucket-start", script)
        self.assertIn("data-bucket-end", script)
        self.assertIn("selectTimelineBucket", script)
        self.assertIn("markSelectedTimelineBucket", script)
        self.assertIn('target.dataset.bucketStart', script)
        self.assertNotIn('target.dataset.bucketStart) {\n      await updateFilter("dateFrom"', script)
        self.assertNotIn('target.dataset.bucketStart) {\n      await updateFilter("dateTo"', script)
        self.assertIn("timeline-overview", script)
        self.assertIn("timeline-stream", script)
        self.assertIn(".timeline-overview", styles)
        self.assertIn("position: sticky;", styles)
        self.assertIn("top: 44px;", styles)
        self.assertIn(".bucket.selected", styles)
        self.assertIn("grid-template-rows: 44px auto minmax(0, 1fr);", styles)
        self.assertIn("overflow-y: auto;", styles)


if __name__ == "__main__":
    unittest.main()
