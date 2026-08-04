"""Provider-free security and protocol checks for the experiment MCP broker."""
from __future__ import annotations

import http.client
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1] / "experiments" / "context-derivation"
sys.path.insert(0, str(HERE))

import broker  # noqa: E402
import mcp_wrapper  # noqa: E402


def immutable_fixture(parent: Path, name: str = "fixture") -> Path:
    root = parent / name
    root.mkdir()
    file = root / "evidence.txt"
    file.write_text("bounded evidence", encoding="utf-8")
    file.chmod(file.stat().st_mode & ~stat.S_IWRITE)
    root.chmod(root.stat().st_mode & ~stat.S_IWRITE)
    return root


def memory_fixture(parent: Path) -> Path:
    root = parent / "memory-fixture"
    sessions = root / ".memory-seed" / "sessions" / "2026-08"
    sessions.mkdir(parents=True)
    (sessions / "2026-08-04.md").write_text(
        """## 2026-08-04 10:00 - Broker evidence

```yaml
entry_id: mse_brokerevidence
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
branch: test
topics:
  - retrieval
```

### Summary

- The broker fixture contains bounded evidence.
""",
        encoding="utf-8",
    )
    for item in sorted(root.rglob("*"), key=lambda path: len(path.parts), reverse=True):
        item.chmod(item.stat().st_mode & ~stat.S_IWRITE)
    root.chmod(root.stat().st_mode & ~stat.S_IWRITE)
    return root


def post(endpoint: broker.BrokerEndpoint, payload: object, *, token: str | None = None, host: str | None = None):
    connection = http.client.HTTPConnection(broker.HOST, endpoint.port, timeout=3)
    headers = {
        "Authorization": f"Bearer {token if token is not None else endpoint.token}",
        "Content-Type": "application/json",
    }
    if host is not None:
        headers["Host"] = host
    connection.request("POST", broker.PATH, json.dumps(payload), headers)
    response = connection.getresponse()
    body = response.read()
    connection.close()
    return response.status, json.loads(body) if body else None


class BrokerTests(unittest.TestCase):
    def test_authenticated_protocol_and_exact_allowlist(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = immutable_fixture(Path(temp))
            with patch.object(mcp_wrapper.mcp_server, "call_tool", return_value={"ok": True}) as call:
                with broker.localhost_mcp_broker(arm="search-mcp", fixture_cwd=fixture) as endpoint:
                    status, initialized = post(endpoint, {
                        "jsonrpc": "2.0", "id": 1, "method": "initialize",
                        "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {}},
                    })
                    self.assertEqual(200, status)
                    self.assertEqual("2025-06-18", initialized["result"]["protocolVersion"])

                    status, listed = post(endpoint, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
                    self.assertEqual(200, status)
                    self.assertEqual(
                        broker.mcp_wrapper.allowed_names("search-mcp"),
                        {item["name"] for item in listed["result"]["tools"]},
                    )

                    status, result = post(endpoint, {
                        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                        "params": {"name": "memory_search", "arguments": {"query": "q", "cwd": "C:/forbidden"}},
                    })
                    self.assertEqual(200, status)
                    self.assertFalse(result["result"]["isError"])
                    self.assertEqual(str(fixture.resolve()), call.call_args.args[1]["cwd"])
                    self.assertFalse(call.call_args.args[1]["semantic_enabled"])

                    leaked_path = str(fixture / "private.txt")
                    call.side_effect = RuntimeError(leaked_path)
                    status, failed = post(endpoint, {
                        "jsonrpc": "2.0", "id": 31, "method": "tools/call",
                        "params": {"name": "memory_search", "arguments": {"query": "q"}},
                    })
                    self.assertEqual(200, status)
                    self.assertTrue(failed["result"]["isError"])
                    self.assertNotIn(leaked_path, json.dumps(failed))
                    call.side_effect = None
                    call.return_value = {"ok": True}

                    status, denied = post(endpoint, {
                        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
                        "params": {"name": "memory_session_append", "arguments": {}},
                    })
                    self.assertEqual(200, status)
                    self.assertEqual(-32602, denied["error"]["code"])

                    status, invalid = post(endpoint, {
                        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
                        "params": {"name": "memory_search", "arguments": {"query": "q", "path": "../gold.json"}},
                    })
                    self.assertEqual(200, status)
                    self.assertEqual(-32602, invalid["error"]["code"])

                    call_count = call.call_count
                    status, semantic = post(endpoint, {
                        "jsonrpc": "2.0", "id": 6, "method": "tools/call",
                        "params": {"name": "memory_search", "arguments": {"query": "q", "semantic_enabled": True}},
                    })
                    self.assertEqual(200, status)
                    self.assertEqual(-32602, semantic["error"]["code"])
                    self.assertEqual(call_count, call.call_count)

                    status, notification = post(endpoint, {
                        "jsonrpc": "2.0", "method": "notifications/initialized",
                    })
                    self.assertEqual(202, status)
                    self.assertIsNone(notification)

                    call_count = call.call_count
                    status, notification = post(endpoint, {
                        "jsonrpc": "2.0", "method": "tools/call",
                        "params": {"name": "memory_search", "arguments": {"query": "q"}},
                    })
                    self.assertEqual(202, status)
                    self.assertIsNone(notification)
                    self.assertEqual(call_count, call.call_count)

    def test_adr_ids_cannot_escape_and_absolute_paths_are_redacted(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = immutable_fixture(Path(temp))
            leaked = str(fixture.resolve())
            payload = {
                "ok": True,
                "path": str(fixture / ".memory-seed" / "decisions" / "adr_valid.md"),
                "issues": [f"problem under {leaked}"],
            }
            with patch.object(mcp_wrapper.mcp_server, "call_tool", return_value=payload) as call:
                with broker.localhost_mcp_broker(arm="adr-mcp-workflow", fixture_cwd=fixture) as endpoint:
                    for adr_id in ("../gold", "C:/repo/adr_secret", "adr_ok/../../secret"):
                        status, denied = post(endpoint, {
                            "jsonrpc": "2.0", "id": adr_id, "method": "tools/call",
                            "params": {"name": "memory_adr_show", "arguments": {"adr_id": adr_id}},
                        })
                        self.assertEqual(200, status)
                        self.assertEqual(-32602, denied["error"]["code"])
                    call.assert_not_called()

                    status, shown = post(endpoint, {
                        "jsonrpc": "2.0", "id": 8, "method": "tools/call",
                        "params": {"name": "memory_adr_show", "arguments": {"adr_id": "adr_valid"}},
                    })
                    self.assertEqual(200, status)
                    text = shown["result"]["content"][0]["text"]
                    self.assertNotIn(leaked, text)
                    self.assertIn("<fixture>", text)

    def test_search_is_forced_lexical_and_creates_no_fixture_telemetry(self):
        from memory_seed import semantic_cache

        with tempfile.TemporaryDirectory() as temp:
            fixture = memory_fixture(Path(temp))
            semantic_cache._load_model2vec_model.cache_clear()
            with patch.object(
                semantic_cache, "_load_model2vec_model",
                side_effect=AssertionError("semantic model must not load"),
            ):
                with broker.localhost_mcp_broker(arm="search-mcp", fixture_cwd=fixture) as endpoint:
                    status, result = post(endpoint, {
                        "jsonrpc": "2.0", "id": 9, "method": "tools/call",
                        "params": {"name": "memory_search", "arguments": {"query": "bounded evidence"}},
                    })
                    self.assertEqual(200, status)
                    self.assertFalse(result["result"]["isError"])
            self.assertFalse((fixture / ".memory-seed" / ".retrieval-log.jsonl").exists())
            self.assertFalse((fixture / ".memory-seed" / ".retrieval-attention.json").exists())

    def test_auth_host_cross_run_and_teardown(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture_a = immutable_fixture(Path(temp), "a")
            fixture_b = immutable_fixture(Path(temp), "b")
            endpoint_a = broker.localhost_mcp_broker(arm="search-mcp", fixture_cwd=fixture_a).start()
            port_a = endpoint_a.port
            try:
                with broker.localhost_mcp_broker(arm="search-mcp", fixture_cwd=fixture_b) as endpoint_b:
                    self.assertNotEqual(endpoint_a.port, endpoint_b.port)
                    self.assertNotEqual(endpoint_a.token, endpoint_b.token)
                    status, _ = post(endpoint_a, {"jsonrpc": "2.0", "id": 1, "method": "ping"}, token="wrong")
                    self.assertEqual(401, status)
                    status, _ = post(endpoint_a, {"jsonrpc": "2.0", "id": 2, "method": "ping"}, token=endpoint_b.token)
                    self.assertEqual(401, status)
                    status, _ = post(endpoint_a, {"jsonrpc": "2.0", "id": 3, "method": "ping"}, host="example.test")
                    self.assertEqual(401, status)
            finally:
                endpoint_a.close()
            with self.assertRaises(OSError):
                socket.create_connection((broker.HOST, port_a), timeout=0.2)

    def test_six_parallel_brokers_have_distinct_capabilities(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            endpoints = [
                stack.enter_context(broker.localhost_mcp_broker(
                    arm="search-mcp", fixture_cwd=immutable_fixture(Path(temp), f"fixture-{index}"),
                ))
                for index in range(6)
            ]
            self.assertEqual(6, len({item.port for item in endpoints}))
            self.assertEqual(6, len({item.token for item in endpoints}))
            for endpoint in endpoints:
                status, payload = post(endpoint, {"jsonrpc": "2.0", "id": 1, "method": "ping"})
                self.assertEqual((200, {}), (status, payload["result"]))

    def test_fixture_validation_rejects_repo_and_links(self):
        with self.assertRaisesRegex(broker.BrokerError, "outside the repository"):
            broker.validate_fixture_tree(HERE, require_immutable=False)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "fixture"
            root.mkdir()
            (root / "evidence.txt").write_text("inside", encoding="utf-8")
            target = Path(temp) / "target.txt"
            target.write_text("outside", encoding="utf-8")
            try:
                os.symlink(target, root / "link.txt")
            except OSError:
                if os.name != "nt":
                    self.skipTest("symlink creation is unavailable")
                target_dir = Path(temp) / "target-dir"
                target_dir.mkdir()
                created = subprocess.run(
                    ["cmd.exe", "/c", "mklink", "/J", str(root / "link-dir"), str(target_dir)],
                    capture_output=True, text=True,
                )
                if created.returncode != 0:
                    self.skipTest("link and junction creation are unavailable")
            with self.assertRaisesRegex(broker.BrokerError, "links and reparse points"):
                broker.validate_fixture_tree(root, require_immutable=False)

            actual = Path(temp) / "actual-root"
            actual.mkdir()
            linked = Path(temp) / "linked-root"
            try:
                os.symlink(actual, linked, target_is_directory=True)
            except OSError:
                created = subprocess.run(
                    ["cmd.exe", "/c", "mklink", "/J", str(linked), str(actual)],
                    capture_output=True, text=True,
                )
                if created.returncode != 0:
                    self.skipTest("root link and junction creation are unavailable")
            with self.assertRaisesRegex(broker.BrokerError, "fixture root links"):
                broker.validate_fixture_tree(linked, require_immutable=False)

    def test_codex_cli_accepts_generated_streamable_http_config(self):
        executable = shutil.which("codex.cmd") or shutil.which("codex")
        if not executable:
            self.skipTest("Codex CLI is unavailable")
        with tempfile.TemporaryDirectory() as temp:
            fixture = immutable_fixture(Path(temp))
            with broker.localhost_mcp_broker(arm="search-mcp", fixture_cwd=fixture) as endpoint:
                command = [executable, "mcp", *endpoint.codex_config_overrides(), "get", "context_fixture", "--json"]
                completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=30)
                self.assertEqual(0, completed.returncode, completed.stderr)
                payload = json.loads(completed.stdout)
                self.assertEqual("streamable_http", payload["transport"]["type"])
                self.assertEqual(broker.TOKEN_ENV, payload["transport"]["bearer_token_env_var"])
                self.assertEqual(sorted(mcp_wrapper.allowed_names("search-mcp")), payload["enabled_tools"])
                self.assertIn(
                    'mcp_servers.context_fixture.default_tools_approval_mode="approve"',
                    endpoint.codex_config_overrides(),
                )
                self.assertNotIn(endpoint.token, completed.stdout + completed.stderr)

    def test_secret_is_environment_only_and_readiness_failure_closes_port(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = immutable_fixture(Path(temp))
            endpoint = broker.localhost_mcp_broker(arm="adr-mcp-workflow", fixture_cwd=fixture)
            command = endpoint.codex_config_overrides()
            self.assertNotIn(endpoint.token, " ".join(command))
            self.assertIn(broker.TOKEN_ENV, " ".join(command))
            self.assertIn(
                'mcp_servers.context_fixture.default_tools_approval_mode="approve"', command,
            )
            environment = endpoint.inject_environment({"SAFE": "yes"})
            self.assertEqual(endpoint.token, environment[broker.TOKEN_ENV])
            with self.assertRaisesRegex(broker.BrokerError, "exact IPv4 loopback"):
                broker.codex_config_overrides("search-mcp", "https://example.test/mcp")
            with self.assertRaisesRegex(broker.BrokerError, "exact IPv4 loopback"):
                broker.codex_config_overrides("search-mcp", "http://localhost:43123/mcp")
            endpoint.close()

            failed = broker.localhost_mcp_broker(arm="search-mcp", fixture_cwd=fixture)
            failed_port = failed.port
            with patch.object(broker.http.client, "HTTPConnection", side_effect=OSError("offline")):
                with self.assertRaisesRegex(broker.BrokerError, "readiness handshake"):
                    failed.start()
            with self.assertRaises(OSError):
                socket.create_connection((broker.HOST, failed_port), timeout=0.2)

    def test_malformed_and_oversized_requests_are_bounded(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = immutable_fixture(Path(temp))
            with broker.localhost_mcp_broker(arm="search-mcp", fixture_cwd=fixture) as endpoint:
                connection = http.client.HTTPConnection(broker.HOST, endpoint.port, timeout=3)
                connection.request("POST", broker.PATH, b"not json", {
                    "Authorization": f"Bearer {endpoint.token}", "Content-Type": "application/json",
                })
                response = connection.getresponse(); body = json.loads(response.read()); connection.close()
                self.assertEqual(400, response.status)
                self.assertEqual(-32700, body["error"]["code"])

                connection = http.client.HTTPConnection(broker.HOST, endpoint.port, timeout=3)
                connection.putrequest("POST", broker.PATH)
                connection.putheader("Authorization", f"Bearer {endpoint.token}")
                connection.putheader("Content-Type", "application/json")
                connection.putheader("Content-Length", str(broker.MAX_REQUEST_BYTES + 1))
                connection.endheaders()
                response = connection.getresponse(); response.read(); connection.close()
                self.assertEqual(413, response.status)

    def test_slow_request_handler_is_drained_before_teardown(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = immutable_fixture(Path(temp))
            endpoint = broker.localhost_mcp_broker(arm="search-mcp", fixture_cwd=fixture).start()
            client = socket.create_connection((broker.HOST, endpoint.port), timeout=2)
            request = (
                f"POST {broker.PATH} HTTP/1.1\r\n"
                f"Host: {broker.HOST}:{endpoint.port}\r\n"
                f"Authorization: Bearer {endpoint.token}\r\n"
                "Content-Type: application/json\r\n"
                "Content-Length: 100\r\n\r\n{"
            )
            client.sendall(request.encode("ascii"))
            deadline = time.monotonic() + 2
            while endpoint._handlers == 0 and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertGreater(endpoint._handlers, 0)
            endpoint.close(timeout=4)
            client.close()
            self.assertEqual(0, endpoint._handlers)


if __name__ == "__main__":
    unittest.main()
