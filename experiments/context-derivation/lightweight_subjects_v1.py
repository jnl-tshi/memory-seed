"""Experiment-only local-SLM and Luna subject harness.

This module deliberately has no dependency on the legacy Claude/Codex harness.
All provider I/O is injectable so its contract can be exercised without network
access, a model download, or a Luna installation.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib import request as urlrequest
import uuid


HERE = Path(__file__).resolve().parent


def _load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contracts = _load("lightweight_subject_contracts", "contracts.py")
queries = _load("lightweight_subject_queries", "revision_constitution_queries_v1.py")

SCHEMA = "lightweight-subject-harness.v1"
RESULT_SCHEMA = "lightweight-subject-result.v1"
SCHEDULE_SCHEMA = "lightweight-subject-schedule.v1"
PACKET_SCHEMA = "lightweight-subject-packet.v1"
LADDER = ("qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b")
SUBJECTS = ("local", "luna")
ARMS = ("decision-only", "adr-current", "adr-constitution")
ADAPTER_VERSION = "lightweight-subjects-v1"
FORBIDDEN_PACKET_KEYS = frozenset({"mcp", "mcp_config", "tools", "tool_config", "filesystem", "repository"})


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _assert_no_provider_config(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_PACKET_KEYS:
                raise ValueError("fixed packets must not expose MCP, tools, filesystem, or repository configuration")
            _assert_no_provider_config(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _assert_no_provider_config(item)


@dataclass(frozen=True)
class SubjectPin:
    subject: str
    requested_model: str
    reported_model: str
    model_digest: str
    quantization: str
    context_window: int
    decoding: tuple[tuple[str, Any], ...]
    provider_version: str
    cli_version: str | None = None
    adapter_version: str = ADAPTER_VERSION

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        """Return the immutable pin in a JSON-serializable manifest shape."""
        return {
            "subject": self.subject, "requested_model": self.requested_model,
            "reported_model": self.reported_model, "model_digest": self.model_digest,
            "quantization": self.quantization, "context_window": self.context_window,
            "decoding": dict(self.decoding), "provider_version": self.provider_version,
            "cli_version": self.cli_version, "adapter_version": self.adapter_version,
        }

    def validate(self) -> None:
        if self.subject not in SUBJECTS or not all(isinstance(item, str) and item for item in (
            self.requested_model, self.reported_model, self.model_digest, self.quantization,
            self.provider_version, self.adapter_version,
        )):
            raise ValueError("pin fields must be non-empty")
        if not isinstance(self.context_window, int) or self.context_window <= 0:
            raise ValueError("pin context_window must be positive")
        if not isinstance(self.decoding, tuple) or any(not isinstance(item, tuple) or len(item) != 2 or not isinstance(item[0], str) for item in self.decoding):
            raise ValueError("pin decoding must be immutable key/value pairs")
        if self.cli_version is not None and (not isinstance(self.cli_version, str) or not self.cli_version):
            raise ValueError("pin cli_version must be a non-empty string or null")


def frozen_decoding(value: Mapping[str, Any]) -> tuple[tuple[str, Any], ...]:
    """Pin only deterministic JSON-compatible decoding configuration."""
    encoded = canonical_json(dict(value))
    decoded = json.loads(encoded)
    return tuple((str(key), decoded[key]) for key in sorted(decoded))


@dataclass(frozen=True)
class SubjectPacket:
    arm: str
    payload: Mapping[str, Any]
    fingerprint: str

    def json(self) -> str:
        return canonical_json(_thaw(self.payload))


@dataclass(frozen=True)
class SubjectRequest:
    query_id: str
    parent_task_id: str
    arm: str
    packet: SubjectPacket
    corpus_fingerprint: str
    task_fingerprint: str
    isolation_cwd: Path

    @property
    def prompt(self) -> str:
        return (
            "Answer only with one JSON object matching context-answer.v1. "
            "Use only the supplied evidence; do not use tools, files, MCP, or a repository.\n"
            + self.packet.json()
        )


@dataclass(frozen=True)
class SubjectResult:
    raw_answer: str
    transcript: str
    pin: SubjectPin
    duration_ms: float
    usage: Mapping[str, Any]
    completion_reason: str
    stable_completion: bool
    isolation: Mapping[str, Any]


class SubjectAdapter(Protocol):
    """A subject has an unscored protocol probe and one isolated run entrypoint."""

    def probe(self) -> SubjectResult: ...

    def run(self, request: SubjectRequest) -> SubjectResult: ...


def _query_payload(query: Mapping[str, Any]) -> dict[str, Any]:
    fields = ("query_id", "parent_task_id", "variant_index", "question")
    if any(field not in query for field in fields):
        raise ValueError("packet query must be a subject-visible v1 query")
    return {field: query[field] for field in fields}


def _compact_decisions(rows: Any, *, compact_lower_ranked: bool) -> list[Any]:
    if not isinstance(rows, list):
        raise ValueError("evidence decisions must be a list")
    result: list[Any] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("evidence decision rows must be objects")
        rank = row.get("rank", 1)
        if compact_lower_ranked and isinstance(rank, int) and rank > 1:
            result.append({key: row[key] for key in ("rank", "ref", "excerpt") if key in row})
        else:
            result.append(dict(row))
    return result


def build_packet(arm: str, query: Mapping[str, Any], evidence: Mapping[str, Any]) -> SubjectPacket:
    """Build one immutable fixed packet arm, without any tool/provider surface."""
    if arm not in ARMS:
        raise ValueError("unknown lightweight subject arm")
    _assert_no_provider_config(evidence)
    included: dict[str, Any] = {"query": _query_payload(query), "decisions": _compact_decisions(evidence.get("decisions"), compact_lower_ranked=arm != "decision-only")}
    if arm in {"adr-current", "adr-constitution"}:
        if not isinstance(evidence.get("adrs"), list):
            raise ValueError("enriched arms require ADR evidence")
        included["adrs"] = list(evidence["adrs"])
    if arm == "adr-constitution":
        if not isinstance(evidence.get("constitution"), list):
            raise ValueError("constitution arm requires Constitution evidence")
        included["constitution"] = list(evidence["constitution"])
    payload = {"schema": PACKET_SCHEMA, "arm": arm, "evidence": included}
    _assert_no_provider_config(payload)
    return SubjectPacket(arm=arm, payload=_freeze(payload), fingerprint=fingerprint(payload))


def build_schedule(query_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ids = [row.get("query_id") for row in query_rows]
    expected = list(queries.subject_visible_queries())
    expected_ids = [row["query_id"] for row in expected]
    if ids != expected_ids:
        raise ValueError("schedule requires the ordered immutable 60-query corpus")
    return [
        {"schema": SCHEDULE_SCHEMA, "query_id": query_id, "parent_task_id": query_id.split(".")[0], "arm": arm, "subject": subject, "repetition": 1}
        for query_id in ids for arm in ARMS for subject in SUBJECTS
    ]


def validate_schedule(cells: Sequence[Mapping[str, Any]], query_rows: Sequence[Mapping[str, Any]]) -> None:
    expected = build_schedule(query_rows)
    expected_keys = {(row["query_id"], row["arm"], row["subject"], row["repetition"]) for row in expected}
    parent_by_query = {row["query_id"]: row["parent_task_id"] for row in query_rows}
    actual_keys = []
    for row in cells:
        if not isinstance(row, Mapping) or row.get("schema") != SCHEDULE_SCHEMA:
            raise ValueError("schedule cells must use lightweight-subject-schedule.v1")
        actual_keys.append((row.get("query_id"), row.get("arm"), row.get("subject"), row.get("repetition")))
        if row.get("parent_task_id") != parent_by_query.get(row.get("query_id")):
            raise ValueError("schedule parent_task_id must match the frozen query")
    if len(cells) != 360 or len(actual_keys) != len(set(actual_keys)) or set(actual_keys) != expected_keys:
        raise ValueError("schedule must contain exactly one of the 360 fixed cells")


def _evidence_refs(packet: SubjectPacket) -> set[str]:
    import re
    refs: set[str] = set()
    singular_identifier_fields = frozenset({"adr_id", "ref", "authoritative_ref", "decision_ref", "source", "target"})
    plural_identifier_fields = frozenset({"adr_ids", "refs", "authoritative_refs", "decision_refs", "citations"})
    identifier = re.compile(r"(?:adr_[A-Za-z0-9._-]+|mse_[A-Za-z0-9]+:d\d+|constitution:[A-Za-z0-9._-]+(?:#[A-Za-z0-9._-]+)?)")

    def collect(value: Any, *, identifier_field: bool = False) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                collect(item, identifier_field=key in singular_identifier_fields or key in plural_identifier_fields)
        elif isinstance(value, tuple) or isinstance(value, list):
            for item in value:
                collect(item, identifier_field=identifier_field)
        elif identifier_field and isinstance(value, str) and identifier.fullmatch(value):
            refs.add(value)

    evidence = packet.payload["evidence"]
    for field in ("decisions", "adrs", "constitution"):
        if field in evidence:
            collect(evidence[field])
    return refs


def _forbidden_claim(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in ("mcp", "filesystem", "file system", "repository access", "i used a tool", "tool call", "read a file", "opened a file"))


def protocol_failure(result: SubjectResult, request: SubjectRequest) -> str | None:
    """Validate the provider-independent probe/run protocol, not answer quality."""
    try:
        answer = json.loads(result.raw_answer)
        contracts.validate_answer(answer)
    except (ValueError, TypeError, json.JSONDecodeError):
        return "invalid-answer-schema"
    if not result.stable_completion or result.completion_reason not in {"stop", "done", "completed"}:
        return "unstable-completion"
    if int(result.usage.get("input_tokens", 0) or 0) > result.pin.context_window:
        return "context-overflow"
    if set(answer["citations"]) - _evidence_refs(request.packet):
        return "citation-outside-evidence"
    if _forbidden_claim(result.raw_answer) or _forbidden_claim(result.transcript):
        return "forbidden-tool-or-filesystem-claim"
    if not bool(result.isolation.get("empty_cwd")) or bool(result.isolation.get("repo_access")) or bool(result.isolation.get("mcp_enabled")):
        return "isolation-failure"
    return None


def assert_pin(expected: SubjectPin, observed: SubjectPin) -> None:
    expected.validate(); observed.validate()
    if expected.fingerprint != observed.fingerprint:
        raise RuntimeError("subject pin drift")


Transport = Callable[[str, str, Mapping[str, Any] | None], Mapping[str, Any]]


def _http_transport(method: str, url: str, payload: Mapping[str, Any] | None) -> Mapping[str, Any]:
    body = None if payload is None else canonical_json(payload).encode("utf-8")
    req = urlrequest.Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    with urlrequest.urlopen(req, timeout=30) as response:  # nosec B310 - local configured endpoint only
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError("Ollama returned a non-object response")
    return value


class OllamaAdapter:
    """Stdlib-only Ollama HTTP adapter. It never calls a pull/download endpoint."""

    def __init__(self, model: str, *, probe_request: SubjectRequest, transport: Transport = _http_transport,
                 base_url: str = "http://127.0.0.1:11434", decoding: Mapping[str, Any] | None = None,
                 expected_pin: SubjectPin | None = None) -> None:
        if model not in LADDER or "base" in model:
            raise ValueError("Ollama model must be one of the eligible non-base ladder models")
        self.model, self.probe_request, self.transport = model, probe_request, transport
        self.base_url = base_url.rstrip("/")
        self.decoding = dict(decoding or {"temperature": 0, "seed": 20260805})
        self.expected_pin = expected_pin
        self._pin: SubjectPin | None = None

    def _call(self, method: str, route: str, payload: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return self.transport(method, self.base_url + route, payload)

    def installed_models(self) -> Mapping[str, Mapping[str, Any]]:
        models = self._call("GET", "/api/tags").get("models", [])
        if not isinstance(models, list):
            raise RuntimeError("Ollama /api/tags models must be a list")
        return {str(row.get("name")): row for row in models if isinstance(row, Mapping) and isinstance(row.get("name"), str)}

    def _observe_pin(self, installed: Mapping[str, Mapping[str, Any]] | None = None) -> SubjectPin:
        row = (installed or self.installed_models()).get(self.model)
        if row is None:
            raise RuntimeError("requested Ollama model is not installed")
        shown = self._call("POST", "/api/show", {"name": self.model})
        details = shown.get("details") if isinstance(shown.get("details"), Mapping) else row.get("details", {})
        details = details if isinstance(details, Mapping) else {}
        info = shown.get("model_info") if isinstance(shown.get("model_info"), Mapping) else {}
        context = info.get("llama.context_length") or info.get("qwen2.context_length") or details.get("context_length")
        version = self._call("GET", "/api/version").get("version")
        pin = SubjectPin("local", self.model, str(shown.get("name") or row.get("name")), str(shown.get("digest") or row.get("digest") or ""),
                         str(details.get("quantization_level") or details.get("quantization") or ""), int(context or 0),
                         frozen_decoding(self.decoding), str(version or ""))
        pin.validate()
        if self.expected_pin is not None:
            assert_pin(self.expected_pin, pin)
        return pin

    def run(self, request: SubjectRequest) -> SubjectResult:
        observed = self._observe_pin()
        if self._pin is not None:
            assert_pin(self._pin, observed)
        self._pin = observed
        pin = observed
        started = time.perf_counter()
        response = self._call("POST", "/api/generate", {"model": self.model, "prompt": request.prompt, "stream": False, "format": "json", "options": dict(self.decoding)})
        elapsed = (time.perf_counter() - started) * 1000
        return SubjectResult(str(response.get("response", "")), canonical_json(response), pin, elapsed,
                             {"input_tokens": response.get("prompt_eval_count", 0), "output_tokens": response.get("eval_count", 0)},
                             str(response.get("done_reason") or "done"), bool(response.get("done")),
                             {"empty_cwd": request.isolation_cwd.exists() and not any(request.isolation_cwd.iterdir()), "repo_access": False, "mcp_enabled": False})

    def probe(self) -> SubjectResult:
        return self.run(self.probe_request)


def select_ollama_adapter(make_adapter: Callable[[str], OllamaAdapter]) -> OllamaAdapter:
    """Choose the first installed model with a valid protocol probe; quality never promotes."""
    first = make_adapter(LADDER[0])
    installed = first.installed_models()
    for model in LADDER:
        if model not in installed:
            continue
        adapter = first if model == LADDER[0] else make_adapter(model)
        result = adapter.probe()
        if protocol_failure(result, adapter.probe_request) is None:
            return adapter
    raise RuntimeError("no installed Ollama ladder model passed the protocol probe")


Runner = Callable[..., subprocess.CompletedProcess[str]]


class LunaAdapter:
    """Luna command adapter constrained to a fresh, empty, minimal-env cwd."""

    def __init__(self, command: Sequence[str], model: str, *, probe_request: SubjectRequest,
                 runner: Runner = subprocess.run, decoding: Mapping[str, Any] | None = None,
                 expected_pin: SubjectPin | None = None) -> None:
        if not command or not model:
            raise ValueError("Luna command and requested model are required")
        self.command, self.model, self.probe_request, self.runner = tuple(command), model, probe_request, runner
        self.decoding, self.expected_pin, self._pin = dict(decoding or {"temperature": 0}), expected_pin, None

    @staticmethod
    def _minimal_env(cwd: Path) -> dict[str, str]:
        return {"PATH": os.defpath, "LANG": "C", "LC_ALL": "C", "HOME": str(cwd), "USERPROFILE": str(cwd)}

    @staticmethod
    def _require_empty_cwd(cwd: Path) -> None:
        if not cwd.exists() or any(cwd.iterdir()):
            raise RuntimeError("Luna cwd must be a fresh empty directory")

    def _invoke(self, prompt: str, cwd: Path) -> Mapping[str, Any]:
        self._require_empty_cwd(cwd)
        completed = self.runner([*self.command, "--model", self.model, "--decoding-json", canonical_json(self.decoding)], input=prompt, cwd=str(cwd), env=self._minimal_env(cwd), text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError("Luna command failed")
        value = json.loads(completed.stdout)
        if not isinstance(value, Mapping):
            raise RuntimeError("Luna command returned a non-object response")
        return value

    def _cli_version(self, cwd: Path) -> str:
        completed = self.runner([*self.command, "--version"], input="", cwd=str(cwd), env=self._minimal_env(cwd), text=True, capture_output=True, check=False)
        if completed.returncode != 0 or not completed.stdout.strip():
            raise RuntimeError("Luna CLI version probe failed")
        return completed.stdout.strip()

    def run(self, request: SubjectRequest) -> SubjectResult:
        self._require_empty_cwd(request.isolation_cwd)
        started = time.perf_counter()
        cli_version = self._cli_version(request.isolation_cwd)
        response = self._invoke(request.prompt, request.isolation_cwd)
        elapsed = (time.perf_counter() - started) * 1000
        pin = SubjectPin("luna", self.model, str(response.get("model") or ""), str(response.get("model_digest") or ""),
                         str(response.get("quantization") or ""), int(response.get("context_window") or 0),
                         frozen_decoding(self.decoding), str(response.get("provider_version") or ""), cli_version)
        pin.validate()
        if self.expected_pin is not None:
            assert_pin(self.expected_pin, pin)
        if self._pin is not None:
            assert_pin(self._pin, pin)
        self._pin = pin
        return SubjectResult(str(response.get("answer", "")), canonical_json(response), pin, elapsed,
                             response.get("usage") if isinstance(response.get("usage"), Mapping) else {},
                             str(response.get("completion_reason") or ""), bool(response.get("stable_completion")),
                             {"empty_cwd": not any(request.isolation_cwd.iterdir()), "repo_access": False, "mcp_enabled": False, "minimal_env": True})

    def probe(self) -> SubjectResult:
        return self.run(self.probe_request)


class SubjectHarness:
    """Writes one uniquely named, redacted run artifact per fixed schedule cell."""

    def __init__(self, output_root: str | Path, repo_root: str | Path) -> None:
        self.output_root, self.repo_root = Path(output_root), Path(repo_root).resolve()

    def run(self, adapter: SubjectAdapter, request: SubjectRequest) -> Path:
        self.output_root.mkdir(parents=True, exist_ok=True)
        output = self.output_root / f"{request.query_id}-{request.arm}-{uuid.uuid4().hex}"
        output.mkdir()
        with tempfile.TemporaryDirectory(prefix="lightweight-subject-") as raw_cwd:
            cwd = Path(raw_cwd).resolve()
            try:
                cwd.relative_to(self.repo_root)
                raise RuntimeError("subject isolation cwd must be outside the repository")
            except ValueError:
                pass
            isolated_request = SubjectRequest(request.query_id, request.parent_task_id, request.arm, request.packet,
                                              request.corpus_fingerprint, request.task_fingerprint, cwd)
            result = adapter.run(isolated_request)
        failure = protocol_failure(result, isolated_request)
        try:
            parsed = json.loads(result.raw_answer)
            contracts.validate_answer(parsed)
        except (ValueError, TypeError, json.JSONDecodeError):
            parsed = None
        manifest = {"schema": RESULT_SCHEMA, "query_id": request.query_id, "parent_task_id": request.parent_task_id,
                    "arm": request.arm, "subject": result.pin.subject, "packet_fingerprint": request.packet.fingerprint,
                    "context_fingerprint": fingerprint(_thaw(request.packet.payload)["evidence"]), "task_fingerprint": request.task_fingerprint,
                    "corpus_fingerprint": request.corpus_fingerprint, "pin": result.pin.as_dict(), "pin_fingerprint": result.pin.fingerprint,
                    "duration_ms": result.duration_ms, "usage": dict(result.usage), "token_proxy": max(1, len(request.prompt.encode("utf-8")) // 4),
                    "transcript": "transcript.json", "parsed_answer": parsed, "protocol_failure": failure,
                    "isolation": dict(result.isolation)}
        (output / "transcript.json").write_text(result.transcript, encoding="utf-8")
        (output / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return output
