# Proposal: Governed Interactive Retrieval for Memory Seed

**Status:** Proposal\
**Scope:** Retrieval contract, orchestration, evidence packets,
sidecars, MCP/CLI, Memory Trace

## Executive Summary

Memory Seed should treat a deterministic task packet as a **reproducible
bootstrap**, not as an agent's complete epistemic boundary.

The packet establishes the minimum governed context known to be relevant
before execution. During work, subagents should be able---and where
appropriate required---to re-query Memory Seed using terminology that
emerges from their own reasoning.

This changes the target from *every agent sees exactly the same
information* to:

> **Every agent begins from the same governed snapshot, can interrogate
> the same institutional memory, and leaves an inspectable trace of how
> its effective context expanded.**

The main residual risk is the **unknown unknown**: an agent may fail to
search because nothing in its current context reveals that an important
concept exists. The proposed control is a small set of configurable
**epistemic checkpoints** that trigger targeted retrieval before
consequential actions.

## 1. Core Retrieval Model

> **Memory Seed gives the agent what it knows the agent needs. The agent
> discovers what else it needs.**

``` mermaid
flowchart TD
    T[Task] --> P[Deterministic Bootstrap Packet]
    P --> C[Constitution]
    P --> D[Relevant Decisions]
    P --> A[Related ADRs]
    P --> E[Evidence and Neighbourhood]
    C --> R[Agent Reasoning]
    D --> R
    A --> R
    E --> R
    R --> G{Information Gap?}
    G -->|Yes| Q[Re-query Memory Seed]
    Q --> K[Keyword Search]
    Q --> S[Semantic Search]
    Q --> TP[Topic / Relationship Traversal]
    Q --> L[Direct Entry Lookup]
    K --> N[New Evidence]
    S --> N
    TP --> N
    L --> N
    N --> R
    G -->|No| X[Execute]
    X --> O[Output + Evidence Trail]
```

The initial packet remains conservative, bounded and deterministic.
Completeness is pursued through interaction rather than context-window
inflation.

## 2. Retrieval Is a Protocol, Not a Packet

The retrieval contract should describe the agent's relationship with
memory throughout the task:

1.  **Bootstrap** --- assemble deterministic starting context.
2.  **Inspect** --- establish understanding and constraints.
3.  **Identify gaps** --- detect ambiguity, missing knowledge, conflicts
    or assumptions.
4.  **Expand** --- query Memory Seed with task-specific terms.
5.  **Verify** --- check consequential conclusions against canonical
    entries.
6.  **Execute** --- perform the work.
7.  **Re-query** --- repeat when assumptions, dependencies or scope
    change.
8.  **Commit** --- record consequential decisions and evidence used.

``` mermaid
flowchart LR
    B[Bootstrap] --> I[Inspect]
    I --> G[Identify Gaps]
    G --> E[Expand Retrieval]
    E --> V[Verify]
    V --> X[Execute]
    X --> R{Changed Assumptions?}
    R -->|Yes| G
    R -->|No| C[Commit]
    C --> T[Decision + Evidence + Retrieval Trace]
```

The MCP therefore becomes a **governed memory interface**, not merely a
mechanism for injecting context before a task.

## 3. Bootstrap Context vs Effective Context

``` mermaid
flowchart TD
    B[Same Bootstrap] --> A1[Agent A]
    B --> A2[Agent B]
    A1 --> E1[Bootstrap Sufficient]
    A2 --> Q1[Search: Sidecar Promotion]
    Q1 --> Q2[Discover Related ADR]
    Q2 --> E2[Expanded Context]
    E1 --> O1[Implementation A]
    E2 --> O2[Implementation B]
```

``` text
Bootstrap Context
        +
Agent-Discovered Context
        =
Effective Task Context
```

Different effective contexts are not inherently a reproducibility
failure. Reproducibility should mean that the starting state is
reproducible and the later retrieval path is inspectable.

## 4. Residual Second-Order Risk: Unknown Unknowns

Re-querying handles:

> "I realise I need information about X."

It does not automatically handle:

> "A critical decision about Y exists, but nothing I have seen causes me
> to realise Y matters."

The preferred solution is not an ever-larger packet. It is **epistemic
checkpoints**: minimum searches triggered by consequential classes of
action.

``` yaml
retrieval_policy:
  before_implementation:
    - search_related_decisions
    - search_related_adrs

  when:
    new_dependency:
      - search_dependency_history

    architecture_change:
      - search_architecture_decisions
      - search_constitution

    conflicting_evidence:
      - expand_relationship_depth
      - search_supersession_chain

    modifying_existing_component:
      - search_component_history

  before_completion:
    - search_for_contradicting_decisions
    - verify_active_decisions
```

``` mermaid
flowchart TD
    A[Agent Working] --> P{Proposed Action}
    P -->|Architecture Change| AR[Search Architecture Decisions]
    P -->|New Dependency| DP[Search Dependency History]
    P -->|Modify Component| CH[Search Component History]
    P -->|Conflict| CF[Search Supersession Chain]
    P -->|Completion| VC[Contradiction + Active-State Check]
    AR --> M[Memory Seed]
    DP --> M
    CH --> M
    CF --> M
    VC --> M
    M --> E[Additional Evidence]
    E --> A
```

Checkpoints establish minimum epistemic behaviour while preserving
freedom for subagents to perform additional searches.

## 5. Proposed Architecture

``` mermaid
flowchart TD
    MT[Memory Trace - Human Interface] <--> MS[Memory Seed Core]
    MS --> BP[Bootstrap Packet - Deterministic]
    MS <--> RA[Retrieval API - Interactive]
    BP --> OR[Orchestrator]
    RA <--> OR
    OR --> A[Agent A]
    OR --> B[Agent B]
    OR --> C[Agent C]
    A <--> RA
    B <--> RA
    C <--> RA
    A --> TR[Retrieval + Evidence Trail]
    B --> TR
    C --> TR
    TR --> MS
    TR --> MT
```

### Responsibilities

**Memory Seed Core:** canonical decisions, ADRs, constitutional rules,
evidence, sidecars, active-state resolution and retrieval interfaces.

**Bootstrap Packet:** deterministic, task-declared, bounded,
reproducible and versioned.

**Retrieval API:** keyword and semantic search, topic and relationship
traversal, direct lookup, supersession inspection and evidence
retrieval.

**Orchestrator:** establishes retrieval policy, enforces epistemic
checkpoints and delegates work.

**Workers:** reason from bootstrap context, identify gaps, re-query
Memory Seed and verify consequential assumptions.

**Memory Trace:** exposes bootstrap context, discovered context and
evidence paths to humans through the same underlying memory state.

## 6. Revised Determinism Principle

> **Determinism applies to context assembly over a declared snapshot.
> Discovery remains interactive and may be probabilistic.**

A bootstrap packet should be reproducible given the same source
snapshot, retrieval-contract version, committed sidecar snapshot,
permissions, active-state resolver, context budget and configuration.

Later searches should be **traceable**, not forced to follow identical
paths.

## 7. Derived Views: Feedback-Loop Control

Derived topics, links and summaries can influence retrieval and then
reinforce themselves.

``` mermaid
flowchart LR
    S[Derived Sidecars] --> R[Retrieval]
    R --> E[Evidence Seen]
    E --> N[New Decisions / Sidecars]
    N --> S
```

Controls:

-   Only committed/versioned sidecars influence authoritative bootstrap
    retrieval.
-   Candidate sidecars remain visibly provisional.
-   Exploratory retrieval may use candidate semantic relationships, but
    labels them as derived.
-   Important results retain canonical source identifiers, not only
    generated summaries.
-   Periodic audits deliberately inspect low-centrality and rarely
    surfaced entries.

## 8. Knowledge Evolution

Interactive retrieval should resolve **current applicability**, not
simply return historical matches.

``` mermaid
flowchart LR
    H[Historical Decision] --> AS[Active-State Resolver]
    U[Updates / Supersession] --> AS
    C[Constitution Version] --> AS
    SC[Scope / Applicability] --> AS
    AS --> Q{Current State}
    Q --> A[Active]
    Q --> P[Partially Applicable]
    Q --> S[Superseded]
    Q --> D[Disputed]
```

An agent discovering a decision should be able to determine whether it
remains active, where it applies, whether later decisions qualify it,
and which governance state applies.

## 9. Human Authority and Evidence Paths

The same retrieval plumbing should serve humans and agents. Memory Trace
should expose:

-   the deterministic bootstrap packet;
-   subsequent consequential queries;
-   entries discovered;
-   evidence actually used;
-   conflicting evidence;
-   final decisions.

Human review then becomes inspection of the **reasoning and evidence
path**, rather than a ceremonial approval of the final output.

### Minimal retrieval trace

``` yaml
retrieval_trace:
  task_id: implement-topic-sidecars
  bootstrap_packet: sha256:...

  queries:
    - query: "sidecar canonical markdown separation"
      method: semantic
      results_used:
        - decision: abc123
        - adr: adr-017

    - query: "derived artifacts reproducibility"
      method: keyword
      results_used:
        - decision: def456

  verification:
    contradictions_checked: true
    active_state_checked: true

  evidence_used:
    - abc123
    - adr-017
    - def456
```

The trace should capture what materially influenced the result rather
than every low-level search operation.

## 10. Benchmark Proposal

``` mermaid
flowchart TD
    A[Condition A: Task] --> A1[Agent] --> A2[Result]
    B[Condition B: Task] --> B1[Static Packet] --> B2[Agent] --> B3[Result]
    C[Condition C: Task] --> C1[Packet] --> C2[Agent]
    C2 <--> C3[Memory Seed]
    C2 --> C4[Result]
    D[Condition D: Task] --> D1[Packet] --> D2[Agent]
    D3[Retrieval Policy + Checkpoints] --> D2
    D2 <--> D4[Memory Seed]
    D2 --> D5[Trace] --> D6[Result]
```

  Metric                            A: None   B: Static   C: Interactive   D: Governed
  ------------------------------- --------- ----------- ---------------- -------------
  Relevant decisions discovered                                          
  Relevant ADRs discovered                                               
  Contradictions discovered                                              
  Relevant evidence missed                                               
  Incorrect assumptions                                                  
  Policy violations                                                      
  Requeries performed                                                    
  Context/retrieval tokens                                               
  Task correctness                                                       
  Human correction required                                              
  Evidence coverage                                                      

The key comparison is **B vs C vs D**. It isolates the benefit of static
context injection, interactive retrieval, and governed interactive
retrieval.

## 11. Retrieval Contract Evolution

Bootstrap assembly remains explicit:

``` yaml
task:
  implement: topic-sidecars

retrieve:
  decisions:
    depth: 2
  topics:
    - session-fuse
    - topics
  evidence:
    latest
  constitutional_rules:
    required
  neighbouring_entries: 15
  related_adrs: true
```

Runtime behaviour becomes a separate concern:

``` yaml
runtime_retrieval:
  allow_requery: true
  record_trace: true

  methods:
    - keyword
    - semantic
    - topic
    - relationship
    - direct_lookup

  checkpoints:
    before_implementation:
      - related_decisions
      - related_adrs
    before_architecture_change:
      - architecture_decisions
      - constitution
    before_completion:
      - contradictions
      - active_state
```

`retrieve` defines **what should be known at task start**.\
`runtime_retrieval` defines **how the agent should interact with memory
during execution**.

## 12. Proposed Design Principles

1.  **Bootstrap, not boundary.** The deterministic packet is the minimum
    governed starting context, not a completeness claim.
2.  **Retrieval is continuous.** Agents query Memory Seed as new
    uncertainties and concepts emerge.
3.  **Determinism applies to assembly.** Bootstrap context is
    reproducible; exploratory search paths may differ.
4.  **Effective context is inspectable.** Bootstrap evidence and
    subsequently discovered evidence remain distinguishable.
5.  **Consequential actions require epistemic checks.** High-impact
    actions trigger targeted retrieval.
6.  **Search remains flexible.** Checkpoints define minimum behaviour
    without constraining additional agent searches.
7.  **Same plumbing for humans and agents.** Memory Trace, MCP, CLI,
    orchestrators and workers resolve from the same underlying state.
8.  **Evidence paths are first-class.** Outputs expose which evidence
    materially influenced them.

## 13. Critical Path

### Phase 1 --- Formalise the split

-   Define `retrieve` as bootstrap retrieval.
-   Define `runtime_retrieval` as task-time policy.
-   Define bootstrap packet identity/hash.
-   Define a minimal retrieval-trace schema.

### Phase 2 --- Expose interactive retrieval

-   Ensure workers can query Memory Seed through MCP during execution.
-   Support keyword, semantic, topic, relationship and direct-entry
    retrieval.
-   Resolve active/superseded state in results.

### Phase 3 --- Instrument

-   Record consequential worker queries.
-   Separate bootstrap evidence from discovered evidence.
-   Record which evidence materially influenced the result.

### Phase 4 --- Add epistemic checkpoints

Start with: - before implementation; - architecture change; - new
dependency; - component modification; - before completion.

Keep checkpoints configurable rather than hard-coded into individual
agents.

### Phase 5 --- Surface in Memory Trace

Show: - bootstrap context; - discovered context; - retrieval
chronology; - evidence used; - contradictions; - active-state changes.

### Phase 6 --- Benchmark

Run identical tasks under conditions A-D and measure correctness,
evidence coverage, missed decisions, contradictions, token cost and
human correction.

## 14. Success Criteria

The proposal succeeds if Memory Seed can demonstrate that:

1.  identical tasks start from identical governed context;
2.  agents can cheaply expand context when needed;
3.  interactive retrieval finds relevant information missed by bootstrap
    retrieval;
4.  consequential actions trigger appropriate verification;
5.  humans can reconstruct why particular evidence influenced an agent;
6.  retrieval overhead produces measurable improvements in correctness
    or evidence coverage;
7.  the protocol avoids solving uncertainty by simply flooding the
    context window.

## 15. Final Architectural Position

``` mermaid
flowchart TD
    T[Task] --> B[Deterministic Bootstrap]
    B --> R[Reason]
    R --> U{Uncertainty or Consequential Action?}
    U -->|Search Needed| M[Interrogate Memory Seed]
    M --> E[Expand Effective Context]
    E --> R
    U -->|Sufficiently Verified| X[Execute]
    X --> V[Final Verification]
    V --> O[Output]
    O --> TR[Evidence + Retrieval Trace]
```

> **Deterministic retrieval establishes where reasoning starts.
> Interactive retrieval determines how understanding grows. Governance
> ensures agents know when further retrieval is required, and provenance
> makes that growth inspectable by humans.**
