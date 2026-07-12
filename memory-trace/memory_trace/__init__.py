"""Memory Trace - the companion review UI for Memory Seed.

Memory Trace ships inside the optional ``memory-seed[trace]`` extra and consumes
Memory Seed's public retrieval service (``memory_seed.retrieval``). It never
reimplements parsing, ranking, graph, or diagram-sidecar logic - the core
package owns those, and this package renders them read-only.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .lense import LenseCache, LenseService, create_app, missing_optional_dependency_hint, run_server

__all__ = [
    "LenseCache",
    "LenseService",
    "create_app",
    "run_server",
    "missing_optional_dependency_hint",
    "__version__",
]
