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

> **Status:** SUPERSEDED on 2026-07-05 by
> [`memory-trace-product-and-trail-view-plan.md`](memory-trace-product-and-trail-view-plan.md).
> The package/product name moves to **Memory Trace**; **Memory Trail** remains as the internal Trace
> feature/view for branch and supersession evolution. This file is retained as provenance for the
> Trail-only naming check and competitor-risk finding.

> **Prior status before supersession:** scoped naming proposal, created 2026-07-05. **Phase 0 availability check ran
> 2026-07-05 and found a problem:** `memory-seed-trail` is free on PyPI, but "Memory Trail" is
> already an active same-niche product (`memory-trail` on PyPI + LobeHub) - see "Phase 0 findings"
> below. Phase 1 (docs rename) was paused pending the user's naming call; the distribution plan's
> retrieval-service work continued under a temporary package placeholder until `memory-trace` was selected.
> **Priority:** P2 companion to
> [`../memory-trace-distribution-plan.md`](../memory-trace-distribution-plan.md). Decide and
> apply the naming transition before the separate UI distribution becomes a public package.
> **Source:** User decisions 2026-07-05: rename the Explorer/Lense workstream to **Memory Trail**;
> use `memory-seed-trail` as the target package/command unless availability checks show a problem;
> run a light PyPI + web/trademark sanity check before release-facing package rename/extraction.
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
- Python distribution target: `memory-seed-trail`, unless availability checks show a problem.
- Console command target: `memory-seed-trail`, unless availability checks show a problem.
- Transitional docs language: "Memory Trail, formerly Memory Lense / Memory Explorer."
- Legacy compatibility: keep `memory-seed lense` as a deprecated alias for at least one release during
  the same deprecation window already planned for `memory-seed[lense]`.

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
[`designing-user-interfaces-source-learnings.md`](../../4_Reference/designing-user-interfaces-source-learnings.md):
clear hierarchy, direct navigation, consistent component language, and microcopy that names the
user's task instead of exposing implementation details.

## Proposed Transition

### Phase 0 - Availability Check

Before any release-facing rename or package extraction:

- check PyPI availability for `memory-seed-trail`, `memory-trail`, and `memoryseed-trail`;
- do a light trademark/domain search for "Memory Trail" in developer tools, knowledge management,
  audit, and note-taking categories;
- confirm no existing Memory Seed docs depend on "Explorer" as a durable architecture term rather
  than a temporary workstream label.

#### Phase 0 findings (checked 2026-07-05)

PyPI (HTTP status of `https://pypi.org/pypi/<name>/json`; 404 = unregistered):

| Name | Status |
|---|---|
| `memory-seed-trail` | **available** (404) |
| `memoryseed-trail` | **available** (404) |
| `memory-seed-explorer` (current placeholder) | **available** (404) |
| `memory-trail` | **TAKEN** (200, v0.0.1) |

**Material naming-risk finding, beyond package availability:** the existing `memory-trail` name is
not a squatter or an unrelated tool - the same-niche positioning ("decision memory and session
logging for AI-assisted development - track architectural decisions across sessions") overlaps
Memory Seed's own product space, not merely its candidate name.

**Refined 2026-07-05** by [`memory-trail-competitor-analysis.md`](../../4_Reference/memory-trail-competitor-analysis.md)
(full evaluation): the PyPI package itself is an inert placeholder (`log()`/`recall()` both raise
`NotImplementedError`; CLI prints "Coming Soon") reserving a name inside a different product line
(Clarity Gate). The actual functioning artifact is a **separate GitHub repo**
(`frmoretto/memory-trail`) distributed as a markdown-only "Skill" - no package, server, CLI,
retrieval, or validator; just templates and instructions an agent follows by hand. Adoption is low
(3 GitHub stars, 0 forks, 2 marketplace installs) but the repo is not dead (pushed 2026-04-04). Net:
**functional-collision risk is close to zero**; **positioning/brand-collision risk is real** (same
tagline shape, same target audience) and is the actual thing to weigh.

Implications (recorded, not decided - the naming call stays with the user):

- The *package* `memory-seed-trail` is technically claimable, and would not collide with any
  installable software - nothing on PyPI under any variant of this name currently does anything.
  The risk is discoverability/first-impression overlap in search results and marketplace listings,
  not a functioning competitor.
- The plan's own fallback suggestion of `memory-trail` as an alternative package name is still void
  in the narrow sense that the exact name is registered (inert) - but choosing it would not create a
  software conflict, only a naming one.
- Options to weigh: (a) keep the Memory Trail name anyway (shared-prefix `memory-seed-trail`
  differentiates the package; the competing project has no software to be confused with, only a
  similar pitch); (b) pick a different trail-adjacent name and re-run this check; (c) stay with the
  "Explorer" working name (`memory-seed-explorer` is available) until a name clears the check.
- Decision needed before Phase 1 (docs rename) proceeds; the distribution plan's Phase 1 (retrieval
  service) is unaffected and can proceed under the existing placeholder.

Sources: [PyPI memory-trail](https://pypi.org/project/memory-trail/),
[LobeHub memory-trail skill](https://lobehub.com/skills/frmoretto-memory-trail).

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

- publish the companion UI package as `memory-seed-trail` if available;
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

- [`../memory-trace-distribution-plan.md`](../memory-trace-distribution-plan.md): package
  split and deprecation-window mechanics.
- [`memory-explorer-entry-level-ui-results-plan.md`](memory-explorer-entry-level-ui-results-plan.md):
  user-facing object model for search, graph, timeline, and reader results.
- [`../../4_Reference/designing-user-interfaces-source-learnings.md`](../../4_Reference/designing-user-interfaces-source-learnings.md):
  UI naming and hierarchy principles.

## Acceptance Criteria

- One canonical product name is used in forward-looking UI/package docs: **Memory Trail**.
- `memory-seed-trail` is used as the target package/command unless PyPI, trademark, or domain checks
  show a problem.
- The chosen package and command names are checked for availability before release-facing extraction.
- Legacy `lense` naming remains as an alias/deprecation path for existing users for at least one
  release.
- Docs distinguish shipped Memory Lense V1 from the future Memory Trail package.
- The rename does not change retrieval contracts, graph semantics, cache location, or read-only scope.
- Normal UI copy avoids internal implementation terms such as "section chunk".

## Provenance

- User naming decision, 2026-07-05.
- Companion distribution plan:
  [`../memory-trace-distribution-plan.md`](../memory-trace-distribution-plan.md).
- Entry-level result proposal:
  [`memory-explorer-entry-level-ui-results-plan.md`](memory-explorer-entry-level-ui-results-plan.md).
- UI design source learnings:
  [`designing-user-interfaces-source-learnings.md`](../../4_Reference/designing-user-interfaces-source-learnings.md).
