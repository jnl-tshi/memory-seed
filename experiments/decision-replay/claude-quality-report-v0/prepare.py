"""Prepare a randomized pair of standalone historical repos for the Claude replay.

The sealed arm receipt is deliberately outside both fixture repositories. Existing targets are
refused rather than overwritten.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import random
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
TASK = HERE / "task" / "TASK.md"
RUNS = HERE / "runs"

SOURCE_REVISION = "6c43f2dbbaf8bdf76d20b5293df74d969e840990"
WITHHELD_REVISION = "b851cb04f7240caa5aec5493d0c1399a50ba05b1"
ARMS = ("historical-rationale", "current-state")
LABELS = ("A", "B")


def _run(command: list[str], *, cwd: Path, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=cwd,
        input=input_bytes,
        capture_output=True,
        check=True,
    )


def _safe_extract_tar(payload: bytes, destination: Path) -> None:
    destination_resolved = destination.resolve()
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
        for member in archive.getmembers():
            target = (destination / member.name).resolve()
            if destination_resolved not in target.parents and target != destination_resolved:
                raise RuntimeError(f"archive member escapes fixture: {member.name}")
        archive.extractall(destination)


def _export_revision(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    archive = _run(
        ["git", "archive", "--format=tar", SOURCE_REVISION],
        cwd=REPO_ROOT,
    ).stdout
    _safe_extract_tar(archive, destination)


def _strip_dated_session_memory(destination: Path) -> None:
    sessions = destination / ".memory-seed" / "sessions"
    if sessions.exists():
        shutil.rmtree(sessions)
    sessions.mkdir(parents=True)
    (sessions / ".gitkeep").write_text("", encoding="utf-8")


def _initialize_fixture(destination: Path) -> str:
    shutil.copyfile(TASK, destination / "TASK.md")
    _run(["git", "init", "-b", "main"], cwd=destination)
    _run(["git", "config", "user.name", "Memory Seed Replay"], cwd=destination)
    _run(["git", "config", "user.email", "replay@example.invalid"], cwd=destination)
    _run(["git", "add", "-A"], cwd=destination)
    _run(["git", "commit", "-m", "fixture: historical starting point"], cwd=destination)
    return _run(["git", "rev-parse", "HEAD"], cwd=destination).stdout.decode().strip()


def _dated_session_documents(destination: Path) -> int:
    sessions = destination / ".memory-seed" / "sessions"
    return sum(
        1
        for path in sessions.rglob("*.md")
        if path.is_file() and path.name[:4].isdigit()
    ) if sessions.exists() else 0


def prepare_pair(output_root: Path, receipt_dir: Path, *, seed: int, run_id: str) -> dict:
    if output_root.exists():
        raise FileExistsError(f"refusing existing output root: {output_root}")
    output_root.mkdir(parents=True)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / f"{run_id}.sealed.json"
    if receipt_path.exists():
        raise FileExistsError(f"refusing existing receipt: {receipt_path}")

    assignments = list(ARMS)
    random.Random(seed).shuffle(assignments)
    mapping = dict(zip(LABELS, assignments, strict=True))
    task_hash = hashlib.sha256(TASK.read_bytes()).hexdigest()
    fixtures: dict[str, dict] = {}

    for label in LABELS:
        destination = output_root / label
        _export_revision(destination)
        if mapping[label] == "current-state":
            _strip_dated_session_memory(destination)
        fixture_commit = _initialize_fixture(destination)
        fixtures[label] = {
            "path": str(destination.resolve()),
            "fixture_commit": fixture_commit,
            "dated_session_documents": _dated_session_documents(destination),
        }

    receipt = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "seed": seed,
        "source_revision": SOURCE_REVISION,
        "withheld_revision": WITHHELD_REVISION,
        "task_sha256": task_hash,
        "mapping": mapping,
        "fixtures": fixtures,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return {"receipt": str(receipt_path.resolve()), **receipt}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True, help="recorded arm-randomization seed")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--receipt-dir", type=Path, default=RUNS)
    args = parser.parse_args()

    run_id = args.run_id or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root = args.output_root or (
        Path(tempfile.gettempdir()) / "memory-seed-decision-replay" / run_id
    )
    result = prepare_pair(
        output_root.resolve(),
        args.receipt_dir.resolve(),
        seed=args.seed,
        run_id=run_id,
    )
    public = {
        "run_id": result["run_id"],
        "fixtures": {label: data["path"] for label, data in result["fixtures"].items()},
        "sealed_receipt": result["receipt"],
        "instruction": "Run one fresh Claude session per fixture; do not open the receipt yet.",
    }
    print(json.dumps(public, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
