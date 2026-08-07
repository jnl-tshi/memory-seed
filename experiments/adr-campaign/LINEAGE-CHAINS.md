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
    - `ms-a3f91c2b:d1`  2026-05-29 15:17  D1 - Decision
    - `ms-6a09aea8:d1`  2026-06-03 22:54  D1 - Claude MCP server belongs in project-root .mcp.json, not settings [`adr_mcp_integration_surface`]
    - `ms-2cd452e4:d1`  2026-06-03 23:43  D1 - Codex MCP belongs in project .codex/config.toml, written via zero [`adr_mcp_integration_surface`]
    - `ms-2cd452e4:d2`  2026-06-03 23:43  D2 - Surface the trust requirement (Codex's silent-failure trap) [`adr_mcp_integration_surface`]
    - `ms-6eeb512f:d1`  2026-06-03 23:55  D1 - Decision
    - `mse_81v7vk4x5ys3k2n0:d3`  2026-07-10 04:27  D3 - Add MCP and skill surfaces [`adr_mcp_integration_surface`]
    - `mse_vzsef0fmpsde2jh4:d1`  2026-07-19 20:01  D1 - Gate the MCP write surface, retire the ungated pair [`adr_mcp_integration_surface`]

## chain 2 — session-fuse (8 decisions)
- areas: session-fuse x8
- claimed by: `adr_merge_branch_primitive`
    - `mse_81v7vk4x5ys3k2n0:d1`  2026-07-10 04:27  D1 - Make fuse Memory Seed-aware
    - `mse_azn6bejpd9xpmh3f:d2`  2026-07-10 06:20  D2 - Scope branch-side validation to the branch delta
    - `mse_dr5eprnhrctqeeg3:d1`  2026-07-10 12:03  D1 - Wrapper command, not a merge driver or blocking hook [`adr_merge_branch_primitive`]
    - `mse_vm7trfd4dbd5yvnn:d1`  2026-07-10 14:18  D1 - Decision
    - `mse_w2fk7qnx4t9b3vmh:d1`  2026-07-11 15:58  D1 - Decision
    - `mse_kq3ba0cy9nkpqkm0:d1`  2026-07-12 12:15  D1 - Fuse the namespace guard proposal branch
    - `mse_x6qgkg61dnq26bk4:d1`  2026-07-20 14:29  D1 - Decision
    - `mse_znfnyxssvhz5srz9:d1`  2026-07-24 13:12  D1 - Gate the primitive, not just the sanctioned commands

## chain 3 — docs-lifecycle (7 decisions)  **UNCLAIMED**
- areas: docs-lifecycle x7
- claimed by: *nothing*
    - `mse_d2daxtnv8eqx4vqr:d1`  2026-07-08 13:46  D1 - Promote inbox items conservatively
    - `mse_mazbt6cek8m8a6st:d1`  2026-07-16 22:24  D1 - Sequence the surviving platform ideas after React Trail parity
    - `mse_ddba1ztxqhasfbwf:d2`  2026-07-16 23:18  D2 - Give every Inbox idea one coherent owner
    - `mse_wjntbg88n3m0qjss:d1`  2026-07-20 07:45  D1 - Bring the roadmap and the inbox back into truth
    - `mse_y9q4bnv2yckk6w74:d1`  2026-07-20 09:36  D1 - Decision
    - `mse_tx1c338ca1ybr666:d1`  2026-07-20 11:20  D1 - Retire both proposal sets; the crosswalk becomes the surviving re
    - `mse_2geqfa8tg182a77p:d1`  2026-07-20 19:03  D1 - Decision

## chain 4 — trail (6 decisions)  **UNCLAIMED**
- areas: trail x6
- claimed by: *nothing*
    - `mse_74fb71s2cdrwqrqp:d1`  2026-07-18 10:30  D1 - Decision
    - `mse_dgc0zvchsqpvjpe7:d1`  2026-07-19 13:11  D1 - Middle-third stability band with distance-eased scrolling
    - `mse_dgc0zvchsqpvjpe7:d2`  2026-07-19 13:11  D2 - A new corpus opens at the top
    - `mse_9wsn23n3k8txnm2m:d1`  2026-07-21 16:50  D1 - Surface decisions as Trail rows via the section chunks that alrea
    - `mse_t5bbdstgmqzagn2y:d1`  2026-07-21 19:47  D1 - Decision
    - `mse_zm2h343r4shfre3j:d2`  2026-07-24 21:06  D2 - The Trail draws all lifecycle edges by default, weighted by a thr

## chain 5 — hooks (4 decisions)  **UNCLAIMED**
- areas: hooks x4
- claimed by: *nothing*
    - `ms-7c4e1f9a:d1`  2026-05-27 01:45  D1 - Merge, don't clobber
    - `ms-5e1a9d44:d1`  2026-05-27 14:57  D1 - Cursor retrieval uses sessionStart, not beforeSubmitPrompt
    - `ms-7b3f1e92:d1`  2026-05-29 14:07  D1 - Script filename as the stable identifier for hook upsert
    - `ms-5e366ef4:d2`  2026-06-11 16:58  D2 - Multi-agent wiring reuses the existing merge framework; Copilot a

## chain 6 — skill-architecture (4 decisions)
- areas: skill-architecture x4
- claimed by: `adr_skill_registry_and_generic_skills`
    - `ms-0bd3d8b2:d1`  2026-05-26 22:09  D1 - Use a seeded trigger registry instead of only prose triggers [`adr_skill_registry_and_generic_skills`]
    - `mse_vexkm8da35zj856x:d1`  2026-06-29 21:37  D1 - Decision [`adr_skill_registry_and_generic_skills`]
    - `mse_fp32yxbxy3k3r5x1:d1`  2026-07-05 02:23  D1 - Generic skill content, project specifics stripped [`adr_skill_registry_and_generic_skills`]
    - `mse_542z3qn0azma9mmx:d1`  2026-07-07 12:52  D1 - Decision [`adr_skill_registry_and_generic_skills`]

## chain 7 — docs-lifecycle (4 decisions)  **UNCLAIMED**
- areas: docs-lifecycle x4
- claimed by: *nothing*
    - `ms-a939b6b4:d2`  2026-06-14 09:52  D2 - Author the functionality audit with data-flow diagrams
    - `ms-4e1b8a07:d1`  2026-06-14 18:45  D1 - Decision
    - `mse_21d4kcx6g1vxt0ky:d1`  2026-07-02 18:51  D1 - Decision
    - `mse_djvwtfx02kjr5j1n:d2`  2026-07-03 11:18  D2 - Refreshed functionality-audit.md

## chain 8 — topic-vocabulary (4 decisions)  **UNCLAIMED**
- areas: topic-vocabulary x4
- claimed by: *nothing*
    - `mse_ehm67mqpmsqm00md:d1`  2026-07-10 16:13  D1 - Vocabulary derived from usage, aliases preserve every observed sl
    - `mse_vy8tq90rr4br8a0z:d1`  2026-07-12 11:49  D1 - Decision
    - `mse_ke0f6x2v8zmd3yrf:d1`  2026-07-19 20:15  D1 - Decision
    - `mse_jz0pwv0ngzzxr484:d1`  2026-07-25 11:13  D1 - Raise the inferred-topic cap to 4 to match the corpus, not hold t

## chain 9 — multi-user-sessions (3 decisions)  **UNCLAIMED**
- areas: multi-user-sessions x3
- claimed by: *nothing*
    - `ms-41f4f32a:d1`  2026-06-13 15:08  D1 - Decision
    - `ms-3cad2a35:d2`  2026-06-14 16:52  D2 - 2.9.0 read-only dual discovery
    - `ms-38098d7a:d1`  2026-06-14 18:18  D1 - Decision

## chain 10 — retrieval (3 decisions)  **UNCLAIMED**
- areas: retrieval x3
- claimed by: *nothing*
    - `mse_77cn2v0rg9na3w0v:d2`  2026-06-15 02:26  D2 - A-P4 MCP metadata and filters
    - `mse_ztcsrx4hw0b6kxdv:d2`  2026-06-15 20:13  D2 - Read-only filterable API surface
    - `mse_dbt6c32kk5dk55xs:d1`  2026-07-04 15:08  D1 - Decision

## chain 11 — package (3 decisions)
- areas: package x3
- claimed by: `adr_trace_boundary`
    - `mse_ztcsrx4hw0b6kxdv:d1`  2026-06-15 20:13  D1 - Separate companion package
    - `mse_eszq6qxf2jck32e8:d1`  2026-06-27 20:37  D1 - Decision
    - `mse_fcecj9hpq4qj16ay:d1`  2026-07-06 06:32  D1 - Decision [`adr_trace_boundary`]

## chain 12 — retrieval (3 decisions)  **UNCLAIMED**
- areas: retrieval x3
- claimed by: *nothing*
    - `ms-845042c7:d1`  2026-05-26 21:26  D1 - Make entry chunks the default MCP memory unit
    - `mse_3n3mp35ekz08t4zb:d2`  2026-07-05 12:20  D2 - Retrieval service extracted; MCP is a wrapper; parity proven by t
    - `mse_pwwz3ys324ght2qs:d1`  2026-07-05 12:45  D1 - Rollup lives in the service (EntryRollup), Lense adapts presentat

## chain 13 — docs-lifecycle (3 decisions)  **UNCLAIMED**
- areas: docs-lifecycle x3
- claimed by: *nothing*
    - `mse_bqc8am1yq8sv5s92:d1`  2026-07-02 19:55  D1 - Decision
    - `mse_r1ey59bbv1jsseth:d1`  2026-07-04 11:06  D1 - Decision
    - `mse_9m2jk06hgx7ctrm1:d3`  2026-07-05 02:27  D3 - Logic-capture source report moved to completed

## chain 14 — upgrade-workflow (3 decisions)  **UNCLAIMED**
- areas: upgrade-workflow x3
- claimed by: *nothing*
    - `mse_2rvggg1jy6y4m1g3:d1`  2026-07-08 07:49  D1 - Safe process MVP
    - `mse_zx704zcr1sd3k91n:d1`  2026-07-08 14:46  D1 - Decision
    - `mse_etm5m5682sseasgm:d3`  2026-07-12 00:38  D3 - Resolve process ownership through Memory Seed

## chain 15 — windows-encoding (3 decisions)  **UNCLAIMED**
- areas: windows-encoding x3
- claimed by: *nothing*
    - `mse_76r59d5yxcqy0kb8:d2`  2026-07-07 23:18  D2 - Encoding policy implementation
    - `mse_2rvggg1jy6y4m1g3:d2`  2026-07-08 07:49  D2 - Encoding check slice
    - `mse_74ddxsena9nj2afk:d1`  2026-07-08 18:40  D1 - Decision

## chain 16 — memory-trace (3 decisions)  **UNCLAIMED**
- areas: memory-trace x3
- claimed by: *nothing*
    - `mse_loe4c3vbaeeq22dt:d1`  2026-07-11 13:00  D1 - Promote the new plan package
    - `mse_rsjbgk4qnyrtvv09:d1`  2026-07-15 17:33  D1 - Decision
    - `mse_rqkgatgt5eh55yb8:d1`  2026-07-16 14:14  D1 - Serve the React shell as an additive packaged route

## ADR candidates

12 of 16 chains are unclaimed. Each is a concern with recorded lineage and no ADR - the strongest kind of candidate, because the decisions are already connected and already topic-coherent.

- **docs-lifecycle** (7 decisions, chain 3): `mse_d2daxtnv8eqx4vqr:d1` … `mse_2geqfa8tg182a77p:d1`
    - suggested head: `mse_2geqfa8tg182a77p:d1` — D1 - Decision
- **trail** (6 decisions, chain 4): `mse_74fb71s2cdrwqrqp:d1` … `mse_zm2h343r4shfre3j:d2`
    - suggested head: `mse_zm2h343r4shfre3j:d2` — D2 - The Trail draws all lifecycle edges by default, weighted by a
- **hooks** (4 decisions, chain 5): `ms-7c4e1f9a:d1` … `ms-5e366ef4:d2`
    - suggested head: `ms-5e366ef4:d2` — D2 - Multi-agent wiring reuses the existing merge framework; Copil
- **docs-lifecycle** (4 decisions, chain 7): `ms-a939b6b4:d2` … `mse_djvwtfx02kjr5j1n:d2`
    - suggested head: `mse_djvwtfx02kjr5j1n:d2` — D2 - Refreshed functionality-audit.md
- **topic-vocabulary** (4 decisions, chain 8): `mse_ehm67mqpmsqm00md:d1` … `mse_jz0pwv0ngzzxr484:d1`
    - suggested head: `mse_jz0pwv0ngzzxr484:d1` — D1 - Raise the inferred-topic cap to 4 to match the corpus, not ho
- **multi-user-sessions** (3 decisions, chain 9): `ms-41f4f32a:d1` … `ms-38098d7a:d1`
    - suggested head: `ms-38098d7a:d1` — D1 - Decision
- **retrieval** (3 decisions, chain 10): `mse_77cn2v0rg9na3w0v:d2` … `mse_dbt6c32kk5dk55xs:d1`
    - suggested head: `mse_dbt6c32kk5dk55xs:d1` — D1 - Decision
- **retrieval** (3 decisions, chain 12): `ms-845042c7:d1` … `mse_pwwz3ys324ght2qs:d1`
    - suggested head: `mse_pwwz3ys324ght2qs:d1` — D1 - Rollup lives in the service (EntryRollup), Lense adapts prese
- **docs-lifecycle** (3 decisions, chain 13): `mse_bqc8am1yq8sv5s92:d1` … `mse_9m2jk06hgx7ctrm1:d3`
    - suggested head: `mse_9m2jk06hgx7ctrm1:d3` — D3 - Logic-capture source report moved to completed
- **upgrade-workflow** (3 decisions, chain 14): `mse_2rvggg1jy6y4m1g3:d1` … `mse_etm5m5682sseasgm:d3`
    - suggested head: `mse_etm5m5682sseasgm:d3` — D3 - Resolve process ownership through Memory Seed
- **windows-encoding** (3 decisions, chain 15): `mse_76r59d5yxcqy0kb8:d2` … `mse_74ddxsena9nj2afk:d1`
    - suggested head: `mse_74ddxsena9nj2afk:d1` — D1 - Decision
- **memory-trace** (3 decisions, chain 16): `mse_loe4c3vbaeeq22dt:d1` … `mse_rqkgatgt5eh55yb8:d1`
    - suggested head: `mse_rqkgatgt5eh55yb8:d1` — D1 - Serve the React shell as an additive packaged route

**Cost if all 12 were founded: 12 diagram answers** — one per ADR, not one per attached decision. A diagram block keys on `adr_id` and is filed under the head's session date, so an ADR is looked at once and the verdict recorded (a diagram, or `diagram_status: not_applicable` with a reason); ESR counts `adrs_without_diagram_answer` over ADR ids. Attaching 11 decisions to one ADR owes one answer, not eleven.

