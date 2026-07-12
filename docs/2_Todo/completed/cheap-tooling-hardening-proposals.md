# Cheap tooling for skill/hook weak points — proposal set

Status: inbox (for discussion, 2026-07-12)
Origin: holistic review after the lifecycle-links + entry-id hardening. Pattern
established today, twice: a skill rule without a one-call tool does not hold
against flow (lifecycle edges rotted to one file in 312 entries; every agent
hand-rolled entry ids). Each proposal below names a process that currently
lives only in skill prose or agent recall, the failure it already caused or
will cause, and the smallest tool that closes it. Ordered by expected payoff.

---

## P1 — `session append`: entry-authoring scaffolder

**Problem.** Session entries are authored as hand-typed heredocs. Every field
is agent recall: the id (hand-rolled until today), the timestamp (must match
the wall clock AND sort after the previous entry), `related_entries` refs
(fabrication happened: a nonexistent `mse_9x5vc50wghc4bnmz` was written and
caught only by luck), the target file, the YAML shape. The standing
**chronological violation (12:15 logged after 12:20 on 2026-07-12) has blocked
`session merge-branch` all day**, forcing manual `--no-ff` merges with
hand-stamped trailers — a direct, ongoing cost of unguarded manual authoring.

**Tooling.** `memory-seed session append --title <t> --topics a,b
[--supersedes id ...] [--evolves id ...] [--related id ...] [--body-file f | stdin]`:
resolves the target (`session_target`), stamps the current timestamp, computes
the id via the canonical generator, **validates every ref against known
entries and the forward-only rule before writing**, rejects an append that
would land out of chronological order, writes the entry. A matching
`memory_session_append`-shaped MCP surface is deliberately NOT proposed — MCP
never writes session files (established contract); MCP agents get P1's
validation via `links check` + `memory_entry_id` instead.

**Payoff.** Eliminates four recurring failure classes (bad ids, fabricated
refs, chronology violations, wrong target) and the token overhead of the
resolve-target → generate-id → self-review loop every entry, several times per
session.

**Discuss.** Should body content stay agent-authored free text (D/R/A/F/T
prose piped in), with the tool owning only heading+YAML? (Recommended: yes —
the tool guards structure, never voice.)

---

## P2 — Chronology repair: `session reorder --date <day> --dry-run/--apply`

**Problem.** The 12:15/12:20 misorder persists because repairing it is a
historical edit agents rightly hesitate to freehand: it needs a byte-precise
block move with nothing else changed. Meanwhile every merge pays the manual
workaround tax.

**Tooling.** Deterministic same-day reorder of entry blocks by heading
timestamp: `--dry-run` prints the planned move as a diff; `--apply` performs
it only with unchanged entry bytes (ids, refs, bodies untouched — pure block
permutation), refuses anything else. Explicit user approval per run.

**Payoff.** Unblocks `session merge-branch` (returns trailer stamping and
fuse to the tool instead of by-hand merges). One-shot repair + permanent
repair path; P1 prevents recurrence.

**Discuss.** Is a pure permutation acceptable under append-only? (Position:
yes — order is presentation, content is history; the entries' bytes are
unchanged. But this is exactly the kind of call the user should make.)

---

## P3 — Memory-Entry trailer automation: `prepare-commit-msg` hook

**Problem.** `session merge-branch` stamps trailers automatically, but
ordinary commits that carry session entries need the agent to remember to
write `Memory-Entry:` trailers by hand (the skill says so; recall-dependent).
A forgotten trailer silently downgrades the Trail's commit-accurate merges to
"estimated" — the exact gap the merge-accuracy work closed, reopening one
forgotten commit at a time.

**Tooling.** A git `prepare-commit-msg` hook (installed/refreshed by
`memory-seed init`/`update`, like the existing session-log-check Stop hook):
scan the staged diff for `+entry_id:` lines and append one `Memory-Entry:`
trailer per new id, deduplicated, only when absent. Zero agent tokens, zero
recall. CLI fallback `memory-seed commit-trailers --print` for environments
where git hooks are unwelcome.

**Payoff.** The entry→commit join becomes true by construction on every
commit, not just tool-mediated merges.

**Discuss.** Hook auto-install policy — opt-in flag vs default-on at init?
(Recommended: default-on at `init`, opt-in at `update` to avoid surprising
existing checkouts.)

---

## P4 — `esr report`: one-command end-of-turn mechanical preflight

**Problem.** `end_of_turn.md` is 16 prose steps. The mechanical half — links
check, topics check, `link audit --date today`, stale-worktree candidates
(list + ahead/behind + dirty status per worktree), untracked/scratch file
scan — costs a dozen exploratory tool calls per session, every session. This
is the single largest recurring token spend in the workflow, and steps get
skipped under length pressure (the lifecycle-edge rot proves it).

**Tooling.** `memory-seed esr report [--date today]`: runs every
deterministic check in one pass and prints one compact sectioned report
(integrity, link gaps, worktree candidates with their dirty status, scratch
debris, topics warnings). The skill's steps then reference report sections;
the agent spends judgment only on flagged items. No auto-fixing — report
only, same read-only posture as `links check`.

**Payoff.** Highest token ROI of the set: ~12 tool calls → 1, per session
close, forever. Also makes skipped-step drift visible (an unread section is
still printed).

**Discuss.** Scope of v1 — start with the four checks that already exist as
commands (links/topics/audit/worktree-listing) and grow, or hold for the full
sweep including orphan heuristics?

---

## P5 — Seed-twin drift check in `doctor` (+ `--sync`)

**Problem.** Live skills under `.memory-seed/skills/` have twins under
`memory_seed/seed/`. Editing one without the other broke main today
(4b2e21a → fixed f29a77a): the mismatch is only caught by the core test
suite, which memory-trace-focused sessions don't run. Recall-dependent
convention, proven to fail.

**Tooling.** `memory-seed doctor` gains a twin-diff section (skill-by-skill
same/differs). `doctor --sync-seed` copies live → seed for confirmed drifts.
Optionally the same check in the session-log-check hook when a skill file is
modified (warning line, not a block).

**Payoff.** A red-main class disappears for the cost of a file diff.

**Discuss.** Sync direction — is live → seed always correct, or can seed be
edited first legitimately (release prep)? (Recommendation: doctor reports
both directions; `--sync-seed` only copies live→seed explicitly.)

---

## P6 — Kill the manual cache-bust convention (serve-time asset versioning)

**Problem.** Every static change requires hand-bumping `?v=<slug>-<date>` in
`index.html` (done by hand three times today). Forgetting ships stale JS to
the browser silently — a debugging time-sink that presents as "my fix didn't
work."

**Tooling.** Delete the convention instead of enforcing it: the lense `/`
route already returns `index.html` text; substitute `?v=<content-hash>` (or
mtime) for both asset tags at serve time. One small code change + test;
the manual rule and its skill-memory footprint vanish.

**Payoff.** A whole category of "why is the browser stale" gone; zero ongoing
cost.

**Discuss.** Content-hash (exact, marginally more work per request) vs mtime
(cheap, OneDrive-timestamp caveat)? (Recommended: content-hash, computed once
per process start.)

---

## P7 — Preview-from-worktree: verify UI changes without the temp-copy dance

**Problem.** The preview server pins to the primary checkout, so verifying a
worktree's UI change means temp-copying files into primary, verifying, then
`git checkout --` restoring. Risky by construction: this session the
copy direction got inverted once (core/retrieval edits accidentally landed in
primary and had to be recovered), and any crash mid-dance leaves primary
dirty. The worktree *switcher* covers per-branch DATA; this is about the
server's CODE/static assets.

**Tooling.** Either (a) a `--static-root <checkout>` / `MEMORY_TRACE_STATIC_ROOT`
override so the running server serves another checkout's `static/` (smallest,
covers the common JS/CSS case), or (b) a second `.claude/launch.json`
configuration launching uvicorn from the worktree (covers backend changes
too, needs a port or stop/start discipline).

**Payoff.** Removes the most error-prone manual sequence in the current
workflow (4+ uses today).

**Discuss.** Is (a) enough? Backend changes still need a restart-from-worktree
anyway, which (b) covers — but (b) is where preview_start's cwd pinning has
resisted before. Recommend (a) now, (b) investigated separately.

---

## P8 — Trail golden-fixture regeneration harness (lower priority)

**Problem.** `memory-trace/tests/fixtures/trail-golden-48.json` has been
stale since the lane-order change; regenerating requires manual browser
debug-hook steps, so it doesn't happen, and the fixture's regression value is
currently zero.

**Tooling.** A node harness (`node memory-trace/tests/fixtures/regen_trail_golden.mjs`)
that evaluates `app.js`'s pure model functions (`trailModel` has no DOM
dependencies) against the synthetic corpus and rewrites the fixture; a pytest
marks the fixture stale when model-relevant code changes.

**Payoff.** Restores a dormant regression net for the Trail's geometry — the
most-churned code in the project this week.

**Discuss.** Worth doing now, or after the Trail stabilizes? (It churned five
times today alone — which argues both ways.)

---

## Suggested order

P4 (biggest recurring token win) → P1+P2 (kills the standing merge blocker and
the largest integrity risk) → P3 (makes the Trail's ground truth complete) →
P5, P6 (tiny, deletes two proven drift classes) → P7 → P8.
