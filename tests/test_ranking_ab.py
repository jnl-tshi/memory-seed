from __future__ import annotations

import contextlib
import io
import json
import unittest
from datetime import date
from unittest import mock

from memory_seed.cli import main
from memory_seed.ranking_ab import (
    ABResult,
    QueryABResult,
    RankChange,
    ab_result_to_dict,
    run_ab,
)
from memory_seed.semantic_cache import MemoryChunk


def _chunk(
    entry_id: str,
    title: str,
    text: str,
    *,
    day: int,
    replaces: tuple[str, ...] = (),
) -> MemoryChunk:
    session_date = date(2026, 7, day)
    return MemoryChunk(
        chunk_id=entry_id,
        source_path=f".memory-seed/sessions/2026-07/2026-07-{day:02d}.md",
        source_file=f"2026-07-{day:02d}.md",
        session_date=session_date,
        entry_datetime=None,
        heading_path=(title,),
        heading_level=2,
        title=title,
        text=text,
        tags=(),
        contexts=(),
        lexical_terms=(),
        start_line=1,
        end_line=4,
        entry_id=entry_id,
        replaces=replaces,
        topics=("ranking",),
        granularity="entry",
    )


class RankingABTests(unittest.TestCase):
    def _independent_lineage_corpus(self):
        lineage_a_old = _chunk(
            "ms-a0a0a0a0",
            "2026-06-15 02:15 - Updated 3.0 plan decisions",
            "Lineage A retired plan decisions.",
            day=1,
        )
        lineage_a_new = _chunk(
            "ms-a1a1a1a1",
            "Retirement record: lineage A plan decisions",
            "Lineage A current plan decisions.",
            day=2,
            replaces=("ms-a0a0a0a0",),
        )
        lineage_b_old = _chunk(
            "ms-b0b0b0b0",
            "2026-07-15 17:46 - Sense-check roadmap plan decisions",
            "Lineage B also shares plan decisions wording.",
            day=3,
        )
        lineage_b_new = _chunk(
            "ms-b1b1b1b1",
            "Constitution-harden lineage B plan decisions",
            "Lineage B current plan decisions.",
            day=4,
            replaces=("ms-b0b0b0b0",),
        )
        distractors = [
            _chunk(
                f"ms-d15a00{i:02x}",
                f"Distractor plan decisions {i}",
                "Plan decisions distractor text.",
                day=5 + i,
            )
            for i in range(8)
        ]
        return [lineage_a_old, lineage_a_new, lineage_b_old, lineage_b_new, *distractors]

    def test_supersession_signal_demotes_retired_entry_below_replacement(self):
        retired = _chunk(
            "mse_old",
            "Alpha ranking policy",
            "Alpha ranking policy keeps the old ordering.",
            day=1,
        )
        replacement = _chunk(
            "mse_new",
            "Revise alpha ranking policy",
            "Alpha ranking policy now prefers the live decision.",
            day=2,
            replaces=("mse_old",),
        )
        unrelated = _chunk("mse_other", "Other work", "Unrelated maintenance.", day=3)

        result = run_ab(
            "supersession_damping",
            corpus=[retired, replacement, unrelated],
            today=date(2026, 7, 3),
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.affected_ids, ("mse_old",))
        self.assertEqual(len(result.queries), 2)
        query = result.queries[0]
        self.assertTrue(query.winner_beats_loser)
        self.assertLess(query.winner_rank_on, query.loser_rank_on)
        self.assertEqual(query.changes[0].entry_id, "mse_old")
        self.assertLess(query.changes[0].score_on, query.changes[0].score_off)
        control = result.queries[1]
        self.assertFalse(control.has_affected_hit)
        self.assertTrue(control.identical)

    def test_replacing_successor_boost_signal_lifts_terminal_replacement_into_window(self):
        retired = _chunk(
            "mse_old",
            "Alpha ranking policy",
            "Alpha ranking policy keeps the old ordering.",
            day=1,
        )
        middle = _chunk(
            "mse_mid",
            "Revise alpha ranking policy",
            "Alpha ranking policy was revised once.",
            day=2,
            replaces=("mse_old",),
        )
        terminal = _chunk(
            "mse_new",
            "Final alpha plan",
            "Alpha policy final plan.",
            day=3,
            replaces=("mse_mid",),
        )
        distractors = [
            _chunk(
                f"mse_other{i}",
                f"Alpha distractor {i}",
                f"Alpha ranking policy distractor {i}.",
                day=4 + i,
            )
            for i in range(8)
        ]

        result = run_ab(
            "replacing_successor_boost",
            corpus=[retired, middle, terminal, *distractors],
            today=date(2026, 7, 15),
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.affected_ids, ("mse_new",))
        directional = result.queries[0]
        self.assertTrue(directional.winner_beats_loser)
        self.assertTrue(directional.winner_within_max_rank)
        control = result.queries[-1]
        self.assertFalse(control.has_affected_hit)
        self.assertTrue(control.identical)

    def test_replacing_successor_boost_gate_rejects_unexpected_terminal_head_changes(self):
        corpus = self._independent_lineage_corpus()

        result = run_ab(
            "replacing_successor_boost",
            corpus=corpus,
            today=date(2026, 7, 15),
        )

        by_winner = {query.winner_id: query for query in result.queries if query.winner_id}
        a_query = by_winner["ms-a1a1a1a1"]
        b_query = by_winner["ms-b1b1b1b1"]
        self.assertEqual(a_query.query, "Updated 3.0 plan decisions")
        self.assertEqual(b_query.query, "Sense-check roadmap plan decisions")
        self.assertEqual(a_query.unexpected_changed_ids, ())
        self.assertEqual(b_query.unexpected_changed_ids, ())
        self.assertTrue(
            any(
                change.entry_id == "ms-b1b1b1b1"
                and change.score_on == change.score_off
                and change.rank_on > change.rank_off
                for change in a_query.changes
            )
        )
        self.assertTrue(a_query.directional_pass)
        self.assertTrue(b_query.directional_pass)

    def test_no_query_run_fails_closed(self):
        corpus = [_chunk("mse_one", "One", "One body", day=1)]

        result = run_ab("recency", corpus=corpus, today=date(2026, 7, 2))

        self.assertEqual(result.queries, ())
        self.assertFalse(result.passed)

    def test_missing_directional_winner_fails(self):
        query = QueryABResult(
            query="alpha",
            label="missing replacement",
            identical=False,
            has_affected_hit=True,
            changes=(),
            winner_id="mse_missing",
            loser_id="mse_old",
            winner_rank_on=None,
            loser_rank_on=1,
        )
        result = ABResult(
            signal="supersession_damping",
            corpus_size=1,
            affected_ids=("mse_old",),
            queries=(query,),
        )

        self.assertFalse(query.winner_beats_loser)
        self.assertFalse(result.directional_queries_pass)
        self.assertFalse(result.passed)

    def test_directional_query_fails_when_winner_stays_outside_required_window(self):
        query = QueryABResult(
            query="alpha",
            label="outside window",
            identical=False,
            has_affected_hit=True,
            changes=(),
            winner_id="mse_new",
            loser_id="mse_old",
            winner_rank_on=9,
            loser_rank_on=10,
            winner_max_rank_on=8,
        )
        result = ABResult(
            signal="replacing_successor_boost",
            corpus_size=12,
            affected_ids=("mse_new",),
            queries=(query,),
            requires_no_hit_control=False,
        )

        self.assertFalse(query.winner_within_max_rank)
        self.assertFalse(query.directional_pass)
        self.assertFalse(result.directional_queries_pass)
        self.assertFalse(result.passed)

    def test_directional_query_fails_on_unexpected_changed_terminal_head(self):
        query = QueryABResult(
            query="alpha",
            label="unexpected head",
            identical=False,
            has_affected_hit=True,
            changes=(),
            winner_id="mse_new",
            loser_id="mse_old",
            winner_rank_on=1,
            loser_rank_on=10,
            winner_max_rank_on=8,
            allowed_changed_ids=("mse_new",),
            unexpected_changed_ids=("mse_other",),
        )
        result = ABResult(
            signal="replacing_successor_boost",
            corpus_size=12,
            affected_ids=("mse_new", "mse_other"),
            queries=(query,),
            requires_no_hit_control=False,
        )

        self.assertFalse(query.directional_pass)
        self.assertFalse(result.directional_queries_pass)
        self.assertFalse(result.passed)

    def test_json_payload_includes_computed_verdicts(self):
        change = RankChange("mse_old", "Old", 1, 2, 1.0, 0.25)
        query = QueryABResult(
            query="alpha",
            label="alpha",
            identical=False,
            has_affected_hit=True,
            changes=(change,),
        )
        control = QueryABResult(
            query="ordinary",
            label="ordinary",
            identical=True,
            has_affected_hit=False,
            changes=(),
        )
        result = ABResult(
            signal="supersession_damping",
            corpus_size=2,
            affected_ids=("mse_old",),
            queries=(query, control),
            requires_no_hit_control=True,
        )

        payload = ab_result_to_dict(result)

        self.assertTrue(payload["passed"])
        self.assertTrue(payload["directional_queries_pass"])
        self.assertIsNone(payload["queries"][0]["winner_beats_loser"])
        self.assertIsNone(payload["queries"][0]["winner_within_max_rank"])


class RankingABCliTests(unittest.TestCase):
    def test_json_command_dispatches_and_uses_gate_exit_code(self):
        result = ABResult(
            signal="recency",
            corpus_size=0,
            affected_ids=(),
            queries=(),
        )
        stdout = io.StringIO()
        with mock.patch("memory_seed.ranking_ab.run_ab", return_value=result), contextlib.redirect_stdout(
            stdout
        ):
            code = main(["ranking-ab", "--signal", "recency", "--json"])

        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["signal"], "recency")
        self.assertFalse(payload["passed"])

    def test_unknown_signal_is_a_usage_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["ranking-ab", "--signal", "not-a-signal"])

        self.assertEqual(code, 2)
        self.assertIn("unknown ranking signal", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
