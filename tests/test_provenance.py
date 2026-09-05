from __future__ import annotations

import copy
import unittest

from memory_seed.provenance import (
    PACKET_IMPLEMENTS_ACTIVATION_SCHEMA,
    PROVENANCE_BINDING_SCHEMA,
    PROVENANCE_LEDGER_SCHEMA,
    append_replacement,
    build_binding,
    build_packet_implements_activation,
    build_runtime_ownership,
    hunk_id,
    project_ledger,
    validate_append_only_update,
    validate_binding,
    validate_packet_implements_activation,
)


OID_A = "a" * 40
OID_B = "b" * 40
OID_C = "c" * 40
HINT_A = "sha256:" + "1" * 64
HINT_B = "sha256:" + "2" * 64
PACKET = "sha256:" + "3" * 64


class ProvenanceContractTests(unittest.TestCase):
    def hunk(self, *, old_start: int = 4, new_start: int = 4) -> dict[str, object]:
        return {
            "hunk_id": hunk_id(
                commit=OID_A,
                parent=OID_B,
                file="memory_seed/example.py",
                old_blob=OID_B,
                new_blob=OID_A,
                old_range={"start": old_start, "count": 2},
                new_range={"start": new_start, "count": 3},
                context_hints={"old": HINT_A, "new": HINT_B},
            ),
            "old_range": {"start": old_start, "count": 2},
            "new_range": {"start": new_start, "count": 3},
            "context_hints": {"old": HINT_A, "new": HINT_B},
        }

    def binding(self, decision_ref: str = "mse_72c6knzvhwzss39j:d2", *, hunk: dict[str, object] | None = None):
        return build_binding(
            decision_ref=decision_ref,
            commit=OID_A,
            parent=OID_B,
            file="memory_seed/example.py",
            old_blob=OID_B,
            new_blob=OID_A,
            hunks=[hunk or self.hunk()],
        )

    def ledger(self, binding=None):
        return {
            "schema": PROVENANCE_LEDGER_SCHEMA,
            "version": 1,
            "bindings": [binding or self.binding()],
            "replacements": [],
        }

    def test_binding_is_reference_only_and_deterministic(self):
        first = self.binding()
        second = self.binding()
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], PROVENANCE_BINDING_SCHEMA)
        self.assertRegex(first["binding_id"], r"^msb_[0-9a-f]{64}$")
        self.assertRegex(first["hunks"][0]["hunk_id"], r"^msh_[0-9a-f]{64}$")
        self.assertEqual(set(first["hunks"][0]["context_hints"]), {"old", "new"})

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
        contaminated["hunks"][0]["context_hints"]["new"] = "def source_text():"
        result = validate_binding(contaminated)
        self.assertFalse(result.ok)
        self.assertIn("sha256", result.issues[0].message)

    def test_replacement_extends_an_append_only_ledger_and_projects_current_head(self):
        original = self.binding()
        successor = build_binding(
            decision_ref="mse_72c6knzvhwzss39j:d3",
            commit=OID_C,
            parent=OID_A,
            file="memory_seed/example.py",
            old_blob=OID_A,
            new_blob=OID_C,
            hunks=[{
                "hunk_id": hunk_id(
                    commit=OID_C, parent=OID_A, file="memory_seed/example.py",
                    old_blob=OID_A, new_blob=OID_C,
                    old_range={"start": 4, "count": 3},
                    new_range={"start": 4, "count": 4},
                    context_hints={"old": HINT_B, "new": HINT_A},
                ),
                "old_range": {"start": 4, "count": 3},
                "new_range": {"start": 4, "count": 4},
                "context_hints": {"old": HINT_B, "new": HINT_A},
            }],
        )
        before = self.ledger(original)
        after = append_replacement(
            before, replaces=original["binding_id"], replacement=successor,
            reason="corrected-reference",
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
            ledger=self.ledger(binding),
        )
        result = validate_packet_implements_activation(activation, ledger=self.ledger(binding))
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


if __name__ == "__main__":
    unittest.main()
