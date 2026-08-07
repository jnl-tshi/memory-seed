"""Reading the corpus without its sidecars must be a deliberate, justified act.

Sidecars are append-only edits authored after an entry is written: link sidecars carry the typed
lifecycle edges (`replaces` / `evolves` / `related_entries`), topic sidecars carry topic
assignments. `extract_memory_chunks` returns none of them. A caller that skips the augmenters gets
chunks that look well-formed, in plausible numbers, with most of the lifecycle graph simply absent -
and nothing anywhere reports a problem.

That has now happened three times in this project:

  - `ranking_ab.run_ab` built its corpus raw, so the gate that exists to validate ranking signals
    computed the supersession signal's affected set from entry-YAML edges alone and A/B-tested
    against a fraction of the real edges while reporting a verdict as if it had covered them all.
  - A calibration harness built its lifecycle labels the same way and reported "the corpus has 4
    `replaces` edges". The link sidecars hold 20 `replaces:` blocks among 558 edge declarations.
  - The same harness called `rank_session_memory` bare, whose `supersession_damping` defaults False
    where `search_memory` sets it True, and reported a live defect that was its own configuration.

`retrieval.load_corpus` is the canonical read. This test does not forbid the raw extractor - some
callers legitimately want it - it forbids adding a raw call WITHOUT saying why, by pinning the count
per module. Change a count and the test fails until the allowlist below is updated with a reason,
which is the point: the omission stops being silent.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "memory_seed"

CALL_RE = re.compile(r"\bextract_memory_chunks\s*\(")
AUGMENTED_RE = re.compile(
    r"augment_chunks_with_link_sidecars|augment_chunks_with_topic_sidecars|load_corpus"
)
# How far back to look for the wrapping augmenter. The composed call is written across at most
# three lines anywhere in this package.
LOOKBEHIND = 3

# module -> (permitted raw calls, why)
ALLOWLIST: dict[str, tuple[int, str]] = {
    "semantic_cache.py": (
        4,
        "Cannot import retrieval - retrieval imports this module, so the augmenters are "
        "downstream and reaching for them would be a cycle. The four are: rank_session_memory's "
        "chunks=None fallback, build_related_entry_graph's chunks=None fallback, and two YAML "
        "write paths that edit entry metadata directly. The two fallbacks are traps for future "
        "callers rather than defects today (every production caller passes chunks=, and "
        "load_corpus is what supplies them). The write paths are RECORDED AS WORTH REVIEW, not "
        "confirmed correct: their idempotency check reads entry YAML only, so re-adding an edge "
        "that already exists in a link sidecar may not be detected as a duplicate.",
    ),
    "cli.py": (
        1,
        "Identity lookup: finds one chunk by entry_id to read its text. No graph, no ranking.",
    ),
    "retrieval.py": (
        1,
        "link-audit apply validates that scaffolded entry_ids exist. It consults "
        "entry_link_sidecars separately for what is already recorded, so augmenting here would be "
        "redundant, not corrective.",
    ),
    "esr.py": (
        2,
        "The topic-attribution reminder measures the DIFFERENCE between the two topic channels - "
        "decision-keyed `<slug>:dN` against entry-level - to count decisions where keying would add "
        "information. An augmenter merges those channels into one list, which is precisely the "
        "distinction being measured, so load_corpus would report zero gaps forever. The two calls "
        "are entry granularity (for entry-level topics) and decision granularity (for the decision "
        "list); the sidecar channel is read separately via entry_topic_sidecars.",
    ),
}


def _raw_call_sites(path: Path) -> list[tuple[int, str]]:
    """Calls to the raw extractor that are not lexically wrapped by an augmenter."""
    lines = path.read_text(encoding="utf-8").splitlines()
    found: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if not CALL_RE.search(line):
            continue
        stripped = line.lstrip()
        # The definition itself is not a call, and a comment mentioning the name is not a read.
        if stripped.startswith(("#", "*", "def ", "from ", "import ")):
            continue
        window = "\n".join(lines[max(0, index - LOOKBEHIND) : index + 1])
        if AUGMENTED_RE.search(window):
            continue
        found.append((index + 1, line.strip()))
    return found


def _modules() -> list[Path]:
    return sorted(p for p in PACKAGE.rglob("*.py") if "seed" not in p.relative_to(PACKAGE).parts)


def test_raw_corpus_reads_match_the_allowlist():
    actual: dict[str, list[tuple[int, str]]] = {}
    for module in _modules():
        sites = _raw_call_sites(module)
        if sites:
            actual[module.name] = sites

    unexpected = sorted(set(actual) - set(ALLOWLIST))
    assert not unexpected, (
        "module(s) read the corpus without sidecar augmentation and are not allowlisted: "
        f"{unexpected}. Use retrieval.load_corpus, or add an entry to ALLOWLIST saying why raw "
        "chunks are correct here."
    )

    for name, (permitted, _reason) in ALLOWLIST.items():
        sites = actual.get(name, [])
        assert len(sites) == permitted, (
            f"{name} has {len(sites)} raw corpus read(s), allowlist permits {permitted}. "
            f"Sites: {sites}. If the new one is correct, raise the count and extend the reason; "
            "if it is not, use retrieval.load_corpus."
        )


def test_every_allowlist_entry_states_a_reason():
    """An allowlist whose entries say 'legacy' would reproduce the problem it exists to prevent."""
    for name, (_count, reason) in ALLOWLIST.items():
        assert len(reason) > 40, f"{name} needs a real reason, not a label"
        assert not reason.lower().startswith(("legacy", "todo", "historical")), name


def test_the_canonical_reader_applies_both_augmentations():
    source = (PACKAGE / "retrieval.py").read_text(encoding="utf-8")
    body = source.split("def load_corpus(", 1)[1].split("\ndef ", 1)[0]
    assert "augment_chunks_with_link_sidecars" in body
    assert "augment_chunks_with_topic_sidecars" in body


def test_search_memory_reads_through_the_canonical_path():
    """The production reader must not drift from the loader every other caller is sent to."""
    source = (PACKAGE / "retrieval.py").read_text(encoding="utf-8")
    body = source.split("def search_memory(", 1)[1].split("\ndef ", 1)[0]
    assert "load_corpus(" in body, "search_memory should compose the corpus via load_corpus"


def test_ranking_gate_does_not_read_raw_chunks():
    """Regression pin for the defect that motivated this file.

    `run_ab` fed `signal.affected` a raw corpus, so supersession's affected set was built from
    entry-YAML edges only and the gate compared arms over a fraction of the entries the signal
    touches.
    """
    source = (PACKAGE / "ranking_ab.py").read_text(encoding="utf-8")
    assert not _raw_call_sites(PACKAGE / "ranking_ab.py")
    assert "load_corpus" in source


@pytest.mark.parametrize("name", sorted(ALLOWLIST))
def test_allowlisted_modules_still_exist(name):
    """A stale allowlist entry silently permits nothing and hides that the risk moved."""
    assert (PACKAGE / name).exists()
