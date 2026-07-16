"""Serve-time asset versioning (P6) + static-root override (P7).

P6 deletes the manual `?v=` cache-bust convention: index.html's asset tags are
rewritten per request with a content hash of app.js + styles.css, so a changed
asset can never hide behind a stale browser cache and there is no tag bump to
forget. P7 lets one running server serve another checkout's UI assets
(`--static-root` / MEMORY_TRACE_STATIC_ROOT), replacing the
copy-into-primary-then-restore verification dance.
"""

import hashlib
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


def _static_override(tmp: Path, *, app_js: str = "console.log('override');") -> Path:
    static = tmp / "static-override"
    static.mkdir(parents=True, exist_ok=True)
    (static / "index.html").write_text(
        '<link rel="stylesheet" href="/assets/styles.css?v=manual-tag">\n'
        '<script src="/assets/app.js?v=manual-tag" defer></script>\n',
        encoding="utf-8",
    )
    (static / "app.js").write_text(app_js, encoding="utf-8")
    (static / "styles.css").write_text("body{}", encoding="utf-8")
    return static


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

    def test_index_rewrites_version_tags_with_content_hash(self):
        static = _static_override(self.tmp)
        client = self._client(static_root=static)

        html = client.get("/").text

        digest = hashlib.sha256()
        digest.update((static / "app.js").read_bytes())
        digest.update((static / "styles.css").read_bytes())
        expected = digest.hexdigest()[:10]
        self.assertIn(f"app.js?v={expected}", html)
        self.assertIn(f"styles.css?v={expected}", html)
        self.assertNotIn("manual-tag", html)

    def test_version_changes_when_an_asset_changes_without_restart(self):
        static = _static_override(self.tmp)
        client = self._client(static_root=static)
        before = client.get("/").text

        (static / "app.js").write_text("console.log('edited');", encoding="utf-8")
        after = client.get("/").text

        self.assertNotEqual(before, after)

    def test_static_root_serves_override_assets(self):
        static = _static_override(self.tmp, app_js="console.log('worktree build');")
        client = self._client(static_root=static)

        self.assertEqual(client.get("/assets/app.js").text, "console.log('worktree build');")

    def test_checkout_root_layout_is_resolved(self):
        checkout = self.tmp / "worktree-checkout"
        nested = checkout / "memory-trace" / "memory_trace" / "static"
        nested.mkdir(parents=True)
        (nested / "index.html").write_text("<title>x</title>", encoding="utf-8")

        self.assertEqual(_resolve_static_root(checkout), nested)

    def test_bad_static_root_raises_instead_of_silent_fallback(self):
        with self.assertRaises(RuntimeError):
            _resolve_static_root(self.tmp / "nowhere")

    def test_default_packaged_assets_still_serve_with_hash(self):
        client = self._client()

        html = client.get("/").text
        self.assertRegex(html, r"app\.js\?v=[0-9a-f]{10}")
        self.assertEqual(client.get("/assets/app.js").status_code, 200)

    def test_renderer_benchmark_is_self_contained_and_served_from_package_assets(self):
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
        self.assertIn("aria-pressed", script.text)
        self.assertIn("shared node selection", script.text)
        self.assertIn("vis-network", script.text)
        self.assertIn("Cytoscape.js", script.text)
        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn("renderer-grid", stylesheet.text)
        self.assertEqual(client.get("/assets/benchmark/unlisted.js").status_code, 404)

    def test_next_react_shell_and_hashed_assets_are_served_separately(self):
        client = self._client()

        html = client.get("/next")
        script = re.search(r'src="/assets/react/([^\"]+\.js)"', html.text)

        self.assertEqual(html.status_code, 200)
        self.assertIn('<div id="root"></div>', html.text)
        self.assertIsNotNone(script)
        self.assertEqual(client.get(f"/assets/react/{script.group(1)}").status_code, 200)
        self.assertEqual(client.get("/assets/react/../../app.js").status_code, 404)

    def test_next_react_bundle_includes_search_and_keyboard_graph_controls(self):
        client = self._client()
        html = client.get("/next").text
        script = re.search(r'src="/assets/react/([^\"]+\.js)"', html)

        self.assertIsNotNone(script)
        bundle = client.get(f"/assets/react/{script.group(1)}").text
        self.assertIn("Search memory or entry ID", bundle)
        graph_bundle = next((Path(__file__).parents[1] / "memory_trace" / "static" / "react" / "assets").glob("GraphWorkspace-*.js"))
        graph_source = graph_bundle.read_text(encoding="utf-8")
        self.assertIn("Fit graph", graph_source)
        self.assertIn("ArrowLeft ArrowRight", graph_source)


if __name__ == "__main__":
    unittest.main()
