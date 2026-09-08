"""CLI and MCP consume the same reflection operation contract."""
import json
import pytest

from memory_seed.cli import main
from memory_seed.mcp_server import call_tool, TOOLS
from memory_seed.reflection_operations import run_reflection_operation
from test_reflection_workstream_ledger import _planned_transaction, _transaction_state


@pytest.mark.parametrize("tool,arguments", [
    ("memory_reflection_ledger_init", {"apply": "false"}),
    ("memory_reflection_ledger_append", {"workstream_id": "w", "role": "planner", "conclusion": "a",
        "reasoning": "b", "source": "c", "no_related_thread": "true"}),
    ("memory_reflection_ledger_close", {"workstream_id": "w", "chain_id": "c", "apply": "false"}),
    ("memory_reflection_board_view", {"unknown": 1}),
    ("memory_reflection_ledger_init", []),
])
def test_mcp_rejects_invalid_arguments_identically(tool, arguments):
    result = call_tool(tool, arguments)
    assert result == run_reflection_operation(tool.removeprefix("memory_reflection_"), arguments)
    assert result["error"]["code"] == "invalid_arguments"


def test_close_schema_and_cli_preview_parity(tmp_path, monkeypatch, capsys):
    root, _, context = _planned_transaction(tmp_path, "close")
    monkeypatch.chdir(root)
    args = dict(workstream_id=context["close_kwargs"]["workstream_id"], chain_id=context["chain"])
    before = _transaction_state(root)
    expected = call_tool("memory_reflection_ledger_close", args)
    assert main(["reflection", "ledger", "close", args["workstream_id"], "--chain-id", args["chain_id"], "--json"]) == 0
    actual = json.loads(capsys.readouterr().out)
    assert actual == expected
    assert _transaction_state(root) == before
    schema = next(tool for tool in TOOLS if tool["name"] == "memory_reflection_ledger_close")["inputSchema"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["apply"]["type"] == "boolean"
    locator = {key: value for key, value in context["receipt_locator"].items() if key != "chain_id"}
    assert main(["reflection", "ledger", "close", args["workstream_id"], "--chain-id", args["chain_id"],
                 "--receipts", json.dumps([locator]), "--apply", "--json"]) == 0
    applied = json.loads(capsys.readouterr().out)
    assert applied["applied"] and applied["status"] == "closed_receipts_pending"
    assert call_tool("memory_reflection_ledger_close", args)["missing_receipts"] == applied["missing_receipts"]


def test_cli_init_preview_identity_and_malformed_close_json(tmp_path, monkeypatch, capsys):
    root, _, _ = _planned_transaction(tmp_path, "init")
    monkeypatch.chdir(root)
    assert main(["reflection", "ledger", "init", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["workstream_id"].startswith("rwl_")
    assert main(["reflection", "ledger", "close", "w", "--chain-id", "c", "--receipts", "{bad", "--json"]) == 1
    assert json.loads(capsys.readouterr().err)["error"]["code"] == "invalid_arguments"


@pytest.mark.parametrize("operation", ["rebind", "finalize"])
@pytest.mark.parametrize("extra", [{"apply": "false"}, {"token": "raw"}, {"target_branch": "main"},
                                  {"source_tip": "0" * 40}, {"expected_head": "0" * 40}, {"unknown": True}])
def test_rebind_mcp_strict_locator_contract(operation, extra):
    args = dict(workstream_id="w", source="feature", reason="integration", **extra)
    result = call_tool("memory_reflection_ledger_" + operation, args)
    assert result == run_reflection_operation("ledger_" + operation, args)
    assert result["error"]["code"] == "invalid_arguments"
    schema = next(tool["inputSchema"] for tool in TOOLS if tool["name"] == "memory_reflection_ledger_" + operation)
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == {"cwd", "workstream_id", "source", "reason", "apply"}
    assert schema["properties"]["apply"]["type"] == "boolean"


def test_rebind_cli_mcp_parity_and_prepare_stays_cli_only(tmp_path, monkeypatch, capsys):
    from test_reflection_operations import _public_rebind_fixture, _merge_public_source
    root, args, _ = _public_rebind_fixture(tmp_path)
    _merge_public_source(root, args)
    monkeypatch.chdir(root)
    expected = call_tool("memory_reflection_ledger_rebind", args)
    assert expected["ok"], expected
    assert main(["reflection", "ledger", "rebind", args["workstream_id"], "--source", args["source"],
                 "--reason", args["reason"], "--json"]) == 0
    actual = json.loads(capsys.readouterr().out)
    for key in ("ok", "operation", "applied", "workstream_id", "head", "pre_ledger_digest", "integration_commit"):
        assert actual[key] == expected[key]
    assert not any(tool["name"] == "memory_reflection_ledger_prepare" for tool in TOOLS)
    assert main(["reflection", "ledger", "rebind", args["workstream_id"], "--source", args["source"],
                 "--reason", args["reason"], "--apply", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["applied"]


@pytest.mark.parametrize("operation", ["prepare", "finalize"])
def test_pr_cli_delegates_locator_inputs_to_facade(operation, monkeypatch, capsys):
    from memory_seed import reflection_operations
    captured = []

    def capture(name, fields):
        captured.append((name, fields))
        return {"ok": True, "applied": fields["apply"]}

    monkeypatch.setattr(reflection_operations, "run_reflection_operation", capture)
    command = ["reflection", "ledger", operation, "workstream", "--apply", "--json"]
    expected = {"workstream_id": "workstream", "apply": True}
    if operation == "finalize":
        command += ["--source", "refs/heads/feature", "--reason", "merged"]
        expected.update(source="refs/heads/feature", reason="merged")
    assert main(command) == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True, "applied": True}
    assert captured == [("ledger_" + operation, expected)]


@pytest.mark.parametrize("option", ["--token", "--target-branch", "--source-tip", "--expected-head"])
def test_finalize_cli_rejects_authority_overrides(option):
    with pytest.raises(SystemExit) as exc:
        main(["reflection", "ledger", "finalize", "w", "--source", "feature", "--reason", "merged", option, "raw"])
    assert exc.value.code == 2
