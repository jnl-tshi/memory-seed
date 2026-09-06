import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from memory_seed.core import commit_cadence
from memory_seed.retrieval import (
    RetrievalSpecResolutionError,
    _evidence_pack_fingerprint,
    resolve_retrieval_spec,
)
from memory_seed.retrieval_profiles import load_retrieval_profile
from memory_seed.task_packet import (
    TASK_PACKET_SCHEMA,
    TaskPacketValidationError,
    activate_task_packet,
    assess_context_budget,
    calculate_cost_ledger,
    canonical_task_packet_json,
    compile_task_packet,
    estimate_tokens,
    materialize_evidence_pack,
    normalize_runtime_binding,
    normalize_task_dispatch,
    project_constitution,
)


class TaskPacketTests(unittest.TestCase):
    def make_project(self):
        root = Path(tempfile.mkdtemp(prefix="memory-seed-task-packet-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        (root / ".memory-seed" / "sessions").mkdir(parents=True)
        (root / ".memory-seed" / "skills").mkdir(parents=True)
        (root / ".memory-seed" / "retrieval-profiles" / "implementation").mkdir(
            parents=True
        )
        (root / "docs").mkdir()
        (root / "docs" / "CONSTITUTION.md").write_text(
            "# Constitution\n\n**Version:** 1.0 — **RATIFIED 2026-09-05**\n\n"
            "## Invariant\n\nMarkdown is authoritative.\n",
            encoding="utf-8",
        )
        (root / "docs" / "evidence.md").write_text(
            "# Evidence\n\nUse exact canonical slices.\n",
            encoding="utf-8",
        )
        (root / ".memory-seed" / "agent-rules.md").write_text(
            "# Active agent rules\n\nGovern every worker.\n",
            encoding="utf-8",
        )
        (root / ".memory-seed" / "skills" / "session_logging.md").write_text(
            "# Active session logging\n\nUse the guarded writer.\n",
            encoding="utf-8",
        )
        (root / ".memory-seed" / "sessions" / "2026-08-01.md").write_text(
            "## 2026-08-01 09:00 - Packet decision\n\n"
            "```yaml\nentry_id: mse_packet0001\nuser_initials: JN\n"
            "agent_type: codex\nproject_path: .\nsubproject_path: null\n```\n\n"
            "### Decision\n\n- D: Compile packets deterministically.\n"
            "- R: Clean workers need exact evidence.\n"
            "- F: `docs/evidence.md`.\n",
            encoding="utf-8",
        )
        (root / ".memory-seed" / "retrieval-profiles" / "implementation" / "v1.yaml").write_text(
            "schema: memory-seed/retrieval-profile\n"
            "schema_version: 1\nid: implementation\nprofile_version: 1\nextends: []\n"
            "spec:\n"
            "  selectors:\n    path_references: true\n"
            "  filters:\n    paths:\n      - docs/evidence.md\n"
            "  output:\n    include_excerpts: true\n"
            "  limits:\n    max_entries: 20\n    max_tokens: 12000\n",
            encoding="utf-8",
        )
        self.git(root, "init", "-b", "main")
        self.git(root, "config", "user.email", "test@example.com")
        self.git(root, "config", "user.name", "Task Packet Test")
        self.git(root, "add", ".")
        self.git(root, "commit", "-m", "fixture")
        return root

    @staticmethod
    def git(root, *args):
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.strip()

    def dispatch(self, *, write_intent="read-only", tier="balanced"):
        # The five values total about 140 tokens under the fixed UTF-8/4 proxy.
        context_piece = " ".join(["grounded"] * 15)
        return {
            "schema": "memory-seed/task-dispatch",
            "version": 1,
            "objective": "Compile one reconstructable packet.",
            "constitution_refs": [],
            "project_context": {
                "project_type_and_purpose": context_piece,
                "relevant_subsystem": context_piece,
                "task_fit": context_piece,
                "downstream_use": context_piece,
                "non_goals": ["Do not dispatch workers or expand authority."],
            },
            "execution": {
                "role": "worker",
                "persona": "none",
                "capability_tier": tier,
                "write_intent": write_intent,
                "allowed_files": ["memory_seed/task_packet.py"] if write_intent == "writing" else [],
                "forbidden_files": [".memory-seed/policy.md"],
                "validation": ["python -m unittest tests.test_task_packet"],
                "output_contract": ["Return a source-linked handoff."],
                "expected_absent": [],
                "acceptance_observables": [
                    {
                        "name": "task-packet-tests",
                        "command": "python -m unittest tests.test_task_packet",
                        "expected_exit_code": 0,
                    }
                ],
                "implements": [],
            },
            "retrieval": {
                "profile": "implementation",
                "profile_version": 1,
                "overrides": {},
            },
            "budget": {
                "supplemental_input_tokens": 1000,
                "output_tokens": 2000,
                "over_soft_cap": "fail",
                "over_soft_cap_reason": None,
            },
        }

    def binding(self, root, *, writing=False):
        base_sha = self.git(root, "rev-parse", "main")
        branch = self.git(root, "rev-parse", "--abbrev-ref", "HEAD")
        return {
            "owner": "orchestrator",
            "agent_type": "codex",
            "base_branch": "main",
            "base_sha": base_sha,
            "working_branch": branch if writing else None,
            "worktree": str(root) if writing else None,
            "expected_directory": str(root),
            "integration_artifact": "branch" if writing else "handoff",
        }

    def compile_at_envelope(self, root, tier, desired, *, allow=False):
        dispatch = self.dispatch(tier=tier)
        dispatch["budget"].update(
            {
                "supplemental_input_tokens": max(0, desired - 5_000),
                "output_tokens": 2_000,
                "over_soft_cap": "allow" if allow else "fail",
                "over_soft_cap_reason": (
                    "Coupled evidence requires one bounded synthesis." if allow else None
                ),
            }
        )
        seen = set()
        for _ in range(20):
            supplemental = dispatch["budget"]["supplemental_input_tokens"]
            self.assertNotIn(supplemental, seen, "boundary adjustment oscillated")
            seen.add(supplemental)
            try:
                outcome = compile_task_packet(dispatch, self.binding(root), root)
                total = outcome["input_ledger"]["total_context_envelope_tokens"]
            except TaskPacketValidationError as exc:
                if exc.code not in {"soft_cap_exceeded", "shard_required"}:
                    raise
                outcome = exc
                total = exc.details["total_context_tokens"]
            if total == desired:
                return outcome
            dispatch["budget"]["supplemental_input_tokens"] += desired - total
            self.assertGreaterEqual(dispatch["budget"]["supplemental_input_tokens"], 0)
        self.fail(f"could not construct exact {tier} envelope {desired}")

    def test_dispatch_is_strict_defaults_memory_owner_and_enforces_context_band(self):
        dispatch = self.dispatch()
        normalized = normalize_task_dispatch(dispatch)
        self.assertEqual(normalized["memory_update_policy"], "orchestrator")
        self.assertIsNone(normalized["execution"]["persona"])
        context = normalized["project_context"]
        context_text = "\n".join(
            [
                context["project_type_and_purpose"],
                context["relevant_subsystem"],
                context["task_fit"],
                context["downstream_use"],
                *context["non_goals"],
            ]
        )
        self.assertGreaterEqual(estimate_tokens(context_text), 100)
        self.assertLessEqual(estimate_tokens(context_text), 250)
        dispatch["unknown"] = True
        with self.assertRaisesRegex(TaskPacketValidationError, "unknown fields"):
            normalize_task_dispatch(dispatch)
        too_short = self.dispatch()
        for key in (
            "project_type_and_purpose",
            "relevant_subsystem",
            "task_fit",
            "downstream_use",
        ):
            too_short["project_context"][key] = "brief"
        with self.assertRaisesRegex(TaskPacketValidationError, "100-250"):
            normalize_task_dispatch(too_short)

    def test_worker_checkpoint_requires_named_guarded_branch_local_scope(self):
        dispatch = self.dispatch(write_intent="writing")
        dispatch["memory_update_policy"] = "worker_checkpoint"
        with self.assertRaises(TaskPacketValidationError):
            normalize_task_dispatch(dispatch)
        dispatch["memory_checkpoints"] = {
            "names": ["implementation-complete"],
            "session_paths": [".memory-seed/sessions/2026-08/2026-08-31.md"],
            "branch_local_only": True,
            "guarded_append": True,
        }
        dispatch["execution"]["allowed_files"].append(
            ".memory-seed/sessions/2026-08/2026-08-31.md"
        )
        normalized = normalize_task_dispatch(dispatch)
        self.assertEqual(normalized["memory_checkpoints"]["names"], ["implementation-complete"])
        dispatch["memory_checkpoints"]["branch_local_only"] = False
        with self.assertRaisesRegex(TaskPacketValidationError, "must be true"):
            normalize_task_dispatch(dispatch)

    def test_checkpoint_paths_reject_wildcards_and_use_windows_alias_identity(self):
        dispatch = self.dispatch(write_intent="writing")
        dispatch["memory_update_policy"] = "worker_checkpoint"
        dispatch["execution"]["allowed_files"] = [
            ".MEMORY-SEED\\SESSIONS\\2026-08\\2026-08-31.md"
        ]
        dispatch["memory_checkpoints"] = {
            "names": ["implementation-complete"],
            "session_paths": [".memory-seed/sessions/2026-08/2026-08-31.md"],
            "branch_local_only": True,
            "guarded_append": True,
        }
        normalized = normalize_task_dispatch(dispatch)
        self.assertEqual(
            normalized["execution"]["allowed_files"],
            [".MEMORY-SEED/SESSIONS/2026-08/2026-08-31.md"],
        )

        wildcard = copy.deepcopy(dispatch)
        wildcard["memory_checkpoints"]["session_paths"] = [
            ".memory-seed/sessions/**/*.md"
        ]
        wildcard["execution"]["allowed_files"] = [
            ".memory-seed/sessions/**/*.md"
        ]
        with self.assertRaisesRegex(TaskPacketValidationError, "exact .* files"):
            normalize_task_dispatch(wildcard)

        alias_conflict = copy.deepcopy(dispatch)
        alias_conflict["execution"]["forbidden_files"] = [
            ".memory-seed/sessions/2026-08/2026-08-31.MD"
        ]
        with self.assertRaisesRegex(TaskPacketValidationError, "must not overlap"):
            normalize_task_dispatch(alias_conflict)

    def test_edit_authority_rejects_paths_outside_the_runtime(self):
        invalid_scopes = (
            "",
            ".",
            "../../outside.py",
            "memory_seed/../../../outside.py",
            r"..\..\outside.py",
            "/etc/passwd",
            r"C:\outside.py",
            r"C:outside.py",
            r"\\server\share\outside.py",
            r"\\?\C:\outside.py",
            r"\\.\C:\outside.py",
            "memory_seed/",
            "memory_seed//task_packet.py",
            "memory_seed/./task_packet.py",
            "memory_seed/*.py",
            "memory_seed/[ab].py",
            "memory_seed/{task,other}.py",
            "memory_seed/task_packet.py:stream",
            "memory_seed/NUL.txt",
        )
        for field in ("allowed_files", "forbidden_files"):
            for scope in invalid_scopes:
                with self.subTest(field=field, scope=scope):
                    dispatch = self.dispatch(write_intent="writing")
                    dispatch["execution"][field] = [scope]
                    with self.assertRaises(TaskPacketValidationError):
                        normalize_task_dispatch(dispatch)

        root = self.make_project()
        escaping = self.dispatch()
        escaping["execution"]["forbidden_files"] = ["../outside.py"]
        with self.assertRaises(TaskPacketValidationError):
            compile_task_packet(escaping, self.binding(root), root)

    def test_edit_authority_uses_one_windows_path_identity(self):
        duplicate = self.dispatch(write_intent="writing")
        duplicate["execution"]["allowed_files"] = [
            r"Memory_Seed\Task_Packet.py",
            "memory_seed/task_packet.py",
        ]
        with self.assertRaisesRegex(TaskPacketValidationError, "separator/case aliases"):
            normalize_task_dispatch(duplicate)

        conflict = self.dispatch(write_intent="writing")
        conflict["execution"]["allowed_files"] = [r"Memory_Seed\Task_Packet.py"]
        conflict["execution"]["forbidden_files"] = ["memory_seed/task_packet.py"]
        with self.assertRaisesRegex(TaskPacketValidationError, "must not overlap"):
            normalize_task_dispatch(conflict)

    def test_edit_authority_rejects_every_windows_reserved_component(self):
        reserved_scopes = (
            "CONIN$",
            "nested/conin$.txt",
            "CONOUT$",
            r"nested\ConOut$.log",
            "COM¹",
            "nested/com².txt",
            "CoM³.LOG",
            "LPT¹",
            "nested/lpt².txt",
            "LpT³.LOG",
        )
        for scope in reserved_scopes:
            with self.subTest(scope=scope):
                dispatch = self.dispatch(write_intent="writing")
                dispatch["execution"]["allowed_files"] = [scope]
                with self.assertRaises(TaskPacketValidationError):
                    normalize_task_dispatch(dispatch)

        valid_near_misses = (
            "CONIN",
            "CONOUT",
            "nested/COM⁴.txt",
            "LPT⁴.txt",
            "COM0.log",
            "LPT0.log",
            "COM10.log",
            "LPT10.log",
            "CONSOLE.md",
            "nested/auxiliary.txt",
        )
        for scope in valid_near_misses:
            with self.subTest(scope=scope):
                dispatch = self.dispatch(write_intent="writing")
                dispatch["execution"]["allowed_files"] = [scope]
                normalized = normalize_task_dispatch(dispatch)
                self.assertEqual(normalized["execution"]["allowed_files"], [scope])

    def test_exact_repo_relative_edit_scopes_preserve_read_only_semantics(self):
        writing = self.dispatch(write_intent="writing")
        writing["execution"]["allowed_files"] = [
            r"memory_seed\task_packet.py",
            "docs/My File.md",
            "LICENSE",
        ]
        writing["execution"]["forbidden_files"] = ["generated/output.json"]
        normalized = normalize_task_dispatch(writing)
        self.assertEqual(
            normalized["execution"]["allowed_files"],
            ["memory_seed/task_packet.py", "docs/My File.md", "LICENSE"],
        )

        read_only = self.dispatch(write_intent="read-only")
        read_only["execution"]["allowed_files"] = []
        read_only["execution"]["forbidden_files"] = ["memory_seed/task_packet.py"]
        normalized_read_only = normalize_task_dispatch(read_only)
        self.assertEqual(normalized_read_only["execution"]["allowed_files"], [])
        self.assertEqual(
            normalized_read_only["retrieval"],
            normalize_task_dispatch(self.dispatch())["retrieval"],
        )

    def test_effective_profile_requires_a_pinned_topic_or_path_selector(self):
        root = self.make_project()
        dispatch = self.dispatch()
        dispatch["retrieval"]["overrides"] = {
            "filters": {"paths": [], "topics": []},
            "selectors": {"pinned": []},
        }
        with self.assertRaises(TaskPacketValidationError) as caught:
            compile_task_packet(dispatch, self.binding(root), root)
        self.assertEqual(caught.exception.code, "empty_retrieval_scope")

    def test_read_only_binding_can_measure_current_tree_but_writing_is_explicit(self):
        root = self.make_project()
        measured = normalize_runtime_binding(
            self.binding(root), write_intent="read-only", cwd=root
        )
        self.assertEqual(measured["working_branch"], "main")
        self.assertEqual(Path(measured["worktree"]), root.resolve())
        self.assertEqual(
            set(measured),
            {
                "owner",
                "agent_type",
                "base_branch",
                "base_sha",
                "working_branch",
                "worktree",
                "expected_directory",
                "integration_artifact",
            },
        )

        dispatch = self.dispatch(write_intent="writing")
        incomplete = self.binding(root)
        with self.assertRaises(TaskPacketValidationError):
            compile_task_packet(dispatch, incomplete, root)
        self.git(root, "checkout", "-b", "codex/task-packet")
        packet = compile_task_packet(dispatch, self.binding(root, writing=True), root)
        self.assertEqual(packet["runtime_binding"]["working_branch"], "codex/task-packet")

    def test_binding_rejects_wrong_base_sha_and_expected_directory(self):
        root = self.make_project()
        binding = self.binding(root)
        binding["base_sha"] = "0" * 40
        with self.assertRaises(TaskPacketValidationError) as caught:
            normalize_runtime_binding(binding, write_intent="read-only", cwd=root)
        self.assertEqual(caught.exception.code, "binding_mismatch")
        binding = self.binding(root)
        binding["expected_directory"] = str(root / "elsewhere")
        with self.assertRaises(TaskPacketValidationError) as caught:
            normalize_runtime_binding(binding, write_intent="read-only", cwd=root)
        self.assertEqual(caught.exception.code, "binding_mismatch")

    def test_base_branch_must_be_an_exact_local_branch(self):
        root = self.make_project()
        self.git(root, "tag", "fixture-tag")
        base_sha = self.git(root, "rev-parse", "HEAD")
        for invalid in ("HEAD", "fixture-tag", base_sha, "main^{commit}"):
            with self.subTest(base_branch=invalid):
                binding = self.binding(root)
                binding["base_branch"] = invalid
                with self.assertRaises(TaskPacketValidationError) as caught:
                    normalize_runtime_binding(
                        binding, write_intent="read-only", cwd=root
                    )
                self.assertEqual(caught.exception.code, "invalid_binding")
                self.assertEqual(caught.exception.path, "runtime_binding.base_branch")
        self.assertEqual(
            normalize_runtime_binding(
                self.binding(root), write_intent="read-only", cwd=root
            )["base_branch"],
            "main",
        )

    def test_compilation_is_byte_identical_and_materializes_content_once(self):
        root = self.make_project()
        dispatch = self.dispatch()
        binding = self.binding(root)
        first = compile_task_packet(dispatch, binding, root)
        second = compile_task_packet(dispatch, binding, root)
        first_json = canonical_task_packet_json(first)
        second_json = canonical_task_packet_json(second)
        self.assertEqual(first_json, second_json)
        self.assertEqual(first["fingerprint"], second["fingerprint"])
        self.assertEqual(first["packet_schema"], TASK_PACKET_SCHEMA)
        self.assertFalse(first["retrieval_profile"]["effective_spec"]["output"]["include_excerpts"])
        self.assertTrue(all(item["excerpt"] is None for item in first["evidence_pack"]["evidence"]))
        for record in first["materialized_evidence"]:
            self.assertEqual(first_json.count(json.dumps(record["content"], ensure_ascii=False)), 1)
        self.assertEqual(
            estimate_tokens(first_json),
            first["input_ledger"]["serialized_packet_input_tokens"],
        )
        self.assertNotIn("generated_at", first_json)

    def test_every_packet_materializes_exact_active_agent_rules_baseline(self):
        root = self.make_project()
        source = root / ".memory-seed" / "agent-rules.md"
        raw = b"# Active agent rules\r\n\r\nExact active bytes.\r\n"
        source.write_bytes(raw)

        packet = compile_task_packet(self.dispatch(), self.binding(root), root)
        baseline = packet["worker_baseline"]
        agent_rules = baseline["sources"]["agent_rules"]

        self.assertEqual(agent_rules["source"], ".memory-seed/agent-rules.md")
        self.assertEqual(agent_rules["content"].encode("utf-8"), raw)
        self.assertEqual(agent_rules["byte_count"], len(raw))
        self.assertEqual(agent_rules["token_estimate"], estimate_tokens(raw))
        self.assertEqual(
            agent_rules["content_digest"],
            "sha256:" + hashlib.sha256(raw).hexdigest(),
        )
        self.assertIsNone(baseline["sources"]["session_logging"])
        self.assertTrue(baseline["fingerprint"].startswith("sha256:"))

    def test_session_logging_baseline_follows_checkpoint_or_session_write_authority(self):
        root = self.make_project()
        session_path = ".memory-seed/sessions/2026-09/2026-09-06.md"
        checkpoint = self.dispatch(write_intent="writing")
        checkpoint["memory_update_policy"] = "worker_checkpoint"
        checkpoint["memory_checkpoints"] = {
            "names": ["implementation-complete"],
            "session_paths": [session_path],
            "branch_local_only": True,
            "guarded_append": True,
        }
        checkpoint["execution"]["allowed_files"].append(session_path)
        checkpoint_packet = compile_task_packet(checkpoint, self.binding(root, writing=True), root)
        checkpoint_logging = checkpoint_packet["worker_baseline"]["sources"]["session_logging"]
        self.assertIsNotNone(checkpoint_logging)
        self.assertEqual(
            checkpoint_logging["content"],
            (root / ".memory-seed" / "skills" / "session_logging.md").read_bytes().decode("utf-8"),
        )

        session_writable = self.dispatch(write_intent="writing")
        session_writable["execution"]["allowed_files"].append(session_path)
        writable_packet = compile_task_packet(session_writable, self.binding(root, writing=True), root)
        self.assertIsNotNone(writable_packet["worker_baseline"]["sources"]["session_logging"])

        ordinary_packet = compile_task_packet(self.dispatch(), self.binding(root), root)
        self.assertIsNone(ordinary_packet["worker_baseline"]["sources"]["session_logging"])

        instructions = checkpoint_packet["execution_defaults"]["session_logging"]
        self.assertTrue(instructions["delegated"])
        self.assertIn("memory_session_append", instructions["append_requirement"])
        self.assertIn("python -X utf8 -m memory_seed.cli session append", instructions["append_requirement"])
        self.assertIn("omit timestamp", instructions["clock_ownership"])
        self.assertIn("Direct Markdown session edits are forbidden.", instructions["prohibitions"])
        self.assertIn("Explicit timestamps are forbidden.", instructions["prohibitions"])
        self.assertIn("narrowly scoped repair/backfill exception", instructions["repair_backfill_exception"])

    def test_baseline_sources_change_packet_and_baseline_fingerprints(self):
        root = self.make_project()
        first = compile_task_packet(self.dispatch(), self.binding(root), root)
        agent_rules = root / ".memory-seed" / "agent-rules.md"
        agent_rules.write_text("# Active agent rules\n\nChanged baseline.\n", encoding="utf-8")
        second = compile_task_packet(self.dispatch(), self.binding(root), root)
        self.assertNotEqual(first["worker_baseline"]["fingerprint"], second["worker_baseline"]["fingerprint"])
        self.assertNotEqual(first["fingerprint"], second["fingerprint"])

    def test_missing_required_worker_baseline_fails_clearly(self):
        root = self.make_project()
        (root / ".memory-seed" / "agent-rules.md").unlink()
        with self.assertRaises(TaskPacketValidationError) as caught:
            compile_task_packet(self.dispatch(), self.binding(root), root)
        self.assertEqual(caught.exception.code, "missing_worker_baseline")
        self.assertIn("agent-rules", caught.exception.path)

        root = self.make_project()
        (root / ".memory-seed" / "skills" / "session_logging.md").unlink()
        dispatch = self.dispatch(write_intent="writing")
        dispatch["execution"]["allowed_files"].append(
            ".memory-seed/sessions/2026-09/2026-09-06.md"
        )
        with self.assertRaises(TaskPacketValidationError) as caught:
            compile_task_packet(dispatch, self.binding(root, writing=True), root)
        self.assertEqual(caught.exception.code, "missing_worker_baseline")
        self.assertIn("session_logging", caught.exception.path)

    def test_constitution_projection_prefers_explicit_anchors_and_never_truncates(self):
        root = self.make_project()
        constitution = root / "docs" / "CONSTITUTION.md"
        constitution.write_text(
            "# Constitution\n\n**Version:** 1.0 — **RATIFIED 2026-09-05**\n\n"
            "## Authority\n\n"
            "<!-- constitution-ref: constitution:v1#markdown-authority -->\n"
            "Markdown is authoritative. This complete clause is deliberately long enough to prove projection.\n\n"
            "## Safety\n\n"
            "<!-- constitution-ref: constitution:v1#local-first -->\n"
            "The runtime remains local-first and bounded.\n",
            encoding="utf-8",
        )
        dispatch = self.dispatch()
        dispatch["constitution_refs"] = ["constitution:v1#markdown-authority"]
        packet = compile_task_packet(dispatch, self.binding(root), root)
        projection = packet["constitution_projection"]
        self.assertEqual(projection["mode"], "anchored_clauses")
        self.assertEqual(projection["selection_mode"], "explicit_dispatch_refs")
        clause = projection["clauses"][0]
        self.assertEqual(clause["ref"], "constitution:v1#markdown-authority")
        self.assertEqual(clause["path"], "docs/CONSTITUTION.md")
        self.assertEqual(clause["line_range"], [7, 9])
        self.assertEqual(clause["selection_reason"], "explicit dispatch Constitution reference")
        self.assertRegex(clause["full_document_digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertRegex(clause["clause_digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertIn("Markdown is authoritative", clause["content"])
        self.assertFalse(any(item["kind"] == "constitution" for item in packet["materialized_evidence"]))

        missing = self.dispatch()
        missing["constitution_refs"] = ["constitution:v1#missing"]
        with self.assertRaises(TaskPacketValidationError) as caught:
            compile_task_packet(missing, self.binding(root), root)
        self.assertEqual(caught.exception.code, "invalid_constitution_projection")

    def test_constitution_projection_uses_adr_refs_then_explicit_full_fallback(self):
        dispatch = normalize_task_dispatch(self.dispatch())
        constitution = {
            "id": "docs/CONSTITUTION.md",
            "kind": "constitution",
            "source": "docs/CONSTITUTION.md",
            "content": (
                "# Constitution\n\n**Version:** 1.0 — **RATIFIED 2026-09-05**\n\n"
                "## Authority\n\n"
                "<!-- constitution-ref: constitution:v1#authority -->\n"
                "Authority clause.\n"
            ),
        }
        adr = {
            "id": "adr_authority",
            "kind": "adr",
            "source": ".memory-seed/decisions/adr_authority.md",
            "content": "### Constitution\n\n- `constitution:v1#authority` (governing)\n",
        }
        adr_projection = project_constitution(dispatch, [constitution, adr])
        self.assertEqual(adr_projection["selection_mode"], "selected_adr_refs")
        self.assertEqual(adr_projection["clauses"][0]["ref"], "constitution:v1#authority")

        fallback = project_constitution(
            dispatch,
            [{
                **constitution,
                "content": "# Constitution\n\n**Version:** 1.0 — **RATIFIED 2026-09-05**\n\nNo stable anchors yet.\n",
            }],
        )
        self.assertEqual(fallback["mode"], "full_document_fallback")
        self.assertIn("No stable anchors", fallback["full_document"]["content"])

    def test_constitution_projection_keeps_all_ranked_clauses_above_target(self):
        dispatch = normalize_task_dispatch(self.dispatch(tier="economy"))
        body = "grounded " * 500
        constitution = {
            "id": "docs/CONSTITUTION.md",
            "kind": "constitution",
            "source": "docs/CONSTITUTION.md",
            "content": (
                "# Constitution\n\n**Version:** 1.0 — **RATIFIED 2026-09-05**\n\n"
                "<!-- constitution-ref: constitution:v1#first -->\n" + body + "\n"
                "<!-- constitution-ref: constitution:v1#second -->\n" + body + "\n"
                "<!-- constitution-ref: constitution:v1#third -->\n" + body + "\n"
            ),
        }
        projection = project_constitution(dispatch, [constitution])
        self.assertEqual(projection["selection_mode"], "ranked_whole_clauses")
        self.assertEqual([item["ref"] for item in projection["clauses"]], [
            "constitution:v1#first",
            "constitution:v1#second",
            "constitution:v1#third",
        ])
        self.assertTrue(projection["over_target"])
        self.assertEqual(projection["governing_overage"]["status"], "over_target")
        self.assertGreater(projection["governing_overage"]["tokens"], 0)

    def test_constitution_projection_refuses_missing_adr_bindings_and_unratified_documents(self):
        dispatch = normalize_task_dispatch(self.dispatch())
        constitution = {
            "id": "docs/CONSTITUTION.md",
            "kind": "constitution",
            "source": "docs/CONSTITUTION.md",
            "content": (
                "# Constitution\n\n**Version:** 1.0 — **RATIFIED 2026-09-05**\n\n"
                "<!-- constitution-ref: constitution:v1#authority -->\nAuthority clause.\n"
            ),
        }
        for label, content, expected in (
            (
                "valid-plus-missing",
                "- `constitution:v1#authority` (governing)\n- `constitution:v1#missing` (supporting)\n",
                {"adr_id": "adr_mixed", "role": "supporting", "missing_anchor": "constitution:v1#missing"},
            ),
            (
                "missing-only",
                "- `constitution:v1#missing` (governing)\n",
                {"adr_id": "adr_missing", "role": "governing", "missing_anchor": "constitution:v1#missing"},
            ),
        ):
            with self.subTest(label=label):
                adr_id = expected["adr_id"]
                adr = {"id": adr_id, "kind": "adr", "source": f".memory-seed/decisions/{adr_id}.md", "content": content}
                with self.assertRaises(TaskPacketValidationError) as caught:
                    project_constitution(dispatch, [constitution, adr])
                self.assertEqual(caught.exception.code, "invalid_constitution_projection")
                self.assertIn(expected, caught.exception.details["missing_adr_bindings"])

        for label, content in (
            ("unratified", "# Constitution\n\n<!-- constitution-ref: constitution:v1#authority -->\nAuthority.\n"),
            ("invalid-version", "# Constitution\n\n**Version:** unknown — **RATIFIED**\n"),
            ("incompatible-anchor", "# Constitution\n\n**Version:** 1.0 — **RATIFIED 2026-09-05**\n\n<!-- constitution-ref: constitution:v2#authority -->\nAuthority.\n"),
        ):
            with self.subTest(label=label), self.assertRaises(TaskPacketValidationError) as caught:
                project_constitution(dispatch, [{**constitution, "content": content}])
            self.assertEqual(caught.exception.code, "invalid_constitution_projection")

    def test_execution_contracts_validate_creation_acceptance_and_implementation(self):
        dispatch = self.dispatch(write_intent="writing")
        dispatch["execution"]["expected_absent"] = ["docs/new-contract.md"]
        with self.assertRaisesRegex(TaskPacketValidationError, "allowed_files"):
            normalize_task_dispatch(dispatch)
        dispatch["execution"]["allowed_files"].append("docs/new-contract.md")
        normalized = normalize_task_dispatch(dispatch)
        self.assertEqual(normalized["execution"]["expected_absent"], ["docs/new-contract.md"])

        invalid_observable = self.dispatch()
        invalid_observable["execution"]["acceptance_observables"] = [{"name": "x"}]
        with self.assertRaisesRegex(TaskPacketValidationError, "acceptance_observables"):
            normalize_task_dispatch(invalid_observable)
        invalid_implements = self.dispatch()
        invalid_implements["execution"]["implements"] = ["mse_packet0001"]
        with self.assertRaisesRegex(TaskPacketValidationError, "exact .*decision"):
            normalize_task_dispatch(invalid_implements)

        root = self.make_project()
        self.git(root, "checkout", "-b", "codex/contracts")
        binding = self.binding(root, writing=True)
        writing = self.dispatch(write_intent="writing")
        writing["execution"]["allowed_files"].append("docs/new-contract.md")
        writing["execution"]["expected_absent"] = ["docs/new-contract.md"]
        writing_packet = compile_task_packet(writing, binding, root)
        defaults = writing_packet["execution_defaults"]
        self.assertEqual(defaults["preflight"][0], f"Set-Location -LiteralPath {str(root)!r}")
        self.assertEqual(
            defaults["preflight"][1],
            "python -X utf8 -m memory_seed.cli worktree guard --agent codex --write-intent",
        )
        self.assertIn("git branch --show-current", defaults["preflight"])
        self.assertEqual(defaults["escalated_shell"]["required_location"], str(root))
        self.assertEqual(defaults["escalated_shell"]["required_branch"], "codex/contracts")
        self.assertTrue({"base_sha", "final_head_sha", "all_commit_hashes"} <= set(defaults["handoff"]))
        (root / "docs" / "new-contract.md").write_text("created\n", encoding="utf-8")
        with self.assertRaises(TaskPacketValidationError) as caught:
            compile_task_packet(writing, binding, root)
        self.assertEqual(caught.exception.code, "unexpected_existing_path")

        implements = self.dispatch()
        implements["execution"]["implements"] = ["mse_packet0001:d1"]
        self.assertEqual(
            compile_task_packet(implements, self.binding(root), root)["dispatch"]["execution"]["implements"],
            ["mse_packet0001:d1"],
        )
        unresolved = self.dispatch()
        unresolved["execution"]["implements"] = ["mse_packet0001:d2"]
        with self.assertRaises(TaskPacketValidationError) as caught:
            compile_task_packet(unresolved, self.binding(root), root)
        self.assertEqual(caught.exception.code, "unresolved_implements")

    def test_writing_packet_activation_uses_a_packet_artifact_and_preserves_reasoned_history(self):
        root = self.make_project()
        self.git(root, "checkout", "-b", "codex/activation")
        dispatch = self.dispatch(write_intent="writing")
        dispatch["execution"]["implements"] = ["mse_packet0001:d1"]
        packet = compile_task_packet(dispatch, self.binding(root, writing=True), root)

        local_config = root / ".git" / "config"
        before_local = local_config.read_bytes()
        isolated_global = root / "protected-global.gitconfig"
        isolated_global.write_text("[user]\n\tname = Protected Global\n", encoding="utf-8")
        before_global = isolated_global.read_bytes()
        with mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(isolated_global)}, clear=False):
            first = activate_task_packet(packet, root)

        self.assertTrue(first["activated"])
        self.assertEqual(first["implements"], ["mse_packet0001:d1"])
        self.assertEqual(local_config.read_bytes(), before_local)
        self.assertEqual(isolated_global.read_bytes(), before_global)
        artifact = Path(first["activation_artifact"])
        history = Path(first["activation_history"])
        self.assertTrue(artifact.is_file())
        self.assertTrue(history.is_file())
        artifact_payload = json.loads(artifact.read_text(encoding="utf-8"))
        self.assertEqual(artifact_payload["packet"]["fingerprint"], packet["fingerprint"])
        self.assertEqual(artifact_payload["receipt"]["packet_fingerprint"], packet["fingerprint"])
        self.assertEqual(artifact_payload["receipt"]["dispatch_fingerprint"], packet["dispatch_fingerprint"])
        self.assertEqual(artifact_payload["receipt"]["evidence_pack_fingerprint"], packet["evidence_pack"]["fingerprint"])
        self.assertIn("activation", packet["execution_defaults"])
        self.assertIn("cadence", packet["execution_defaults"])
        first_history = history.read_text(encoding="utf-8")
        first_artifact = artifact.read_text(encoding="utf-8")

        identical = activate_task_packet(packet, root)
        self.assertFalse(identical["binding_updated"])
        self.assertEqual(history.read_text(encoding="utf-8"), first_history)
        self.assertEqual(artifact.read_text(encoding="utf-8"), first_artifact)

        changed_implements = self.dispatch(write_intent="writing")
        changed_implements["execution"]["implements"] = []
        updated_packet = compile_task_packet(changed_implements, self.binding(root, writing=True), root)
        with self.assertRaises(TaskPacketValidationError) as caught:
            activate_task_packet(updated_packet, root)
        self.assertEqual(caught.exception.code, "binding_update_required")

        updated = activate_task_packet(
            updated_packet,
            root,
            binding_update_reason="Removed completed decision attribution from this packet.",
        )
        self.assertTrue(updated["binding_updated"])
        self.assertIn("Removed completed", updated["binding_update_reason"])
        history_after_implements = history.read_text(encoding="utf-8")
        receipt = json.loads(history_after_implements.splitlines()[-1])
        self.assertEqual(receipt["changed"], ["implements"])
        self.assertEqual(receipt["reason"], updated["binding_update_reason"])

        # Repeating the exact replacement cannot erase its historical reason.
        activate_task_packet(updated_packet, root)
        self.assertEqual(history.read_text(encoding="utf-8"), history_after_implements)

        changed_scope = self.dispatch(write_intent="writing")
        changed_scope["execution"]["allowed_files"].append("docs/evidence.md")
        scoped_packet = compile_task_packet(changed_scope, self.binding(root, writing=True), root)
        with self.assertRaises(TaskPacketValidationError) as caught:
            activate_task_packet(scoped_packet, root)
        self.assertEqual(caught.exception.code, "binding_update_required")
        scoped = activate_task_packet(
            scoped_packet,
            root,
            binding_update_reason="Expanded packet scope for the evidence fixture.",
        )
        self.assertTrue(scoped["binding_updated"])

    def test_activation_rejects_unvalidated_runtime_binding_fields(self):
        root = self.make_project()
        self.git(root, "checkout", "-b", "codex/activation-binding")
        dispatch = self.dispatch(write_intent="writing")
        dispatch["execution"]["implements"] = ["mse_packet0001:d1"]
        packet = compile_task_packet(dispatch, self.binding(root, writing=True), root)

        invalid_values = {
            "owner": "Not A Slug",
            "agent_type": "Not A Slug",
            "integration_artifact": "untracked",
            "base_branch": "codex/missing-base",
            "base_sha": "0" * 40,
            "expected_directory": str(root.parent),
            "working_branch": "main",
            "worktree": str(root.parent),
        }
        for field, value in invalid_values.items():
            with self.subTest(field=field):
                invalid = copy.deepcopy(packet)
                invalid["runtime_binding"][field] = value
                identity = dict(invalid)
                identity.pop("fingerprint", None)
                invalid["fingerprint"] = "sha256:" + hashlib.sha256(
                    json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                ).hexdigest()
                with self.assertRaises(TaskPacketValidationError) as caught:
                    activate_task_packet(invalid, root)
                self.assertEqual(caught.exception.code, "binding_mismatch")

    def test_packet_activation_uses_the_measured_stacked_base_for_cadence(self):
        root = self.make_project()
        self.git(root, "checkout", "-b", "codex/stack-base")
        (root / "stack-base-only.txt").write_text("base layer\n", encoding="utf-8")
        self.git(root, "add", "stack-base-only.txt")
        self.git(root, "commit", "-m", "stack base")
        stacked_base = self.git(root, "rev-parse", "HEAD")
        self.git(root, "checkout", "-b", "codex/stacked-cadence")

        dispatch = self.dispatch(write_intent="writing")
        dispatch["execution"]["implements"] = ["mse_packet0001:d1"]
        binding = self.binding(root, writing=True)
        binding["base_branch"] = "codex/stack-base"
        binding["base_sha"] = stacked_base
        packet = compile_task_packet(dispatch, binding, root)
        activate_task_packet(packet, root)
        (root / "product-change.txt").write_text("top layer\n", encoding="utf-8")

        cadence = commit_cadence(root)

        self.assertEqual(cadence.base_ref, stacked_base)
        self.assertEqual((cadence.files, cadence.churn), (1, 1))

    def test_component_measurements_are_complete_and_fingerprinted(self):
        root = self.make_project()
        first_dispatch = self.dispatch()
        second_dispatch = self.dispatch()
        second_dispatch["execution"]["acceptance_observables"][0]["command"] = "python -m unittest changed"
        first = compile_task_packet(first_dispatch, self.binding(root), root)
        second = compile_task_packet(second_dispatch, self.binding(root), root)
        self.assertNotEqual(first["dispatch_fingerprint"], second["dispatch_fingerprint"])
        measurements = first["input_ledger"]["component_measurements"]
        self.assertEqual(
            set(measurements),
            {
                "serialized_packet_input_tokens",
                "fixed_instruction_tokens",
                "tool_schema_input_tokens",
                "supplemental_input_reserve_tokens",
                "output_reasoning_reserve_tokens",
                "materialized_agent_rules_tokens",
                "materialized_session_logging_tokens",
            },
        )
        self.assertTrue(all("tokens" in item and "percentage_of_context_envelope" in item for item in measurements.values()))
        self.assertEqual(
            measurements["materialized_agent_rules_tokens"]["accounting_scope"],
            "subset_of_serialized_packet_input_tokens",
        )

    def test_materialization_rejects_tampered_and_stale_packs(self):
        root = self.make_project()
        spec = load_retrieval_profile("implementation", 1, root)
        spec["output"]["include_excerpts"] = False
        pack = resolve_retrieval_spec(spec, root)
        tampered = copy.deepcopy(pack)
        tampered["evidence"][0]["content_digest"] = "sha256:" + "0" * 64
        tampered["fingerprint"] = _evidence_pack_fingerprint(tampered)
        with self.assertRaises(RetrievalSpecResolutionError) as caught:
            materialize_evidence_pack(tampered, root)
        self.assertEqual(caught.exception.code, "content_digest_mismatch")

        path = root / "docs" / "evidence.md"
        path.write_text(path.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
        with self.assertRaises(RetrievalSpecResolutionError) as caught:
            materialize_evidence_pack(pack, root)
        self.assertEqual(caught.exception.code, "stale_pack")

    def test_all_budget_boundaries_and_override_rules(self):
        common = {
            "tier": "economy",
            "fixed_instruction_tokens": 0,
            "tool_schema_tokens": 0,
            "supplemental_input_tokens": 0,
            "output_tokens": 0,
            "over_soft_cap": "fail",
            "over_soft_cap_reason": None,
        }
        at_target = assess_context_budget(serialized_packet_tokens=16_000, **common)
        self.assertEqual(at_target["status"], "within_target")
        above_target = assess_context_budget(serialized_packet_tokens=16_001, **common)
        self.assertEqual(above_target["status"], "elevated")
        at_soft = assess_context_budget(serialized_packet_tokens=24_000, **common)
        self.assertEqual(at_soft["status"], "elevated")
        with self.assertRaises(TaskPacketValidationError) as caught:
            assess_context_budget(serialized_packet_tokens=24_001, **common)
        self.assertEqual(caught.exception.code, "soft_cap_exceeded")
        allowed = assess_context_budget(
            serialized_packet_tokens=24_001,
            **{
                **common,
                "over_soft_cap": "allow",
                "over_soft_cap_reason": "Coupled evidence requires one synthesis.",
            },
        )
        self.assertEqual(allowed["status"], "allowed_above_soft_cap")
        with self.assertRaises(TaskPacketValidationError) as caught:
            assess_context_budget(
                serialized_packet_tokens=32_000,
                **{
                    **common,
                    "over_soft_cap": "allow",
                    "over_soft_cap_reason": "Still too large.",
                },
            )
        self.assertEqual(caught.exception.code, "shard_required")

    def test_compiler_hits_exact_target_soft_override_and_shard_boundaries_for_all_tiers(self):
        root = self.make_project()
        bands = {
            "economy": (16_000, 24_000, 32_000),
            "balanced": (32_000, 48_000, 64_000),
            "frontier": (64_000, 96_000, 128_000),
        }
        for tier, (target, soft_cap, shard) in bands.items():
            with self.subTest(tier=tier, boundary="target"):
                packet = self.compile_at_envelope(root, tier, target)
                self.assertIsInstance(packet, dict)
                self.assertEqual(packet["input_ledger"]["status"], "within_target")
                self.assertEqual(
                    packet["input_ledger"]["total_context_envelope_tokens"], target
                )
            with self.subTest(tier=tier, boundary="soft_cap"):
                packet = self.compile_at_envelope(root, tier, soft_cap)
                self.assertIsInstance(packet, dict)
                self.assertEqual(packet["input_ledger"]["status"], "elevated")
                self.assertEqual(
                    packet["input_ledger"]["total_context_envelope_tokens"], soft_cap
                )
            with self.subTest(tier=tier, boundary="override"):
                refusal = self.compile_at_envelope(root, tier, soft_cap + 1)
                self.assertIsInstance(refusal, TaskPacketValidationError)
                self.assertEqual(refusal.code, "soft_cap_exceeded")
                self.assertEqual(
                    refusal.details["total_context_tokens"], soft_cap + 1
                )
                packet = self.compile_at_envelope(root, tier, soft_cap + 1, allow=True)
                self.assertIsInstance(packet, dict)
                self.assertEqual(
                    packet["input_ledger"]["status"], "allowed_above_soft_cap"
                )
                self.assertEqual(
                    packet["input_ledger"]["total_context_envelope_tokens"], soft_cap + 1
                )
            with self.subTest(tier=tier, boundary="shard"):
                refusal = self.compile_at_envelope(root, tier, shard, allow=True)
                self.assertIsInstance(refusal, TaskPacketValidationError)
                self.assertEqual(refusal.code, "shard_required")
                self.assertEqual(refusal.details["total_context_tokens"], shard)

    def test_tier_bands_are_exact(self):
        expected = {
            "economy": (16_000, 24_000, 32_000),
            "balanced": (32_000, 48_000, 64_000),
            "frontier": (64_000, 96_000, 128_000),
        }
        for tier, values in expected.items():
            with self.subTest(tier=tier):
                ledger = assess_context_budget(
                    tier,
                    serialized_packet_tokens=1,
                    fixed_instruction_tokens=0,
                    tool_schema_tokens=0,
                    supplemental_input_tokens=0,
                    output_tokens=0,
                    over_soft_cap="fail",
                    over_soft_cap_reason=None,
                )
                self.assertEqual(tuple(ledger["band"].values()), values)

    def test_optional_pricing_reports_five_and_six_x_ratios_and_cache(self):
        for output_price, ratio in ((5, 5.0), (6, 6.0)):
            with self.subTest(ratio=ratio):
                ledger = calculate_cost_ledger(
                    input_tokens=1_000_000,
                    output_tokens=100_000,
                    cached_input_tokens=500_000,
                    pricing={
                        "currency": "USD",
                        "effective_date": "2026-08-31",
                        "per_million_input": 1,
                        "per_million_cached_input": 0.1,
                        "per_million_output": output_price,
                        "tool_cost": 0.25,
                    },
                )
                self.assertEqual(ledger["output_input_ratio"], ratio)
                self.assertEqual(ledger["uncached_ceiling"], 1.25 + output_price / 10)
                self.assertIsNotNone(ledger["expected_cost"])
                self.assertEqual(
                    ledger["input_equivalent_tokens"],
                    1_250_000 + 100_000 * ratio,
                )

    def test_cost_is_explicitly_unavailable_without_prices(self):
        ledger = calculate_cost_ledger(
            input_tokens=1000, output_tokens=200, pricing=None
        )
        self.assertEqual(ledger["status"], "unavailable")
        self.assertEqual(ledger["reason"], "pricing_not_supplied")
        self.assertIsNone(ledger["uncached_ceiling"])

    def test_compiler_accounts_for_environment_and_pricing_without_network(self):
        root = self.make_project()
        packet = compile_task_packet(
            self.dispatch(),
            self.binding(root),
            root,
            environment={
                "fixed_instructions": ["Follow exact source ranges."],
                "tool_schemas": [{"name": "read", "input": {"path": "string"}}],
                "cached_input_tokens": 100,
            },
            pricing={
                "currency": "GBP",
                "effective_date": "2026-08-31",
                "per_million_input": 2,
                "per_million_cached_input": 0.2,
                "per_million_output": 10,
                "tool_cost": 0,
            },
        )
        self.assertGreater(packet["input_ledger"]["fixed_instruction_tokens"], 0)
        self.assertGreater(packet["input_ledger"]["tool_schema_input_tokens"], 0)
        self.assertEqual(packet["cost_ledger"]["output_input_ratio"], 5.0)
        self.assertEqual(packet["cost_ledger"]["cached_input_tokens"], 100)

    def test_cached_input_can_equal_the_converged_final_total_input(self):
        root = self.make_project()
        pricing = {
            "currency": "GBP",
            "effective_date": "2026-09-01",
            "per_million_input": 2,
            "per_million_cached_input": 0.2,
            "per_million_output": 10,
            "tool_cost": 0,
        }
        cached = 0
        for _ in range(12):
            packet = compile_task_packet(
                self.dispatch(),
                self.binding(root),
                root,
                environment={
                    "fixed_instructions": [],
                    "tool_schemas": [],
                    "cached_input_tokens": cached,
                },
                pricing=pricing,
            )
            final_input = packet["input_ledger"]["total_input_tokens"]
            if cached == final_input:
                break
            cached = final_input
        else:
            self.fail("cached-input/final-input equality did not converge")
        self.assertEqual(packet["cost_ledger"]["cached_input_tokens"], final_input)
        self.assertIsNotNone(packet["cost_ledger"]["expected_cost"])


if __name__ == "__main__":
    unittest.main()
