"""Prepare a blinded three-arm replay with observable rationale exposure.

The sealed arm receipt is deliberately outside every fixture. Existing output paths are refused
rather than overwritten.
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
import sys
import tarfile
import tempfile
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
TASK = HERE / "task" / "TASK.md"
DEFAULT_STATE_ROOT = Path(tempfile.gettempdir()) / "memory-seed-decision-replay-v1"

SOURCE_REVISION = "6c43f2dbbaf8bdf76d20b5293df74d969e840990"
WITHHELD_REVISION = "b851cb04f7240caa5aec5493d0c1399a50ba05b1"
ARMS = (
    "no-dated-memory",
    "historical-available",
    "relevant-rationale-pushed",
)
LABELS = ("A", "B", "C")
RELEVANT_ENTRY_IDS = ("mse_gbc4m5m71dqmen75",)
SUBJECT_PROMPT = (
    "Read EXPERIMENT_CONTEXT.md first, then read TASK.md and implement it. "
    "Stay inside this repository and obey its experimental constraints."
)


def _run(
    command: list[str], *, cwd: Path, input_bytes: bytes | None = None
) -> subprocess.CompletedProcess:
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


def _context_receipt(seed: int, run_id: str, label: str) -> str:
    digest = hashlib.sha256(f"{seed}:{run_id}:{label}:context".encode()).hexdigest()[:20]
    return f"ctx_{digest}"


def _context_document(arm: str, receipt: str) -> str:
    header = textwrap.dedent(
        f"""\
        # Experiment context

        Read this file before `TASK.md`. It is experimental evidence, not an authorization to edit
        anything beyond the task's stated file boundary.

        CONTEXT_RECEIPT: {receipt}
        """
    )
    if arm != "relevant-rationale-pushed":
        body = textwrap.dedent(
            """\

            No supplemental historical rationale is supplied in this file. Follow the repository's
            normal routing and use only evidence you actually encounter.
            """
        )
    else:
        body = textwrap.dedent(
            """\

            ## Bounded pre-fix historical rationale

            Source: `.memory-seed/sessions/2026-08/2026-08-03.md`, entry
            `mse_gbc4m5m71dqmen75`, recorded before the withheld fix.

            Its rationale records:

            > Real-init-plus-strips means results generalise to actual installs rather than
            > hand-assembled approximations, and JNL confirmed the local tree over PyPI because the
            > published 2.19.0 lacks the adr layer. The standalone-git and identical-stub
            > requirements each close a verified hazard: the commit hook installs into the nearest
            > git common dir, the parent's prepare-commit-msg deliberately globs nested session
            > stores, resolve_runtime walks upward with no boundary guard, and an agent reading
            > agent-rules.md without index/policy diverts into bootstrap interviewing - which would
            > contaminate arms asymmetrically.

            Its follow-up records:

            > The `quality report` cwd path-join bug found during exploration is flagged as its own
            > task chip and deliberately not fixed in this workstream.

            This is the complete task-relevant excerpt selected before the run. It flags the
            runtime-boundary/path-join concern but contains no later patch, test, or reference answer.
            """
        )
    return header + body


def _initialize_fixture(destination: Path, *, arm: str, receipt: str) -> str:
    shutil.copyfile(TASK, destination / "TASK.md")
    (destination / "EXPERIMENT_CONTEXT.md").write_text(
        _context_document(arm, receipt), encoding="utf-8", newline="\n"
    )
    (destination / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "memory-seed": {
                        "command": sys.executable,
                        "args": ["-X", "utf8", "-m", "memory_seed.mcp_server"],
                    }
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    _run(["git", "init", "-b", "main"], cwd=destination)
    _run(["git", "config", "user.name", "Memory Seed Replay"], cwd=destination)
    _run(["git", "config", "user.email", "replay@example.invalid"], cwd=destination)
    _run(["git", "add", "-A"], cwd=destination)
    _run(["git", "commit", "-m", "fixture: historical starting point"], cwd=destination)
    return _run(["git", "rev-parse", "HEAD"], cwd=destination).stdout.decode().strip()


def _dated_session_documents(destination: Path) -> int:
    sessions = destination / ".memory-seed" / "sessions"
    if not sessions.exists():
        return 0
    return sum(
        1
        for path in sessions.rglob("*.md")
        if path.is_file() and path.name[:4].isdigit()
    )


def prepare_study(output_root: Path, receipt_dir: Path, *, seed: int, run_id: str) -> dict:
    if output_root.exists():
        raise FileExistsError(f"refusing existing output root: {output_root}")
    output_root.mkdir(parents=True)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / f"{run_id}.sealed.json"
    public_path = receipt_dir / f"{run_id}.public.json"
    for path in (receipt_path, public_path):
        if path.exists():
            raise FileExistsError(f"refusing existing manifest: {path}")

    assignments = list(ARMS)
    rng = random.Random(seed)
    rng.shuffle(assignments)
    mapping = dict(zip(LABELS, assignments, strict=True))
    execution_order = list(LABELS)
    rng.shuffle(execution_order)
    task_hash = hashlib.sha256(TASK.read_bytes()).hexdigest()
    prompt_hash = hashlib.sha256(SUBJECT_PROMPT.encode()).hexdigest()
    fixtures: dict[str, dict] = {}

    for label in LABELS:
        arm = mapping[label]
        destination = output_root / label
        receipt = _context_receipt(seed, run_id, label)
        _export_revision(destination)
        if arm in {"no-dated-memory", "relevant-rationale-pushed"}:
            _strip_dated_session_memory(destination)
        fixture_commit = _initialize_fixture(destination, arm=arm, receipt=receipt)
        context_path = destination / "EXPERIMENT_CONTEXT.md"
        fixtures[label] = {
            "path": str(destination.resolve()),
            "fixture_commit": fixture_commit,
            "dated_session_documents": _dated_session_documents(destination),
            "context_sha256": hashlib.sha256(context_path.read_bytes()).hexdigest(),
            "context_receipt": receipt,
        }

    public_fixtures = {
        label: {
            "path": data["path"],
            "fixture_commit": data["fixture_commit"],
        }
        for label, data in fixtures.items()
    }
    public = {
        "schema_version": 2,
        "run_id": run_id,
        "source_revision": SOURCE_REVISION,
        "task_sha256": task_hash,
        "prompt_sha256": prompt_hash,
        "execution_order": execution_order,
        "fixtures": public_fixtures,
    }
    sealed = {
        **public,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "seed": seed,
        "withheld_revision": WITHHELD_REVISION,
        "mapping": mapping,
        "relevant_entry_ids": list(RELEVANT_ENTRY_IDS),
        "fixtures": fixtures,
    }
    receipt_path.write_text(json.dumps(sealed, indent=2) + "\n", encoding="utf-8")
    public_path.write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    return {
        "run_id": run_id,
        "public_manifest": str(public_path.resolve()),
        "sealed_receipt": str(receipt_path.resolve()),
        "execution_order": execution_order,
        "fixtures": {label: data["path"] for label, data in fixtures.items()},
        "instruction": "Run fresh sessions from the public manifest; do not open the sealed receipt.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True, help="recorded arm-randomization seed")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--receipt-dir", type=Path, default=DEFAULT_STATE_ROOT / "receipts")
    args = parser.parse_args()

    run_id = args.run_id or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root = args.output_root or (
        DEFAULT_STATE_ROOT / run_id
    )
    result = prepare_study(
        output_root.resolve(),
        args.receipt_dir.resolve(),
        seed=args.seed,
        run_id=run_id,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
