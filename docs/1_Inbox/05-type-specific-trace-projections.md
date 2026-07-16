# Initial Proposal: Type-Specific Memory Trace Projections

**Status:** Exploration candidate  
**Promotion state:** Not ready for `todo`  
**Related systems:** Memory Trace, typed entries, topics, ADR sidecars, search

> [!IMPORTANT]
> **Exploration status:** This is an initial proposal, not an approved implementation plan.  
> It must be researched, stress-tested against the current Memory Seed architecture, and reviewed before any part is promoted into `docs/todo/` or implementation tickets.


## 1. Summary

This proposal explores whether Memory Trace should present different entry types through purpose-built projections rather than one uniform document view.

The core hypothesis is:

> Entry type should affect how information is surfaced, filtered, summarised, and navigated in Trace.

The proposal does not require completely separate pages for every type. It explores whether a small set of projections can make typed entries visibly useful to humans.

## 2. Problem

Mandatory entry types improve the data model, but users receive limited benefit if Trace renders every entry identically.

Different records answer different questions:

- session logs show what happened
- findings show what was discovered
- research-planning entries show what was investigated or proposed
- handoffs show what another session needs to continue
- ADRs show what governs the system
- decision updates show how an ADR evolved

A uniform chronological list may conceal these distinctions.

## 3. Proposed Projection Set

### 3.1 Session Trail

Primary source: `session-log`

Potential features:

- chronological ordering
- author and session grouping
- files and artifacts touched
- next steps
- links to decisions and findings produced
- search that scrolls to exact entry anchors

### 3.2 Decision View

Primary sources:

- ADR sidecars
- `architecture-decision`
- `decision-update`

Potential features:

- current accepted decisions
- proposed decisions
- topic filtering
- transition timeline
- source decision deep link
- supersession chain
- implementation and verification links

### 3.3 Findings View

Primary source: `finding`

Potential features:

- verified and unverified findings
- supporting evidence
- contradictions
- affected topics and components
- downstream decisions informed by the finding

Verification status is not yet part of the agreed type proposal and requires exploration.

### 3.4 Research and Planning View

Primary source: `research-planning`

Potential features:

- research question
- conclusions
- recommendations
- proposal status if externally represented
- linked findings and ADRs
- resulting tickets or workstreams

This projection must avoid becoming a replacement issue tracker.

### 3.5 Handoff View

Primary source: `handoff`

Potential features:

- current state
- completed work
- unresolved questions
- next recommended action
- required files and entries
- whether another session continued the handoff

## 4. Cross-Type Navigation

The greatest value may come from moving between projections.

Example:

```text
Session Trail
    ↓ produced
Finding
    ↓ informed
ADR
    ↓ governed
Implementation session
    ↓ produced
Commit
```

Trace should preserve one underlying relationship model while offering different views over it.

## 5. Shared Interface Elements

Potential shared elements include:

- topic filters
- author filters
- date ranges
- entry-type filters
- exact anchor links
- relationship panels
- evidence appendix
- source file inspector
- active versus historical state indicators

Shared primitives should reduce duplication between projections.

## 6. Pull-Forward Behaviour

Some entries should remain historically located but contextually persistent.

Examples:

- accepted ADRs appear when viewing affected topics
- unresolved handoffs appear when resuming a workstream
- verified findings appear alongside decisions they support
- current research-planning entries appear in active work views

This is projection behaviour, not movement or duplication of source entries.

## 7. Potential User Value

- clearer distinction between authoritative, supporting, and chronological memory
- faster project orientation
- better decision review
- easier resumption of interrupted work
- more useful search results
- stronger rationale for mandatory entry typing

## 8. Risks

### UI fragmentation

Too many specialised views could make Trace harder to learn.

**Mitigation:** begin with a small number of tabs or filters built on shared components.

### Premature projection design

The type schemas may change before the UI is validated.

**Mitigation:** prototype with static data and defer production implementation.

### Sparse data

Early projects may contain few typed entries.

**Mitigation:** ensure the trail remains useful even when specialised views are empty.

### Type misuse

Incorrect entry typing would produce misleading projections.

**Mitigation:** improve validation and creation workflows before relying on type heavily in UI.

### Duplicate information

The same entry may appear in several views.

**Mitigation:** treat projections as different lenses over one source record and preserve clear deep links.

## 9. Questions Requiring Further Exploration

1. Which projections deserve dedicated tabs?
2. Which should be filters or panels within the trail?
3. Should accepted ADRs appear globally or only by topic?
4. How should empty or sparse projections behave?
5. What information should be summarised versus loaded from source?
6. How should Trace distinguish current and historical information?
7. How should exact decision anchors be represented visually?
8. Which projections are free versus potential premium features?
9. How should mobile and desktop layouts differ?
10. Can the current Trace architecture support these views without major restructuring?

## 10. Required Exploration Before Promotion

Before promotion to `todo`, complete:

- audit of current Memory Trace information architecture
- low-fidelity designs for all five projections
- evaluation using realistic typed-entry fixtures
- user journey testing for project orientation and decision review
- component reuse analysis
- sparse-data and empty-state design
- search and deep-link behaviour
- performance assessment for aggregated ADR and relationship views
- prioritisation of one initial projection

## 11. Promotion Gate

Promote only if:

1. At least one type-specific projection materially improves a real user task.
2. The design can reuse common Trace primitives.
3. The UI does not require a separate complex page for every type.
4. Typed-entry data is sufficiently reliable to drive the view.
5. A staged implementation order is agreed.

## 12. Initial Recommendation

Explore all projections, but expect only one or two to be promoted first.

The ADR decision view and improved session trail are the strongest initial candidates. Production work should wait until the typed-entry and ADR data contracts are stable.
