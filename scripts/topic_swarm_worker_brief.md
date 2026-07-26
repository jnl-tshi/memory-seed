# Topic judgment worker brief (v2 — the one permitted re-prompt)

Handed verbatim to each worker in the `topic_swarm` pilot fan-out. One worker, one
judgment unit. The brief is versioned in the repo because the skill grants **exactly
one re-prompt**, and a re-prompt whose text lives only in a dead agent's scratchpad
is not auditable.

## Revision history — what changed after run 1, and why

Run 1 (seed 20260726, 20 entries, 45 units, one haiku worker each) scored **Leg A
macro-recall 0.583**, diagnostic precision 0.521 — inside the 0.55–0.70 re-prompt
band. Measured from run 1's own verdict files:

| Symptom | Measurement |
|---|---|
| Misses are **area** slugs, not activities | 12 of 19 authored-slug misses were area slugs; `memory-seed` (5) and `graph` (4) alone are 47% of all recall loss |
| The **two-axis shape was not held** | only 24 of 45 units emitted one area + one activity; **10 units emitted no area slug at all**, and 8 emitted two areas and no activity |
| Budget was **not** the problem | 1.96 slugs/unit, mean rolled-up union 3.40 against mean authored 2.45; precision (0.521) ≈ recall (0.583), i.e. the swarm *substituted* wrong slugs rather than emitting too few |
| Two activities are systematically over-called | `bugfix` spurious 6×, `documentation` spurious 4× — the largest precision leaks |
| Two areas are over-called and never missed | `session-fuse` and `session-logging` each spurious 3×, missed 0× |
| Groundedness cost real recall | 5 slugs dropped as `quote-not-grounded`; 2 of them (`graph`, `session-logging`) were slugs the author had actually written |

So v2 **re-allocates the same budget** rather than enlarging it. The changes:

1. The two-axis rule is now an **output contract** — exactly one area slug and exactly
   one activity slug — with both observed failure shapes named and rejected. v1 said
   "two axes, one of each, ~2 slugs total" as advice; 21 of 45 units ignored it.
2. An explicit **area table** with per-slug applicability, replacing v1's bare "the
   area or subsystem". Area choice was 63% of the recall loss and v1 gave no help
   making it.
3. `memory-seed` is defined as the **residual core area** — which is the vocabulary's
   own wording ("Memory Seed product behavior not captured by narrower topics"), not a
   frequency guess. Five of run 1's misses were exactly this slug.
4. **Boundary rules for the measured confusions only**: edges vs queries
   (`graph`/`retrieval`), and narrow readings of the two over-called areas.
5. **Over-call brakes** on `bugfix` and `documentation`, the two activities that leaked
   precision.
6. A concrete **quote recipe** (short contiguous single-line fragment, verify before
   writing, shorten rather than abandon) in place of v1's "verbatim phrase".
7. **Two worked examples**, which v1 had none of. Both deliberately use low-frequency
   slug pairs so the examples teach the *shape* and the *quote discipline* rather than
   the corpus's popular slugs.

Nothing about the sample, the model tier, the validator, or the pass line changed.
Slugs are never ranked by how often the corpus uses them, and no rule tells a worker
to guess a slug it cannot ground.

---

# Your task

You are ONE worker in a topic-judgment swarm. You judge exactly ONE decision from a
software project's engineering log.

## What you may read — nothing else

1. Your TASK file (path given in your prompt). It holds `ordinal`, `decision_name`,
   and `decision_body`. The `decision_body` is the ONLY material you may judge.
2. `vocabulary.md` (path given in your prompt) — the 23 canonical topic slugs with
   labels and descriptions.

Do NOT search the repository, do NOT open any session log, do NOT try to find the
entry this decision came from, and do NOT guess its title. This judgment is
deliberately blind; reading anything else invalidates it.

## The output contract: one AREA + one ACTIVITY

Every judgment names **where** the work is and **what kind of work it was**. Your
answer has **exactly one area slug and exactly one activity slug**. A third slug is
allowed only in the narrow cross-cutting case below.

Two shapes are **wrong** and were the single largest source of error in the previous
run:

- **Two activities and no area** (e.g. `bugfix` + `documentation`). Every decision
  happens *somewhere*. If you cannot name a narrower area, the area is `memory-seed`
  — a broad area is right, a missing area is wrong.
- **Two areas and no activity** (e.g. `graph` + `memory-trace`). Every decision *did
  something*. Pick the activity that best describes the work, even if the decision
  touches two surfaces.

### AREA — where the work is. Exactly one.

| slug | choose it when the decision is about... |
|---|---|
| `memory-seed` | the core package, CLI, MCP server, seed runtime, validators, entry/metadata fields, caps, checks, or any core-product behaviour **that none of the narrower areas below covers**. The vocabulary defines it as the residual core area; using it is correct, not lazy. |
| `memory-trace` | the companion review UI package — its views, client, service, or rendering |
| `graph` | related-entry edges, lifecycle edges (`supersedes` / `evolves` / `related_entries`), continuity lineage, link audit, edge schema, edge confidence |
| `retrieval` | search, ranking, scoring, the retrieval service — the **query** side |
| `session-fuse` | the branch-session fuse and `merge-branch` integration machinery **specifically** — not branching in general |
| `session-layout` | session file layout, migrations, multi-user directory structure |
| `session-logging` | entry authoring, DRAFT discipline, decision harvest, append-only chronology **specifically** — not any change that happens to touch a session file |
| `mcp-tools` | the MCP tool surface, or CLI command design |
| `hooks` | session-start, prompt, and stop hooks |
| `mermaid` | decision-diagram sidecars and diagram authoring |
| `control-plane` | agent rules, skills governance, personas, reusable runtime files |
| `process-management` | process discovery, shutdown, upgrade workflows |

**Boundary rules** (these three confusions were measured, so read them):

- **Edges are `graph`; queries are `retrieval`.** Work on `related_entries`,
  `supersedes`, `evolves`, lineage, link audit, or edge schema is `graph` even when
  scoring, ranking, or candidate selection appears in the reasoning.
- **`session-logging` is about the act of authoring entries**, not about anything
  stored in a session file. A validator change that happens to read session files is
  `memory-seed`.
- **`session-fuse` is the fuse mechanism itself.** Ordinary branching, merging, or
  push mechanics is the `git-workflow` *activity*, with its own area.

### ACTIVITY — what kind of work it was. Exactly one.

| slug | choose it when the work was... |
|---|---|
| `bugfix` | repairing an **observed defect** — something was broken, wrong, or misbehaving and this fixes it |
| `ui-design` | interface layout, visual hierarchy, interaction design, rendered-UI behaviour |
| `documentation` | producing or correcting **prose as the artifact** — a README, spec, audit, or public doc |
| `proposal-lifecycle` | roadmap and proposal movement — filing, promoting, resolving, superseding a proposal or goal |
| `release` | version cuts, changelog folds, packaging, publish gates |
| `git-workflow` | branching, merging, integration topology, push/publish mechanics |
| `agent-collaboration` | subagents, worktrees, task packets, multi-agent hazards |
| `tooling-evaluation` | assessing an external tool or library, licensing checks |

**Over-call brakes** (the two activities that were most often wrong last run):

- **`bugfix` needs a defect.** Designing, hardening, or tightening a mechanism that
  was not broken is not `bugfix`. If the decision adds or shapes behaviour rather than
  repairing it, the activity is something else.
- **`documentation` needs prose to be the product.** Explaining a change inside the
  decision body is not `documentation`. Writing or fixing a doc, spec, or README is.

### Cross-cutting concerns — a rare third slug

`windows-encoding`, `performance`, and `security` are quality attributes that span any
area. Add one as a **third** slug only when that concern is genuinely the theme of the
decision — an encoding-corruption decision is `windows-encoding`, a profiling or
caching decision is `performance`. A decision that merely runs fast is not
`performance`. **Never** use one *instead of* an area or an activity.

### The cap

**At most 3 slugs. Two — one area, one activity — is the expected answer.** A label
applied to everything distinguishes nothing.

## Canonical spelling and grounding quotes

- Copy each slug's spelling from `vocabulary.md` exactly. A slug not in that list is
  discarded, even if it is a synonym of one that is.
- Every slug needs a `quote`. The recipe:
  1. Find the words in `decision_body` that justify that slug.
  2. Take a **contiguous run of roughly 4 to 12 words that sits on ONE line** of the
     body. Do not span two lines. Do not use an ellipsis. Do not stitch fragments.
  3. Copy it **character-for-character** — same words, same punctuation, same
     capitalisation, same backticks.
  4. **Re-read the body and confirm your quote appears in it literally** before you
     write the file.
- If a quote you drafted is not literally present, **shorten it** to the exact words
  you can see rather than abandoning a slug you are confident in. A shorter true quote
  is always available when the slug is right.
- If you genuinely cannot point at specific words for a slug, drop the slug rather
  than guess it.
- A quote not found verbatim in the body causes that slug to be **discarded even when
  the slug was correct.** Last run this silently threw away five judgments, two of
  which were right.

## Two worked examples

These are illustrative, not from your data. They demonstrate the *shape* and the
*quote discipline*.

**Example A.** `decision_body` contains the line:

```
- D: The SessionStart hook printed a stale orientation brief because it read the cached index instead of the newest session file; point it at the file.
```

CORRECT — one area (`hooks`), one activity (`bugfix`), each quote a short contiguous
run copied off that single line:

```json
{"entry_id": "...", "ordinal": "d1", "slugs": [
  {"slug": "hooks", "why": "the subject is the SessionStart hook", "quote": "The SessionStart hook printed a stale orientation brief"},
  {"slug": "bugfix", "why": "an observed defect is being repaired", "quote": "because it read the cached index instead of the newest session file"}
], "confidence": 0.8}
```

WRONG — `hooks` + `control-plane` is **two areas and no activity**. Also wrong:
`bugfix` + `documentation`, which is **two activities and no area**. Exactly one from
each list.

**Example B.** `decision_body` contains the line:

```
- D: Split the flat session directory into `sessions/<user>/` and document the migration in the layout spec.
```

Correct answer:

```json
{"entry_id": "...", "ordinal": "d2", "slugs": [
  {"slug": "session-layout", "why": "restructures the session directory layout", "quote": "Split the flat session directory into"},
  {"slug": "documentation", "why": "the layout spec is the artifact produced", "quote": "document the migration in the layout spec"}
], "confidence": 0.8}
```

One area, one activity, each quote a short contiguous run copied off a single line.

## What to write

Use the Write tool to create the output file named in your prompt, containing ONLY
this JSON and nothing else:

```json
{
  "entry_id": "<copy from the task file>",
  "ordinal": "<copy from the task file>",
  "slugs": [
    {"slug": "<the AREA slug>", "why": "<one clause>", "quote": "<verbatim fragment>"},
    {"slug": "<the ACTIVITY slug>", "why": "<one clause>", "quote": "<verbatim fragment>"}
  ],
  "confidence": 0.0
}
```

`confidence` is your own 0.0–1.0 estimate. Then reply with just the slugs you chose.
