"""Keep the published Reflection guide aligned with executable public schemas."""
import contextlib
import io
import re
from pathlib import Path

import pytest

from memory_seed.cli import main
from memory_seed.mcp_server import TOOLS

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/4_Reference/reflection-board-v1-operator-guide.md"
TEXT = GUIDE.read_text(encoding="utf-8")
CLI_ROWS = re.findall(r"^\| `(reflection [^`]+)` \| ([^|]+) \|", TEXT, re.MULTILINE)
MCP_ROWS = re.findall(r"^\| `(memory_reflection_[^`]+)` \| ([^|]+) \|", TEXT, re.MULTILINE)


@pytest.mark.parametrize("command,inputs", CLI_ROWS, ids=[row[0] for row in CLI_ROWS])
def test_documented_cli_command_and_all_flags_match_parser(command, inputs):
    output = io.StringIO()
    with contextlib.redirect_stdout(output), pytest.raises(SystemExit) as stopped:
        main([*command.split(), "--help"])
    assert stopped.value.code == 0
    actual = set(re.findall(r"--[a-z][a-z-]*", output.getvalue())) - {"--help", "--json", "--apply"}
    documented = set(re.findall(r"--[a-z][a-z-]*", inputs))
    assert actual == documented


def test_guide_covers_every_public_reflection_operation():
    assert {command for command, _ in CLI_ROWS} == {
        "reflection trust init", "reflection board view",
        *(f"reflection ledger {name}" for name in
          ("init", "append", "view", "check", "close", "rebind", "prepare", "finalize", "expire")),
    }
    actual = {tool["name"]: tool for tool in TOOLS if tool["name"].startswith("memory_reflection_")}
    assert {name for name, _ in MCP_ROWS} == set(actual)
    for name, fields in MCP_ROWS:
        documented = re.findall(r"`([a-z_]+)`", fields)
        assert set(documented) == set(actual[name]["inputSchema"].get("required", []))
        assert actual[name]["inputSchema"]["additionalProperties"] is False
    assert "memory_reflection_trust_init" not in actual
    assert "memory_reflection_ledger_prepare" not in actual


@pytest.mark.parametrize("name", ["agent_collaboration.md", "session_logging.md", "end_of_turn.md"])
def test_reflection_runbooks_are_present_and_byte_identical_in_seed(name):
    live = ROOT / ".memory-seed/skills" / name
    seed = ROOT / "memory_seed/seed/.memory-seed/skills" / name
    assert live.read_bytes() == seed.read_bytes()
    assert "Reflection Board" in live.read_text(encoding="utf-8")


def test_reflection_registry_routes_have_matching_live_and_seed_rules():
    for prefix in (".memory-seed", "memory_seed/seed/.memory-seed"):
        registry = (ROOT / prefix / "skills/index.md").read_text(encoding="utf-8")
        for phrase in (
            "initializing, appending, inspecting, rebinding, or preparing/finalizing a Reflection Board v1",
            "preparing or finalizing ordinary session receipts for Reflection Board v1 close",
            "closing or expiring a Reflection Board v1 chain",
        ):
            assert phrase in registry


def test_guidance_preserves_lifecycle_and_recovery_limits():
    for phrase in (
        "retention-extension authoring is planned",
        "closed_receipts_pending",
        "immutable",
        "new ordinary entry",
        "single-use handoff",
        "same tip cannot be prepared twice",
        "already-integrated ledger",
        "Legacy pre-proof close",
        "not cryptographic erasure",
        "not constant-time",
        "prototype has no",
    ):
        assert phrase.casefold() in TEXT.casefold()
    audit = (ROOT / "docs/3_Spec/functionality-audit.md").read_text(encoding="utf-8")
    storyline = (ROOT / "docs/1_Inbox/agent-interaction-storylines-review.md").read_text(encoding="utf-8")
    assert "public lifecycle (implemented; first-board evaluation planned)" in audit
    assert "The public workflow is **implemented in the current source tree**" in storyline
    assert f"**MCP ({len(TOOLS)}):**" in storyline
    assert "(planned public surface)" not in storyline
    assert "Public `reflection` CLI/MCP adapters, ESR reporting, hook/runbook guidance" not in audit
    for unsupported in ("reflection board view --active", "reflection ledger view --workstream"):
        assert unsupported not in TEXT


@pytest.mark.parametrize("path", [
    "docs/4_Reference/reflection-board-v1-operator-guide.md",
    ".memory-seed/skills/agent_collaboration.md",
    "memory_seed/seed/.memory-seed/skills/agent_collaboration.md",
])
def test_hook_guidance_distinguishes_admission_from_message_inspection(path):
    text = " ".join((ROOT / path).read_text(encoding="utf-8").split())
    assert "Invented Reflection trailers cannot grant admission or bypass reserved-family checks" in text
    assert "ordinary commits without reserved paths may not read the message" in text
    assert "invented Reflection trailers are refused" not in text
    assert "or invented trailers is refused" not in text


@pytest.mark.parametrize("path", [
    "docs/4_Reference/reflection-board-v1-operator-guide.md",
    ".memory-seed/skills/session_logging.md",
    "memory_seed/seed/.memory-seed/skills/session_logging.md",
])
def test_receipt_status_guidance_requires_json_output(path):
    text = " ".join((ROOT / path).read_text(encoding="utf-8").split())
    assert (
        "`memory-seed reflection ledger check <workstream_id> --json` "
        "to inspect `closed_receipts_pending` and `missing_receipts`"
    ) in text
    assert "non-JSON ledger view/check prints raw ledger text" in text
