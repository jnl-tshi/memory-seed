# Progressive provenance contracts report

## Status

Complete: the shared serialized, reference-only contract foundation is implemented and focused acceptance passed. No Git derivation, hook mutation, CLI/MCP/ESR surface, cadence rule, Seed Pod lifecycle mutation, or language parsing was added.

## Git receipt

- Base HEAD: `37a58b2f2d62e8a0e8bdf28a129eb4bce792f1b4`
- Implementation/checkpoint HEAD: `3af13c6a418ac19b750598e4b5e9325deb8b0c68`
- Final HEAD: supplied in the handoff after this report-bearing commit. A committed file cannot contain its own Git object ID without changing that ID.
- Commits: `3af13c6a418ac19b750598e4b5e9325deb8b0c68` (`Add progressive provenance contracts`), `22b41db14a35a2dbad3ab4d501edd95b68fef077` (`Record provenance contract handoff`), and this correction/report commit, whose exact hash is listed in the handoff.

## Files changed

- `memory_seed/provenance.py` — adapter-free schemas, builders, deterministic identities, validators, append-only replacements, projection, runtime ownership, and activation contracts.
- `tests/test_provenance.py` — focused acceptance coverage.
- `.memory-seed/sessions/2026-09/2026-09-05.md` — first-hand decision checkpoint.
- `.superpowers/sdd/progressive-provenance/contracts-report.md` — this handoff record.

## Contract choices

- A binding has one exact decision reference, commit and parent object IDs, repository-relative file, old/new blob IDs, and non-empty reference-only hunks.
- Hunk identity is deterministic from the Git references, old/new ranges, and two SHA-256 context hints. No source line, patch, snapshot, symbol, or parser field is permitted.
- Binding, replacement, and packet activation identities are canonical SHA-256 records. Validation fails closed for tampering, unknown fields, ambiguous replacements, and replacement cycles.
- Corrections append a new binding plus a replacement record; the old binding remains historical. The ledger projection exposes active and replaced IDs without becoming authoritative state.
- Runtime input maps exactly one owner to one Markdown sidecar: root uses `.memory-seed/provenance/bindings.md`; a pod uses `.memory-seed/provenance/pods/<pod-id>.md`. Reads remain valid for retired pods; activation/appending new bindings is refused.
- Packet activation is normalized from a Task Packet fingerprint, exact `implements` decision refs, bound binding IDs, and runtime ownership. With a supplied ledger it requires exact implementation-ref coverage. It never stamps a Git commit message.

## Acceptance observables

- `python -X utf8 -m pytest -q tests/test_provenance.py` — 5 passed in 0.11s.
- `git diff --check` — passed.

## Concerns

- The contract accepts SHA-1 and SHA-256 Git object IDs, but adapters must derive and verify them against the selected Git repository; this module deliberately does neither.
- Replacement rationale is a small declared reason code. Durable narrative rationale belongs to the referenced decision record, avoiding a source-text side channel in provenance records.
- The markdown serialization format and lifecycle mutation are intentionally deferred. This module only fixes the data shape and deterministic validation boundary.

## Task Packet effectiveness reflection

The packet was sufficient for implementation: it supplied the governing Constitution clauses, the exact reference-only decision, decision identity, Markdown authority, runtime-scoping ADRs, allowed files, required observables, and a measured worktree binding.

Supplemental governance/history hops, using the approved reflection taxonomy:

- `.memory-seed/sessions/2026-09/2026-09-05.md` — **appropriate task-scoped authority check**: read the explicitly authorized append target to preserve its schema and append-only history.
- `experiments/seed-pod-task-packet-evaluation/REFLECTION_LOG.md` — **appropriate task-scoped authority check**: read only to obtain the packet-required supplemental-hop taxonomy for this report.

Direct source and test inspection was **expected implementation inspection**, not a governance/history retrieval. No compiler omission, stale compiled content, unclear dispatch instruction, or unjustified broad discovery was found.

## Fix round 1 — independent review response

The original hunk-context choice is superseded by this narrower contract: a binding now records a validated authorship record (`first-hand` or `reconstructed` plus compact actor kind/ID), and a hunk identity commits to commit, parent, file, ranges, and a SHA-256 digest of exact Git unified-diff hunk-body bytes. The byte preimage/canonicalization is declared in `PATCH_BYTES_SCHEMA` and `PATCH_BYTES_CANONICALIZATION`; no patch bytes are stored. V1 context hints are always null, so a future adapter must derive any compact locator rather than storing source text.

Ledgers now carry their exact runtime ownership. Packet activation requires that owned ledger, accepts many active bindings per packet decision, rejects arbitrary/unowned/replaced bindings, and requires its selected decision set to exactly equal the packet's implements. The runtime contract now distinguishes active root/pod owners, retired pods, and `detached-former-root` metadata-only records; reads remain valid for all while appending/activation rejects retired and detached owners. Replacements carry both a bounded reason code and an exact decision reference owning the correction rationale.

`project_ledger` exposes an adapter-supplied evidence state (`unverified`, `available`, `git-unavailable`, `missing-git-object`, or `projection-unavailable`) without performing Git work itself.

### Fix-round validation

- `python -X utf8 -m pytest -q tests/test_provenance.py` — 10 passed, 12 subtests passed in 0.16s.
- `git diff --check` — passed before checkpoint/report append; rerun before commit.

### Fix-round reflection

No additional governance or history retrieval was needed to resolve the review: the direct review request supplied the required corrections. Reading the authorized session append target is an **appropriate task-scoped authority check**; contract and test inspection remains **expected implementation inspection**. There is no plan contradiction or scope blocker.

## Fix round 2 — raw append authorization

`validate_append_only_update` now checks append authorization against the existing normalized ledger runtime whenever the candidate extends bindings or replacements. Retired pods and detached former roots can still validate unchanged historical metadata and serve reads, but raw candidate binding appends and raw candidate replacement appends now fail with the same owner-state codes as the convenience append path.

### Fix-round validation

- `python -X utf8 -m pytest -q tests/test_provenance.py` — 11 passed, 18 subtests passed in 0.18s.
- `git diff --check` — passed before checkpoint/report append; rerun before commit.

No additional governance/history retrieval, plan contradiction, or scope blocker occurred.
