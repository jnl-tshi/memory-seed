"""Packaged React serving, static-root overrides, and benchmark assets."""

import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from memory_trace.service import _resolve_static_root, create_app


def _corpus(tmp: Path) -> Path:
    sessions = tmp / ".memory-seed" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / "2026-06-01.md").write_text(
        "---\ntags:\n  - session-log\n---\n\n"
        "## 2026-06-01 09:00 - Only\n\n```yaml\nentry_id: mse_aaaaaaaaaaaaaaaa\n```\n\nBody.\n",
        encoding="utf-8",
    )
    return tmp


def _react_override(tmp: Path, *, script: str = "console.log('override');") -> Path:
    build = tmp / "react-build"
    assets = build / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (build / "index.html").write_text(
        '<div id="root"></div>\n<script type="module" src="/assets/react/assets/app.js"></script>\n',
        encoding="utf-8",
    )
    (assets / "app.js").write_text(script, encoding="utf-8")
    return build


class StaticServingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mseed-static-"))
        self.cache_root = Path(tempfile.mkdtemp(prefix="mseed-static-cache-"))
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(self.cache_root, ignore_errors=True))
        self.cwd = _corpus(self.tmp)

    def _client(self, **kwargs):
        from fastapi.testclient import TestClient

        with mock.patch.dict(os.environ, {"MEMORY_SEED_LENSE_CACHE_ROOT": str(self.cache_root)}):
            return TestClient(create_app(self.cwd, rebuild_cache=True, **kwargs))

    def test_root_serves_the_packaged_react_shell(self):
        client = self._client()
        html = client.get("/")
        script = re.search(r'src="/assets/react/([^\"]+\.js)"', html.text)

        self.assertEqual(html.status_code, 200)
        self.assertIn('<div id="root"></div>', html.text)
        self.assertIsNotNone(script)
        self.assertEqual(client.get(f"/assets/react/{script.group(1)}").status_code, 200)

    def test_next_redirects_existing_bookmarks_to_the_supported_root(self):
        client = self._client()

        response = client.get("/next", follow_redirects=False)

        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/")

    def test_static_root_serves_a_direct_react_build(self):
        build = _react_override(self.tmp, script="console.log('worktree build');")
        client = self._client(static_root=build)

        self.assertIn('<div id="root"></div>', client.get("/").text)
        self.assertEqual(client.get("/assets/react/assets/app.js").text, "console.log('worktree build');")

    def test_checkout_root_layout_is_resolved(self):
        checkout = self.tmp / "worktree-checkout"
        build = checkout / "memory-trace" / "memory_trace" / "static" / "react"
        build.mkdir(parents=True)
        (build / "index.html").write_text("<title>x</title>", encoding="utf-8")

        self.assertEqual(_resolve_static_root(checkout), build)

    def test_package_static_root_layout_is_resolved(self):
        static = self.tmp / "static"
        build = static / "react"
        build.mkdir(parents=True)
        (build / "index.html").write_text("<title>x</title>", encoding="utf-8")

        self.assertEqual(_resolve_static_root(static), build)

    def test_bad_static_root_raises_instead_of_silent_fallback(self):
        with self.assertRaises(RuntimeError):
            _resolve_static_root(self.tmp / "nowhere")

    def test_renderer_benchmark_remains_separate_and_self_contained(self):
        client = self._client()

        html = client.get("/benchmarks/renderer")
        script = client.get("/assets/benchmark/renderer-benchmark.js")
        stylesheet = client.get("/assets/benchmark/renderer-benchmark.css")

        self.assertEqual(html.status_code, 200)
        self.assertRegex(html.text, r"renderer-benchmark\.js\?v=[0-9a-f]{10}")
        self.assertIn('id="benchmark-app"', html.text)
        self.assertEqual(script.status_code, 200)
        self.assertGreater(len(script.content), 100_000)
        self.assertIn("Visible nodes", script.text)
        self.assertIn("vis-network", script.text)
        self.assertIn("Cytoscape.js", script.text)
        self.assertEqual(stylesheet.status_code, 200)
        self.assertEqual(client.get("/assets/benchmark/unlisted.js").status_code, 404)

    def test_react_asset_route_rejects_path_traversal(self):
        client = self._client()

        self.assertEqual(client.get("/assets/react/../../manifest.json").status_code, 404)

    def test_packaged_bundle_includes_search_and_keyboard_graph_controls(self):
        client = self._client()
        html = client.get("/").text
        script = re.search(r'src="/assets/react/([^\"]+\.js)"', html)

        self.assertIsNotNone(script)
        bundle = client.get(f"/assets/react/{script.group(1)}").text
        self.assertIn("Search memory or entry ID", bundle)
        graph_bundle = next(
            (Path(__file__).parents[1] / "memory_trace" / "static" / "react" / "assets").glob(
                "GraphWorkspace-*.js"
            )
        )
        graph_source = graph_bundle.read_text(encoding="utf-8")
        self.assertIn("Fit graph", graph_source)
        self.assertIn("ArrowLeft ArrowRight", graph_source)


if __name__ == "__main__":
    unittest.main()
