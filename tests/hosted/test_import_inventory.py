from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hosted.importing.inventory import build_inventory, load_json_yaml, validate_inventory


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "hosted_import"


def _contracts() -> tuple[dict, dict]:
    return (
        load_json_yaml(ROOT / "hosted" / "importing" / "crosswalk.yaml"),
        load_json_yaml(ROOT / "hosted" / "importing" / "actors.yaml"),
    )


def test_live_corpus_has_no_unclassified_fields_or_actors() -> None:
    crosswalk, actors = _contracts()
    inventory = build_inventory(ROOT)
    result = validate_inventory(inventory, crosswalk, actors)

    assert result["unknown_fields"] == []
    assert result["unknown_actors"] == []
    assert result["missing_required_families"] == []
    assert inventory["counts"]["session_entries"] > 1_000
    assert inventory["counts"]["adrs"] > 50


def test_crosswalk_is_a_total_explicit_classification_contract() -> None:
    crosswalk, actors = _contracts()
    entries = crosswalk["fields"]
    sources = [entry["source"] for entry in entries]

    assert len(sources) == len(set(sources))
    assert all(entry["classification"] and entry["rationale"] for entry in entries)
    assert all(
        entry["target"] is not None or entry["classification"] == "structural_container"
        for entry in entries
    )
    assert actors["status"] == "complete"
    assert crosswalk["status"] == "complete"


def test_inventory_snapshot_matches_the_live_field_and_actor_vocabulary() -> None:
    snapshot = json.loads(
        (ROOT / "hosted" / "importing" / "inventory.json").read_text(encoding="utf-8")
    )
    live = build_inventory(ROOT)

    assert snapshot["observed_fields"] == live["observed_fields"]
    assert snapshot["observed_actors"] == live["observed_actors"]
    assert snapshot["observed_actor_counts"] == live["observed_actor_counts"]


def test_representative_fixture_is_complete_and_hash_locked() -> None:
    manifest = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))
    actual = {}
    for relative_path, expected_digest in manifest["files"].items():
        payload = (FIXTURE_ROOT / relative_path).read_bytes()
        actual[relative_path] = hashlib.sha256(payload).hexdigest()
        assert actual[relative_path] == expected_digest

    assert set(manifest["coverage"]) == {
        "archive-snapshot",
        "constitution",
        "legacy-session",
        "living-adr",
        "project-actors",
        "session-diagram-sidecar",
        "session-link-sidecar",
        "session-topic-sidecar",
        "topic-catalog",
        "typed-session",
    }

    crosswalk, actors = _contracts()
    result = validate_inventory(build_inventory(FIXTURE_ROOT / "source"), crosswalk, actors)
    assert result["unknown_fields"] == []
    assert result["unknown_actors"] == []
    assert result["missing_required_families"] == []


def test_unknown_field_negative_control_proves_the_detector(tmp_path: Path) -> None:
    source = tmp_path / ".memory-seed" / "sessions" / "2026-01"
    source.mkdir(parents=True)
    (source / "2026-01-01.md").write_text(
        """---
tags:
  - session-log
---

## 2026-01-01 00:00 - Negative control

---
entry_id: mse_0000000000000000
user_initials: JNL
agent_type: codex
unclassified_probe: true
---

#### D1 - Documentation: Detector fixture

- **Scope:** test-only
- **D:** The detector must reject unknown fields.
- **F:** Synthetic negative control.
""",
        encoding="utf-8",
    )

    crosswalk, actors = _contracts()
    result = validate_inventory(build_inventory(tmp_path), crosswalk, actors)

    assert result["unknown_fields"] == ["sessions.entry.unclassified_probe"]
