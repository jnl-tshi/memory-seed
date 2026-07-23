---
title: "First-Message Operating-Mode Gate + Session Variable Schema"
date: "2026-07-23"
project: "memory-seed"
status: "proposed-awaiting-design-review"
priority: "P2"
blocked_by: "user design review — accept/amend the variable schema and the merge_trigger semantics before any agent-rules.md change"
next_action: "JNL reacts to the schema and the open questions in §6. Only then draft the agent-rules.md gate + project.yaml merge_trigger default."
related:
  - "docs/CONSTITUTION.md"
  - ".memory-seed/agent-rules.md"
  - ".memory-seed/skills/orientation.md"
  - ".memory-seed/skills/agent_collaboration.md"
  - ".memory-seed/skills/risk_signaling.md"
  - "docs/5_Completed/configurable-integration-mode-plan.md"
  - "docs/5_Completed/agent-worktree-and-branch-hygiene-plan.md"
---

# First-Message Operating-Mode Gate + Session Variable Schema

Status: **PROPOSED — awaiting design review.** Nothing in the control plane changes until JNL reacts to
the schema (§4) and the open questions (§6). This is the "design it, then you react" artifact.
Priority: P2 — a control-plane consistency improvement, not a B0b blocker.
Source: JNL, 2026-07-22, in the session that shipped the worktree-posture Location work. Two operating-mode
decisions in that session — *create a worktree?* and *hold the merge or auto-land it?* — were both made ad
hoc rather than by any established rule. JNL's framing: "the first message a user inputs to a project should
trigger a sequence of operating mode variables to be set," with the merge-to-main trigger (manual vs
automatic) as the worked example.

## 1. Problem

Operating mode today is a **procedure** (`agent-rules.md` "Operating Mode Start": read these files, establish
state) that produces no explicit, checkable *decisions*. The consequential per-session choices — is this
read-only or writing work, what risk tier, do I isolate in a worktree, do I hold the merge for the user — are
made implicitly, per turn, by prose discipline. That has two failure modes, both observed:

- **Skipped.** The worktree decision was nearly missed this session; the agent was one command away from
  branching off another session's in-flight HEAD in the shared checkout. Recorded remedy shipped, but the
  decision itself had no gate forcing it.
- **Re-litigated / drifted.** The same choice gets re-made differently on later turns, especially after
  context is summarized. `mse_61bnt9ty6rfgpw1e` (D3) records three same-day collisions with a concurrent
  session because coordination posture was never a fixed session fact.

The SessionStart hook and `situate` already establish the **facts** (newest state, version, checkout
posture). What's missing is the layer that turns facts **plus the user's intent** into a small set of
**decisions** that then govern the whole session consistently.

## 2. Key insight: intent is what the first message adds

Every existing orientation surface fires *before the user has said anything* — SessionStart injects context,
`situate` reconciles local facts. Neither knows what the user wants. A whole class of operating-mode
decisions can only be made once **intent** arrives, i.e. on the first substantive message. That is the seam
this proposal sits on, and it cleanly splits the variables:

- **Session-stable** variables are established at SessionStart / orientation and only need **checking** at
  first message.
- **Intent-dependent** variables can only be **set** at first message, from the task.

## 3. Why a routine, not a hook (already decided)

JNL selected a **routine in `agent-rules.md`**, not a new hook. Reasons, recorded so the decision survives:

- **Portability.** A first-prompt hook needs a per-prompt event. Claude/Codex/Cursor have one; Gemini has no
  `UserPromptSubmit` equivalent and Copilot is limited (per `index.md`). A vendor-neutral system cannot put
  the *source of truth* on a surface a third of its agents lack.
- **Judgment.** A hook injects deterministic text; it cannot classify intent or weigh a risk tier. The
  intent-dependent half of the schema *requires the model*, so it cannot live in a hook at all.
- **Constitution.** The variables are **established-and-acted-on, not persisted.** No new state file — that
  would be a derived store the "Markdown is source of truth, every DB is a rebuildable projection" invariant
  then has to account for, and it would drift from ground truth like any cache. The deterministic facts keep
  coming from the SessionStart injection; the gate reads them, it does not re-store them.

A per-prompt hook MAY later *reinforce* the routine on agents that support it, but as reinforcement, never as
the authority.

## 4. Proposed variable schema (react to this)

Two groups, set in dependency order. Names are proposed; all are open to amendment.

### 4a. Session-stable — established at SessionStart, CHECKED at first message

| Variable | Values | Source (today) | Notes |
|---|---|---|---|
| `checkout_posture` | `primary` / `owned-worktree` / `foreign` | measured — `worktree_guard` / `situate` `## Location` | shipped this session |
| `integration_mode` | `local-merge` / `pr` | `.memory-seed/project.yaml` | exists; how integration happens |
| `merge_trigger` | `manual` / `automatic` | **NEW** — proposed `project.yaml` default | when/who lands it — see §5 |
| `governing_persona` | one active persona | `.agents/_registry.yaml` | most task-relevant active persona |
| `version_state` | local vs published; unreleased? | `situate` + PyPI check | already in the orientation brief |

### 4b. Intent-dependent — SET at first message, from the task

| Variable | Values | Depends on | Source rule |
|---|---|---|---|
| `write_intent` | `read-only` / `writing` | the task | does the task change files/state? |
| `risk_tier` | `proceed` / `proceed-and-flag` / `propose-and-wait` / `stop` | task + write_intent | `risk_signaling.md` |
| `orchestration_level` | `0` / `1` / `2` / `3` | task scope | `agent-rules.md` orchestration levels |
| `worktree_decision` | `stay` / `create` | `write_intent` × `checkout_posture` | writing + `primary` ⇒ create before first write |
| `skills_to_load` | set of skill files | task | trigger registry match |

### 4c. The sequence ("a sequence of variables to be set")

Ordered because each step depends on the ones above it:

1. **Check** `checkout_posture` (measured — believe it over any banner).
2. **Check** `integration_mode` and `merge_trigger` (the landing contract for anything this session produces).
3. **Classify** intent → set `write_intent`.
4. If `writing`: set `risk_tier`, then `orchestration_level`.
5. Derive `worktree_decision` = f(`write_intent`, `checkout_posture`): writing into a `primary` checkout ⇒
   create an isolated worktree **before the first write**, verify after creating (per `agent_collaboration.md`).
6. Load `skills_to_load` from the registry.

Read-only tasks stop after step 3 — the gate is cheap and self-terminating, exactly the property that keeps a
mandatory step from becoming noise (the same reasoning that kept a warning out of `situate`).

## 5. The worked example: `merge_trigger` (JNL's case)

> "whether the user wants the merges back to main to be triggered or automatic to allow multi branch entries
> and a check of key session variables"

`merge_trigger` decides **when and by whom** a task branch lands in local `main`:

- **`manual` (proposed default under `local-merge`).** The agent commits on the task branch, holds
  integration, and waits for the user to trigger `session merge-branch`. This is what **allows multi-branch
  entries**: several task branches can coexist, each carrying its own *on-branch* session entries, and the
  Trail keeps the lanes separate. This session did exactly this — held both branches, asked before merging.
- **`automatic`.** The agent merges its own task branch into local `main` at a stable, tested stopping point
  without waiting. Faster for solo rapid iteration, but it collapses the multi-branch picture: each workstream
  lands immediately, so branches never accumulate side by side.

Two things make this a genuine variable rather than a restatement of `integration_mode`:

- **Orthogonal axis.** `integration_mode` is *how* you integrate (local merge vs PR). `merge_trigger` is
  *when/who* triggers it (hold-for-user vs auto). In `pr` mode the trigger is arguably always manual (a human
  reviews the PR), so `merge_trigger` varies meaningfully mainly under `local-merge` — see the open question.
- **It governs session-logging.** `manual` is what makes the "log on branch, not main" discipline work:
  entries live on the task branch until integration, and `session merge-branch` fuses them in chronological
  order preserving the branch lane. Logging on `main` post-merge loses that lane separation and starves the
  `Memory-Entry` trailers — a hazard already recorded in durable memory. So `merge_trigger` is not a
  convenience toggle; it is upstream of where session memory is written.

"A check of key session variables" (JNL's phrase) is step 1–2 of the sequence: the gate **verifies**
`checkout_posture`, `integration_mode`, and `merge_trigger` before acting, so the landing contract is a known
session fact rather than a per-turn improvisation. On a later turn after context is summarized, the check
re-runs.

## 6. Open questions (the design review)

1. **`merge_trigger` default.** Propose `manual` under `local-merge` (matches today's "do NOT push without
   instruction" spirit and preserves multi-branch accumulation). Is `automatic` ever the right default for
   solo rapid iteration, or should it always be an explicit per-session opt-in?
2. **Is `merge_trigger` a facet of `integration_mode` or its own field?** Proposed: its own `project.yaml`
   field (orthogonal axis), read fail-open like `integration_mode`. Alternative: fold it in as
   `local-merge-auto` vs `local-merge-manual`. The separate field is cleaner but adds a knob.
3. **Enforcement.** As a routine, the gate is discipline + a checklist in `agent-rules.md`. Should anything
   *verify* it ran — e.g. an ESR line "operating-mode gate: variables recorded this session"? Or is a recorded
   routine enough for v0, matching how orchestration-level and risk-tier are handled today?
4. **Schema fixity.** A fixed named list (§4) is checkable and teachable but rigid. Is the full list right, or
   should some variables (e.g. `governing_persona`, `skills_to_load`) stay as prose rather than named slots?
5. **Where the intent-dependent decisions get recorded, if anywhere.** Options: nowhere durable (act on them,
   let them re-derive); a one-line note in the session entry's context; surfaced by `situate`. Proposed:
   nowhere durable for the intent-dependent half (Constitution), session-stable half stays in `project.yaml` /
   measured as today.

## 7. Scope / Non-goals

**In scope (if accepted):** a "First-Message Operating-Mode Gate" section in `agent-rules.md` documenting the
schema and the ordered sequence; a `merge_trigger` `project.yaml` default read fail-open and surfaced by
`situate`/`esr`; cross-references from `session_logging.md` and `agent_collaboration.md` for the on-branch
logging + multi-branch behavior `merge_trigger` governs; both seed twins.

**Non-goals:** no persistent variable *store* / new state file (Constitution); no new hook as the source of
truth (a reinforcing hook is a possible later follow-on, not this proposal); no change to `integration_mode`
semantics; no automation of the merge *decision* away — `merge_trigger: manual` keeps the human in the loop;
the variable only makes the choice explicit and consistent instead of per-turn improvisation.

## 8. Acceptance criteria

- `agent-rules.md` (+ seed twin) carries the gate: the variable schema and the ordered sequence, with the
  read-only early-exit.
- `merge_trigger` is a documented `project.yaml` default, read fail-open as the chosen default, surfaced by
  `situate` and `esr`, and honored by the integration guidance in `agent_collaboration.md`.
- `session_logging.md` and `agent_collaboration.md` cross-reference `merge_trigger` for on-branch logging and
  multi-branch accumulation.
- No new persistent state file; no new required hook. Seed/live parity holds (twin tests green).
- The gate demonstrably would have forced this session's two decisions (worktree, merge-hold) rather than
  leaving them to improvisation.

## 9. Provenance

Extracted from the 2026-07-22 worktree-posture session (`situate` `## Location`, the SessionStart posture
note, and the two ad-hoc operating-mode decisions that motivated JNL's framing). Builds on the shipped
[configurable integration mode](../5_Completed/configurable-integration-mode-plan.md) (which added
`integration_mode`) and the
[agent worktree/branch hygiene plan](../5_Completed/agent-worktree-and-branch-hygiene-plan.md) (worktree=session,
branch=task).
