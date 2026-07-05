---
memory-system-version: 2.15
tags:
  - memory-seed
  - proposal
  - memory-trail
  - naming
  - memory-explorer
---

# Memory Trail Renaming Plan

> **Status:** ACTIVE - scoped naming proposal, created 2026-07-05.
> **Priority:** P2 companion to
> [`memory-seed-explorer-distribution-plan.md`](memory-seed-explorer-distribution-plan.md). Decide and
> apply the naming transition before the separate UI distribution becomes a public package.
> **Source:** User decision 2026-07-05: rename the Explorer/Lense workstream to **Memory Trail**.
> Prior naming discussion favored traceability-oriented names over generic browsing names; "Trail"
> keeps the traceability cue while feeling shorter and more approachable than "Explorer".
> **Scope:** User-facing product naming, package/command naming recommendations, docs copy, and
> deprecation/alias handling for the existing `lense` and Explorer names.
> **Non-goals:** No immediate code rename in this proposal. No rename of the core `memory-seed`
> control-plane package. No guarantee of trademark/domain availability without a later availability
> check. No change to retrieval, graph, cache, or UI behavior.
> **Dependencies:** The separate-distribution plan and the entry-level UI result plan remain the
> implementation drivers. This proposal names that UI product line.
> **Acceptance criteria:** see below.

## Decision

Use **Memory Trail** as the product name for the read-only UI currently described as Memory Explorer
and prototyped as Memory Lense.

Recommended naming shape:

- Product/UI name: **Memory Trail**.
- Python distribution candidate: `memory-seed-trail`.
- Console command candidate: `memory-seed-trail`.
- Transitional docs language: "Memory Trail, formerly Memory Lense / Memory Explorer."
- Legacy compatibility: keep `memory-seed lense` as a deprecated alias during the same deprecation
  window already planned for `memory-seed[lense]`.

The exact package name should be checked against PyPI and trademark/domain availability before
publication. If `memory-seed-trail` is unavailable or legally risky, keep Memory Trail as the product
name and choose the nearest unambiguous package name, such as `memory-trail` or
`memoryseed-trail`.

## Rationale

"Explorer" describes browsing, but the intended audience is increasingly premium and
traceability-focused: people and teams who need to understand where a decision came from, how it
evolved, and which entries support it. "Trail" better matches that job:

- It suggests a navigable evidence path through sessions, decisions, graph links, commits, and
  supersession history.
- It is shorter than "Explorer" and easier to say in product copy.
- It avoids over-promising full observability or audit-log guarantees that "Trace" or "Ledger" might
  imply before the product has stronger compliance features.
- It connects naturally to the entry-level UI result model: users follow a trail of entries, with
  subsection matches highlighted inside the entry rather than presented as separate objects.

The name also fits the UI source-learning guidance already captured in
[`designing-user-interfaces-source-learnings.md`](../inbox/designing-user-interfaces-source-learnings.md):
clear hierarchy, direct navigation, consistent component language, and microcopy that names the
user's task instead of exposing implementation details.

## Proposed Transition

### Phase 0 - Availability Check

Before any release-facing rename:

- check PyPI availability for `memory-seed-trail`, `memory-trail`, and `memoryseed-trail`;
- do a light trademark/domain search for "Memory Trail" in developer tools, knowledge management,
  audit, and note-taking categories;
- confirm no existing Memory Seed docs depend on "Explorer" as a durable architecture term rather
  than a temporary workstream label.

### Phase 1 - Docs Rename

Update roadmap and proposal docs so the canonical product workstream reads as Memory Trail, while
retaining historical notes where useful:

- Rename or retitle the separate-distribution plan once the package naming is confirmed.
- Replace forward-looking "Explorer" UI wording with "Memory Trail".
- Keep "Memory Lense" only for the shipped in-package V1 / legacy command.
- Add a short glossary note: Lense = shipped prototype/legacy alias; Memory Trail = future companion
  UI product.

### Phase 2 - Package / Command Rename

When extracting the separate distribution:

- publish the companion UI package under the chosen Trail package name if available;
- expose the chosen Trail console command;
- keep `memory-seed lense` and any `memory-seed-explorer` references as transitional aliases only if
  they have already shipped publicly;
- print deprecation copy that points users to Memory Trail and the new install command.

## Non-Goals

- Do not rename the core package from `memory-seed`.
- Do not turn Memory Trail into a write/curation product in this naming pass.
- Do not remove `memory-seed lense` without a deprecation window.
- Do not use the rename to reopen the separate-distribution decision.
- Do not expose raw chunk/section implementation terms in user-facing naming or navigation.

## Dependencies

- [`memory-seed-explorer-distribution-plan.md`](memory-seed-explorer-distribution-plan.md): package
  split and deprecation-window mechanics.
- [`memory-explorer-entry-level-ui-results-plan.md`](memory-explorer-entry-level-ui-results-plan.md):
  user-facing object model for search, graph, timeline, and reader results.
- [`../inbox/designing-user-interfaces-source-learnings.md`](../inbox/designing-user-interfaces-source-learnings.md):
  UI naming and hierarchy principles.

## Acceptance Criteria

- One canonical product name is used in forward-looking UI/package docs: **Memory Trail**.
- The chosen package and command names are checked for availability before publication.
- Legacy `lense` naming remains as an alias/deprecation path for existing users.
- Docs distinguish shipped Memory Lense V1 from the future Memory Trail package.
- The rename does not change retrieval contracts, graph semantics, cache location, or read-only scope.
- Normal UI copy avoids internal implementation terms such as "section chunk".

## Provenance

- User naming decision, 2026-07-05.
- Companion distribution plan:
  [`memory-seed-explorer-distribution-plan.md`](memory-seed-explorer-distribution-plan.md).
- Entry-level result proposal:
  [`memory-explorer-entry-level-ui-results-plan.md`](memory-explorer-entry-level-ui-results-plan.md).
- UI design source learnings:
  [`designing-user-interfaces-source-learnings.md`](../inbox/designing-user-interfaces-source-learnings.md).
