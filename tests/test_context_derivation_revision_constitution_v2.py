from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "experiments" / "context-derivation" / "revision_constitution_v2.py"
SPEC = importlib.util.spec_from_file_location("revision_constitution_v2", PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_revision_scoped_draft_is_complete_and_not_an_execution_approval() -> None:
    manifest, gold = module.load_draft()
    assert manifest["status"] == "DRAFT-PENDING-OWNER-REVIEW"
    assert gold["approval_status"] == "DRAFT-PENDING-OWNER-REVIEW"
    labels = {row["task_id"]: row for row in gold["tasks"]}
    assert len(labels["CTX-06"]["required_constitution_bindings"]) == 2
    assert {item["adr_id"] for item in labels["CTX-09"]["required_constitution_bindings"]} == {"adr_shared_cache", "adr_shared_audit"}
    assert labels["CTX-12"]["required_constitution_bindings"] == []
