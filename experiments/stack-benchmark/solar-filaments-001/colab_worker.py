"""Colab-side worker contract. Colab executes training; it does not own benchmark policy."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def gpu_metadata() -> dict:
    command = ["nvidia-smi", "--query-gpu=name,uuid,memory.total,driver_version", "--format=csv,noheader,nounits"]
    try:
        output = subprocess.check_output(command, text=True, timeout=15).strip()
    except (OSError, subprocess.SubprocessError):
        output = "unavailable"
    return {"nvidia_smi": output, "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", type=Path, required=True)
    args = parser.parse_args()
    job = args.job.resolve()
    config = json.loads((job / "job.json").read_text(encoding="utf-8"))
    result_dir = job / "result"
    result_dir.mkdir(exist_ok=True)
    started = now(); monotonic = time.monotonic()
    command = config["command"]
    process = subprocess.run(command, cwd=job / "payload", text=True, capture_output=True)
    (result_dir / "stdout.log").write_text(process.stdout, encoding="utf-8")
    (result_dir / "stderr.log").write_text(process.stderr, encoding="utf-8")
    artifacts = []
    for relative in config.get("expected_artifacts", []):
        path = job / "payload" / relative
        if path.is_file():
            artifacts.append({"path": relative, "sha256": sha256(path), "bytes": path.stat().st_size})
    result = {
        "schema": "solar-colab-result.v1", "job_id": config["job_id"],
        "config_sha256": sha256(job / "job.json"), "started_at": started,
        "finished_at": now(), "compute_seconds": time.monotonic() - monotonic,
        "exit_code": process.returncode, "interrupted": False,
        "environment": {"python": sys.version, "platform": platform.platform(), **gpu_metadata()},
        "artifacts": artifacts,
    }
    (result_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
