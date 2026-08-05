import importlib.util
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "context-derivation"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, EXPERIMENT / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fixture_builder = _load("strong_context_sweep_fixture_builder", "generate_fixtures.py")
sweep = _load("strong_context_sweep", "strong_context_sweep_v2.py")


def approved_ranking_receipt(question, fixture_root, *, top_k):
    receipt = sweep.bridge.ranking_receipt_proposal(question, fixture_root, top_k=top_k)
    receipt["approval_status"] = "APPROVED"
    receipt["fingerprint"] = sweep.bridge.fingerprint({key: value for key, value in receipt.items() if key != "fingerprint"})
    return receipt


def test_configuration_grid_is_bounded_unique_and_keeps_top_k_out_of_the_packet_policy():
    grid = sweep.configuration_grid()

    assert len(grid) == 216
    assert len({tuple(sorted(row.items())) for row in grid}) == len(grid)
    assert all("top_k" not in row for row in grid)


def test_sweep_uses_literal_question_and_reports_top_k_only_as_offline_metrics():
    _manifest, gold, tasks = fixture_builder.load_definitions()
    task = next(item for item in tasks if item["task_id"] == "CTX-10")
    label = next(item for item in gold["tasks"] if item["task_id"] == task["task_id"])
    with tempfile.TemporaryDirectory() as temporary:
        built = fixture_builder.build_all(Path(temporary) / "fixtures")
        root = next(item.path for item in built if item.fixture_id == task["fixture"])
        result = sweep.sweep_task(
            task, label, root,
            [{"result_cap": 3, "strong_cap": 1, "adr_cap": 1, "constitution_binding_cap": 1, "constitution_excerpt_chars": 96, "lineage_item_cap": 4}],
            ranking_receipt=approved_ranking_receipt(task["question"], root, top_k=3),
        )

    assert result["schema"] == "strong-context-v2-offline-sweep.v1"
    assert result["top_k_metrics"]["schema"] == "context-top-k-metrics.v2"
    assert len(result["cells"]) == 1
    assert "top_k" not in result["cells"][0]["configuration"]
    assert result["derived_topk_gold"]["required_constitution_refs"]
    assert result["cells"][0]["packet_token_proxy"] > 0
    coverage = result["cells"][0]["coverage"]
    assert {"decision", "authority", "status", "lineage", "related", "absence"} <= set(coverage)
    assert coverage["related"]["never_classified_as_lineage"]


def test_coverage_checks_pending_authority_status_and_typed_lineage():
    _manifest, gold, tasks = fixture_builder.load_definitions()
    task = next(item for item in tasks if item["task_id"] == "CTX-10")
    label = next(item for item in gold["tasks"] if item["task_id"] == task["task_id"])
    with tempfile.TemporaryDirectory() as temporary:
        built = fixture_builder.build_all(Path(temporary) / "fixtures")
        root = next(item.path for item in built if item.fixture_id == task["fixture"])
        bindings = sweep.bridge.materialize_fixture_bindings(root)
        _membership, constitution = sweep._mappings(bindings)
        packet = sweep.resolver.resolve_strong_context(
            [{"ref": "mse_ctxpendingnew:d1", "relevance": "strong", "excerpt": "pending", "links": {"evolves": [], "replaces": [], "related": []}}],
            bindings,
        )
        coverage = sweep._coverage(packet, sweep._derived_topk_gold(label, constitution))

    assert coverage["decision"]["complete"]
    assert coverage["authority"]["complete"]
    assert coverage["status"]["complete"]
    assert coverage["lineage"]["complete"]
    assert coverage["related"]["never_classified_as_lineage"]


def test_parallel_cell_resolution_has_the_same_deterministic_result():
    _manifest, gold, tasks = fixture_builder.load_definitions()
    task = next(item for item in tasks if item["task_id"] == "CTX-09")
    label = next(item for item in gold["tasks"] if item["task_id"] == task["task_id"])
    configurations = [
        {"result_cap": 3, "strong_cap": 1, "adr_cap": 1, "constitution_binding_cap": 1, "constitution_excerpt_chars": 96, "lineage_item_cap": 4},
        {"result_cap": 5, "strong_cap": 2, "adr_cap": 2, "constitution_binding_cap": 2, "constitution_excerpt_chars": 192, "lineage_item_cap": 8},
    ]
    with tempfile.TemporaryDirectory() as temporary:
        built = fixture_builder.build_all(Path(temporary) / "fixtures")
        root = next(item.path for item in built if item.fixture_id == task["fixture"])
        receipt = approved_ranking_receipt(task["question"], root, top_k=5)
        serial = sweep.sweep_task(task, label, root, configurations, workers=1, ranking_receipt=receipt)
        parallel = sweep.sweep_task(task, label, root, configurations, workers=2, ranking_receipt=receipt)

    assert parallel == serial
