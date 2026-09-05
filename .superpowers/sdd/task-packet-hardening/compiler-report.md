# Task Packet compiler hardening report

Status: **DONE**

## Git receipt

- Base SHA: `84bc7fb64c21e16a530911b177a705cc3a3b4fa9`
- Final implementation HEAD: `764dee933f79b7c677499a752f2f0eec9583450d`
- Implementation commits:
  - `348cc4dafdd4f4965b178903c5a5a6f4ed87a25c` — Harden Task Packet compiler contracts
  - `764dee933f79b7c677499a752f2f0eec9583450d` — Verify Task Packet execution receipts
- This report is the final receipt artifact and is committed after it is written; its commit SHA is necessarily recorded in the handoff rather than self-referentially in this file.

Changed files:

- `memory_seed/task_packet.py`
- `memory_seed/retrieval.py`
- `memory_seed/retrieval_spec.py`
- `memory_seed/retrieval_profiles.py`
- `tests/test_task_packet.py`
- `tests/test_task_packet_surfaces.py`
- `tests/test_retrieval_spec.py`
- `tests/test_retrieval_spec_resolver.py`
- `tests/test_task_packet_pilot.py`
- `tests/fixtures/task_packet_pilot/dispatch.json`
- `.memory-seed/sessions/2026-09/2026-09-05.md` (authorized first-hand worker checkpoint)
- `.superpowers/sdd/task-packet-hardening/compiler-report.md`

## Phase 1 requirement evidence

| Requirement | Implementation and test evidence |
| --- | --- |
| Project complete relevant Constitution clauses by stable anchors, with ordered selection and explicit full fallback | `project_constitution()` performs dispatch refs → selected ADR bindings → ranked clauses, or supplies the complete document. `test_constitution_projection_prefers_explicit_anchors_and_never_truncates` and `test_constitution_projection_uses_adr_refs_then_explicit_full_fallback` cover the paths. |
| Preserve clause path/version/heading/ranges/digests/reason/full reference; do not silently truncate | Each projected clause carries those fields and complete content; fallback carries the complete document and explicit reason. Tests assert stable projection metadata and contents. |
| Exact paths by default; F metadata only by explicit opt-in | `selectors.path_references` is normalized as false by default and gates session `F:` matching. `test_v2_path_references_are_an_explicit_opt_in_selector` and `test_path_metadata_references_require_explicit_v2_opt_in` cover default refusal and opt-in. |
| Component token and percentage measurements, while retaining tier budgets and Constitution targets | The unchanged economy/balanced/frontier bands now produce fixed-width component percentage measurements; projection targets are 2k/4k/8k and overages are explicit. Boundary tests and `test_component_measurements_are_complete_and_fingerprinted` pass. |
| `expected_absent`, directly testable `acceptance_observables`, and exact `implements` | Execution validation requires exact creation paths within the allowlist, named command/expected-exit observables, and canonical decision refs resolved in selected evidence. `test_execution_contracts_validate_creation_acceptance_and_implementation` covers positive and negative cases. |
| Worktree-safe execution/report receipts and scope blockers | Default preflight begins with an absolute `Set-Location`, verifies top-level and branch, records the escalated-shell context, names base/final/all-commit handoff receipts, and gives the allowlist scope-blocker comparison. The execution-contract test asserts this. |
| CLI/MCP parity and clean-context regression coverage | `tests/test_task_packet_surfaces.py` and `tests/test_task_packet_pilot.py` pass alongside the compiler tests. |

## Validation

Commands and outcomes:

1. `python -X utf8 -m memory_seed.cli worktree guard --agent codex --write-intent` — passed: owned worktree, correct branch, clean at base.
2. `python -X utf8 -m pytest -q tests/test_task_packet.py tests/test_task_packet_surfaces.py tests/test_retrieval_spec.py tests/test_retrieval_spec_resolver.py tests/test_task_packet_pilot.py` — **58 passed, 100 subtests passed** (50.95s).
3. `git diff --check` — passed before each implementation commit.

The literal `memory-seed worktree guard` preflight initially resolved a foreign global installation and correctly refused to attest the checkout. The checkout-local module invocation above passed and is the valid evidence.

## Concerns

- Existing dispatch producers must add the now-explicit execution contracts. Profiles that intentionally select session entries through `F:` metadata must set `selectors.path_references: true`; exact-path defaults otherwise prevent that widening.
- The report receipt commit follows this report. Its SHA is in the final handoff, because embedding a commit's own SHA in the content it hashes is not possible.

## Task Packet reflection

Expected context was a bounded compiler task, a materialized Constitution/ADR/decision evidence pack, execution binding, and the approved Phase 1 plan. Received context matched that expectation: the packet supplied all governing evidence, exact worktree/base binding, the plan pointer, allowlist, validations, and a session-checkpoint authorization.

Evidence actually used was the materialized Task Packet evidence (including Constitution-anchor form and ADR bindings), the explicitly referenced approved plan, and direct inspection of owned compiler/resolver/surface code and tests. No supplemental Memory Seed governance or history was fetched. The only additional read was CLI help to invoke the authorized checkpoint correctly; this is an execution-interface lookup, not a governance hop. The checkpoint append itself is first-hand evidence and is recorded in the allowed session file.

Authority fidelity was maintained: every changed file is in the packet allowlist; forbidden plan, Constitution, provenance, Seed Pod, policy, core, and hook files were untouched. The worktree command context was explicit; no network call, packet-registry write, worktree creation, release, push, merge, or provenance implementation occurred.

The packet was effective enough to complete the work without a blocker. Its full Constitution payload was intentionally more than the worker needed, and that excess directly demonstrated the hardening target. The approved plan defined the required semantics but not the concrete JSON shapes for `constitution_refs`, `selectors.path_references`, or `acceptance_observables`; the implementation selected small, strict, deterministic schemas and pinned them with focused tests. A future compiler packet would be more implementation-ready if it materialized field-schema examples or acceptance vectors for new contracts, while retaining the current governing evidence and scope precision.

## Fix round 1 — independent review response

Status: **DONE**

- Fix base: `148887984021e5ca4930ba30498c528a85fdd645`
- Final implementation HEAD: `e05156a991abcc90c281e3cce43df8601ee0ab9d`
- Implementation commit: `e05156a991abcc90c281e3cce43df8601ee0ab9d` — Fail closed on Task Packet governing evidence

### Findings resolved

1. Ranked relevant clauses are no longer cut off at the projection target. Every established ranked clause is included, and `governing_overage` records the target excess. The multi-clause economy regression proves all three relevant clauses remain present above target.
2. Any selected ADR binding whose anchor is absent now fails closed with `missing_adr_bindings` records containing `adr_id`, `role`, and `missing_anchor`. Valid-plus-missing and missing-only regressions both prove refusal.
3. Writing preflight now emits `python -X utf8 -m memory_seed.cli worktree guard --agent <agent> --write-intent` after explicit `Set-Location`; the regression asserts the exact checkout-local command.
4. Constitution projection now requires explicit ratified numeric Version metadata and rejects anchors whose `vN` major does not match that ratified version. Unratified, malformed-version, and incompatible-anchor regressions cover the failure path.

Changed files in this round:

- `memory_seed/task_packet.py`
- `tests/test_task_packet.py`
- `tests/test_task_packet_surfaces.py`
- `tests/fixtures/task_packet_pilot/runtime/docs/CONSTITUTION.md`
- `.superpowers/sdd/task-packet-hardening/compiler-report.md`

Validation:

1. `python -X utf8 -m pytest -q tests/test_task_packet.py` — **26 passed, 84 subtests passed** (39.20s).
2. `python -X utf8 -m pytest -q tests/test_task_packet.py tests/test_task_packet_surfaces.py tests/test_retrieval_spec.py tests/test_retrieval_spec_resolver.py tests/test_task_packet_pilot.py` — **60 passed, 105 subtests passed** (54.11s).
3. `git diff --check` — passed before the implementation commit and again before this report receipt.

### Decision and reflection delta

The user clarification is now enforced directly: the orchestrator defines decision/ADR relevance, ADR heads define governing clauses, and relevance never yields a target-truncated governing set. Targets are observability only. The independent review exposed that the original packet's word “complete” was not captured by a target-bound ranking implementation, and that the global guard text was not safe in a worktree. The revision adds explicit fail-closed and overage test vectors; no extra governance/history evidence or scope expansion was required.
