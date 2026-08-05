from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "experiments" / "context-derivation" / "topk_metrics_v2.py"
SPEC = importlib.util.spec_from_file_location("topk_metrics_v2", MODULE_PATH)
assert SPEC and SPEC.loader
topk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(topk)


D1 = "mse_alpha123:d1"
D2 = "mse_bravo234:d1"
D3 = "mse_charlie345:d2"
D4 = "mse_delta456:d1"
D5 = "mse_echo567:d1"


def _gold() -> dict[str, object]:
    return {
        "required_decision_refs": [D2, D3],
        "required_adr_ids": ["adr_storage", "adr_sync"],
        "required_constitution_refs": ["constitution:v1#local-first", "constitution:v1#durability"],
    }


def _memberships() -> dict[str, list[str]]:
    return {
        D1: ["adr_distractor"],
        D2: ["adr_storage"],
        D3: ["adr_sync"],
        D4: ["adr_related_only"],
        D5: ["adr_weak"],
    }


def _bindings() -> dict[str, list[str]]:
    return {
        "adr_storage": ["constitution:v1#local-first"],
        "adr_sync": ["constitution:v1#durability"],
        "adr_distractor": ["constitution:v1#noise"],
        "adr_related_only": ["constitution:v1#related"],
        "adr_weak": ["constitution:v1#weak"],
    }


def test_metrics_measure_decision_adr_and_constitution_recall_at_each_supported_k() -> None:
    result = topk.measure_top_k(
        [
            {"decision_ref": D1, "relevance": "strong"},
            {"decision_ref": D2, "relevance": "strong"},
            {"decision_ref": D3, "relevance": "strong"},
            {"decision_ref": D4, "relevance": "strong", "relation_type": "related"},
            {"decision_ref": D5, "relevance": "weak"},
        ],
        _gold(), adr_membership=_memberships(), constitution_bindings=_bindings(),
    )

    assert result["schema"] == "context-top-k-metrics.v2"
    assert result["k_values"] == [1, 2, 3, 5, 8]
    assert result["first_hit_rank"] == 2
    assert result["mrr"] == 0.5
    assert result["metrics"]["1"]["decision_recall"] == {"hits": 0, "required": 2, "rate": 0.0}
    assert result["metrics"]["2"]["adr_trigger_recall"] == {"hits": 1, "required": 2, "rate": 0.5}
    assert result["metrics"]["3"]["constitution_binding_recall"] == {
        "hits": 2, "required": 2, "rate": 1.0
    }
    assert result["metrics"]["1"]["mrr_at_k"] == 0.0
    assert result["metrics"]["2"]["mrr_at_k"] == 0.5


def test_only_strong_canonical_non_related_rows_expand_to_adrs() -> None:
    result = topk.measure_top_k(
        [
            {"decision_ref": D2, "relevance": "strong"},
            {"decision_ref": D4, "relevance": "strong", "relation_type": "related"},
            {"decision_ref": D5, "relevance": "weak"},
        ],
        {
            "required_decision_refs": [D2],
            "required_adr_ids": ["adr_storage"],
            "required_constitution_refs": ["constitution:v1#local-first"],
        },
        adr_membership=_memberships(), constitution_bindings=_bindings(),
    )

    cell = result["metrics"]["5"]
    assert cell["expanded_decision_refs"] == [D2]
    assert cell["selected_adr_ids"] == ["adr_storage"]
    assert cell["selected_constitution_refs"] == ["constitution:v1#local-first"]
    assert cell["false_expansion"] == {
        "invalid_decision_refs": [],
        "suppressed_decision_refs": [D4, D5],
        "attempted": 1,
        "count": 0,
        "rate": 0.0,
    }


def test_instrumented_weak_none_and_related_expansions_are_false_and_never_contribute_recall() -> None:
    result = topk.measure_top_k(
        [
            {"decision_ref": D2, "relevance": "strong"},
            {"decision_ref": D4, "relevance": "strong", "relation_type": "related"},
            {"decision_ref": D5, "relevance": "weak"},
            {"decision_ref": D1, "relevance": "none"},
        ],
        {
            "required_decision_refs": [D2],
            "required_adr_ids": ["adr_storage", "adr_related_only", "adr_weak"],
            "required_constitution_refs": [
                "constitution:v1#local-first", "constitution:v1#related", "constitution:v1#weak",
            ],
        },
        adr_membership=_memberships(), constitution_bindings=_bindings(),
        expanded_decision_refs=[D2, D4, D5, D1],
    )

    cell = result["metrics"]["5"]
    assert cell["expanded_decision_refs"] == [D2]
    assert cell["adr_trigger_recall"] == {"hits": 1, "required": 3, "rate": pytest.approx(1 / 3)}
    assert cell["false_expansion"] == {
        "invalid_decision_refs": [D1, D4, D5],
        "suppressed_decision_refs": [],
        "attempted": 4,
        "count": 3,
        "rate": 0.75,
    }


def test_validation_rejects_noncanonical_duplicate_and_unsupported_k_values() -> None:
    with pytest.raises(ValueError, match="canonical"):
        topk.measure_top_k(
            [{"decision_ref": "not-a-decision", "relevance": "strong"}],
            _gold(), adr_membership=_memberships(), constitution_bindings=_bindings(),
        )
    with pytest.raises(ValueError, match="duplicate"):
        topk.measure_top_k(
            [{"decision_ref": D1, "relevance": "strong"}, {"decision_ref": D1, "relevance": "strong"}],
            _gold(), adr_membership=_memberships(), constitution_bindings=_bindings(),
        )
    with pytest.raises(ValueError, match="unsupported"):
        topk.measure_top_k(
            [{"decision_ref": D1, "relevance": "strong"}],
            _gold(), adr_membership=_memberships(), constitution_bindings=_bindings(), k_values=[4],
        )
    with pytest.raises(ValueError, match="absent"):
        topk.measure_top_k(
            [{"decision_ref": D1, "relevance": "strong"}],
            _gold(), adr_membership=_memberships(), constitution_bindings=_bindings(),
            expanded_decision_refs=[D2],
        )


def test_empty_gold_dimensions_are_explicitly_not_scored() -> None:
    result = topk.measure_top_k(
        [{"decision_ref": D1, "relevance": "strong"}],
        {
            "required_decision_refs": [],
            "required_adr_ids": [],
            "required_constitution_refs": [],
        },
        adr_membership=_memberships(), constitution_bindings=_bindings(),
    )
    assert result["first_hit_rank"] is None
    assert result["mrr"] == 0.0
    assert result["metrics"]["1"]["decision_recall"]["rate"] is None
    assert result["metrics"]["1"]["adr_trigger_recall"]["rate"] is None
    assert result["metrics"]["1"]["constitution_binding_recall"]["rate"] is None
