# Lineage chains (same-area segmentation)

From 267 lineage edges ({'not-lineage': 137, 'ambiguous-bare-ref': 9}), 88 of which join decisions sharing a declared area.

The unfiltered graph's largest component is 67 decisions spanning six unrelated areas. Filtering to shared area produces the chains below - each one reads as a single concern.

Chains of 3+ decisions, largest first. **UNCLAIMED** means no ADR names any member (counting hard membership and soft `context-added` alike) - those are candidate concerns.

## chain 1 — mcp-tools (11 decisions)
- areas: mcp-tools x11
- claimed by: `adr_mcp_integration_surface`
    - `ms-4c8e2a17:d1`  2026-05-29 13:48  D1 - Write MCP config unconditionally, no PATH check at init time [`adr_mcp_integration_surface`]
    - `ms-4c8e2a17:d2`  2026-05-29 13:48  D2 - Detect missing binary in the retrieval hook, not at init time [`adr_mcp_integration_surface`]
    - `ms-4c8e2a17:d4`  2026-05-29 13:48  D4 - Claude MCP entry includes "type": "stdio"; Cursor and Gemini omit [`adr_mcp_integration_surface`]
    - `ms-7b3f1e92:d3`  2026-05-29 14:07  D3 - MCP upsert: overwrite if command matches, skip if different comma [`adr_mcp_integration_surface`]
    - `ms-a3f91c2b:d1`  2026-05-29 15:17  D1 - Decision [`adr_mcp_integration_surface`]
    - `ms-6a09aea8:d1`  2026-06-03 22:54  D1 - Claude MCP server belongs in project-root .mcp.json, not settings [`adr_mcp_integration_surface`]
    - `ms-2cd452e4:d1`  2026-06-03 23:43  D1 - Codex MCP belongs in project .codex/config.toml, written via zero [`adr_mcp_integration_surface`]
    - `ms-2cd452e4:d2`  2026-06-03 23:43  D2 - Surface the trust requirement (Codex's silent-failure trap) [`adr_mcp_integration_surface`]
    - `ms-6eeb512f:d1`  2026-06-03 23:55  D1 - Decision [`adr_mcp_integration_surface`]
    - `mse_81v7vk4x5ys3k2n0:d3`  2026-07-10 04:27  D3 - Add MCP and skill surfaces [`adr_mcp_integration_surface`]
    - `mse_vzsef0fmpsde2jh4:d1`  2026-07-19 20:01  D1 - Gate the MCP write surface, retire the ungated pair [`adr_mcp_integration_surface`]

## chain 2 — session-fuse (8 decisions)
- areas: session-fuse x8
- claimed by: `adr_merge_branch_primitive`
    - `mse_81v7vk4x5ys3k2n0:d1`  2026-07-10 04:27  D1 - Make fuse Memory Seed-aware [`adr_merge_branch_primitive`]
    - `mse_azn6bejpd9xpmh3f:d2`  2026-07-10 06:20  D2 - Scope branch-side validation to the branch delta [`adr_merge_branch_primitive`]
    - `mse_dr5eprnhrctqeeg3:d1`  2026-07-10 12:03  D1 - Wrapper command, not a merge driver or blocking hook [`adr_merge_branch_primitive`]
    - `mse_vm7trfd4dbd5yvnn:d1`  2026-07-10 14:18  D1 - Decision [`adr_merge_branch_primitive`]
    - `mse_w2fk7qnx4t9b3vmh:d1`  2026-07-11 15:58  D1 - Decision [`adr_merge_branch_primitive`]
    - `mse_kq3ba0cy9nkpqkm0:d1`  2026-07-12 12:15  D1 - Fuse the namespace guard proposal branch [`adr_merge_branch_primitive`]
    - `mse_x6qgkg61dnq26bk4:d1`  2026-07-20 14:29  D1 - Decision [`adr_merge_branch_primitive`]
    - `mse_znfnyxssvhz5srz9:d1`  2026-07-24 13:12  D1 - Gate the primitive, not just the sanctioned commands [`adr_merge_branch_primitive`]

## chain 3 — docs-lifecycle (7 decisions)
- areas: docs-lifecycle x7
- claimed by: `adr_inbox_promotion_workflow`
    - `mse_d2daxtnv8eqx4vqr:d1`  2026-07-08 13:46  D1 - Promote inbox items conservatively [`adr_inbox_promotion_workflow`]
    - `mse_mazbt6cek8m8a6st:d1`  2026-07-16 22:24  D1 - Sequence the surviving platform ideas after React Trail parity [`adr_inbox_promotion_workflow`]
    - `mse_ddba1ztxqhasfbwf:d2`  2026-07-16 23:18  D2 - Give every Inbox idea one coherent owner [`adr_inbox_promotion_workflow`]
    - `mse_wjntbg88n3m0qjss:d1`  2026-07-20 07:45  D1 - Bring the roadmap and the inbox back into truth [`adr_inbox_promotion_workflow`]
    - `mse_y9q4bnv2yckk6w74:d1`  2026-07-20 09:36  D1 - Decision [`adr_inbox_promotion_workflow`]
    - `mse_tx1c338ca1ybr666:d1`  2026-07-20 11:20  D1 - Retire both proposal sets; the crosswalk becomes the surviving re [`adr_inbox_promotion_workflow`]
    - `mse_2geqfa8tg182a77p:d1`  2026-07-20 19:03  D1 - Decision [`adr_inbox_promotion_workflow`]

## chain 4 — trail (6 decisions)
- areas: trail x6
- claimed by: `adr_trail_lifecycle_visualization`
    - `mse_74fb71s2cdrwqrqp:d1`  2026-07-18 10:30  D1 - Decision [`adr_trail_lifecycle_visualization`]
    - `mse_dgc0zvchsqpvjpe7:d1`  2026-07-19 13:11  D1 - Middle-third stability band with distance-eased scrolling [`adr_trail_lifecycle_visualization`]
    - `mse_dgc0zvchsqpvjpe7:d2`  2026-07-19 13:11  D2 - A new corpus opens at the top [`adr_trail_lifecycle_visualization`]
    - `mse_9wsn23n3k8txnm2m:d1`  2026-07-21 16:50  D1 - Surface decisions as Trail rows via the section chunks that alrea [`adr_trail_lifecycle_visualization`]
    - `mse_t5bbdstgmqzagn2y:d1`  2026-07-21 19:47  D1 - Decision [`adr_trail_lifecycle_visualization`]
    - `mse_zm2h343r4shfre3j:d2`  2026-07-24 21:06  D2 - The Trail draws all lifecycle edges by default, weighted by a thr [`adr_trail_lifecycle_visualization`]

## chain 5 — hooks (4 decisions)
- areas: hooks x4
- claimed by: `adr_hook_merge_framework`
    - `ms-7c4e1f9a:d1`  2026-05-27 01:45  D1 - Merge, don't clobber [`adr_hook_merge_framework`]
    - `ms-5e1a9d44:d1`  2026-05-27 14:57  D1 - Cursor retrieval uses sessionStart, not beforeSubmitPrompt [`adr_hook_merge_framework`]
    - `ms-7b3f1e92:d1`  2026-05-29 14:07  D1 - Script filename as the stable identifier for hook upsert [`adr_hook_merge_framework`]
    - `ms-5e366ef4:d2`  2026-06-11 16:58  D2 - Multi-agent wiring reuses the existing merge framework; Copilot a [`adr_hook_merge_framework`]

## chain 6 — skill-architecture (4 decisions)
- areas: skill-architecture x4
- claimed by: `adr_skill_registry_and_generic_skills`
    - `ms-0bd3d8b2:d1`  2026-05-26 22:09  D1 - Use a seeded trigger registry instead of only prose triggers [`adr_skill_registry_and_generic_skills`]
    - `mse_vexkm8da35zj856x:d1`  2026-06-29 21:37  D1 - Decision [`adr_skill_registry_and_generic_skills`]
    - `mse_fp32yxbxy3k3r5x1:d1`  2026-07-05 02:23  D1 - Generic skill content, project specifics stripped [`adr_skill_registry_and_generic_skills`]
    - `mse_542z3qn0azma9mmx:d1`  2026-07-07 12:52  D1 - Decision [`adr_skill_registry_and_generic_skills`]

## chain 7 — docs-lifecycle (4 decisions)
- areas: docs-lifecycle x4
- claimed by: `adr_documentation_lane_structure`
    - `ms-a939b6b4:d2`  2026-06-14 09:52  D2 - Author the functionality audit with data-flow diagrams [`adr_documentation_lane_structure`]
    - `ms-4e1b8a07:d1`  2026-06-14 18:45  D1 - Decision [`adr_documentation_lane_structure`]
    - `mse_21d4kcx6g1vxt0ky:d1`  2026-07-02 18:51  D1 - Decision [`adr_documentation_lane_structure`]
    - `mse_djvwtfx02kjr5j1n:d2`  2026-07-03 11:18  D2 - Refreshed functionality-audit.md [`adr_documentation_lane_structure`]

## chain 8 — topic-vocabulary (4 decisions)
- areas: topic-vocabulary x4
- claimed by: `adr_topic_vocabulary_controlled`
    - `mse_ehm67mqpmsqm00md:d1`  2026-07-10 16:13  D1 - Vocabulary derived from usage, aliases preserve every observed sl [`adr_topic_vocabulary_controlled`]
    - `mse_vy8tq90rr4br8a0z:d1`  2026-07-12 11:49  D1 - Decision [`adr_topic_vocabulary_controlled`]
    - `mse_ke0f6x2v8zmd3yrf:d1`  2026-07-19 20:15  D1 - Decision [`adr_topic_vocabulary_controlled`]
    - `mse_jz0pwv0ngzzxr484:d1`  2026-07-25 11:13  D1 - Raise the inferred-topic cap to 4 to match the corpus, not hold t [`adr_topic_vocabulary_controlled`]

## chain 9 — multi-user-sessions (3 decisions)
- areas: multi-user-sessions x3
- claimed by: `adr_session_layout_participant_gating`
    - `ms-41f4f32a:d1`  2026-06-13 15:08  D1 - Decision [`adr_session_layout_participant_gating`]
    - `ms-3cad2a35:d2`  2026-06-14 16:52  D2 - 2.9.0 read-only dual discovery [`adr_session_layout_participant_gating`]
    - `ms-38098d7a:d1`  2026-06-14 18:18  D1 - Decision [`adr_session_layout_participant_gating`]

## chain 10 — retrieval (3 decisions)
- areas: retrieval x3
- claimed by: `adr_mcp_metadata_and_filters`
    - `mse_77cn2v0rg9na3w0v:d2`  2026-06-15 02:26  D2 - A-P4 MCP metadata and filters [`adr_mcp_metadata_and_filters`]
    - `mse_ztcsrx4hw0b6kxdv:d2`  2026-06-15 20:13  D2 - Read-only filterable API surface [`adr_mcp_metadata_and_filters`]
    - `mse_dbt6c32kk5dk55xs:d1`  2026-07-04 15:08  D1 - Decision [`adr_mcp_metadata_and_filters`]

## chain 11 — package (3 decisions)
- areas: package x3
- claimed by: `adr_trace_boundary`
    - `mse_ztcsrx4hw0b6kxdv:d1`  2026-06-15 20:13  D1 - Separate companion package
    - `mse_eszq6qxf2jck32e8:d1`  2026-06-27 20:37  D1 - Decision
    - `mse_fcecj9hpq4qj16ay:d1`  2026-07-06 06:32  D1 - Decision [`adr_trace_boundary`]

## chain 12 — retrieval (3 decisions)
- areas: retrieval x3
- claimed by: `adr_retrieval_entry_granularity`
    - `ms-845042c7:d1`  2026-05-26 21:26  D1 - Make entry chunks the default MCP memory unit [`adr_retrieval_entry_granularity`]
    - `mse_3n3mp35ekz08t4zb:d2`  2026-07-05 12:20  D2 - Retrieval service extracted; MCP is a wrapper; parity proven by t [`adr_retrieval_entry_granularity`]
    - `mse_pwwz3ys324ght2qs:d1`  2026-07-05 12:45  D1 - Rollup lives in the service (EntryRollup), Lense adapts presentat [`adr_retrieval_entry_granularity`]

## chain 13 — docs-lifecycle (3 decisions)
- areas: docs-lifecycle x3
- claimed by: `adr_proposal_completion_moves_lane`
    - `mse_bqc8am1yq8sv5s92:d1`  2026-07-02 19:55  D1 - Decision [`adr_proposal_completion_moves_lane`]
    - `mse_r1ey59bbv1jsseth:d1`  2026-07-04 11:06  D1 - Decision [`adr_proposal_completion_moves_lane`]
    - `mse_9m2jk06hgx7ctrm1:d3`  2026-07-05 02:27  D3 - Logic-capture source report moved to completed [`adr_proposal_completion_moves_lane`]

## chain 14 — upgrade-workflow (3 decisions)
- areas: upgrade-workflow x3
- claimed by: `adr_safe_process_and_upgrade_workflow`
    - `mse_2rvggg1jy6y4m1g3:d1`  2026-07-08 07:49  D1 - Safe process MVP [`adr_safe_process_and_upgrade_workflow`]
    - `mse_zx704zcr1sd3k91n:d1`  2026-07-08 14:46  D1 - Decision [`adr_safe_process_and_upgrade_workflow`]
    - `mse_etm5m5682sseasgm:d3`  2026-07-12 00:38  D3 - Resolve process ownership through Memory Seed [`adr_safe_process_and_upgrade_workflow`]

## chain 15 — windows-encoding (3 decisions)
- areas: windows-encoding x3
- claimed by: `adr_windows_encoding_policy`
    - `mse_76r59d5yxcqy0kb8:d2`  2026-07-07 23:18  D2 - Encoding policy implementation [`adr_windows_encoding_policy`]
    - `mse_2rvggg1jy6y4m1g3:d2`  2026-07-08 07:49  D2 - Encoding check slice [`adr_windows_encoding_policy`]
    - `mse_74ddxsena9nj2afk:d1`  2026-07-08 18:40  D1 - Decision [`adr_windows_encoding_policy`]

## chain 16 — memory-trace (3 decisions)
- areas: memory-trace x3
- claimed by: `adr_trace_trail_first_ui`
    - `mse_loe4c3vbaeeq22dt:d1`  2026-07-11 13:00  D1 - Promote the new plan package [`adr_trace_trail_first_ui`]
    - `mse_rsjbgk4qnyrtvv09:d1`  2026-07-15 17:33  D1 - Decision [`adr_trace_trail_first_ui`]
    - `mse_rqkgatgt5eh55yb8:d1`  2026-07-16 14:14  D1 - Serve the React shell as an additive packaged route [`adr_trace_trail_first_ui`]

## ADR candidates

0 of 16 chains are unclaimed. Each is a concern with recorded lineage and no ADR - the strongest kind of candidate, because the decisions are already connected and already topic-coherent.


**Cost if all 0 were founded: 0 diagram answers** — one per ADR, not one per attached decision. A diagram block keys on `adr_id` and is filed under the head's session date, so an ADR is looked at once and the verdict recorded (a diagram, or `diagram_status: not_applicable` with a reason); ESR counts `adrs_without_diagram_answer` over ADR ids. Attaching 11 decisions to one ADR owes one answer, not eleven.

## Chains that have grown since review

3 chains carry decisions the claiming ADR does not name. The concern was reviewed at one size and the lineage has since extended, so the review is stale in one of two ways: the new decisions belong to the concern and should be attached, or the chain has grown into a SECOND concern that should be split off into its own ADR. Either way it wants a look.

- `adr_trace_boundary` — 2 of 3 members unnamed
    - `mse_ztcsrx4hw0b6kxdv:d1`  2026-06-15 20:13  D1 - Separate companion package
    - `mse_eszq6qxf2jck32e8:d1`  2026-06-27 20:37  D1 - Decision
- `adr_control_file_authority` — 1 of 2 members unnamed
    - `mse_v9stt3nxkg7s4m84:d1`  2026-07-20 13:31  D1 - Decision
- `adr_topic_backfill_rejected` — 1 of 2 members unnamed
    - `mse_hqzcxnkehb7mbcma:d1`  2026-08-07 20:29  D1 - The swarm works, and two write-path lessons are now in the br

## Candidate pairs (two linked decisions)

23 of 28 pairs are unclaimed. A pair is a candidate, not a chain: two decisions sharing an area and one edge may be a concern, or may just be two decisions. Each needs an architectural judgement before it is founded - read both, and found only what a reader would expect to find recorded as a standing concern.

- **hooks**
    - `ms-9f3a2b1c:d2`  2026-05-27 01:30  D2 - Python for cross-platform compatibility
    - `ms-2d8b4c7e:d1`  2026-05-27 02:00  D1 - Shared script with --codex flag, not two separate scripts
- **hooks**
    - `ms-2d8b4c7e:d2`  2026-05-27 02:00  D2 - systemMessage for Codex (not additionalContext)
    - `ms-8d2f4a1e:d1`  2026-05-27 14:10  D1 - Use systemMessage for Stop hook output
- **session-logging**
    - `ms-f83a27d3:d1`  2026-05-26 19:59  D1 - Rationale is required only when it matters
    - `ms-db2d715c:d1`  2026-05-26 20:40  D1 - Use DRAFT for compact decision records
- **related-entries**
    - `mse_a67jnwa1048dn3wc:d1`  2026-06-15 22:57  D1 - Decision
    - `mse_1cabc5sw1g4hkb25:d1`  2026-07-17 02:05  D1 - Ship `link add`, refuse any non-newest source
- **diagram-view**
    - `mse_1xexde5bhezse690:d3`  2026-07-13 07:46  D3 - Arc 2d flowchart renderer honours `<br/>`
    - `mse_fdt9nfjrtfep0d7z:d1`  2026-07-16 20:20  D1 - Decision
- **session-logging**
    - `mse_2b1bthj8x03nfe91:d1`  2026-07-13 14:07  D1 - Decision
    - `mse_skcmezqbxxh5dtp6:d2`  2026-07-19 22:12  D2 - Fix the body-extraction bug and repair the one entry it expos
- **inspector**
    - `mse_wv9pzg6ayy0wa61j:d1`  2026-07-17 17:35  D1 - Decision
    - `mse_2pgcs90wcbhhk2kc:d1`  2026-07-19 13:47  D1 - Spell the DRAFT grammar out in the reader, with files as pill
- **package**
    - `mse_x82bptzravde7h4x:d1`  2026-07-05 23:47  D1 - Memory Trace name is clear; findings recorded in the Trace pl
    - `mse_38mmhbyvxyta2wgd:d1`  2026-07-06 00:04  D1 - Decision
- **package**
    - `mse_3n3mp35ekz08t4zb:d1`  2026-07-05 12:20  D1 - memory-seed-trail availability: package free, but "Memory Tra
    - `mse_kandgwtqkcydhvq7:d1`  2026-07-05 14:05  D1 - Distinguish the inert PyPI stub from the real GitHub "skill";
- **schema**
    - `mse_t22wn997q5005zjp:d1`  2026-07-10 12:34  D1 - Propose a typed `evolves` edge rather than stretching `supers
    - `mse_4670mpw532yec14w:d1`  2026-07-10 12:38  D1 - Decision
- **mermaid**
    - `mse_4f8g7h2j9k3m5n6p:d1`  2026-07-07 11:35  D1 - Decision
    - `mse_m6amd5db4c7s8sfw:d2`  2026-07-10 03:28  D2 - Strengthen sidecar triggers
- **docs-lifecycle**
    - `mse_5nr2pvjyrs92bvj2:d1`  2026-07-17 05:00  D1 - Ship `docs check`; the missing gate was proven by the migrati
    - `mse_ntkt6m0pqd0g8c9j:d1`  2026-07-17 14:10  D1 - Decision
- **skill-architecture**
    - `mse_nyk16t2d8xexetgv:d1`  2026-07-09 19:43  D1 - Decision
    - `mse_5trzymn43k92ky7z:d4`  2026-07-29 12:34  D4 - The new budget is documented as a real, citable fact in its o
- **docs-lifecycle**
    - `mse_dpf02qvaymr40nm7:d5`  2026-07-10 15:05  D5 - Alignment repairs applied (Phase 2 consolidation)
    - `mse_7g027mnv9xbmh5j7:d1`  2026-07-16 07:29  D1 - Decision
- **memory-trace**
    - `mse_7qfd6tx63txn9v3v:d1`  2026-07-21 10:58  D1 - Decision
    - `mse_cdndmm2p0dmbkbq9:d1`  2026-07-21 19:25  D1 - One line per pair, taken by the strongest relationship
- **session-fuse**
    - `mse_et9pkwnsm5cmz3h9:d1`  2026-07-24 12:35  D1 - Fail-open to `automatic`, opt this repo into `manual`
    - `mse_84hmbf34tw8mm9qe:d1`  2026-07-30 12:39  D1 - Decision
- **docs-lifecycle**
    - `mse_8e7e78fx4hspcfta:d1`  2026-07-05 11:31  D1 - Next goal pass is Phase 1 retrieval plus decision diagrams, n
    - `mse_wzr3rh9cjce924vf:d1`  2026-07-07 13:33  D1 - Decision
- **topic-vocabulary**
    - `mse_dpf02qvaymr40nm7:d3`  2026-07-10 15:05  D3 - Topics starter vocabulary derived from existing slugs
    - `mse_903jqy9v4pr8g388:d3`  2026-07-10 15:25  D3 - Topics slug contract pinned (approved)
- **inspector**
    - `mse_9xfpvhqrm44jedce:d1`  2026-07-17 18:25  D1 - Decision
    - `mse_cdndmm2p0dmbkbq9:d2`  2026-07-21 19:25  D2 - Following a link never disturbs the workspace
- **seed-core**
    - `mse_a0bxp5n1wcnsjxvw:d3`  2026-07-15 18:05  D3 - Add narrow provenance/authority and quality gates
    - `mse_b1q6bjqv5w1zyn2k:d1`  2026-07-17 02:45  D1 - Ship v0 with two metrics measured and three honestly unmeasur
- **diagram-view**
    - `mse_rqkgatgt5eh55yb8:d2`  2026-07-16 14:14  D2 - Keep the first Cytoscape graph bounded and explicitly incompl
    - `mse_aja6sm9019315yh1:d1`  2026-07-18 19:30  D1 - Decision
- **docs-lifecycle**
    - `mse_fyz3rdhky8pyem0s:d1`  2026-07-08 07:25  D1 - Decision
    - `mse_qkvkd8qkza7kk4y8:d1`  2026-07-17 01:05  D1 - Surface the Trace distribution plan in NEXT_STEPS rather than
- **test-suite**
    - `mse_gvq7xhvgekts00at:d3`  2026-08-04 02:05  D3 - Pin the Claude arm to the fixture's own MCP config
    - `mse_r32k8mk46ky8rdtv:d3`  2026-08-04 11:33  D3 - Retire the worktree-guard confound as measured and absent

