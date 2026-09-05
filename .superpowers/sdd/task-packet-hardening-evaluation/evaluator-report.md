# Hardened Task Packet evaluator report

## Status

**COMPLETE_WITH_CONCERN** — the hardened compiler met the packet's reconstruction, precision, deterministic-output, and behavioral-proof requirements. The concern is scope of evidence: this is a compiler evaluation, not a repeat clean-worker implementation trial.

- Evaluation worktree/branch: `C:\Users\johnn\OneDrive\Documents\2nd Brain\Foundry\memory seed\.codex\worktrees\task-packet-hardening-evaluation` / `codex/experiment/task-packet-hardening-evaluation`
- Base HEAD: `53a35e4e6df6610ca2fb829b6d4eeea66df62c7f`
- Frozen Seed Pod runtime used for replay: `b7e623bfe42120c3a1970d8d5ee6478461f62398` on `codex/feature/seed-pods`
- Evaluated-content HEAD: `ebdd61f7cc2b7f062bf8a8ca0aba78fe43379a3f`
- Evaluated range: `53a35e4e6df6610ca2fb829b6d4eeea66df62c7f..ebdd61f7cc2b7f062bf8a8ca0aba78fe43379a3f`

## Scope-blocker check

The required output paths were compared with `dispatch.execution.allowed_files` before writing:

| Required path | Allowed? | Result |
|---|---|---|
| `experiments/seed-pod-task-packet-evaluation/REFLECTION_LOG.md` | yes | created from frozen reflection, then cycle two appended |
| `.superpowers/sdd/task-packet-hardening-evaluation/evaluator-report.md` | yes | this report |
| `.superpowers/sdd/task-packet-hardening-evaluation/dispatches/` | yes | upgraded dispatch copies only |
| `.superpowers/sdd/task-packet-hardening-evaluation/bindings/` | yes | replay-safe binding copies only |

No forbidden path was edited. No Seed Pod worktree, compiler source, tests, control-plane file, or baseline packet was modified.

## Inputs and supplemental-context ledger

| Input/hop | Classification | Reason |
|---|---|---|
| Compiled evaluator packet | packet material | sole initial task/governance context |
| Frozen reflection; four dispatches/bindings; saved baseline packets | named frozen evaluation input | explicitly required by the packet output contract |
| Frozen runtime branch/HEAD/status | appropriate task-scoped authority check | confirms replay binding and protects the frozen worktree from writes |
| `memory_seed/task_packet.py`, `memory_seed/cli.py`, and named test surfaces | expected implementation/test inspection | direct compiler and proof surfaces needed to interpret and execute the required checks |
| Ad-hoc policy-path probe | appropriate task-scoped behavioral probe, inconclusive | the deliberately minimal spec omitted required canonical evidence, so it was not used as a product conclusion; the authoritative resolver test supplied the proof |

There were no broad discovery hops and no supplemental governance/history retrieval beyond the named frozen input. The plan/spec and decision/ADR content used in replay were materialized by the compiler.

## Replay upgrade and authority fidelity

Each frozen dispatch was copied unmodified first, then its copy gained the hardened schema elements: exact Constitution refs, declared expected-absent paths, observable commands, an exact `implements` decision identity, and `selectors.path_references: false`. Replay bindings were copied and remeasured to the frozen source worktree. The original bindings produced the expected `binding_mismatch`; the upgraded bindings then compiled safely.

| Packet | Expected context / retained decisions and ADRs | Selected Constitution clauses and reason | Missing or excessive context | Authority / fingerprint |
|---|---|---|---|---|
| Core governance | root-centered P0 kernel; `mse_ynyx8kn8wx8stfvm:d1`, `mse_z29mmqx2tgbn3wvr:d1`; `adr_decision_identity`, `adr_subproject_scoping` | `authority`, `provenance`, `integration-mode`; each explicitly named by dispatch | no required evidence missing; full Constitution removed from materialized worker evidence | precedence preserved; `sha256:fe61b9a77ff8b9d53d5c7747d7582639b9625a84eea8e4ff2dc1001d98e1c63c`, stable |
| Documentation | P0 status/docs; same decisions; `adr_control_file_authority`, `adr_subproject_scoping` | `authority`, `minimal-context`, `control-plane-precedence`; explicit dispatch refs | no required evidence missing; full Constitution removed | precedence preserved; `sha256:f86eb28b8199f1f7aa2b139e67dd3f96944e78d61e503ae409385d48cbf6f9b5`, stable |
| Fixtures | governed versus independent fixtures; same decisions; `adr_control_file_authority`, `adr_subproject_scoping` | `authority`, `provenance`, `minimal-context`; explicit dispatch refs | no required evidence missing; full Constitution removed | precedence preserved; `sha256:a0d3e9b98f6d0841284bc1d7775baec74e2e11087aca474473112f87f50fcc57`, stable |
| Surfaces | CLI/MCP/situate/ESR P0 contracts; same decisions; `adr_decision_identity`, `adr_subproject_scoping` | `authority`, `provenance`, `minimal-context`; explicit dispatch refs | no required evidence missing; full Constitution removed | precedence preserved; `sha256:d77074d0ee45f8f0560e18b289a4bf306edc2363cdf7cb296fa0c8b7c24e9da2`, stable |

All retained the same seven evidence records as their saved baseline: two decisions, two ADR heads, the governing Constitution manifest, and exact plan/spec Markdown. The after-packet resolver traces state `path_references: false`, proving direct file selection did not silently add `F:`-referencing decisions; explicit opt-in remains covered by the resolver proof below.

## Measurements

Saved baseline packets used the legacy ledger (fixed instruction count 382 and no per-component table); after packets supply the hardened component ledger.

| Packet | Baseline serialized / envelope | After serialized / envelope | Change | Constitution tokens | After components (serialized, fixed, tool, supplemental, output) |
|---|---:|---:|---:|---:|---|
| Core | 16,080 / 27,463 | 8,736 / 19,737 | -45.7% / -28.1% | 8,571 -> 379 (-95.6%) | 8,736 (44.262%), 0 (0%), 1 (0.005%), 6,000 (30.400%), 5,000 (25.333%) |
| Documentation | 15,903 / 23,786 | 8,688 / 16,189 | -45.4% / -31.9% | 8,571 -> 460 (-94.6%) | 8,688 (53.666%), 0 (0%), 1 (0.006%), 4,000 (24.708%), 3,500 (21.620%) |
| Fixtures | 15,952 / 25,335 | 8,901 / 17,902 | -44.2% / -29.3% | 8,571 -> 584 (-93.2%) | 8,901 (49.721%), 0 (0%), 1 (0.006%), 5,000 (27.930%), 4,000 (22.344%) |
| Surfaces | 16,060 / 25,943 | 8,980 / 18,481 | -44.1% / -28.8% | 8,571 -> 584 (-93.2%) | 8,980 (48.590%), 0 (0%), 1 (0.005%), 5,000 (27.055%), 4,500 (24.349%) |

Evidence count/token totals were unchanged: core/surfaces 7 / 11,397 and documentation/fixtures 7 / 11,269. The reduction comes from replacing duplicate full-Constitution worker payload with complete, source-linked clauses, plus the schema's canonical execution contracts.

## Commands and results

| Command | Result |
|---|---|
| `python -X utf8 -m memory_seed.cli worktree guard --agent codex --write-intent` | PASS: owned worktree, clean, correct branch and `53a35e4e…` base |
| Four copied dispatches replayed against their original copied bindings | EXPECTED FAIL: `binding_mismatch` named former track worktree versus measured frozen source worktree |
| Four upgraded copies replayed with `compile_task_packet(...)` twice each | PASS: all complete, no warnings, byte-identical canonical JSON/fingerprint per packet |
| `python -X utf8 -m pytest -q tests/test_task_packet.py tests/test_task_packet_surfaces.py tests/test_retrieval_spec.py tests/test_retrieval_spec_resolver.py tests/test_task_packet_pilot.py` | PASS: 60 passed, 105 subtests passed in 50.16s |
| `git diff --check` | PASS after the evaluation artifacts were authored and again at the fix-round preflight; no whitespace errors |

The proof suite exercises exact path-reference opt-in (including reference expansion only with `true`), full/uncertain Constitution fallback, complete whole-clause selection and ordering above target, digest validation, stable canonical fingerprints, expected-absent and `implements` enforcement, and byte-equivalent CLI/MCP task-packet preview/compile behavior.

## Concerns and packet-effectiveness assessment

The hardening is effective for precision and execution safety: it preserves the original relevant evidence, removes 93–96% of the previously delivered Constitution text, makes path-expansion intent explicit, rejects stale worktree bindings, and turns previously ambiguous creations and validation prose into machine-checkable contracts.

Two limits remain. First, the old four saved packets did not themselves filter `.memory-seed/policy.md`; the targeted resolver proof demonstrates the requested exact-selection semantics, but the old reflection's policy over-breadth observation is from earlier draft packets rather than these four baselines. Second, this cycle measures compiler behavior, not whether a new clean worker now commits fewer errors. A future controlled clean-worker comparison should preserve the same bounded task and independently score implementation/review outcomes.

## Commit record

The initial evaluation produced one commit in the evaluated range:

| Commit | Subject | Role |
|---|---|---|
| `ebdd61f7cc2b7f062bf8a8ca0aba78fe43379a3f` | `docs: record hardened task packet evaluation` | evaluated content: frozen-input copies, second-cycle reflection, and evaluator report |

The fix-round receipt below records subsequent receipt commits separately from this evaluated-content head, so it does not retroactively claim that a receipt commit was part of the evaluated compiler result.

## Fix round 1 receipt

- Fix base: `ebdd61f7cc2b7f062bf8a8ca0aba78fe43379a3f`
- Evaluated-content range: `53a35e4e6df6610ca2fb829b6d4eeea66df62c7f..ebdd61f7cc2b7f062bf8a8ca0aba78fe43379a3f`
- Final substantive fix commit: `15ebf3c680bb1fd1c9a3d522736b33df9e592fb3` (`docs: complete task packet evaluation record`)
- Commit coverage: `ebdd61f7cc2b7f062bf8a8ca0aba78fe43379a3f` is the original evaluated content; `15ebf3c680bb1fd1c9a3d522736b33df9e592fb3` completes the missing receipt, component ledger, and per-packet matrix. The commit that records this receipt is intentionally a separate administrative receipt head and does not change the evaluated compiler result.
- Validation before the substantive fix commit: `git diff --check` PASS; all four scratch dispatch JSON files passed `python -m json.tool`.

The final handoff must name the separate administrative receipt head alongside the two commits above. It is not a new compiler evaluation and it makes no claim beyond recording this exact receipt.

## Fix round 2 pre-commit receipt

The evaluated substantive range remains `53a35e4e6df6610ca2fb829b6d4eeea66df62c7f..ebdd61f7cc2b7f062bf8a8ca0aba78fe43379a3f`. The prior administrative receipt is `fa23627b207bb3a60372bbcfc2ecdd3c95009fe1` (`docs: append evaluation fix receipt`), whose parent substantive record is `15ebf3c680bb1fd1c9a3d522736b33df9e592fb3` (`docs: complete task packet evaluation record`).

Every evaluation-record commit preceding this fix round is therefore:

| Commit | Subject | Disposition |
|---|---|---|
| `ebdd61f7cc2b7f062bf8a8ca0aba78fe43379a3f` | `docs: record hardened task packet evaluation` | original evaluated content |
| `15ebf3c680bb1fd1c9a3d522736b33df9e592fb3` | `docs: complete task packet evaluation record` | substantive record completion |
| `fa23627b207bb3a60372bbcfc2ecdd3c95009fe1` | `docs: append evaluation fix receipt` | prior administrative receipt |

This round adds the missing taxonomy-based dispositions directly to the reflection and changes no compiler, tests, memory control files, or Seed Pod work. The actual new branch head is necessarily reported by the post-commit handoff, rather than inserted as a self-referential future hash in this file.
