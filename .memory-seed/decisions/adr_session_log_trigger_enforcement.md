---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_session_log_trigger_enforcement
title: Session-log entries are triggered by content change, not elapsed time alone
topics:
  - control-plane
  - bugfix
  - session-logging
created_at: 2026-08-31T13:28:10Z
user_initials: JNL
agent_type: claude
source: write-time
---

# Session-log entries are triggered by content change, not elapsed time alone

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_dpa5g3h1fma6dazw:d1`

### Decision

Replace the stale-or-dirty obligation rule with evidence-backed checkpoint debt: Git evidence creates immediate debt, while elapsed time creates only one clean non-escalating self-check.

### Reason

The current OR-combined trigger makes clean elapsed time manufacture repeatable debt. The successor retains the proven Git baseline, turn-anchored language, and file-vs-memory checkpoint while separating clean advisory delivery from unresolved evidence.

### Impact

The accepted ADR remains authoritative during the staged trial. If the candidate passes the paired scenario gate, this decision becomes the accepted head and the runtime, CLI, MCP, hooks, seed templates, and ignored state move to the checkpoint model together; if it fails, the current head remains in force.

### Awaiting review

- `mse_4e4y2348y7493b37:d1` - A session-log entry is required whenever git detects tracked-file changes outside the session log since the...
- `mse_9xcwr1j80g755x16:d1` - State explicitly in the hook wording and standing rules that writing a fact into a project file is not itself...

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-31T13:28:10Z

```json
{
  "decision_ref": "mse_4e4y2348y7493b37:d1",
  "event_id": "adre_92c0459a5d6eb0a37203",
  "impact_provenance": "preserved",
  "source": "write-time",
  "supporting_decisions": [
    "mse_97jrpfbzq4pyr77h:d2"
  ],
  "update_entry_id": "mse_4e4y2348y7493b37"
}
```

#### Decision

A session-log entry is required whenever git detects tracked-file changes outside the session log since the last logged entry, not only after 15 minutes of elapsed time.

#### Reason

A fast automated session can edit real files and exit well inside a time-based staleness window; the 2026-08-27 independent memory-index dry-run replication measured this directly - a 13-minute, 10-session run in which 6 sessions edited files without logging, and no gap between logged entries ever approached 15 minutes. A content-based git-diff trigger, baselined at the last logged entry and excluding the session log's own paths, closes this without over-firing on already-covered or self-referential changes.

#### Impact

Originally enforced only by a 15-minute staleness clock in session-log-check.py (fixed 2026-05-29 to key off the entry heading timestamp rather than file mtime). Extended 2026-08-29 with a SHA-256 git-diff fingerprint trigger, OR-combined with the time-based check, after the independent replication (mse_97jrpfbzq4pyr77h) measured the time-only mechanism's structural blind spot.

### revision-proposed - 2026-08-31T15:05:48Z

```json
{
  "decision_ref": "mse_81504w3dkaanm395:d1",
  "event_id": "adre_2ba08657d4d7a1ae55a8",
  "impact_provenance": "preserved",
  "predecessors": [
    {
      "decision": "mse_4e4y2348y7493b37:d1",
      "relation_assertion": "link:mse_81504w3dkaanm395:d1:evolves:mse_4e4y2348y7493b37:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_81504w3dkaanm395"
}
```

#### Decision

Reword the git-diff/stale-only/repeated hook reminders to restore turn-anchored urgency and close the 'not my work' loophole

#### Reason

Run 7 (the fix-validation replication) proved the trigger fires correctly (consecutive_misses: 7) but overall compliance got worse, not better - the new git-diff message's impersonal, historical framing ('the working tree has changes... detected from git') gave a session linguistic room to rationalize pre-existing dirty state as 'another session's in-progress work' and skip logging, a reading the old turn-anchored message never supported. That rationalization, written into a durable entry, appears to have propagated to the two sessions whose real code changes then also went unlogged.

#### Impact

The reworded messages should be falsifiable against a second replication run (Run 8) on the same fixture and questions used for Run 6/Run 7: if compliance and the blended score recover toward Run 6's baseline without a new blocking mechanism, the wording was the cause; if not, the next escalation is enforcement, not further wording iteration.

### revision-accepted - 2026-08-31T18:12:37Z

```json
{
  "decision_ref": "mse_81504w3dkaanm395:d1",
  "event_id": "adre_c5873867c407f6f96c83",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_s931k17g4d3w01r4"
}
```

#### Decision

Accept mse_81504w3dkaanm395:d1.

#### Reason

Run 8 (mse_s931k17g4d3w01r4:d1) validated the wording-fix revision empirically: blended 83.9/CLEAR, the best of three runs, with the two sessions whose silence caused Run 7's regression logging again.

#### Impact

mse_81504w3dkaanm395:d1 becomes the authoritative decision; later contrary evidence must create a successor revision.

### revision-proposed - 2026-08-31T20:34:12Z

```json
{
  "decision_ref": "mse_9xcwr1j80g755x16:d1",
  "event_id": "adre_2a23fcd846c314c42869",
  "impact_provenance": "preserved",
  "predecessors": [
    {
      "decision": "mse_81504w3dkaanm395:d1",
      "relation_assertion": "link:mse_9xcwr1j80g755x16:d1:evolves:mse_81504w3dkaanm395:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_9xcwr1j80g755x16"
}
```

#### Decision

State explicitly in the hook wording and standing rules that writing a fact into a project file is not itself a memory record

#### Reason

S3, S4, and S10 never logged in any of Run 6/7/8, unaffected by the turn-anchoring wording fix - a different rationalization than Run 7's 'not my work': the task hands the session an already-settled fact and one mechanical file edit, and writing it into the file appears to read as task-complete without a separate memory-record checkpoint.

#### Impact

Falsifiable against a fourth run (Run 9) on the same fixture/questions: if S3/S4/S10 log (at minimum a small-work entry) and the corresponding questions (Q3, Q6, Q19) recover, the file-vs-memory framing was the missing piece; if not, this is a genuine negative result and the next lever is enforcement, not a third wording attempt.

### revision-proposed - 2026-09-28T16:38:00

```json
{
  "decision_ref": "mse_dpa5g3h1fma6dazw:d1",
  "event_id": "adre_4e74735e25596a5c5558",
  "impact_provenance": "preserved",
  "predecessors": [
    {
      "decision": "mse_81504w3dkaanm395:d1",
      "relation_assertion": "link:mse_dpa5g3h1fma6dazw:d1:replaces:mse_81504w3dkaanm395:d1"
    },
    {
      "decision": "mse_9xcwr1j80g755x16:d1",
      "relation_assertion": "link:mse_dpa5g3h1fma6dazw:d1:evolves:mse_9xcwr1j80g755x16:d1"
    }
  ],
  "source": "write-time",
  "update_entry_id": "mse_dpa5g3h1fma6dazw"
}
```

#### Decision

Replace the stale-or-dirty obligation rule with evidence-backed checkpoint debt: Git evidence creates immediate debt, while elapsed time creates only one clean non-escalating self-check.

#### Reason

The current OR-combined trigger makes clean elapsed time manufacture repeatable debt. The successor retains the proven Git baseline, turn-anchored language, and file-vs-memory checkpoint while separating clean advisory delivery from unresolved evidence.

#### Impact

The accepted ADR remains authoritative during the staged trial. If the candidate passes the paired scenario gate, this decision becomes the accepted head and the runtime, CLI, MCP, hooks, seed templates, and ignored state move to the checkpoint model together; if it fails, the current head remains in force.

### revision-accepted - 2026-09-28T17:13:00Z

```json
{
  "decision_ref": "mse_dpa5g3h1fma6dazw:d1",
  "event_id": "adre_732a4cac26c881cfb0bf",
  "expected_authoritative_decision": "mse_81504w3dkaanm395:d1",
  "impact_provenance": "preserved",
  "source": "write-time",
  "update_entry_id": "mse_gef34nw8hafgv3nf"
}
```

#### Decision

Accept mse_dpa5g3h1fma6dazw:d1.

#### Reason

The approved paired scenario gate passed: the candidate removed clean elapsed-time debt, preserved tracked and untracked implementation capture, added changed-HEAD capture the legacy rule missed, cleared on a new entry, and restricted mechanical clearance to deterministic whitespace-only proof. The broader interface, parity, lifecycle, and documentation slice passed 212 tests plus six host-shape subtests.

#### Impact

mse_dpa5g3h1fma6dazw:d1 becomes the authoritative decision; later contrary evidence must create a successor revision.
