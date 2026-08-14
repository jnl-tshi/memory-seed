"""Reveal and combine grader, transcript-audit, and timing results after all arms finish."""

from __future__ import annotations

import argparse
import json
from pathlib import Path



def summarize(receipt_path: Path, artifacts: Path) -> dict:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema_version") != 2 or set(receipt.get("mapping", {})) != {"A", "B", "C"}:
        raise ValueError("expected a sealed schema-v2 three-arm receipt")
    public = json.loads((artifacts / "public-manifest.json").read_text(encoding="utf-8"))
    for field in ("run_id", "source_revision", "task_sha256", "prompt_sha256", "execution_order"):
        if public.get(field) != receipt.get(field):
            raise ValueError(f"artifact manifest and sealed receipt disagree on {field}")
    arms = {}
    for label in ("A", "B", "C"):
        transcript = artifacts / f"{label}-transcript.jsonl"
        metadata_path = artifacts / f"{label}-metadata.json"
        grade_path = artifacts / f"{label}-grade.json"
        audit_path = artifacts / f"{label}-audit.json"
        if not all(path.is_file() for path in (transcript, metadata_path, grade_path, audit_path)):
            raise FileNotFoundError(f"arm {label} is incomplete; refusing reveal summary")
        grade = json.loads(grade_path.read_text(encoding="utf-8"))
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        expected_fixture = str(Path(receipt["fixtures"][label]["path"]).resolve())
        if any(
            value != expected_fixture
            for value in (grade.get("candidate"), audit.get("fixture"), metadata.get("fixture"))
        ):
            raise ValueError(f"arm {label} artifacts point at a different fixture")
        arms[label] = {
            "condition": receipt["mapping"][label],
            "grade": grade,
            "audit": audit,
            "runner_metadata": metadata,
        }
    return {
        "schema_version": 1,
        "run_id": receipt["run_id"],
        "instrument": "claude-quality-report-v1",
        "interpretation": "corrected three-arm pilot; not a general product-effect estimate",
        "arms": arms,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    result = summarize(args.receipt.resolve(), args.artifacts.resolve())
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        if args.output.exists():
            raise FileExistsError(f"refusing existing result: {args.output}")
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
