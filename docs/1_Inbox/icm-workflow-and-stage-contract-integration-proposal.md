---
status: inbox
priority: P1
source: Gagiste ICM field prototype and MSI-022/MSI-024
scope: opt-in ICM workflow scaffolding and a Task Dispatch stage-contract adapter
non_goals:
  - implementing MSI-022 or MSI-024 before JNL approval
  - making ICM a Memory Seed runtime dependency
  - moving durable decisions, session memory, policy, or repository controls into workflow stages
  - granting a stage contract write authority that its source plan or Task Dispatch does not already grant
dependencies:
  - Task Dispatch v2 explicit read_inputs and do_not_load contract from MSI-023
  - existing task-packet compile, render, and from-plan surfaces
  - accepted ownership, routing, and deterministic-composition decisions
acceptance_criteria:
  - JNL selects or rejects the proposed scaffold and adapter contracts
  - any approved implementation begins with collision, compatibility, authority, and round-trip tests
  - generated workflow files are project-owned after creation and never silently overwritten
  - stage-contract conversion preserves exact read scope and never expands write scope
next_action: JNL reviews the decisions and trial gate before promotion to docs/2_Todo
---

# Proposal: ICM Workflow And Stage-Contract Integration

## Status

This is the MSI-022/MSI-024 design record requested after the Gagiste ICM prototype. It is a proposal,
not an implementation plan or an accepted contract. No CLI, schema, seed, or hook behavior changes are
authorized by this document.

## Recommendation

Adopt ICM as an optional, project-owned workflow layer and add one loss-aware adapter at Memory Seed's
existing Task Dispatch boundary:

1. `memory-seed init --workflow icm` creates a generic workflow scaffold only when the destination paths
   are absent.
2. `memory-seed task-packet render --format stage-contract` renders a validated Task Dispatch v2 as a
   human-readable stage contract.
3. `memory-seed task-packet from-plan --stage-contract PATH` may use a stage contract to supply missing
   read-scope and presentation defaults, but the implementation plan remains authoritative for objective,
   edit ownership, dependencies, verification, acceptance, and replan conditions.

The adapter composes two existing ownership domains. It does not merge them: ICM owns project workflow
instructions; Memory Seed owns deterministic packets, repository controls, durable memory, and integration.

## Evidence And Authority

### Field evidence

The Gagiste prototype uses a root `CONTEXT.md`, a workflow-level `CONTEXT.md`, and five stage-local
`CONTEXT.md` files. Each stage declares working inputs, reference inputs, exclusions, a process, outputs,
and checks. Status is derived from checks, while product artifacts stay in their canonical product paths.
A small link checker validates Markdown links, frontmatter references, imports, and backticked inputs.

That prototype exposed two reusable gaps:

- Memory Seed cannot scaffold the workflow shape without a project copying the prototype manually
  (MSI-022).
- Task Packet rendering cannot emit the stage-contract form, and `from-plan` cannot consume one as
  bounded defaults (MSI-024).

### Governing decisions

| Authority | Consequence for this proposal |
|---|---|
| Constitution `ownership`, `single-source`, `markdown-authority` | Every fact has one canonical owner; generated workflow prose cannot become a second decision or policy store. |
| Constitution `minimal-context`, `path-of-least-resistance` | The stage view should expose exactly the inputs needed for the stage and be easier than manually translating a packet. |
| Constitution `prove-automation`, `integration-mode` | Automation must be proven by fixtures and checks; the adapter cannot bypass repository integration controls. |
| Accepted outcome-level composition ADR | Deterministic conversion may compose automatically, but ambiguity, authority conflicts, and overwrite risk must stop. |
| Accepted skill-registry ADR | Workflow stages may reference skills through the existing deterministic registry; the scaffold must not introduce a parallel trigger registry. |
| Accepted foreign-file routing ADR | Existing project-owned files are preserved; scaffold creation refuses collisions rather than replacing or marker-editing them. |
| Accepted collaboration-ownership ADR | ICM stage instructions do not replace Memory Seed's worktree, packet, consent, or integration safeguards. |
| MSI-023 Task Dispatch v2 decision (`mse_7da2dwpntn4arc3r:d1`) | `read_inputs.working`, `read_inputs.reference`, and `do_not_load` are the canonical machine-readable source for stage input scope. Dispatch v1 remains unchanged. |

## Ownership Model

| Concern | Canonical owner | Adapter rule |
|---|---|---|
| Durable decisions, session history, policy, Constitution | Memory Seed | Link to them; never copy their normative text into stage contracts. |
| Write authority, validation commands, acceptance, packet identity | Task Dispatch / Task Packet | Render exactly; ingestion cannot broaden them. |
| Workflow sequence and project-specific stage instructions | Project-owned ICM files | Scaffold once, then leave unmanaged. |
| Product stories, features, meetings, and implementation artifacts | Existing product paths | Stages reference these files; they do not relocate or duplicate them. |
| Skill triggers | `.memory-seed/skills/index.md` plus local overlay | Stage prose names outcomes or registered skills, never a second trigger map. |

This preserves the prototype's strongest property: workflow stages describe how work moves, while the work
and its authority stay in their established homes.

## MSI-022: Opt-In Workflow Scaffold

### Proposed CLI

```text
memory-seed init --workflow icm
```

The option is explicit and additive. Plain `memory-seed init` remains unchanged. The first proposed pack
contains:

```text
CONTEXT.md
workflow/
  CONTEXT.md
  01-discovery/CONTEXT.md
  02-formulation/CONTEXT.md
  03-review/CONTEXT.md
  04-automation/CONTEXT.md
  05-change-control/CONTEXT.md
```

The numbered stages are a generic default pack derived from the field trial, not a new universal law.
A later proposal may define named packs or a project-supplied manifest after at least two projects show a
need. The initial implementation should avoid a pack registry, plugin interface, or workflow engine.

### Generated content contract

- Root `CONTEXT.md` is a routing map: workflow work points to `workflow/`, product facts point to existing
  documentation, and durable decisions point to `.memory-seed/`.
- `workflow/CONTEXT.md` defines stage order, transition checks, and the one-home-per-fact rule.
- Each stage template contains: Purpose, Inputs (Working and Reference), Do Not Load, Process, Outputs,
  Check, and Handoff.
- A stage describes checks but does not maintain a separate status file. Passing checks derive readiness.
- Templates use relative Markdown links and portable commands. They contain no Gagiste-specific paths,
  personas, or product vocabulary.
- Generated files are project-owned immediately. They are not added to the managed-seed manifest and
  later `update` operations do not rewrite them.

### Collision and repeat behavior

The operation is atomic and fail-closed:

- preflight every destination before writing any file;
- if every expected file already exists and its bytes equal the template, report `unchanged`;
- if any destination exists with different bytes, write nothing and report every collision;
- never insert marker regions into an existing root or workflow file;
- expose the same result through CLI and library code so dry-run and tests share the implementation.

This deliberately favors a clear refusal over guessing whether a project file is replaceable.

### Validation

The scaffold reuses current documentation and repository checks where their contracts fit. The initial
slice should not vendor the Gagiste link checker into every project. Instead, add workflow-link coverage to
Memory Seed's existing link/doctor path, including the stage input forms the prototype proved useful. A
standalone exported checker is a separate decision if projects without Memory Seed need one.

## MSI-024: Stage-Contract Adapter

### Canonical stage-contract shape

The Markdown form is a view over validated data, with a small machine-readable header:

```yaml
---
schema: memory-seed/stage-contract
version: 1
source_schema: memory-seed/task-dispatch
source_version: 2
source_fingerprint: sha256:...
---
```

Required headings are `Objective`, `Working Inputs`, `Reference Inputs`, `Do Not Load`, `Allowed Writes`,
`Validation`, `Acceptance`, `Outputs`, and `Stop Conditions`. Paths are repository-relative canonical
paths. Empty lists are explicit rather than omitted.

### Render mapping

| Task Dispatch / Packet field | Stage-contract field |
|---|---|
| `objective` | Objective |
| `execution.read_inputs.working` | Working Inputs |
| `execution.read_inputs.reference` | Reference Inputs |
| `execution.do_not_load` | Do Not Load |
| `execution.allowed_files` | Allowed Writes |
| `execution.validation` | Validation |
| `execution.acceptance_observables` | Acceptance |
| `execution.output_contract` | Outputs and Stop Conditions, classified by their structured source when available |
| canonical dispatch fingerprint | `source_fingerprint` |

Rendering accepts only Dispatch v2 or a packet containing Dispatch v2. Dispatch v1 already states that
read scope is unspecified; producing a complete stage contract from it would invent authority. The command
therefore refuses v1 with a migration message instead of rendering misleading empty lists.

`--format prompt` remains the default and preserves current output. `--format stage-contract` is explicit.
When compiling from `--dispatch-file`, `--packet-out` retains its current meaning; the stage contract goes
to stdout unless a separately named output option is approved during implementation planning.

### From-plan ingestion

Proposed form:

```text
memory-seed task-packet from-plan \
  --plan-file PLAN.md \
  --stage-contract workflow/02-formulation/CONTEXT.md
```

The stage contract is a defaults source, not a second plan. The implementation plan remains authoritative
for task identity, objective, dependency order, edit ownership, verification, acceptance observables,
evidence references, and replan conditions.

Only these values may default from the contract when the plan-dispatch source does not express them:

- `execution.read_inputs.working`;
- `execution.read_inputs.reference`;
- `execution.do_not_load`;
- non-authoritative presentation lines appended to `output_contract`.

The first implementation should require one contract per invocation and apply it only when the plan has
one task. Multi-task plan mapping needs an explicit task-to-contract manifest and is deferred; positional
or filename inference would be fragile.

### Authority and conflict rules

1. The adapter normalizes all paths with the existing Task Dispatch canonicalizer.
2. A path may not appear in both a load list and `do_not_load`.
3. `Allowed Writes` from the stage contract is evidence for conflict checking only. It cannot add to the
   plan's `edit_ownership`; any mismatch is an error listing both sources.
4. Stage validation, acceptance, objective, and stop conditions must either match the plan-derived values
   or be omitted. They never override the plan.
5. Contract paths outside the discovered runtime fail closed.
6. Unknown headings are preserved as human prose only when they cannot be mistaken for authority;
   unknown frontmatter keys are rejected.
7. Conversion reports provenance for every accepted default and every ignored non-authoritative section.

### Identity and compatibility

- Existing plan-dispatch v1 input and output remain byte-for-byte compatible when no stage contract is
  supplied.
- Supplying a stage contract produces Task Dispatch v2 because explicit read scope is then present.
- The normalized Dispatch v2, not the Markdown bytes, determines packet identity and fingerprint.
- Rendering the same normalized dispatch is deterministic across platforms.
- Render -> parse -> normalize must reproduce the same dispatch authority fields. Human prose that has no
  dispatch representation is intentionally outside the round trip and is reported as such.
- CLI and MCP should call the same parser/renderer. New MCP parameters or tools follow only after the core
  contract passes the CLI fixtures.

## Rejected Alternatives

### Make stage contracts the primary execution schema

Rejected. Markdown stages are excellent project-facing instructions, but Task Dispatch already owns
canonical validation, packet identity, telemetry, and execution authority. Replacing it would duplicate
controls and weaken deterministic checks.

### Copy the complete Gagiste prototype into the seed

Rejected. Product-specific stages and a vendored checker would turn one field trial into universal policy.
The proposed scaffold extracts only the reusable structure and integrates validation with existing checks.

### Keep generated workflow files managed by `memory-seed update`

Rejected. Workflow prose is expected to evolve with the project. Silent updates would overwrite local
process knowledge or require another marker-management subsystem.

### Infer read scope from the implementation plan

Rejected for the same reason MSI-023 kept plan-generated dispatches on v1: edit ownership is not read
authority. The explicit stage contract is the source for those defaults.

### Merge contracts into multi-task plans by stage order

Rejected for the initial slice. Ordering is not identity; a named manifest is required before supporting
that case.

## Approval And Trial Gate

JNL approval is required on four decisions before implementation:

1. the five-stage default pack and `init --workflow icm` CLI shape;
2. project-owned, create-once lifecycle for generated workflow files;
3. Dispatch v2-only rendering and single-task-only initial ingestion;
4. the precedence rule that a stage contract may narrow or supply read scope but never expand plan-derived
   write authority.

If approved, implementation should be split into two independently reviewable tranches:

1. **MSI-022 scaffold:** collision tests first, then generic templates, init plumbing, and link/doctor
   validation. Trial in a temporary project and one Gagiste-shaped fixture.
2. **MSI-024 adapter:** parser and authority-conflict tests first, then deterministic render, single-task
   ingestion, CLI surfaces, MCP parity, and round-trip/property tests.

Promotion requires all focused tests, the full serial suite, docs/link/encoding checks, and an isolated
fresh-init/update smoke test. A real Gagiste trial should compare the generated generic scaffold and
rendered contract with the prototype without replacing its existing project-owned files.

## Acceptance For This Design Record

- The ownership boundary is explicit and no source of authority is duplicated.
- The proposed CLI, file lifecycle, schema mapping, precedence, conflicts, compatibility, and stop
  conditions are concrete enough to plan and test.
- Alternatives and deferrals are recorded.
- The document remains in Inbox until JNL accepts, revises, or rejects the proposal.

