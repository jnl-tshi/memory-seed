"""Optional, project-scoped Graphify refresh after a successful local merge.

Graphify is an external, optional tool. This adapter never imports it into the
Memory Seed interpreter and never makes its failure a merge failure.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


STATE_NAME = "merge-refresh-state.json"
GRAPH_NAME = "graph.json"
_CONTROL_FILES = {
    "agent-rules.md", "project-bootstrap.md", "index.md", "policy.md"
}


@dataclass(frozen=True)
class RefreshResult:
    status: str
    head: str | None = None
    indexed_commit: str | None = None
    warning: str | None = None


def enabled(root: Path) -> bool:
    """Require an explicit top-level project opt-in; other projects are inert."""
    config = root / ".memory-seed" / "project.yaml"
    try:
        lines = config.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    value: str | None = None
    for line in lines:
        match = re.match(r"^graphify_merge_refresh\s*:\s*([^#]+)", line)
        if match:
            value = match.group(1).strip().strip("'\"").lower()
    return value == "true"


def selected(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    if len(parts) < 2 or not path.lower().endswith(".md"):
        return False
    if parts[0] == "docs":
        return True
    if parts[0] != ".memory-seed":
        return False
    if len(parts) == 2:
        return parts[1] in _CONTROL_FILES
    return len(parts) == 3 and parts[1] in {"skills", "decisions"}


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, check=False,
    )


def _head(root: Path) -> str | None:
    result = _git(root, "rev-parse", "HEAD")
    return result.stdout.decode("ascii", "replace").strip() if result.returncode == 0 else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _state(root: Path) -> dict:
    try:
        value = json.loads((root / "graphify-out" / STATE_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _dirty_selected_paths(root: Path) -> bool:
    tracked = _git(root, "diff", "--name-only", "-z", "HEAD", "--", "docs", ".memory-seed", ".graphifyignore")
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z", "--", "docs", ".memory-seed", ".graphifyignore")
    if tracked.returncode or untracked.returncode:
        return True
    paths = [os.fsdecode(part) for raw in (tracked.stdout, untracked.stdout) for part in raw.split(b"\0") if part]
    return any(path == ".graphifyignore" or selected(path) for path in paths)


def status(root: Path) -> RefreshResult:
    root = root.resolve()
    head = _head(root)
    state = _state(root)
    indexed = state.get("indexed_commit")
    graph = root / "graphify-out" / GRAPH_NAME
    if not enabled(root):
        return RefreshResult("disabled", head, indexed)
    if not head or not graph.is_file() or not isinstance(indexed, str):
        return RefreshResult("stale", head, indexed, "Graphify index or freshness marker is missing")
    try:
        digest_matches = _sha256(graph) == state.get("graph_sha256")
    except OSError:
        digest_matches = False
    if head == indexed and digest_matches and not _dirty_selected_paths(root):
        return RefreshResult("fresh", head, indexed)
    if not digest_matches:
        reason = "Graphify index differs from its recorded digest"
    elif head != indexed:
        reason = "Graphify index is behind HEAD"
    else:
        reason = "Selected documents or Graphify scope have uncommitted changes"
    return RefreshResult("stale", head, indexed, reason)


def _write_state(root: Path, head: str, graph: Path) -> None:
    output = graph.parent / STATE_NAME
    payload = {"version": 1, "indexed_commit": head, "graph_sha256": _sha256(graph)}
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=output.parent, prefix=".merge-refresh-state-",
        suffix=".tmp", delete=False,
    ) as temporary:
        json.dump(payload, temporary, indent=2)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, output)


def _graphify_python(root: Path) -> Path | None:
    candidates: list[Path] = []
    explicit = os.environ.get("GRAPHIFY_PYTHON")
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(Path(sys.executable))
    saved = root / "graphify-out" / ".graphify_python"
    try:
        candidates.append(Path(saved.read_text(encoding="utf-8").strip()))
    except OSError:
        pass
    launcher = shutil.which("graphify")
    if launcher:
        bin_dir = Path(launcher).parent
        candidates.extend([
            bin_dir / "python", bin_dir / "python.exe", bin_dir.parent / "python.exe",
        ])
    uv = shutil.which("uv")
    if uv:
        try:
            found = subprocess.run(
                [uv, "tool", "dir"], capture_output=True, text=True,
                check=False, timeout=10,
            )
            if found.returncode == 0:
                tool = Path(found.stdout.strip()) / "graphifyy"
                candidates.extend([tool / "Scripts" / "python.exe", tool / "bin" / "python"])
        except (OSError, subprocess.TimeoutExpired):
            pass
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            probe = subprocess.run(
                [str(candidate), "-c", "import importlib.util; assert importlib.util.find_spec('graphify')"],
                capture_output=True, check=False, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if probe.returncode == 0:
            return candidate
    return None


def _changed_paths(root: Path, base: str, head: str) -> list[str] | None:
    # --no-renames yields both old and new paths: pruning and addition are explicit.
    result = _git(root, "diff", "--name-only", "--no-renames", "-z", base, head)
    if result.returncode:
        return None
    return [os.fsdecode(part) for part in result.stdout.split(b"\0") if part]


def refresh_after_merge(root: Path) -> RefreshResult:
    root = root.resolve()
    if not enabled(root):
        return RefreshResult("disabled")
    head = _head(root)
    if not head:
        return RefreshResult("stale", warning="Cannot resolve HEAD for Graphify refresh")
    if _dirty_selected_paths(root):
        return RefreshResult("stale", head, warning="Commit selected documents and the Graphify scope file before refreshing")
    output = root / "graphify-out"
    graph = output / GRAPH_NAME
    state = _state(root)
    base = state.get("indexed_commit")
    valid_base = (
        isinstance(base, str) and re.fullmatch(r"[0-9a-f]{40}", base) is not None and graph.is_file()
        and state.get("graph_sha256") == _sha256(graph)
        and _git(root, "merge-base", "--is-ancestor", base, head).returncode == 0
    )
    changed: list[str] | None = None
    if valid_base:
        diff = _changed_paths(root, base, head)
        if diff is not None and ".graphifyignore" not in diff:
            changed = [path for path in diff if selected(path)]
            if not changed:
                _write_state(root, head, graph)
                return RefreshResult("fresh", head, head)
    interpreter = _graphify_python(root)
    if interpreter is None:
        return RefreshResult("stale", head, base, "Graphify Python is unavailable; merge succeeded but index is stale")

    output.mkdir(exist_ok=True)
    # Build in a separate output directory. A failed extraction cannot replace
    # the last usable graph; the freshness marker is written only at the end.
    with tempfile.TemporaryDirectory(prefix=".merge-refresh-", dir=output) as temporary:
        stage = Path(temporary)
        if changed is not None:
            shutil.copy2(graph, stage / GRAPH_NAME)
        spec = stage / "request.json"
        spec.write_text(json.dumps({"root": str(root), "changed": changed}), encoding="utf-8")
        env = dict(os.environ)
        env["GRAPHIFY_OUT"] = str(stage)
        package_root = str(Path(__file__).resolve().parent.parent)
        env["PYTHONPATH"] = package_root + os.pathsep + env.get("PYTHONPATH", "")
        try:
            completed = subprocess.run(
                [str(interpreter), "-m", "memory_seed.graphify_refresh_worker", str(spec)],
                cwd=root, env=env, capture_output=True, text=True, check=False, timeout=300,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return RefreshResult("stale", head, base, f"Graphify refresh failed: {exc}")
        staged_graph = stage / GRAPH_NAME
        if completed.returncode or not staged_graph.is_file():
            detail = (completed.stderr or completed.stdout).strip().splitlines()
            tail = detail[-1] if detail else "no graph produced"
            return RefreshResult("stale", head, base, f"Graphify refresh failed: {tail}")
        try:
            candidate = json.loads(staged_graph.read_text(encoding="utf-8"))
            if not candidate.get("nodes"):
                raise ValueError("empty graph")
            for node in candidate["nodes"]:
                source = node.get("source_file", "")
                if source and not selected(str(source)):
                    raise ValueError(f"out-of-scope graph source: {source}")
        except (OSError, ValueError, TypeError) as exc:
            return RefreshResult("stale", head, base, f"Graphify output failed validation: {exc}")
        os.replace(staged_graph, graph)
        for name in ("GRAPH_REPORT.md", "graph.html", ".graphify_analysis.json"):
            artifact = stage / name
            if artifact.is_file():
                os.replace(artifact, output / name)
        _write_state(root, head, graph)
    return RefreshResult("fresh", head, head)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check or query the merge-maintained Graphify index")
    parser.add_argument("command", choices=("status", "refresh", "query"))
    parser.add_argument("question", nargs="*")
    args = parser.parse_args(argv)
    root = Path.cwd()
    state = refresh_after_merge(root) if args.command == "refresh" else status(root)
    print(
        f"Graphify index: {state.status} (HEAD {state.head or 'unknown'}, indexed {state.indexed_commit or 'none'})",
        flush=True,
    )
    if state.warning:
        print(state.warning, file=sys.stderr)
    if args.command == "status":
        return 0 if state.status == "fresh" else 1
    if state.status != "fresh":
        print("Refusing to query a stale Graphify index.", file=sys.stderr)
        return 1
    if not args.question:
        parser.error("query requires a question")
    launcher = shutil.which("graphify")
    if not launcher:
        print("Graphify CLI is unavailable", file=sys.stderr)
        return 1
    env = dict(os.environ)
    env["GRAPHIFY_OUT"] = "graphify-out"
    return subprocess.run(
        [launcher, "query", " ".join(args.question)], cwd=root, env=env, check=False
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
