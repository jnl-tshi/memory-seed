"""Make a bare `pytest` from the repo root equal what CI runs.

CI installs the package, so `memory_trace` is importable everywhere - including in the subprocesses
some Trace tests spawn. Locally it is a source tree, not an install, and that difference hid three
real failures on `main` from 2026-07-28 until a push finally ran CI's Verify job.

Two consumers need the path, which is why `pythonpath` in `pyproject.toml` is not enough on its own:

- **in-process imports**, during collection - handled by `pythonpath = ["memory-trace"]`;
- **subprocesses**, which inherit the environment but not the parent's `sys.path`. Without this,
  `test_cache_rebuild_lease_blocks_an_independent_process` fails only in the combined run, because
  it launches a child that does `from memory_trace.service import _CacheRebuildLease`.

Setting PYTHONPATH here covers the second. Prepend-and-preserve, so an existing value still wins
for anything it already resolves.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_TRACE_SRC = Path(__file__).resolve().parent / "memory-trace"

if _TRACE_SRC.is_dir():
    if str(_TRACE_SRC) not in sys.path:
        sys.path.insert(0, str(_TRACE_SRC))
    _existing = os.environ.get("PYTHONPATH", "")
    _parts = [part for part in _existing.split(os.pathsep) if part]
    if str(_TRACE_SRC) not in _parts:
        os.environ["PYTHONPATH"] = os.pathsep.join([str(_TRACE_SRC), *_parts])
