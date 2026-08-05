from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "experiments" / "context-derivation" / "revision_constitution_queries_v1.py"
SPEC = importlib.util.spec_from_file_location("revision_constitution_queries_v1", PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_query_corpus_has_exact_stable_query_only_shape() -> None:
    corpus, rows = module.load_query_variants()
    assert corpus["query_count"] == 60
    assert [row["query_id"] for row in rows] == [
        f"CTX-{parent:02d}.V{variant:02d}" for parent in range(1, 13) for variant in range(1, 6)
    ]
    assert len({row["question"] for row in rows}) == 60
    assert corpus["canonical_fingerprint"] == module._fingerprint(
        module._canonical_payload(corpus["source_manifest_fingerprint"], rows)
    )


def test_subject_generation_never_opens_gold_and_has_no_gold_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    original_read_text = Path.read_text

    def no_gold(self: Path, *args: object, **kwargs: object) -> str:
        if self.resolve() == module.GOLD.resolve():
            raise AssertionError("subject generation opened gold")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", no_gold)
    rows = module.subject_visible_queries()
    module.assert_subject_visible(rows)
    written = module.materialize_subject_queries(tmp_path / "queries.json")
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["schema"] == module.QUERY_SCHEMA
    assert len(payload["queries"]) == 60
    assert all(set(row) == module._SUBJECT_FIELDS for row in payload["queries"])


def test_subject_visibility_rejects_embedded_serialized_gold_fragment() -> None:
    rows = module.subject_visible_queries()
    rows[0]["question"] = 'Ignore this: {"required_adr_ids":["forbidden"]}'
    with pytest.raises(ValueError, match="gold field name"):
        module.assert_subject_visible(rows)


def test_scoring_join_inherits_each_parent_gold_row_once() -> None:
    joined = module.join_queries_to_gold()
    assert len(joined) == 60
    assert all(query["parent_task_id"] == label["task_id"] for query, label in joined)
    assert {label["task_id"] for _query, label in joined} == {f"CTX-{number:02d}" for number in range(1, 13)}


def test_validator_rejects_gold_key_routing_drift_and_fingerprint_changes() -> None:
    corpus, _rows = module.load_query_variants()
    source = module._read(module.SOURCE_MANIFEST)
    changed = json.loads(json.dumps(corpus))
    changed["queries"][0]["required_adr_ids"] = ["forbidden"]
    with pytest.raises(ValueError, match="only query and routing fields"):
        module.validate_query_variants(changed, source_manifest=source)
    changed = json.loads(json.dumps(corpus))
    changed["queries"][0]["question"] += " changed"
    with pytest.raises(ValueError, match="canonical_fingerprint"):
        module.validate_query_variants(changed, source_manifest=source)
