# ADR lineage review queue

Generated from 313 decision-level link-sidecar edges (11 unusable after normalisation).

A head moves automatically only when every step of its chain is AUTHORED. Machine-scored edges land here instead: the swarm suggests, a human decides. Read both titles before approving - a 0.75 edge already carried one ADR onto an unrelated concern.

- automatic (authored chain): **0**
- needs review (machine-suggested): **1**
- pinned, report only: **3**

## adr_mcp_decision_envelope_review (PINNED - report only)
*MCP decision envelope and mandatory ADR review*
- head now: `mse_17d0qqh34a07qp5b:d1`
- `mse_17d0qqh34a07qp5b:d1` unmoved (no-successor)
- `mse_ddeat5w29spep3qw:d1` unmoved (fan-out)
- `mse_z7rfq8x5qjfbyzdc:d1` => evolves `mse_17d0qqh34a07qp5b:d1` (authored)
    - from: D1 - Decision
    - to:   D1 - Bind lineage-linked MCP writes to living ADR review

## adr_merge_branch_primitive
*session merge-branch is the one-step integration primitive, not a git merge driver*
- head now: `founding:.memory-seed/index.md#L172`
- `mse_9c151e4gbkkv1w5v:d1` unmoved (no-successor)
- `mse_dr5eprnhrctqeeg3:d1` unmoved (fan-out)
- related: `mse_v26pem9hsvsbjbge:d3` - D3 - Use reviewed local integration and retain publish gates

## adr_parent_first_sidecar_transaction (PINNED - report only)
*Parent-first recoverable sidecar transaction*
- head now: `mse_17d0qqh34a07qp5b:d2`
- `mse_17d0qqh34a07qp5b:d2` unmoved (no-successor)
- `mse_d06t9bccm3yykfqs:d1` => evolves `mse_17d0qqh34a07qp5b:d2` (authored)
    - from: D1 - Publish the parent before decision sidecars
    - to:   D2 - Extend parent-first recovery and structural fusion to ADR events
- `mse_qbp1ndbnhezj34eb:d1` unmoved (no-successor)
- related: `mse_ypmrtzfmw4qwtbnn:d1` - D1 - Use authored sidecars as the only Trace topic truth
- related: `mse_ypmrtzfmw4qwtbnn:d2` - D2 - Require complete authored topics for MCP session writes

## adr_session_decision_authority (PINNED - report only)
*Session-decision authority and ADR-curated synopsis*
- head now: `mse_17d0qqh34a07qp5b:d1`
- `mse_17d0qqh34a07qp5b:d1` unmoved (no-successor)
- `mse_ddeat5w29spep3qw:d1` unmoved (fan-out)
- `mse_z7rfq8x5qjfbyzdc:d1` => evolves `mse_17d0qqh34a07qp5b:d1` (authored)
    - from: D1 - Decision
    - to:   D1 - Bind lineage-linked MCP writes to living ADR review

## adr_subproject_scoping
*Sub-project runtime scoping and inheritance defaults*
- head now: `founding:.memory-seed/policy.md#L78`
- `ms-0bd3d8b2:d2` unmoved (no-successor)
- `ms-f776aff0:d1` => evolves `ms-0bd3d8b2:d1` (0.75)
    - from: D1 - Restore operational guardrails in v2 language
    - to:   D1 - Use a seeded trigger registry instead of only prose triggers

