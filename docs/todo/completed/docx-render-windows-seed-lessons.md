---
tags:
  - memory-seed
  - seed-promotion
  - docx
  - windows
  - libreoffice
---

# DOCX Render Windows Seed Lessons

> **Status: IMPLEMENTED 2026-07-05 (unreleased).** The universal lazy skill
> `.memory-seed/skills/docx_render_windows.md` now ships in the seed (live + seed twin), is
> registered in the skill trigger registry with the deterministic triggers from Lesson 7, is
> cross-referenced from `office_document_editing.md`, and is wired into `SEED_FILES`,
> `pyproject.toml` package data, and the seed-inventory test. Content is generic (no project paths):
> the LibreOffice `UserInstallation` URI failure mode, the two-step bounded-timeout render pattern,
> stale-process cleanup, Word field/TOC refresh, page-level visual QA rules, and the single-writer
> render / read-only validator collaboration boundary. This file started as a lesson capture from a
> separate DOCX editing session and is retained as source context.

## Summary

This note collects lessons from the AM1 Project Report DOCX editing session on 2026-07-01. The immediate issue was that the bundled Documents renderer hung during LibreOffice conversion on Windows, while a local Windows-safe renderer succeeded.

These lessons should be considered for a future Memory Seed baseline skill or an update to `office_document_editing.md`.

## Lessons To Promote

### 1. Windows DOCX Render Fallback

- The bundled Documents renderer can hang on Windows when LibreOffice receives an invalid profile URI such as `file://C:\...`.
- LibreOffice expects a valid Windows file URI such as `file:///C:/...`.
- A Windows-safe renderer should construct the profile URI with `Path(profile).as_uri()` or an equivalent `file:///C:/...` conversion.
- Future seeds should include a Windows DOCX render fallback skill, for example `docx_render_windows.md`.

### 2. Renderer Commands Need Timeouts

- DOCX rendering should not rely on unbounded `subprocess.run`.
- Safe render helpers should timeout the LibreOffice DOCX-to-PDF step and the Poppler PDF-to-PNG step separately.
- If rendering hangs, stop only the stale `soffice` / `soffice.bin` processes from the failed render attempt before retrying.

### 3. Word Fields Need Word When Available

- After inserting headings, front matter, captions, cross-references, or TOC-relevant content, update fields before final render.
- LibreOffice rendering may show stale TOC/page-number field results if Word fields were not refreshed first.
- On Windows with Word installed, use Word automation to update `TablesOfContents` and document fields before render QA.

### 4. Abstract Front Matter Should Not Always Be `Heading1`

- If an abstract belongs on the title/front page and should not renumber the report, insert it as unnumbered front matter.
- Use `Heading1` only when the abstract should appear as a numbered report section and in the table of contents.
- Verify the TOC after inserting an abstract because a wrongly styled abstract can shift all section numbering.

### 5. Visual QA Needs Page-Level Inspection

- Contact sheets are useful for fast scanning, but they are not sufficient final QA.
- Inspect affected pages directly after edits: title page, TOC, first body page, figure/caption pages, references, and appendices.
- Re-render after every layout-sensitive fix.

### 6. Figure/Captions Are High-Risk After Structure Edits

- Adding headings or front matter can shift figures enough to split a chart from its caption.
- Rendered pages should be checked for caption separation, clipped charts, broken tables, and awkward page breaks.
- Prefer keeping each figure and caption together; use a targeted page break only when it improves layout.

### 7. Skill Trigger Should Be Deterministic

- Future Memory Seed runtimes should route DOCX rendering on Windows to a lazy skill like `docx_render_windows.md`.
- Trigger terms should include:
  - rendering `.docx` pages
  - visual QA on Windows
  - LibreOffice hangs
  - Documents plugin renderer slow or hung
  - DOCX-to-PNG verification

## Suggested Seed Change

Add a universal lazy skill such as `.memory-seed/skills/docx_render_windows.md`, with a seed twin under `memory_seed/seed/`, and register it in the skill index.

The skill should:

- Explain the Windows LibreOffice `UserInstallation` URI failure mode.
- Provide a safe DOCX-to-PNG command pattern.
- Require bounded timeouts.
- Explain stale-process cleanup.
- Require Word field/TOC refresh when Word is available.
- Require direct page-image inspection after rendering.

Also cross-reference the skill from `office_document_editing.md` or equivalent Office-document guidance, so agents using the general DOCX editing skill can discover the Windows fallback when rendering hangs.

## Source Memory

Project Report Memory Seed entry:

- `ms-6e9d1c42` - `2026-07-01 12:30 - Added Windows-safe DOCX render skill`

Key local files from that runtime:

- `Project Report/.memory-seed/skills/docx_render_windows.md`
- `Project Report/.memory-seed/skills/index.md`
- `Project Report/AGENTS.md`
- `L7_Uni_Assignments/scripts/render_docx_windows_safe.py`
