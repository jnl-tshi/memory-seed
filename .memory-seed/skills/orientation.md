---
memory-system-version: 2.19
tags:
  - memory-seed
  - orientation
  - session-start
---

# Orientation routine (start-of-session)

Run this before substantive work so you act on ground truth, not a stale in-context snapshot (which can
be frozen from an earlier turn or a detached worktree). It is the start-of-session mirror of the End Of
Turn routine: `memory-seed situate` does the deterministic local report, and the judgment below turns it
into a briefing.

1. **Run `memory-seed situate`** — one read-only report of local facts: current branch + uncommitted count
   + commits ahead of origin, the declared `integration_mode`, the newest session-log entry (path + last
   heading), the local `pyproject` version and whether the CHANGELOG carries unreleased work, and worktree
   posture (a stale sweep candidate is merged + clean).

2. **Verify the PUBLISHED version from the source of truth — never assume.** `situate` prints the exact
   command; run it (`curl -s https://pypi.org/pypi/memory-seed/json | python -c "import sys,json;print(json.load(sys.stdin)['info']['version'])"`,
   or `pip index versions memory-seed`; degrade gracefully if offline). If the local version is ahead of
   the published release, there is an unreleased tranche — read `CHANGELOG.md` "## Unreleased". Do not
   claim any version is released or unreleased without this check (the recurring stale-version trap).

3. **Read the newest session file directly** (the path `situate` names). It holds the current state and
   the last thing done. Do NOT use `memory_search` to find "latest" — semantic/lexical ranking can bury
   the newest entry beneath older topically-similar ones.

4. **Read the project's next-steps doc** if present (`docs/2_Todo/0_NEXT_STEPS.md`, or the project's
   equivalent) for the top pending actions.

5. **Brief the user in ≤ 6 lines:** version (local vs published, and whether an unreleased tranche
   exists), branch + uncommitted/ahead state, the last thing done, any stale worktree (and any dirty
   worktree — another agent's uncommitted work, which you must not touch), and the top 2–3 next actions.

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
