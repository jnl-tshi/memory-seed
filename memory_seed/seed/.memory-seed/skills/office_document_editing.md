---
memory-system-version: 2.7
tags:
  - memory-seed
  - skill
  - office-document-editing
---

# Office Document Editing Skill

Use when programmatically editing an Office document that contains **fields or content controls** — citations (reference-manager / Word `CITATION` fields), `SEQ` caption numbering, `REF` cross-references, a `TOC`, or `w:sdt` structured tags. These break easily; edit surgically.

## Rules

1. **Version, don't mutate:** edit a byte-copy as a new version (`vN` then `vN+1`); keep prior versions.
2. **Edit the XML surgically** (for example `word/document.xml` via lxml), preserving every field, content-control, and hyperlink node. **Avoid full round-trips through high-level libraries** (for example python-docx) on field-heavy files — they can drop or renormalise structure.
3. **Never blank-rewrite a field-bearing paragraph** (it orphans the field). To change one, either **delete the whole paragraph** (clean) or do **run-level edits** that leave the field/content-control intact. Check field/SDT counts per paragraph before editing.
4. **Do not insert literal citation numbers** — add sources via the document's reference manager so numbering stays live; literal numbers will not renumber.
5. **Locked files:** read a **share-aware** copy of the last-saved bytes when the app holds the file open.
6. **POC-gate a new edit method:** apply one trivial edit to a throwaway copy, have the user open it in the real app, and only scale up if it opens with no repair prompt.
7. **Verification split:** the agent can confirm the package/XML is well-formed and report a **field-count delta** (should be 0 unless intended); **only the user** can confirm the app opens it cleanly and must trigger a field/TOC update (for example Word: Ctrl+A then F9).

## Checks

- Field-count delta (captions/cross-refs/TOC/content-controls) is 0 unless a change was intended.
- No orphaned or blanked fields introduced; new versioned file written; original untouched.

## Output

- Path to the new version plus the field-delta result plus the explicit "open-in-app and update-fields" step left to the user.
