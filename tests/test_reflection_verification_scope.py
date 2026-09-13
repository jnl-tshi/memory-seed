"""Operation-local proof reuse must never become mutable-state admission."""

import pytest

from memory_seed import reflection_ledger as ledger


def test_scope_reuses_success_but_resolves_refs_on_every_load(tmp_path, monkeypatch):
    head = ["a" * 40]
    resolutions, classifications = [], []

    def resolve(root, ref):
        resolutions.append(ref)
        return head[0]

    def classify(root, ref, commit, path):
        result = object()
        classifications.append((root, ref, commit, path, result))
        return result

    monkeypatch.setattr(ledger, "_commit", resolve)
    monkeypatch.setattr(ledger, "_classify_trusted_workstream_ledger", classify)

    def load(root=tmp_path, path="ledger.md"):
        return ledger.load_trusted_workstream_ledger(root, trusted_ref="HEAD", ledger_path=path)

    @ledger.reflection_verification_operation
    def nested():
        return load()

    @ledger.reflection_verification_operation
    def operation():
        first = load()
        assert nested() is first
        head[0] = "b" * 40
        assert load() is not first
        assert load(tmp_path / "other") is not first
        assert load(path="other.md") is not first

    operation()
    assert len(resolutions) == 5
    assert len(classifications) == 4
    assert ledger._TRUSTED_LEDGER_CLASSIFICATION_CONTEXT.get() is None
    assert ledger._REFLECTION_VERIFICATION_CONTEXT.get() is None
    load()
    assert len(classifications) == 5  # a new operation proves history again


def test_failed_classification_is_not_cached_and_exception_discards_scope(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(ledger, "_commit", lambda *args: "a" * 40)

    def fail(*args):
        calls.append(args)
        raise ValueError("invalid history")

    monkeypatch.setattr(ledger, "_classify_trusted_workstream_ledger", fail)

    @ledger.reflection_verification_operation
    def operation():
        for _ in range(2):
            with pytest.raises(ValueError, match="invalid history"):
                ledger.load_trusted_workstream_ledger(tmp_path, trusted_ref="HEAD", ledger_path="ledger.md")
        raise RuntimeError("operation failed")

    with pytest.raises(RuntimeError, match="operation failed"):
        operation()
    assert len(calls) == 2
    assert ledger._TRUSTED_LEDGER_CLASSIFICATION_CONTEXT.get() is None
    assert ledger._REFLECTION_VERIFICATION_CONTEXT.get() is None


def test_layout_reuse_is_bounded_to_exact_objects_and_operation(tmp_path, monkeypatch):
    reads = []

    def read(root, commit):
        reads.append((root, commit))
        return ()

    monkeypatch.setattr(ledger, "_read_reflection_tree_layout", read)

    @ledger.reflection_verification_operation
    def operation():
        for _ in range(3):
            ledger._reflection_tree_layout(tmp_path, "a" * 40)
        for _ in range(2):
            ledger._reflection_tree_layout(tmp_path, "HEAD")
        ledger._reflection_tree_layout(tmp_path / "other", "a" * 40)
        ledger._reflection_tree_layout(tmp_path, "b" * 40)

    operation()
    assert len(reads) == 5
    operation()
    assert len(reads) == 10


def test_operation_memo_limit_does_not_become_aggregate_validation_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "MAX_TRUSTED_LEDGER_CLASSIFICATIONS", 2)
    monkeypatch.setattr(ledger, "_commit", lambda *args: "a" * 40)
    monkeypatch.setattr(ledger, "_classify_trusted_workstream_ledger", lambda *args: object())

    @ledger.reflection_verification_operation
    def operation():
        for index in range(4):
            ledger.load_trusted_workstream_ledger(tmp_path, trusted_ref="HEAD", ledger_path=f"ledger-{index}.md")
        assert len(ledger._REFLECTION_VERIFICATION_CONTEXT.get().completed) == 2

    operation()  # cache saturation falls back to validation, never refusal


def test_warm_child_proofs_cannot_bypass_dependency_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "MAX_TRUSTED_LEDGER_CLASSIFICATIONS", 2)
    monkeypatch.setattr(ledger, "_commit", lambda *args: "a" * 40)

    def load(path):
        return ledger.load_trusted_workstream_ledger(tmp_path, trusted_ref="HEAD", ledger_path=path)

    def classify(root, ref, commit, path):
        if path == "parent.md":
            load("child-1.md")
            load("child-2.md")
        return object()

    monkeypatch.setattr(ledger, "_classify_trusted_workstream_ledger", classify)

    @ledger.reflection_verification_operation
    def operation():
        load("child-1.md")
        load("child-2.md")
        with pytest.raises(ledger.ReflectionValidationError, match="bounded context"):
            load("parent.md")

    operation()
