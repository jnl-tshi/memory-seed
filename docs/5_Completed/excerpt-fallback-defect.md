---
title: "Excerpt Fallback Defect"
date: "2026-08-06"
project: "memory-seed"
status: "FIXED 2026-08-06"
priority: "P1"
next_action: "None. Fixed at the cause: the reader now recognises the legacy singular decision form, so the fallback almost never fires."
related:
  - "experiments/memory-index-dryrun/answer_visible.py"
  - "docs/5_Completed/memory-index-dry-run-plan.md"
  - "experiments/band-calibration/FINDINGS.md"
---

# Nearly half the corpus is served as a 280-character teaser

> **Fixed 2026-08-06.** The payload-budget framing below was the wrong diagnosis. JNL's reading was
> that the real fault is having two ways of seeing a decision at all, and that is correct: the
> reader matched only `#### Dn`, so a singular `### Decision` entry produced no decision chunk and
> fell through to the entry branch. Teaching the reader that shape - and making the numbered form
> the only one authored going forward - fixes it at the cause, with no payload trade-off to make:
>
> | | before | after |
> |---|---|---|
> | real corpus served at 280 chars | 571/1259 (45%) | **77/1259 (6%)** |
> | content withheld | **51%** | **2%** |
> | answer-visible@8, seeded fixture | 7/23 | **22/23** |
>
> The three options below are kept as the record of a diagnosis that was one layer too shallow. The
> remaining 77 chunks are entries with no decision section at all, which correctly stay whole.

## The defect

`retrieval.py:2625` chooses how much of a chunk to serve:

```python
"excerpt": (
    _decision_body(chunk.text)      # whole block, cap 2500
    if chunk.granularity == "decision"
    else _excerpt(chunk.text)       # 280 characters, single line, "..."
),
```

The condition is the chunk's **actual** granularity, not the granularity that was requested. Asking
for `granularity="decision"` does not return only decision chunks: an entry with no `#### Dn` DRAFT
block has no decision to extract, so it comes back as an **entry** chunk - and entry chunks take the
280-character branch.

The result is that a search asking for whole decision blocks silently receives a one-line preview
for every entry that does not use the DRAFT decision format.

## Measured

| | chunks served at 280 | content withheld |
|---|---|---|
| dry-run fixture (12 chunks) | 8 (67%) | 79% |
| real corpus (1259 chunks) | **571 (45%)** | **51% - 987,701 characters** |

488 of the 571 affected chunks in the real corpus hold more than 1000 characters, so this is not an
edge case around short entries.

## How it surfaced

Not from the ranking work. It came from asking why the memory-index dry-run scored 96.8 while
retrieval could only surface 7 of 23 answers. Chasing that gap ruled out, in order: the ranking
configuration (both configurations tested, orderings differ), the corpus (all 23 answers are present
in the indexed session entries), the top-k window (serving the entire 12-chunk store changes
nothing), and `DECISION_TEXT_LIMIT` truncation (the target terms sit at characters 859-1180, well
inside the 2500 cap). What remained was the excerpt branch.

The dry-run's dependence on `index.md` is a consequence rather than a design choice: the answers ARE
in the session entries, but retrieval was serving 280 characters of each, so the agent had to read
the summary file.

## The fix is a payload-budget decision, not a one-line change

Serving entry chunks through `_decision_body` would raise a top-8 payload from roughly 2k characters
to as much as 20k - about 5k tokens - and the 280-character preview presumably exists to prevent
exactly that. Three shapes worth measuring:

1. **Serve at the decision cap regardless of granularity.** Simplest, largest payload.
2. **Budget across the result set.** Fill a total character budget from the top down, so one long
   entry cannot crowd out seven others; the tail degrades to previews rather than the head being
   truncated arbitrarily.
3. **Extract the relevant span.** Serve the window around the matched terms rather than the head of
   the chunk. Best information per token, most work, and it needs the match positions the scorer
   already computes.

Option 2 is the likely answer, because the current behaviour is not "previews are cheap" but
"whichever chunks happen to lack DRAFT formatting are invisible", which is arbitrary rather than
economical.

## Verification when it is fixed

`experiments/memory-index-dryrun/answer_visible.py` measures this directly: answer-visible is
currently 7/23 at k=8 on the seeded store with all 23 answers present in the indexed corpus. That
number is the before. Re-run it after, and re-check served payload size per search, which
`experiments/band-calibration/calibrate.py` already reports.

The band is inert and the dry-run cannot see ranking changes, so this metric is currently the
sharpest end-to-end instrument available for retrieval.
