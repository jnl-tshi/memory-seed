from __future__ import annotations

import argparse
import json
from pathlib import Path

from hosted.capture.evaluation import run_evaluation


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the offline P0.2 decision-capture evaluation.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--codex-home", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("hosted/evaluation/results"))
    args = parser.parse_args()
    report = run_evaluation(args.repo.resolve(), args.codex_home.resolve(), args.output.resolve())
    print(json.dumps({"feasible": report["feasible"], "gates": report["gates"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
