from __future__ import annotations

import json
import subprocess
import time
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

import memory_seed.corpus_cache as corpus_cache
from memory_seed.corpus_cache import CorpusSnapshot, _Lease, _git_identity, get_corpus_snapshot
from memory_seed.core import resolve_runtime
from memory_seed.retrieval import (
    augment_chunks_with_link_sidecars, augment_chunks_with_topic_sidecars, load_corpus,
)
from memory_seed.semantic_cache import ContinuityBlock, MemoryChunk, extract_memory_chunks


def test_snapshot_exposes_immutable_empty_views():
    snapshot = CorpusSnapshot.empty(origin="isolated")

    assert snapshot.origin == "isolated"
    assert snapshot.chunks("entry", "raw") == ()


def _project(tmp_path: Path) -> Path:
    (tmp_path / ".memory-seed" / "sessions").mkdir(parents=True)
    (tmp_path / ".memory-seed" / "sessions" / "2026-01-01.md").write_text(
        "## 2026-01-01 09:00 - Source\n\n```yaml\nentry_id: source\n```\n\n### Decision\n\n- D: source\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True)
    return tmp_path


def _views(marker: str = "one"):
    chunk = MemoryChunk(
        chunk_id=marker, source_path=".memory-seed/sessions/2026-01-01.md", source_file="2026-01-01.md",
        session_date=date(2026, 1, 1), entry_datetime=None, heading_path=("entry",), heading_level=2,
        title=marker, text="text", tags=("tag",), contexts=("context",), lexical_terms=("term",),
        start_line=1, end_line=2, entry_id=marker, decision_edges=(("evolves", "d1", "old", "d2", ""),),
        continuity=(ContinuityBlock("rename", "old", "new"),), inferred_topics=("topic",),
        inferred_decision_topics=(("d1", "topic"),), entry_line_range=(1, 2), sections=("Decision",),
    )
    augmented = replace(chunk, replaces=("old",), inferred_topics=("sidecar-topic",))
    return {(granularity, view): (augmented if view == "augmented" else chunk,)
            for granularity in ("entry", "section", "decision") for view in ("raw", "augmented")}


def test_cold_cache_is_exact_and_warm_hit_skips_source_builder(tmp_path):
    project = _project(tmp_path / "project")
    cache = tmp_path / "cache"
    calls = []

    def build(_cwd):
        calls.append(1)
        return _views()

    cold = get_corpus_snapshot(project, cache_dir=cache, source_builder=build)
    warm = get_corpus_snapshot(project, cache_dir=cache, source_builder=build)

    assert cold.chunks("decision", "raw") == _views()["decision", "raw"]
    assert cold.chunks("section", "augmented") == _views()["section", "augmented"]
    assert warm.chunks("entry", "augmented") == cold.chunks("entry", "augmented")
    assert calls == [1]
    assert warm.origin == "persistent"
    assert not list(cache.glob("*.tmp"))
    assert not list(cache.glob("*.lease"))


def test_default_builder_is_field_exact_to_the_canonical_uncached_reader(tmp_path):
    project = _project(tmp_path / "project")
    snapshot = get_corpus_snapshot(project, cache_dir=tmp_path / "cache")

    for granularity in ("entry", "section", "decision"):
        raw = tuple(extract_memory_chunks(project, granularity=granularity))
        augmented = tuple(augment_chunks_with_topic_sidecars(augment_chunks_with_link_sidecars(raw, project), project))
        assert snapshot.chunks(granularity, "raw") == raw
        assert snapshot.chunks(granularity, "augmented") == augmented


@pytest.mark.parametrize("relative", [
    ".memory-seed/sessions/2026-01-02.md",
    ".memory-seed/sessions/links/2026-01-01.md",
    ".memory-seed/sessions/topics/2026-01-01.md",
    ".memory-seed/project.yaml",
])
def test_relevant_source_changes_invalidate_the_projection(tmp_path, relative):
    project = _project(tmp_path / "project")
    cache = tmp_path / "cache"
    calls = []
    build = lambda _cwd: (calls.append(1) or _views(str(len(calls))))
    get_corpus_snapshot(project, cache_dir=cache, source_builder=build)
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("changed\n", encoding="utf-8")
    rebuilt = get_corpus_snapshot(project, cache_dir=cache, source_builder=build)

    assert calls == [1, 1]
    assert rebuilt.chunks("entry", "raw")[0].chunk_id == "2"


def test_corruption_and_replace_failure_reconstruct_without_failing_consumers(tmp_path):
    project = _project(tmp_path / "project")
    cache = tmp_path / "cache"
    calls = []
    build = lambda _cwd: (calls.append(1) or _views())
    get_corpus_snapshot(project, cache_dir=cache, source_builder=build)
    artifact = next(cache.glob("*.json"))
    artifact.write_text("{not json", encoding="utf-8")
    rebuilt = get_corpus_snapshot(project, cache_dir=cache, source_builder=build)
    assert rebuilt.chunks("entry", "raw") == _views()["entry", "raw"]
    assert calls == [1, 1]

    failed = get_corpus_snapshot(
        project, cache_dir=tmp_path / "bad-cache", source_builder=build,
        replace=lambda _source, _target: (_ for _ in ()).throw(PermissionError()),
    )
    assert failed.chunks("decision", "augmented") == _views()["decision", "augmented"]
    assert failed.origin == "isolated"


@pytest.mark.parametrize("mutation", [
    lambda document: document.update(schema_version=999),
    lambda document: document["views"]["entry/raw"][0].pop("source_path"),
    lambda document: document["views"].pop("section/raw"),
])
def test_schema_or_wrong_field_artifacts_reconstruct(tmp_path, mutation):
    project = _project(tmp_path / "project")
    cache = tmp_path / "cache"
    calls = []
    build = lambda _cwd: (calls.append(1) or _views())
    get_corpus_snapshot(project, cache_dir=cache, source_builder=build)
    artifact = next(cache.glob("*.json"))
    document = json.loads(artifact.read_text(encoding="utf-8"))
    mutation(document)
    artifact.write_text(json.dumps(document), encoding="utf-8")

    snapshot = get_corpus_snapshot(project, cache_dir=cache, source_builder=build)
    assert snapshot.chunks("entry", "raw") == _views()["entry", "raw"]
    assert calls == [1, 1]


@pytest.mark.parametrize("mutation", [
    lambda document: document["views"]["decision/raw"][0].update(text="tampered"),
    lambda document: document["views"]["entry/augmented"][0].update(replaces=["different"]),
    lambda document: document["views"]["section/raw"][0].update(tags=["second", "tag"]),
])
def test_valid_looking_view_tampering_reconstructs(tmp_path, mutation):
    project = _project(tmp_path / "project")
    cache = tmp_path / "cache"
    calls = []
    build = lambda _cwd: (calls.append(1) or _views())
    get_corpus_snapshot(project, cache_dir=cache, source_builder=build)
    artifact = next(cache.glob("*.json"))
    document = json.loads(artifact.read_text(encoding="utf-8"))
    mutation(document)
    artifact.write_text(json.dumps(document), encoding="utf-8")

    snapshot = get_corpus_snapshot(project, cache_dir=cache, source_builder=build)
    assert snapshot.chunks("decision", "raw") == _views()["decision", "raw"]
    assert calls == [1, 1]


def test_payload_serialization_failure_keeps_the_authoritative_snapshot_usable(tmp_path, monkeypatch):
    project = _project(tmp_path / "project")
    cache = tmp_path / "cache"
    monkeypatch.setattr(corpus_cache, "_payload", lambda *_args: (_ for _ in ()).throw(TypeError("not json")))

    snapshot = get_corpus_snapshot(project, cache_dir=cache, source_builder=lambda _cwd: _views())
    assert snapshot.chunks("entry", "augmented") == _views()["entry", "augmented"]
    assert snapshot.origin == "isolated"
    assert not list(cache.glob("*.json"))
    assert not list(cache.glob("*.tmp"))
    assert not list(cache.glob("*.lease"))


def test_lease_release_does_not_remove_a_replaced_owner_token(tmp_path):
    lease = _Lease(tmp_path / "snapshot.json")
    assert lease.acquire()
    lease.path.write_text("replacement-owner", encoding="utf-8")
    lease.release()
    assert lease.path.read_text(encoding="utf-8") == "replacement-owner"


def test_head_change_and_runtime_keys_never_reuse_another_projection(tmp_path):
    first = _project(tmp_path / "first")
    second = _project(tmp_path / "second")
    cache = tmp_path / "cache"
    first_calls, second_calls = [], []
    get_corpus_snapshot(first, cache_dir=cache, source_builder=lambda _cwd: (first_calls.append(1) or _views("first")))
    get_corpus_snapshot(second, cache_dir=cache, source_builder=lambda _cwd: (second_calls.append(1) or _views("second")))
    assert len(list(cache.glob("*.json"))) == 2

    (first / "HEAD-change.txt").write_text("rewrite", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=first, check=True)
    subprocess.run(["git", "commit", "-qm", "rewrite"], cwd=first, check=True)
    rebuilt = get_corpus_snapshot(first, cache_dir=cache, source_builder=lambda _cwd: (first_calls.append(1) or _views("rewritten")))
    assert rebuilt.chunks("entry", "raw")[0].chunk_id == "rewritten"
    assert first_calls == [1, 1]
    assert second_calls == [1]


def test_bounded_lease_contention_returns_isolated_authoritative_snapshot(tmp_path):
    project = _project(tmp_path / "project")
    cache = tmp_path / "cache"
    runtime = resolve_runtime(project)
    identity = _git_identity(runtime.workspace_root, runtime.memory_dir)
    assert identity is not None
    key = __import__("hashlib").sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    cache.mkdir()
    (cache / f"{key}.json.lease").write_text("other process", encoding="utf-8")
    snapshot = get_corpus_snapshot(project, cache_dir=cache, source_builder=lambda _cwd: _views())
    assert snapshot.origin == "isolated"
    assert snapshot.chunks("decision", "augmented") == _views()["decision", "augmented"]
    assert list(cache.glob("*.json")) == []


def test_no_git_never_reads_or_publishes_a_persistent_artifact(tmp_path):
    project = tmp_path / "plain"
    (project / ".memory-seed" / "sessions").mkdir(parents=True)
    cache = tmp_path / "cache"
    snapshot = get_corpus_snapshot(project, cache_dir=cache, source_builder=lambda _cwd: _views())

    assert snapshot.origin == "isolated"
    assert not cache.exists()


def test_moving_source_retries_once_then_returns_isolated(tmp_path):
    project = _project(tmp_path / "project")
    cache = tmp_path / "cache"
    calls = []

    def moving(_cwd):
        calls.append(1)
        (project / ".memory-seed" / "sessions" / "2026-01-01.md").write_text(str(len(calls)), encoding="utf-8")
        return _views(str(len(calls)))

    snapshot = get_corpus_snapshot(project, cache_dir=cache, source_builder=moving)
    assert snapshot.origin == "isolated"
    assert calls == [1, 1]
    assert not cache.exists()


def test_supplied_snapshot_prevents_a_second_load(tmp_path):
    project = _project(tmp_path / "project")
    snapshot = get_corpus_snapshot(project, cache_dir=tmp_path / "cache", source_builder=lambda _cwd: _views())

    assert load_corpus(project, "section", snapshot=snapshot) == list(snapshot.chunks("section", "augmented"))
    assert load_corpus(project, "section", view="raw", snapshot=snapshot) == list(snapshot.chunks("section", "raw"))


def test_measurement_records_cold_warm_build_reduction(tmp_path):
    project = _project(tmp_path / "project")
    cache = tmp_path / "cache"
    builds = []
    builder = lambda _cwd: (builds.append(1) or _views())
    started = time.perf_counter()
    cold = get_corpus_snapshot(project, cache_dir=cache, source_builder=builder)
    cold_elapsed = time.perf_counter() - started
    started = time.perf_counter()
    warm = get_corpus_snapshot(project, cache_dir=cache, source_builder=builder)
    warm_elapsed = time.perf_counter() - started
    print(f"corpus-cache measurement cold={cold_elapsed:.6f}s warm={warm_elapsed:.6f}s source_builds={len(builds)}")

    assert cold.chunks("decision", "augmented") == warm.chunks("decision", "augmented")
    assert builds == [1]
