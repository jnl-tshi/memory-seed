"""Frozen external semantic oracle for the Codex decision-edge replay.

This module is executed from the harness directory with the candidate's
``memory-trace`` package on ``PYTHONPATH``.  It is never copied into a subject
fixture and never imports candidate-authored tests.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from memory_trace.service import TraceCache, TraceService
from memory_seed.retrieval import get_chunk, search_memory

ORACLE_SCHEMA_VERSION = 1
ORACLE_VERSION = "codex-decision-edge-v4-semantic-v1"

TARGET = "mse_tgt00000000aaaa"
SINGLE = "mse_sgl00000000bbbb"
SOURCE = "mse_src00000000cccc"
OTHER = "mse_oth00000000dddd"
TARGET_D2 = f"{TARGET}#decisions/d2-default-the-range-to-seven-days"
EDGE_TYPES = ("branch", "supersedes", "evolves", "related")

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


def _sidecar(ref: str, *, source: str = SOURCE, kind: str = "evolves") -> str:
    return (
        "---\ntags:\n  - session-log-links\nlink_date: 2026-06-03\n---\n\n"
        "## 2026-06-03 09:00 - later-found lifecycle edge\n\n"
        f"```yaml\nentry_id: {source}\n{kind}:\n  - {ref}\n```\n"
    )


def _edge_set(payload: dict[str, object]) -> set[tuple[str, str, str]]:
    return {
        (edge["source"], edge["target"], edge["type"])
        for edge in payload["edges"]  # type: ignore[index]
    }


class FrozenSemanticOracle(unittest.TestCase):
    def setUp(self) -> None:
        self._workspace = Path(tempfile.mkdtemp(prefix="codex-dedge-oracle-"))
        self._cache = Path(tempfile.mkdtemp(prefix="codex-dedge-cache-"))
        sessions = self._workspace / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True)
        (sessions / "2026-06-01.md").write_text(
            "---\ntags:\n  - session-log\n---\n\n" + SESSIONS,
            encoding="utf-8",
            newline="\n",
        )
        links = sessions / "links" / "2026-06"
        links.mkdir(parents=True)
        self.sidecar = links / "2026-06-03.md"
        self._write_sidecar(f"{TARGET}:d2")

    def tearDown(self) -> None:
        shutil.rmtree(self._workspace, ignore_errors=True)
        shutil.rmtree(self._cache, ignore_errors=True)

    def _write_sidecar(self, ref: str, *, source: str = SOURCE, kind: str = "evolves") -> None:
        self.sidecar.write_text(
            _sidecar(ref, source=source, kind=kind),
            encoding="utf-8",
            newline="\n",
        )

    def _service(self) -> TraceService:
        cache = TraceCache(self._workspace, cache_root=self._cache)
        cache.rebuild()
        return TraceService(cache)

    def _trail(self, **kwargs: object) -> dict[str, object]:
        return self._service().graph(
            edge_types=EDGE_TYPES,
            limit=1000,
            include_decisions=True,
            **kwargs,
        )

    def test_decision_row_target(self) -> None:
        trail = self._trail()
        self.assertIn(TARGET_D2, {node["id"] for node in trail["nodes"]})
        edge = {"source": SOURCE, "target": TARGET_D2, "type": "evolves"}
        self.assertIn(edge, trail["edges"])
        self.assertNotIn(
            {"source": SOURCE, "target": TARGET, "type": "evolves"},
            trail["edges"],
        )
        self.assertEqual({"source", "target", "type"}, set(edge))

    def test_focused_membership_from_both_endpoints(self) -> None:
        for focus, far in ((SOURCE, TARGET), (TARGET, SOURCE)):
            with self.subTest(focus=focus):
                trail = self._trail(entry_id=focus, depth=1)
                self.assertIn(far, {node["entry_id"] for node in trail["nodes"]})
                self.assertIn(
                    {"source": SOURCE, "target": TARGET_D2, "type": "evolves"},
                    trail["edges"],
                )

    def test_non_decision_edge_set_equals_sidecar_free_control(self) -> None:
        service = self._service()
        with_sidecar = service.graph(edge_types=EDGE_TYPES, limit=1000)
        self.assertEqual((), service._derived()[1][SOURCE].evolves)
        trace_search = service.search(q="later", limit=1000)
        trace_source = service.chunk(SOURCE)
        retrieval_search = search_memory(
            "later",
            self._workspace,
            top_k=10,
            recency_enabled=False,
            semantic_enabled=False,
            supersession_damping=False,
            superseding_successor_boost=False,
        )
        retrieval_source = get_chunk(SOURCE, self._workspace)
        self.sidecar.unlink()
        control_service = self._service()
        control = control_service.graph(edge_types=EDGE_TYPES, limit=1000)
        self.assertEqual(_edge_set(control), _edge_set(with_sidecar))
        self.assertEqual(trace_search, control_service.search(q="later", limit=1000))
        self.assertEqual(trace_source, control_service.chunk(SOURCE))
        self.assertEqual(
            retrieval_search,
            search_memory(
                "later",
                self._workspace,
                top_k=10,
                recency_enabled=False,
                semantic_enabled=False,
                supersession_damping=False,
                superseding_successor_boost=False,
            ),
        )
        self.assertEqual(retrieval_source, get_chunk(SOURCE, self._workspace))

    def test_entry_level_ref_regression(self) -> None:
        self._write_sidecar(TARGET)
        expected = {"source": SOURCE, "target": TARGET, "type": "evolves"}
        graph = self._service().graph(edge_types=EDGE_TYPES, limit=1000)
        trail = self._trail()
        self.assertIn(expected, graph["edges"])
        self.assertIn(expected, trail["edges"])

    def test_invalid_ordinal_does_not_widen(self) -> None:
        self._write_sidecar(f"{TARGET}:d99")
        trail = self._trail()
        outbound = [
            edge
            for edge in trail["edges"]
            if edge["source"] == SOURCE and edge["type"] == "evolves"
        ]
        self.assertEqual([], outbound)

    def test_single_decision_d1_fallback(self) -> None:
        self._write_sidecar(f"{SINGLE}:d1", source=OTHER, kind="supersedes")
        self.assertIn(
            {"source": OTHER, "target": SINGLE, "type": "supersedes"},
            self._trail()["edges"],
        )


GATE_METHODS = {
    "decision_row_target": "test_decision_row_target",
    "focused_membership": "test_focused_membership_from_both_endpoints",
    "entry_edge_set_equality": "test_non_decision_edge_set_equals_sidecar_free_control",
    "entry_ref_regression": "test_entry_level_ref_regression",
    "invalid_ordinal_no_widening": "test_invalid_ordinal_does_not_widen",
    "single_decision_d1": "test_single_decision_d1_fallback",
}


def main() -> int:
    results: dict[str, dict[str, str]] = {}
    for gate, method in GATE_METHODS.items():
        case = FrozenSemanticOracle(method)
        result = unittest.TestResult()
        case.run(result)
        if result.wasSuccessful():
            results[gate] = {"status": "pass", "detail": "1 hidden semantic test passed"}
            continue
        messages = [text for _test, text in (*result.failures, *result.errors)]
        results[gate] = {
            "status": "fail",
            "detail": "\n".join(messages)[-4000:] or "hidden semantic test failed",
        }
    print(
        json.dumps(
            {
                "schema_version": ORACLE_SCHEMA_VERSION,
                "oracle_version": ORACLE_VERSION,
                "gates": results,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
