"""Memory-quality metrics v0 - a deterministic, read-only report over the corpus.

The measurable subset of Constitution section 8 ("Memory quality"), which is
still a **[candidate]** clause: this report exists to produce the evidence that
would let it graduate, not to assume it already has.

Everything here is a *measurement*. Per the v0 proposal's non-goals there is no
composite score, no target threshold, no telemetry, and no metric may feed
ranking, filtering, automation, or agent instructions. The report is a
rebuildable projection over authoritative Markdown (Invariant #6): it stores
nothing, and re-running it against the same corpus revision reproduces the same
values.

The honesty rules are load-bearing, not decoration:

* every metric declares its population, numerator, denominator, and exclusions;
* a metric with **no eligible population reports ``not_applicable``** - never
  100% coverage, which would read as perfect when it means "nothing to measure";
* a metric whose input is absent reports ``unavailable`` - distinct from "we
  measured it and it was empty";
* ineligible records stay visible in ``excluded`` rather than being silently
  dropped out of the denominator.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

SCHEMA_VERSION = 1

MetricStatus = Literal["measured", "not_applicable", "unavailable"]

# Substring of core's "a decision (D:) has no reason (R:) - R is mandatory"
# issue. Coupled to that wording on purpose rather than reimplementing the
# structural rule - `check_entry_format` is the one canonical parser. If the
# message changes, test_entry_with_decision_but_no_reason_is_counted_uncovered
# fails loudly; without that test this metric would silently report 100%.
_MISSING_REASON_MARKER = "no reason (R:)"


@dataclass(frozen=True)
class Metric:
    """One measurement. ``numerator``/``denominator`` are None unless
    ``status == "measured"`` - a rate is meaningless without a population."""

    id: str
    status: MetricStatus
    population: int
    excluded: int
    notes: str
    numerator: int | None = None
    denominator: int | None = None
    breakdown: dict[str, int] = field(default_factory=dict)

    @property
    def rate(self) -> float | None:
        if self.status != "measured" or not self.denominator:
            return None
        return (self.numerator or 0) / self.denominator

    def to_dict(self) -> dict:
        payload: dict = {
            "id": self.id,
            "status": self.status,
            "population": self.population,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "excluded": self.excluded,
            "notes": self.notes,
        }
        if self.breakdown:
            payload["breakdown"] = dict(sorted(self.breakdown.items()))
        return payload


@dataclass(frozen=True)
class QualityReport:
    schema_version: int
    corpus_revision: str | None
    generated_at: str
    metrics: tuple[Metric, ...]

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "corpus_revision": self.corpus_revision,
            "generated_at": self.generated_at,
            "metrics": [metric.to_dict() for metric in self.metrics],
        }


def _corpus_revision(cwd: Path) -> str | None:
    """The git commit the corpus was measured at, so a baseline is reproducible.

    None outside a git repo - the report still runs; it just cannot pin itself.
    """
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _age_band(age_days: int) -> str:
    if age_days <= 30:
        return "0-30d"
    if age_days <= 90:
        return "31-90d"
    return "90d+"


def _metric_unlinked_entries(chunks, graph, today) -> Metric:
    """Metric 1 - unlinked entry rate.

    An investigation queue, not a defect count: a standalone entry that genuinely
    relates to nothing is legitimately unlinked. Reported by age band so legacy
    entries stay visible instead of being normalised away.
    """
    if not chunks:
        return Metric(
            id="unlinked_entry_rate",
            status="not_applicable",
            population=0,
            excluded=0,
            notes="no parseable session entries with an entry_id",
        )

    unlinked = 0
    breakdown: dict[str, int] = {}
    for chunk in chunks:
        node = graph.get(chunk.entry_id)
        has_edge = bool(
            node
            and (
                node.outbound
                or node.inbound
                or node.replaces
                or node.replaced_by
                or node.evolves
                or node.evolved_by
            )
        )
        if not has_edge:
            unlinked += 1
            band = _age_band((today - chunk.session_date).days)
            breakdown[band] = breakdown.get(band, 0) + 1

    return Metric(
        id="unlinked_entry_rate",
        status="measured",
        population=len(chunks),
        numerator=unlinked,
        denominator=len(chunks),
        excluded=0,
        breakdown=breakdown,
        notes=(
            "entries with no inbound/outbound related_entries, replaces, or evolves edge "
            "after link-sidecar folding; an investigation queue, not proof an entry is bad. "
            "breakdown counts the unlinked by age band."
        ),
    )


def _metric_draft_reason_coverage(entry_texts, format_issues) -> Metric:
    """Metric 2 - DRAFT reason coverage.

    Population is entries that actually make a decision; entries that record no
    decision (and legacy entries predating DRAFT) are *excluded*, not counted as
    failures. Measures structure only - it never judges whether a reason is good.
    """
    decision_entries = {
        entry_id for entry_id, text in entry_texts.items() if _declares_a_decision(text)
    }
    excluded = len(entry_texts) - len(decision_entries)
    if not decision_entries:
        return Metric(
            id="draft_reason_coverage",
            status="not_applicable",
            population=0,
            excluded=excluded,
            notes=(
                "no entry uses a '### Decision'/'### Decisions' DRAFT shape, so there is "
                "nothing to measure; reported as not_applicable rather than 100% coverage"
            ),
        )

    missing = {
        entry_id
        for entry_id, issue in format_issues
        if entry_id in decision_entries and _MISSING_REASON_MARKER in issue
    }
    covered = len(decision_entries) - len(missing)
    return Metric(
        id="draft_reason_coverage",
        status="measured",
        population=len(decision_entries),
        numerator=covered,
        denominator=len(decision_entries),
        excluded=excluded,
        notes=(
            "decision records whose every D: has a non-empty R:. structural only - it does "
            "not judge whether a reason is persuasive. excluded: entries that record no "
            "decision, including legacy entries predating DRAFT."
        ),
    )


def _declares_a_decision(text: str) -> bool:
    return "### Decision" in text


def build_quality_report(cwd: str | Path = ".") -> QualityReport:
    """Measure the corpus. Read-only: performs no writes and needs no network."""
    from .core import check_entry_format
    from .retrieval import augment_chunks_with_link_sidecars
    from .semantic_cache import build_related_entry_graph, extract_memory_chunks
    from .text_files import read_text_file

    root = Path(cwd).resolve()
    chunks = [
        chunk
        for chunk in augment_chunks_with_link_sidecars(
            extract_memory_chunks(root, granularity="entry"), cwd=root
        )
        if chunk.entry_id
    ]
    graph = build_related_entry_graph(root, chunks=chunks)

    entry_texts = {chunk.entry_id: chunk.text for chunk in chunks}
    format_issues: list[tuple[str, str]] = []
    for path in sorted({root / chunk.source_path for chunk in chunks}):
        try:
            format_issues.extend(check_entry_format(read_text_file(path)))
        except OSError:
            continue

    today = datetime.now(timezone.utc).date()
    metrics = [
        _metric_unlinked_entries(chunks, graph, today),
        _metric_draft_reason_coverage(entry_texts, format_issues),
        # Metrics 3 and 4 depend on the provenance/authority taxonomy (BG1),
        # which is not built. They are `unavailable` - the input does not exist
        # yet - rather than `not_applicable`, which would claim we looked and
        # found an empty population.
        Metric(
            id="generated_claim_citation_coverage",
            status="unavailable",
            population=0,
            excluded=0,
            notes=(
                "requires artefacts conforming to the derived-artifact provenance contract; "
                "the contract exists but no artefact in this corpus declares material claims "
                "under it yet"
            ),
        ),
        Metric(
            id="provenance_coverage",
            status="unavailable",
            population=0,
            excluded=0,
            notes=(
                "requires the provenance/authority taxonomy (BG1), which is not implemented; "
                "provenance_class/authority_class are not yet recorded on non-authored records"
            ),
        ),
        Metric(
            id="ranking_ab_regression_rate",
            status="not_applicable",
            population=0,
            excluded=0,
            notes=(
                "population is the named query cases of a completed `memory-seed ranking-ab` "
                "run; none supplied to this report. run ranking-ab per signal - this report "
                "never reimplements its scoring"
            ),
        ),
    ]

    return QualityReport(
        schema_version=SCHEMA_VERSION,
        corpus_revision=_corpus_revision(root),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        metrics=tuple(metrics),
    )


def format_quality_report(report: QualityReport) -> str:
    """The human surface. Explains populations and exclusions rather than
    presenting bare percentages."""
    lines = [
        f"Memory quality report (schema v{report.schema_version})",
        f"  corpus revision: {report.corpus_revision or '(not a git repo)'}",
        "",
    ]
    for metric in report.metrics:
        lines.append(f"{metric.id}: {metric.status}")
        if metric.status == "measured":
            rate = metric.rate
            lines.append(
                f"  {metric.numerator}/{metric.denominator}"
                + (f"  ({rate:.1%})" if rate is not None else "")
                + f"   population={metric.population} excluded={metric.excluded}"
            )
            for key, value in sorted(metric.breakdown.items()):
                lines.append(f"    {key}: {value}")
        else:
            lines.append(f"  population={metric.population} excluded={metric.excluded}")
        lines.append(f"  {metric.notes}")
        lines.append("")
    lines.append("No metric here feeds ranking, filtering, or automation. Measurement only.")
    return "\n".join(lines)
