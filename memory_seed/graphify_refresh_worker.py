"""Run the stock Graphify structural updater in its own Python environment."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    root = Path(request["root"])
    changed = request["changed"]
    from graphify.watch import _rebuild_code

    ok = _rebuild_code(
        root,
        changed_paths=[root / path for path in changed] if changed is not None else None,
        block_on_lock=True,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
