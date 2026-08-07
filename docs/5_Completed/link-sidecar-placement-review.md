---
memory-system-version: 2.19
tags:
  - memory-seed
  - review
  - lifecycle-edges
  - link-sidecars
---

# Link Sidecar Placement Review — as-is vs. the origin-date proposal

> **Status: reviewed and closed 2026-08-07.** JNL proposed that link sidecars be filed under the
> originating decision's month folder and date filename, append-only across passes. The review found
> that is already the enforced design — no delta to close — but surfaced a live defect the placement
> rule and the block-identity rule create between them. All four recommended fixes were applied the
> same day (`105dffb`, `4961678`); session entry `mse_9aggjnyaqrmb545d`.
>
> Code citations below are as reviewed, i.e. **before** the fix; `retrieval.py` line numbers have
> since moved. Symbol names are stable.

## Verdict

The proposal is already the implemented design. It is not a change to make — it is the enforced
invariant, enforced at five independent points plus a test. The value of the review is elsewhere: two
conventions diverge *inside* that design, and one of them had already hard-broken the stub writer on
four dates.

## As-is, precisely

Layout is `.memory-seed/sessions/links/YYYY-MM/YYYY-MM-DD.md` — one file per **originating (source)
entry's session date**, not per authoring date.

| Layer | Where | What it does |
|---|---|---|
| Spec | `docs/3_Spec/lifecycle-edge-linking-sidecars.md` | "one dated file per day", blocks keyed to the **source** entry |
| Writer | `apply_link_gap_stubs` (`memory_seed/retrieval.py`) | refuses to scaffold: `entry_id X belongs to <date>, not <session_date>` |
| Validator | `check_session_links` (`memory_seed/core.py:2626`) | `link-sidecar-date-mismatch` at **error** severity → non-zero exit, CI gate |
| Test | `tests/test_links_check.py:731` | asserts the mismatch is raised |
| Fuse (route) | `_split_link_sidecar_records` (`memory_seed/core.py:4515`) | `target_date = link_date or timestamp[:10]` — merges route back to the origin-date path |
| Fuse (check) | `_plan_session_fuse` (`memory_seed/core.py:5285`) | refuses a merge whose `link_date` ≠ the parent entry's own date |

The append-only-across-passes half of the proposal is also already built, and was built for exactly
that reason. Block identity is `(entry_id, heading timestamp)` — amended 2026-07-23 because identity
by `entry_id` alone made the first block the only block forever, and by cycle 5 of that judgment
programme eight validated edges were unwritable. A second swarm pass appends a new block; it never
reopens the first.

**Live proof of the model already running.** `.memory-seed/sessions/links/2026-05/2026-05-26.md` is a
May file whose six blocks were all authored on 2026-07-25 by the haiku swarm. And
`links/2026-07/2026-07-12.md` shows both passes stacked in one file: seven blocks from the
2026-07-12 sweep, then twelve more appended by the 2026-07-25 campaign.

`links check` on the corpus at review time: **integrity OK, 159 files, zero errors** (warnings only —
unclassified stubs and decision-granularity nudges).

## Comparison

| | Proposal | As-is |
|---|---|---|
| File = originating decision's date | yes | yes (enforced, error-severity) |
| Month folder mirrors that date | yes | yes (`YYYY-MM/`) |
| Later pass appends to the same file | yes | yes (`(entry_id, timestamp)` identity, since 2026-07-23) |
| Append-only, never reopen | yes | yes |

No delta. The alternative reading — filing by the *target* (older) entry's date — would scatter one
entry's edges across many files and isn't a coherent design; the plain reading was taken.

## What the review found

### 1. Two heading conventions, and the stub writer rejected the one the swarm needs

Both are blessed somewhere, and they disagree about the `## <timestamp>` heading inside an
origin-date file:

- **Mechanical stubs** (`apply_link_gap_stubs`) stamp the **source entry's own** timestamp.
  `links/2026-08/2026-08-04.md` → `## 2026-08-04 00:21`.
- **The swarm** stamps the **authoring wall clock**. `links/2026-05/2026-05-26.md` →
  `## 2026-07-25 17:58`. The spec blessed this: headings are "cosmetic", a later append is "stamped
  with the wall clock".

The collision: a wall-clock heading inside an origin-date file makes the file non-chronological, and
`apply_link_gap_stubs` **refused to write to a non-chronological file** (`Existing link sidecar
blocks are not chronological`).

Not hypothetical. Four files were in that state — `2026-07-03`, `2026-07-05`, `2026-07-12`,
`2026-07-17` — and each still had unblocked entries (8, 7, 5, 14 respectively), so the guard was
reachable, not shadowed by the `pending`-empty early return. Verified by running the audit+apply
against a scratchpad copy of `.memory-seed`:

```
2026-07-12  gaps 19  RAISED: Existing link sidecar blocks are not chronological
2026-07-17  gaps 34  RAISED: Existing link sidecar blocks are not chronological
2026-08-04  gaps 17  OK added 5
```

Those four dates were **permanently closed to further mechanical link enrichment** until the block
order was repaired. The proposal's core promise — a subsequent swarm pass adding further links to the
same file — is exactly what was broken there.

**The wall-clock heading is not the defect; it is load-bearing.** Block identity is `(entry_id,
heading timestamp)`, and `link_swarm.md`'s guardrails state it plainly: *two blocks for one entry
need distinct timestamps.* If the heading were the source entry's own timestamp, pass 2's block for
entry X would key identically to pass 1's — reintroducing the exact bug the 2026-07-23 amendment
fixed, and killing multi-pass enrichment for good. Stubs dodge this only because
`apply_link_gap_stubs` skips any entry that already has a block; the swarm, which is the thing that
enriches repeatedly, would hit it every pass.

The defect was the stub writer's chronological **rejection**. The fix already existed elsewhere in
the codebase: `_write_chronological_link_sidecar_file` **sorts** on write rather than refusing, so a
`session merge-branch` fuse silently repairs order — but only for files it happens to touch, and the
four affected files had not been fused since.

### 2. `link_swarm.md` documented the wrong rule

Step 5 read: *"Write approved edges into the day's link sidecar
`.memory-seed/sessions/links/YYYY-MM/YYYY-MM-DD.md`"*. "The day's" reads as **today's**. A campaign
following it literally writes every edge into one authoring-date file and trips
`link-sidecar-date-mismatch` on every block. The same sentence then specified
`## <source entry timestamp>` for the heading — the identity collision above. The 2026-07-25 campaign
did the right thing on both counts, but that was judgment rather than instruction.

### 3. Latent: the fuse's fallback routes by heading date

`target_date = link_date or timestamp[:10]`. Every current sidecar carries `link_date`, so the
fallback never fires. If one ever lacked it, the wall-clock heading would route the block to the
*authoring* date's file — the mismatch the validator then rejects. Low risk, recorded not fixed.

## Fixes — all applied 2026-08-07

1. **`apply_link_gap_stubs` relaxed from reject-if-unsorted to sort-on-write**, matching
   `_write_chronological_link_sidecar_file`'s stable sort. Existing blocks keep their relative order
   within a minute; new blocks land after them; block content is never touched. Covered by
   `test_apply_sorts_a_wall_clock_stamped_sidecar_instead_of_refusing` and
   `test_apply_appends_to_a_frontmatter_only_sidecar_without_duplicating_it`.
2. **The four affected files re-sorted** as a pure permutation, verified by comparing the sorted line
   multiset before and after. Safe against the fuse: immutability is compared per `(entry_id, heading
   timestamp)` on record *text* (`core.py:5269`), and a re-sort changes neither. All four dates now
   accept a stub apply.
3. **Wall-clock headings recorded as deliberate in the spec**, alongside the `(entry_id, timestamp)`
   identity rule they exist to serve, with the standing instruction that a writer meeting a
   non-chronological sidecar must sort rather than refuse.
4. **`link_swarm.md` step 5 rewritten** (live and seed) to name the source entry's own session date,
   the `link-sidecar-date-mismatch` failure mode, and the authoring wall clock for the heading with
   its identity reason attached.
