"""Decision-granularity retrieval: canonical identity, whole DRAFT blocks, relevance bands.

Why this exists (field evidence E9 dry-run): entry-granularity search returned every entry in a
small store and the agent still answered "not recorded", because 59% of each 280-char excerpt was
identical YAML frontmatter and the facts sat in bodies the excerpt never reached. Decision chunks
make the served unit the thing the agent must reason about, keyed by the `mse_x:dN` identity that
topics, lifecycle edges, ADRs and Trace already speak.

The 2026-05-26 decision (ms-845042c7) that made entries the default rejected heading-level chunking
because it "can separate a decision from its rationale and validation". These tests pin the property
that makes decision chunks exempt: a `#### Dn` block carries its own D/R/A/F/T/S.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.retrieval import (
    DECISION_TEXT_LIMIT,
    _selection_preview,
    get_chunk,
    load_corpus,
    search_memory,
)
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

    def test_planning_consumes_decision_topics_without_changing_reader_or_lifecycle(self):
        from memory_seed.planning import PlanningCandidate, assess_candidate
        from memory_seed.topics import TopicIndex, TopicRecord

        root = self.make_store()
        chunks = self.chunks(root)
        index = TopicIndex("topics.yaml", True, "3", (
            TopicRecord("retrieval"), TopicRecord("ranking", parent="retrieval"),
            TopicRecord("hooks"), TopicRecord("shared-topic"),
        ))
        first, second = chunks["mse_multidecision1:d1"], chunks["mse_multidecision1:d2"]
        for chunk, expected in ((first, True), (second, False)):
            candidate = PlanningCandidate(chunk.chunk_id, chunk.text, "session_evidence", topics=chunk.topics)
            assessment = assess_candidate(candidate, ("ranking",), index)
            self.assertEqual(assessment.binding, expected)
            self.assertIn("not exhaustive", assessment.coverage)
        # The same readers still return the same identities, DRAFT bodies and edges.
        self.assertEqual(self.chunks(root), chunks)

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

    def test_decision_fetch_carries_entry_level_sections(self):
        """A decision fetched alone arrives with the entry sections that frame it."""
        root = self.make_store()
        payload = get_chunk("mse_multidecision1:d1", root)
        headings = [s["heading"] for s in payload["entry_context"]]
        self.assertIn("Summary", headings)
        # The decision's own block is still the payload text, unchanged.
        self.assertIn("- D: Cache widgets", payload["text"])

    def test_entry_context_excludes_sibling_decisions(self):
        """Asking for :d1 must not drag :d2 along inside the context."""
        root = self.make_store()
        payload = get_chunk("mse_multidecision1:d1", root)
        joined = "\n".join(s["text"] for s in payload["entry_context"])
        self.assertNotIn("#### D2", joined)
        self.assertNotIn("Priya", joined)  # d2's distinctive content

    def test_entry_granularity_fetch_has_no_entry_context(self):
        """The whole entry already contains its sections; duplicating them would be noise."""
        root = self.make_store()
        payload = get_chunk("mse_plainentry0001", root)
        self.assertEqual(payload["entry_context"], [])


class SelectionPreviewTests(unittest.TestCase):
    """A preview answers "is this the one I want?", so it has to carry signal.

    Before this, an entry preview was the first 280 characters of the raw chunk - which begins
    with the YAML metadata fence. Measured on the live corpus: 857 of 891 entry chunks led with
    the fence, it took a median 84% of the budget, and 124 previews never escaped it at all. Every
    field in it is already a structured key on the same result, so the preview spent the reader's
    whole selection budget restating the envelope.
    """

    FENCED = (
        "```yaml\nentry_id: mse_preview00000001\nuser_initials: JNL\nbranch: main\n```\n\n"
        "- D: " + ("filler prose. " * 40)
        + "The distinctive phrase is nearest-runtime discovery. "
        + ("trailing prose. " * 40)
    )

    def test_the_metadata_fence_never_reaches_the_preview(self):
        preview = _selection_preview(self.FENCED)
        self.assertNotIn("entry_id:", preview)
        self.assertNotIn("```", preview)
        self.assertTrue(preview.startswith("- D: filler prose."), preview[:60])

    def test_the_window_opens_on_the_term_that_made_it_rank(self):
        preview = _selection_preview(self.FENCED, matched_terms=("nearest-runtime",))
        self.assertIn("nearest-runtime discovery", preview)
        # The head was elided to reach it, and says so.
        self.assertTrue(preview.startswith("... "), preview[:40])

    def test_a_shortened_preview_names_the_call_that_returns_the_rest(self):
        self.assertIn("memory_get_chunk", _selection_preview(self.FENCED))
        # An unshortened preview claims nothing: no marker, no ellipsis.
        whole = _selection_preview("```yaml\nentry_id: mse_x\n```\n\n- D: Short and complete.")
        self.assertEqual(whole, "- D: Short and complete.")

    def test_no_live_entry_chunk_is_previewed_as_metadata(self):
        """The corpus-wide assertion: the 857 are 0, and none regressed to empty."""
        repo = Path(__file__).resolve().parents[1]
        for granularity in ("decision", "entry"):
            for chunk in load_corpus(repo, granularity=granularity):
                if chunk.granularity == "decision":
                    continue
                preview = _selection_preview(chunk.text)
                self.assertTrue(preview.strip(), chunk.chunk_id)
                self.assertNotIn("entry_id:", preview[:120], chunk.chunk_id)


if __name__ == "__main__":
    unittest.main()
    unittest.main()
