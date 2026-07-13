"""Link sidecars: late-authored lifecycle edges (Phase 1, read path).

A link sidecar records `supersedes`/`evolves`/`related_entries` edges authored
*after* an entry, without reopening the append-only entry (mirrors the
decision-diagram sidecar mechanism). These tests pin the read path end to end:
the core file-discoverer, the retrieval parser, and the lense merge that folds
sidecar edges into `graph()` so the Trail draws the lines. This is the walking
skeleton - if `graph()` emits a sidecar-declared `supersedes` edge, the whole
payoff (TRAIL_EDGE_TYPES already requests it) is proven.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from memory_seed.core import iter_link_sidecar_documents
from memory_seed.retrieval import entry_link_sidecars
from memory_trace.lense import create_app

# entry_id shape is mse_ + 16 Crockford-base32 chars (memory_seed.core
# _V2_ENTRY_ID_RE); the ref-extraction regex the reader shares with links check
# rejects anything else, so tests must use real-shaped ids.
OLD = "mse_" + "a" * 16
NEW = "mse_" + "b" * 16
THIRD = "mse_" + "c" * 16


def _entry(dt, entry_id, title, *, branch=None):
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
    if branch:
        lines.append(f"branch: {branch}")
    lines += ["```", "", "Body text.", ""]
    return "\n".join(lines)


def _link_block(dt, entry_id, title, **edges):
    lines = [f"## {dt} - {title}", "", "```yaml", f"entry_id: {entry_id}"]
    for key, refs in edges.items():
        lines.append(f"{key}:")
        lines.extend(f"  - {ref}" for ref in refs)
    lines += ["```", ""]
    return "\n".join(lines)


class LinkSidecarReadPathTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-linksidecar-"))
        self.cache_root = Path(tempfile.mkdtemp(prefix="mseed-linksidecar-cache-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(self.cache_root, ignore_errors=True))
        self.sessions = self.cwd / ".memory-seed" / "sessions"
        self.sessions.mkdir(parents=True, exist_ok=True)
        (self.sessions / "2026-06-01.md").write_text(
            "---\ntags:\n  - session-log\n---\n\n"
            + _entry("2026-06-01 09:00", OLD, "Old palette", branch="feature-x")
            + _entry("2026-06-01 10:00", NEW, "New palette", branch="feature-x")
            + _entry("2026-06-01 11:00", THIRD, "Third", branch="feature-x"),
            encoding="utf-8",
        )

    def _write_sidecar(self, body, *, month="2026-06", day="2026-06-01"):
        links_dir = self.sessions / "links" / month
        links_dir.mkdir(parents=True, exist_ok=True)
        (links_dir / f"{day}.md").write_text(body, encoding="utf-8")

    def _app(self):
        with mock.patch.dict(os.environ, {"MEMORY_SEED_LENSE_CACHE_ROOT": str(self.cache_root)}):
            return create_app(self.cwd, rebuild_cache=True)

    def _graph_edges(self, app):
        from fastapi.testclient import TestClient

        payload = TestClient(app).get(
            "/api/graph", params={"granularity": "entry", "edge_types": "supersedes,evolves,related"}
        ).json()
        return payload["edges"]

    def test_reader_returns_empty_without_sidecars(self):
        self.assertEqual(entry_link_sidecars(self.cwd), {})

    def test_reader_parses_edges_keyed_to_source_entry(self):
        self._write_sidecar(
            _link_block("2026-06-01 10:00", NEW, "New palette", supersedes=[OLD], evolves=[THIRD])
        )
        parsed = entry_link_sidecars(self.cwd)
        self.assertEqual(parsed[NEW]["supersedes"], (OLD,))
        self.assertEqual(parsed[NEW]["evolves"], (THIRD,))

    def test_reader_unions_multiple_blocks_for_one_entry(self):
        self._write_sidecar(
            _link_block("2026-06-01 10:00", NEW, "a", supersedes=[OLD])
            + _link_block("2026-06-01 10:00", NEW, "b", supersedes=[THIRD])
        )
        self.assertEqual(set(entry_link_sidecars(self.cwd)[NEW]["supersedes"]), {OLD, THIRD})

    def test_graph_emits_sidecar_supersedes_edge(self):
        # The walking skeleton: a sidecar-declared supersedes must show up as a
        # graph edge the Trail can draw.
        self._write_sidecar(_link_block("2026-06-01 10:00", NEW, "New palette", supersedes=[OLD]))
        edges = self._graph_edges(self._app())
        self.assertIn({"source": NEW, "target": OLD, "type": "supersedes"}, edges)

    def test_v1_graph_inherits_sidecar_lifecycle_edges(self):
        # Sidecar edges are ordinary supersedes/evolves entries in the edges
        # list, which the versioned surface never stripped - they flow through
        # the shared service. Pins that v1 sees them just like the legacy graph
        # (the merge-geometry v1 promotion did not disturb edge provenance).
        from fastapi.testclient import TestClient

        self._write_sidecar(_link_block("2026-06-01 10:00", NEW, "New palette", supersedes=[OLD]))
        payload = TestClient(self._app()).get(
            "/api/v1/graph", params={"granularity": "entry", "edge_types": "supersedes,evolves,related"}
        ).json()
        self.assertIn({"source": NEW, "target": OLD, "type": "supersedes"}, payload["edges"])

    def test_graph_has_no_lifecycle_edge_without_sidecar(self):
        edges = self._graph_edges(self._app())
        self.assertFalse([e for e in edges if e["type"] in {"supersedes", "evolves"}])

    def test_self_reference_is_dropped(self):
        self._write_sidecar(_link_block("2026-06-01 10:00", NEW, "self", supersedes=[NEW, OLD]))
        edges = self._graph_edges(self._app())
        lifecycle = [e for e in edges if e["type"] == "supersedes"]
        self.assertEqual(lifecycle, [{"source": NEW, "target": OLD, "type": "supersedes"}])

    def test_malformed_sidecar_filename_is_flagged_not_read(self):
        links_dir = self.sessions / "links" / "2026-06"
        links_dir.mkdir(parents=True, exist_ok=True)
        (links_dir / "not-a-date.md").write_text(
            _link_block("2026-06-01 10:00", NEW, "x", supersedes=[OLD]), encoding="utf-8"
        )
        docs = list(iter_link_sidecar_documents(self.sessions))
        self.assertTrue(any(d.malformed_reason for d in docs))
        # A malformed file is skipped by the parser, so no edge leaks from it.
        self.assertEqual(entry_link_sidecars(self.cwd), {})

    def test_non_crockford_entry_ids_still_parse(self):
        # Real corpus ids include o/u/i/l (outside the strict Crockford charset
        # of the entry-YAML ref regex), e.g. codex-authored entries. The sidecar
        # reader must not silently drop them - regression for a live bug where
        # an evolves edge to mse_...o/u/i/l... vanished without a trace.
        loose = "mse_37fpcovvuniqzlxk"  # contains o, u, i, l
        (self.sessions / "2026-06-02.md").write_text(
            "---\ntags:\n  - session-log\n---\n\n"
            + _entry("2026-06-02 09:00", loose, "Codex-style id", branch="feature-y"),
            encoding="utf-8",
        )
        self._write_sidecar(
            _link_block("2026-06-02 10:00", NEW, "late edge", evolves=[loose]),
            month="2026-06",
            day="2026-06-01",
        )
        parsed = entry_link_sidecars(self.cwd)
        self.assertEqual(parsed[NEW]["evolves"], (loose,))

    def test_month_folder_mismatch_is_flagged(self):
        links_dir = self.sessions / "links" / "2026-06"
        links_dir.mkdir(parents=True, exist_ok=True)
        (links_dir / "2026-07-01.md").write_text("## x\n", encoding="utf-8")
        docs = list(iter_link_sidecar_documents(self.sessions))
        self.assertTrue(any(d.malformed_reason and "month folder" in d.malformed_reason for d in docs))


if __name__ == "__main__":
    unittest.main()
