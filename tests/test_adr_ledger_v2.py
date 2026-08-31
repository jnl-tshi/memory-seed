from dataclasses import replace
from pathlib import Path

import pytest

from memory_seed._adr_ledger_v2_migration import convert_record
from memory_seed.adr import _v2_body_issues, parse_adr, parse_adr_text, reconcile_adr_records, render_adr, validate_adr


ROOT = Path(__file__).resolve().parents[1]


def _v2_text() -> str:
    record = parse_adr(ROOT / ".memory-seed" / "decisions" / "adr_session_decision_authority.md")
    return render_adr(convert_record(record))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda text: text.replace("#### Reason", "#### Why", 1),
        lambda text: text.replace("#### Impact", "", 1),
        lambda text: text.replace("#### Reason", "#### Impact", 1).replace("#### Impact", "#### Reason", 1),
        lambda text: text.replace("#### Impact", "#### Unknown", 1),
        lambda text: text.replace("#### Decision", "unframed prose\n\n#### Decision", 1),
        lambda text: text.replace("```\n\n#### Decision", "```\n\n```json\n{}\n```\n\n#### Decision", 1),
    ],
)
def test_v2_rejects_noncanonical_event_bodies(mutate):
    issues = _v2_body_issues(mutate(_v2_text()).split("### revision-proposed", 1)[1])
    assert issues


def test_v2_round_trip_and_impact_provenance_requirements():
    parsed = parse_adr_text(_v2_text())
    assert parsed.schema_version == 2
    assert render_adr(parsed) == _v2_text()
    assert validate_adr(parsed, ROOT) == []

    invalid = replace(parsed.events[0], impact_provenance="reconstructed", impact_evidence=())
    bad = replace(parsed, events=[invalid, *parsed.events[1:]])
    assert any("reconstructed Impact requires direct evidence" in issue for issue in validate_adr(bad, ROOT))


def test_v1_reader_remains_available_without_normalizing_history():
    source = ROOT / ".memory-seed" / "decisions" / "adr_session_decision_authority.md"
    parsed = parse_adr(source)
    assert parsed.schema_version == 1
    assert render_adr(parsed) == source.read_text(encoding="utf-8")


def test_reconciler_accepts_only_the_exact_one_time_v1_to_v2_projection():
    legacy = parse_adr(PREIMAGE)
    migrated = convert_record(legacy)
    merged, issues = reconcile_adr_records(legacy, migrated)
    assert issues == []
    assert merged is migrated

    altered = replace(migrated.events[0], impact="An invented outcome.")
    merged, issues = reconcile_adr_records(legacy, replace(migrated, events=[altered, *migrated.events[1:]]))
    assert merged is None
    assert any("diverges" in issue for issue in issues)
