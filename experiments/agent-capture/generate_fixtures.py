"""Generate agent-capture fixture templates (L0-L3) from a real memory-seed install.

Each fixture is a standalone git repo containing the stub `strutil` project plus a Memory Seed
runtime at one of four scaffolding levels. Levels are produced by running the REAL
`init_project()` and then applying documented strips - never by hand-assembling a runtime -
so results generalise to actual installs. See PREREGISTRATION.md for what each level tests.

Hazards this script exists to respect (verified in code, see the plan):
  H1  every fixture gets its own .memory-seed/ (resolve_runtime walks upward with no boundary)
  H2  `git init` runs BEFORE init_project so the commit hook lands in the fixture's .git
  H4  the fixture's .mcp.json pins the local working tree via absolute interpreter + PYTHONPATH
  H5  the stock seed topics.yaml is kept - the decisions envelope requires a vocabulary
  H6  identical hand-written index.md/policy.md stubs so bootstrap mode never fires
  H8  init_project() (Python) does not write integration_mode; we append it for CLI parity

Usage:
  python experiments/agent-capture/generate_fixtures.py [--agent claude] [--levels L0,L1,L2,L3]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from memory_seed.core import init_project  # noqa: E402

STUBS = HERE / "stubs"
TEMPLATES = HERE / "templates"

LEVELS = ("L0", "L1", "L2", "L3")

LEVEL_DESCRIPTIONS = {
    "L0": "MCP write path only: store + topics.yaml + .mcp.json. No routing files, no rules, no hooks.",
    "L1": "L0 plus a single hand-written AGENTS.md line naming the store.",
    "L2": "Full install (routing files, agent-rules contract, skills registry) with all hooks removed.",
    "L3": "Full stock install, untouched: rules, skills, agent hooks, and the git commit hook.",
}


def rmtree_force(path: Path) -> None:
    """rmtree that clears the Windows read-only bit git sets on object files."""

    def _onerror(func, target, _exc_info):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    shutil.rmtree(path, onerror=_onerror)


def run_git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _delete(fixture: Path, relative: str, log: list[str]) -> None:
    target = fixture / relative
    if not target.exists():
        return
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    log.append(f"deleted {relative}")


def _write_local_mcp(fixture: Path, log: list[str]) -> None:
    """Pin the MCP server to the local working tree (H4).

    Stock init writes `uvx --from memory-seed`, which resolves the published PyPI package.
    The experiment tests the local code, so we bake the generating interpreter and the repo
    root's PYTHONPATH. `python -m` also prepends the process cwd to sys.path, but the process
    cwd is the FIXTURE (the client spawns the server there), so PYTHONPATH is what finds the
    local package.
    """
    payload = {
        "mcpServers": {
            "memory-seed": {
                "command": sys.executable,
                "args": ["-m", "memory_seed.mcp_server", "--stdio"],
                "env": {"PYTHONPATH": str(REPO_ROOT)},
            }
        }
    }
    (fixture / ".mcp.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    log.append(".mcp.json rewritten to local working tree (absolute interpreter + PYTHONPATH)")


def _strip_claude_hooks(fixture: Path, log: list[str]) -> None:
    settings_path = fixture / ".claude" / "settings.json"
    if not settings_path.exists():
        return
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    if "hooks" in settings:
        del settings["hooks"]
        if settings:
            settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
            log.append(".claude/settings.json: hooks key removed")
        else:
            settings_path.unlink()
            log.append(".claude/settings.json deleted (contained only hooks)")


def _append_integration_mode(fixture: Path, log: list[str]) -> None:
    project_yaml = fixture / ".memory-seed" / "project.yaml"
    if project_yaml.exists():
        text = project_yaml.read_text(encoding="utf-8")
        if "integration_mode" not in text:
            if not text.endswith("\n"):
                text += "\n"
            project_yaml.write_text(text + "integration_mode: local-merge\n", encoding="utf-8")
            log.append("project.yaml: integration_mode: local-merge appended (H8)")


def _install_stubs(fixture: Path, log: list[str]) -> None:
    memory_dir = fixture / ".memory-seed"
    memory_dir.mkdir(exist_ok=True)
    for name in ("index.md", "policy.md"):
        shutil.copyfile(STUBS / name, memory_dir / name)
        log.append(f".memory-seed/{name} written from stubs/ (byte-identical across levels, H6)")


def build_fixture(level: str, agent: str) -> Path:
    fixture = TEMPLATES / f"{agent}-{level}"
    if fixture.exists():
        rmtree_force(fixture)
    fixture.mkdir(parents=True)
    log: list[str] = []

    # 1. Stub project content.
    shutil.copytree(STUBS / "project", fixture, dirs_exist_ok=True)
    log.append("stub strutil project copied")

    # 2. Own git repo BEFORE init, so install_git_hooks lands here (H2).
    run_git(fixture, "init", "-b", "main")
    run_git(fixture, "config", "user.email", "fixture@agent-capture.local")
    run_git(fixture, "config", "user.name", "Agent Capture Fixture")
    log.append("standalone git repo initialised before init_project (H2)")

    # 3. Real install.
    if level in ("L0", "L1"):
        init_project(cwd=fixture, agents={agent}, skill_profiles=set())
        log.append(f"init_project(agents={{{agent!r}}}, skill_profiles=set())")
    else:
        init_project(cwd=fixture, agents={agent})
        log.append(f"init_project(agents={{{agent!r}}}) - full install")

    # 4. Per-level strips.
    if level in ("L0", "L1"):
        for relative in (
            "AGENTS.md",
            "CLAUDE.md",
            ".agents",
            ".claude",
            ".memory-seed/agent-rules.md",
            ".memory-seed/project-bootstrap.md",
            ".memory-seed/skills",
            ".memory-seed/hooks",
            ".memory-seed/archive",
            ".git/hooks/prepare-commit-msg",
        ):
            _delete(fixture, relative, log)
    if level == "L1":
        shutil.copyfile(STUBS / "AGENTS-L1.md", fixture / "AGENTS.md")
        log.append("AGENTS.md written from stubs/AGENTS-L1.md (single store-naming line)")
    if level == "L2":
        _delete(fixture, ".memory-seed/hooks", log)
        _delete(fixture, ".git/hooks/prepare-commit-msg", log)
        _strip_claude_hooks(fixture, log)
    # L3: untouched.

    # 5. Constant stubs, local MCP pin, integration mode.
    _install_stubs(fixture, log)
    _write_local_mcp(fixture, log)
    _append_integration_mode(fixture, log)

    # 6. Manifest: the fixture's provenance, reviewable in the parent repo via this script.
    manifest = {
        "level": level,
        "agent": agent,
        "description": LEVEL_DESCRIPTIONS[level],
        "generated_by": "experiments/agent-capture/generate_fixtures.py",
        "build_log": log,
    }
    (fixture / "FIXTURE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    # 7. Baseline commit so every run starts from a committed clean tree.
    run_git(fixture, "add", "-A")
    run_git(fixture, "commit", "-m", f"fixture baseline: {agent}-{level}")
    return fixture


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", default="claude")
    parser.add_argument("--levels", default=",".join(LEVELS))
    args = parser.parse_args()

    levels = [item.strip() for item in args.levels.split(",") if item.strip()]
    unknown = [item for item in levels if item not in LEVELS]
    if unknown:
        parser.error(f"unknown levels: {unknown}; valid: {LEVELS}")

    for level in levels:
        fixture = build_fixture(level, args.agent)
        print(f"built {fixture.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
