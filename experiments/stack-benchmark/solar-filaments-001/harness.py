"""Offline-first harness for Solar Filaments Stack Benchmark 001."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import sys
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
BENCHMARK = ROOT / "benchmark.json"
RUNS = ROOT / "runs"
GENERATED = ROOT / "generated"
ARM_TOOLS = {
    "baseline": [],
    "icm": [],
    "memory-seed": ["memory-seed"],
    "graphify": ["graphify"],
    "semble": ["semble"],
    "memory-seed-icm": ["memory-seed"],
    "memory-seed-graphify": ["memory-seed", "graphify"],
    "memory-seed-semble": ["memory-seed", "semble"],
}
SECRET_PATTERNS = [re.compile(p, re.I) for p in (r"kaggle[_-]?key", r"api[_-]?token", r"authorization:\s*bearer", r"BEGIN [A-Z ]+PRIVATE KEY")]
REQUIRED_RUN_PATHS = ["source", "working", "submission", "handoff-test", "final-report.md", "decisions.md", "run-log.jsonl", "metrics.json"]
FREEZE_FIELDS = ["source_commit", "data_manifest_sha256", "validation_manifest_sha256", "prompt_sha256", "claude_model", "claude_cli_version", "python_version", "dependency_lock_sha256", "icm_commit", "graphify_version", "graphify_model", "semble_version", "semble_model", "capability_envelope"]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fingerprint_tree(root: Path) -> list[dict]:
    return [{"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in sorted(root.rglob("*")) if p.is_file()]


def freeze_issues(config: dict) -> list[str]:
    issues = []
    if config.get("status") != "FROZEN": issues.append("benchmark status is not FROZEN")
    if not config["competition"].get("rules_accepted"): issues.append("Kaggle rules are not accepted")
    for field in FREEZE_FIELDS:
        if not config["freeze"].get(field): issues.append(f"freeze.{field} is missing")
    if config.get("arms") != list(ARM_TOOLS): issues.append("arm order/identity differs from the v1 contract")
    return issues


def require_frozen() -> dict:
    config = load_json(BENCHMARK); issues = freeze_issues(config)
    if issues: raise SystemExit("benchmark is not runnable:\n- " + "\n- ".join(issues))
    return config


def parse_time(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def union_seconds(intervals: Iterable[dict]) -> float:
    spans = sorted((parse_time(x["start"]), parse_time(x["end"])) for x in intervals)
    total = 0.0; current = None
    for start, end in spans:
        if end < start: raise ValueError("interval ends before it starts")
        if current is None: current = [start, end]
        elif start <= current[1]: current[1] = max(current[1], end)
        else: total += current[1] - current[0]; current = [start, end]
    if current: total += current[1] - current[0]
    return total


def overlaps(a: dict, b: dict) -> bool:
    return parse_time(a["start"]) < parse_time(b["end"]) and parse_time(b["start"]) < parse_time(a["end"])


def derive_clocks(events: list[dict]) -> dict:
    groups = {name: [] for name in ("agent_active", "compute_wait", "treatment_setup")}
    for event in events:
        if event.get("type") == "interval" and event.get("class") in groups: groups[event["class"]].append(event)
    conflicts = [
        (a, b)
        for a in groups["agent_active"]
        for b in groups["compute_wait"]
        if (
            a.get("interval_id") is not None
            and b.get("interval_id") is not None
            and a["interval_id"] == b["interval_id"]
        )
        or (a.get("exclusive", False) and b.get("exclusive", False) and overlaps(a, b))
    ]
    if conflicts: raise ValueError("telemetry merges agent-active and compute-wait classification")
    starts = [parse_time(x["start"]) for values in groups.values() for x in values]
    ends = [parse_time(x["end"]) for values in groups.values() for x in values]
    return {"agent_active_seconds": union_seconds(groups["agent_active"]), "compute_wait_seconds": union_seconds(groups["compute_wait"]), "treatment_setup_seconds": union_seconds(groups["treatment_setup"]), "end_to_end_seconds": max(ends) - min(starts) if starts else 0.0}


def validate_submission(path: Path, expected_image_ids: set[str] | None = None) -> list[str]:
    issues = []
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, UnicodeError, csv.Error) as exc: return [f"submission unreadable: {exc}"]
    if not rows: return ["submission has no prediction rows"]
    if set(rows[0]) != {"filament_id", "segmentation_rle"}: issues.append("submission columns must be exactly filament_id,segmentation_rle")
    ids = [r.get("filament_id", "") for r in rows]
    if any(not value or "_" not in value for value in ids): issues.append("every filament_id must contain an image id and instance suffix")
    if len(ids) != len(set(ids)): issues.append("filament_id values must be unique")
    if any(not r.get("segmentation_rle", "").strip() for r in rows): issues.append("segmentation_rle must be non-empty")
    if expected_image_ids:
        predicted = {value.rsplit("_", 1)[0] for value in ids if "_" in value}
        missing = sorted(expected_image_ids - predicted)
        if missing: issues.append(f"submission omits {len(missing)} expected image ids")
    return issues


def check_secrets(root: Path) -> list[str]:
    issues = []
    for path in root.rglob("*"):
        if not path.is_file() or path.stat().st_size > 2_000_000: continue
        try: text = path.read_text(encoding="utf-8")
        except UnicodeError: continue
        if any(pattern.search(text) for pattern in SECRET_PATTERNS): issues.append(f"possible credential in {path}")
    return issues


def arm_manifest(arm: str, config: dict, source_hash: str) -> dict:
    return {"schema": "solar-arm-manifest.v1", "experiment_id": config["experiment_id"], "arm": arm, "tools": ARM_TOOLS[arm], "source_tree_sha256": source_hash, "treatments": {"icm": "icm" in arm, "memory_seed": "memory-seed" in arm, "graphify": "graphify" in arm, "semble": "semble" in arm}, "graphify": {"llm_document_analysis": "graphify" in arm, "backend": config["freeze"]["graphify_backend"], "model": config["freeze"]["graphify_model"]} if "graphify" in arm else None, "semble": {"content": "code", "cache": "cache/semble"} if "semble" in arm else None}


def normalized_tree_hash(root: Path) -> str:
    payload = json.dumps(fingerprint_tree(root), sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def generate(source: Path) -> None:
    config = require_frozen(); source = source.resolve()
    if not (source / ".git").exists(): raise SystemExit("source must be a standalone git repository")
    source_hash = normalized_tree_hash(source)
    if GENERATED.exists(): shutil.rmtree(GENERATED)
    for arm in config["arms"]:
        target = GENERATED / "arms" / arm
        shutil.copytree(source, target / "workspace", ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc"))
        for path in REQUIRED_RUN_PATHS[:4]: (target / "workspace" / path).mkdir(parents=True, exist_ok=True)
        for path in REQUIRED_RUN_PATHS[4:]: (target / "workspace" / path).write_text("" if path.endswith(".jsonl") else "{}\n" if path.endswith(".json") else f"# {path}\n", encoding="utf-8")
        dump(target / "ARM_MANIFEST.json", arm_manifest(arm, config, source_hash))
    dump(GENERATED / "generation.json", {"schema": "solar-generation.v1", "source_tree_sha256": source_hash, "arms": config["arms"]})


def package_job(run: Path, training_config: Path) -> Path:
    config = require_frozen(); run = run.resolve(); spec = load_json(training_config)
    if not isinstance(spec.get("command"), list) or not spec["command"]: raise SystemExit("training config command must be a non-empty argv list")
    job_id = spec.get("job_id") or hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:16]
    job = run / "colab-jobs" / job_id
    if job.exists(): shutil.rmtree(job)
    payload = job / "payload"; payload.mkdir(parents=True)
    for relative in spec.get("payload", []):
        src = run / relative; dst = payload / relative
        if src.is_dir(): shutil.copytree(src, dst)
        elif src.is_file(): dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)
        else: raise SystemExit(f"missing payload path: {relative}")
    job_spec = {**spec, "schema": "solar-colab-job.v1", "job_id": job_id, "experiment_id": config["experiment_id"], "benchmark_sha256": sha256(BENCHMARK)}
    dump(job / "job.json", job_spec); shutil.copy2(ROOT / "colab_worker.py", job / "colab_worker.py")
    archive = shutil.make_archive(str(job), "zip", root_dir=job)
    print(archive); return Path(archive)


def validate_job(job: Path) -> list[str]:
    issues = []; spec_path = job / "job.json"; result_path = job / "result" / "result.json"
    if not spec_path.is_file() or not result_path.is_file(): return ["job.json or result/result.json missing"]
    spec, result = load_json(spec_path), load_json(result_path)
    if result.get("job_id") != spec.get("job_id"): issues.append("result job_id does not match job")
    if result.get("config_sha256") != sha256(spec_path): issues.append("result config fingerprint does not match job")
    if not isinstance(result.get("compute_seconds"), (int, float)) or result.get("compute_seconds", -1) < 0: issues.append("invalid compute_seconds")
    if not isinstance(result.get("exit_code"), int): issues.append("exit_code missing")
    indexed = {row.get("path"): row for row in result.get("artifacts", [])}
    for relative in spec.get("expected_artifacts", []):
        path = job / "payload" / relative
        if relative not in indexed or not path.is_file(): issues.append(f"expected artifact missing: {relative}")
        elif indexed[relative].get("sha256") != sha256(path): issues.append(f"artifact checksum mismatch: {relative}")
    issues.extend(check_secrets(job))
    return issues


def collect() -> dict:
    config = require_frozen(); rows = []
    for run in sorted(RUNS.glob("*")):
        if not run.is_dir(): continue
        issues = [f"missing {name}" for name in REQUIRED_RUN_PATHS if not (run / name).exists()]
        try:
            events = [json.loads(line) for line in (run / "run-log.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
            clocks = derive_clocks(events)
        except (OSError, json.JSONDecodeError, ValueError) as exc: issues.append(str(exc)); clocks = {}
        try: metrics = load_json(run / "metrics.json")
        except (OSError, json.JSONDecodeError): metrics = {}; issues.append("metrics.json unreadable")
        issues.extend(check_secrets(run))
        rows.append({"run_id": run.name, "arm": metrics.get("arm"), "clocks": clocks, "metrics": metrics, "issues": issues})
    result = {"schema": "solar-collection.v1", "experiment_id": config["experiment_id"], "runs": rows}
    dump(ROOT / "results" / "collection.json", result); return result


def score_value(row: dict, name: str) -> float | None:
    value = row.get("metrics", {}).get(name)
    return float(value) if isinstance(value, (int, float)) and math.isfinite(value) else None


def report(collection: dict | None = None) -> dict:
    collection = collection or load_json(ROOT / "results" / "collection.json")
    by_arm = {row["arm"]: row for row in collection["runs"] if row.get("arm")}
    comparisons = []
    pairs = [(a, "baseline") for a in ("icm", "memory-seed", "graphify", "semble")] + [("memory-seed-icm", "memory-seed"), ("memory-seed-icm", "icm"), ("memory-seed-graphify", "memory-seed"), ("memory-seed-graphify", "graphify"), ("memory-seed-semble", "memory-seed"), ("memory-seed-semble", "semble")]
    for treatment, control in pairs:
        values = {}
        for metric in ("best_validation_dice", "final_validation_dice", "input_tokens", "output_tokens", "estimated_cost"):
            left, right = score_value(by_arm.get(treatment, {}), metric), score_value(by_arm.get(control, {}), metric)
            values[metric] = left - right if left is not None and right is not None else None
        left_clock, right_clock = by_arm.get(treatment, {}).get("clocks", {}), by_arm.get(control, {}).get("clocks", {})
        values["agent_active_seconds"] = left_clock.get("agent_active_seconds", 0) - right_clock.get("agent_active_seconds", 0) if left_clock and right_clock else None
        comparisons.append({"treatment": treatment, "control": control, "deltas": values})
    result = {"schema": "solar-report.v1", "pilot_only": True, "comparisons": comparisons, "raw_runs": collection["runs"]}
    dump(ROOT / "results" / "report.json", result); return result


def command_check() -> int:
    config = load_json(BENCHMARK); issues = freeze_issues(config)
    prompt_hash = sha256(ROOT / "initial-prompt.md")
    print(json.dumps({"ok": not issues, "issues": issues, "computed_prompt_sha256": prompt_hash}, indent=2))
    return 1 if issues else 0


def main() -> int:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    freeze = sub.add_parser("freeze-data"); freeze.add_argument("--data", type=Path, required=True)
    gen = sub.add_parser("generate"); gen.add_argument("--source", type=Path, required=True)
    package = sub.add_parser("package-job"); package.add_argument("--run", type=Path, required=True); package.add_argument("--config", type=Path, required=True)
    validate = sub.add_parser("validate-job"); validate.add_argument("--job", type=Path, required=True)
    sub.add_parser("collect"); sub.add_parser("report")
    args = parser.parse_args()
    if args.command == "check": return command_check()
    if args.command == "freeze-data":
        rows = fingerprint_tree(args.data.resolve()); dump(ROOT / "data-manifest.json", {"schema": "solar-data-manifest.v1", "files": rows}); print(sha256(ROOT / "data-manifest.json")); return 0
    if args.command == "generate": generate(args.source); return 0
    if args.command == "package-job": package_job(args.run, args.config); return 0
    if args.command == "validate-job":
        issues = validate_job(args.job.resolve()); print(json.dumps({"ok": not issues, "issues": issues}, indent=2)); return 1 if issues else 0
    if args.command == "collect": print(json.dumps(collect(), indent=2)); return 0
    if args.command == "report": print(json.dumps(report(), indent=2)); return 0
    return 2


if __name__ == "__main__": raise SystemExit(main())
