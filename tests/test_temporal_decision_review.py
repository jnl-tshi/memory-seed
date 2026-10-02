import unittest

from hosted.evaluation.temporal_decision_review import compare_temporal_reviews


class TemporalDecisionReviewTests(unittest.TestCase):
    def test_later_implementation_is_not_an_extraction_error(self):
        reviews = [
            {"reviewer_id": reviewer, "case_id": "case-a", "field": "selected_action",
             "evidence_phase": "at_turn", "candidate_relation": "missing",
             "source_refs": ["turn-15"], "post_turn_refs": [],
             "external_refs": [], "log_refs": ["entry:d1"]}
            for reviewer in ("r1", "r2")
        ] + [
            {"reviewer_id": reviewer, "case_id": "case-a", "field": "implementation",
             "evidence_phase": "later_only", "candidate_relation": "missing",
             "source_refs": [], "post_turn_refs": ["turn-17"],
             "external_refs": [], "log_refs": ["entry:t"]}
            for reviewer in ("r1", "r2")
        ]
        result = compare_temporal_reviews(reviews)
        self.assertEqual(result["counts"]["extraction_error"], 1)
        self.assertEqual(result["counts"]["later_enrichment"], 1)
        self.assertEqual(result["counts"]["scorable_at_turn"], 1)

    def test_disagreement_is_not_forced_into_a_failure(self):
        reviews = [
            {"reviewer_id": "r1", "case_id": "case-a", "field": "acceptance",
             "evidence_phase": "at_turn", "candidate_relation": "missing",
             "source_refs": ["turn-16"], "post_turn_refs": [],
             "external_refs": [], "log_refs": ["entry:d1"]},
            {"reviewer_id": "r2", "case_id": "case-a", "field": "acceptance",
             "evidence_phase": "unknown", "candidate_relation": "unknown",
             "source_refs": [], "post_turn_refs": [],
             "external_refs": [], "log_refs": ["entry:d1"]},
        ]
        result = compare_temporal_reviews(reviews)
        self.assertEqual(result["counts"]["unresolved_review"], 1)
        self.assertEqual(result["counts"]["extraction_error"], 0)

    def test_duplicate_or_unreferenced_reviews_rejected(self):
        review = {"reviewer_id": "r1", "case_id": "case-a", "field": "scope",
                  "evidence_phase": "at_turn", "candidate_relation": "matched",
                  "source_refs": [], "post_turn_refs": [],
                  "external_refs": [], "log_refs": ["entry:d1"]}
        with self.assertRaises(ValueError):
            compare_temporal_reviews([review, review])

    def test_external_context_is_separate_from_later_information(self):
        reviews = [
            {"reviewer_id": reviewer, "case_id": "case-a", "field": "scope",
             "evidence_phase": "outside_dialogue_at_turn", "candidate_relation": "missing",
             "source_refs": [], "post_turn_refs": [], "external_refs": ["tool-5"],
             "log_refs": ["entry:d1"]}
            for reviewer in ("r1", "r2")
        ]
        result = compare_temporal_reviews(reviews)
        self.assertEqual(result["counts"]["context_gap"], 1)
        self.assertEqual(result["counts"]["later_enrichment"], 0)

    def test_later_only_requires_post_turn_evidence(self):
        reviews = [
            {"reviewer_id": reviewer, "case_id": "case-a", "field": "implementation",
             "evidence_phase": "later_only", "candidate_relation": "missing",
             "source_refs": [], "post_turn_refs": [], "external_refs": [],
             "log_refs": ["entry:t"]}
            for reviewer in ("r1", "r2")
        ]
        with self.assertRaises(ValueError):
            compare_temporal_reviews(reviews)


if __name__ == "__main__":
    unittest.main()
