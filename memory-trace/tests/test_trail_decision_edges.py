"""Decision-level sidecar edges land on the Trail's decision rows.

The ratified contract (docs/3_Spec/draft/decision-level-link-sidecar-refs.md)
has two halves and both are asserted here:

1. A ref written ``<entry_id>:dN`` in a link sidecar draws an edge terminating
   on that entry's ``dN`` Trail row, not on its entry row.
2. It is a DISTINCT edge set. "B evolves A:d2" does not license "B evolves A",
   so every consumer that does not model decisions must see exactly the edge
   set it saw before the feature existed.

The second is the one that is easy to lose by accident, so it is asserted as a
set equality against a sidecar-free control corpus rather than by spot-check.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from memory_trace.service import TraceCache, TraceService

SESSIONS = """## 2026-06-01 09:00 - earlier multi-decision entry

```yaml
entry_id: mse_tgt00000000aaaa
branch: main
```

### Summary

- Two independent calls.

### Decisions

#### D1 - Keep the parser

- D: keep.
- R: because.

#### D2 - Default the range to seven days

- D: seven days.
- R: because.

## 2026-06-01 10:00 - earlier single-decision entry

```yaml
entry_id: mse_sgl00000000bbbb
branch: main
```

### Decision

- D: only.
- R: because.

## 2026-06-02 09:00 - later entry that reverses one call

```yaml
entry_id: mse_src00000000cccc
branch: main
```

### Decision

- D: all dates.
- R: because.

## 2026-06-02 10:00 - later entry pointing at a single-decision entry

```yaml
entry_id: mse_oth00000000dddd
branch: main
```

### Decision

- D: something.
- R: because.
"""

SIDECAR = """## 2026-06-03 09:00 - later-found lifecycle edges

```yaml
entry_id: mse_src00000000cccc
evolves:
  - mse_tgt00000000aaaa:d2
```
## 2026-06-03 09:10 - a decision ref at d1 of a singular-Decision entry

```yaml
entry_id: mse_oth00000000dddd
replaces:
  - mse_sgl00000000bbbb:d1
```
"""

EDGE_TYPES = ("branch", "replaces", "evolves", "related")


class TrailDecisionEdgeTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mtrace-dedges-"))
        self.cache_root = Path(tempfile.mkdtemp(prefix="mtrace-dedges-cache-"))
        sessions = self.cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True)
        (sessions / "2026-06-01.md").write_text(
            "---\ntags:\n  - session-log\n---\n\n" + SESSIONS, encoding="utf-8"
        )
        self.links_dir = sessions / "links" / "2026-06"
        self.links_dir.mkdir(parents=True)
        self.sidecar_path = self.links_dir / "2026-06-03.md"
        self.sidecar_path.write_text(
            "---\ntags:\n  - session-log-links\nlink_date: 2026-06-03\n---\n\n" + SIDECAR,
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.cwd, ignore_errors=True)
        shutil.rmtree(self.cache_root, ignore_errors=True)

    def service(self):
        cache = TraceCache(self.cwd, cache_root=self.cache_root)
        cache.rebuild()
        return TraceService(cache)

    def trail(self, service=None, **kwargs):
        service = service or self.service()
        return service.graph(edge_types=EDGE_TYPES, limit=1000, include_decisions=True, **kwargs)

    def test_decision_ref_terminates_on_the_decision_row_not_the_entry_row(self):
        trail = self.trail()
        row_ids = {node["id"] for node in trail["nodes"]}
        d2_row = "mse_tgt00000000aaaa#decisions/d2-default-the-range-to-seven-days"
        self.assertIn(d2_row, row_ids, "the decision row must exist to terminate on")
        outbound = [edge for edge in trail["edges"] if edge["source"] == "mse_src00000000cccc"]
        self.assertIn({"source": "mse_src00000000cccc", "target": d2_row, "type": "evolves"}, outbound)
        # The whole point: the entry-level edge is NOT also drawn. Drawing both
        # would restore the overstatement the decision ref exists to remove.
        self.assertNotIn({"source": "mse_src00000000cccc", "target": "mse_tgt00000000aaaa", "type": "evolves"}, outbound)

    def test_focused_view_still_reaches_the_far_end_of_a_decision_edge(self):
        # Membership expansion: upgrading a ref to ':dN' must not make its
        # target disappear when the source is focused.
        trail = self.trail(entry_id="mse_src00000000cccc", depth=1)
        self.assertIn("mse_tgt00000000aaaa", {node["entry_id"] for node in trail["nodes"]})
        self.assertTrue(
            any(edge["target"].startswith("mse_tgt00000000aaaa#decisions/d2-") for edge in trail["edges"])
        )

    def test_single_decision_target_attaches_to_its_entry_row(self):
        # A singular '### Decision' entry has no separate d1 row, and the draft
        # states the entry-level and d1 forms denote the same edge - so the
        # entry row IS d1 here. Documented behaviour, not an accident.
        trail = self.trail()
        self.assertIn(
            {"source": "mse_oth00000000dddd", "target": "mse_sgl00000000bbbb", "type": "replaces"}, trail["edges"]
        )

    def test_dangling_ordinal_on_an_expanded_entry_draws_nothing(self):
        # links check errors on this, so it should never reach a clean corpus -
        # but if it does, falling back to the entry row would widen a bad ':d7'
        # into an entry-level edge, which is the overstatement being removed.
        self.sidecar_path.write_text(
            "---\ntags:\n  - session-log-links\nlink_date: 2026-06-03\n---\n\n"
            "## 2026-06-03 09:00 - ordinal that does not exist\n\n"
            "```yaml\nentry_id: mse_src00000000cccc\nevolves:\n  - mse_tgt00000000aaaa:d7\n```\n",
            encoding="utf-8",
        )
        edges = self.trail()["edges"]
        self.assertEqual([e for e in edges if e["source"] == "mse_src00000000cccc" and e["type"] == "evolves"], [])

    def _write_multi_decision_source(self):
        (self.cwd / ".memory-seed" / "sessions" / "2026-06-04.md").write_text(
            "---\ntags:\n  - session-log\n---\n\n"
            "## 2026-06-04 09:00 - later multi-decision source\n\n"
            "```yaml\nentry_id: mse_msrc0000000eeee\nbranch: main\n```\n\n"
            "### Decisions\n\n"
            "#### D1 - Unrelated call\n\n- D: x.\n- R: y.\n\n"
            "#### D2 - The reversal\n\n- D: z.\n- R: w.\n",
            encoding="utf-8",
        )

    def test_arrow_source_prefix_resolves_to_the_source_decision_row(self):
        # Grammar v2 (2026-07-24): `d2 -> <ref>` names WHICH decision of the
        # authoring entry drives the edge, so the edge leaves from that
        # decision's own Trail row instead of the entry anchor.
        self._write_multi_decision_source()
        self.sidecar_path.write_text(
            "---\ntags:\n  - session-log-links\nlink_date: 2026-06-03\n---\n\n"
            "## 2026-06-04 10:00 - arrow-attributed edge\n\n"
            "```yaml\nentry_id: mse_msrc0000000eeee\nevolves:\n"
            "  - d2 -> mse_tgt00000000aaaa:d2\n```\n",
            encoding="utf-8",
        )
        trail = self.trail()
        row_ids = {node["id"] for node in trail["nodes"]}
        d2_source = next(i for i in row_ids if i.startswith("mse_msrc0000000eeee#decisions/d2-"))
        d2_target = "mse_tgt00000000aaaa#decisions/d2-default-the-range-to-seven-days"
        self.assertIn({"source": d2_source, "target": d2_target, "type": "evolves"}, trail["edges"])
        # The entry-anchor edge is NOT also drawn - the arrow narrowed it.
        self.assertEqual(
            [e for e in trail["edges"] if e["source"] == "mse_msrc0000000eeee" and e["type"] == "evolves"], []
        )

    def test_arrow_bare_ref_draws_the_decision_row_edge_not_its_entry_twin(self):
        # `d2 -> mse_x` (bare target) keeps its entry-level edge for /graph
        # and lifecycle consumers, but the Trail renders only the finer
        # decision-row line - drawing both would duplicate one statement.
        self._write_multi_decision_source()
        self.sidecar_path.write_text(
            "---\ntags:\n  - session-log-links\nlink_date: 2026-06-03\n---\n\n"
            "## 2026-06-04 10:00 - arrow-bare edge\n\n"
            "```yaml\nentry_id: mse_msrc0000000eeee\nreplaces:\n"
            "  - d2 -> mse_sgl00000000bbbb\n```\n",
            encoding="utf-8",
        )
        trail = self.trail()
        d2_source = next(
            i for i in {n["id"] for n in trail["nodes"]} if i.startswith("mse_msrc0000000eeee#decisions/d2-")
        )
        replaces = [e for e in trail["edges"] if e["type"] == "replaces" and e["target"] == "mse_sgl00000000bbbb"]
        self.assertEqual(replaces, [{"source": d2_source, "target": "mse_sgl00000000bbbb", "type": "replaces"}])

    def test_decision_edges_never_reach_entry_level_consumers(self):
        # Set equality against a control corpus with the sidecar deleted: the
        # non-decision surface must be indistinguishable from the world where
        # this feature was never built.
        service = self.service()
        with_sidecar = service.graph(edge_types=EDGE_TYPES, limit=1000)
        self.assertEqual(service._derived()[1]["mse_src00000000cccc"].evolves, ())
        self.sidecar_path.unlink()
        control = self.service().graph(edge_types=EDGE_TYPES, limit=1000)

        def edge_set(payload):
            return {(edge["source"], edge["target"], edge["type"]) for edge in payload["edges"]}

        self.assertEqual(edge_set(with_sidecar), edge_set(control))

    def test_trail_survives_a_cold_cache_load_of_an_entry_yaml_decision_edge(self):
        # Regression, found live on 2026-07-24: every other test here rebuilds
        # the cache in-process, where decision_edges are still the tuples the
        # extractor made. A SECOND process reads them back from storage, where
        # JSON has no tuple - so each edge came back as a LIST and the Trail's
        # dedup died with `unhashable type: 'list'`, 500-ing the whole view.
        # The equivalence suite could not see it either: it compares
        # json.dumps output, in which a tuple and a list are the same bytes.
        (self.cwd / ".memory-seed" / "sessions" / "2026-06-04.md").write_text(
            "---\ntags:\n  - session-log\n---\n\n"
            "## 2026-06-04 09:00 - entry-yaml decision edge\n\n"
            "```yaml\nentry_id: mse_yaml0000000ffff\nbranch: main\nevolves:\n"
            "  - mse_tgt00000000aaaa:d2\n```\n\n"
            "### Decision\n\n- D: x.\n- R: y.\n",
            encoding="utf-8",
        )
        self.service()  # writes the projection to cache_root

        # A cache pointed at the SAME cache_root, never rebuilt: this is what a
        # fresh process sees, and the only path that deserializes chunks.
        cold = TraceCache(self.cwd, cache_root=self.cache_root)
        chunk = next(c for c in cold.chunks() if c.entry_id == "mse_yaml0000000ffff")
        self.assertEqual(chunk.decision_edges, (("evolves", "", "mse_tgt00000000aaaa", "d2"),))
        self.assertEqual(len(set(chunk.decision_edges)), 1, "edges must be hashable after a load")

        trail = TraceService(cold).graph(edge_types=EDGE_TYPES, limit=1000, include_decisions=True)
        d2_row = "mse_tgt00000000aaaa#decisions/d2-default-the-range-to-seven-days"
        self.assertIn(
            {"source": "mse_yaml0000000ffff", "target": d2_row, "type": "evolves"}, trail["edges"]
        )

    def test_entry_level_sidecar_refs_are_unaffected(self):
        self.sidecar_path.write_text(
            "---\ntags:\n  - session-log-links\nlink_date: 2026-06-03\n---\n\n"
            "## 2026-06-03 09:00 - entry-level edge\n\n"
            "```yaml\nentry_id: mse_src00000000cccc\nevolves:\n  - mse_tgt00000000aaaa\n```\n",
            encoding="utf-8",
        )
        trail = self.trail()
        self.assertIn(
            {"source": "mse_src00000000cccc", "target": "mse_tgt00000000aaaa", "type": "evolves"}, trail["edges"]
        )


if __name__ == "__main__":
    unittest.main()
