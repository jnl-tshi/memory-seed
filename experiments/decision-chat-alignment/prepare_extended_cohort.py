"""Freeze 53 unseen typed Codex decisions for the 100-decision experiment.

The original 50-row cohort is preserved; three historical rows are now typed
Documentation, so 53 new Decision records yield 100 strict Decision cases.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

BASE = Path(__file__).resolve().parent
SEED = 20260925
NEW_DECISIONS = 53


def load_alignment_module(repo: Path) -> Any:
    sys.path.insert(0, str(repo))
    import memory_seed

    package_path = Path(memory_seed.__file__).resolve()
    if not package_path.is_relative_to(repo):
        raise RuntimeError(f"Loaded Memory Seed package outside checkout: {package_path}")
    spec = importlib.util.spec_from_file_location("extended_cohort_alignment", BASE / "align_decisions.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load align_decisions.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def digest_ids(ids: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def choose_unseen(records: Sequence[Any], known_ids: set[str], size: int, seed: int) -> list[Any]:
    eligible = sorted(
        (record for record in records if record.decision_id not in known_ids),
        key=lambda record: record.decision_id,
    )
    if len({record.decision_id for record in eligible}) != len(eligible):
        raise RuntimeError("Eligible decision IDs are not unique")
    if len(eligible) < size:
        raise ValueError(f"Need {size} unseen decisions; only {len(eligible)} eligible")
    return sorted(random.Random(seed).sample(eligible, size), key=lambda record: record.decision_id)


def build_manifest(repo: Path, known_gold: Path, seed: int = SEED) -> dict[str, Any]:
    alignment = load_alignment_module(repo)
    gold = [json.loads(line) for line in known_gold.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(gold) != 50:
        raise RuntimeError("Frozen known cohort must contain 50 rows")
    known_ids = {row["decision"]["id"] for row in gold}
    if len(known_ids) != 50:
        raise RuntimeError("Frozen known cohort has duplicate IDs")
    population = alignment.filter_decisions(alignment.load_decisions(repo), "codex")
    population_ids = {record.decision_id for record in population}
    new = choose_unseen(population, known_ids, NEW_DECISIONS, seed)
    new_ids = [record.decision_id for record in new]
    known_typed = sorted(known_ids & population_ids)
    if len(known_typed) != 47:
        raise RuntimeError(f"Expected 47 surviving typed known Decisions; found {len(known_typed)}")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    return {
        "schema_version": "decision-alignment-cohort/1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository_revision": revision,
        "sampler_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python_version": sys.version.split()[0],
        "agent_filter": "codex",
        "sample_method": "random.Random(seed).sample over sorted, unseen typed Codex Decisions",
        "sample_seed": seed,
        "sample_size": NEW_DECISIONS,
        "sample_ids": new_ids,  # align_decisions.py --sample-ids-from compatibility
        "sample_ids_sha256": digest_ids(new_ids),
        "eligible_population_size": len(population),
        "eligible_ids_sha256": digest_ids(sorted(population_ids)),
        "unseen_population_size": len(population_ids - known_ids),
        "known_record_ids_sha256": digest_ids(sorted(known_ids)),
        "known_typed_decision_ids_sha256": digest_ids(known_typed),
        "known_typed_decisions": len(known_typed),
        "known_documentation_records": sorted(known_ids - population_ids),
        "strict_decision_total": len(known_typed) + len(new_ids),
        "secondary_documentation_total": len(known_ids - population_ids),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--known-gold", type=Path, default=BASE / "GOLD-SET.jsonl")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_manifest(args.repo.resolve(), args.known_gold.resolve(), args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"metadata": manifest}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ("sample_size", "sample_seed", "sample_ids_sha256", "strict_decision_total", "secondary_documentation_total")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
