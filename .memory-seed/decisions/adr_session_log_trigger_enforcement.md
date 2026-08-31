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
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

A session-log entry is required whenever git detects tracked-file changes outside the session log since the last logged entry, not only after 15 minutes of elapsed time.

### Reason

A fast automated session can edit real files and exit well inside a time-based staleness window; the 2026-08-27 independent memory-index dry-run replication measured this directly - a 13-minute, 10-session run in which 6 sessions edited files without logging, and no gap between logged entries ever approached 15 minutes. A content-based git-diff trigger, baselined at the last logged entry and excluding the session log's own paths, closes this without over-firing on already-covered or self-referential changes.

### Impact

Originally enforced only by a 15-minute staleness clock in session-log-check.py (fixed 2026-05-29 to key off the entry heading timestamp rather than file mtime). Extended 2026-08-29 with a SHA-256 git-diff fingerprint trigger, OR-combined with the time-based check, after the independent replication (mse_97jrpfbzq4pyr77h) measured the time-only mechanism's structural blind spot.

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
