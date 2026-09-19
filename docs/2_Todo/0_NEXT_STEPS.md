# Next Steps

Status: **ACTIVE — navigation and sequencing guide**
Updated: 2026-09-19

The hosted Memory Seed programme is now the primary product workstream. The local OSS edition remains
complete and Markdown-authoritative; the separate hosted edition will be SQL-authoritative and expose a
complete Markdown export. The two editions share semantics, not writable persistence.

## P0 hosted sequence

1. Start with [Hosted Memory MVP Programme](hosted-memory-mvp-programme.md): validate authenticated
   MCP/Codex-first capture, the pause-and-queue contract, team/project boundaries, and deletion/export
   acceptance fixtures.
2. Implement the smallest SQL event and curated-memory model that satisfies the
   [live edition authority contract](../3_Spec/edition-authority-contract.md).
3. Prove permission-filtered retrieval parity, curator evidence, and provider fail-closed behaviour before
   widening the surface.
4. Keep launch UI, chatbot, bidirectional repository sync, embeddings as authority, and broad provider
   ingestion out of the MVP.

No hosted service, provider call, upload, paid trial, release, or remote-setting change is authorized by
the documentation amendment alone.

## Local OSS obligations that remain active

- [Memory quality metrics v0](memory-quality-metrics-v0-proposal.md): maintainer review of the existing
  baseline remains the next gate.
- [Task Packet hardening](task-packet-hardening-progressive-provenance-plan.md) and
  [calibration](task-packet-calibration-harness-plan.md): finish independent review, dogfooding, and the
  representative/holdout design.
- [Memory Trace UX reference plan](memory-trace-ux-reference-model-implementation-plan.md) and
  [interaction matrix](memory-trace-ux-m0-interaction-matrix.md): M3 bounded graph perspectives remain
  the next local UI slice.
- [Reflection launch verification](reflection-launch-verification-closeout.md): complete only the bounded
  launch-matrix and first-board checks; future Reflection expansion is deferred.

## Parked and historical work

- Post-MVP product ideas live in [`8_Deferred/`](../8_Deferred/), each with a revisit condition.
- Consolidated or superseded plans live in [`7_Replaced/`](../7_Replaced/) with successor pointers.
- Shipped plans live in [`5_Completed/`](../5_Completed/); external account or submission choices are
  references/checklists, not active engineering plans.
- The full 41-document disposition is recorded in the
  [2026-09-19 consolidation audit](../4_Reference/hosted-roadmap-consolidation-audit-2026-09-19.md).

## Decisions still requiring JNL

- Whether and when to authorize any hosted implementation tranche beyond local documentation/design.
- Provider, hosting, billing, and retention choices once the MVP gates require them.
- Whether to submit the completed Memory Index dry run externally.
- Any remote OpenSSF, branch-protection, vulnerability-reporting, or organisation-owner settings.

The folder remains lifecycle authority. Do not reopen a replaced plan to recover one requirement: carry
the requirement into the canonical hosted programme or a new bounded successor instead.
