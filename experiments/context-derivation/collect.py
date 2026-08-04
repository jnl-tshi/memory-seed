"""Normalize raw Claude/Codex streams without reading gold labels."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent; RUNS = HERE / "runs"; sys.path.insert(0, str(HERE))
from contracts import ANSWER_SCHEMA, RUN_SCHEMA, require_schema, validate_answer  # noqa: E402
from mcp_wrapper import allowed_names  # noqa: E402

SUMMARY_SCHEMA = "context-run-summary.v1"
SMOKE_EXCLUSION = "unscored_or_smoke_artifact"
_JSON_OBJECT = re.compile(r"\{.*\}", re.S)
_EVIDENCE_REF = re.compile(r"\b(?:mse_[a-z0-9]+:d[0-9]+|adr_[a-z0-9_]+)\b", re.I)


def events(path: Path) -> list[dict[str, Any]]:
    output = []
    if not path.exists(): return output
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            value = json.loads(line)
            if isinstance(value, dict): output.append(value)
        except json.JSONDecodeError: continue
    return output


def transcript_tool_calls(raw_events: list[dict[str, Any]]) -> list[str]:
    found = []
    for event in raw_events:
        item = event.get("item") or {}
        item_type = str(item.get("type", ""))
        if item_type == "mcp_tool_call": found.append(str(item.get("tool", "")))
        elif item_type and any(marker in item_type for marker in ("tool", "command", "file", "function_call", "web_search")):
            found.append(item_type)
        for block in (event.get("message") or {}).get("content", []):
            if block.get("type") == "tool_use": found.append(str(block.get("name", "")))
    return found


def transcript_evidence(raw_events: list[dict[str, Any]], *, limit: int = 12000) -> tuple[str, list[str]]:
    """Extract observable tool results only; prompts and model prose are not evidence."""
    chunks: list[str] = []
    for event in raw_events:
        item = event.get("item") or {}
        if item.get("type") == "mcp_tool_call" and item.get("result") is not None:
            chunks.append(json.dumps(item.get("result"), ensure_ascii=False))
        for block in (event.get("message") or {}).get("content", []):
            if block.get("type") != "tool_result":
                continue
            content = block.get("content", "")
            if isinstance(content, list):
                chunks.extend(str(part.get("text", "")) for part in content if isinstance(part, dict))
            else:
                chunks.append(str(content))
    excerpt = "\n".join(chunk for chunk in chunks if chunk)[:limit]
    return excerpt, sorted(set(_EVIDENCE_REF.findall(excerpt)))


def usage(raw_events: list[dict[str, Any]]) -> dict[str, Any]:
    input_tokens = output_tokens = None; cost = None
    for event in raw_events:
        source = event.get("usage") or event.get("response", {}).get("usage") or {}
        if source:
            input_tokens = source.get("input_tokens", source.get("prompt_tokens", input_tokens))
            output_tokens = source.get("output_tokens", source.get("completion_tokens", output_tokens))
            cost = source.get("cost_usd", source.get("cost", cost))
    return {"input_tokens": input_tokens, "output_tokens": output_tokens, "cost_usd": cost}


def parse_answer(text: str) -> dict[str, Any] | None:
    candidates = [text]
    candidates.extend(match.group(0) for match in _JSON_OBJECT.finditer(text))
    for candidate in reversed(candidates):
        try: value = json.loads(candidate)
        except json.JSONDecodeError: continue
        if isinstance(value, dict) and value.get("schema") == ANSWER_SCHEMA:
            try:
                require_schema(value, ANSWER_SCHEMA)
                return validate_answer(value)
            except ValueError:
                continue
    return None


def analyse_run(run_dir: Path) -> dict[str, Any]:
    defaults = {"run_id": run_dir.name, "task_id": None, "arm": None, "agent": None, "repetition": None,
                "answer": None, "included_refs": [], "evidence_excerpt": "", "context_token_proxy": None, "duration_ms": None,
                "input_tokens": None, "output_tokens": None, "cost_usd": None, "tool_calls": [],
                "model": None, "cli_version": None, "parent_isolated": None, "fixture_isolated": None,
                "protocol_failure": None, "harness_failure": None, "exclusion_reason": None}
    manifest_path = run_dir / "RUN_MANIFEST.json"
    if not manifest_path.exists():
        defaults.update(protocol_failure="missing_manifest", exclusion_reason="incomplete")
        return defaults
    try: manifest = json.loads(manifest_path.read_text(encoding="utf-8")); require_schema(manifest, RUN_SCHEMA)
    except (json.JSONDecodeError, ValueError):
        defaults.update(protocol_failure="invalid_manifest", exclusion_reason="incomplete")
        return defaults
    raw = events(run_dir / manifest.get("transcript", "transcript.jsonl"))
    final_path = run_dir / manifest.get("final_answer", "final_answer.txt")
    final = final_path.read_text(encoding="utf-8", errors="replace") if final_path.exists() else ""
    calls = transcript_tool_calls(raw)
    for call in manifest.get("tool_calls") or []:
        if call not in calls:
            calls.append(call)
    evidence_excerpt, observed_refs = transcript_evidence(raw)
    arm = str(manifest.get("arm", ""))
    allowed = set(allowed_names(arm)) if arm in {"search-mcp", "adr-mcp-workflow"} else set()
    unallowed = sorted(set(manifest.get("undeclared_tool_calls") or ()) | (set(calls) - allowed))
    protocol: list[str] = []
    if manifest.get("scored") is not True or manifest.get("smoke") is True:
        protocol.append(SMOKE_EXCLUSION)
    if not raw: protocol.append("missing_or_unparseable_transcript")
    if unallowed: protocol.append("undeclared_tool_call")
    if manifest.get("direct_filesystem_retrieval"): protocol.append("direct_filesystem_retrieval")
    if manifest.get("parent_isolated") is False: protocol.append("parent_isolation_failure")
    if manifest.get("fixture_isolated") is False: protocol.append("fixture_isolation_failure")
    parsed = parse_answer(final)
    if parsed is None and not manifest.get("failure_classification"): protocol.append("invalid_or_missing_answer")
    tokens = usage(raw)
    included_refs = sorted(set(manifest.get("included_refs") or ()) | set(observed_refs))
    defaults.update({"run_id": manifest["run_id"], "task_id": manifest["task_id"], "arm": manifest["arm"], "agent": manifest["agent"], "repetition": manifest["repetition"], "answer": parsed, "included_refs": included_refs, "evidence_excerpt": evidence_excerpt, "context_token_proxy": manifest.get("context_token_proxy"), "duration_ms": manifest.get("duration_ms"), "tool_calls": calls, "model": manifest.get("model"), "cli_version": manifest.get("cli_version"), "parent_isolated": manifest.get("parent_isolated"), "fixture_isolated": manifest.get("fixture_isolated"), "protocol_failure": ";".join(protocol) or None, "harness_failure": manifest.get("failure_classification")})
    defaults.update(tokens)
    if defaults["harness_failure"]: defaults["exclusion_reason"] = defaults["harness_failure"]
    elif defaults["protocol_failure"]: defaults["exclusion_reason"] = defaults["protocol_failure"]
    return defaults


def collect(runs: Path = RUNS) -> dict[str, Any]:
    rows = []
    for path in sorted(runs.iterdir()) if runs.exists() else ():
        if not path.is_dir():
            continue
        row = analyse_run(path)
        failures = set(str(row.get("protocol_failure") or "").split(";"))
        if SMOKE_EXCLUSION not in failures:
            rows.append(row)
    return {"schema": SUMMARY_SCHEMA, "runs": rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--runs", default=str(RUNS)); parser.add_argument("--output")
    args = parser.parse_args(argv); result = collect(Path(args.runs)); output = Path(args.output) if args.output else Path(args.runs) / "summary.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8"); print(output)
    return 0


if __name__ == "__main__": raise SystemExit(main())
