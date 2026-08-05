from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "experiments" / "context-derivation" / "lightweight_subjects_v1.py"
SPEC = importlib.util.spec_from_file_location("lightweight_subjects_v1", PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def answer(**overrides):
    value = {"schema": "lightweight-context-answer.v1", "adr_ids": [], "authoritative_refs": [], "adr_statuses": {}, "lineage_edges": [], "related_edges": [], "citations": ["mse_alpha123:d1"], "constitution_bindings": [], "explanation": "from supplied evidence", "insufficient_evidence": False, "missing_refs": []}
    value.update(overrides)
    return value


def query():
    return {"query_id": "CTX-01.V01", "parent_task_id": "CTX-01", "variant_index": 1, "question": "What changed?"}


def evidence():
    return {"decisions": [{"rank": 1, "ref": "mse_alpha123:d1", "excerpt": "full", "links": ["x"]}, {"rank": 2, "ref": "mse_beta456:d1", "excerpt": "compact", "links": ["y"]}], "adrs": [{"adr_id": "adr_alpha", "current": "current"}], "constitution": [{"ref": "constitution:v1#authority", "text": "binding"}], "constitution_bindings": [{"adr_id": "adr_alpha", "decision_ref": "mse_alpha123:d1", "constitution_refs": ["constitution:v1#authority"]}]}


def arm_evidence(arm):
    full = evidence()
    fields = {"decision-only": ("decisions",), "adr-current": ("decisions", "adrs"), "adr-constitution": ("decisions", "adrs", "constitution", "constitution_bindings")}
    return {field: full[field] for field in fields[arm]}


def request(arm="decision-only", cwd=None):
    packet = module.build_packet(arm, query(), arm_evidence(arm))
    return module.SubjectRequest("CTX-01.V01", "CTX-01", arm, packet, "sha256:" + "a" * 64, "sha256:" + "b" * 64, Path(cwd or tempfile.gettempdir()))


def pin(subject="local", model="qwen2.5:0.5b"):
    return module.SubjectPin(subject, model, model, "sha256:digest", "Q4_K_M", 4096, module.frozen_decoding({"temperature": 0}), "1.0")


def approved_request(*, arm="decision-only", cwd=None, local=None, luna=None):
    corpus, _rows = module.queries.load_query_variants()
    base = request(arm, cwd)
    base = module.SubjectRequest(base.query_id, base.parent_task_id, base.arm, base.packet, corpus["canonical_fingerprint"], base.task_fingerprint, base.isolation_cwd)
    proposal = module.frozen_run_proposal(base, {"local": local or pin(), "luna": luna or pin("luna", "luna-small")})
    proposal["approval_status"] = "APPROVED"
    proposal["fingerprint"] = module._receipt_fingerprint(proposal)
    return module.SubjectRequest(base.query_id, base.parent_task_id, base.arm, base.packet, base.corpus_fingerprint, base.task_fingerprint, base.isolation_cwd, proposal)


def approved_probe_request(*, cwd=None, subject="local", model="qwen2.5:0.5b"):
    base = module.protocol_probe_request(Path(cwd or tempfile.gettempdir()))
    proposal = module.probe_run_proposal(base, subject=subject, requested_model=model)
    proposal["approval_status"] = "APPROVED"
    proposal["fingerprint"] = module._receipt_fingerprint(proposal)
    return module.protocol_probe_request(base.isolation_cwd, receipt=proposal)


def result(**overrides):
    value = {"raw_answer": json.dumps(answer()), "transcript": "{}", "pin": pin(), "duration_ms": 1.0, "usage": {"input_tokens": 20}, "completion_reason": "stop", "stable_completion": True, "isolation": {"empty_cwd": True, "repo_access": False, "mcp_enabled": False}}
    value.update(overrides)
    return module.SubjectResult(**value)


def test_packets_are_fixed_immutable_and_expose_no_mcp_or_repository_config():
    current = module.build_packet("adr-current", query(), arm_evidence("adr-current"))
    constitution = module.build_packet("adr-constitution", query(), arm_evidence("adr-constitution"))
    assert set(module.ARMS) == {"decision-only", "adr-current", "adr-constitution"}
    assert current.payload["evidence"]["decisions"][1] == {"rank": 2, "ref": "mse_beta456:d1", "excerpt": "compact"}
    assert "constitution" in constitution.payload["evidence"]
    with pytest.raises(TypeError): current.payload["arm"] = "changed"
    with pytest.raises(ValueError, match="MCP"):
        module.build_packet("decision-only", query(), {**arm_evidence("decision-only"), "mcp": {"enabled": True}})
    with pytest.raises(ValueError, match="decision-only evidence"):
        module.build_packet("decision-only", query(), evidence())
    with pytest.raises(ValueError, match="adr-current evidence"):
        module.build_packet("adr-current", query(), arm_evidence("adr-constitution"))


def test_protocol_validation_rejects_citation_claim_context_and_isolation_failures():
    req = request()
    assert module.protocol_failure(result(), req) is None
    assert module.protocol_failure(result(raw_answer=json.dumps(answer(citations=["mse_notfound:d1"]))), req) == "citation-outside-evidence"
    assert module.protocol_failure(result(transcript="I used a tool"), req) == "forbidden-tool-or-filesystem-claim"
    assert module.protocol_failure(result(usage={"input_tokens": 5000}), req) == "context-overflow"
    assert module.protocol_failure(result(isolation={"empty_cwd": False, "repo_access": False, "mcp_enabled": False}), req) == "isolation-failure"
    question_ref = {**query(), "question": "Does mse_question999:d1 change the answer?"}
    packet = module.build_packet("decision-only", question_ref, arm_evidence("decision-only"))
    question_request = module.SubjectRequest("CTX-01.V01", "CTX-01", "decision-only", packet, req.corpus_fingerprint, req.task_fingerprint, req.isolation_cwd)
    assert module.protocol_failure(result(raw_answer=json.dumps(answer(citations=["mse_question999:d1"]))), question_request) == "citation-outside-evidence"
    enriched = request("adr-current")
    assert module.protocol_failure(result(raw_answer=json.dumps(answer(citations=["adr_alpha"]))), enriched) is None


def test_schedule_is_exact_deterministic_and_rejects_missing_duplicate_or_extra_cells():
    rows = module.queries.subject_visible_queries()
    first = module.build_schedule(rows)
    assert first == module.build_schedule(rows) and len(first) == 360
    module.validate_schedule(first, rows)
    with pytest.raises(ValueError): module.validate_schedule(first[:-1], rows)
    with pytest.raises(ValueError): module.validate_schedule([*first[:-1], first[-2]], rows)
    extra = [*first]; extra[-1] = {**extra[-1], "subject": "other"}
    with pytest.raises(ValueError): module.validate_schedule(extra, rows)
    wrong_parent = [*first]; wrong_parent[0] = {**wrong_parent[0], "parent_task_id": "CTX-12"}
    with pytest.raises(ValueError, match="parent_task_id"): module.validate_schedule(wrong_parent, rows)


def test_ollama_ladder_selects_first_protocol_valid_installed_model_and_never_pulls():
    calls = []
    with tempfile.TemporaryDirectory() as temp:
        def transport(method, url, payload):
            calls.append(url)
            if url.endswith("/api/tags"):
                return {"models": [{"name": "qwen2.5:0.5b", "digest": "sha256:a", "details": {"quantization_level": "Q4"}}, {"name": "qwen2.5:1.5b", "digest": "sha256:b", "details": {"quantization_level": "Q4"}}]}
            if url.endswith("/api/show"):
                return {"name": payload["name"], "digest": "sha256:" + payload["name"], "details": {"quantization_level": "Q4"}, "model_info": {"llama.context_length": 4096}}
            if url.endswith("/api/version"): return {"version": "0.5"}
            if url.endswith("/api/generate"):
                bad = payload["model"] == "qwen2.5:0.5b"
                return {"response": "{}" if bad else json.dumps(answer()), "done": True, "done_reason": "stop", "prompt_eval_count": 10, "eval_count": 5}
            raise AssertionError(url)
        chosen = module.select_ollama_adapter(lambda model: module.OllamaAdapter(model, probe_request=approved_probe_request(cwd=temp, model=model), transport=transport))
        assert chosen.model == "qwen2.5:1.5b"
        assert not any("pull" in url for url in calls)
        with pytest.raises(ValueError): module.OllamaAdapter("qwen2.5-coder:1.5b-base", probe_request=approved_probe_request(cwd=temp), transport=transport)
        expected = module.SubjectPin("local", "qwen2.5:1.5b", "qwen2.5:1.5b", "sha256:qwen2.5:1.5b", "Q4", 4096, module.frozen_decoding({"temperature": 0, "seed": 20260805}), "0.5")
        chosen.expected_pin = expected
        scored = approved_request(cwd=temp, local=expected)
        observed = chosen.run(scored)
        assert observed.pin.fingerprint.startswith("sha256:")
        assert json.loads(json.dumps(observed.pin.as_dict()))["decoding"] == {"seed": 20260805, "temperature": 0}
        artifact = module.SubjectHarness(Path(temp) / "runs", ROOT).run(chosen, scored)
        manifest = json.loads((artifact / "RUN_MANIFEST.json").read_text())
        assert manifest["pin"]["decoding"] == {"seed": 20260805, "temperature": 0}


def test_content_error_does_not_promote_ladder_model():
    probe = approved_probe_request(cwd=tempfile.gettempdir())
    class Adapter:
        def __init__(self, model): self.model, self.probe_request = model, probe
        def installed_models(self): return {name: {} for name in module.LADDER}
        def probe(self): return result()  # Valid protocol despite unscored content quality.
    assert module.select_ollama_adapter(Adapter).model == "qwen2.5:0.5b"


@pytest.mark.parametrize("changed", ["digest", "version", "context"])
def test_ollama_reobserves_show_and_version_and_rejects_pin_drift(changed):
    with tempfile.TemporaryDirectory() as temp:
        state = {"digest": "sha256:stable", "version": "0.5", "context": 4096}
        def transport(method, url, payload):
            if url.endswith("/api/tags"):
                return {"models": [{"name": "qwen2.5:0.5b", "digest": state["digest"], "details": {"quantization_level": "Q4"}}]}
            if url.endswith("/api/show"):
                return {"name": "qwen2.5:0.5b", "digest": state["digest"], "details": {"quantization_level": "Q4"}, "model_info": {"llama.context_length": state["context"]}}
            if url.endswith("/api/version"): return {"version": state["version"]}
            if url.endswith("/api/generate"):
                return {"response": json.dumps(answer()), "done": True, "done_reason": "stop", "prompt_eval_count": 3, "eval_count": 2}
            raise AssertionError(url)
        probe = approved_probe_request(cwd=temp)
        expected = module.SubjectPin("local", "qwen2.5:0.5b", "qwen2.5:0.5b", "sha256:stable", "Q4", 4096, module.frozen_decoding({"temperature": 0, "seed": 20260805}), "0.5")
        adapter = module.OllamaAdapter("qwen2.5:0.5b", probe_request=probe, transport=transport, expected_pin=expected)
        adapter.probe()
        state[changed] = {"digest": "sha256:changed", "version": "0.6", "context": 8192}[changed]
        with pytest.raises(RuntimeError, match="pin drift"):
            adapter.run(approved_request(cwd=temp, local=expected))


def test_pin_drift_fails_and_luna_uses_empty_minimal_environment_with_mocked_runner():
    with pytest.raises(RuntimeError, match="pin drift"):
        module.assert_pin(pin(), pin(model="qwen2.5:1.5b"))
    seen = {}
    def fake_runner(command, **kwargs):
        seen.update(command=command, **kwargs)
        if command[-1] == "--version":
            return subprocess.CompletedProcess(command, 0, "luna-cli 2.0\n", "")
        response = {"model": "luna-small", "model_digest": "sha256:luna", "quantization": "Q4", "context_window": 2048, "provider_version": "2.0", "answer": json.dumps(answer()), "usage": {"input_tokens": 4}, "completion_reason": "stop", "stable_completion": True}
        return subprocess.CompletedProcess(command, 0, json.dumps(response), "")
    with tempfile.TemporaryDirectory() as temp:
        cwd = Path(temp)
        expected = module.SubjectPin("luna", "luna-small", "luna-small", "sha256:luna", "Q4", 2048, module.frozen_decoding({"temperature": 0, "seed": 7}), "2.0", "luna-cli 2.0")
        adapter = module.LunaAdapter(["luna"], "luna-small", probe_request=approved_probe_request(cwd=cwd, subject="luna", model="luna-small"), runner=fake_runner, decoding={"temperature": 0, "seed": 7}, expected_pin=expected)
        observed = adapter.run(approved_request(cwd=cwd, luna=expected))
        assert observed.pin.reported_model == "luna-small"
        assert observed.pin.cli_version == "luna-cli 2.0"
        assert Path(seen["cwd"]) == cwd and not list(cwd.iterdir())
        assert set(seen["env"]) == {"PATH", "LANG", "LC_ALL", "HOME", "USERPROFILE"}
        assert "--model" in seen["command"]
        assert json.loads(seen["command"][-1]) == {"seed": 7, "temperature": 0}
        mismatched_expected = module.SubjectPin("luna", "luna-small", "luna-small", "sha256:luna", "Q4", 2048, module.frozen_decoding({"temperature": 0}), "2.0", "different-cli")
        mismatched = module.LunaAdapter(["luna"], "luna-small", probe_request=approved_probe_request(cwd=cwd, subject="luna", model="luna-small"), runner=fake_runner, expected_pin=mismatched_expected)
        with pytest.raises(RuntimeError, match="pin drift"):
            mismatched.run(approved_request(cwd=cwd, luna=expected))


def test_luna_rejects_non_empty_cwd_before_any_subprocess():
    calls = []
    def runner(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("runner must not be called")
    with tempfile.TemporaryDirectory() as temp:
        cwd = Path(temp)
        (cwd / "unexpected.txt").write_text("occupied")
        expected = module.SubjectPin("luna", "luna-small", "luna-small", "sha256:luna", "Q4", 2048, module.frozen_decoding({"temperature": 0}), "2.0", "luna-cli 2.0")
        adapter = module.LunaAdapter(["luna"], "luna-small", probe_request=request(cwd=cwd), runner=runner, expected_pin=expected)
        with pytest.raises(RuntimeError, match="fresh empty"):
            adapter.run(approved_request(cwd=cwd, luna=expected))
    assert calls == []


@pytest.mark.parametrize("mutation", ["missing", "stale", "wrong-packet", "wrong-schedule", "wrong-corpus", "optional-pin"])
def test_scored_adapter_and_harness_fail_before_provider_or_adapter_calls(mutation):
    calls = []
    class Adapter:
        def run(self, _request):
            calls.append("adapter")
            raise AssertionError("approval must fail before adapter execution")
    with tempfile.TemporaryDirectory() as temp:
        req = approved_request(cwd=temp)
        if mutation == "missing":
            req = module.SubjectRequest(req.query_id, req.parent_task_id, req.arm, req.packet, req.corpus_fingerprint, req.task_fingerprint, req.isolation_cwd)
        else:
            receipt = dict(req.frozen_run)
            if mutation == "stale": receipt["fingerprint"] = "sha256:" + "0" * 64
            elif mutation == "wrong-packet": receipt["packet_fingerprint"] = "sha256:" + "0" * 64
            elif mutation == "wrong-schedule": receipt["schedule_fingerprint"] = "sha256:" + "0" * 64
            elif mutation == "wrong-corpus": receipt["corpus_fingerprint"] = "sha256:" + "0" * 64
            else: receipt["selected_pins"] = {"local": pin().as_dict()}
            if mutation not in {"stale", "optional-pin"}:
                receipt["fingerprint"] = module._receipt_fingerprint(receipt)
            req = module.SubjectRequest(req.query_id, req.parent_task_id, req.arm, req.packet, req.corpus_fingerprint, req.task_fingerprint, req.isolation_cwd, receipt)
        with pytest.raises(RuntimeError, match="frozen-run|approved frozen-run"):
            module.SubjectHarness(Path(temp) / "runs", ROOT).run(Adapter(), req)
    assert calls == []


@pytest.mark.parametrize("stale", [False, True])
def test_direct_adapter_gate_makes_zero_provider_transport_calls(stale):
    calls = []
    expected = pin()
    with tempfile.TemporaryDirectory() as temp:
        req = approved_request(cwd=temp, local=expected)
        receipt = None if not stale else {**req.frozen_run, "fingerprint": "sha256:" + "0" * 64}
        gated = module.SubjectRequest(req.query_id, req.parent_task_id, req.arm, req.packet, req.corpus_fingerprint, req.task_fingerprint, req.isolation_cwd, receipt)
        adapter = module.OllamaAdapter("qwen2.5:0.5b", probe_request=req, expected_pin=expected, transport=lambda *_args: calls.append("provider") or {})
        with pytest.raises(RuntimeError, match="frozen-run|approved frozen-run"):
            adapter.run(gated)
    assert calls == []


@pytest.mark.parametrize("normal_request", [False, True])
def test_provider_probe_gate_requires_an_approved_synthetic_request_before_transport(normal_request):
    calls = []
    with tempfile.TemporaryDirectory() as temp:
        probe = request(cwd=temp) if normal_request else module.protocol_probe_request(temp)
        adapter = module.OllamaAdapter("qwen2.5:0.5b", probe_request=probe, transport=lambda *_args: calls.append("provider") or {})
        with pytest.raises(RuntimeError, match="probe receipt|synthetic protocol"):
            adapter.probe()
    assert calls == []


@pytest.mark.parametrize("field,value", [("requested_model", 7), ("context_window", True), ("decoding", [("temperature", 0)]), ("cli_version", "")])
def test_malformed_frozen_pin_fails_before_any_transport_call(field, value):
    calls = []
    with tempfile.TemporaryDirectory() as temp:
        expected = pin()
        req = approved_request(cwd=temp, local=expected)
        receipt = dict(req.frozen_run)
        selected = {name: dict(raw) for name, raw in receipt["selected_pins"].items()}
        selected["local"][field] = value
        receipt["selected_pins"] = selected
        receipt["fingerprint"] = module._receipt_fingerprint(receipt)
        malformed = module.SubjectRequest(req.query_id, req.parent_task_id, req.arm, req.packet, req.corpus_fingerprint, req.task_fingerprint, req.isolation_cwd, receipt)
        adapter = module.OllamaAdapter("qwen2.5:0.5b", probe_request=approved_probe_request(cwd=temp), expected_pin=expected, transport=lambda *_args: calls.append("provider") or {})
        with pytest.raises(RuntimeError, match="selected pin is malformed"):
            adapter.run(malformed)
    assert calls == []


def test_harness_writes_unique_redacted_manifest_and_fresh_cwd_outside_repo():
    seen = []
    class Adapter:
        def run(self, req):
            seen.append(req.isolation_cwd)
            return result(isolation={"empty_cwd": True, "repo_access": False, "mcp_enabled": False})
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        harness = module.SubjectHarness(root / "runs", ROOT)
        first = harness.run(Adapter(), approved_request())
        second = harness.run(Adapter(), approved_request())
        manifest = json.loads((first / "RUN_MANIFEST.json").read_text())
        assert first != second and manifest["subject"] == "local" and "env" not in manifest
        assert all(not str(cwd).startswith(str(ROOT)) for cwd in seen)
