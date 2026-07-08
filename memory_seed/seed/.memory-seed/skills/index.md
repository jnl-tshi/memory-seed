---
memory-system-version: 2.16
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

  - skill: agent_collaboration.md
    required: true
    load_when:
      - coordinating subagents, branch/worktree coordination, or multi-developer agent workflows
      - creating or reviewing feature branches for agent work
      - using worktrees for parallel code-writing agents
      - preparing worker, validator, or merge-conflict handoffs
    do_not_load_when:
      - direct single-agent edits with no branch, worktree, merge, or handoff implications

  - skill: history_retrieval.md
    required: true
    load_when:
      - prior decisions, rationale, unresolved risks, or release history matter
      - using memory_search or memory_get_chunk
      - reconciling current files with older session history
      - deciding whether older memory conflicts with current authority files
    do_not_load_when:
      - task is a small obvious edit and current files plus index.md and policy.md are sufficient

  - skill: session_logging.md
    required: true
    load_when:
      - writing, validating, or repairing session entries
      - deciding DRAFT labels, entry shapes, related_entries, or append-only chronology
      - changing session log schema or examples
    do_not_load_when:
      - only reading recent session state without writing or repairing logs

  - skill: compact_mermaid_diagrams.md
    required: true
    load_when:
      - authoring or revising Mermaid graph or flowchart diagrams
      - choosing between Mermaid and D2 for documentation diagrams
      - authoring or reviewing D2 only for dense architecture or nested system diagrams
      - Mermaid diagram layout is too wide, too tall, stretched, or sparse
      - preventing isolated single nodes, orphan baselines, or runaway horizontal rows
      - needing compact rectangular Mermaid layout with tiers, grids, subgraphs, or invisible links
    do_not_load_when:
      - prose or lists communicate the structure as well as a diagram
      - the task has no Mermaid, D2, or diagram layout concern
      - editing sequence diagrams without graph or flowchart layout pressure

  - skill: end_of_turn.md
    required: true
    load_when:
      - running End Of Turn, ESR, or /esr
      - performing closeout, consolidation review, orphan sweep, persona evolution, skill evolution, or baseline-promotion review
    do_not_load_when:
      - ordinary mid-task work before closeout

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
      - moving implemented, rejected, or superseded proposals into docs/2_Todo/completed or docs/todo/completed
      - reorganizing proposal folders, roadmap docs, or completed-proposal archives
      - updating NEXT_STEPS, 0_NEXT_STEPS, or functionality-audit because proposal status changed
    do_not_load_when:
      - ordinary documentation edit with no proposal, roadmap, inbox, todo, reference, or completed status change
      - code-only implementation work where proposal files are not being moved or resolved

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
```

## Deterministic Use

Evaluate skills in the listed order. Load every matching required skill, but keep the loaded set as small as the task safely allows. A skill match means the agent must read that skill before acting on the matching part of the task.

For sub-projects, use the nearest runtime's registry first. Parent registries and parent skills apply only when inherited and not disabled or overridden in the local `index.md`.

If trigger confidence is ambiguous and the decision affects durable design, policy, bootstrap behavior, release behavior, memory structure, security, privacy, or destructive operations, ask the user before proceeding.
