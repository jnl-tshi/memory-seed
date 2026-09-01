import copy
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from memory_seed.cli import main as cli_main
from memory_seed.mcp_server import TOOLS, call_tool, handle_jsonrpc_message
from memory_seed.retrieval import (
    RetrievalSpecResolutionError,
    _evidence_pack_fingerprint,
    canonical_retrieval_json,
    preview_retrieval_spec,
    resolve_retrieval_spec,
    validate_evidence_pack,
)


FIXTURE_SPEC = json.loads(
    (
        Path(__file__).parent
        / "fixtures"
        / "retrieval-spec"
        / "topic-sidecar-inline.json"
    ).read_text(encoding="utf-8")
)
EXPECTED_PACK = json.loads(
    (
        Path(__file__).parent
        / "fixtures"
        / "retrieval-spec"
        / "m1-expected-pack.json"
    ).read_text(encoding="utf-8")
)


class _StepClock:
    def __init__(self, *values):
        self.values = iter(values)
        self.last = 0.0

    def __call__(self):
        try:
            self.last = next(self.values)
        except StopIteration:
            pass
        return self.last


class _RevisionSequence:
    def __init__(self, *values):
        self.values = iter(values)
        self.last = ""

    def __call__(self, _cwd, _spec):
        try:
            self.last = next(self.values)
        except StopIteration:
            pass
        return self.last


class _CallDeadlineClock:
    def __init__(self, cross_on_call, *, elapsed=0.010):
        self.cross_on_call = cross_on_call
        self.elapsed = elapsed
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.elapsed if self.calls >= self.cross_on_call else 0.0


class RetrievalSpecResolverTests(unittest.TestCase):
    def make_project(self):
        root = Path(tempfile.mkdtemp(prefix="memory-seed-retrieval-spec-m1-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        (root / ".memory-seed" / "sessions").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / "memory_seed").mkdir()
        (root / "docs" / "CONSTITUTION.md").write_text(
            "# Constitution\n\n## Invariant\n\nMarkdown is authoritative.\n",
            encoding="utf-8",
        )
        (root / "memory_seed" / "core.py").write_text(
            "# fixture source path\n",
            encoding="utf-8",
        )
        (root / ".memory-seed" / "topics.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "topics:",
                    "  - slug: session-fuse",
                    "    label: Session fuse",
                    "    status: active",
                    "    aliases: []",
                    "  - slug: worktree-integration",
                    "    label: Worktree integration",
                    "    status: active",
                    "    aliases: []",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        self.write_entry(
            root,
            "2026-07-01",
            "mse_base0001",
            "Base resolver decision",
            "### Decision\n\n"
            "- D: Keep the resolver local.\n"
            "- R: The network-free core is authoritative.\n"
            "- F: `memory_seed/core.py`.\n",
        )
        self.write_entry(
            root,
            "2026-07-02",
            "mse_side0002",
            "Topic sidecar decision",
            "### Decision\n\n"
            "- D: Fuse topic sidecars through canonical readers.\n"
            "- R: Late attribution must stay append-only.\n",
        )
        for day in range(3, 8):
            self.write_entry(
                root,
                f"2026-07-0{day}",
                f"mse_neigh00{day}",
                f"Neighbour {day}",
                f"Neighbouring session evidence {day}.\n",
            )
        self.write_topic_sidecar(root)
        self.write_link_sidecar(root)
        return root

    def write_entry(self, root, day, entry_id, title, body, *, topics=()):
        path = root / ".memory-seed" / "sessions" / f"{day}.md"
        topic_lines = (
            "topics:\n" + "".join(f"  - {topic}\n" for topic in topics)
            if topics
            else ""
        )
        path.write_text(
            f"## {day} 09:00 - {title}\n\n"
            "```yaml\n"
            f"entry_id: {entry_id}\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            f"{topic_lines}"
            "```\n\n"
            f"{body}\n",
            encoding="utf-8",
        )

    def write_adr(self, root, adr_id="adr_retrieval_contract"):
        path = root / ".memory-seed" / "decisions" / f"{adr_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\n"
            "format: memory-seed-adr/2\n"
            "schema_version: 2\n"
            f"adr_id: {adr_id}\n"
            'title: "Retrieval contract"\n'
            "topics:\n"
            "  - retrieval\n"
            "created_at: 2026-07-01T09:00:00Z\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "source: write-time\n"
            "---\n\n"
            "# Retrieval contract\n\n"
            "## Current view\n\n"
            "Status: **Accepted**\n",
            encoding="utf-8",
        )
        return path

    def write_topic_sidecar(self, root):
        path = (
            root
            / ".memory-seed"
            / "sessions"
            / "topics"
            / "2026-07"
            / "2026-07-02.md"
        )
        path.parent.mkdir(parents=True)
        path.write_text(
            "## 2026-07-02 10:00 - Topic attribution\n\n"
            "```yaml\n"
            "entry_id: mse_side0002\n"
            "topics:\n"
            "  area:\n"
            "    - session-fuse:d1\n"
            "  activity:\n"
            "    - worktree-integration:d1\n"
            "```\n",
            encoding="utf-8",
        )

    def write_link_sidecar(self, root):
        path = (
            root
            / ".memory-seed"
            / "sessions"
            / "links"
            / "2026-07"
            / "2026-07-02.md"
        )
        path.parent.mkdir(parents=True)
        path.write_text(
            "## 2026-07-02 10:05 - Related base decision\n\n"
            "```yaml\n"
            "entry_id: mse_side0002\n"
            "related_entries:\n"
            "  - mse_base0001\n"
            "```\n",
            encoding="utf-8",
        )

    def memory_snapshot(self, root):
        memory = root / ".memory-seed"
        return {
            path.relative_to(memory).as_posix(): path.read_bytes()
            for path in memory.rglob("*")
            if path.is_file()
        }

    def test_mcp_surface_is_inline_or_exact_profile_only(self):
        retrieval_tools = {
            item["name"]: item for item in TOOLS if item["name"].startswith("memory_retrieval_spec_")
        }
        self.assertEqual(
            set(retrieval_tools),
            {
                "memory_retrieval_spec_preview",
                "memory_retrieval_spec_resolve",
            },
        )
        for tool in retrieval_tools.values():
            self.assertEqual(
                set(tool["inputSchema"]["properties"]),
                {"spec", "profile", "profile_version", "overrides", "cwd"},
            )
            self.assertFalse(tool["inputSchema"].get("required"))

    def test_mcp_rejects_unknown_arguments_before_retrieval(self):
        root = self.make_project()
        for tool_name, service_name in (
            (
                "memory_retrieval_spec_preview",
                "memory_seed.mcp_server.preview_retrieval_input",
            ),
            (
                "memory_retrieval_spec_resolve",
                "memory_seed.mcp_server.resolve_retrieval_input_pack",
            ),
        ):
            with self.subTest(tool=tool_name), patch(service_name) as service:
                response = handle_jsonrpc_message(
                    {
                        "jsonrpc": "2.0",
                        "id": 7,
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": {
                                "spec": FIXTURE_SPEC,
                                "cwd": str(root),
                                "profile": "deferred",
                                "unknown": 1,
                            },
                        },
                    }
                )
                payload = json.loads(response["result"]["content"][0]["text"])
                self.assertFalse(payload["ok"])
                self.assertEqual(payload["error"]["code"], "invalid_arguments")
                self.assertEqual(
                    payload["error"]["details"]["unsupported_arguments"],
                    ["unknown"],
                )
                service.assert_not_called()

    def test_real_mcp_topic_sidecar_resolution_is_bounded_and_fetchable(self):
        root = self.make_project()
        response = handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "memory_retrieval_spec_resolve",
                    "arguments": {"spec": FIXTURE_SPEC, "cwd": str(root)},
                },
            }
        )
        result = json.loads(response["result"]["content"][0]["text"])
        self.assertTrue(result["ok"])
        pack = result["pack"]
        self.assertEqual(pack["pack_schema"], EXPECTED_PACK["pack_schema"])
        self.assertEqual(pack["pack_version"], EXPECTED_PACK["pack_version"])
        self.assertEqual(pack["resolver_version"], EXPECTED_PACK["resolver_version"])
        self.assertEqual(
            [item["id"] for item in pack["evidence"]],
            EXPECTED_PACK["ordered_ids"],
        )
        self.assertLessEqual(len(pack["evidence"]), 30)
        self.assertLessEqual(pack["token_estimate"], 12_000)
        self.assertEqual(
            {item["id"] for item in pack["evidence"]},
            {item["id"] for item in resolve_retrieval_spec(FIXTURE_SPEC, root)["evidence"]},
        )
        self.assertTrue(
            any(
                "topic-sidecar reader" in stage["reader"]
                for stage in pack["resolution_trace"]
            )
        )
        for item in pack["evidence"]:
            if item["chunk_id"]:
                fetched = call_tool(
                    "memory_get_chunk",
                    {"chunk_id": item["chunk_id"], "cwd": str(root)},
                )
                self.assertEqual(fetched["chunk"]["chunk_id"], item["chunk_id"])
            else:
                self.assertTrue((root / item["source"]).is_file())
                self.assertEqual((root / item["source"]).suffix.lower(), ".md")
        self.assertTrue(validate_evidence_pack(pack, root)["valid"])

    def test_repeated_resolution_at_one_revision_is_identical(self):
        root = self.make_project()
        first = resolve_retrieval_spec(FIXTURE_SPEC, root)
        second = resolve_retrieval_spec(FIXTURE_SPEC, root)
        self.assertEqual(first["corpus_revision"], second["corpus_revision"])
        self.assertEqual(first["fingerprint"], second["fingerprint"])
        self.assertEqual(
            [item["id"] for item in first["evidence"]],
            [item["id"] for item in second["evidence"]],
        )
        self.assertEqual(canonical_retrieval_json(first), canonical_retrieval_json(second))

    def test_adr_paths_emit_typed_ids_and_content_digests(self):
        root = self.make_project()
        adr = self.write_adr(root)
        spec = copy.deepcopy(FIXTURE_SPEC)
        spec["filters"]["paths"] = [adr.relative_to(root).as_posix()]

        pack = resolve_retrieval_spec(spec, root)
        adr_item = next(item for item in pack["evidence"] if item["kind"] == "adr")

        self.assertEqual(adr_item["id"], "adr_retrieval_contract")
        self.assertEqual(adr_item["source"], ".memory-seed/decisions/adr_retrieval_contract.md")
        self.assertNotIn("ref", adr_item)
        self.assertRegex(adr_item["content_digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertTrue(all("id" in item and "ref" not in item for item in pack["evidence"]))
        self.assertEqual(validate_evidence_pack(pack, root)["evidence_count"], len(pack["evidence"]))

        wrong_identity = copy.deepcopy(pack)
        wrong_adr = next(item for item in wrong_identity["evidence"] if item["kind"] == "adr")
        wrong_adr["id"] = "adr_not_the_source_identity"
        wrong_identity["fingerprint"] = _evidence_pack_fingerprint(wrong_identity)
        with self.assertRaises(RetrievalSpecResolutionError) as invalid_identity:
            validate_evidence_pack(wrong_identity, root)
        self.assertEqual(invalid_identity.exception.code, "invalid_pack")

    def test_invalid_markdown_in_decisions_directory_fails_as_invalid_adr(self):
        root = self.make_project()
        path = root / ".memory-seed" / "decisions" / "not-an-adr.md"
        path.parent.mkdir(parents=True)
        path.write_text("# Not an ADR\n", encoding="utf-8")
        spec = copy.deepcopy(FIXTURE_SPEC)
        spec["filters"]["paths"] = [path.relative_to(root).as_posix()]

        with self.assertRaises(RetrievalSpecResolutionError) as invalid:
            resolve_retrieval_spec(spec, root)
        self.assertEqual(invalid.exception.code, "invalid_adr")

    def test_omitted_sessions_spec_previews_and_resolves_with_one_fingerprint(self):
        root = self.make_project()
        spec = copy.deepcopy(FIXTURE_SPEC)
        spec.pop("optional")
        preview = preview_retrieval_spec(spec, root)
        pack = resolve_retrieval_spec(spec, root)
        self.assertIsNone(preview["effective_spec"]["optional"]["sessions"])
        self.assertEqual(
            preview["effective_spec_fingerprint"],
            pack["effective_spec_fingerprint"],
        )
        self.assertTrue(validate_evidence_pack(pack, root)["valid"])

    def test_sidecar_topics_override_authored_topics_and_select_only_attributed_decision(self):
        root = self.make_project()
        self.write_entry(
            root,
            "2026-07-02",
            "mse_side0002",
            "Topic sidecar decisions",
            "### Decision\n\n"
            "#### D1 - Canonical sidecar decision\n\n"
            "- D: Use current sidecar attribution.\n"
            "- R: The sidecar is authoritative.\n\n"
            "#### D2 - Stale authored decision\n\n"
            "- D: Do not re-admit stale authored topics.\n"
            "- R: Decision precision is part of selection.\n",
            topics=("session-fuse",),
        )
        topic_sidecar = (
            root
            / ".memory-seed"
            / "sessions"
            / "topics"
            / "2026-07"
            / "2026-07-02.md"
        )
        topic_sidecar.write_text(
            "## 2026-07-02 10:00 - Topic attribution\n\n"
            "```yaml\n"
            "entry_id: mse_side0002\n"
            "topics:\n"
            "  activity:\n"
            "    - worktree-integration:d1\n"
            "```\n",
            encoding="utf-8",
        )

        stale = copy.deepcopy(FIXTURE_SPEC)
        stale["filters"] = {"topics": ["session-fuse"]}
        stale.pop("optional")
        with self.assertRaises(RetrievalSpecResolutionError) as missing:
            resolve_retrieval_spec(stale, root)
        self.assertEqual(missing.exception.code, "missing_required")

        precise = copy.deepcopy(stale)
        precise["filters"]["topics"] = ["worktree-integration"]
        pack = resolve_retrieval_spec(precise, root)
        refs = {item["id"] for item in pack["evidence"]}
        self.assertIn("mse_side0002:d1", refs)
        self.assertNotIn("mse_side0002:d2", refs)

    def test_decision_sidecar_edges_traverse_to_the_exact_target(self):
        root = self.make_project()
        self.write_entry(
            root,
            "2026-07-02",
            "mse_side0002",
            "Decision edge source",
            "### Decision\n\n"
            "#### D1 - Linked source\n\n"
            "- D: Follow the decision edge.\n\n"
            "#### D2 - Unlinked source\n\n"
            "- D: Stay outside the traversal.\n",
        )
        self.write_entry(
            root,
            "2026-07-08",
            "mse_target0008",
            "Decision edge target",
            "### Decision\n\n"
            "#### D1 - Linked target\n\n"
            "- D: Resolve this exact target.\n\n"
            "#### D2 - Unlinked target\n\n"
            "- D: Do not broaden the edge to this decision.\n",
        )
        link_sidecar = (
            root
            / ".memory-seed"
            / "sessions"
            / "links"
            / "2026-07"
            / "2026-07-02.md"
        )
        link_sidecar.write_text(
            "## 2026-07-02 10:05 - Related target decision\n\n"
            "```yaml\n"
            "entry_id: mse_side0002\n"
            "related_entries:\n"
            "  - d1 -> mse_target0008:d1\n"
            "```\n",
            encoding="utf-8",
        )
        spec = copy.deepcopy(FIXTURE_SPEC)
        spec["filters"] = {"topics": ["session-fuse"]}
        spec.pop("optional")
        pack = resolve_retrieval_spec(spec, root)
        refs = {item["id"] for item in pack["evidence"]}
        self.assertIn("mse_side0002:d1", refs)
        self.assertNotIn("mse_side0002:d2", refs)
        self.assertIn("mse_target0008:d1", refs)
        self.assertNotIn("mse_target0008:d2", refs)

    def test_token_estimates_match_fetch_recipes_without_duplicate_entry_fetches(self):
        root = self.make_project()
        self.write_entry(
            root,
            "2026-07-02",
            "mse_side0002",
            "Precise fetch decisions",
            "### Decision\n\n"
            "#### D1 - Selected\n\n"
            f"- D: {'selected evidence ' * 80}\n\n"
            "#### D2 - Not selected\n\n"
            f"- D: {'unrelated evidence ' * 240}\n",
        )
        spec = copy.deepcopy(FIXTURE_SPEC)
        spec["filters"] = {"topics": ["session-fuse"]}
        spec.pop("optional")
        pack = resolve_retrieval_spec(spec, root)
        fetched_proxy_total = 0
        chunk_fetches = []
        for item in pack["evidence"]:
            fetch = item["fetch"]
            if fetch.get("tool") == "memory_get_chunk":
                chunk_id = fetch["arguments"]["chunk_id"]
                chunk_fetches.append(chunk_id)
                fetched_text = call_tool(
                    "memory_get_chunk",
                    {"chunk_id": chunk_id, "cwd": str(root)},
                )["chunk"]["text"]
            else:
                source_lines = (root / fetch["path"]).read_text(
                    encoding="utf-8"
                ).splitlines()
                fetched_text = "\n".join(
                    source_lines[fetch["line_start"] - 1 : fetch["line_end"]]
                )
            fetched_proxy = max(
                1, (len(fetched_text.encode("utf-8")) + 3) // 4
            )
            self.assertEqual(item["token_estimate"], fetched_proxy)
            fetched_proxy_total += fetched_proxy
        self.assertEqual(pack["token_estimate"], fetched_proxy_total)
        self.assertLessEqual(fetched_proxy_total, spec["limits"]["max_tokens"])
        self.assertEqual(len(chunk_fetches), len(set(chunk_fetches)))
        self.assertNotIn("mse_side0002", chunk_fetches)

    def test_cli_and_mcp_preview_are_byte_equivalent_canonical_json(self):
        root = self.make_project()
        spec_file = root / "inline-spec.json"
        spec_file.write_text(json.dumps(FIXTURE_SPEC), encoding="utf-8")
        response = handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "memory_retrieval_spec_preview",
                    "arguments": {"spec": FIXTURE_SPEC, "cwd": str(root)},
                },
            }
        )
        expected_bytes = response["result"]["content"][0]["text"]
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = cli_main(
                [
                    "retrieval-spec",
                    "preview",
                    "--spec-file",
                    str(spec_file),
                    "--cwd",
                    str(root),
                ]
            )
        self.assertEqual(exit_code, 0)
        self.assertEqual(output.getvalue(), expected_bytes)
        self.assertEqual(output.getvalue().encode("utf-8"), expected_bytes.encode("utf-8"))
        self.assertFalse(output.getvalue().endswith(("\r", "\n")))
        self.assertEqual(expected_bytes, canonical_retrieval_json(json.loads(expected_bytes)))

    def test_missing_required_and_forbidden_path_fail_closed(self):
        root = self.make_project()
        (root / "docs" / "CONSTITUTION.md").unlink()
        missing = call_tool(
            "memory_retrieval_spec_resolve",
            {"spec": FIXTURE_SPEC, "cwd": str(root)},
        )
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["error"]["code"], "missing_required")
        self.assertEqual(
            missing["error"]["details"]["clause"], "required.constitution"
        )

        root = self.make_project()
        forbidden = copy.deepcopy(FIXTURE_SPEC)
        forbidden["filters"]["paths"] = [".git/config"]
        denied = call_tool(
            "memory_retrieval_spec_resolve",
            {"spec": forbidden, "cwd": str(root)},
        )
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["error"]["code"], "forbidden_path")
        self.assertNotIn(str(root.parent), denied["error"]["message"])

    def test_optional_truncation_is_deterministic_and_reported(self):
        root = self.make_project()
        spec = copy.deepcopy(FIXTURE_SPEC)
        spec["limits"] = {"max_entries": 3, "max_tokens": 12_000}
        pack = resolve_retrieval_spec(spec, root)
        self.assertEqual(pack["completeness"], "partial")
        self.assertEqual(len(pack["evidence"]), 3)
        self.assertIn("truncated", {warning["code"] for warning in pack["warnings"]})
        required = {
            clause
            for item in pack["evidence"]
            for clause in item["selected_by"]
            if clause.startswith("required.")
        }
        self.assertEqual(
            required,
            set(EXPECTED_PACK["required_clauses"]),
        )

    def test_timeout_and_corpus_change_use_deterministic_local_seams(self):
        root = self.make_project()
        with self.assertRaises(RetrievalSpecResolutionError) as timeout:
            resolve_retrieval_spec(
                FIXTURE_SPEC,
                root,
                _clock=_StepClock(0.0, 0.010),
                _timeout_ms=1,
                _revision_reader=lambda _cwd, _spec: "r1",
            )
        self.assertEqual(timeout.exception.code, "timeout")
        self.assertEqual(timeout.exception.completed_stages, ("runtime",))

        retried = resolve_retrieval_spec(
            FIXTURE_SPEC,
            root,
            _revision_reader=_RevisionSequence("r1", "r2", "r2", "r2"),
        )
        self.assertEqual(retried["corpus_revision"], "r2")
        self.assertEqual(retried["resolution_trace"][-1]["attempt"], 2)

        with self.assertRaises(RetrievalSpecResolutionError) as changed:
            resolve_retrieval_spec(
                FIXTURE_SPEC,
                root,
                _revision_reader=_RevisionSequence("r1", "r2", "r2", "r3"),
            )
        self.assertEqual(changed.exception.code, "corpus_changed")
        self.assertEqual(len(changed.exception.details["attempts"]), 2)

    def test_timeout_crossed_during_pack_finalization_fails(self):
        root = self.make_project()
        # Calls 1-8 cover start + reader stages; call 9 is the stable
        # end-revision deadline check; call 10 is after pack construction and
        # fingerprinting. Only the final check crosses the deadline.
        clock = _CallDeadlineClock(10)
        with self.assertRaises(RetrievalSpecResolutionError) as timeout:
            resolve_retrieval_spec(
                FIXTURE_SPEC,
                root,
                _clock=clock,
                _timeout_ms=1,
                _revision_reader=lambda _cwd, _spec: "r1",
            )
        self.assertEqual(clock.calls, 10)
        self.assertEqual(timeout.exception.code, "timeout")
        self.assertEqual(timeout.exception.stage, "pack_format")
        self.assertIn("revision_check", timeout.exception.completed_stages)

    def test_stale_and_tampered_packs_are_rejected(self):
        root = self.make_project()
        pack = resolve_retrieval_spec(FIXTURE_SPEC, root)
        tampered = copy.deepcopy(pack)
        tampered["evidence"][0]["id"] = "invented"
        with self.assertRaises(RetrievalSpecResolutionError) as mismatch:
            validate_evidence_pack(tampered, root)
        self.assertEqual(mismatch.exception.code, "fingerprint_mismatch")

        false_digest = copy.deepcopy(pack)
        false_digest["evidence"][0]["content_digest"] = "sha256:" + "0" * 64
        false_digest["fingerprint"] = _evidence_pack_fingerprint(false_digest)
        with self.assertRaises(RetrievalSpecResolutionError) as digest_mismatch:
            validate_evidence_pack(false_digest, root)
        self.assertEqual(digest_mismatch.exception.code, "content_digest_mismatch")

        false_decision_id = copy.deepcopy(pack)
        decision = next(
            item for item in false_decision_id["evidence"] if item["kind"] == "decision"
        )
        decision["id"] = "mse_invented:d9"
        false_decision_id["fingerprint"] = _evidence_pack_fingerprint(false_decision_id)
        with self.assertRaises(RetrievalSpecResolutionError) as decision_identity:
            validate_evidence_pack(false_decision_id, root)
        self.assertEqual(decision_identity.exception.code, "invalid_pack")

        session = root / ".memory-seed" / "sessions" / "2026-07-07.md"
        session.write_text(
            session.read_text(encoding="utf-8") + "\nCorpus changed.\n",
            encoding="utf-8",
        )
        with self.assertRaises(RetrievalSpecResolutionError) as stale:
            validate_evidence_pack(pack, root)
        self.assertEqual(stale.exception.code, "stale_pack")

    def test_preview_and_resolve_do_not_write_authoritative_memory(self):
        root = self.make_project()
        before = self.memory_snapshot(root)
        preview = preview_retrieval_spec(FIXTURE_SPEC, root)
        self.assertNotIn("pack_schema", preview)
        resolve_retrieval_spec(FIXTURE_SPEC, root)
        self.assertEqual(self.memory_snapshot(root), before)


if __name__ == "__main__":
    unittest.main()
