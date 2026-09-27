"""Design Discovery authority lookup and link carry-forward."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from memory_seed.discovery import DiscoveryError, discovery_assess, discovery_evidence

REPO = Path(__file__).resolve().parents[1]

CONSTITUTION = """# Constitution

**Version:** 2.0 — **RATIFIED 2026-09-05**

## 2. Invariants

<!-- constitution-ref: constitution:v2#markdown-authority -->
Markdown is the source of truth; every index is a derived projection.

<!-- constitution-ref: constitution:v2#append-only -->
Session history is append-only.

## 3. Principles

<!-- constitution-ref: constitution:v2#evidence-first -->
Retrieval returns evidence before conclusions.
"""

SESSIONS = """## 2026-09-01 09:00 - Retrieval ranks evidence

```yaml
entry_id: mse_discovery0001
user_initials: JN
agent_type: claude
project_path: .
subproject_path: null
topics:
  - retrieval
```

### Decision

- D: Rank evidence before summarising.
- R: Readers verify the evidence.

## 2026-09-02 09:00 - Retrieval returns packs

```yaml
entry_id: mse_discovery0002
user_initials: JN
agent_type: claude
project_path: .
subproject_path: null
topics:
  - retrieval
related_entries:
  - mse_discovery0001
```

### Decision

- D: Return an evidence pack with reasons.
- R: A pack is auditable.
"""

TOPICS = "schema_version: 2\ntopics:\n  - slug: retrieval\n    description: Retrieval.\n    axis: area\n"


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="memory-seed-discovery-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        profile = (REPO / ".memory-seed" / "retrieval-profiles" / "design-discovery" / "v1.yaml").read_text(
            encoding="utf-8"
        )
        files = {
            "docs/CONSTITUTION.md": CONSTITUTION,
            ".memory-seed/sessions/2026-09/2026-09-01.md": SESSIONS,
            ".memory-seed/topics.yaml": TOPICS,
            ".memory-seed/retrieval-profiles/design-discovery/v1.yaml": profile,
        }
        for relative, text in files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        from memory_seed.adr import ConstitutionRef, promote_decision

        result = promote_decision(
            self.root,
            adr_id="adr_evidence_ranking",
            source_entry_id="mse_discovery0001",
            source_decision="d1",
            title="Evidence ranking",
            topics=["retrieval"],
            user_initials="JN",
            agent_type="claude",
            source="derived",
            reason="fixture",
            impact="fixture",
            constitution_refs=[ConstitutionRef(ref="constitution:v2#evidence-first", role="governing")],
        )
        self.assertTrue(result.ok, result.issues)
        from memory_seed.adr import transition_adr

        accepted = transition_adr(
            self.root,
            adr_id="adr_evidence_ranking",
            status="accepted",
            decision_ref="mse_discovery0001:d1",
            update_entry_id="mse_discovery0002",
            source="derived",
            reason="fixture",
        )
        self.assertTrue(accepted.ok, accepted.issues)
        for args in (("init", "-b", "main"), ("config", "user.email", "t@example.com"),
                     ("config", "user.name", "T"), ("add", "."), ("commit", "-m", "fixture")):
            subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)

    def evidence(self, **kwargs):
        return discovery_evidence(self.root, topics=kwargs.pop("topics", ["retrieval"]), **kwargs)

    def test_lookup_returns_adr_decisions_and_governing_clauses(self):
        result = self.evidence()
        self.assertFalse(result["empty"])
        summary = result["summary"]
        self.assertEqual([row["ref"] for row in summary["adrs"]], ["adr_evidence_ranking"])
        self.assertEqual(summary["adrs"][0]["head"], "mse_discovery0001:d1")
        self.assertEqual(
            {row["ref"] for row in summary["decisions"]},
            {"mse_discovery0001:d1", "mse_discovery0002:d1"},
        )
        self.assertIn("constitution:v2#evidence-first", [row["ref"] for row in summary["constitution"]])
        self.assertNotIn("docs/CONSTITUTION.md", [row["ref"] for row in summary["constitution"]])

    def test_an_area_without_history_is_a_finding_not_an_error(self):
        result = self.evidence(topics=[])
        self.assertTrue(result["empty"])
        self.assertEqual(result["warnings"][0]["code"], "no_prior_evidence")

    def test_pins_seed_the_lookup(self):
        result = self.evidence(topics=[], pins=["mse_discovery0002"])
        refs = {row["ref"] for row in result["summary"]["decisions"]}
        self.assertEqual(refs, {"mse_discovery0001:d1", "mse_discovery0002:d1"})

    def test_verdicts_become_the_append_envelope(self):
        pack = self.evidence()["pack"]
        answer = discovery_assess(
            self.root,
            pack=pack,
            verdicts=[
                {"ref": "mse_discovery0002:d1", "relation": "refines", "why": "adds per-item reasons", "applies_to": ["d1"]},
                {"ref": "mse_discovery0001:d1", "relation": "related", "applies_to": ["d2"]},
                {"ref": "constitution:v2#evidence-first", "relation": "governed-by", "why": "packs show evidence first"},
                {"ref": "adr_evidence_ranking", "relation": "no-edge"},
            ],
        )
        self.assertEqual(
            answer["links"],
            {
                # single-decision entries are named bare, as the append requires
                "d1": {"evolves": [{"ref": "mse_discovery0002", "type": "refines", "why": "adds per-item reasons"}]},
                "d2": {"related_entries": ["mse_discovery0001"]},
            },
        )
        # consulted names the entries behind every assessed decision (an ADR by
        # its head), no-edge included; clauses are authority, not candidates
        self.assertEqual(answer["consulted"], ["mse_discovery0002", "mse_discovery0001"])
        self.assertEqual(
            [row["relation"] for row in answer["authority_answer"] if row["ref"] == "adr_evidence_ranking"],
            ["no-edge"],
        )
        self.assertEqual(answer["governing_clauses"][0]["ref"], "constitution:v2#evidence-first")
        self.assertIn(
            "| `constitution:v2#evidence-first` | constitution | Retrieval returns evidence before conclusions. |",
            answer["authority_table"],
        )
        self.assertEqual(answer["adr_outcomes_needed"], [])

    def test_an_adr_verdict_links_its_head_and_flags_the_review(self):
        pack = self.evidence()["pack"]
        answer = discovery_assess(
            self.root,
            pack=pack,
            verdicts=[{"ref": "adr_evidence_ranking", "relation": "builds-on", "why": "extends the ranking"}],
        )
        self.assertEqual(
            answer["links"]["d1"]["evolves"],
            [{"ref": "mse_discovery0001", "type": "builds-on", "why": "extends the ranking"}],
        )
        self.assertEqual([item["adr_id"] for item in answer["adr_outcomes_needed"]], ["adr_evidence_ranking"])
        self.assertTrue(answer["authority_answer"][0]["adr_outcome_needed"])

    def test_closed_list_why_and_kind_rules_fail_closed(self):
        pack = self.evidence()["pack"]
        bad = [
            {"ref": "mse_invented0001:d1", "relation": "related"},
            {"ref": "mse_discovery0002:d1", "relation": "replaces"},
            {"ref": "constitution:v2#evidence-first", "relation": "refines", "why": "x"},
            {"ref": "mse_discovery0001:d1", "relation": "supersedes", "why": "x"},
        ]
        with self.assertRaises(DiscoveryError) as caught:
            discovery_assess(self.root, pack=pack, verdicts=bad)
        issues = " ".join(caught.exception.issues)
        self.assertIn("not in the evidence pack", issues)
        self.assertIn("needs a one-line 'why'", issues)
        self.assertIn("cannot be 'refines'", issues)
        self.assertIn("relation must be one of", issues)

    def test_one_refines_successor_per_target(self):
        pack = self.evidence()["pack"]
        with self.assertRaises(DiscoveryError) as caught:
            discovery_assess(
                self.root,
                pack=pack,
                verdicts=[
                    {"ref": "mse_discovery0001:d1", "relation": "refines", "why": "a", "applies_to": ["d1"]},
                    {"ref": "mse_discovery0001:d1", "relation": "refines", "why": "b", "applies_to": ["d2"]},
                ],
            )
        self.assertIn("refined twice", " ".join(caught.exception.issues))

    def test_a_stale_pack_is_refused(self):
        pack = self.evidence()["pack"]
        session = self.root / ".memory-seed" / "sessions" / "2026-09" / "2026-09-01.md"
        session.write_text(session.read_text(encoding="utf-8") + "\n", encoding="utf-8", newline="\n")
        with self.assertRaises(DiscoveryError):
            discovery_assess(
                self.root, pack=pack, verdicts=[{"ref": "mse_discovery0001:d1", "relation": "no-edge"}]
            )


if __name__ == "__main__":
    unittest.main()
