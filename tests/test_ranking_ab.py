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
    supersedes: tuple[str, ...] = (),
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
        supersedes=supersedes,
        topics=("ranking",),
        granularity="entry",
    )


class RankingABTests(unittest.TestCase):
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
            supersedes=("mse_old",),
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
