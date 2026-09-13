---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_merge_branch_primitive
title: session merge-branch is the one-step integration primitive, not a git merge driver
topics:
  - git-workflow
  - session-fuse
created_at: 2026-08-06T20:00:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# session merge-branch is the one-step integration primitive, not a git merge driver

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_dr5eprnhrctqeeg3:d1`

### Decision

Current authoritative decision for this concern: `mse_dr5eprnhrctqeeg3:d1`. See the source decision for its full statement.

### Reason

No lifecycle edge has carried this decision forward, so it remains current. Related decisions are recorded as supporting context only - the contract keeps related references out of lineage semantics.

### Impact

Re-anchored from the control-file founding onto its session decision; related decisions recorded as context: mse_v26pem9hsvsbjbge:d3.

### Awaiting review

- `mse_j41ywke76agqw4yj:d1` - session merge-branch remains the one-step integration primitive, and its refusal exits now abort their own...
- `mse_87n8q05m0k01kjr4:d1` - After the post-fuse commit command reports failure, session merge-branch reconciles repository state before...
- `mse_ghpefqfxx4n9cbnw:d1` - The one-step merge primitive includes source-worktree retirement: after committing and verifying the merge,...

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T20:00:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#write-surface-parity",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#append-only",
      "role": "supporting"
    }
  ],
  "event_id": "adre_c52de32a7351a02eed33",
  "founding_quote": "One-step branch integration (current unreleased worktree)",
  "founding_source": ".memory-seed/index.md#L172",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_dr5eprnhrctqeeg3:d1",
    "mse_9c151e4gbkkv1w5v:d1"
  ]
}
```

#### Decision

Branch integration is one explicit CLI wrapper, `memory-seed session merge-branch --branch <branch>`, which sequences fuse dry-run, `git merge --no-ff --no-commit`, session-path reset to base content, fuse apply, staging and the merge commit. It fails closed: fuse issues abort before any merge state exists. It is deliberately NOT a git merge driver and not an enforcement-only pre-commit hook.

#### Reason

Git can merge text and preserve branch topology, but it cannot validate entry_id, branch provenance, or append-only session order - so raw line-merges landed session entries out of chronological order twice in a single day when the manual dry-run/apply dance was skipped. Making the correct sequence a single command removes the opportunity to skip a step, while keeping it an explicit command (rather than a driver that fires invisibly on every merge) keeps the Memory-Seed-aware validation visible and refusable.

#### Impact

Founded on the position that fuse is an explicit integration command rather than a Git union merge driver, then hardened into the one-step wrapper after the two out-of-order incidents.

### revision-accepted - 2026-08-06T21:20:00Z

```json
{
  "event_id": "adre_48efed23f793af01c1d5",
  "founding_source": ".memory-seed/index.md#L172",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/index.md#L172.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/index.md#L172 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-08-07T01:00:00Z

```json
{
  "decision_ref": "mse_dr5eprnhrctqeeg3:d1",
  "event_id": "adre_2014f8c7d421d848f0f7",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_v26pem9hsvsbjbge:d3"
  ],
  "update_entry_id": "mse_ex5216t2hn30s5wx"
}
```

#### Decision

Current authoritative decision for this concern: `mse_dr5eprnhrctqeeg3:d1`. See the source decision for its full statement.

#### Reason

No lifecycle edge has carried this decision forward, so it remains current. Related decisions are recorded as supporting context only - the contract keeps related references out of lineage semantics.

#### Impact

Re-anchored from the control-file founding onto its session decision; related decisions recorded as context: mse_v26pem9hsvsbjbge:d3.

### revision-accepted - 2026-08-07T03:00:00Z

```json
{
  "decision_ref": "mse_dr5eprnhrctqeeg3:d1",
  "event_id": "adre_db0cd093162d58ddc446",
  "expected_authoritative_decision": "founding:.memory-seed/index.md#L172",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_ex5216t2hn30s5wx"
}
```

#### Decision

Accept mse_dr5eprnhrctqeeg3:d1.

#### Reason

Approved by JNL 2026-08-07: attach the related integration decision; head converges onto the ADR's own decision.

#### Impact

mse_dr5eprnhrctqeeg3:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.

### context-added - 2026-08-08T04:01:00Z

```json
{
  "event_id": "adre_2cd4d88a99201691eeda",
  "impact_provenance": "preserved",
  "source": "derived",
  "supporting_decisions": [
    "mse_81v7vk4x5ys3k2n0:d1",
    "mse_azn6bejpd9xpmh3f:d2",
    "mse_kq3ba0cy9nkpqkm0:d1",
    "mse_vm7trfd4dbd5yvnn:d1",
    "mse_w2fk7qnx4t9b3vmh:d1",
    "mse_x6qgkg61dnq26bk4:d1",
    "mse_znfnyxssvhz5srz9:d1"
  ],
  "update_entry_id": "mse_g9xegd9ct9sns5s4"
}
```

#### Decision

Record the supplied decisions as context for this ADR.

#### Reason

Attaching the seven session-fuse chain members this concern was never given. Founded from a lineage pass that carried only one related decision, so it named 1 of its chain's 8 members.

#### Impact

This adds supporting context only; it does not change ADR membership, status, or authority.

### revision-proposed - 2026-08-10T07:12:00

```json
{
  "decision_ref": "mse_j41ywke76agqw4yj:d1",
  "event_id": "adre_59894d6e06cd058259e8",
  "impact_provenance": "preserved",
  "predecessors": [
    {
      "decision": "mse_dr5eprnhrctqeeg3:d1",
      "relation_assertion": "link:mse_j41ywke76agqw4yj:d1:evolves:mse_dr5eprnhrctqeeg3:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_j41ywke76agqw4yj"
}
```

#### Decision

session merge-branch remains the one-step integration primitive, and its refusal exits now abort their own half-started merge: any exit with merge_in_progress and no content conflicts runs git merge --abort and reports 'merge aborted automatically; nothing was committed'. Genuine non-session content conflicts are still left in progress for manual resolution, and a post-fuse commit failure does not abort (the fused tree is worth inspecting). Apply-phase refusal messages name the side whose copy was validated.

#### Reason

A refusal's half-started merge holds no state a human can use - there are no conflict markers, only a rejection - and committing it would half-apply a changeset. The prior never-abort rule predates the refusal/conflict distinction; conflicts keep it, refusals do not. The side attribution closes the 2026-08-09 misdirection where a base-side chronology failure read as the branch's fault and the repair deadlocked.

#### Impact

Refines the one-step primitive's failure contract; proposed by mse_ entry this event anchors to, pending JNL's acceptance.

### revision-proposed - 2026-08-10T16:00:00

```json
{
  "decision_ref": "mse_87n8q05m0k01kjr4:d1",
  "event_id": "adre_0f1cf73bc521ae6d5866",
  "impact_provenance": "preserved",
  "predecessors": [
    {
      "decision": "mse_j41ywke76agqw4yj:d1",
      "relation_assertion": "link:mse_87n8q05m0k01kjr4:d1:evolves:mse_j41ywke76agqw4yj:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_87n8q05m0k01kjr4"
}
```

#### Decision

After the post-fuse commit command reports failure, session merge-branch reconciles repository state before classifying the operation: a new merge commit containing the expected source tip and Memory-Entry trailers is committed success; otherwise the genuine in-progress failure remains inspectable.

#### Reason

A slow post-commit hook can outlive the shared 30-second Git subprocess timeout after Git has already created the merge commit, producing a false failure result and skipping safe source-worktree cleanup.

#### Impact

Refines the one-step integration primitive's commit-failure contract without weakening its timeout, genuine-failure preservation, or exact-target cleanup safeguards.

### revision-proposed - 2026-09-10T14:56:00

```json
{
  "decision_ref": "mse_ghpefqfxx4n9cbnw:d1",
  "event_id": "adre_20b3c6d76185d6af743d",
  "impact_provenance": "preserved",
  "predecessors": [
    {
      "decision": "mse_87n8q05m0k01kjr4:d1",
      "relation_assertion": "link:mse_ghpefqfxx4n9cbnw:d1:evolves:mse_87n8q05m0k01kjr4:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_ghpefqfxx4n9cbnw"
}
```

#### Decision

The one-step merge primitive includes source-worktree retirement: after committing and verifying the merge, it removes the clean registered source through Git and may remove only the exact same directory residue after Git deregistration when repository, branch, administrative pointer, directory identity, and path-type checks still pass. A failure leaves the merge committed but the task cleanup incomplete.

#### Reason

A merge that silently leaves its task checkout consuming disk space is operationally incomplete, while exact pre-removal identity plus fresh post-failure checks bounds the destructive fallback to the source checkout already approved for Git removal.

#### Impact

Normal successful integrations reclaim their source-worktree disk space even when Git partially removes a checkout on Windows or OneDrive; unsafe or still-locked cases surface as cleanup-pending and cannot be mistaken for a fully closed task.
