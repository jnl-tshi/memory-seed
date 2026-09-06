# Seed Pod P0 Task Packet evaluation

## Purpose

Evaluate whether `memory-seed task-packet compile` reconstructs enough relevant authority and project memory for clean Terra workers to execute bounded Seed Pod P0 tracks without inherited conversation or broad Memory Seed discovery.

The primary question is packet-compilation effectiveness: did the materialized projection contain the relevant plan, decisions, ADRs, Constitution, and policy constraints, and did workers follow the regenerated authority and execution boundaries?

## Controlled setup

- Checkpoint: `b7e623bfe42120c3a1970d8d5ee6478461f62398` on `codex/feature/seed-pods`.
- Integration boundary: local branches only; no merge, push, release, or P1 federated retrieval.
- Worker model: `gpt-5.6-terra`; effort selected by risk.
- Clean context: `fork_turns: none`; the compiled packet is the only initial task/governance context.
- Memory authority: each worker may append only its named branch-local first-hand checkpoint; the orchestrator owns cross-track decisions and this reflection.
- Materialized evidence must not be refetched. Direct inspection of owned code/tests is expected implementation work. Any additional governance or Memory Seed retrieval is recorded as a supplemental hop.

## Evaluation dimensions

1. Coverage: required plan clauses, Constitution, policy, ADR heads, and session decisions were present.
2. Precision: included evidence was useful rather than distracting or redundant.
3. Authority fidelity: the worker preserved `Constitution -> current control file -> accepted ADR -> session evidence -> derived projection` precedence.
4. Reconstruction quality: the worker could explain the task and constraints without inherited chat history.
5. Self-sufficiency: governance gaps, extra memory hops, and clarification requests were limited and justified.
6. Instruction compliance: ownership, preflight, no-refetch, validation, decision logging, and no-integration rules were followed.
7. Provenance: claims and decisions remained traceable to packet evidence, inspected implementation files, or explicitly logged supplemental sources.

Supplemental hops are classified as: expected implementation inspection; appropriate task-scoped authority check; compiler omission; stale compiled content; unclear dispatch instruction; or unjustified broad discovery.

## Planned tracks

| Track | Branch | Terra effort | Initial ownership | Status |
|---|---|---:|---|---|
| Coupled kernel governance | `codex/feature/seed-pods-core-governance` | xhigh | `core.py` plus kernel-focused tests | Fix round 1 complete; scoped re-review pending |
| Surfaces and diagnostics | `codex/feature/seed-pods-surfaces-diagnostics` | high | CLI, MCP, situate, ESR plus surface tests | Fix round 2 complete; scoped re-review pending |
| Fixtures and verification | `codex/feature/seed-pods-fixtures-verification` | high | demo/fixture data plus fixture-facing tests | Fix round 1 complete; scoped re-review pending |
| Documentation alignment | `codex/docs/seed-pods-p0` | medium | Seed Pod docs/indexes only | Fix round 1 complete; scoped re-review pending |
| Integrated review | pending after branch convergence | xhigh | read-only review first | Pending |

## Initial design observation

The conceptual promotion, lifecycle, and update-safety tracks all edit `memory_seed/core.py` at the checkpoint. The Task Dispatch schema grants exact file authority rather than symbol-level ownership, so three concurrent writers would produce intentionally overlapping packets. They were consolidated into one xhigh kernel track. This is a useful positive control: packet compilation made the ownership conflict explicit before dispatch rather than leaving it to merge-time conflict handling.

## Worker results

### Compiler preflight

- The strict 100-250 token project-frame gate rejected the first core and fixture drafts at 263 and 275 estimated tokens. Removing repeated framing brought them into contract without dropping authority or execution constraints.
- A path filter selects both the declared Markdown file and session decisions whose `F:` fields mention that path. Including `.memory-seed/policy.md` therefore pulled many unrelated recent decisions ahead of the plan/spec under the token limit, producing `completeness: partial` with 119 omitted candidates. Removing that broad path and relying on the packet's explicit constraints plus governing ADRs produced a smaller, complete seven-record projection containing the Constitution, P0 plan, boundary spec, two P0 decisions, and two relevant ADR heads.
- Exporting with the compiler's create-new atomic hard-link path stalled in the OneDrive-backed worktree, while the same validated compile completed in about 5.5 seconds to a local temporary directory. The derived packets therefore live at `C:/Users/johnn/AppData/Local/Temp/seed-pods-p0-task-packets/`; semantic dispatches and bindings remain in ignored branch scratch. This should be investigated as a storage/export portability issue, separately from retrieval quality.

| Packet | Fingerprint | Evidence | Envelope | Completeness |
|---|---|---:|---:|---|
| Kernel | `sha256:4a6daff48775cca42394fd1af9d6d720b38c51f82142f983194c830bd480cfb9` | 7 / 11,397 tokens | 27,463 tokens | Complete, no warnings |
| Surfaces | `sha256:d0031f878b9f204f7c461705d4f5b539c800605206f4d1b742e2e20e819f3a08` | 7 / 11,397 tokens | 25,943 tokens | Complete, no warnings |
| Fixtures | `sha256:0b690ffb1b17baa0f492854d263189ccc8a3b89f6b798e47883960501bdcf63a` | 7 / 11,269 tokens | 25,335 tokens | Complete, no warnings |

Pending first-wave worker reports.

### Fixture worker result

- Status: complete at `1e7a455d` plus branch-local memory/report commit `9fad83ce`; 113 tests and 8 subtests passed, docs check passed with 16 pre-existing warnings, and `git diff --check` passed.
- Packet reconstruction: sufficient. The worker used the two P0 decisions, `adr_subproject_scoping`, and the implementation plan to recover the governed-pod versus independent-root boundary without inherited conversation. The full Constitution was authoritative but broader than this fixture-only task needed.
- Extra hops: fixture/test inventory, focused existing test conventions, CLI help, and resolver/lifecycle test excerpts. These are classified as expected implementation inspection, not missing governance context.
- Precision issue: packet `allowed_files` named a new test and missing fixture declaration without saying they were expected creations. Suggested schema/dispatch improvement: an explicit `expected_absent` list.
- Outcome: added direct regression coverage proving maintained `demo/` is a governed active pod and the standalone strong-context fixture is an independent root excluded from pod discovery. No production change was needed.

### Surface worker result

- Status: `DONE_WITH_CONCERNS` at implementation commit `fda35161` plus branch-local memory/report commit `12ee790e`; 69 tests passed, the reference audit and ESR completed successfully, and no adapter implementation defect was found.
- Packet reconstruction: sufficient. The two P0 decisions, identity/scoping ADRs, plan, and boundary spec directly supported the CLI/MCP/situate/ESR assertions. The worker reported no stale materialized evidence; the full Constitution was authoritative but broader than necessary.
- Extra hops: only owned surface source, fixed core interfaces, and adjacent test conventions. Classification: expected implementation inspection.
- Instruction failure: the first escalated session append and commit relied on the tool's supplied workdir, which escalation did not preserve. The worker notified the orchestrator promptly, used an explicit absolute `Set-Location` for the corrected branch-local append/commit, and reported both locations. The duplicate untracked primary entry was removed only after the identical branch-local `mse_5g8cwehd1m7ppceg` was verified; the primary checkout returned to its three pre-run untracked items.
- Outcome: added focused tests for CLI/MCP reference audit parity, mutation dry-run parity, situate role/identity/ancestry fields, ESR audit exposure, and pod-cwd parity. Production adapters remained unchanged.

### Kernel worker result

- Status: complete at `c636cc26`; 76 focused tests passed and `git diff --check` passed.
- Packet reconstruction: sufficient. The plan/spec, exact decision identity ADR, scoping ADR, and two P0 decisions led the worker to two checkpoint gaps without inherited chat: audit did not reject incomplete or postdated provenance, and the update journal did not capture all root-local mutation destinations.
- Extra hops: one local `session append --help` lookup. Classification: appropriate task-scoped procedural inspection.
- Precision issue: the packet named a new test path without declaring it expected absent, matching the fixture worker's recommendation. The full Constitution again dominated packet tokens while only a few clauses were applied.
- Outcome: audit now labels postdated sources and rejects partial decision mappings; update receipts now capture the skill registry, selected skill artifacts, agent merge destinations, and active pod manifests. The worker retained a concern that Git hook metadata remains outside the root-local rollback receipt; independent review is pending.

### Documentation worker result

- Status: complete at implementation/memory commit `6f8b3d7f` plus report commit `2a91370a`; docs, generated indexes, links, and diff checks passed. Topic checking still reports pre-existing historical invalid-suffix errors outside the track.
- Packet reconstruction: sufficient for conservative status language. The plan, spec, two P0 decisions, scoping/authority ADRs, and Constitution let the worker distinguish implemented checkpoint evidence from integration or release evidence and preserve P1 exclusion.
- Extra hops: editable documentation inspection, a targeted functionality-audit location search, current session tail, and append help. Classification: expected implementation/procedural inspection.
- Missing context: no integrated implementation SHA or completed full-suite receipt existed, so the worker correctly avoided release-ready or fully integrated claims.
- Recommendation: packetize the exact user-supplied flow block and current implementation/test receipt, rather than expecting a documentation worker to reconstruct those details from the plan and checkpoint decision.

### Dispatch-time worktree routing observation

- Every worker's non-escalated preflight measured the intended owned worktree and exact checkpoint correctly.
- The surfaces worker's first sandboxed session append failed; its escalated retry relied on the tool call's supplied working directory. The escalated shell instead ran in the primary checkout, creating `mse_5g8cwehd1m7ppceg` in the primary `.memory-seed/sessions/2026-09/2026-09-05.md`. A later escalated commit attempt likewise ran on primary and failed harmlessly before staging because the worker test file was absent there.
- The packet said to verify the binding and use the packet branch, but it did not require an explicit `Set-Location` inside every escalated command. The worker also omitted the explicit branch argument on the misplaced append. Classification: environment/workdir routing failure plus partial instruction-compliance failure; the packet's measured binding caught the intended starting state but did not mechanically bind later escalated shells.
- The fixture worker reported a successful branch-local checkpoint, `mse_3f0kk38nczh22246`, at the exact fixture worktree path before the safety correction arrived. It is retained. Other workers were told to use an explicit absolute `Set-Location`, remeasure the top-level path, and pass `--branch` before any branch-local checkpoint or commit.
- After the equivalent branch-local `mse_5g8cwehd1m7ppceg` entry was verified byte-for-byte, the newly created duplicate in the primary checkout was removed. The primary checkout returned to its three pre-run unrelated untracked items; the branch-local evidence remains recoverable.

## Independent-review and fix-round outcomes

These statuses distinguish worker completion and focused test evidence from independent acceptance. No branch is integrated merely because its fix round passes its own tests; each amended diff still requires a scoped independent re-review.

### Kernel fix round 1

- Initial independent verdict: failed with critical gaps in detached-snapshot verification and update-transaction exclusivity/receipt coverage, plus important duplicate-source and fault-injection coverage gaps.
- Remediation head: `9284ef48bc787c456ef53b3283a2b9019c59b58f`.
- Outcome: detached snapshots now carry and validate exact source/timestamp envelopes; duplicate sources are rejected and audited; update operations acquire a nonblocking OS lock before recovery or mutation; transaction receipts cover generated root-local writes, Git hook targets, modes, and created directories; rollback restores or removes those artifacts deterministically.
- Evidence: `tests/test_seed_pod_core.py` passed 6 focused tests; the assigned core suite passed 80 tests; `git diff --check` passed.
- Reflection impact: the packet reconstructed the intended guarantees, but initial implementation still under-scoped the transaction boundary. This confirms that packet sufficiency and implementation correctness are separate dimensions and that high-risk kernel packets require adversarial review and fault-injection acceptance criteria.
- Residual worker concern: recovery intentionally fails closed if the configured Git common-hooks path changes.
- Gate: scoped independent re-review pending.

### Surfaces and diagnostics fix rounds 1 and 2

- Initial independent verdict: failed on missing CLI promotion parity, missing negative reference-audit coverage, weak formatted-output assertions, and boundary faults that escaped before `situate` or ESR could render a report.
- Fix-round-1 head: `ff5c7aa95042b1368e839fdd7efccce41b5af1ca`; fix-round-2 head: `ada4f2e363a65ce28503ab270aba682c92586cb0`.
- Outcome: tests now cover CLI/core/MCP promotion dry-run parity, invalid exact-decision provenance across core/CLI/MCP/ESR, and stronger rendered identity/ancestry fields. `situate_report` converts resolver exceptions into an `invalid-boundary` report with explicit faults; ESR exposes the same condition as a hard integrity failure and structured failed reference payload instead of propagating the exception.
- Evidence: the assigned surface suite passed 71 tests; CLI reference audit passed; ESR reported Integrity and Seed Pod references `OK`; `git diff --check` passed.
- Reflection impact: the first fix response incorrectly classified `situate.py` and `esr.py` as out of scope even though both were in `allowed_files`. The second round corrected that reading. Packet compilation supplied the authority and ownership needed, but the worker's scope reconstruction was imperfect; future packet evaluation should explicitly compare claimed scope blockers with the materialized allowlist.
- Gate: scoped independent re-review pending.

### Fixture fix round 1

- Initial independent verdict: partially compliant. The test proved the demo's pod role and governing root but did not prove it remained active, and the report omitted the reviewed head/full commit range.
- Remediation head: `f6bc92c0`.
- Outcome: the root's `include_retired=False` discovery set must contain the demo, and the discovered record must be `active`; the report records the branch commit sequence rather than only the implementation commit.
- Evidence: 2 focused fixture tests passed; the assigned suite passed 113 tests and 8 subtests; `git diff --check` passed.
- Reflection impact: the packet accurately stated “active,” but its acceptance wording allowed a weaker role-only assertion. Lifecycle status should be emitted as a distinct observable acceptance check rather than left inside descriptive prose.
- Gate: scoped independent re-review pending.

### Documentation fix round 1

- Initial independent verdict: broadly correct with an important completion-status overstatement/report-head ambiguity and a minor roadmap summary omission.
- Remediation head: `4fb275ef`.
- Outcome: documentation now calls P0 a branch-local checkpoint under review, distinguishes content/report commits from the final handoff head, and states `active descendant` plus exact `pod_sources` semantics. It does not claim integration, full-suite validation, release, merge, or push.
- Evidence: docs, generated-index, link, and diff checks passed. Topic checking retains the classified pre-existing historical invalid-suffix failures.
- Reflection impact: the packet lacked an integrated SHA and full validation receipt, and the worker correctly became more conservative after review. Documentation packets should carry exact implementation receipts when precise completion claims are expected.
- Gate: scoped independent re-review pending.

## Updated experiment conclusion

- Governance reconstruction was successful across all four clean-context workers: no worker required an additional Memory Seed decision/ADR/Constitution retrieval hop.
- Expected code, test, fixture, and CLI inspection remained necessary and should not be counted as compiler failure.
- The review loops exposed three packet-quality improvements: clause-level Constitution projection, `expected_absent` declarations, and acceptance criteria expressed as directly testable observables.
- They also exposed two orchestration controls outside retrieval quality: explicit worktree binding inside escalated commands and export behavior that is portable across OneDrive-backed paths.
- Most importantly, a complete packet is not a correctness certificate. Independent task review found material omissions in otherwise well-reconstructed work, and every fix diff remains gated on scoped re-review before integration.

## Second-cycle hardened-compiler evaluation — 2026-09-05

### Scope and method

This is a compiler evaluation, not a new implementation or clean-worker run. The evaluator received the compiled evaluator packet as its only initial task/governance context, verified its own measured worktree binding at `53a35e4e6df6610ca2fb829b6d4eeea66df62c7f`, and used the frozen Seed Pod semantic dispatches, bindings, prior reflection, and saved baseline packets as named inputs. It copied the reflection text above unchanged before adding this cycle.

The four frozen dispatches were copied into the evaluator's authorized scratch area and upgraded with explicit clause references, `expected_absent`, directly testable acceptance observables, exact implementation references, explicit `selectors.path_references: false`, and bindings measured against the frozen Seed Pod runtime at `b7e623bfe42120c3a1970d8d5ee6478461f62398`. The original per-track bindings intentionally failed when replayed against that frozen source worktree: `binding_mismatch` named the expected former track worktree and the measured frozen worktree. That is a successful safety check, not a compiler defect.

### Before-and-after measurement

| Packet | Baseline serialized / envelope | Hardened serialized / envelope | Serialized change | Constitution | Evidence |
|---|---:|---:|---:|---|---|
| Kernel | 16,080 / 27,463 | 8,736 / 19,737 | -7,344 (-45.7%) | full 8,571 -> 379 anchored tokens | 7 / 11,397 unchanged |
| Documentation | 15,903 / 23,786 | 8,688 / 16,189 | -7,215 (-45.4%) | full 8,571 -> 460 anchored tokens | 7 / 11,269 unchanged |
| Fixtures | 15,952 / 25,335 | 8,901 / 17,902 | -7,051 (-44.2%) | full 8,571 -> 584 anchored tokens | 7 / 11,269 unchanged |
| Surfaces | 16,060 / 25,943 | 8,980 / 18,481 | -7,080 (-44.1%) | full 8,571 -> 584 anchored tokens | 7 / 11,397 unchanged |

All four after packets were complete, had no resolver warnings, retained the same two decisions, two ADRs, and two exact plan/spec documents as the saved baselines, and were deterministic across repeated compiles. Their materialized worker evidence omitted the full Constitution and instead supplied complete anchored clauses, each with source range and content digests.

### Behavioral proof

`python -X utf8 -m pytest -q tests/test_task_packet.py tests/test_task_packet_surfaces.py tests/test_retrieval_spec.py tests/test_retrieval_spec_resolver.py tests/test_task_packet_pilot.py` passed: **60 tests and 105 subtests** in 50.16 seconds. This covers exact path-reference opt-in, whole and multiple clause ordering, digest validation and uncertainty/full-document fallback, expected-absent and implementation contracts, deterministic fingerprints, and canonical CLI/MCP preview/compile parity.

### Reflection

The hardened packets preserve authority and task coverage while removing 93.2–95.6% of the formerly materialized Constitution payload. Explicit path-reference selection makes the non-expanding policy-file behavior inspectable in the effective spec rather than an undocumented resolver default; explicit opt-in remains covered by the resolver proof. Expected creations and acceptance commands are now actionable execution contracts, and replaying stale bindings fails before a worker can write in the wrong worktree.

No compiler or Seed Pod source was changed. The remaining limitation is methodological: this cycle proves compilation precision and surface behavior, not whether a new clean worker makes fewer implementation mistakes. A later worker trial should measure that independently.

### Cycle-two component ledger and packet matrix

The hardened ledger is fixed-width against each compiled packet's context envelope. Baselines used the legacy ledger and therefore do not have comparable per-component percentages.

| Packet | Serialized | Fixed | Tool | Supplemental | Output |
|---|---:|---:|---:|---:|---:|
| Kernel | 8,736 (044.262%) | 0 (000.000%) | 1 (000.005%) | 6,000 (030.400%) | 5,000 (025.333%) |
| Documentation | 8,688 (053.666%) | 0 (000.000%) | 1 (000.006%) | 4,000 (024.708%) | 3,500 (021.620%) |
| Fixtures | 8,901 (049.721%) | 0 (000.000%) | 1 (000.006%) | 5,000 (027.930%) | 4,000 (022.344%) |
| Surfaces | 8,980 (048.590%) | 0 (000.000%) | 1 (000.005%) | 5,000 (027.055%) | 4,500 (024.349%) |

| Packet | Expected context and compiled projection | Evidence used | Self-sufficiency / instruction compliance | Provenance disposition |
|---|---|---|---|---|
| Kernel | Root-centered P0 kernel; projection retained two Seed Pod decisions, identity/scoping ADRs, and exact plan/spec paths; three explicit clauses replaced full Constitution | 7 records / 11,397 tokens; `authority`, `provenance`, `integration-mode` | Compiler self-sufficiency: PASS; stale binding rejected, upgraded binding passed; clean-worker behavior: N/A, not measured | All claims trace to saved baseline, frozen dispatch/binding, materialized evidence, or replay fingerprint `fe61…1c63c` |
| Documentation | P0 status/docs; retained two decisions, authority/scoping ADRs, and exact plan/spec paths; three explicit clauses | 7 / 11,269; `authority`, `minimal-context`, `control-plane-precedence` | Compiler self-sufficiency: PASS; expected-absent/observable contracts present; clean-worker behavior: N/A, not measured | Materialized sources and stable replay fingerprint `f86e…f9b5` support the record |
| Fixtures | Governed-pod versus independent-root fixtures; retained two decisions, authority/scoping ADRs, and plan/spec paths; three explicit clauses | 7 / 11,269; `authority`, `provenance`, `minimal-context` | Compiler self-sufficiency: PASS; creation/validation intent explicit; clean-worker behavior: N/A, not measured | Materialized sources and stable replay fingerprint `a0d3…cc57` support the record |
| Surfaces | CLI/MCP/situate/ESR P0 contracts; retained two decisions, identity/scoping ADRs, and plan/spec paths; three explicit clauses | 7 / 11,397; `authority`, `provenance`, `minimal-context` | Compiler self-sufficiency: PASS; CLI/MCP parity covered by proof suite; clean-worker behavior: N/A, not measured | Materialized sources and stable replay fingerprint `d770…9da2` support the record |

“N/A, not measured” is deliberate: cycle two did not dispatch a clean worker or make implementation changes, so worker reconstruction quality, worker instruction compliance, and implementation correctness cannot be inferred from deterministic compilation or test-surface parity. The matrix records compiler-level self-sufficiency and provenance only.

### Cycle-two disposition matrix — completion addendum

The following dispositions complete the compiler-evaluation record. “Extra hop” uses the approved experiment taxonomy exactly: expected implementation inspection; appropriate task-scoped authority check; compiler omission; stale compiled content; unclear dispatch instruction; or unjustified broad discovery.

| Packet | Extra hops and classification | Missing / excessive context | Authority fidelity and reconstruction quality | Scope-blocker accuracy | Recommended compiler change |
|---|---|---|---|---|---|
| Kernel | No packet-external governance/history retrieval. Frozen runtime branch/HEAD/status: **appropriate task-scoped authority check**. Compiler/CLI and named test reads: **expected implementation inspection**. The minimal policy-path probe: **expected implementation inspection**; it was inconclusive because its ad-hoc spec lacked canonical required evidence and was not used as a conclusion. | Missing: none for compiler replay; seven retained records covered task, ADR, and plan/spec authority. Excessive: none in the hardened materialization; the former 8,571-token full Constitution was removed. | Explicit clauses plus retained decisions/ADRs preserve Constitution → control file → ADR → session evidence ordering. Worker reconstruction quality: **N/A, not measured**; no clean worker was dispatched. | Accurate: every required reflection/report/scratch path was in the allowlist; initial original-binding `binding_mismatch` accurately named the wrong worktree and prevented replay. | Keep explicit clause refs, expected-absent, observables, exact `implements`, and measured binding receipts mandatory for writing packets. |
| Documentation | Same shared evaluation hops: frozen binding check **appropriate task-scoped authority check**; compiler/test reads **expected implementation inspection**; no governance/history hop and no broad discovery. | Missing: none for compilation. Excessive: none after explicit clauses replaced the full Constitution. | Explicit `authority`, `minimal-context`, and `control-plane-precedence` clauses plus authority/scoping ADRs are source-linked. Worker reconstruction quality: **N/A, not measured**, for the stated methodological reason. | Accurate: the report path was explicitly allowed and expected absent; no claimed blocker fell outside the allowlist. | Preserve source-linked whole clauses and make the effective `path_references` mode visible in all compiled projections. |
| Fixtures | Same shared evaluation hops: frozen binding check **appropriate task-scoped authority check**; compiler/test reads **expected implementation inspection**; no governance/history hop and no broad discovery. | Missing: none for compiler replay. Excessive: none after the full Constitution was replaced by three explicit clauses. | Explicit clauses and authority/scoping ADRs retain the source chain for governed-versus-independent fixture intent. Worker reconstruction quality: **N/A, not measured**; compiler parity is not a worker trial. | Accurate: all three declared creations plus the report were allowlisted/expected absent; no scope blocker was inferred. | Continue requiring expected-absent declarations for every intended fixture/test/report creation. |
| Surfaces | Same shared evaluation hops: frozen binding check **appropriate task-scoped authority check**; compiler/CLI/MCP and test reads **expected implementation inspection**; no governance/history hop and no broad discovery. | Missing: none for compilation. Excessive: none after full-Constitution removal; CLI/MCP parity proof was scoped to compiler surfaces. | Explicit clauses and identity/scoping ADRs preserve governing source identities. Worker reconstruction quality: **N/A, not measured**; CLI/MCP parity does not measure worker reasoning. | Accurate: surface test/report creations were explicitly allowlisted and expected absent; the replay binding check rejected wrong-worktree scope before write. | Retain canonical CLI/MCP parity as an observable and add a future optional controlled worker-outcome field rather than inferring worker quality from compiler tests. |

No row is classified as compiler omission, stale compiled content, unclear dispatch instruction, or unjustified broad discovery: the completed packets carried the required evidence, had no warnings, and the evaluator did not perform those kinds of hops. The only unmeasured dimensions are clean-worker reconstruction, worker instruction compliance, and implementation correctness, because this cycle intentionally evaluated packet compilation rather than dispatching a worker.

## Progressive provenance packet correction — 2026-09-06

- Failure: the original worker reconstruction skipped the complete `.memory-seed/agent-rules.md` and `session_logging.md` route, then manually authored future-dated session entries rather than using the session CLI.
- Detection gap: packet preflight verified worktree identity and source scope, but did not require or record the agent-rules/session-skill baseline before a worker checkpoint.
- Remedy: the clean repair worktree reconstructed the reviewed code/test commits from the original range while excluding the invalid session entries and disposable report; it read the missing governance routes before edits.
- Repair: the three milestones were appended only through `python -X utf8 -m memory_seed.cli session append`, with new canonical IDs and explicit author-time estimates (00:23, 00:44, 00:51 Europe/London). Each record declares that its timestamp is commit-derived rather than direct wall-clock evidence.
- Follow-up: worker packets that delegate checkpoint logging should make the required agent-rules and session-logging baseline explicit, and validation should surface future-dated session timestamps before handoff.

## Baseline-governance correction — Ada future-timestamp incident

- Ada's clean worker packet omitted the active session-writing contract, so the worker manually edited a
  session entry and supplied a future timestamp instead of letting the canonical append writer own the
  clock. That was an instruction-completeness failure, not a reason to relax append-only validation.
- The compiler now gives every worker the complete active `.memory-seed/agent-rules.md`; checkpoint and
  session-writable packets additionally receive the complete active
  `.memory-seed/skills/session_logging.md`. Their execution defaults require `memory_session_append` or
  checkout-local `python -X utf8 -m memory_seed.cli session append`, require automatic clock ownership,
  and forbid direct Markdown session edits and explicit timestamps unless a dispatch grants a narrowly
  scoped repair/backfill exception.
- This makes the governance source bytes, digest, baseline fingerprint, and token share visible in the
  packet itself. A changed baseline changes the compiled packet fingerprint, preventing a clean worker
  from silently receiving stale or absent session-authoring governance.
