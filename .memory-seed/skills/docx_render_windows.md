---
memory-system-version: 2.15
tags:
  - memory-seed
  - skill
  - documents
  - docx-render
  - windows
---

# DOCX Render Windows Skill

Use this skill when rendering or visually inspecting a `.docx` on Windows — DOCX-to-PNG page
verification, visual QA after document edits, or when a bundled document renderer hangs or runs
suspiciously slowly during LibreOffice conversion.

## Failure Mode

Bundled renderers can hang on Windows because they pass LibreOffice a profile URI in the form
`file://C:\...`, which is not a valid Windows file URI. LibreOffice expects `file:///C:/...`.
Construct the `UserInstallation` profile URI with `Path(profile).as_uri()` or an equivalent
forward-slash `file:///C:/...` conversion, and use a throwaway temp directory as the profile so
parallel or crashed renders never share LibreOffice profile state.

## Safe Render Pattern

Render in two bounded steps — DOCX to PDF via LibreOffice, then PDF to PNG via Poppler — each with
its own timeout. Never rely on an unbounded `subprocess.run`.

```python
import subprocess, tempfile
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="lo_profile_") as profile:
    subprocess.run(
        [
            "soffice",
            f"-env:UserInstallation={Path(profile).as_uri()}",
            "--headless", "--norestore",
            "--convert-to", "pdf", "--outdir", str(out_dir), str(docx),
        ],
        timeout=45, check=True,
    )

subprocess.run(
    ["pdftoppm", "-png", "-r", "150", str(pdf), str(out_dir / "page")],
    timeout=60, check=True,
)
```

Verify the expected output actually exists and is non-empty after each step; a zero exit code
without a produced PDF or PNG pages is still a failure.

## Recovery

If a render times out or hangs:

1. Stop only the stale `soffice` / `soffice.bin` processes from the failed attempt — do not kill
   unrelated LibreOffice sessions the user may have open.
2. Retry from a short temp path (long or deeply nested paths are a known Windows failure source).
3. If rendering still fails, do not claim visual QA passed. Report that structural checks passed but
   render QA is blocked.

## Word Fields Before Render

LibreOffice renders the field results stored in the file, not recalculated ones. After inserting
headings, front matter, captions, cross-references, or TOC-relevant content, refresh fields before
render QA — on Windows with Word installed, use Word automation to update `TablesOfContents` and
document fields; otherwise have the user open the document and update fields (Ctrl+A then F9). A
render made from stale fields can show wrong TOC entries and page numbers that look like layout bugs.

## Visual QA Rules

- Contact sheets are for fast scanning only; final QA inspects affected pages directly — title page,
  TOC, first body page, figure/caption pages, references, appendices.
- Structure edits (new headings, front matter) are high-risk for figures: check for captions split
  from their figures, clipped charts, broken tables, and awkward page breaks.
- Watch section numbering: front matter styled as a numbered heading (for example an abstract set to
  `Heading1` when it should be unnumbered) shifts the TOC and every section number after it.
- Re-render after every layout-sensitive fix.

## Collaboration Boundary

Rendering, retries, and stale-process cleanup are single-writer operations owned by one agent.
Read-only validators may inspect the produced page images in parallel and report findings back, but
must not re-render, delete artifacts, or kill processes.

## Related Skills

- `office_document_editing.md` — creating or surgically editing the `.docx` itself.
- `document_ingestion.md` — reading a binary document as text instead of rendering it.
