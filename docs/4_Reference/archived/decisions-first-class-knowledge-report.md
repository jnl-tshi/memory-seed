---
title: "Decisions as first-class knowledge — source rationale"
date: "2026-09-21"
status: archived-reference
extracted_into: "docs/2_Todo/hosted-memory-mvp-programme.md"
source: "User-supplied decision-intelligence proposal pack, 2026-09-21"
---

# Proposal: Decisions as a First-Class Knowledge Primitive

## Current disposition

**ARCHIVED SOURCE RATIONALE.** Its stable decision/evidence boundary is already expressed in the ratified [Constitution](../../CONSTITUTION.md), the [edition authority contract](../../3_Spec/edition-authority-contract.md), and the [hosted programme](../../2_Todo/hosted-memory-mvp-programme.md). This essay provides context; it creates no second authority or new active workstream.

## Purpose

Formalize the architectural idea that Memory Seed should treat decisions as a stable knowledge primitive rather than treating them as incidental artifacts of conversations or model reasoning.

## Observation

The AI stack is currently separating into several distinct capabilities.

A useful abstraction is:

```text
Retrieval  → What information matters?
Generation → How should it be expressed?
Decision   → What should be selected or done?
```

Historically, large language models often bundled all three into one generation call.

However, these concerns do not need to remain coupled.

Memory Seed can benefit from separating them.

## Why Decisions Matter

A decision has properties that ordinary generated text does not necessarily have.

It can be:

- identified;
- timestamped;
- linked;
- superseded;
- justified;
- reviewed;
- accepted;
- rejected;
- compared;
- audited;
- reproduced;
- governed.

This makes decisions particularly useful as durable knowledge objects.

## Decision Record as an External Contract

Model internals are changing rapidly.

Modern models may:

- hide chain-of-thought;
- compress internal reasoning;
- pass hidden reasoning state internally;
- use proprietary latent reasoning;
- change reasoning architecture entirely.

Therefore Memory Seed should not depend on access to internal reasoning traces.

Instead, the stable contract should be the externally observable decision.

Example:

```yaml
decision:
  id: D055
  statement: Use a persistent local decision worker.
  reasons:
    - avoids repeated model loading
    - keeps task inference stateless
  alternatives:
    - process-per-task
    - multiple parallel workers
  evidence:
    - measured warm latency
    - memory consumption
  relationships:
    - evolves_from: D041
```

This remains meaningful regardless of the model that produced it.

## Governance Value

The decision record creates an auditable boundary between:

```text
opaque model reasoning
        ↓
explicit proposal/decision
        ↓
human/system acceptance
        ↓
persistent project state
```

Memory Seed therefore does not need to know every hidden thought that produced a decision.

It needs to know:

- what was decided;
- why;
- what alternatives mattered;
- what evidence supported it;
- what it changed;
- what later superseded it.

## Industry-Change Resilience

Model providers, agent frameworks and harnesses are likely to change frequently.

A decision-centric architecture reduces coupling to those changes.

For example:

```text
2026:
Jev / Laya / frontier LLM

2027:
new decision architecture

2028:
latent agent systems
```

If each implementation produces the same decision contract, Memory Seed can replace the underlying model without replacing the knowledge system.


## Why This Boundary Becomes More Valuable as Reasoning Becomes Hidden

The architectural value of the decision record increases if model providers stop exposing intermediate reasoning and instead pass latent or hidden reasoning state internally. Memory Seed should not attempt to preserve private chain-of-thought as the durable memory format.

A more robust boundary is:

```text
opaque/latent reasoning
        ↓
explicit decision
        ↓
reason / evidence / alternatives
        ↓
accepted project state
```

This boundary is relatively immune to changes in model architecture. A future model may reason in a completely different way, but it can still be required to externalize the decision that affects project state.

## Emerging Three-Layer Pattern

A useful industry-level framing for Memory Seed is:

```text
Retrieval → assemble relevant state
Decision  → select/classify/route
Generation → explain or communicate
```

Memory systems and context engineering currently receive much of the attention because agents need reliable retrieval. The decision layer is less mature, but typed decision systems such as Jev and Laya suggest that decision-making can become an explicit, measurable interface rather than remaining hidden inside generation.

Memory Seed should treat this as an architectural hypothesis to test, not as a dependency on any particular vendor/model.

## Decision Layer as an Interface

Suggested conceptual API:

```text
state + typed question
        ↓
decision engine
        ↓
decision + probability
```

The engine could be:

- logistic regression;
- XGBoost;
- SetFit;
- Laya;
- Jev;
- an LLM;
- a future architecture.

The rest of Memory Seed should not care.

## Retrieval and Decisions

Retrieval should provide evidence to the decision layer.

Example:

```text
query/task
   ↓
hybrid retrieval
   ↓
candidate evidence
   ↓
decision layer
   ↓
classification / action / relationship
```

The decision layer should not replace retrieval.

It answers a different question.

## Generation and Decisions

Generation should primarily be used for:

- explanations;
- summaries;
- proposals;
- narrative synthesis;
- human-facing output.

A classifier can decide:

```text
relationship = supersedes
```

A generator can then explain:

```text
D55 supersedes D41 because...
```

Keeping these functions separate makes the system easier to test.

## Implication for Memory Seed

Memory Seed can become a decision-management and decision-memory layer rather than merely an AI memory system.

Potential conceptual hierarchy:

```text
Constitution
    ↓
Important Decisions / ADRs
    ↓
Operational Decisions
    ↓
Evidence / Entries / Conversations / Code
```

The durable object is the decision.

Raw conversations and tool outputs become evidence from which decisions are extracted and validated.

## Recommendation

Preserve and strengthen the decision object as a stable system boundary.

Do not make Memory Seed dependent on:

- exposed chain-of-thought;
- one agent framework;
- one LLM provider;
- one decision model;
- one retrieval implementation.

Instead, make the durable contract:

```text
Evidence
   ↓
Decision
   ↓
Relationships
   ↓
Evolution
   ↓
Governance
```
