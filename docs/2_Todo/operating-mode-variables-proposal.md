---
title: "First-Message Operating-Mode Gate + Session Variable Schema"
date: "2026-07-23"
project: "memory-seed"
status: "proposed-awaiting-design-review"
priority: "P2"
blocked_by: "user design review — accept/amend the enforcement-classed schema (§4) and the merge_trigger gate mechanism (§5) before any control-plane or tooling change"
next_action: "JNL reacts to the enforcement-class framing and the open questions in §6. Only then draft the agent-rules.md gate, the project.yaml merge_trigger default, and the merge_trigger gate on session merge-branch / memory_session_integrate."
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

That "set when" split is one axis. §4 adds the second — **enforcement class** — which is what answers whether
setting a variable flips a real switch or only records a decision.

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

## 4. Proposed variable schema, by enforcement class

The variables carry two axes. **Set when** — session-stable (established at SessionStart, *checked* at first
message) vs intent-dependent (*set* from the task) — is §2's axis. **Enforcement class** is the one that
answers *does setting this flip a switch?*, and it is the primary framing here. Three classes. Names are
proposed; all are open to amendment.

### 4a. Tooling-enforced — a command refuses a disallowed action (real switches)

These bite at the tool boundary: the CLI/MCP command itself declines, so compliance does not depend on the
agent remembering.

| Variable | Set when | The switch |
|---|---|---|
| `checkout_posture` | session start (measured) | `worktree guard` returns `severity: block` for a root-checkout write — **shipped** |
| `worktree_decision` | first message (derived) | same guard: writing from the wrong checkout is refused |
| `integration_mode` | session (config) | `memory_session_integrate` **declines** when `pr` — **shipped** |
| `merge_trigger` | session (config) | **PROPOSED:** `session merge-branch` / `memory_session_integrate` refuse to land without an explicit user-authorization override when `manual` — see §5 |

### 4b. Config-toggled — a config/registry value changes what loads (agent-read, no refusal)

Mechanical in effect but not enforced by refusal: the value decides what is in scope, and the agent reads it.

| Variable | Set when | The toggle |
|---|---|---|
| `governing_persona` | session (registry) | `.agents/_registry.yaml` `status: active/inactive` already toggles which personas load |
| `skills_to_load` | first message | the trigger registry's `load_when`/`do_not_load_when` (deterministic). The gate **names** this decision; it adds no new toggle |

### 4c. Advisory — a judgment or fact with no enforcement point

Establishes reasoning, never a switch. Two are judgments no code can compute; one is informational; one is a
classification that *feeds* a 4a switch.

| Variable | Set when | Why advisory |
|---|---|---|
| `write_intent` | first message | a classification — it **feeds** the tooling-enforced worktree switch (4a) but is not itself refused |
| `risk_tier` | first message | judgment (`risk_signaling.md`); no code can compute a risk tier |
| `orchestration_level` | first message | judgment; a scope call |
| `version_state` | session start (measured) | informational; already in the orientation brief |

So, directly: **for 4a, yes — the gate flips real switches, and `merge_trigger` is the one new switch this
proposes.** For 4b it routes through config toggles that already exist without adding new ones. For 4c it
records reasoning the agent then acts on, and can be nothing more — a judgment has no switch to flip, and the
proposal says so rather than pretending otherwise.

### 4d. The sequence ("a sequence of variables to be set")

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

`merge_trigger` decides one thing: at a stable, tested stopping point, does the agent **auto-advance to the
integration handoff, or hold for the user?** The handoff itself is set by `integration_mode` — a **merge into
local `main`** under `local-merge`, or **opening the PR** under `pr`:

- **`manual` (proposed default).** The agent commits on the task branch and **holds**, waiting for the user
  before it takes the handoff step (`session merge-branch` under `local-merge`, `session open-pr` under `pr`).
  This is what **allows multi-branch entries**: several task branches coexist, each carrying its own
  *on-branch* session entries, and the Trail keeps the lanes separate. This session did exactly this — held
  both branches, asked before merging.
- **`automatic`.** The agent takes the handoff step itself at a stable stopping point: under `local-merge` it
  **merges into local `main`**; under `pr` it **opens the PR** (JNL, 2026-07-24). It never completes an
  irreversible or external step alone — under `pr` the merge stays the human reviewer's, and under
  `local-merge` it never pushes. Faster for solo iteration, but under `local-merge` it collapses the
  multi-branch picture: each workstream lands immediately, so branches never accumulate side by side.

Two things make this a genuine variable rather than a restatement of `integration_mode`:

- **Orthogonal axis.** `integration_mode` is *how* you integrate (local merge vs PR); `merge_trigger` is
  *whether the agent auto-advances* to that handoff or holds. It varies meaningfully under **both** modes:
  under `pr`, `automatic` auto-opens the PR while `manual` waits for the user to open it — so it is a genuine
  own axis, not a `local-merge` sub-mode (see §6.2).
- **It governs session-logging.** `manual` is what makes the "log on branch, not main" discipline work:
  entries live on the task branch until integration, and `session merge-branch` fuses them in chronological
  order preserving the branch lane. Logging on `main` post-merge loses that lane separation and starves the
  `Memory-Entry` trailers — a hazard already recorded in durable memory. So `merge_trigger` is not a
  convenience toggle; it is upstream of where session memory is written.

"A check of key session variables" (JNL's phrase) is step 1–2 of the sequence: the gate **verifies**
`checkout_posture`, `integration_mode`, and `merge_trigger` before acting, so the landing contract is a known
session fact rather than a per-turn improvisation. On a later turn after context is summarized, the check
re-runs.

### How `merge_trigger` gets teeth (the gate on the tooling)

Under `merge_trigger: manual`, whichever command performs the handoff — `session merge-branch` /
`memory_session_integrate` under `local-merge`, `session open-pr` under `pr` — **refuses to advance** unless
an explicit user-authorization override is present, the same shape as the worktree guard's `--allow-root-write`
(a deliberate flag the agent is contractually barred from self-supplying) and `integration_mode: pr` making
integrate decline. The agent commits on the task branch and holds; the user's
"go" is what authorizes the override. Under `automatic`, the command runs without it and the agent advances at a
stable, tested stopping point — merging locally, or opening the PR.

Why a flag and not agent-discipline alone: a CLI cannot distinguish an agent-initiated invocation from a
user-initiated one, so "refuse to auto-run" needs a token that *represents* user authorization — the override
flag is that token. That is what turns `merge_trigger` from prose the agent might skip into a switch the
tooling enforces, which is the whole point of the hybrid: the two decisions this proposal cares most about
(don't auto-advance integration, don't write into a shared checkout) become things a command refuses, not things the agent
must remember. `risk_tier` and `orchestration_level` cannot be made switches this way because nothing can
compute them — they stay advisory (§4c), and the proposal says so rather than pretending otherwise.

### Modes available (`integration_mode` × `merge_trigger`)

These two config axes are all a user actually *selects* — every other variable in §4 is measured or derived.
Their product is the operating modes:

| | `merge_trigger: manual` | `merge_trigger: automatic` |
|---|---|---|
| **`local-merge`** | **DEFAULT — hold and ask.** Agent commits on the task branch and stops; the user runs `session merge-branch` to land. Branches accumulate side by side with on-branch entries. This session's mode. | **auto-land.** Agent commits *and* merges into local `main` at stable stopping points. Fast solo iteration, no side-by-side accumulation. Never pushes. |
| **`pr`** | **hold and hand off.** Agent commits and pushes, then waits for the user before opening the PR; a human reviews and merges. | **auto-open PR** (JNL, 2026-07-24). Agent opens the PR itself at a stable stopping point; the human still reviews and merges — `automatic` never auto-*merges* a PR. |

`automatic` is bounded to local, reversible advancement: it may merge locally or open a PR, but never pushes
under `local-merge` and never merges a PR under `pr`. The irreversible or external step stays a human one in
both modes.

## 6. Open questions (the design review)

1. **`merge_trigger` default.** Propose `manual` under `local-merge` (matches today's "do NOT push without
   instruction" spirit and preserves multi-branch accumulation). Is `automatic` ever the right default for
   solo rapid iteration, or should it always be an explicit per-session opt-in?
2. **Is `merge_trigger` its own field?** Now leaning **yes**: JNL's 2026-07-24 resolution that `automatic`
   under `pr` means *auto-open the PR* confirms `merge_trigger` is meaningful under **both** integration
   modes, so it is a real orthogonal axis rather than a `local-merge` sub-mode (which would have argued for
   folding it in as `local-merge-auto`/`local-merge-manual`). Remaining call: confirm the own-field form and
   its `project.yaml` key name.
3. **`merge_trigger` gate mechanism.** The teeth are an override flag on `session merge-branch` /
   `memory_session_integrate` (mirroring `--allow-root-write`). Is that the right mechanism, or is a lighter
   agent-contract ("never merge without explicit user instruction") enough given `local-merge` never pushes?
   The flag is more robust and testable; the contract is simpler and adds no CLI surface. This is the one
   genuinely open piece of the hybrid.
4. **Schema fixity.** A fixed named list (§4) is checkable and teachable but rigid. Is the full list right, or
   should some variables (e.g. `governing_persona`, `skills_to_load`) stay as prose rather than named slots?
5. **Where the intent-dependent decisions get recorded, if anywhere.** Options: nowhere durable (act on them,
   let them re-derive); a one-line note in the session entry's context; surfaced by `situate`. Proposed:
   nowhere durable for the intent-dependent half (Constitution), session-stable half stays in `project.yaml` /
   measured as today.
6. **Does the advisory half need any verification?** The tooling-enforced (4a) and config-toggled (4b)
   variables carry their own enforcement; the advisory ones (`risk_tier`, `orchestration_level`) do not.
   Is a recorded routine enough for them, or should ESR note the gate ran — matching how orchestration-level
   and risk-tier are handled today (it does not)?

## 7. Scope / Non-goals

**In scope (if accepted):** a "First-Message Operating-Mode Gate" section in `agent-rules.md` documenting the
enforcement-classed schema and the ordered sequence; a `merge_trigger` `project.yaml` default read fail-open
and surfaced by `situate`/`esr`; the **`merge_trigger` gate itself** — an override flag on `session
merge-branch` / `memory_session_integrate` that refuses to land under `manual` without explicit authorization
(a real code change to the integration tooling, mirroring `--allow-root-write` and the `integration_mode: pr`
decline); cross-references from `session_logging.md` and `agent_collaboration.md` for the on-branch logging +
multi-branch behavior `merge_trigger` governs; both seed twins.

**Non-goals:** no persistent variable *store* / new state file (Constitution); no new hook as the source of
truth (a reinforcing hook is a possible later follow-on, not this proposal); no change to `integration_mode`
semantics; no automation of the merge *decision* away — `merge_trigger: manual` keeps the human in the loop;
the variable only makes the choice explicit and consistent instead of per-turn improvisation.

## 8. Acceptance criteria

- `agent-rules.md` (+ seed twin) carries the gate: the variable schema and the ordered sequence, with the
  read-only early-exit.
- `merge_trigger` is a documented `project.yaml` default, read fail-open as the chosen default, surfaced by
  `situate` and `esr`, and honored by the integration guidance in `agent_collaboration.md`.
- The `merge_trigger` gate has teeth: `session merge-branch` / `memory_session_integrate` **refuse** to land
  under `manual` without the explicit override, and proceed under `automatic` (or with the override), proven
  by tests on both paths.
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
