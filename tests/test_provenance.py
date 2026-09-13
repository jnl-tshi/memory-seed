from __future__ import annotations

import copy
import unittest

from memory_seed.provenance import (
    PACKET_IMPLEMENTS_ACTIVATION_SCHEMA,
    ProvenanceValidationError,
    PROVENANCE_BINDING_SCHEMA,
    PROVENANCE_LEDGER_SCHEMA,
    activation_id,
    append_replacement,
    authorize_runtime_operation,
    build_binding,
    build_ledger,
    build_packet_implements_activation,
    build_replacement,
    build_runtime_ownership,
    hunk_id,
    patch_bytes_digest,
    project_ledger,
    validate_ledger,
    validate_append_only_update,
    validate_binding,
    validate_packet_implements_activation,
)


OID_A = "a" * 40
OID_B = "b" * 40
OID_C = "c" * 40
PATCH_A = "sha256:" + "1" * 64
PATCH_B = "sha256:" + "2" * 64
PACKET = "sha256:" + "3" * 64


class ProvenanceContractTests(unittest.TestCase):
    authorship = {"provenance": "first-hand", "actor": {"kind": "agent", "id": "codex"}}

    def hunk(self, *, old_start: int = 4, new_start: int = 4) -> dict[str, object]:
        patch = patch_bytes_digest(PATCH_A)
        return {
            "hunk_id": hunk_id(
                commit=OID_A,
                parent=OID_B,
                file="memory_seed/example.py",
                old_range={"start": old_start, "count": 2},
                new_range={"start": new_start, "count": 3},
                patch_bytes=patch,
            ),
            "old_range": {"start": old_start, "count": 2},
            "new_range": {"start": new_start, "count": 3},
            "patch_bytes": patch,
            "context_hint": None,
        }

    def binding(self, decision_ref: str = "mse_72c6knzvhwzss39j:d2", *, hunk: dict[str, object] | None = None):
        return build_binding(
            decision_ref=decision_ref,
            authorship=self.authorship,
            commit=OID_A,
            parent=OID_B,
            file="memory_seed/example.py",
            old_blob=OID_B,
            new_blob=OID_A,
            hunks=[hunk or self.hunk()],
        )

    def runtime(self, *, kind="runtime", owner_id="root", state="active"):
        return build_runtime_ownership(
            runtime_path=".", owner_kind=kind, owner_id=owner_id, owner_state=state
        )

    def ledger(self, binding=None, *, runtime=None, replacements=()):
        return build_ledger(
            runtime=runtime or self.runtime(), bindings=[binding or self.binding()], replacements=replacements
        )

    def test_binding_is_reference_only_and_deterministic(self):
        first = self.binding()
        second = self.binding()
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], PROVENANCE_BINDING_SCHEMA)
        self.assertRegex(first["binding_id"], r"^msb_[0-9a-f]{64}$")
        self.assertRegex(first["hunks"][0]["hunk_id"], r"^msh_[0-9a-f]{64}$")
        self.assertEqual(first["authorship"], self.authorship)
        self.assertEqual(first["hunks"][0]["context_hint"], None)
        self.assertEqual(first["hunks"][0]["patch_bytes"], patch_bytes_digest(PATCH_A))

        contaminated = copy.deepcopy(first)
        contaminated["patch"] = "@@ source must never be here @@"
        result = validate_binding(contaminated)
        self.assertFalse(result.ok)
        self.assertEqual(result.issues[0].code, "invalid_provenance")
        self.assertIn("unknown fields", result.issues[0].message)

    def test_binding_refuses_tampered_id_and_text_context_hints(self):
        tampered = copy.deepcopy(self.binding())
        tampered["hunks"][0]["new_range"]["count"] = 4
        result = validate_binding(tampered)
        self.assertFalse(result.ok)
        self.assertIn("deterministic hunk", result.issues[0].message)

        contaminated = copy.deepcopy(self.binding())
        contaminated["hunks"][0]["context_hint"] = "def source_text():"
        result = validate_binding(contaminated)
        self.assertFalse(result.ok)
        self.assertIn("derived later", result.issues[0].message)

        bad_digest = copy.deepcopy(self.binding())
        bad_digest["hunks"][0]["patch_bytes"]["bytes"] = b"must not persist"
        result = validate_binding(bad_digest)
        self.assertFalse(result.ok)
        self.assertIn("unknown fields", result.issues[0].message)

    def test_replacement_extends_an_append_only_ledger_and_projects_current_head(self):
        original = self.binding()
        successor = build_binding(
            decision_ref="mse_72c6knzvhwzss39j:d3",
            authorship={"provenance": "reconstructed", "actor": {"kind": "system", "id": "replay"}},
            commit=OID_C,
            parent=OID_A,
            file="memory_seed/example.py",
            old_blob=OID_A,
            new_blob=OID_C,
            hunks=[{
                "hunk_id": hunk_id(
                    commit=OID_C, parent=OID_A, file="memory_seed/example.py",
                    old_range={"start": 4, "count": 3},
                    new_range={"start": 4, "count": 4},
                    patch_bytes=patch_bytes_digest(PATCH_B),
                ),
                "old_range": {"start": 4, "count": 3},
                "new_range": {"start": 4, "count": 4},
                "patch_bytes": patch_bytes_digest(PATCH_B),
                "context_hint": None,
            }],
        )
        before = self.ledger(original)
        after = append_replacement(
            before, replaces=original["binding_id"], replacement=successor,
            reason="corrected-reference", reason_decision_ref="mse_72c6knzvhwzss39j:d1",
        )
        self.assertTrue(validate_append_only_update(before, after).ok)
        projection = project_ledger(after)
        self.assertEqual(projection["active_binding_ids"], [successor["binding_id"]])
        self.assertEqual(projection["replaced_binding_ids"], [original["binding_id"]])

        rewritten = copy.deepcopy(after)
        rewritten["bindings"] = list(reversed(rewritten["bindings"]))
        result = validate_append_only_update(before, rewritten)
        self.assertFalse(result.ok)
        self.assertEqual(result.issues[0].code, "not_append_only")

    def test_retired_pod_is_readable_but_cannot_activate_new_binding(self):
        runtime = build_runtime_ownership(
            runtime_path=".", owner_kind="pod", owner_id="provenance", owner_state="retired"
        )
        binding = self.binding()
        activation = build_packet_implements_activation(
            packet_fingerprint=PACKET,
            implements=[binding["decision_ref"]],
            binding_ids=[binding["binding_id"]],
            runtime=runtime,
            ledger=self.ledger(binding, runtime=runtime),
        )
        result = validate_packet_implements_activation(activation, ledger=self.ledger(binding, runtime=runtime))
        self.assertFalse(result.ok)
        self.assertEqual(result.issues[0].code, "retired_owner")

    def test_packet_implements_activation_requires_exact_ledger_coverage(self):
        runtime = build_runtime_ownership(
            runtime_path=".", owner_kind="runtime", owner_id="root", owner_state="active"
        )
        binding = self.binding()
        activation = build_packet_implements_activation(
            packet_fingerprint=PACKET,
            implements=[binding["decision_ref"]],
            binding_ids=[binding["binding_id"]],
            runtime=runtime,
            ledger=self.ledger(binding),
        )
        self.assertEqual(activation["schema"], PACKET_IMPLEMENTS_ACTIVATION_SCHEMA)
        self.assertTrue(validate_packet_implements_activation(activation, ledger=self.ledger(binding)).ok)

        extra = copy.deepcopy(activation)
        extra["implements"] = [binding["decision_ref"], "mse_72c6knzvhwzss39j:d3"]
        # A caller cannot preserve the old ID after changing activation inputs.
        result = validate_packet_implements_activation(extra, ledger=self.ledger(binding))
        self.assertFalse(result.ok)
        self.assertIn("deterministic activation", result.issues[0].message)

    def test_hunk_identity_is_sensitive_to_every_declared_input(self):
        common = {
            "commit": OID_A,
            "parent": OID_B,
            "file": "memory_seed/example.py",
            "old_range": {"start": 4, "count": 2},
            "new_range": {"start": 4, "count": 3},
            "patch_bytes": patch_bytes_digest(PATCH_A),
        }
        baseline = hunk_id(**common)
        variants = (
            {"commit": OID_C},
            {"parent": None},
            {"file": "memory_seed/other.py"},
            {"old_range": {"start": 5, "count": 2}},
            {"new_range": {"start": 4, "count": 4}},
            {"patch_bytes": patch_bytes_digest(PATCH_B)},
        )
        for changed in variants:
            with self.subTest(changed=changed):
                self.assertNotEqual(baseline, hunk_id(**(common | changed)))

        first_hand = self.binding()
        reconstructed = build_binding(
            decision_ref=first_hand["decision_ref"],
            authorship={"provenance": "reconstructed", "actor": {"kind": "system", "id": "replay"}},
            commit=OID_A,
            parent=OID_B,
            file="memory_seed/example.py",
            old_blob=OID_B,
            new_blob=OID_A,
            hunks=[self.hunk()],
        )
        self.assertNotEqual(first_hand["binding_id"], reconstructed["binding_id"])
        malformed = copy.deepcopy(first_hand)
        malformed["authorship"]["actor"]["id"] = "not an actor identity"
        self.assertFalse(validate_binding(malformed).ok)

    def test_runtime_authorization_distinguishes_root_pod_retired_and_detached(self):
        cases = (
            (self.runtime(), True),
            (self.runtime(kind="pod", owner_id="active-pod", state="active"), True),
            (self.runtime(kind="pod", owner_id="retired-pod", state="retired"), False),
            (self.runtime(kind="detached-former-root", owner_id="former-root", state="detached"), False),
        )
        for runtime, append_allowed in cases:
            with self.subTest(owner=runtime["owner"]):
                self.assertTrue(authorize_runtime_operation(runtime, operation="read").ok)
                result = authorize_runtime_operation(runtime, operation="append")
                self.assertEqual(result.ok, append_allowed)
        detached = cases[-1][0]
        self.assertEqual(
            detached["sidecar_path"], ".memory-seed/provenance/detached-roots/former-root.md"
        )
        successor = self.binding(hunk=self.hunk(new_start=5))
        for runtime in (cases[2][0], detached):
            with self.subTest(new_binding_owner=runtime["owner"]):
                with self.assertRaises(ProvenanceValidationError):
                    append_replacement(
                        self.ledger(runtime=runtime),
                        replaces=self.binding()["binding_id"],
                        replacement=successor,
                        reason="corrected-reference",
                        reason_decision_ref="mse_72c6knzvhwzss39j:d1",
                    )

    def test_append_only_update_refuses_raw_retired_and_detached_appends(self):
        for runtime, expected_code in (
            (self.runtime(kind="pod", owner_id="retired-pod", state="retired"), "retired_owner"),
            (self.runtime(kind="detached-former-root", owner_id="former-root", state="detached"), "detached_owner"),
        ):
            with self.subTest(owner=runtime["owner"], change="binding"):
                previous = self.ledger(runtime=runtime)
                successor = self.binding(hunk=self.hunk(new_start=5))
                candidate = {**previous, "bindings": [*previous["bindings"], successor]}
                result = validate_append_only_update(previous, candidate)
                self.assertFalse(result.ok)
                self.assertEqual(result.issues[0].code, expected_code)
            with self.subTest(owner=runtime["owner"], change="replacement"):
                previous = self.ledger(runtime=runtime)
                successor = self.binding(hunk=self.hunk(new_start=5))
                replacement = build_replacement(
                    replaces=previous["bindings"][0]["binding_id"], replacement=successor,
                    reason="corrected-reference", reason_decision_ref="mse_72c6knzvhwzss39j:d1",
                )
                candidate = {
                    **previous,
                    "bindings": [*previous["bindings"], successor],
                    "replacements": [replacement],
                }
                result = validate_append_only_update(previous, candidate)
                self.assertFalse(result.ok)
                self.assertEqual(result.issues[0].code, expected_code)
            with self.subTest(owner=runtime["owner"], change="unchanged"):
                previous = self.ledger(runtime=runtime)
                self.assertTrue(validate_ledger(previous).ok)
                self.assertTrue(validate_append_only_update(previous, previous).ok)

    def test_activation_requires_owned_active_exact_many_to_many_bindings(self):
        first = self.binding()
        second = self.binding(hunk=self.hunk(new_start=5))
        third = self.binding("mse_72c6knzvhwzss39j:d3", hunk=self.hunk(old_start=7))
        ledger = build_ledger(runtime=self.runtime(), bindings=[first, second, third])
        activation = build_packet_implements_activation(
            packet_fingerprint=PACKET,
            implements=[first["decision_ref"], third["decision_ref"]],
            binding_ids=[first["binding_id"], second["binding_id"], third["binding_id"]],
            runtime=self.runtime(),
            ledger=ledger,
        )
        self.assertTrue(validate_packet_implements_activation(activation, ledger=ledger).ok)
        self.assertEqual(first["hunks"][0]["hunk_id"], self.binding("mse_72c6knzvhwzss39j:d3")["hunks"][0]["hunk_id"])
        self.assertFalse(validate_packet_implements_activation(activation).ok)
        self.assertEqual(validate_packet_implements_activation(activation).issues[0].code, "ledger_required")

        arbitrary = copy.deepcopy(activation)
        arbitrary["binding_ids"] = ["msb_" + "f" * 64]
        arbitrary["activation_id"] = activation_id(
            packet_fingerprint=PACKET, implements=arbitrary["implements"],
            binding_ids=arbitrary["binding_ids"], runtime=arbitrary["runtime"],
        )
        self.assertFalse(validate_packet_implements_activation(arbitrary, ledger=ledger).ok)

        unrelated = copy.deepcopy(activation)
        unrelated["implements"] = [third["decision_ref"]]
        unrelated["activation_id"] = activation_id(
            packet_fingerprint=PACKET, implements=unrelated["implements"],
            binding_ids=unrelated["binding_ids"], runtime=unrelated["runtime"],
        )
        self.assertFalse(validate_packet_implements_activation(unrelated, ledger=ledger).ok)

        foreign = self.runtime(kind="pod", owner_id="foreign-pod", state="active")
        unowned = copy.deepcopy(activation)
        unowned["runtime"] = foreign
        unowned["activation_id"] = activation_id(
            packet_fingerprint=PACKET, implements=unowned["implements"],
            binding_ids=unowned["binding_ids"], runtime=foreign,
        )
        unowned_result = validate_packet_implements_activation(unowned, ledger=ledger)
        self.assertFalse(unowned_result.ok)
        self.assertEqual(unowned_result.issues[0].code, "unowned_ledger")

        unknown = copy.deepcopy(activation)
        unknown["patch"] = "not a contract field"
        self.assertFalse(validate_packet_implements_activation(unknown, ledger=ledger).ok)

    def test_replaced_binding_cannot_activate_and_replacement_graph_refuses_conflicts(self):
        original = self.binding()
        successor = self.binding(hunk=self.hunk(new_start=5))
        replacement = build_replacement(
            replaces=original["binding_id"], replacement=successor,
            reason="corrected-reference", reason_decision_ref="mse_72c6knzvhwzss39j:d1",
        )
        ledger = build_ledger(
            runtime=self.runtime(), bindings=[original, successor], replacements=[replacement]
        )
        valid = build_packet_implements_activation(
            packet_fingerprint=PACKET, implements=[original["decision_ref"]],
            binding_ids=[successor["binding_id"]], runtime=self.runtime(), ledger=ledger,
        )
        self.assertTrue(validate_packet_implements_activation(valid, ledger=ledger).ok)
        stale = copy.deepcopy(valid)
        stale["binding_ids"] = [original["binding_id"]]
        stale["activation_id"] = activation_id(
            packet_fingerprint=PACKET, implements=stale["implements"],
            binding_ids=stale["binding_ids"], runtime=stale["runtime"],
        )
        stale_result = validate_packet_implements_activation(stale, ledger=ledger)
        self.assertFalse(stale_result.ok)
        self.assertEqual(stale_result.issues[0].code, "replaced_binding")

        alternate = self.binding(hunk=self.hunk(old_start=9))
        competing = build_replacement(
            replaces=original["binding_id"], replacement=alternate,
            reason="superseded-reference", reason_decision_ref="mse_72c6knzvhwzss39j:d1",
        )
        conflict = {
            "schema": PROVENANCE_LEDGER_SCHEMA,
            "version": 1,
            "runtime": self.runtime(),
            "bindings": [original, successor, alternate],
            "replacements": [replacement, competing],
        }
        conflict_result = validate_ledger(conflict)
        self.assertFalse(conflict_result.ok)
        self.assertIn("competing", conflict_result.issues[0].message)

        cycle = build_replacement(
            replaces=successor["binding_id"], replacement=original,
            reason="corrected-reference", reason_decision_ref="mse_72c6knzvhwzss39j:d1",
        )
        cycle_result = validate_ledger({**conflict, "replacements": [replacement, cycle]})
        self.assertFalse(cycle_result.ok)
        self.assertIn("cycle", cycle_result.issues[0].message)

        malformed = copy.deepcopy(replacement)
        del malformed["reason_decision_ref"]
        missing_reason = validate_ledger({**conflict, "replacements": [malformed]})
        self.assertFalse(missing_reason.ok)
        self.assertIn("reason_decision_ref", missing_reason.issues[0].message)

        malformed_reason = copy.deepcopy(replacement)
        malformed_reason["reason"] = "narrative-code-is-not-allowed"
        invalid_reason = validate_ledger({**conflict, "replacements": [malformed_reason]})
        self.assertFalse(invalid_reason.ok)
        self.assertIn("reason code", invalid_reason.issues[0].message)

    def test_projection_exposes_adapter_evidence_states_without_reading_git(self):
        projection = project_ledger(self.ledger(), evidence_state="git-unavailable")
        self.assertEqual(projection["evidence_state"], "git-unavailable")
        self.assertEqual(projection["runtime"], self.runtime())


if __name__ == "__main__":
    unittest.main()
