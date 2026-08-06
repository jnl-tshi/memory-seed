"""Decision-granularity retrieval: canonical identity, whole DRAFT blocks, relevance bands.

Why this exists (field evidence E9 dry-run): entry-granularity search returned every entry in a
small store and the agent still answered "not recorded", because 59% of each 280-char excerpt was
identical YAML frontmatter and the facts sat in bodies the excerpt never reached. Decision chunks
make the served unit the thing the agent must reason about, keyed by the `mse_x:dN` identity that
topics, lifecycle edges, ADRs and Trace already speak.

The 2026-05-26 decision (ms-845042c7) that made entries the default rejected heading-level chunking
because it "can separate a decision from its rationale and validation". These tests pin the property
that makes decision chunks exempt: a `#### Dn` block carries its own D/R/A/F/T.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.retrieval import DECISION_TEXT_LIMIT, search_memory
from memory_seed.semantic_cache import extract_memory_chunks

MULTI = """## 2026-06-10 09:30 - Two decisions in one entry

```yaml
entry_id: mse_multidecision1
user_initials: JN
agent_type: claude
topics:
  - retrieval:d1
  - hooks:d2
  - shared-topic
replaces:
  - d1 -> mse_oldentry000001:d1
```

### Summary

- Settled two unrelated questions in one sitting.

### Decisions

#### D1 - Adopt the widget cache

- D: Cache widgets in memory for the request lifetime.
- R: The registry lookup dominated the profile at 40% of request time.
- A: A process-wide cache was rejected - staleness across requests.
- F: `widgets/cache.py`.
- T: `pytest tests/test_widgets.py`.

#### D2 - Name Priya as release approver

- D: Priya signs off every release before the tag is pushed.
- R: One named approver beats a rota nobody remembers to consult.
- F: `RELEASE.md`.
"""

NO_DECISION = """## 2026-06-12 09:00 - Notes with no decision section

```yaml
entry_id: mse_nodecision00001
user_initials: JN
agent_type: claude
```

### Summary

- Read through the release checklist; nothing was decided.
"""

SINGLE = """## 2026-06-11 10:00 - A plain entry with no decision headings

```yaml
entry_id: mse_plainentry0001
user_initials: JN
agent_type: claude
```

### Summary

- Routine housekeeping with a single inline decision.

### Decision

- D: Keep the changelog folded per release.
- R: Unreleased sections rot when nobody folds them.
"""


class DecisionRetrievalTests(unittest.TestCase):
    def make_store(self):
        root = Path(tempfile.mkdtemp(prefix="memory-seed-decision-test-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        sessions = root / ".memory-seed" / "sessions" / "2026-06"
        sessions.mkdir(parents=True)
        (sessions / "2026-06-10.md").write_text(MULTI, encoding="utf-8")
        (sessions / "2026-06-11.md").write_text(SINGLE, encoding="utf-8")
        (sessions / "2026-06-12.md").write_text(NO_DECISION, encoding="utf-8")
        return root

    def chunks(self, root):
        return {c.chunk_id: c for c in extract_memory_chunks(root, granularity="decision")}

    def test_canonical_decision_identity(self):
        chunks = self.chunks(self.make_store())
        self.assertIn("mse_multidecision1:d1", chunks)
        self.assertIn("mse_multidecision1:d2", chunks)

    def test_legacy_singular_decision_becomes_a_decision_chunk(self):
        """The `### Decision` form is the same concept as `#### D1`, and is chunked as one.

        This fixture is titled "no decision headings" but carries a singular `### Decision` section
        with D/R bullets - which is exactly the shape 494 entries in the real store use. Until
        2026-08-06 it produced no decision chunk, fell back to the whole-entry unit, and was then
        served as a 280-character preview: 45% of the corpus, 51% of its text, invisible.
        """
        chunks = self.chunks(self.make_store())
        self.assertIn("mse_plainentry0001:d1", chunks)
        block = chunks["mse_plainentry0001:d1"]
        self.assertEqual(block.granularity, "decision")
        self.assertIn("- D: Keep the changelog folded", block.text)
        self.assertIn("- R: Unreleased sections rot", block.text)

    def test_entry_with_no_decision_section_at_all_stays_whole(self):
        """The property the test above used to claim, with a fixture that actually has it."""
        chunks = self.chunks(self.make_store())
        self.assertIn("mse_nodecision00001", chunks)
        self.assertEqual(chunks["mse_nodecision00001"].granularity, "entry")

    def test_decision_block_keeps_its_own_rationale(self):
        """The property that exempts decision chunks from the 2026-05-26 objection."""
        chunks = self.chunks(self.make_store())
        first = chunks["mse_multidecision1:d1"].text
        self.assertIn("- D: Cache widgets", first)
        self.assertIn("- R: The registry lookup", first)
        self.assertIn("- A: A process-wide cache", first)
        self.assertIn("- T: `pytest", first)
        # and does not bleed into the sibling decision
        self.assertNotIn("Priya", first)

    def test_topics_and_edges_are_decision_scoped(self):
        chunks = self.chunks(self.make_store())
        first, second = chunks["mse_multidecision1:d1"], chunks["mse_multidecision1:d2"]
        self.assertIn("retrieval", first.topics)
        self.assertIn("shared-topic", first.topics)  # bare topics apply to every decision
        self.assertNotIn("hooks", first.topics)
        self.assertIn("hooks", second.topics)
        self.assertTrue(any(e[0] == "replaces" for e in first.decision_edges))
        self.assertFalse([e for e in second.decision_edges if e[1] == "d1"])

    def test_search_serves_whole_draft_block_not_a_preview(self):
        root = self.make_store()
        payload = search_memory("widget cache registry lookup", root, semantic_enabled=False)
        hit = next(r for r in payload["results"] if r["chunk_id"] == "mse_multidecision1:d1")
        # The full rationale is present - this is the regression the dry-run exposed.
        self.assertIn("- R: The registry lookup", hit["excerpt"])
        self.assertNotIn("...", hit["excerpt"][-4:])
        self.assertLessEqual(len(hit["excerpt"]), DECISION_TEXT_LIMIT + 80)

    def test_relevance_band_and_no_match_signal(self):
        root = self.make_store()
        payload = search_memory("widget cache registry lookup", root, semantic_enabled=False)
        self.assertIn("relevance_rule", payload)
        self.assertIn(payload["results"][0]["relevance"], ("strong", "weak", "none"))
        self.assertFalse(payload["no_match_above_threshold"])

        nothing = search_memory(
            "kubernetes helm chart rollout strategy", root, semantic_enabled=False
        )
        self.assertTrue(nothing["no_match_above_threshold"])
        self.assertTrue(all(r["relevance"] != "strong" for r in nothing["results"]))

    def test_entry_granularity_still_available(self):
        root = self.make_store()
        payload = search_memory(
            "widget cache", root, semantic_enabled=False, granularity="entry"
        )
        self.assertTrue(
            all(":d" not in r["chunk_id"] for r in payload["results"]),
            "entry granularity must not return decision ids",
        )


if __name__ == "__main__":
    unittest.main()
