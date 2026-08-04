"""Run isolated, unscored provider probes before freezing the live matrix."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from contracts import canonical_json
from run import (
    REPO_ROOT, build_command, installed_cli_version, redact_output,
    sanitize_subject_artifacts, subject_environment, subject_isolation,
)

PROMPT = 'Return only this JSON object and do not use tools: {"probe":"ok"}'


def codex_catalog_slugs() -> set[str]:
    executable = shutil.which("codex") or "codex"
    completed = subprocess.run(
        [executable, "debug", "models", "--bundled"], capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=30,
        env=subject_environment(),
    )
    if completed.returncode != 0:
        raise RuntimeError(f"codex bundled model catalog failed: {redact_output(completed.stderr).strip()}")
    payload = json.loads(completed.stdout)
    rows = payload.get("models", payload) if isinstance(payload, dict) else payload
    return {str(item["slug"]) for item in rows if isinstance(item, dict) and item.get("slug")}


def claude_models(transcript: str) -> set[str]:
    models: set[str] = set()
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init" and event.get("model"):
            models.add(str(event["model"]))
        usage = event.get("modelUsage") or event.get("model_usage") or {}
        if isinstance(usage, dict):
            models.update(str(key) for key in usage)
    return models


def claude_primary_models(transcript: str) -> set[str]:
    models: set[str] = set()
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init" and event.get("model"):
            models.add(str(event["model"]))
    return models


def _outside_repo(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return resolved
    raise ValueError("probe output must be outside the repository")


def run_probe(
    *, agent: str, model: str, cli_version: str, effort: str | None,
    output: Path, repetitions: int = 2,
) -> dict[str, object]:
    if repetitions != 2:
        raise ValueError("the frozen probe contract requires exactly two observations")
    output = _outside_repo(output)
    if output.exists():
        raise FileExistsError(output)
    raw_before, normalized_before = installed_cli_version(agent)
    if normalized_before != cli_version:
        raise ValueError(
            f"installed {agent} CLI {normalized_before!r} does not match requested pin {cli_version!r}"
        )
    if agent == "codex" and model not in codex_catalog_slugs():
        raise ValueError(f"Codex model must be one canonical bundled catalog slug: {model!r}")
    staging = Path(tempfile.mkdtemp(prefix=f"context-probe-{agent}-")).resolve()
    observations: list[dict[str, object]] = []
    try:
        for repetition in range(1, repetitions + 1):
            work = staging / f"observation-{repetition}"
            work.mkdir()
            command = build_command(
                agent, work, PROMPT, arm="adr-candidate-packet", fixture=None,
                model=model, effort=effort,
            )
            completed = subprocess.run(
                command, cwd=work, env=subject_environment(), capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=300,
            )
            sanitize_subject_artifacts(work)
            transcript = redact_output(completed.stdout)
            stderr = redact_output(completed.stderr)
            (work / "transcript.jsonl").write_text(transcript, encoding="utf-8")
            if stderr:
                (work / "stderr.log").write_text(stderr, encoding="utf-8")
            if completed.returncode != 0:
                detail = stderr.strip() or transcript.strip() or "no provider output"
                raise RuntimeError(
                    f"{agent} probe {repetition} failed with exit {completed.returncode}: {detail}"
                )
            used_models = claude_models(transcript) if agent == "claude" else {model}
            primary_models = claude_primary_models(transcript) if agent == "claude" else {model}
            resolved = primary_models or used_models
            if len(resolved) != 1:
                raise RuntimeError(
                    f"{agent} probe {repetition} did not resolve one primary model: {sorted(resolved)}"
                )
            observations.append({
                "repetition": repetition,
                "resolved_model": next(iter(resolved)),
                "observed_models": sorted(used_models),
                "exit_code": completed.returncode,
                "transcript": f"observation-{repetition}/transcript.jsonl",
                "command": ["<prompt>" if value == PROMPT else value for value in command],
            })
        raw_after, normalized_after = installed_cli_version(agent)
        models = {str(item["resolved_model"]) for item in observations}
        if normalized_after != normalized_before or raw_after != raw_before:
            raise RuntimeError(f"{agent} CLI version changed during probes")
        if len(models) != 1:
            raise RuntimeError(f"{agent} model resolution changed during probes: {sorted(models)}")
        manifest: dict[str, object] = {
            "schema": "context-provider-probe.v1",
            "agent": agent,
            "requested_model": model,
            "resolved_model": next(iter(models)),
            "cli_version": normalized_before,
            "cli_version_raw": raw_before,
            "subject_isolation": subject_isolation(agent),
            "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "scored": False,
            "task_id": None,
            "gold_used": False,
            "observations": observations,
        }
        manifest["fingerprint"] = __import__("contracts").fingerprint(manifest)
        (staging / "PROBE_MANIFEST.json").write_text(
            canonical_json(manifest) + "\n", encoding="utf-8"
        )
        shutil.move(str(staging), str(output))
        return manifest
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-approved", action="store_true")
    parser.add_argument("--agent", required=True, choices=("claude", "codex"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--cli-version", required=True)
    parser.add_argument("--effort")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if not args.owner_approved:
        parser.error("--owner-approved is required before paid provider probes")
    manifest = run_probe(
        agent=args.agent, model=args.model, cli_version=args.cli_version,
        effort=args.effort, output=Path(args.output),
    )
    print(canonical_json({
        "agent": manifest["agent"], "resolved_model": manifest["resolved_model"],
        "cli_version": manifest["cli_version"], "fingerprint": manifest["fingerprint"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
