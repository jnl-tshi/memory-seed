"""Qualify the Codex v5 preparer, grader, reference, and live mutants."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import common  # noqa: E402
import grade  # noqa: E402
import prepare  # noqa: E402

REFERENCE_VISIBILITY = "0ba56be3b08a2fcf44090e90e754da3350526045"
REFERENCE_ROBUSTNESS = "12884ac96c428d18d7e26079e03583a600fe1973"
SOURCE_REVISION = common.SOURCE_REVISION

HELPER_TEST = '''"""Candidate-authored focused decision-row test."""
import unittest
import memory_trace.service as service_module


class CandidateDecisionHelperTest(unittest.TestCase):
    def test_valid_d2_resolves_to_decision_row(self):
        helper = getattr(service_module, "_decision_edges_for_rows", None)
        self.assertIsNotNone(helper)
        nodes = [
            {"id": "mse_src00000000cccc", "entry_id": "mse_src00000000cccc", "decision_ordinal": None},
            {"id": "mse_tgt00000000aaaa", "entry_id": "mse_tgt00000000aaaa", "decision_ordinal": None},
            {"id": "mse_tgt00000000aaaa#decisions/d2-target", "entry_id": "mse_tgt00000000aaaa", "decision_ordinal": "d2"},
        ]
        sidecars = {"mse_src00000000cccc": {"decision_edges": (("evolves", "mse_tgt00000000aaaa", "d2"),)}}
        self.assertEqual(
            [{"source": "mse_src00000000cccc", "target": "mse_tgt00000000aaaa#decisions/d2-target", "type": "evolves"}],
            helper(nodes, sidecars, {"evolves"}),
        )


if __name__ == "__main__":
    unittest.main()
'''

V4_INVALID_ORDINAL_TEST = '''

class CandidateInvalidOrdinalTest(unittest.TestCase):
    def test_invalid_multi_decision_d99_does_not_widen_to_entry(self):
        from memory_trace import service as service_module

        helper = getattr(service_module, "_decision_edges_for_rows", None)
        self.assertIsNotNone(helper)
        nodes = [
            {"id": "mse_src00000000cccc", "entry_id": "mse_src00000000cccc", "decision_ordinal": None},
            {"id": "mse_tgt00000000aaaa", "entry_id": "mse_tgt00000000aaaa", "decision_ordinal": None},
            {"id": "mse_tgt00000000aaaa#decisions/d1-target", "entry_id": "mse_tgt00000000aaaa", "decision_ordinal": "d1"},
            {"id": "mse_tgt00000000aaaa#decisions/d2-target", "entry_id": "mse_tgt00000000aaaa", "decision_ordinal": "d2"},
        ]
        sidecars = {"mse_src00000000cccc": {"decision_edges": (("evolves", "mse_tgt00000000aaaa", "d99"),)}}
        self.assertEqual([], helper(nodes, sidecars, {"evolves"}))
'''

PROJECTION_TEST = '''"""Candidate-authored broad visibility assertion for the projection mutant."""
import shutil
import tempfile
import unittest
from pathlib import Path

from memory_trace.service import TraceCache, TraceService


class CandidateProjectionVisibilityTest(unittest.TestCase):
    def test_decision_ref_is_obviously_visible(self):
        root = Path(tempfile.mkdtemp(prefix="projection-test-"))
        cache_root = Path(tempfile.mkdtemp(prefix="projection-cache-"))
        try:
            sessions = root / ".memory-seed" / "sessions"
            sessions.mkdir(parents=True)
            (sessions / "2026-06-01.md").write_text("""---
tags: [session-log]
---

## 2026-06-01 09:00 - target

```yaml
entry_id: mse_tgt00000000aaaa
```

### Decisions

#### D1 - first

- D: one.

#### D2 - second

- D: two.

## 2026-06-02 09:00 - source

```yaml
entry_id: mse_src00000000cccc
```

### Decision

- D: source.
""", encoding="utf-8")
            links = sessions / "links" / "2026-06"
            links.mkdir(parents=True)
            (links / "2026-06-03.md").write_text("""---
tags: [session-log-links]
link_date: 2026-06-03
---

## 2026-06-03 09:00 - edge

```yaml
entry_id: mse_src00000000cccc
evolves:
  - mse_tgt00000000aaaa:d2
```
""", encoding="utf-8")
            cache = TraceCache(root, cache_root=cache_root)
            cache.rebuild()
            trail = TraceService(cache).graph(
                edge_types=("evolves",), limit=1000, include_decisions=True
            )
            self.assertIn(
                {"source": "mse_src00000000cccc", "target": "mse_tgt00000000aaaa", "type": "evolves"},
                trail["edges"],
            )
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(cache_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
'''

DEFECTIVE_CANDIDATE_TEST = '''"""A real but non-discriminating candidate regression test."""
import unittest


class CandidateQualityDefectTest(unittest.TestCase):
    def test_only_checks_a_constant(self):
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
'''


def _git_bytes(revision: str, path: str) -> bytes:
    return common.run(["git", "show", f"{revision}:{path}"], cwd=REPO_ROOT).stdout


def _candidate_copy(pristine: Path, destination: Path) -> Path:
    shutil.copytree(pristine, destination)
    return destination


def _write_revision_file(candidate: Path, revision: str, relative: str) -> None:
    target = candidate / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_git_bytes(revision, relative))


def _write_test(candidate: Path, content: str) -> None:
    target = candidate / grade.PUBLIC_TEST_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")


def _replace_once(candidate: Path, old: str, new: str) -> None:
    path = candidate / grade.SERVICE_PATH
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"mutant anchor occurred {text.count(old)} times")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def _reference(candidate: Path, revision: str, *, test_revision: str | None = None) -> None:
    _write_revision_file(candidate, revision, grade.SERVICE_PATH.as_posix())
    _write_revision_file(
        candidate,
        test_revision or revision,
        grade.PUBLIC_TEST_PATH.as_posix(),
    )
    test_path = candidate / grade.PUBLIC_TEST_PATH
    test_path.write_text(
        test_path.read_text(encoding="utf-8").replace(
            '\n\nif __name__ == "__main__":',
            V4_INVALID_ORDINAL_TEST + '\n\nif __name__ == "__main__":',
        ),
        encoding="utf-8",
        newline="\n",
    )


def _projection_mutant(candidate: Path) -> None:
    old = '''        extra = sidecars.get(chunk.entry_id or "")
        if not extra:
            augmented.append(chunk)
            continue
        augmented.append(
'''
    new = '''        extra = sidecars.get(chunk.entry_id or "")
        if not extra:
            augmented.append(chunk)
            continue
        # MUTANT: project decision-qualified targets onto entry-level lists.
        extra = dict(extra)
        for kind, target_entry_id, _ordinal in extra.get("decision_edges", ()):
            extra[kind] = tuple(extra.get(kind, ())) + (target_entry_id,)
        augmented.append(
'''
    _replace_once(candidate, old, new)
    _write_test(candidate, PROJECTION_TEST)


def _filter_mutant(candidate: Path) -> None:
    _reference(candidate, REFERENCE_ROBUSTNESS)
    old = '''            visible_edges.extend(
                _decision_edges_for_rows(nodes, self._link_sidecars(), edge_type_set)
            )
'''
    new = '''            # MUTANT: entry-ID filtering drops decision-row endpoints.
            for edge in _decision_edges_for_rows(nodes, self._link_sidecars(), edge_type_set):
                if edge["source"] in limited_ids and edge["target"] in limited_ids:
                    visible_edges.append(edge)
'''
    _replace_once(candidate, old, new)
    _write_test(candidate, HELPER_TEST)


def _ordinal_fallback_mutant(candidate: Path) -> None:
    _reference(candidate, REFERENCE_ROBUSTNESS)
    old = '''            target = decision_row.get((target_entry_id, ordinal))
            if not target and target_entry_id not in expanded_entries:
                target = entry_row.get(target_entry_id)
'''
    new = '''            # MUTANT: an unknown dN silently widens to the entry row.
            target = decision_row.get((target_entry_id, ordinal)) or entry_row.get(target_entry_id)
'''
    _replace_once(candidate, old, new)
    _write_test(candidate, HELPER_TEST)


def _candidate_test_quality_mutant(candidate: Path) -> None:
    """Keep the semantic patch while deliberately providing a non-discriminating test."""

    _reference(candidate, REFERENCE_ROBUSTNESS)
    _write_test(candidate, DEFECTIVE_CANDIDATE_TEST)


def _task1_controls(prepared_root: Path) -> dict[str, object]:
    """Re-execute Task 1's load-bearing controls on the same one-block run."""

    public = json.loads((prepared_root / "public-manifest.json").read_text(encoding="utf-8"))
    sealed = json.loads(
        (prepared_root / "sealed" / "condition-map.json").read_text(encoding="utf-8")
    )
    delta = json.loads(
        (prepared_root / "sealed" / "treatment-deltas.json").read_text(encoding="utf-8")
    )
    fixtures = [Path(record["fixture_path"]) for record in sealed["subjects"].values()]
    checks: dict[str, str] = {}

    relationship = common.verify_source_relationship(REPO_ROOT)
    if relationship["withheld_parent"] != SOURCE_REVISION or len(fixtures) != len(common.ARMS):
        raise RuntimeError("Task 1 ancestry/sample control failed")
    checks["ancestry_and_one_block_shape"] = "pass"

    for fixture in fixtures:
        common.assert_no_active_project_agent_config(fixture)
        common.assert_object_isolation(fixture)
        if common.run(["git", "status", "--porcelain"], cwd=fixture).stdout:
            raise RuntimeError("Task 1 pristine fixture control failed")
        if (fixture / "TASK.md").read_bytes() != common.TASK_PATH.read_bytes():
            raise RuntimeError("Task 1 task identity control failed")
    checks["sanitation_task_identity_and_object_isolation"] = "pass"

    serialized_public = json.dumps(public, sort_keys=True)
    if any(arm in serialized_public for arm in common.ARMS):
        raise RuntimeError("Task 1 sealed-mapping placement control failed")
    checks["sealed_mapping_placement"] = "pass"

    common.assert_cross_arm_equality(
        fixtures,
        allowed_treatment_paths=delta["allowed_treatment_paths"],
    )
    neutral_fixture = next(
        fixture for fixture in fixtures if not common.dated_session_documents(fixture)
    )
    neutral = neutral_fixture / ".memory-seed" / "sessions" / ".gitkeep"
    original = neutral.read_bytes()
    neutral.write_bytes(original + b"qualification mutation\n")
    try:
        try:
            common.assert_cross_arm_equality(
                fixtures,
                allowed_treatment_paths=delta["allowed_treatment_paths"],
            )
        except RuntimeError:
            pass
        else:
            raise RuntimeError("Task 1 cross-arm mutation control did not fail")
    finally:
        neutral.write_bytes(original)
    checks["cross_arm_equality_negative_control"] = "pass"

    fixture = fixtures[0]
    test_module = fixture / grade.PUBLIC_TEST_PATH
    missing = common.run(list(grade.PUBLIC_COMMAND), cwd=fixture, check=False)
    missing_output = (missing.stdout + missing.stderr).decode("utf-8", errors="replace")
    if missing.returncode == 0 or "test_trail_decision_edges" not in missing_output:
        raise RuntimeError("Task 1 missing-module command boundary failed")
    test_module.write_text(
        "import unittest\n\nclass Surface(unittest.TestCase):\n"
        "    def test_surface(self):\n        self.assertTrue(True)\n",
        encoding="utf-8",
        newline="\n",
    )
    try:
        present = common.run(list(grade.PUBLIC_COMMAND), cwd=fixture, check=False)
        if present.returncode:
            raise RuntimeError("Task 1 minimal-module command boundary failed")
    finally:
        test_module.unlink(missing_ok=True)
    checks["candidate_command_missing_and_minimal_module_boundary"] = "pass"

    contaminated = prepared_root.parent / "object-contamination-control"
    contaminated.mkdir()
    shutil.copytree(fixture / ".git", contaminated / ".git")
    commit_bytes = common.run(
        ["git", "cat-file", "commit", common.WITHHELD_REVISION], cwd=REPO_ROOT
    ).stdout
    imported = common.run(
        ["git", "hash-object", "-t", "commit", "-w", "--stdin"],
        cwd=contaminated,
        input_bytes=commit_bytes,
    ).stdout.decode("ascii").strip()
    if imported != common.WITHHELD_REVISION:
        raise RuntimeError("Task 1 contamination setup failed")
    try:
        common.assert_object_isolation(contaminated)
    except RuntimeError:
        pass
    else:
        raise RuntimeError("Task 1 object contamination control did not fail")
    checks["object_contamination_negative_control"] = "pass"

    artifact = json.loads((prepared_root / "artifact-sha256.json").read_text(encoding="utf-8"))
    for relative, expected in artifact["files"].items():
        if common.sha256_file(prepared_root / relative) != expected:
            raise RuntimeError(f"Task 1 artifact checksum failed: {relative}")
    checks["artifact_checksums"] = "pass"
    return {"status": "pass", "controls": checks}


def _summarize_grade(report: dict[str, object]) -> dict[str, object]:
    gates = report["gates"]
    return {
        "status": report["status"],
        "outcomes": report["outcomes"],
        "gates": {name: value["status"] for name, value in gates.items()},
    }


def _expect(
    name: str,
    report: dict[str, object],
    expected: dict[str, str],
    *,
    top_status: str,
    ready_for_scoring: bool,
) -> None:
    observed = {gate: report["gates"][gate]["status"] for gate in grade.ALL_GATES}
    top = (report["status"], report["ready_for_scoring"], report["baseline_integrity"]["status"])
    expected_top = (top_status, ready_for_scoring, "pass")
    if observed != expected or top != expected_top:
        details = {gate: report["gates"][gate] for gate in grade.ALL_GATES}
        raise RuntimeError(
            f"{name} qualification mismatch: expected={expected}/{expected_top}, "
            f"observed={observed}/{top}, details={details}"
        )


def verify() -> dict[str, object]:
    parent_visibility = common.run(
        ["git", "rev-parse", f"{REFERENCE_VISIBILITY}~1"], cwd=REPO_ROOT
    ).stdout.decode("ascii").strip()
    parent_robustness = common.run(
        ["git", "rev-parse", f"{REFERENCE_ROBUSTNESS}~1"], cwd=REPO_ROOT
    ).stdout.decode("ascii").strip()
    if parent_visibility != SOURCE_REVISION or parent_robustness != REFERENCE_VISIBILITY:
        raise RuntimeError("reference commits do not form the frozen source -> visibility -> robustness chain")

    plan = {
        "invariant": "Decision-scoped edges must never widen to entry-scoped edges.",
        "affected_code_path": "memory-trace/memory_trace/service.py",
        "acceptance_cases": ["D2 survives without projecting B-to-A at entry level."],
        "non_goals": ["Do not change unrelated entry-level retrieval behavior."],
    }
    treatment_receipt = {
        "retrieval_receipt": {
            "required": True,
            "query": grade.REQUIRED_RETRIEVAL_QUERY,
            "selected_chunk_id": grade.REQUIRED_RETRIEVAL_CHUNK_ID,
            "pre_edit_plan": plan,
        }
    }
    if grade.assess_retrieval_compliance(treatment_receipt, True)["status"] != "pass":
        raise RuntimeError("prescribed retrieval receipt positive control failed")
    treatment_receipt["retrieval_receipt"]["selected_chunk_id"] = "wrong-chunk"
    if grade.assess_retrieval_compliance(treatment_receipt, True)["status"] != "fail":
        raise RuntimeError("prescribed retrieval receipt negative control failed")

    with tempfile.TemporaryDirectory(prefix="codex-dedge-qualification-") as temporary:
        root = Path(temporary)
        prepared_root = root / "one-block"
        prepared = prepare.prepare_study(
            prepared_root,
            seed=20260816,
            run_id="harness-qualification",
            repo_root=REPO_ROOT,
            blocks=1,
        )
        task1 = _task1_controls(prepared_root)
        public = json.loads((prepared_root / "public-manifest.json").read_text(encoding="utf-8"))
        subject_id = public["blocks"][0]["subject_ids"][0]
        pristine = prepared_root / "subjects" / subject_id
        expected_baseline = public["subjects"][subject_id]["fixture_commit"]
        pristine_snapshot = root / "external-pristine-snapshot"
        grade._safe_extract_archive(pristine, pristine_snapshot)

        builders: dict[str, Callable[[Path], None]] = {
            "pristine": lambda _candidate: None,
            "unamended_visibility_reference": lambda candidate: _reference(
                candidate, REFERENCE_VISIBILITY
            ),
            "composite_reference": lambda candidate: _reference(
                candidate, REFERENCE_ROBUSTNESS
            ),
            "projection_mutant": _projection_mutant,
            "filter_mutant": _filter_mutant,
            "ordinal_fallback_mutant": _ordinal_fallback_mutant,
            "semantic_safe_defective_candidate_test": _candidate_test_quality_mutant,
        }
        reports: dict[str, dict[str, object]] = {}
        for name, builder in builders.items():
            candidate = _candidate_copy(pristine, root / f"candidate-{name}")
            builder(candidate)
            reports[name] = grade.grade_candidate(
                candidate,
                expected_baseline=expected_baseline,
                _qualification_pristine_snapshot=pristine_snapshot,
            )

        p = "pass"
        f = "fail"
        _expect(
            "pristine",
            reports["pristine"],
            {
                "decision_row_target": f,
                "focused_membership": f,
                "entry_edge_set_equality": p,
                "entry_ref_regression": p,
                "invalid_ordinal_no_widening": p,
                "single_decision_d1": f,
                "public_task_tests": f,
                "bounded_scope": p,
                "candidate_test_discriminates": f,
            },
            top_status=f,
            ready_for_scoring=True,
        )
        _expect(
            "unamended visibility reference",
            reports["unamended_visibility_reference"],
            {
                **{gate: p for gate in grade.ALL_GATES},
                "invalid_ordinal_no_widening": f,
                "public_task_tests": f,
                "candidate_test_discriminates": f,
            },
            top_status=f,
            ready_for_scoring=True,
        )
        _expect(
            "composite reference",
            reports["composite_reference"],
            {gate: p for gate in grade.ALL_GATES},
            top_status=p,
            ready_for_scoring=True,
        )
        _expect(
            "semantic-safe candidate with defective candidate test quality",
            reports["semantic_safe_defective_candidate_test"],
            {
                **{gate: p for gate in grade.ALL_GATES},
                "candidate_test_discriminates": f,
            },
            top_status=p,
            ready_for_scoring=True,
        )
        if (
            reports["semantic_safe_defective_candidate_test"]["outcomes"]["semantic_safety_pass"]
            is not True
            or reports["semantic_safe_defective_candidate_test"]["outcomes"]["candidate_test_quality"]
            is not False
        ):
            raise RuntimeError("candidate-test quality must not change a semantic-safe top-level pass")
        _expect(
            "projection mutant",
            reports["projection_mutant"],
            {
                "decision_row_target": f,
                "focused_membership": f,
                "entry_edge_set_equality": f,
                "entry_ref_regression": p,
                "invalid_ordinal_no_widening": f,
                "single_decision_d1": p,
                "public_task_tests": p,
                "bounded_scope": p,
                "candidate_test_discriminates": p,
            },
            top_status=f,
            ready_for_scoring=True,
        )
        _expect(
            "filter mutant",
            reports["filter_mutant"],
            {
                **{gate: p for gate in grade.ALL_GATES},
                "decision_row_target": f,
                "focused_membership": f,
            },
            top_status=f,
            ready_for_scoring=True,
        )
        _expect(
            "ordinal fallback mutant",
            reports["ordinal_fallback_mutant"],
            {
                **{gate: p for gate in grade.ALL_GATES},
                "invalid_ordinal_no_widening": f,
            },
            top_status=f,
            ready_for_scoring=True,
        )

        mismatch_candidate = _candidate_copy(pristine, root / "candidate-baseline-mismatch")
        common.run(
            ["git", "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "mutant baseline"],
            cwd=mismatch_candidate,
        )
        wrong_baseline = grade.grade_candidate(
            mismatch_candidate,
            expected_baseline=expected_baseline,
            _qualification_pristine_snapshot=pristine_snapshot,
        )
        absent_baseline = grade.grade_candidate(
            pristine,
            expected_baseline="f" * 40,
            _qualification_pristine_snapshot=pristine_snapshot,
        )
        for label, rejected in (("mismatched", wrong_baseline), ("absent", absent_baseline)):
            if (
                rejected["status"] != "error"
                or rejected["ready_for_scoring"] is not False
                or rejected["baseline_integrity"]["status"] != "error"
                or any(rejected["gates"][gate]["status"] != "error" for gate in grade.ALL_GATES)
            ):
                raise RuntimeError(f"{label} baseline control was not rejected before grading")

        return {
            "schema_version": 1,
            "instrument": "codex-decision-edge-v5",
            "status": "pass",
            "qualification_fixture_count": prepared["fixture_count"],
            "qualification_block_count": 1,
            "task1_controls": task1,
            "retrieval_receipt_controls": "pass",
            "reference_chain": {
                "source": SOURCE_REVISION,
                "visibility": REFERENCE_VISIBILITY,
                "robustness": REFERENCE_ROBUSTNESS,
                "visibility_parent": parent_visibility,
                "robustness_parent": parent_robustness,
            },
            "controls": {name: _summarize_grade(report) for name, report in reports.items()},
            "baseline_rejection_controls": {
                "mismatched_expected_commit": wrong_baseline["baseline_integrity"],
                "absent_expected_commit": absent_baseline["baseline_integrity"],
            },
            "artifacts_persisted": False,
        }


def main() -> int:
    print(json.dumps(verify(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
