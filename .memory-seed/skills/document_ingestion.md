---
memory-system-version: 2.12
tags:
  - memory-seed
  - skill
  - document-ingestion
---

# Document Ingestion Skill

Use when an agent needs to **read** a binary document (`.docx`, `.pdf`, `.pptx`, `.xlsx`, `.csv`, images) as plain Markdown. Tool: **Microsoft markitdown** (`pip install "markitdown[all]"`), invoked as `python -m markitdown` (the `markitdown` shim may not be on PATH).

## Routing (evidence-based)

| Source | Path | Notes |
|---|---|---|
| `.docx`/`.pdf`/`.pptx`/`.xlsx` | markitdown | Prose, in-text citations, and SDT-wrapped bibliographies are preserved; **SEQ caption numbers are dropped** (captions render `Figure :` blank) â€” for caption numbering or a guaranteed field audit, use field-resolved (lxml) extraction. |
| `.csv` | **NOT markitdown** | markitdown decodes CSV as ASCII and fails on non-ASCII; use an encoding-aware reader (try utf-8-sig, cp1252, latin-1) then emit a Markdown table. |
| images | **native Read/vision** | markitdown returns ~0 bytes without an LLM client; read the image directly, or configure `llm_client` for captions. |

## Procedure

1. Check for a cached `.md` first (convert into a gitignored `.cache/markdown/`, never into `.memory-seed/`).
2. Convert with markitdown; read the cached Markdown with the standard Read tool.
3. Respect the runtime's data policy â€” do not auto-convert sensitive or raw source rows; prefer aggregates and ask first.
4. Locked files (held open by another app): read a share-aware copy of the last-saved bytes.

## Output

- Path to cached Markdown plus a one-line fidelity note (what may have been lost, for example caption numbers).
