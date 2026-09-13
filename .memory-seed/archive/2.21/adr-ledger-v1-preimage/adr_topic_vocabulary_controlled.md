---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_topic_vocabulary_controlled
title: "Topic vocabulary: controlled, alias-preserving, canonicalised at read time"
topics:
  - topic-vocabulary
  - graph
  - retrieval
created_at: 2026-08-08T03:05:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Topic vocabulary: controlled, alias-preserving, canonicalised at read time

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_jz0pwv0ngzzxr484:d1`

### Decision

The project maintains a controlled topic vocabulary in `.memory-seed/topics.yaml` as a deploy-once project-local file. Authored entries use 1-3 slugs validated against the canonical list; unknown historical slugs resolve as aliases at read time, preserving every observed variation. The cap for inferred topics is 4, matching the corpus-authored maximum.

### Why

Usage-derived vocabulary was necessary because sprawl had materialized before a formal schema existed. Deriving from 62 real-world slugs and aliasing ensured the entire live corpus validated with zero errors immediately. The 4-topic cap reflects the highest authored reach: a genuinely four-facet entry should not be rejected for inferring a fourth topic, which would hold inference to a stricter standard than the human author. The cap is kept rather than removed because universal labels distinguish nothing; bounded at 4, nothing in the corpus exceeds it.

### How it evolved

The decision started by consolidating observed 62 slugs into 19 canonical ones with aliases (2026-07-10). Two later extensions added `ui-design` and `memory-seed`, then `security` (with openssf/supply-chain aliases) and `performance` (with perf/profiling aliases), growing the vocabulary to 23 by reflecting real entry usage rather than retroactively constraining historical corpus. Finally, the inferred-topic cap rose from 3 to 4 to treat the machine and author equally.

### Constitution

- `constitution:v1#topic-vocabulary` (governing)
- `constitution:v1#append-only` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-08T03:05:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#topic-vocabulary",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#append-only",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_jz0pwv0ngzzxr484:d1",
  "event_id": "adre_688f717362ebdd95fd36",
  "source": "derived",
  "supporting_decisions": [
    "mse_ehm67mqpmsqm00md:d1",
    "mse_vy8tq90rr4br8a0z:d1",
    "mse_ke0f6x2v8zmd3yrf:d1"
  ],
  "update_entry_id": "mse_jz0pwv0ngzzxr484"
}
```

#### Decision

The project maintains a controlled canonical topic vocabulary in `.memory-seed/topics.yaml` as a deploy-once project-local file that update never overwrites. Authored entries carry 1-3 slugs validated against the canonical list; aliases resolve to canonical slugs at read time, preserving every observed historical slug in the alias table. The inferred-topic cap is 4, matching the corpus-authored maximum. Unknown topics are errors; overreach warns only.

#### Why

Usage-derived vocabulary was necessary because topic sprawl had already materialised - 62 slugs across 50 entries. Deriving from real usage plus alias preservation made the corpus validate with zero errors on day one, and deploy-once protects curation from update overwrites. Capping at 4 reflects the authored maximum: a genuinely four-facet entry should not be rejected for inferring a fourth topic, which would hold the inference path to a stricter standard than the author.

#### Evolution

2026-07-10 consolidated 62 observed slugs into 19 canonicals with alias preservation; 2026-07-12 added ui-design and memory-seed; 2026-07-19 added security and performance, growing to 23; 2026-07-25 raised the cap from 3 to 4 to match the corpus.

### revision-rejected - 2026-08-08T23:21:00Z

```json
{
  "decision_ref": "mse_jz0pwv0ngzzxr484:d1",
  "event_id": "adre_a06d23aad25d180b0715",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

### revision-proposed - 2026-08-08T23:21:20Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#topic-vocabulary",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#append-only",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_jz0pwv0ngzzxr484:d1",
  "event_id": "adre_5ff551249f0f0d0634f2",
  "source": "derived",
  "supporting_decisions": [
    "mse_ehm67mqpmsqm00md:d1",
    "mse_vy8tq90rr4br8a0z:d1",
    "mse_ke0f6x2v8zmd3yrf:d1"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

The project maintains a controlled topic vocabulary in `.memory-seed/topics.yaml` as a deploy-once project-local file. Authored entries use 1-3 slugs validated against the canonical list; unknown historical slugs resolve as aliases at read time, preserving every observed variation. The cap for inferred topics is 4, matching the corpus-authored maximum.

#### Why

Usage-derived vocabulary was necessary because sprawl had materialized before a formal schema existed. Deriving from 62 real-world slugs and aliasing ensured the entire live corpus validated with zero errors immediately. The 4-topic cap reflects the highest authored reach: a genuinely four-facet entry should not be rejected for inferring a fourth topic, which would hold inference to a stricter standard than the human author. The cap is kept rather than removed because universal labels distinguish nothing; bounded at 4, nothing in the corpus exceeds it.

#### Evolution

The decision started by consolidating observed 62 slugs into 19 canonical ones with aliases (2026-07-10). Two later extensions added `ui-design` and `memory-seed`, then `security` (with openssf/supply-chain aliases) and `performance` (with perf/profiling aliases), growing the vocabulary to 23 by reflecting real entry usage rather than retroactively constraining historical corpus. Finally, the inferred-topic cap rose from 3 to 4 to treat the machine and author equally.

### revision-accepted - 2026-08-08T23:21:40Z

```json
{
  "decision_ref": "mse_jz0pwv0ngzzxr484:d1",
  "event_id": "adre_8a2e3012f6ddd004a6a4",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```
