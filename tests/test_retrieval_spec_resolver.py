import copy
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from memory_seed.cli import main as cli_main
from memory_seed.mcp_server import TOOLS, call_tool, handle_jsonrpc_message
from memory_seed.retrieval import (
    RetrievalSpecResolutionError,
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

    def write_entry(self, root, day, entry_id, title, body):
        path = root / ".memory-seed" / "sessions" / f"{day}.md"
        path.write_text(
            f"## {day} 09:00 - {title}\n\n"
            "```yaml\n"
            f"entry_id: {entry_id}\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "project_path: .\n"
            "subproject_path: null\n"
            "```\n\n"
            f"{body}\n",
            encoding="utf-8",
        )

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

    def test_mcp_surface_is_inline_only(self):
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
                {"spec", "cwd"},
            )
            self.assertNotIn("profile", tool["inputSchema"]["properties"])

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
            [item["ref"] for item in pack["evidence"]],
            EXPECTED_PACK["ordered_refs"],
        )
        self.assertLessEqual(len(pack["evidence"]), 30)
        self.assertLessEqual(pack["token_estimate"], 12_000)
        self.assertEqual(
            {item["ref"] for item in pack["evidence"]},
            {item["ref"] for item in resolve_retrieval_spec(FIXTURE_SPEC, root)["evidence"]},
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
            [item["ref"] for item in first["evidence"]],
            [item["ref"] for item in second["evidence"]],
        )
        self.assertEqual(canonical_retrieval_json(first), canonical_retrieval_json(second))

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
        self.assertEqual(output.getvalue().strip(), expected_bytes)
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

    def test_stale_and_tampered_packs_are_rejected(self):
        root = self.make_project()
        pack = resolve_retrieval_spec(FIXTURE_SPEC, root)
        tampered = copy.deepcopy(pack)
        tampered["evidence"][0]["ref"] = "invented"
        with self.assertRaises(RetrievalSpecResolutionError) as mismatch:
            validate_evidence_pack(tampered, root)
        self.assertEqual(mismatch.exception.code, "fingerprint_mismatch")

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
