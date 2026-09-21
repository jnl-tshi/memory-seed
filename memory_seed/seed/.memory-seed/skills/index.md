---
memory-system-version: 2.21
tags:
  - memory-seed
  - skill-registry
  - trigger-registry
---

# Skill Trigger Registry

This registry is the deterministic trigger map for universal Memory Seed skills. Read it during operating-mode startup, then lazy-load only the full skill files that match the active task.

```yaml
trigger_registry_version: 1
default_behavior:
  read_this_file_at_startup: true
  lazy_load_full_skills: true
  evaluate_order: listed
  load_every_matching_required_skill: true
  smallest_sufficient_skill_set: true
  ambiguity_policy: ask_when_durable
  local_registry_precedence: nearest_runtime_first
  inherited_parent_skills: apply_when_not_disabled_or_overridden_locally

skills:
  - skill: code_search.md
    required: true
    load_when:
      - source code exploration
      - symbol lookup
      - call path or dependency tracing
      - repository structure search
      - broad grep or full-file read would otherwise be used
    do_not_load_when:
      - task only touches memory control-plane docs
      - exact file path and required lines are already known

  - skill: graphify_analysis.md
    required: true
    load_when:
      - architecture, dependency-impact, call-path, community, or structural-code analysis is needed
      - deciding which files or symbols are affected by a proposed code change
    do_not_load_when:
      - routine semantic or symbol lookup (use code_search.md and Semble)

  - skill: agent_collaboration.md
    required: true
    load_when:
      - coordinating subagents, branch/worktree coordination, or multi-developer agent workflows
      - creating or reviewing feature branches for agent work
      - using worktrees for parallel code-writing agents
      - preparing worker, validator, or merge-conflict handoffs
      - using memory_branch_status, memory_worktree_guard, or memory_session_fuse_preview MCP tools
      - initializing, appending, inspecting, rebinding, or preparing/finalizing a Reflection Board v1 ledger or its trust
    do_not_load_when:
      - direct single-agent edits with no branch, worktree, merge, handoff, or Reflection Board implications

  - skill: superpowers_integration.md
    required: true
    load_when:
      - routing independent read-only investigation to Superpowers parallel dispatch
      - routing an approved multi-task same-session plan to Superpowers SDD
      - verifying optional Superpowers availability, version, scratch isolation, or the return handoff
      - deciding whether an external execution workflow may run inside a Memory Seed worktree
    do_not_load_when:
      - Superpowers is unavailable and the task remains entirely in the normal Memory Seed workflow
      - a mechanical one-task edit, unresolved architecture, coupled writes, or shared control-plane work

  - skill: history_retrieval.md
    required: true
    load_when:
      - prior decisions, rationale, unresolved risks, or release history matter
      - reviews, audits, or recommendations may conclude that behavior is redundant, obsolete, removable, replaceable, superseded, or ready to consolidate
      - using memory_search or memory_get_chunk
      - filling an entry's related_entries or resolving the session-log append target via memory_link_suggest, memory_link_show, or memory_session_append
      - inspecting controlled topics via memory_topics_list, memory_topic_inspect, or memory_topics_check
      - reconciling current files with older session history
      - deciding whether older memory conflicts with current authority files
    do_not_load_when:
      - task is a small obvious edit and current files plus index.md and policy.md are sufficient

  - skill: session_logging.md
    required: true
    load_when:
      - writing, validating, or repairing session entries
      - deciding DRAFTS labels, entry shapes, topics, related_entries, or append-only chronology
      - changing session log schema or examples
      - preparing or finalizing ordinary session receipts for Reflection Board v1 close
    do_not_load_when:
      - only reading recent session state without writing or repairing logs

  - skill: compact_mermaid_diagrams.md
    required: true
    load_when:
      - authoring or revising Mermaid diagrams of any type
      - choosing which Mermaid diagram type fits what is being drawn
      - recording an ADR sidecar, which should normally carry a diagram
      - choosing between Mermaid and D2 for documentation diagrams
      - authoring or reviewing D2 only for dense architecture or nested system diagrams
      - Mermaid diagram layout is too wide, too tall, stretched, or sparse
      - preventing isolated single nodes, orphan baselines, or runaway horizontal rows
      - authoring a diagram sidecar under `.memory-seed/sessions/diagrams/`
    do_not_load_when:
      - prose or lists communicate the structure as well as a diagram
      - the task has no Mermaid, D2, or diagram layout concern
      - editing sequence diagrams without graph or flowchart layout pressure

  - skill: orientation.md
    required: true
    load_when:
      - orienting at the start of a session (running `memory-seed situate` or /situate)
      - reconciling local git, version, session, and worktree state before acting
      - a stale in-context snapshot or frozen worktree may misrepresent current state
      - setting the operating-mode variables on the first substantive message (the gate), or re-running
        the gate on a later turn once context has been summarized
    do_not_load_when:
      - mid-task work after orientation and the operating-mode gate are already established

  - skill: end_of_turn.md
    required: true
    load_when:
      - running End Of Turn, ESR, or /esr
      - performing closeout, consolidation review, orphan sweep, persona evolution, skill evolution, or baseline-promotion review
      - closing or expiring a Reflection Board v1 chain, or resolving its pending close receipts
    do_not_load_when:
      - ordinary mid-task work with no closeout or Reflection Board expiry/receipt work

  - skill: worktree_reconciliation.md
    required: true
    load_when:
      - reconciling dirty, stale, or deletion-candidate Git worktrees
      - deciding whether a worktree or deregistered worktree residue is safe to remove
      - recovering or classifying unique, duplicated, referenced, generated, or uncertain worktree content
      - producing a cleanup recommendation from branch-local session history and Git evidence
    do_not_load_when:
      - only listing current worktrees with no cleanup assessment or recommendation
      - immediate cleanup of the exact clean source worktree after guarded branch integration

  - skill: adr_sweep.md
    required: true
    load_when:
      - running an ADR sweep, audit, or corpus-wide ADR review
      - reviewing ADR attachment candidates, ADR review queue items, or ADR sweep candidates from ESR
      - finding decision chains or pairs that do not yet have an ADR
      - reviewing grown decision chains for ADR membership or concern splitting
      - preparing batch ADR promotion, revision, reviewed-no-change, or deferral recommendations
    do_not_load_when:
      - reading or showing one known ADR with no corpus-wide review
      - recording the current turn's decision and its content-bound ADR review (use session_logging.md)

  - skill: memory_hygiene.md
    required: true
    load_when:
      - secrets, credentials, private identities, client data, publishable memory, or reusable-template hygiene are involved
      - editing memory content that may later become public
      - changing seed templates with privacy or portability implications
    do_not_load_when:
      - task has no privacy, public-memory, or reusable-template surface

  - skill: proposal_lifecycle.md
    required: true
    load_when:
      - triaging proposals, research reports, or task documents in docs/1_Inbox or docs/inbox
      - promoting proposal documents from docs/1_Inbox to docs/2_Todo or from docs/inbox to docs/todo
      - moving source-only research or reference material into docs/4_Reference or docs/reference
      - moving shipped proposals to the completed lane and rejected/replaced/deferred proposals to their own lanes (docs/5_Completed, docs/6_Rejected, docs/7_Replaced, docs/8_Deferred or the project equivalents)
      - reorganizing proposal folders, roadmap docs, or completed-proposal archives
      - updating NEXT_STEPS, 0_NEXT_STEPS, or functionality-audit because proposal status changed
    do_not_load_when:
      - ordinary documentation edit with no proposal, roadmap, inbox, todo, reference, or completed status change
      - code-only implementation work where proposal files are not being moved or resolved

  - skill: design_discovery.md
    required: true
    load_when:
      - making a consequential new product, architectural, data, safety, or workflow choice
      - choosing a new capability, component, policy, workflow, or data approach before implementation
      - deciding whether uncertainty warrants a bounded trial before committing to an approach
      - starting a new work tranche whose next-steps roadmap declares a design discovery gate
    do_not_load_when:
      - routine work directly follows an already assessed decision whose scope and evidence remain current, after any declared tranche-entry gate is complete
      - a task only executes an approved detailed plan and introduces no consequential new choice

  - skill: subproject_runtime.md
    required: true
    load_when:
      - creating, repairing, or reviewing a nested .memory-seed runtime
      - deciding parent/root summaries, inheritance choices, or bootstrap target boundaries
      - work crosses root and sub-project runtime boundaries
    do_not_load_when:
      - work stays inside the current runtime and does not affect runtime topology

  - skill: data_architecture.md
    required: true
    load_when:
      - changing durable data structures
      - changing indexes or ranking behavior
      - changing schemas, persistence, cache format, or retrieval contracts
      - changing semantic memory extraction or scoring
    do_not_load_when:
      - documentation-only wording change with no data contract impact

  - skill: local_compilation.md
    required: true
    load_when:
      - validating local build, test, package, or CLI behavior
      - changing dependency or packaging configuration
      - reproducing a local failure
    do_not_load_when:
      - analysis-only task with no local validation needed

  - skill: systematic_debugging.md
    required: true
    load_when:
      - diagnosing an unexpected failure, regression, or unexplained behaviour
      - reproducing a defect or tracing its causal path before a fix
      - repeated hypothesis-led debugging attempts require architectural reconsideration
    do_not_load_when:
      - the cause is established and a narrow routine change has proportionate verification
      - no unexpected behaviour is being diagnosed

  - skill: memory_consolidation.md
    required: true
    load_when:
      - reviewing compact output
      - promoting session history into durable memory
      - reconciling sessions with index.md or policy.md
      - deciding whether long session logs need summarizing
    do_not_load_when:
      - appending a normal session entry only

  - skill: memory_doctor.md
    required: true
    load_when:
      - runtime health is uncertain
      - bootstrap completion is uncertain
      - migration or archive integrity is being checked
      - seed/live sync is being changed
      - control-plane repair is needed
    do_not_load_when:
      - ordinary implementation work in a healthy runtime

  - skill: release_publishing.md
    required: true
    load_when:
      - preparing or publishing a package release
      - changing release process, tags, changelog, or packaging metadata
      - verifying release workflow state
    do_not_load_when:
      - local-only development with no release impact

  - skill: security_triage.md
    required: true
    load_when:
      - security-sensitive code or policy changes
      - secrets, credentials, auth, permissions, user data, payments, network exposure, or destructive operations are involved
      - reviewing public-memory hygiene risks
    do_not_load_when:
      - task has no security, privacy, or destructive-operation surface

  - skill: risk_signaling.md
    required: true
    load_when:
      - ambiguous, underspecified, broad, or outside-explicit-authorization actions
      - destructive, irreversible, externally visible, financial, or high-blast-radius actions
      - shared control-plane state, seed templates, lockfiles, or session/memory files may be changed
      - deciding whether to proceed, proceed-and-flag, propose-and-wait, or stop
    do_not_load_when:
      - routine, reversible work that is explicitly requested and follows established local patterns

  - skill: skill_architecture.md
    required: true
    load_when:
      - adding, removing, renaming, splitting, or refactoring Memory Seed skills
      - editing .memory-seed/skills/index.md trigger entries
      - changing core skill names, optional profiles, or skill selection behavior
      - moving procedural guidance from agent-rules.md into a lazy-loaded skill
      - deciding whether behavior belongs in agent-rules.md, policy.md, a skill, or a profile
    do_not_load_when:
      - merely using an existing skill for its normal task
      - ordinary documentation edits with no skill, profile, registry, or control-plane boundary impact

  - skill: developer-rendered-ui-debugging.md
    required: false
    persona: developer
    load_when:
      - debugging local browser UI behavior
      - rendered frontend click, hover, scroll, layout, theme, or cache regressions
      - SVG, canvas, graph, timeline, or pane interaction bugs
    do_not_load_when:
      - backend-only changes
      - static documentation changes
      - no browser-rendered behavior is involved

  - skill: document_ingestion.md
    required: true
    load_when:
      - reading or ingesting a binary document as Markdown
      - needing the content of a `.docx`, `.pdf`, `.pptx`, or `.xlsx` as text
      - converting a source document so a file-reading agent can read it
    do_not_load_when:
      - the source is already plain text, Markdown, or source code (use code_search)
      - producing or editing an Office document (use office_document_editing)

  - skill: office_document_editing.md
    required: true
    load_when:
      - creating or editing an Office document (.docx/.pptx/.xlsx) programmatically
      - the document contains fields (citations, captions, cross-references, TOC) or content controls
    do_not_load_when:
      - only reading a document as text (use document_ingestion)
      - editing plain text, Markdown, or source code

  - skill: docx_render_windows.md
    required: true
    load_when:
      - rendering .docx pages to images on Windows
      - visual QA of a rendered Word document on Windows
      - LibreOffice conversion hangs or a bundled document renderer is slow or hung
      - DOCX-to-PNG page verification
    do_not_load_when:
      - reading a document as text only (use document_ingestion)
      - editing document content without render verification (use office_document_editing)
      - not on Windows and no Windows render target is involved

  - skill: copywriter-conversion.md
    required: false
    persona: copywriter
    load_when:
      - writing or revising landing page copy
      - writing headlines for README, Product Hunt, or GitHub description
      - drafting email subject lines or body copy for conversion
      - writing CTAs, taglines, or product descriptions
      - preparing launch copy for Product Hunt, Hacker News, or newsletter
      - persuasion-focused short-form writing for any channel
    do_not_load_when:
      - writing long-form educational content
      - writing code documentation or technical reference
      - task is SEO strategy or content calendar planning
      - copywriter persona is not active

  - skill: link_swarm.md
    required: true
    load_when:
      - running a lifecycle-edge enrichment campaign (replaces/evolves/related) over many audited gaps
      - orchestrating a model-judgment swarm over link audit --json candidates
      - backfilling decision-level lifecycle edges across the corpus at scale
    do_not_load_when:
      - classifying one or two lifecycle-link stubs by hand (use end_of_turn.md's Lifecycle Link Sweep)
      - no link audit gaps to judge, or the task is a single authored edge

  - skill: topic_swarm.md
    required: true
    load_when:
      - backfilling controlled-vocabulary topics across the corpus at scale
      - orchestrating a model-judgment swarm that attributes topics to decisions (<slug>:dN)
      - running or scoring the topic-backfill pilot against authored topics
      - writing topic sidecars under sessions/topics/ for many entries at once
    do_not_load_when:
      - choosing topics for the entry being written now (use session_logging.md)
      - correcting the topics of one or two entries by hand
      - the task is vocabulary maintenance in topics.yaml rather than attribution
```

## Deterministic Use

Evaluate skills in the listed order. Load every matching required skill, but keep the loaded set as small as the task safely allows. A skill match means the agent must read that skill before acting on the matching part of the task.

For sub-projects, use the nearest runtime's registry first. Parent registries and parent skills apply only when inherited and not disabled or overridden in the local `index.md`.

If trigger confidence is ambiguous and the decision affects durable design, policy, bootstrap behavior, release behavior, memory structure, security, privacy, or destructive operations, ask the user before proceeding.
