import re
import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.quality import SCHEMA_VERSION, build_quality_report, format_quality_report


def _entry(heading, entry_id, body, related=None):
    yaml = [
        "```yaml",
        f"entry_id: {entry_id}",
        "user_initials: JNL",
        "agent_type: claude",
        "project_path: .",
    ]
    if related:
        yaml.append("related_entries:")
        yaml.extend(f"  - {ref}" for ref in related)
    yaml.append("```")
    return f"## {heading}\n\n" + "\n".join(yaml) + f"\n\n{body}\n"


class QualityReportTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-quality-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def write_day(self, cwd, *entries):
        sessions = cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-05-10.md").write_text(
            "# Session Log\n\n" + "\n".join(entries), encoding="utf-8"
        )

    def metric(self, report, metric_id):
        return next(m for m in report.metrics if m.id == metric_id)

    def test_empty_corpus_reports_not_applicable_not_perfect_coverage(self):
        cwd = self.make_project()
        (cwd / ".memory-seed" / "sessions").mkdir(parents=True)

        report = build_quality_report(cwd)

        # The load-bearing honesty rule: nothing to measure must never render as
        # 100% coverage.
        unlinked = self.metric(report, "unlinked_entry_rate")
        self.assertEqual(unlinked.status, "not_applicable")
        self.assertIsNone(unlinked.rate)
        self.assertIsNone(unlinked.numerator)
        coverage = self.metric(report, "draft_reason_coverage")
        self.assertEqual(coverage.status, "not_applicable")
        self.assertIsNone(coverage.rate)

    def test_fully_linked_corpus_measures_zero_unlinked(self):
        cwd = self.make_project()
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - A", "ms-a0000000", "### Decision\n\n- D: a.\n- R: because."),
            _entry(
                "2026-05-10 10:00 - B",
                "ms-b0000000",
                "### Decision\n\n- D: b.\n- R: because.",
                related=["ms-a0000000"],
            ),
        )

        unlinked = self.metric(build_quality_report(cwd), "unlinked_entry_rate")

        # B declares the edge; A earns an inbound backlink from it, so neither
        # is unlinked even though A's own YAML has no related_entries.
        self.assertEqual(unlinked.status, "measured")
        self.assertEqual((unlinked.numerator, unlinked.denominator), (0, 2))
        self.assertEqual(unlinked.breakdown, {})

    def test_mixed_corpus_counts_unlinked_by_age_band(self):
        cwd = self.make_project()
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - A", "ms-a0000000", "### Decision\n\n- D: a.\n- R: because."),
            _entry("2026-05-10 10:00 - B", "ms-b0000000", "### Decision\n\n- D: b.\n- R: because."),
        )

        unlinked = self.metric(build_quality_report(cwd), "unlinked_entry_rate")

        self.assertEqual((unlinked.numerator, unlinked.denominator), (2, 2))
        self.assertEqual(sum(unlinked.breakdown.values()), 2)  # every unlinked is banded

    def test_entries_without_decisions_are_excluded_not_failed(self):
        cwd = self.make_project()
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - A", "ms-a0000000", "### Decision\n\n- D: a.\n- R: because."),
            _entry("2026-05-10 10:00 - B", "ms-b0000000", "### Summary\n\n- Just a note."),
        )

        coverage = self.metric(build_quality_report(cwd), "draft_reason_coverage")

        # B makes no decision: it leaves the denominator rather than counting
        # against coverage.
        self.assertEqual(coverage.status, "measured")
        self.assertEqual((coverage.numerator, coverage.denominator), (1, 1))
        self.assertEqual(coverage.excluded, 1)

    def test_entry_with_decision_but_no_reason_is_counted_uncovered(self):
        cwd = self.make_project()
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - A", "ms-a0000000", "### Decision\n\n- D: a.\n- R: because."),
            # A decision with no R:. session append would refuse to write this,
            # but historical/hand-edited entries can contain it.
            _entry("2026-05-10 10:00 - B", "ms-b0000000", "### Decision\n\n- D: b with no reason."),
        )

        coverage = self.metric(build_quality_report(cwd), "draft_reason_coverage")

        # Guards the coupling to core's issue wording: if check_entry_format's
        # message changes, this fails instead of the metric quietly showing 2/2.
        self.assertEqual((coverage.numerator, coverage.denominator), (1, 2))

    def test_bg1_dependent_metrics_are_unavailable_not_not_applicable(self):
        cwd = self.make_project()
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - A", "ms-a0000000", "### Decision\n\n- D: a.\n- R: because."),
        )

        report = build_quality_report(cwd)

        # "the input does not exist yet" is a different claim from "we looked
        # and the population was empty" - the report must not conflate them.
        self.assertEqual(self.metric(report, "provenance_coverage").status, "unavailable")
        self.assertEqual(
            self.metric(report, "generated_claim_citation_coverage").status, "unavailable"
        )
        self.assertEqual(self.metric(report, "ranking_ab_regression_rate").status, "not_applicable")

    def test_report_is_deterministic_for_the_same_corpus(self):
        cwd = self.make_project()
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - A", "ms-a0000000", "### Decision\n\n- D: a.\n- R: because."),
            _entry("2026-05-10 10:00 - B", "ms-b0000000", "### Decision\n\n- D: b.\n- R: because."),
        )

        first = build_quality_report(cwd).to_dict()
        second = build_quality_report(cwd).to_dict()

        # Everything but the wall clock must reproduce byte-for-byte.
        first.pop("generated_at")
        second.pop("generated_at")
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], SCHEMA_VERSION)

    def test_report_performs_no_writes(self):
        cwd = self.make_project()
        self.write_day(
            cwd,
            _entry("2026-05-10 09:00 - A", "ms-a0000000", "### Decision\n\n- D: a.\n- R: because."),
        )
        session = cwd / ".memory-seed" / "sessions" / "2026-05-10.md"
        before = session.read_text(encoding="utf-8")
        before_tree = sorted(p.name for p in cwd.rglob("*"))

        format_quality_report(build_quality_report(cwd))

        self.assertEqual(before, session.read_text(encoding="utf-8"))
        self.assertEqual(before_tree, sorted(p.name for p in cwd.rglob("*")))

    def test_human_report_never_prints_a_rate_for_an_unmeasured_metric(self):
        cwd = self.make_project()
        (cwd / ".memory-seed" / "sessions").mkdir(parents=True)

        text = format_quality_report(build_quality_report(cwd))

        # No computed rate is rendered anywhere on an all-empty corpus. (The
        # literal "100%" in a note is explanatory prose saying we deliberately
        # do NOT report that, so match the rendered "(12.3%)" shape instead.)
        self.assertIsNone(re.search(r"\(\d+\.\d+%\)", text))
        self.assertIn("not_applicable", text)


if __name__ == "__main__":
    unittest.main()
