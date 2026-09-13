"""Read-only comparison of separate versus shared preview/recheck proof scopes.

Run from the checkout root:
python scripts/profile_reflection_verification.py --source <branch> --base HEAD
No merge, commit, cache file, or protected record is written. Run without other
heavy jobs for useful elapsed-time comparisons; Git call counts are also shown.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from time import perf_counter
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from memory_seed import reflection_ledger as ledger


def measure(root, source, base, shared):
    calls = Counter()
    original_git = ledger._git
    original_classify = ledger._classify_trusted_workstream_ledger

    def git(*args, **kwargs):
        calls["git_calls"] += 1
        return original_git(*args, **kwargs)

    def classify(*args, **kwargs):
        calls["classifications"] += 1
        return original_classify(*args, **kwargs)

    def operation():
        preview = ledger.preview_reflection_integration(root, source_ref=source, base_ref=base)
        ledger.recheck_reflection_integration(root, preview)
        return preview

    ledger.clear_trusted_workstream_history_cache()
    start = perf_counter()
    with patch.object(ledger, "_git", git), patch.object(ledger, "_classify_trusted_workstream_ledger", classify):
        preview = ledger.reflection_verification_operation(operation)() if shared else operation()
    return preview, dict(mode="shared" if shared else "separate", seconds=round(perf_counter() - start, 3),
                         git_calls=calls["git_calls"], classifications=calls["classifications"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--cwd", default=".")
    args = parser.parse_args()
    root = Path(args.cwd).resolve()
    before, baseline = measure(root, args.source, args.base, False)
    after, shared = measure(root, args.source, args.base, True)
    if before != after:
        raise SystemExit("State changed between measurements; comparison is invalid.")
    print(json.dumps(dict(source_commit=after.source_commit, base_commit=after.base_commit,
                          measurements=[baseline, shared],
                          note="In-process proof reuse only; not end-to-end merge timing."), indent=2))


if __name__ == "__main__":
    main()
