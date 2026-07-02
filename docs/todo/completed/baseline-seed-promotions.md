---
memory-system-version: 2.0
tags:
  - memory-seed
  - plan
  - baseline-promotion
---

# Baseline Memory-Seed Promotions (port-ready spec)

> **Status:** Approved by JNL 2026-06-10. Target = the **Memory Seed package** seed templates (separate repo), *not* this project's live runtime. Each item below is genericised (no project/domain facts) per the seed's public-hygiene rule. Port the text as-is.
>
> **Promote:** (1) `document_ingestion` skill, (2) new `office_document_editing` skill, (3) three principles into `agent-rules.md`.
> **Do NOT promote (project-local only):** the 10k word limit, the criteria tracker, template-locked section order, the report-reviewer "Submission Constraints" block, and all L7 persona adaptations.

---

## 1) Promote skill: `document_ingestion.md`

**Where:** baseline universal skills set (alongside `code_search.md`, etc.). Add a trigger-registry entry (below). Origin: this project's `.memory-seed/skills/document_ingestion.md`, de-projected.

**Trigger registry entry (`skills/index.md`):**
```yaml
  - skill: document_ingestion.md
    required: true
    load_when:
      - reading or ingesting a binary document as Markdown
      - needing the content of a `.docx`, `.pdf`, `.pptx`, or `.xlsx` as text
      - converting a source document so a file-reading agent can read it
    do_not_load_when:
      - the source is already plain text, Markdown, or source code (use code_search)
      - producing or editing an Office document (use office_document_editing)
```

**Genericised skill body:**
```markdown
---
memory-system-version: 2.0
tags: [memory-seed, skill, document-ingestion]
---

# Document Ingestion Skill

Use when an agent needs to **read** a binary document (`.docx`, `.pdf`, `.pptx`, `.xlsx`, `.csv`, images) as plain Markdown. Tool: **Microsoft markitdown** (`pip install "markitdown[all]"`), invoked as `python -m markitdown` (the `markitdown` shim may not be on PATH).

## Routing (evidence-based)
| Source | Path | Notes |
|---|---|---|
| `.docx`/`.pdf`/`.pptx`/`.xlsx` | markitdown | Prose, in-text citations, and SDT-wrapped bibliographies are preserved; **SEQ caption numbers are dropped** (captions render `Figure :` blank) — for caption numbering or a guaranteed field audit, use field-resolved (lxml) extraction. |
| `.csv` | **NOT markitdown** | markitdown decodes CSV as ASCII and fails on non-ASCII; use an encoding-aware reader (try utf-8-sig, cp1252, latin-1) → Markdown table. |
| images | **native Read/vision** | markitdown returns ~0 bytes without an LLM client; read the image directly, or configure `llm_client` for captions. |

## Procedure
1. Check for a cached `.md` first (convert to a gitignored `.cache/markdown/`, never into `.memory-seed/`).
2. Convert with markitdown; read the cached Markdown with the standard Read tool.
3. Respect the runtime's data policy — do not auto-convert sensitive/raw source rows; prefer aggregates and ask first.
4. Locked files (held open by another app): read a share-aware copy of the last-saved bytes.

## Output
- Path to cached Markdown + a one-line fidelity note (what may have been lost, e.g. caption numbers).
```

---

## 2) Promote NEW skill: `office_document_editing.md`

**Where:** baseline universal skills. Add the trigger entry below. Generalises this session's `.docx` field-safety lessons to any Office document with fields (citations, captions, cross-references, TOC).

**Trigger registry entry (`skills/index.md`):**
```yaml
  - skill: office_document_editing.md
    required: true
    load_when:
      - creating or editing an Office document (.docx/.pptx/.xlsx) programmatically
      - the document contains fields (citations, captions, cross-references, TOC) or content controls
    do_not_load_when:
      - only reading a document as text (use document_ingestion)
      - editing plain text / Markdown / source code
```

**Genericised skill body:**
```markdown
---
memory-system-version: 2.0
tags: [memory-seed, skill, office-document-editing]
---

# Office Document Editing Skill

Use when programmatically editing an Office document that contains **fields or content controls** — citations (reference-manager / Word `CITATION` fields), `SEQ` caption numbering, `REF` cross-references, a `TOC`, or `w:sdt` structured tags. These break easily; edit surgically.

## Rules
1. **Version, don't mutate:** edit a byte-copy as a new version (`vN`→`vN+1`); keep prior versions.
2. **Edit the XML surgically** (e.g. `word/document.xml` via lxml), preserving every field / content-control / hyperlink node. **Avoid full round-trips through high-level libraries** (e.g. python-docx) on field-heavy files — they can drop or renormalise structure.
3. **Never blank-rewrite a field-bearing paragraph** (it orphans the field). To change one, either **delete the whole paragraph** (clean) or do **run-level edits** that leave the field/content-control intact. Check field/SDT counts per paragraph before editing.
4. **Do not insert literal citation numbers** — add sources via the document's reference manager so numbering stays live; literal numbers will not renumber.
5. **Locked files:** read a **share-aware** copy of the last-saved bytes when the app holds the file open.
6. **POC-gate a new edit method:** apply one trivial edit to a throwaway copy → have the user open it in the real app → only scale up if it opens with no repair prompt.
7. **Verification split:** the agent can confirm the package/XML is well-formed and report a **field-count delta** (should be 0 unless intended); **only the user** can confirm the app opens it cleanly and must trigger a field/TOC update (e.g. Word: Ctrl+A → F9).

## Checks
- Field-count delta (captions/cross-refs/TOC/content-controls) is 0 unless a change was intended.
- No orphaned/blanked fields introduced; new versioned file written; original untouched.

## Output
- Path to the new version + the field-delta result + the explicit "open-in-app + update-fields" step left to the user.
```

---

## 3) Promote principles into `agent-rules.md`

Add a short **Working Principles** subsection (suggested under *Orchestration Levels* / Level 3, or near *End Of Turn*). Generic, vendor-neutral:

```markdown
### Working Principles (cross-cutting)

- **POC-gate before scaling a risky or hard-to-verify automated method.** Prove a new editing/transformation pipeline on one throwaway case the user can validate, before applying it broadly.
- **Verification split.** State plainly what the agent can verify (e.g. file integrity, structural checks, diffs) versus what only the user can verify (e.g. an app opens the artifact without error). Never imply you verified the latter.
- **Read share-aware copies of locked files.** When another application holds a file open, read the last-saved bytes via a shared/read-write handle rather than failing or assuming staleness.
```

---

## 4) Promote: end-of-session evolution trigger (HYBRID — command + throttled hook)

**Principle:** evolution = analyse session → draft persona/skill changes → **user approval** → apply. That is an LLM+human task; a hook can only **remind**, never *do* or auto-apply. The `Stop` event fires on **every** turn, so an ungated reminder would nag constantly. Therefore: an explicit command does the work; a throttled, gated `Stop` hook is a reminder-only safety net.

### 4a) Baseline command/skill: `/end-session` (a.k.a. `session_wrap`)
Runs, in order:
1. Append/confirm today's session-log entry (existing End-Of-Turn discipline).
2. Consolidation review — promote durable facts to `index.md`/`policy.md` (see `memory_consolidation`).
3. **Persona/skill evolution review** (agent-rules §End Of Turn steps 7–8): identify ≤3 durable lessons → draft changes to `.agents/<persona>.md` and/or `skills/*.md` → **present for approval** → on approval apply + add Project Adaptation entries + log. If nothing emerged, state that and skip.
4. **Baseline-promotion check:** flag any approved adaptation generic enough to port to the seed package; record in `.memory-seed/plans/`.
- **Never edits personas/skills without explicit approval.**

### 4b) Throttled Stop hook: `evolution-nudge-check.py` (reminder-only)
On `Stop`, **stay silent unless ALL hold:**
- last-nudge stamp older than a throttle window (e.g. ≥6h) — use the stamp pattern from `memory-retrieval-check.py`;
- a **meaningful-change signal** this session — e.g. ≥3 new `### Decision`/DRAFT entries in today's log, **or** a file under `.agents/` or `.memory-seed/skills/` changed;
- the evolution review hasn't already run this session (no `/end-session` marker).

If the gate passes: exit non-zero once to block the stop with a short message — *"Meaningful work this session; consider `/end-session` to review persona/skill evolution"* — then write the stamp so it does not repeat. **Hard rules:** reminder text only; **no auto-apply**; on any error degrade to silent (never block work because a hook failed).

### settings.json (baseline)
```json
"Stop": [
  { "hooks": [
      { "type": "command", "command": "python3 .memory-seed/hooks/session-log-check.py" },
      { "type": "command", "command": "python3 .memory-seed/hooks/evolution-nudge-check.py" }
  ]}
]
```

### Counters captured (why NOT a pure auto-hook)
- `Stop` fires per-turn, not at "session end" → must throttle + gate or it nags every response.
- Hooks can't reason or obtain approval → reminder-only; the command + human do the work; auto-applying would bypass the approval gate.
- Most sessions have nothing to evolve → gate on change signals and allow a clean "nothing to evolve" skip to avoid alarm fatigue.

## 5) Promote: GitHub Copilot agent integration

> **Status (updated 2026-06-13): IMPLEMENTED in Release 2.6.0.** The original spec below is retained for context, but reality diverged once each Copilot surface was researched — there are **three distinct surfaces** with different config files, not one:
> - **Copilot CLI** (shipped 2.6.0): repo-local `.github/mcp.json` (note: `mcpServers` key, `type: stdio`) for `memory_search`/`memory_get_chunk`, plus a `sessionStart` **prompt** hook in `.github/hooks/memory-seed.json` (Copilot command hooks cannot inject context at sessionStart; only prompt hooks can — and its `userPromptSubmitted`/`agentStop`/`sessionEnd` events don't support `additionalContext`, so it gets no per-turn reminders).
> - **VS Code Copilot** (shipped 2.6.0): `.vscode/mcp.json` (note: **`servers`** key, not `mcpServers`) + thin `.github/copilot-instructions.md` router (emitted as a seed file alongside `CLAUDE.md`/`GEMINI.md`).
> - **Copilot coding agent** (github.com): MCP lives in repo/org settings, not a repo file — documented as a manual step, not automatable.
>
> All wiring is auto-registered by `init`/`update` via merge functions in `core.py` (`_merge_copilot_mcp`, `_merge_copilot_startup_hook`, `_merge_vscode_mcp`) + the `.github/copilot-instructions.md` seed file.

**Why:** Memory Seed is vendor-neutral with per-tool routing files; Copilot is the main gap. Good news — Copilot (coding agent, CLI, VS Code) **already reads `AGENTS.md` and `CLAUDE.md`/`GEMINI.md`** (coding-agent `AGENTS.md` support landed 2025-08), which the seed already emits, so Copilot largely works today via `AGENTS.md`. This adds a Copilot-canonical entry point + MCP wiring to make it first-class. **Keep routing files thin (point to `AGENTS.md`) — never duplicate policy.**

**Routing files (bootstrap should emit alongside `CLAUDE.md`/`GEMINI.md`):**
- `.github/copilot-instructions.md` — thin router:
```markdown
# GitHub Copilot Instructions
The canonical agent instructions for this repository are in `AGENTS.md`.
Before planning, editing, reviewing, or running commands:
1. Open `AGENTS.md`.
2. Follow its nearest `.memory-seed/` runtime discovery and read order.
3. Adapt only tooling, not policy.
Do not treat this file as a replacement for `AGENTS.md`.
```
- *(Optional, path-specific)* `.github/instructions/memory-seed.instructions.md` with YAML frontmatter `applyTo: "**"` routing nested sub-projects to their nearest runtime.
- **Existing `AGENTS.md` already covers the Copilot coding agent** — no change needed; just document it.

**MCP wiring (so `memory_search`/`memory_get_chunk` work in Copilot):**
- `.vscode/mcp.json` for VS Code Copilot (note: VS Code uses the `servers` key, unlike the `mcpServers` key in `.mcp.json`/`.cursor/mcp.json`):
```json
{ "servers": { "memory-seed": { "command": "uvx", "args": ["--from","memory-seed","memory-seed-mcp","--stdio"] } } }
```
- For the **Copilot coding agent** (autonomous, on github.com) MCP servers are configured in **repository/org Copilot settings**, not a repo file — document as a manual step.

**Caveats:** Copilot's instruction/MCP conventions change frequently — **verify current filenames/keys at port time**. The win is mostly the canonical entry point + MCP; the actual instructions already flow through `AGENTS.md`.

## Porting checklist (for the Memory Seed package repo)

1. Add `seed/skills/document_ingestion.md` (body above) + its trigger entry to the seed `skills/index.md`.
2. Add `seed/skills/office_document_editing.md` (body above) + its trigger entry.
3. Add the **Working Principles** block to `seed/.memory-seed/agent-rules.md` (bump `memory-system-version` per the package's release process).
4. Confirm no project/domain facts leaked (warranty, Nissan, L7, paths) — all text above is generic.
5. Add the `/end-session` command/skill template (steps in §4a) to the seed.
6. Add `seed/.memory-seed/hooks/evolution-nudge-check.py` (reminder-only, throttled, gated — §4b) and the `Stop` hook entry to the seed `settings.json` template; reuse the throttle-stamp pattern from `memory-retrieval-check.py`.
7. Add Copilot routing to bootstrap: `.github/copilot-instructions.md` (thin router) + `.vscode/mcp.json` (memory-seed MCP) templates, emitted alongside `CLAUDE.md`/`GEMINI.md`; document that `AGENTS.md` already covers the Copilot coding agent and that its MCP servers are set in repo/org settings.
8. Version/changelog + `memory-seed doctor` on a fresh init to validate the new skills, command, hook, and Copilot routing load.
