import json
import unittest

from memory_seed.mcp_server import MUTATING_TOOL_NAMES, TOOLS, call_tool


class DecisionMarkerToolTests(unittest.TestCase):
    def test_tool_is_listed_and_explicitly_read_only(self):
        tool = next(tool for tool in TOOLS if tool["name"] == "memory_decision_mark")
        self.assertNotIn("memory_decision_mark", MUTATING_TOOL_NAMES)
        self.assertIn("does not write", tool["description"])
        self.assertEqual(
            set(tool["inputSchema"]["required"]),
            {"strength", "state", "origin", "trigger_class", "issue_hint", "trigger_quote"},
        )
        self.assertFalse(tool["inputSchema"]["additionalProperties"])

    def test_valid_marker_returns_inert_stable_payload(self):
        arguments = {
            "strength": "hard",
            "state": "accepted",
            "origin": "user",
            "trigger_class": "explicit_commitment",
            "issue_hint": "Use evidence-first capture",
            "trigger_quote": "Yeah, I think that would be wise",
        }

        first = call_tool("memory_decision_mark", arguments)
        second = call_tool("memory_decision_mark", arguments)

        self.assertEqual(first, second)
        self.assertTrue(first["ok"])
        self.assertFalse(first["authoritative"])
        self.assertFalse(first["written"])
        self.assertEqual(first["schema_version"], "memory-decision-mark-v1")
        self.assertIn("marker_digest", first)
        self.assertNotIn("marker", first)
        json.dumps(first)

    def test_rejects_unknown_missing_and_semantically_invalid_fields(self):
        base = {
            "strength": "hard",
            "state": "accepted",
            "origin": "user",
            "trigger_class": "contextual_acceptance",
            "issue_hint": "Choose the parser",
            "trigger_quote": "that's the right approach",
        }
        cases = [
            {**base, "cwd": "."},
            {key: value for key, value in base.items() if key != "trigger_quote"},
            {**base, "strength": "certain"},
            {**base, "trigger_class": "agent_inference", "strength": "hard", "origin": "agent"},
            {**base, "state": "proposed", "strength": "hard"},
            {**base, "trigger_quote": "x" * 501},
        ]

        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = call_tool("memory_decision_mark", arguments)
                self.assertFalse(result["ok"])
                self.assertFalse(result["written"])
                self.assertTrue(result["issues"])


if __name__ == "__main__":
    unittest.main()
