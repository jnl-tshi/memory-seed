"""Authenticated, per-run Streamable HTTP broker for Codex experiment subjects.

The broker is intentionally tiny and stateless.  It exposes only the read-only
fixture facade from ``mcp_wrapper`` and never gives the subject a filesystem path
to the fixture, repository, or gold labels.
"""
from __future__ import annotations

import hmac
import http.client
import json
import os
import secrets
import socket
import stat
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import mcp_wrapper

HOST = "127.0.0.1"
PATH = "/mcp"
TOKEN_ENV = "CONTEXT_DERIVATION_MCP_TOKEN"
MAX_REQUEST_BYTES = 1_048_576
MAX_RESPONSE_BYTES = 8_388_608
MAX_CONCURRENT_REQUESTS = 8
CONNECTION_TIMEOUT_SECONDS = 2.0
SUPPORTED_PROTOCOL_VERSIONS = frozenset({
    "2024-11-05",
    "2025-03-26",
    "2025-06-18",
    "2025-11-25",
})
REPO_ROOT = Path(__file__).resolve().parents[2]


class BrokerError(RuntimeError):
    """Fail-closed broker startup or shutdown failure."""


def _under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_fixture_tree(
    root: Path, *, require_immutable: bool = True, require_isolated: bool = True,
) -> Path:
    """Reject links, junctions, devices, repo paths, and mutable fixture files."""
    try:
        root_info = root.lstat()
    except OSError as exc:
        raise BrokerError("fixture path is unavailable") from exc
    root_attributes = getattr(root_info, "st_file_attributes", 0)
    if stat.S_ISLNK(root_info.st_mode) or root_attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
        raise BrokerError("fixture root links and reparse points are forbidden")
    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise BrokerError("fixture must be a directory")
    if require_isolated and _under(resolved, REPO_ROOT.resolve()):
        raise BrokerError("broker fixture must be an isolated copy outside the repository")

    count = 0
    pending = [resolved]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                count += 1
                if count > 4096:
                    raise BrokerError("fixture contains too many entries")
                info = entry.stat(follow_symlinks=False)
                attributes = getattr(info, "st_file_attributes", 0)
                if entry.is_symlink() or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
                    raise BrokerError("fixture links and reparse points are forbidden")
                path = Path(entry.path)
                if entry.is_dir(follow_symlinks=False):
                    pending.append(path)
                elif not entry.is_file(follow_symlinks=False) or not stat.S_ISREG(info.st_mode):
                    raise BrokerError("fixture may contain only directories and regular files")
                if require_immutable and info.st_mode & stat.S_IWRITE:
                    raise BrokerError("fixture must be read-only before broker startup")
    return resolved


def loopback_capable() -> bool:
    """Cheap batch preflight: prove an IPv4 loopback listener can be created."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind((HOST, 0))
        return True
    except OSError:
        return False


def validate_broker_url(url: str) -> str:
    """Refuse credentials, aliases, non-loopback hosts, and non-MCP paths."""
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise BrokerError("invalid broker URL") from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname != HOST
        or port is None
        or not 0 <= port <= 65535
        or parsed.path != PATH
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise BrokerError("broker URL must be an exact IPv4 loopback MCP endpoint")
    return url


class BrokerEndpoint:
    """A running one-fixture MCP capability with an in-memory bearer secret."""

    def __init__(self, *, arm: str, fixture_cwd: Path) -> None:
        mcp_wrapper.allowed_names(arm)
        self.arm = arm
        self.fixture_cwd = validate_fixture_tree(fixture_cwd)
        self.token = secrets.token_urlsafe(32)
        self._semaphore = threading.BoundedSemaphore(MAX_CONCURRENT_REQUESTS)
        self._calls: list[str] = []
        self._calls_lock = threading.Lock()
        self._handlers = 0
        self._handlers_condition = threading.Condition()
        self._closed = False
        self._server = self._make_server()
        self.port = int(self._server.server_address[1])
        self.url = f"http://{HOST}:{self.port}{PATH}"
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name=f"context-mcp-{self.port}",
            daemon=True,
        )

    def _make_server(self) -> ThreadingHTTPServer:
        endpoint = self

        class Server(ThreadingHTTPServer):
            daemon_threads = True
            allow_reuse_address = False

            def process_request_thread(self, request: Any, client_address: Any) -> None:
                with endpoint._handlers_condition:
                    endpoint._handlers += 1
                try:
                    super().process_request_thread(request, client_address)
                finally:
                    with endpoint._handlers_condition:
                        endpoint._handlers -= 1
                        endpoint._handlers_condition.notify_all()

        class Handler(BaseHTTPRequestHandler):
            server_version = "context-derivation-broker/1"
            sys_version = ""

            def setup(self) -> None:
                super().setup()
                self.connection.settimeout(CONNECTION_TIMEOUT_SECONDS)

            def log_message(self, _format: str, *_args: Any) -> None:
                return

            def _reply(self, status: int, payload: dict[str, Any] | None = None, *, authenticate: bool = False) -> None:
                body = b"" if payload is None else json.dumps(
                    payload, separators=(",", ":"), ensure_ascii=False,
                ).encode("utf-8")
                if len(body) > MAX_RESPONSE_BYTES:
                    status = 500
                    body = json.dumps(mcp_wrapper.rpc_error(None, -32603, "tool response exceeded broker limit"), separators=(",", ":")).encode("utf-8")
                self.send_response(status)
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                if authenticate:
                    self.send_header("WWW-Authenticate", "Bearer")
                if body:
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                else:
                    self.send_header("Content-Length", "0")
                self.end_headers()
                if body:
                    self.wfile.write(body)

            def _trusted_request(self) -> bool:
                expected_host = f"{HOST}:{endpoint.port}"
                if self.headers.get("Host") != expected_host:
                    return False
                origin = self.headers.get("Origin")
                if origin and origin != f"http://{expected_host}":
                    return False
                supplied = self.headers.get("Authorization", "")
                prefix = "Bearer "
                return supplied.startswith(prefix) and hmac.compare_digest(
                    supplied[len(prefix):], endpoint.token,
                )

            def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
                self._reply(405, mcp_wrapper.rpc_error(None, -32601, "GET is not supported"))

            def do_DELETE(self) -> None:  # noqa: N802 - stdlib handler API
                self._reply(405, mcp_wrapper.rpc_error(None, -32601, "DELETE is not supported"))

            def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
                if self.path != PATH:
                    self._reply(404, mcp_wrapper.rpc_error(None, -32601, "endpoint not found"))
                    return
                if not self._trusted_request():
                    self._reply(401, mcp_wrapper.rpc_error(None, -32001, "unauthorized"), authenticate=True)
                    return
                if not endpoint._semaphore.acquire(blocking=False):
                    self._reply(503, mcp_wrapper.rpc_error(None, -32000, "broker is busy"))
                    return
                try:
                    if self.headers.get_content_type() != "application/json":
                        self._reply(415, mcp_wrapper.rpc_error(None, -32600, "application/json required"))
                        return
                    raw_length = self.headers.get("Content-Length")
                    try:
                        length = int(raw_length or "")
                    except ValueError:
                        self._reply(411, mcp_wrapper.rpc_error(None, -32600, "valid content length required"))
                        return
                    if length < 0 or length > MAX_REQUEST_BYTES:
                        self._reply(413, mcp_wrapper.rpc_error(None, -32600, "request exceeded broker limit"))
                        return
                    try:
                        message = json.loads(self.rfile.read(length))
                    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                        self._reply(400, mcp_wrapper.rpc_error(None, -32700, "invalid JSON"))
                        return
                    if not isinstance(message, dict):
                        self._reply(400, mcp_wrapper.rpc_error(None, -32600, "JSON-RPC request must be an object"))
                        return
                    method = message.get("method")
                    if method == "tools/call":
                        name = (message.get("params") or {}).get("name")
                        if isinstance(name, str):
                            with endpoint._calls_lock:
                                endpoint._calls.append(name)
                    response = mcp_wrapper.handle_message(
                        message, arm=endpoint.arm, fixture_cwd=endpoint.fixture_cwd,
                    )
                    self._reply(202 if response is None else 200, response)
                finally:
                    endpoint._semaphore.release()

        return Server((HOST, 0), Handler)

    @property
    def calls(self) -> tuple[str, ...]:
        with self._calls_lock:
            return tuple(self._calls)

    def inject_environment(self, base: dict[str, str]) -> dict[str, str]:
        return {**base, TOKEN_ENV: self.token}

    def codex_config_overrides(self) -> list[str]:
        return codex_config_overrides(self.arm, self.url)

    def start(self, *, timeout: float = 5.0) -> "BrokerEndpoint":
        self._thread.start()
        try:
            connection = http.client.HTTPConnection(HOST, self.port, timeout=timeout)
            connection.request(
                "POST", PATH,
                body=json.dumps({"jsonrpc": "2.0", "id": "ready", "method": "ping"}),
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
            )
            response = connection.getresponse()
            response.read()
            connection.close()
            if response.status != 200:
                raise BrokerError("broker readiness handshake failed")
        except Exception as exc:
            self.close()
            raise BrokerError("broker readiness handshake failed") from exc
        return self

    def close(self, *, timeout: float = 5.0) -> None:
        if self._closed:
            return
        self._closed = True
        if self._thread.is_alive():
            self._server.shutdown()
        self._server.server_close()
        if self._thread.ident is not None:
            self._thread.join(timeout)
        if self._thread.is_alive():
            raise BrokerError("broker thread did not terminate")
        deadline = time.monotonic() + timeout
        with self._handlers_condition:
            while self._handlers:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise BrokerError("broker handlers did not terminate")
                self._handlers_condition.wait(remaining)
        try:
            with socket.create_connection((HOST, self.port), timeout=0.2):
                pass
        except OSError:
            return
        raise BrokerError("broker port remained open after teardown")

    def __enter__(self) -> "BrokerEndpoint":
        return self.start()

    def __exit__(self, _exc_type: Any, _exc: Any, _traceback: Any) -> None:
        self.close()


def localhost_mcp_broker(*, arm: str, fixture_cwd: Path) -> BrokerEndpoint:
    return BrokerEndpoint(arm=arm, fixture_cwd=fixture_cwd)


def codex_config_overrides(arm: str, url: str) -> list[str]:
    url = validate_broker_url(url)
    tools = json.dumps(sorted(mcp_wrapper.allowed_names(arm)), separators=(",", ":"))
    values = [
        f'mcp_servers.context_fixture.url="{url}"',
        f'mcp_servers.context_fixture.bearer_token_env_var="{TOKEN_ENV}"',
        "mcp_servers.context_fixture.enabled=true",
        f"mcp_servers.context_fixture.enabled_tools={tools}",
        "mcp_servers.context_fixture.startup_timeout_sec=10",
        "mcp_servers.context_fixture.tool_timeout_sec=30",
    ]
    return [part for value in values for part in ("-c", value)]


def isolated_fixture_parent(run_id: str) -> Path:
    """Create a broker-only directory outside both repository and subject root."""
    parent = Path(tempfile.mkdtemp(prefix=f"context-broker-{run_id}-")).resolve()
    if _under(parent, REPO_ROOT.resolve()):
        raise BrokerError("temporary broker directory resolved inside repository")
    return parent
