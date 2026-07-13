---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - control-plane
  - git-workflow
  - agent-collaboration
---

# Configurable integration mode (`local-merge` vs `pr`)

Status: **IN PROGRESS** (2026-07-13) — P0.1 shipped (the `integration_mode` field in `project.yaml` + core
reader + `esr` surfacing); P0.2 (agent contract: skills/agent-rules read and follow the mode) pending.
Stays in `docs/2_Todo/`.
Priority: P2 — foundational control-plane feature; the OpenSSF credibility work (`openssf-credibility-proposals.md`)
sits on top of it. Sequence this **before** that plan's PR/branch-protection step (G2), which becomes
"set this repo to `pr` and follow it."
Source: User 2026-07-13 — "have the option to support both the PR + branch-protection workflow and
the direct-merge-to-local-main flow… based on user decision and whether it's a solo dev or a team."
Scope: Add a declared, project-local **integration mode** that governs how branch work lands, and make
the tooling + agent contract follow it. Two modes to start: `local-merge` (today's behaviour) and `pr`.
Non-goals: No auto-detection of "solo vs team" at runtime; no richer enum yet (`patch`/`handoff` deferred);
no change to what an *entry* records; no new hosting-provider dependency for `local-merge` projects.

## Why this fits (not a bolt-on)
Memory Seed already treats PR systems as **optional integration layers** and carries a *per-task*
`integration_artifact: pr|merge-request|patch|branch|handoff` in the Task Packet
(`skills/agent_collaboration.md`). What's missing is a **project-level default** so the agent and
tooling pick one model consistently instead of deciding ad hoc — and the tooling only implements the
local side today (`session merge-branch` merges to local `main`; there is no push→PR primitive). This
proposal promotes that implicit per-task choice to a declared project setting.

## Locked decisions (user, 2026-07-13)
- **Simple enum to start:** `integration_mode: local-merge | pr`. (`patch`/`handoff` deferred.)
- **Declare, don't detect.** No silent runtime switch; bootstrap may *suggest* based on heuristics,
  the human confirms.
- **Default `local-merge`** — backward-compatible; unset/old projects behave exactly as today.
- **Layering:** the project `integration_mode` is the default; the existing per-task
  `integration_artifact` remains the override for a single task.
- **Safety:** a declared `integration_mode: pr` *is* the durable push authorization for the normal
  push→PR flow (satisfies the standing "never push to origin without explicit instruction" default,
  recorded once). Force-push and other destructive/irreversible ops stay gated regardless of mode.

## The setting
`.memory-seed/project.yaml` gains one field, alongside `participants:`:

```yaml
integration_mode: local-merge   # or: pr
```

Deploy-once / project-local, like `participants` and `topics.yaml`: created at bootstrap, preserved by
`update` (never version-overwritten). Absent field ⇒ `local-merge`.

## Mode semantics
- **`local-merge`** (default, unchanged): branch work integrates into local `main` via
  `memory-seed session merge-branch` — fuse dry-run gate → `git merge --no-ff --no-commit` →
  conflict classification → session-path reset → fuse apply → commit → Memory-Entry trailers. No push.
- **`pr`**: branch work integrates through the hosting provider. The agent **prepares the branch**
  (see the key design point below), pushes it to `origin`, and opens a PR; the **host** performs the
  merge (behind required checks / review). The agent does **not** merge to local `main`.

## Key design point — where the fuse work happens
`session merge-branch`'s fuse does load-bearing work *during the local merge*: it imports branch-only
session entries in chronological order, **resets session paths to defeat git's silent out-of-order
auto-merge**, and stamps trailers. In `pr` mode the actual merge happens on GitHub, which runs none of
that — so a naïve "just push and PR" risks interleaved/out-of-order session entries on merge.

**Proposed resolution: prepare the branch so the host merge is trivially clean.** Before pushing, the
`pr`-mode integrate step brings the branch up to date with `main` and lays its session entries into
their correct chronological position **as commits on the branch** (reusing the fuse's chronology
logic, applied branch-side rather than merge-side), with trailers stamped by the existing
`prepare-commit-msg` hook. The pushed branch then merges cleanly on the host with no reordering.
(Alternative — a post-merge CI repair on `main` — is heavier and needs CI write access; deferred.)
This branch-prep is the main implementation risk and should be prototyped first.

## Tooling
A mode-aware entry point dispatches on `integration_mode`:
- `local-merge` → the existing `session merge-branch` (unchanged).
- `pr` → a new push→PR primitive: fuse **dry-run as a gate** (must pass), branch-prep (above), push,
  then `gh pr create` with a body summarising the branch's session entries + validation evidence.
- **Preflight for `pr`:** an `origin` remote must exist and `gh` be available/authenticated; fail with
  a clear message if not (a purely local project cannot PR — tell the user to use `local-merge`).

Naming is open — either a unified `session integrate --branch <b>` that dispatches, keeping
`merge-branch` as the explicit local primitive and adding e.g. `session open-pr`; or teaching
`merge-branch` the mode (rejected: "merge-branch" is the wrong name for a flow that doesn't merge
locally). Recommendation: `session integrate` dispatcher + `merge-branch` (local) + `open-pr` (pr).

## Bootstrap heuristic (suggest, never switch)
At bootstrap/init, detect team signals — branch protection already on `main`, >1 collaborator, or
existing PRs (via `gh`, fail-open) — and **suggest** `pr`; otherwise default `local-merge`. The human
confirms the written value. Never flip an existing project's mode automatically.

## Agent contract (skills)
`agent-rules.md` + `agent_collaboration.md` (live + seed) gain a short rule: **read
`project.yaml: integration_mode` and follow it.** In `local-merge`, integrate via `session
merge-branch` and do not push. In `pr`, integrate via the push→PR primitive; the declared mode is the
standing push authorization for that normal flow. `session_logging.md`'s handoff guidance references
whichever integration artifact the mode produces. Unset ⇒ `local-merge`.

## Phases
1. **Setting + readers:** `integration_mode` in `project.yaml`; a core reader (fail-open, default
   `local-merge`); `esr`/`doctor` surface the active mode. Tests.
2. **Agent contract:** skills + agent-rules read and follow the mode (live + seed twins); safety-rule
   interaction documented. Tests / startup-contract line-budget check.
3. **`pr` tooling:** the branch-prep + push + `gh pr create` primitive and the `session integrate`
   dispatcher, with the `origin`/`gh` preflight. Tests over a temp git repo (mock/skip the actual
   `gh` call; assert the prepared branch and the PR-body plan).
4. **Bootstrap heuristic:** suggest-`pr` detection at init; `update` preserves the field.

## Acceptance criteria
- `project.yaml` carries `integration_mode`; default and unset both behave as `local-merge` (no
  regression to current flows).
- The agent contract makes `local-merge` (no push) vs `pr` (push→PR) unambiguous, and a declared `pr`
  mode is honoured as push authorization without per-action re-prompting.
- `pr` mode produces a clean, correctly-ordered branch and an opened PR; it refuses clearly when
  `origin`/`gh` are absent.
- Force-push and destructive operations remain gated in both modes.
- `update` preserves a project's chosen mode.

## Relationship to the OpenSSF credibility plan
This is the foundation that plan's **G2** consumes: rather than a one-off "adopt PR flow," this repo
simply declares `integration_mode: pr` and everything (agent + tooling + the OpenSSF branch-protection
step) follows. A solo project stays `local-merge`. Sequence: this proposal's Phases 1–3, then the
OpenSSF plan.
