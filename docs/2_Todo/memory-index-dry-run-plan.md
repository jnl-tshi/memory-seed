---
title: "Memory Index Dry-Run Plan"
date: "2026-08-05"
project: "memory-seed"
status: "RUN 3x 2026-08-05 - 71.0 -> 74.2 -> 96.8 after the retrieval and capture fixes; kill condition CLEAR"
priority: "P1"
next_action: "JNL decides whether to submit to Verging Labs v0.2 (early September). Independent replication of the 96.8 on a second seeded corpus would strengthen it first."
related:
  - "business/research/field-evidence-log.md"
  - "business/market/competitor-landscape.md"
  - "docs/2_Todo/attention-retrieval-signal-proposal.md"
---

# Memory Index Dry-Run Plan

Status: **designed, not started.** Five-question test: **Trust, Retrieval**. Purpose: know Memory
Seed's approximate Agentic Memory Index score *privately* before deciding whether to submit via
verginglabs.com/radar for v0.2 (early September 2026). Never enter a published benchmark blind.

## What is being approximated

Verging Labs' six probe categories, reconstructed from their methodology page and the author's
thread. Their mechanics: the agent is **given the tool's own docs and left to follow them** across
simulated multi-week working sessions, then quizzed; 200 stored-fact questions + 72 never-stored
trap questions; judge calibrated against human labels; verdicts include *Fabricated Citation*.
A Memory Seed run therefore measures the shipped instruction surface (AGENTS.md routing,
agent-rules, session_logging, MCP tools) end to end — not the store in isolation.

## Design (reuses the agent-capture machinery wholesale)

**Fixture:** one claude-L3 fixture (full stock install = the product as shipped). **Store
population happens the way the benchmark does it**: N seeding sessions (headless, cwd=fixture),
each given a work-diary brief ("this week the team decided/learned/changed X, Y, Z…") and left to
store per the shipped instructions. ~10 sessions across a simulated 5-week arc, fact list frozen
in an answer key the sessions never see verbatim (facts are embedded in prose briefs).

Fact classes mirror their taxonomy:

| Their category | Our probe | Answer-key shape |
|---|---|---|
| Direct recall | "What did we decide about X?" | fact stored in week w |
| Updated facts | fact stated week 1, reversed week 3 | current answer + the superseded one |
| Thread growth | fact accreted across 3 sessions | composite answer |
| Synthesis | question spanning 2+ entries | requires joining entries |
| Long-term retention | week-1 fact quizzed at end | fact + age |
| False memory check | 24+ never-stored plausible questions | correct answer = abstain |

**Quiz phase:** fresh headless sessions (no seeding context), one question per session batch,
answering only from the store. **Blind judging:** the two-stage judge harness (`judge.py` pattern —
stage 1 never sees the answer key; stage 2 maps onto it; prompts over stdin per the Windows lesson).
Verdicts copied from theirs: correct / not addressed / incorrect / outdated / fabricated.

**Pre-registered expectations** (stated now so the result can't be read opportunistically):
- *Updated facts* and *false memory* are expected strengths (E8 stale-head navigation was 6/6;
  0 fabricated rationale in 121 v2-matrix judgements; `memory_search` exposes `replaced_by`/
  `evolved_head` on every row).
- *Arbitrary-fact direct recall* is the expected weakness: the store is decision-shaped, and the
  validators refuse unstructured writes — facts that aren't decisions must survive as Summary
  prose or be declined by the seeding agent. If the score dies here, the finding is "adapter
  needed" (a fact-note convention), not "memory is bad" — but that distinction must be measured,
  not assumed.
- **Kill condition for submission:** if the blended dry-run score lands below the published #8
  (Zep, 75.1), do not submit v0.2; fix what the dry-run exposes first.

**Cost/scope:** ~10 seeding + ~25 quiz sessions ≈ $25 at observed per-session costs; one day
wall-clock with the batch runner. Explicitly NOT a replication of their 272-probe set — it is a
directional private estimate with honest error bars, per the pattern-over-threshold rule.

## Results (2026-08-05, first run)

| Category | n | correct | not_addr | incorrect | outdated | fabricated |
|---|---|---|---|---|---|---|
| direct_recall | 6 | 3 | 0 | 3 | 0 | 0 |
| updated_facts | 6 | 4 | 0 | 2 | 0 | 0 |
| thread_growth | 3 | 3 | 0 | 0 | 0 | 0 |
| synthesis | 4 | 3 | 0 | 1 | 0 | 0 |
| long_term_retention | 4 | 1 | 2 | 1 | 0 | 0 |
| false_memory | 8 | **8** | 0 | 0 | 0 | **0** |

**Blended 22/31 = 71.0 — below Zep (75.1). Kill condition TRIGGERED: do not submit.**

**The pre-registered expectations both held.** False-memory was perfect (8/8, zero fabrications —
the published index winner failed exactly here), updated-facts/thread/synthesis strong. The losses
are concentrated in arbitrary-fact recall and retention — the predicted weakness of a
decision-shaped store.

**Every miss is an over-abstention, not a wrong answer.** All nine failures are the agent saying
"not recorded". Provenance split (checked against the seeded workspace):

- **Capture loss (~5):** the kickoff session (S1: roster, cadence, CI budget, codename) recorded
  ZERO entries — E5's capture finding replayed on fact-dense, no-code-change sessions. The facts
  died at storage, so recall never had a chance. The shipped instruction surface routes *decisions*
  to the store but gives diary-style *facts* no home; `index.md` is that home per
  `memory_consolidation.md`, and no seeding session used it.
- **Retrieval under-confidence (~4):** Sofia (stored, S9), the 40-minute original budget
  (recoverable from the superseding entry's own text), and the Granite codename (present in
  RELEASE.md) were all on disk and denied anyway.

**Reading:** the honesty posture that produces zero fabrications is the same posture that
over-abstains on weakly-stored facts. For *acting* agents that trade is right (a miss stalls
loudly; an invention proceeds confidently — the asymmetry a top thread comment argued). For this
*blended score* it loses ~9 points. The fix is not loosening honesty; it is (1) routing durable
non-decision facts to `index.md` at capture time, and (2) letting quiz-style retrieval trust
project files and superseding-entry context it already has.

Caveats: n=31, one run, own judge chain (Codex, calibrated only by rubric), timeline-compressed
retention. Directional, per the pattern-over-threshold rule.

> **Attribution correction, 2026-08-06.** A free pre-check before a planned run 4 found that this
> score is carried by `index.md`, not by ranked retrieval. The expected answers - the maintainer
> roster, benchmark ownership, the 1.2us baseline - live in `.memory-seed/index.md`;
> `memory_search` indexes only `.memory-seed/sessions/**`; and the fixture's `AGENTS.md` instructs
> the agent to read `index.md` as step 2 of orientation. That is consistent with what this document
> already records - decision-level retrieval was worth +3.2 of the +25.8 - and it explains the rest.
>
> The blended figure is a fair measure of the product, because agents really do read that file. It
> is **not** evidence about the retrieval layer, and it should not be quoted as a recall result
> beside index entrants whose scores are recall measurements.
>
> Run 4 was therefore **not run**: after the 2026-08-05 ranking rebuild it would have returned
> roughly 96.8 whatever the ranker did, and that null invited being read as "the rebuild did no
> harm". The measurement that would test retrieval end to end is a quiz with `index.md` withheld,
> so `memory_search` is the only route to an answer - a new measurement, not a comparison with
> run 3. See `experiments/memory-index-dryrun/answer_visible.py`.

## Run 5 (2026-08-06) - retrieval ENFORCED as the only route

Run 4's caveat was that agents could still read the session file directly, and 2 of 8 batches
demonstrably did. Two further runs closed it:

**5a, instruction only.** The preamble told agents to use `memory_search` and `memory_get_chunk`
exclusively and not to open anything under `.memory-seed/`. **It did not hold.** All 8 batches used
file tools anyway - 16 `Grep` and 13 `Read` calls against 19 `memory_search`. Roughly half the
lookups bypassed retrieval in direct contravention of an explicit instruction. That is a finding
about instructions, not about retrieval, and it is why compliance is now recorded per batch in
`tools_used` rather than assumed.

**5b, enforced.** `--disallowedTools Read Grep Glob LS Bash`, verified to survive
`--dangerously-skip-permissions` on a single-batch probe first. Result: **zero file-access calls
across all 8 batches**; the MCP tools were the only route.

| Category | n | run 3 | run 4 (readable) | **run 5b (enforced)** |
|---|---|---|---|---|
| direct_recall | 6 | 5 | 6 | **5** |
| updated_facts | 6 | 6 | 6 | **6** |
| thread_growth | 3 | 3 | 3 | **3** |
| synthesis | 4 | 4 | 4 | **4** |
| long_term_retention | 4 | 4 | 4 | **4** |
| false_memory | 8 | 8 | 8 | **8** |
| **blended** | | 96.8 | 100.0 | **96.8** |
| fabrications | | 0 | 0 | **0** |

**This is the first properly isolated retrieval measurement.** No index.md facts, no file reads,
enforced rather than requested. 96.8 with `memory_search` and `memory_get_chunk` as the only way in,
and the fabrication column still zero.

The single miss is Q1, and it is a fixture ambiguity rather than a retrieval failure: the agent
answered Dana, Priya and Marcus **plus Sofia**, while the key predates Sofia. The store says she
"joined 2026-08-05, specifically to own Windows CI", which does not settle whether she is a
maintainer. Retrieval surfaced the later update and was marked wrong against the earlier key.

**Caveats.** Own judge chain, n=31, one run per arm, timeline-compressed. The enforced arm also
denies reading committed project files, which no question here needed but a future fixture might.

## Run 4 (2026-08-06) - retrieval-only arm, index.md's Active State blanked

Same seeded store, same 31 questions, no re-seeding. The one change: each quiz copy had the
`## Active State` section of `.memory-seed/index.md` blanked, so the durable facts existed only in
the session entries. The file itself was kept, because `AGENTS.md` treats a missing index.md as
"seeded but not bootstrapped" and would have sent the agent to rebuild it instead of answering.
Every seeded answer lives in that one section; nothing outside it leaks a fact, checked term by term.

| Category | n | run 3 | **run 4 (no index facts)** |
|---|---|---|---|
| direct_recall | 6 | 5 | **6** |
| updated_facts | 6 | 6 | **6** |
| thread_growth | 3 | 3 | **3** |
| synthesis | 4 | 4 | **4** |
| long_term_retention | 4 | 4 | **4** |
| false_memory | 8 | 8 | **8** |
| **blended** | | **96.8** | **100.0** |
| fabrications | | 0 | **0** |

**What this establishes.** Every one of the 31 answers is recoverable from the session entries
alone - previously unproven, and the reason run 3's dependence on `index.md` looked like a design
choice rather than a symptom. Abstention holds under the harder condition: 8/8 on the false-memory
traps with the summary stripped, zero fabrications.

**What it does NOT establish, and this is the important caveat.** It does not isolate retrieval. The
quiz preamble permits reading "files under `.memory-seed/`", the whole store is a single 10-entry
file, and 2 of the 8 answer batches explicitly cite that file path as their source. Agents do not
narrate tool use, so the artifacts cannot tell us how the other 6 answered. **The 100.0 is evidence
that the store contains the answers and agents can reach them - not that ranked retrieval surfaced
them.**

Isolating retrieval needs a harness change rather than a fixture change: deny filesystem reads of
`.memory-seed/sessions/**` so the MCP tools are the only route. Until then, the sharpest retrieval
instrument remains `experiments/memory-index-dryrun/answer_visible.py`, which measures the search
path directly and went 7/23 to 22/23 on the same store when the excerpt-fallback defect was fixed.

## Run 3 (2026-08-05) - after the retrieval and capture fixes

| Category | n | run 1 | run 2 | **run 3** |
|---|---|---|---|---|
| direct_recall | 6 | 3 | 3 | **5** |
| updated_facts | 6 | 4 | 5 | **6** |
| thread_growth | 3 | 3 | 3 | **3** |
| synthesis | 4 | 3 | 3 | **4** |
| long_term_retention | 4 | 1 | 1 | **4** |
| false_memory | 8 | 8 | 8 | **8** |
| **blended** | | **71.0** | **74.2** | **96.8** |
| fabrications | | 0 | 0 | **0** |

**Kill condition CLEAR.** For context only, against the published v0.1 index: 96.8 sits between
Mitosis Cortex (96.9) and the Karpathy wiki (98.5) - while holding the zero-fabrication column the
wiki failed. Not a like-for-like comparison (own judge chain, 31 probes vs their 272), so it is an
estimate of the band, not a rank.

**What each fix bought:**

- **Run 2, decision-level retrieval** (+3.2): answer-visible@1 went 2/8 -> 5/8, but the blended
  score moved only one question, because 4 of 8 remaining misses were facts never stored.
  Retrieval work was necessary and provably not sufficient.
- **Run 3, capture routing + trust-the-band** (+22.6): seeding sessions went 7/10 -> **10/10
  recording**, and `index.md` gained the roster and perf baseline it had silently dropped.
  **long_term_retention 1/4 -> 4/4** is the signature of the capture fix; updated_facts and
  synthesis completing is the signature of agents now trusting a strong-band result instead of
  denying facts in their own payload.

**The single remaining miss is a key ambiguity, not a defect.** Q1 named Dana, Priya and Marcus
correctly and added Sofia, who did join the project but as Windows CI owner rather than a
maintainer. A stricter key or a clearer brief resolves it; the retrieval and capture paths both
worked.

**Caveats that still stand:** one seeded corpus, 31 probes, own judge chain (Codex, rubric-
calibrated only), timeline-compressed retention, and the fixes were authored by the same agent that
designed the probes - the standing experimenter-equals-subject limitation. A second independent
corpus is the cheapest strengthening move before submission.

## Scale addendum (2026-08-05): what the 7-entry store could not show

Re-measured on the live corpus — **836 entries / 1,241 decision chunks** — via
`experiments/decision-retrieval-scale/measure.py`.

**Token cost, measured not estimated** (8 results, mean served characters):

| granularity | mean served | ~tokens |
|---|---|---|
| entry | 2,239 chars | ~560 |
| decision | 7,203 chars (median 7,612, max 10,649) | ~1,800 |

Decision granularity costs **~3.2x** entry granularity per search. The earlier estimate of ~2,250
tokens was low but the right order; 1,800 mean / 2,660 max is an acceptable price for serving whole
DRAFT blocks, and it is a real budget line for a busy session.

**The relevance band does not work at scale — a defect, found here.** Bands came out 88% `strong`
at *both* granularities, and `no_match_above_threshold` fired for **0 of 12** probe queries. Pure
nonsense ("recipe for sourdough starter hydration", "premier league transfer window rules")
returned eight results banded `strong`. Neither discriminator separates real from nonsense:

| | real queries | nonsense queries |
|---|---|---|
| top score | 17.9 – 53.5 | 8.8 – 19.3 (**overlapping**) |
| top ÷ median | 1.11 – 2.12 | 1.00 – 1.41 (**overlapping**) |

Semantic ranking on or off makes no difference to the verdict. The constants were fitted to a
7-entry store where everything banded `strong` and the answer was present anyway — the saturation
was invisible there, and the 96.8 dry-run score does not validate the band for the same reason.

**Consequence, corrected the same day.** The shipped `history_retrieval` guidance said a `strong`
band should be answered from and that `no_match_above_threshold` alone licenses "not recorded".
Against a signal that never fires and bands noise as strong, that instruction told agents to answer
confidently from irrelevant content and never abstain. It has been replaced with an explicit
uncalibrated warning, and `search_memory` now returns `relevance_calibrated: False` so no consumer
can read the band as evidence. Recalibration needs a wider probe set than twelve queries and is not
attempted here — the distribution above is the evidence a future attempt should start from.

**Lifecycle top-1 stability** was measured over only 4 derivable supersession lineages (entry 3/4
head@1, decision 2/4) — too few to distinguish the granularities, and reported only so the number
is not silently omitted.

## Contamination guard

Dry-run materials stay out of the published store paths (`experiments/memory-index-dryrun/`,
gitignored like the capture runs). Nothing from the answer key enters `.memory-seed/` in this
repo; the fixture's store is disposable.

## Out of scope

- The 5,000-page scale test (their separate scale probe) — revisit only if submission proceeds.
- Cost-per-answer accounting — theirs is subscription-vs-API sensitive; note qualitatively.
- Any contact with Verging Labs before the dry-run result is read.
