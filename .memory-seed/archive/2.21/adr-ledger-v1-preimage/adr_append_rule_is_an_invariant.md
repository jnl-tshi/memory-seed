---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_append_rule_is_an_invariant
title: The append rule is stated as an invariant, not as a mechanism
topics:
  - session-logging
  - agent-rules
created_at: 2026-08-08T03:00:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# The append rule is stated as an invariant, not as a mechanism

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `ms-e30b9c47:d1`

### Decision

The append rule is stated as a vendor-neutral invariant: session entries must be added at the physical end of their file, in chronological order, never inserted above existing content. The mechanism to achieve this—whether shell append (>>), Python append mode, or editor-based with an anchor—is left to each agent's available tooling.

### Why

Mandating a specific tool like >> or Python append mode assumed shell or Python access and was platform-unsafe; Windows PowerShell's heredoc example fails or misencodes, making such requirements unsuitable for a cross-platform agent contract. The durable rule is the invariant itself; the property that actually matters is that nothing is inserted above existing content and chronological order is preserved, while the mechanism belongs to each agent's tools.

### How it evolved

Initially instituted as a requirement for >> or Python append mode because append operations write unconditionally to the physical end with no anchor, making correct ordering mechanical rather than reliant on editor care. Later recognized as platform-dependent and reframed to state the invariant itself, demoting the specific tool to an optional shell tip so any file-reading agent can satisfy it with whatever writing surface it has.

### Constitution

- `constitution:v1#append-only` (governing)
- `constitution:v1#model-independence` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-08T03:00:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#append-only",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#model-independence",
      "role": "supporting"
    }
  ],
  "decision_ref": "ms-e30b9c47:d1",
  "event_id": "adre_8e176ec34cf3f51cabda",
  "source": "derived",
  "supporting_decisions": [
    "ms-d15e8a03:d1"
  ],
  "update_entry_id": "ms-e30b9c47"
}
```

#### Decision

The agent contract states the append INVARIANT - an entry is added at the physical end of its file, never inserted above existing content, and chronological order holds - and does not mandate the tool that achieves it. Shell append and Python append mode are optional tips, not requirements.

#### Why

The contract is read by any file-reading agent, so mandating `>>` assumed shell or Python access and was platform-unsafe: the shell example simply fails for an agent that edits files directly. Stating the invariant lets each agent satisfy it with whatever writing surface it has, while the property that actually matters - nothing is inserted above existing content - is unchanged. This is distinct from Constitution Invariant #2, which says the past IS append-only; this concern is about how that rule is expressed to the agents bound by it.

#### Evolution

The rule first shipped as a mechanism, requiring shell append or Python append mode as the method for writing session entries; it was then reframed as a vendor-neutral invariant with the mechanism demoted to an optional shell tip.

### revision-rejected - 2026-08-08T23:00:00Z

```json
{
  "decision_ref": "ms-e30b9c47:d1",
  "event_id": "adre_9b1701919888335655ec",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

### revision-proposed - 2026-08-08T23:00:20Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#append-only",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#model-independence",
      "role": "supporting"
    }
  ],
  "decision_ref": "ms-e30b9c47:d1",
  "event_id": "adre_9a25bf746de587161e2b",
  "source": "derived",
  "supporting_decisions": [
    "ms-d15e8a03:d1"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

The append rule is stated as a vendor-neutral invariant: session entries must be added at the physical end of their file, in chronological order, never inserted above existing content. The mechanism to achieve this—whether shell append (>>), Python append mode, or editor-based with an anchor—is left to each agent's available tooling.

#### Why

Mandating a specific tool like >> or Python append mode assumed shell or Python access and was platform-unsafe; Windows PowerShell's heredoc example fails or misencodes, making such requirements unsuitable for a cross-platform agent contract. The durable rule is the invariant itself; the property that actually matters is that nothing is inserted above existing content and chronological order is preserved, while the mechanism belongs to each agent's tools.

#### Evolution

Initially instituted as a requirement for >> or Python append mode because append operations write unconditionally to the physical end with no anchor, making correct ordering mechanical rather than reliant on editor care. Later recognized as platform-dependent and reframed to state the invariant itself, demoting the specific tool to an optional shell tip so any file-reading agent can satisfy it with whatever writing surface it has.

### revision-accepted - 2026-08-08T23:00:40Z

```json
{
  "decision_ref": "ms-e30b9c47:d1",
  "event_id": "adre_5b3b51e3b4256e055e99",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```
