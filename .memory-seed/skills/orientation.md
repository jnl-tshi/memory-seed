---
memory-system-version: 2.22
governing_adr: adr_runtime_discovery
tags:
  - memory-seed
  - orientation
  - session-start
---

# Orientation routine (start-of-session)

Run this before substantive work so you act on measured checkout facts and a bounded representation of
the latest session. The SessionStart hook is the automatic front door: it consumes the same report as
`memory-seed situate`, injects the latest file's path/size/entry count, and selects `direct` or `summarize`
from a fixed 12,000-character boundary. If hook facts are absent or stale, run `memory-seed situate`.

1. **Use the shared situate report** — it owns checkout identity, branch + uncommitted/ahead state,
   `integration_mode`, `merge_trigger`, worktree posture, local version facts, and the latest applicable
   session document. It also reports `characters`, `bytes`, `entries`,
   `compression_threshold_characters`, and `context_route`. The CLI and hook must not reimplement these
   measurements separately.

2. **Believe `## Location` over anything that told you where you are.** Worktree identity is *measured,
   never declared*. A harness banner, a task packet, or a directory named `…/worktrees/<session>` can all
   assert an isolated worktree that was never created — the directory exists, the checkout does not, and
   git silently resolves every command up to the primary checkout. `situate` classifies from your cwd, so
   its answer is the real one. If you need to check by hand, three commands settle it:
   `git rev-parse --show-toplevel` (a real worktree returns *itself*, not the repo root),
   `git rev-parse --git-dir` (a real worktree points into `.git/worktrees/<name>`), and `git worktree list`
   (a real worktree is listed).

   **If Location says PRIMARY checkout and this session will do more than read**, create an isolated
   worktree before the first write rather than at the first conflict — the shared checkout may be in use
   by another agent, and by the time you are ready to write, HEAD may have moved under you, so the base
   you branch from was never verified. See `agent_collaboration.md` for the namespace convention and the
   verify-after-create step. Orientation itself stays read-only; this is a decision to carry into the work,
   not something to act on while briefing.

3. **Apply the measured session-context route.** Never use `memory_search` to determine latest state.
   - `direct` (the file is at most 12,000 characters): read the entire latest session file in the primary
     context. The unit is the whole file, not a fixed number of recent entries.
   - `summarize` (the file is over 12,000 characters): launch one read-only worker at the smallest
     available economy capability tier whose context window can hold the whole file. Give it only the
     exact file path and the contract below; do not inherit conversation, personas, index, policy, or
     skill-registry context. If no suitable worker exists, read the file directly. If the file exceeds
     available worker context, split only at timestamped `##` entry boundaries, summarize every chunk,
     then reduce the results to the same contract.
   - `unavailable`: report the read failure and inspect the source safely; never guess a route.

   Economy-worker contract (maximum 800 tokens): final state after later corrections; accomplishments
   grouped by workstream; important decisions and recorded reasons; open follow-ups, risks, and unresolved
   questions; stale or superseded intermediate claims; source entry IDs/headings for consequential
   conclusions; and coverage as the exact source path plus `N/N` entries considered. The worker writes
   nothing and infers nothing absent from the file.

4. **Treat compression as a derived orientation, not authority.** Reopen the exact source entry before a
   consequential decision depends on its reasoning. Use `memory_search` only for topical "why?" history,
   followed by `memory_get_chunk` when the result matters.

5. **Load optional orientation context only when intent requires it.** Verify the published package version
   only for release/version questions. Read the next-steps document only for planning or prioritisation.
   Load policy, the Constitution, project index sections, and other skills when the task's trigger requires
   them, not merely because a session started.

6. **Brief the user in ≤ 6 lines:** checkout posture when shared or unsafe, branch + dirty/ahead state,
   the latest session's final state, relevant unresolved follow-ups, and any task-triggered version or
   worktree facts. Do not narrate the startup procedure.

Read-only: reconcile and brief — do not edit files, commit, or start work as part of orienting.

## First message: the operating-mode gate

Everything above runs *before the user has said anything*. A second set of decisions can only be made
once **intent** arrives, so run this once on the first substantive message of a session — and again on a
later turn if context was summarized and the answers are no longer in view.

The variables split by **enforcement class**, which is what decides whether setting one flips a real
switch or only records a judgment:

- **Tooling-enforced** — a command refuses, so compliance does not depend on the agent remembering.
  `checkout_posture` (measured; `worktree guard` blocks a root-checkout write), `worktree_decision`
  (the same guard refuses a write from the wrong checkout), `integration_mode`
  (`memory_session_integrate` declines under `pr`), and `merge_trigger` (the handoff commands —
  `session merge-branch`, `session open-pr`, `session fuse --apply` — refuse to land under `manual`
  without `--user-approved`, which an agent must never self-supply).
- **Config-toggled** — a value decides what is in scope and the agent reads it; no refusal.
  `governing_persona` (`.agents/_registry.yaml` `status:`) and `skills_to_load` (this registry's
  `load_when`/`do_not_load_when`). The gate *names* these decisions; it adds no new toggle.
- **Advisory** — judgment with no enforcement point. `write_intent` (a classification that *feeds* the
  tooling-enforced worktree switch), `risk_tier` (`risk_signaling.md`), `orchestration_level`, and
  `version_state` (informational, already in the brief). No code can compute a risk tier, so the gate
  records reasoning the agent then acts on and says so rather than pretending otherwise.

Run them in order — each step depends on the ones above it:

1. **Check `checkout_posture`** — measured, and believe it over any banner or task packet claiming
   otherwise (`situate`'s `## Location` names the checkout you are actually in).
2. **Check `integration_mode` and `merge_trigger`** — the landing contract for anything this session
   produces, established before work starts rather than discovered at merge time.
3. **Classify intent → set `write_intent`** (`read-only` or `writing`).
4. If `writing`: set `risk_tier`, then `orchestration_level` — the lowest that can do the work safely.
5. **Derive `worktree_decision`** = f(`write_intent`, `checkout_posture`): writing into a `primary`
   checkout means create an isolated worktree **before the first write**, then verify it after creating
   rather than trusting the create — see `agent_collaboration.md`.
6. **Load `skills_to_load`** from the trigger registry.

**Read-only work stops after step 3.** The gate is cheap and self-terminating; that property is what
keeps a mandatory step from decaying into noise nobody reads.

None of this is persisted. The variables are established and acted on, not stored: the deterministic
facts keep arriving from the SessionStart injection and `situate`, and a new state file would be a
derived store that drifts from ground truth.
