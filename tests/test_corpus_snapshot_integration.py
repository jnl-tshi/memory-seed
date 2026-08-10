"""ESR consumes one authoritative in-memory corpus without mutating its cache."""

from __future__ import annotations

import subprocess
import json
import time
from pathlib import Path

import memory_seed.corpus_cache as corpus_cache
from memory_seed.esr import esr_report


def _project(tmp_path: Path) -> Path:
    (tmp_path / ".memory-seed" / "sessions").mkdir(parents=True)
    (tmp_path / ".memory-seed" / "sessions" / "2026-01-01.md").write_text(
        "## 2026-01-01 09:00 - Source\n\n```yaml\nentry_id: mse_source\n```\n\n### Decision\n\n- D: source\n- R: source\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True)
    return tmp_path


def test_esr_builds_one_live_snapshot_and_never_creates_a_missing_cache(tmp_path, monkeypatch):
    project = _project(tmp_path / "project")
    cache = tmp_path / "missing-cache"
    monkeypatch.setenv("MEMORY_SEED_CORPUS_CACHE_DIR", str(cache))
    real = corpus_cache._default_source_builder
    builds: list[Path] = []

    def counted(cwd):
        builds.append(Path(cwd))
        return real(cwd)

    monkeypatch.setattr(corpus_cache, "_default_source_builder", counted)
    started = time.perf_counter()
    report = esr_report(project, session_date="2026-01-01")
    elapsed = time.perf_counter() - started
    print(json.dumps({"measurement": "esr_snapshot", "elapsed_seconds": elapsed, "source_builds": len(builds)}))

    assert builds == [project]
    assert report.corpus_cache["health"] == "missing"
    assert report.corpus_cache["reconstruction_required"] is True
    assert not cache.exists()


def test_esr_conclusions_are_cache_state_independent(tmp_path, monkeypatch):
    project = _project(tmp_path / "project")
    cache = tmp_path / "cache"
    monkeypatch.setenv("MEMORY_SEED_CORPUS_CACHE_DIR", str(cache))
    corpus_cache.get_corpus_snapshot(project, cache_dir=cache)
    current = esr_report(project, session_date="2026-01-01").to_dict()
    artifact = next(cache.glob("*.json"))
    artifact.unlink()
    missing = esr_report(project, session_date="2026-01-01").to_dict()
    corpus_cache.get_corpus_snapshot(project, cache_dir=cache)
    artifact = next(cache.glob("*.json"))
    artifact.write_text("{broken", encoding="utf-8")
    corrupt = esr_report(project, session_date="2026-01-01").to_dict()

    for payload in (current, missing, corrupt):
        payload.pop("corpus_cache")
    assert current == missing == corrupt
