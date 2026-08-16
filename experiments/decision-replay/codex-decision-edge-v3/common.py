"""Shared, standard-library-only helpers for the Codex decision-edge replay."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import tarfile
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
TASK_PATH = HERE / "task" / "TASK.md"
SOURCE_REVISION = "21749f40e1173d0862201921ff6f41de24f3b914"
WITHHELD_REVISION = "0ba56be3b08a2fcf44090e90e754da3350526045"
RELEVANT_ENTRY_ID = "mse_j55kt6mq230zj2p4"
ARMS = ("no-dated-memory", "historical-available", "relevant-rationale-pushed")
BLOCK_COUNT = 8

REMOVED_DOCUMENT = Path("docs/3_Spec/draft/decision-level-link-sidecar-refs.md")
COMMENT_PATH = Path("memory_seed/retrieval.py")
CODEX_CONTRACT_PATH = Path("CODEX_EXPERIMENT_CONTRACT.md")
FIXTURE_TEST_RUNNER_PATH = Path("RUN_TASK_TESTS.py")
FIXTURE_TEST_RUNNER = """\
\"\"\"Run only the candidate-authored decision-edge regression module.\"\"\"

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MEMORY_TRACE = ROOT / "memory-trace"
TEST_FILE = MEMORY_TRACE / "tests" / "test_trail_decision_edges.py"

# The fixture owns its imports. Do not depend on PYTHONPATH inherited from the
# dispatch shell or an installed package outside this standalone repository.
sys.path.insert(0, str(MEMORY_TRACE))


def main() -> int:
    if not TEST_FILE.is_file():
        print(f"candidate test module is missing: {TEST_FILE}", file=sys.stderr)
        return 1
    spec = importlib.util.spec_from_file_location("candidate_task_tests", TEST_FILE)
    if spec is None or spec.loader is None:
        print(f"cannot load candidate test module: {TEST_FILE}", file=sys.stderr)
        return 1
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
"""
PROJECT_AGENT_CONFIG_SURFACES = (
    Path(".codex"),
    Path(".claude"),
    Path(".cursor"),
    Path(".gemini"),
    Path(".vscode"),
    Path(".mcp.json"),
    Path(".github/mcp.json"),
    Path(".github/hooks"),
    Path(".github/copilot-instructions.md"),
)
INERT_SOURCE_AGENT_NAME_MATCHES = {
    "memory-trace/client/src/SettingsMenu.stories.tsx": "UI component source",
    "memory-trace/client/src/SettingsMenu.tsx": "UI component source",
    "memory_seed/mcp_server.py": "package implementation source",
    "memory_seed/mcp_validate.py": "package implementation source",
    "memory_seed/seed/.claude/settings.json": "inactive seed template",
    "memory_seed/seed/.github/copilot-instructions.md": "inactive seed template",
    "scripts/launch-memory-trace.ps1": "manually invoked repository script",
    "tests/test_git_hooks.py": "test source",
    "tests/test_mcp_merge.py": "test source",
    "tests/test_mcp_server.py": "test source",
    "tests/test_mcp_session_append.py": "test source",
    "tests/test_mcp_session_integrate.py": "test source",
    "tests/test_mcp_validation.py": "test source",
}
CODEX_EXPERIMENT_CONTRACT = """# Codex experiment contract

This is a standalone historical fixture. Work only inside this fixture and only on the paths allowed
by `TASK.md`.

- Do not use the network, remotes, user-level connectors, user-level MCP servers, another checkout,
  another fixture, or external history.
- Do not ask another tool or agent to read or modify anything outside this fixture.
- Treat any externally supplied repository or rationale content as out of protocol.

All exported project-level agent configuration surfaces are removed from this fixture, including the
narrow GitHub MCP, hooks, and Copilot-instructions surfaces. Instrument limitation: that structural
removal cannot programmatically disable a Codex collaboration subagent's user-level tool inventory or
connectors. The subject is therefore instructed not to use them. Any external or cross-fixture tool use
is an exclusion and must be reported by the runner.
"""
ANSWER_BEARING_COMMENT = (
    b"            # Entry-level refs keep their existing keys unchanged. Decision\n"
    b"            # refs are collected separately and NEVER folded into them: \"D2 of\n"
    b"            # B supersedes D1 of A\" does not license \"B supersedes A\", so a\n"
    b"            # consumer that does not model decisions must see exactly the edge\n"
    b"            # set it saw before this feature existed.\n"
)
DECISIVE_PHRASE = '"D2 of B supersedes D1 of A" does not license "B supersedes A"'


def _git_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_INDEX_FILE",
    ):
        environment.pop(name, None)
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return environment


def run(
    command: list[str],
    *,
    cwd: Path,
    input_bytes: bytes | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command,
        cwd=cwd,
        input=input_bytes,
        capture_output=True,
        check=check,
        env=_git_environment(),
    )


def primary_checkout_root(repo_root: Path = REPO_ROOT) -> Path:
    """Resolve the repository's primary checkout, even when the harness runs in a worktree."""

    listing = run(["git", "worktree", "list", "--porcelain"], cwd=repo_root).stdout.decode("utf-8")
    for line in listing.splitlines():
        if line.startswith("worktree "):
            return Path(line.removeprefix("worktree ")).resolve()
    raise RuntimeError("git worktree list did not identify a primary checkout")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def verify_source_relationship(repo_root: Path = REPO_ROOT) -> dict[str, str]:
    source = run(["git", "rev-parse", f"{SOURCE_REVISION}^{{commit}}"], cwd=repo_root)
    withheld = run(["git", "rev-parse", f"{WITHHELD_REVISION}^{{commit}}"], cwd=repo_root)
    parent = run(["git", "rev-parse", f"{WITHHELD_REVISION}^"], cwd=repo_root)
    resolved = {
        "source_revision": source.stdout.decode("ascii").strip(),
        "withheld_revision": withheld.stdout.decode("ascii").strip(),
        "withheld_parent": parent.stdout.decode("ascii").strip(),
    }
    if resolved["source_revision"] != SOURCE_REVISION:
        raise RuntimeError("source revision did not resolve exactly")
    if resolved["withheld_revision"] != WITHHELD_REVISION:
        raise RuntimeError("withheld revision did not resolve exactly")
    if resolved["withheld_parent"] != SOURCE_REVISION:
        raise RuntimeError("source revision is not the withheld commit's direct parent")
    return resolved


def _validated_member_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"unsafe archive member path: {name!r}")
    if path.parts and ":" in path.parts[0]:
        raise RuntimeError(f"unsafe archive member drive path: {name!r}")
    return path


def safe_extract_tar(payload: bytes, destination: Path) -> None:
    """Extract regular files/directories only; links and traversal fail closed."""

    destination.mkdir(parents=True, exist_ok=False)
    destination_root = destination.resolve()
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
        for member in archive.getmembers():
            member_path = _validated_member_path(member.name)
            target = destination.joinpath(*member_path.parts)
            resolved_parent = target.parent.resolve()
            if resolved_parent != destination_root and destination_root not in resolved_parent.parents:
                raise RuntimeError(f"archive member escapes destination: {member.name!r}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise RuntimeError(f"unsupported archive member type: {member.name!r}")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise RuntimeError(f"archive member has no payload: {member.name!r}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                shutil.copyfileobj(extracted, handle)


def export_source(destination: Path, repo_root: Path = REPO_ROOT) -> None:
    archive = run(["git", "archive", "--format=tar", SOURCE_REVISION], cwd=repo_root).stdout
    safe_extract_tar(archive, destination)


def _removed_lines(payload: bytes, *, starting_line: int = 1) -> list[dict[str, Any]]:
    return [
        {"line_number": number, "sha256": sha256_bytes(line), "byte_length": len(line)}
        for number, line in enumerate(payload.splitlines(keepends=True), start=starting_line)
    ]


def assert_no_active_project_agent_config(root: Path) -> None:
    """Fail if any known project-level agent configuration surface exists."""

    survivors = [surface.as_posix() for surface in PROJECT_AGENT_CONFIG_SURFACES if (root / surface).exists()]
    if survivors:
        raise RuntimeError(f"active project agent configuration survived isolation: {survivors}")


def sanitize_source(root: Path) -> dict[str, Any]:
    document_path = root / REMOVED_DOCUMENT
    comment_path = root / COMMENT_PATH
    if not document_path.is_file() or not comment_path.is_file():
        raise RuntimeError("source tree lacks a required sanitation target")
    document_bytes = document_path.read_bytes()
    comment_bytes = comment_path.read_bytes()
    if comment_bytes.count(ANSWER_BEARING_COMMENT) != 1:
        raise RuntimeError("exact answer-bearing comment was not found exactly once")
    comment_offset = comment_bytes.index(ANSWER_BEARING_COMMENT)
    comment_starting_line = comment_bytes[:comment_offset].count(b"\n") + 1
    transformed_comment = comment_bytes.replace(ANSWER_BEARING_COMMENT, b"", 1)
    document_path.unlink()
    comment_path.write_bytes(transformed_comment)
    transformations: list[dict[str, Any]] = [
        {
            "path": REMOVED_DOCUMENT.as_posix(),
            "action": "delete-file",
            "original_sha256": sha256_bytes(document_bytes),
            "transformed_sha256": None,
            "removed_lines": _removed_lines(document_bytes),
        },
        {
            "path": COMMENT_PATH.as_posix(),
            "action": "remove-exact-comment",
            "original_sha256": sha256_bytes(comment_bytes),
            "transformed_sha256": sha256_bytes(transformed_comment),
            "removed_lines": _removed_lines(
                ANSWER_BEARING_COMMENT,
                starting_line=comment_starting_line,
            ),
        },
    ]
    for surface in PROJECT_AGENT_CONFIG_SURFACES:
        surface_path = root / surface
        if not surface_path.exists():
            raise RuntimeError(f"source tree lacks required project agent surface: {surface.as_posix()}")
        files = [surface_path] if surface_path.is_file() else sorted(
            (path for path in surface_path.rglob("*") if path.is_file()),
            key=lambda path: path.as_posix(),
        )
        for config_path in files:
            relative = config_path.relative_to(root)
            config_bytes = config_path.read_bytes()
            transformations.append(
                {
                    "path": relative.as_posix(),
                    "action": "delete-project-agent-surface-file",
                    "original_sha256": sha256_bytes(config_bytes),
                    "transformed_sha256": None,
                    "removed_lines": _removed_lines(config_bytes),
                }
            )
        if surface_path.is_dir():
            shutil.rmtree(surface_path)
        else:
            surface_path.unlink()
    contract_bytes = CODEX_EXPERIMENT_CONTRACT.encode("utf-8")
    (root / CODEX_CONTRACT_PATH).write_bytes(contract_bytes)
    transformations.append(
        {
            "path": CODEX_CONTRACT_PATH.as_posix(),
            "action": "add-fixture-local-agent-contract",
            "original_sha256": None,
            "transformed_sha256": sha256_bytes(contract_bytes),
            "removed_lines": [],
        }
    )
    runner_bytes = FIXTURE_TEST_RUNNER.encode("utf-8")
    (root / FIXTURE_TEST_RUNNER_PATH).write_bytes(runner_bytes)
    transformations.append(
        {
            "path": FIXTURE_TEST_RUNNER_PATH.as_posix(),
            "action": "add-fixture-local-task-test-runner",
            "original_sha256": None,
            "transformed_sha256": sha256_bytes(runner_bytes),
            "removed_lines": [],
        }
    )
    assert_no_active_project_agent_config(root)
    inert_audit: list[dict[str, str]] = []
    for relative, classification in INERT_SOURCE_AGENT_NAME_MATCHES.items():
        if not (root / relative).is_file():
            raise RuntimeError(f"declared inert source audit match is missing: {relative}")
        inert_audit.append({"path": relative, "classification": classification})
    manifest = {
        "schema_version": 1,
        "source_revision": SOURCE_REVISION,
        "transformations": transformations,
        "agent_surface_audit": {
            "declared_removed_surfaces": [
                surface.as_posix() for surface in PROJECT_AGENT_CONFIG_SURFACES
            ],
            "remaining_inert_source_or_template_matches": inert_audit,
        },
    }
    write_json(root / "fixture-transformation.json", manifest)
    return manifest


def tree_hashes(root: Path, *, excluded_paths: Iterable[str] = ()) -> dict[str, str]:
    excluded = frozenset(excluded_paths)
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative == ".git" or relative.startswith(".git/"):
            continue
        if relative in excluded:
            continue
        hashes[relative] = sha256_file(path)
    return hashes


def tree_digest(hashes: dict[str, str]) -> str:
    payload = json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(payload)


def assert_cross_arm_equality(
    fixtures: Iterable[Path],
    *,
    allowed_treatment_paths: Iterable[str],
) -> str:
    paths = list(fixtures)
    if not paths:
        raise ValueError("at least one fixture is required")
    allowed = frozenset(allowed_treatment_paths)
    if "EXPERIMENT_CONTEXT.md" not in allowed:
        raise ValueError("allowed treatment paths must name EXPERIMENT_CONTEXT.md")
    reference = tree_hashes(paths[0], excluded_paths=allowed)
    for candidate in paths[1:]:
        observed = tree_hashes(candidate, excluded_paths=allowed)
        if observed != reference:
            missing = sorted(set(reference) - set(observed))
            extra = sorted(set(observed) - set(reference))
            changed = sorted(
                path for path in set(reference) & set(observed) if reference[path] != observed[path]
            )
            raise RuntimeError(
                "unexpected cross-arm difference: "
                f"fixture={candidate.name} missing={missing[:5]} extra={extra[:5]} "
                f"changed={changed[:5]}"
            )
    return tree_digest(reference)


def dated_session_documents(root: Path) -> list[Path]:
    """Return all Markdown artifacts beneath the dated session-memory store."""

    sessions = root / ".memory-seed" / "sessions"
    if not sessions.exists():
        return []
    return sorted(path for path in sessions.rglob("*.md") if path.is_file())


def strip_dated_session_memory(root: Path) -> list[str]:
    documents = dated_session_documents(root)
    removed = [path.relative_to(root).as_posix() for path in documents]
    for path in documents:
        path.unlink()
    sessions = root / ".memory-seed" / "sessions"
    for directory in sorted(
        (path for path in sessions.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        try:
            directory.rmdir()
        except OSError:
            pass
    return removed


def normalize_exposure(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text)
    folded = folded.translate(
        str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-"})
    )
    return " ".join(folded.split())


def assert_no_decisive_phrase(root: Path) -> None:
    needle = normalize_exposure(DECISIVE_PHRASE)
    matches: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith(".git/") or relative == "EXPERIMENT_CONTEXT.md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if needle in normalize_exposure(text):
            matches.append(relative)
    if matches:
        raise RuntimeError(f"decisive phrase survived no-memory sanitation: {matches}")


def initialize_fixture(root: Path) -> str:
    run(["git", "init", "-b", "main"], cwd=root)
    run(["git", "config", "user.name", "Memory Seed Codex Replay"], cwd=root)
    run(["git", "config", "user.email", "replay@example.invalid"], cwd=root)
    run(["git", "config", "core.hooksPath", ".git/no-hooks"], cwd=root)
    (root / ".git" / "no-hooks").mkdir(exist_ok=True)
    run(["git", "add", "-A"], cwd=root)
    run(
        ["git", "-c", "commit.gpgsign=false", "commit", "-m", "fixture: historical starting point"],
        cwd=root,
    )
    commit = run(["git", "rev-parse", "HEAD"], cwd=root).stdout.decode("ascii").strip()
    assert_object_isolation(root)
    if run(["git", "status", "--porcelain"], cwd=root).stdout:
        raise RuntimeError(f"fixture did not start clean: {root}")
    return commit


def assert_object_isolation(root: Path) -> None:
    for revision in (SOURCE_REVISION, WITHHELD_REVISION):
        result = run(["git", "cat-file", "-e", f"{revision}^{{commit}}"], cwd=root, check=False)
        if result.returncode == 0:
            raise RuntimeError(f"historical object unexpectedly resolves in fixture: {revision}")
