---
memory-system-version: 2.22
governing_adr: adr_worktree_convention
tags:
  - memory-seed
  - skill
  - worktree-reconciliation
  - git-workflow
---

# Worktree Reconciliation Skill

Use this skill before recommending or performing cleanup of a dirty, stale, detached, deregistered,
or otherwise uncertain Git worktree. It owns evidence-led review of candidate worktrees. Immediate
cleanup of the exact source worktree after a successful guarded branch integration remains owned by
`agent_collaboration.md` and the integration command.

## Outcome

Produce one descriptive summary per worktree before any deletion recommendation. The summary must
reconstruct why the worktree exists, what its own Memory Seed history claims happened, what remains
open, what Git independently verifies, what differs from the local integration branch, and which
content class each relevant change belongs to.

This workflow is Session-first and Git-second:

- Session evidence reconstructs workstream intent, chronology, claimed completion, follow-ups, and
  discrepancies that a commit graph cannot explain.
- Git verifies rather than replaces that storyline. Git remains authoritative for whether content is
  present on the integration branch and whether removal is mechanically safe.

## Safety And Authority

- Preserve the active authority order: declared ratified Constitution, current concern-owning control
  file, accepted ADR head, session evidence, then derived projections.
- Treat deletion as a destructive STOP-category action. Assessment and recommendation are read-only;
  removal requires separate live approval for each exact worktree.
- Approval for one worktree never authorizes another. A general earlier cleanup request, a plan, or a
  recorded approval is not live consent for an exact removal.
- Preserve the branch unless branch deletion is separately and explicitly authorized. A worktree and
  its branch are different lifecycle objects.
- Never modify, reset, clean, stash, commit, or discard another worktree merely to make it removable.
  Recover unique content into an explicitly chosen destination before cleanup.
- Never use `memory_search` to determine newest state. It is a topical-history tool, not a recency
  instrument.

## Procedure

### 1. Resolve The Candidate Set

1. Start from an explicit candidate list or the Worktrees section of `memory-seed esr`. ESR and
   `memory-seed worktree classify --json` are read-only evidence; neither is permission to remove.
2. Resolve every candidate to one normalized, resolved absolute target. Reject a namespace root,
   glob, unresolved variable, nested computed target, reparse point that escapes its namespace, or
   any target whose identity is ambiguous.
3. From the repository context, capture `git worktree list --porcelain`. Record whether the target is
   registered, its branch or detached HEAD, its Git administrative path, lock/prunable state, and the
   local integration branch (normally local `main`, unless project configuration says otherwise).
4. Review candidates individually. Do not collapse several worktrees into a single assessment.

### 2. Session-First Storyline

For each registered worktree, enter that worktree read-only and use its nearest `.memory-seed/`
runtime. For deregistered residue, use the nearest provable surviving runtime associated with the
repository and label the resulting storyline reconstructed rather than worktree-local.

1. Run the worktree's local orientation path (the `memory-seed situate` route). When the checkout
   contains Memory Seed source, use the checkout-local command, for example
   `python -X utf8 -m memory_seed.cli situate`, rather than a bare globally installed executable.
   Otherwise use the project's documented local launcher and verify which package or script it loaded.
2. Apply the measured latest-session route from `orientation.md`: read the entire latest session file
   directly at or below the threshold; above it, use the read-only economy-summary contract. The unit
   is the whole routed file, not an arbitrary last-two-entry slice.
3. Identify relevant branch-local session entries by the worktree's recorded branch and workstream.
   Read the exact entries that bear on creation, intent, claimed completion, integration, cleanup,
   follow-ups, or known discrepancies with the integration branch. Topical `memory_search` may help
   find older rationale only after the measured newest-state route has been applied; fetch exact
   consequential chunks before relying on them.
4. Reconstruct the storyline in time order:
   - workstream purpose and intended outcome;
   - decisions and material source evidence;
   - work claimed complete and validation claimed;
   - recorded follow-ups, blockers, and retained risks;
   - later corrections or supersessions; and
   - differences between what the worktree history claims and what current local `main` contains.
5. Label session statements as claims until Git or current files verify them. Missing, malformed, or
   contradictory session evidence makes the item uncertain; it never becomes evidence of safety.

### 3. Git-Second Verification

Use Git to test the reconstructed storyline. At minimum, capture or verify:

- exact worktree registration and administrative identity from `git worktree list --porcelain`;
- current HEAD, branch or detached state, and lock/prunable flags;
- `git status --short --untracked-files=all` inside the candidate;
- merge base, ahead/behind counts, commit reachability, and whether the candidate tip is an ancestor
  of the local integration branch;
- branch-only commits and their changed paths;
- tracked working-tree diffs against HEAD and against the local integration branch; and
- content hashes or direct diffs for untracked or suspicious files when path equality alone cannot
  prove duplication.

Do not infer content equivalence from matching filenames, similar summaries, a clean branch, or a
merged commit alone. A merged branch can still have dirty unique work, and an unmerged branch can be
safe to dematerialize only when its branch is deliberately retained and all working-tree content is
accounted for.

### 4. Classify The Evidence

Classify every material commit, tracked change, untracked file, or residue into one of these explicit
categories. A worktree may contain more than one category.

- **committed work preserved by the branch** — unique commits remain reachable from a retained branch
  even when they are not on the integration branch;
- **uncommitted unique work** — tracked or untracked content is not otherwise proven preserved;
- **content already present on the integration branch** — Git ancestry, content hashes, or a direct
  diff proves the same content is on local `main` or the configured integration branch;
- **content preserved elsewhere as non-governing reference** — exact evidence was intentionally
  retained outside active authority, with its destination and provenance named;
- **generated or disposable residue** — reproducible caches, build output, environments, or partial
  debris whose source and regeneration path are known; or
- **uncertain** — any item whose identity, provenance, uniqueness, authority, or recoverability is not
  established.

Uncommitted unique work and uncertain items block deletion. Committed work preserved only by a branch
requires an explicit recommendation to retain that branch and proof that the ref exists before and
after worktree removal.

### 5. Report Before Recommending

Write one descriptive summary per worktree with:

- exact resolved path, registration state, branch/HEAD, and integration branch;
- the session-first storyline with exact session entry references;
- the Git-second findings, including divergence, reachability, dirty paths, and content checks;
- every material item assigned to one of the six evidence categories;
- discrepancies between the session story, current files, and Git;
- a recommendation: retain, recover first, safe to remove after approval, or uncertain; and
- the branch-preservation statement and any remaining risk.

Do not present a table-only verdict or a bare `clean/merged/removable` label as the summary. The user
must be able to understand what the workstream was and what would be lost or retained.

### 6. Live Approval And Removal

1. Name one exact resolved worktree target and its recommendation. Ask for separate live approval for
   that target. Repeat for each additional worktree; do not batch consent by implication.
2. Immediately before removal, re-run registration, identity, branch/HEAD, lock, and dirty-state
   checks. If anything changed, stop and re-reconcile that worktree.
3. Prefer `git worktree remove <exact-resolved-path>` for a registered worktree. The bulk
   `memory-seed worktree classify --apply` path may act on every currently removable worktree, so do
   not use it unless every target it would remove has been individually named, freshly reconciled,
   and separately approved live.
4. Never use `--force` to bypass unreviewed dirty or unique content. If live approval explicitly
   discards a reviewed diff, record the exact discarded paths and evidence first.
5. For already-deregistered residue, remove only the pre-verified resolved absolute target after
   confirming it is absent from the registered set, contains no unique or uncertain content, and has
   not changed identity. On Windows use a native literal-path operation; never construct a recursive
   delete from enumeration output, a wildcard, or an unvalidated variable.
6. If deletion fails or is partial, report it immediately and do not claim success. Retain the exact
   error and residual path for deliberate follow-up; never broaden the target to make the result tidy.

#### Windows directory-handle recovery

Use this recovery only when a previously approved, exact deregistered residue remains proven empty or
otherwise disposable and native deletion fails because Windows reports that the directory is in use.
It does not relax any content, identity, path, or approval gate above.

1. Make at most one passive retry after a short wait, re-running the exact registration, resolved-path,
   path-type, reparse-point, and content checks first. Repeated blind retries are not recovery.
2. Diagnose the exact path with a read-only OS handle inspector. Record every owning PID, process name,
   executable or command line when available, creation time, parent chain, and matched path. A common
   cause is app-managed helper processes that inherited working-directory handles from the removed
   worktree. Do not infer the owner from a process name alone.
3. If local handle inspection is unavailable, report that limitation. Do not enable system-wide handle
   tracking, download or run a diagnostic utility, accept its licence, or install software without the
   authorization those actions require. Never close an individual foreign handle directly; forced
   handle closure can destabilize the owning process.
4. Process termination requires separate live approval. Deletion approval does not authorize interrupting
   helpers or shared tools. Before acting, show the exact verified process group and expected impact.
5. Immediately before termination, re-read every candidate PID and refuse stale, missing, reused, renamed,
   or differently parented processes. Stop only the minimum verified lock-owning helper subtree, children
   before helper roots. Never terminate any process outside that subtree, including the owning application's
   user interface, control plane, IDE, editor, or app server, unless the user separately authorizes that exact
   process after seeing its verified identity and impact. Never kill by executable name, vendor-specific
   allowlist or denylist, wildcard, or an earlier PID inventory.
6. After the approved helper stop, re-run every target proof from step 1 and attempt the exact literal-path
   deletion once. If it still fails, retain the residue and report the new error; do not escalate to broader
   termination or deletion.
7. Restart helpers through their owning application or tool surface from the intended surviving workspace,
   not by launching their raw executables. Stdio-managed MCP and REPL helpers need the owner's connection
   channel as well as a corrected working directory. Verify each restarted surface with a minimal,
   non-mutating health check. Do not index or transmit private repository content merely to perform a
   restart health check; use a disposable non-sensitive fixture when a real request is required, then
   remove that fixture.
8. Confirm the exact residue is physically absent, the application/server processes intentionally preserved
   above remain alive, and each restarted helper surface responds. Report separately which helpers were
   stopped, which were restarted, and whether any could not be restored.

### 7. Post-Removal Verification

After each individually approved removal:

- confirm the exact target is absent from `git worktree list --porcelain`;
- confirm physical post-removal absence of the exact resolved path, or report the residue precisely;
- confirm the preserved branch ref and expected commits still exist;
- run `git worktree prune` only after the target-specific result is understood; and
- rerun the relevant ESR Worktrees section or equivalent inventory without treating a clean report as
  proof until the instrument is shown to have enumerated the expected repository.

## Output

- One descriptive assessment per worktree, session evidence first and Git evidence second.
- Explicit six-way content classification for every material item.
- A target-specific recommendation and unresolved-risk statement.
- If removal is authorized: exact approval scope, removal command/result, branch preservation, and
  post-removal verification. A partial or failed removal remains incomplete.
