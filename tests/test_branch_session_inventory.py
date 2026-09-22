"""Regression tests for the read-only branch session inventory."""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.branch_session_inventory import build_inventory, parse_session_text


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _entry(entry_id: str, title: str, branch: str = "topic") -> str:
    return (
        f"## 2026-09-22 10:00 - {title}\n\n"
        f"```yaml\nentry_id: {entry_id}\nbranch: {branch}\n```\n\n"
        f"### Summary\n\n- {title} summary.\n"
    )


def test_parse_session_text_keeps_entry_identity_and_title() -> None:
    entries = parse_session_text(
        _entry("mse_aaaaaaaaaaaaaaaa", "First")
        + "\n"
        + _entry("mse_bbbbbbbbbbbbbbbb", "Second"),
        ".memory-seed/sessions/2026-09/2026-09-22.md",
    )
    assert [entry["id"] for entry in entries] == [
        "mse_aaaaaaaaaaaaaaaa",
        "mse_bbbbbbbbbbbbbbbb",
    ]
    assert entries[1]["title"] == "Second"
    assert entries[1]["authored_branch"] == "topic"


def test_inventory_compares_ids_across_files_and_includes_worktree_edits(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.invalid")
    session = repo / ".memory-seed" / "sessions" / "2026-09" / "2026-09-22.md"
    session.parent.mkdir(parents=True)
    session.write_text(_entry("mse_aaaaaaaaaaaaaaaa", "On main", "main"), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "base")

    _git(repo, "switch", "-qc", "topic")
    branch_session = session.parent / "2026-09-22" / "jnl.md"
    branch_session.parent.mkdir()
    session.rename(branch_session)
    branch_session.write_text(
        branch_session.read_text(encoding="utf-8")
        + "\n"
        + _entry("mse_bbbbbbbbbbbbbbbb", "On topic"),
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "topic change")
    branch_session.write_text(
        branch_session.read_text(encoding="utf-8")
        + "\n"
        + _entry("mse_cccccccccccccccc", "Uncommitted"),
        encoding="utf-8",
    )

    report = build_inventory(repo, base="main", selected=["topic"])
    branch = report["branches"][0]
    assert [entry["id"] for entry in branch["unique_sessions"]] == [
        "mse_bbbbbbbbbbbbbbbb"
    ]
    assert [entry["id"] for entry in branch["authored_sessions"]] == [
        "mse_bbbbbbbbbbbbbbbb"
    ]
    assert branch["ahead"] == 1
    assert branch["worktrees"][0]["dirty_paths"]
    assert [entry["id"] for entry in branch["worktrees"][0]["uncommitted_sessions"]] == [
        "mse_cccccccccccccccc"
    ]
    assert report["base"] == "main"

    detached = tmp_path / "detached"
    _git(repo, "worktree", "add", "-q", "--detach", str(detached), "topic")
    detached_session = detached / ".memory-seed" / "sessions" / "2026-09" / "2026-09-22" / "jnl.md"
    detached_session.write_text(
        detached_session.read_text(encoding="utf-8")
        + "\n"
        + _entry("mse_dddddddddddddddd", "Detached work"),
        encoding="utf-8",
    )
    report = build_inventory(repo, base="main", selected=["topic"])
    assert [entry["id"] for entry in report["detached_worktrees"][0]["unique_sessions"]] == [
        "mse_bbbbbbbbbbbbbbbb"
    ]
    assert [entry["id"] for entry in report["detached_worktrees"][0]["uncommitted_sessions"]] == [
        "mse_dddddddddddddddd"
    ]
