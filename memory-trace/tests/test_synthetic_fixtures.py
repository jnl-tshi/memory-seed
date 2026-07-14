import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from memory_trace.service import TraceCache, TraceService

FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(FIXTURES))

from generate_synthetic import generate  # noqa: E402


class SyntheticFixtureTests(unittest.TestCase):
    """Phase 0 baseline: the synthetic-corpus generator is itself a fixture.

    The 500/1k/10k datasets are generated on demand, so what the tests pin is
    the determinism contract (same count+seed -> byte-identical tree) and that
    the output is a real corpus the actual cache ingests with the shapes the
    Trail needs (branches, lifecycle edges).
    """

    def setUp(self):
        self.out = Path(tempfile.mkdtemp(prefix="memory-trace-synth-"))
        self.cache_root = Path(tempfile.mkdtemp(prefix="memory-trace-synth-cache-"))
        self.addCleanup(lambda: shutil.rmtree(self.out, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(self.cache_root, ignore_errors=True))

    def _tree_bytes(self, root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*.md"))
        }

    def test_generator_is_deterministic(self):
        first = self.out / "a"
        second = self.out / "b"
        generate(64, first)
        generate(64, second)
        self.assertEqual(self._tree_bytes(first), self._tree_bytes(second))
        # A different seed produces a different corpus (the seed is real).
        third = self.out / "c"
        generate(64, third, seed=7)
        self.assertNotEqual(self._tree_bytes(first), self._tree_bytes(third))

    def test_generated_corpus_feeds_the_real_cache(self):
        project = self.out / "proj"
        generate(64, project)
        cache = TraceCache(project, cache_root=self.cache_root)
        cache.rebuild()
        service = TraceService(cache)

        facets = service.facets()
        self.assertEqual(facets["runtime"]["entry_count"], 64)

        graph = service.graph(
            granularity="entry",
            edge_types=("branch", "supersedes", "evolves", "related"),
            limit=1000,
        )
        self.assertEqual(len(graph["nodes"]), 64)
        edge_types = {edge["type"] for edge in graph["edges"]}
        # The Trail's full edge grammar must be present at fixture scale.
        self.assertIn("branch", edge_types)
        self.assertIn("related", edge_types)
        branches = {node.get("branch") for node in graph["nodes"]}
        self.assertIn("main", branches)
        self.assertTrue(any(b and b.startswith("feature/synth-") for b in branches))

        # Search over the synthetic prose returns ranked matches.
        page = service.search(q="trail lane allocation", granularity="entry", limit=10)
        self.assertTrue(page["results"])


if __name__ == "__main__":
    unittest.main()
