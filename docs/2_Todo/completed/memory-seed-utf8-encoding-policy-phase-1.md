# Encoding Policy and Agent Skill: Prevent Mojibake in MemorySeed and MemoryTrace

Status: Completed Phase 1 on 2026-07-07; follow-up remains active for checker/repair tooling.
Priority: High
Source: Promoted from `docs/1_Inbox/memory_seed_utf8_encoding_policy.md`.
Scope: Establish the UTF-8/LF/NFC repository policy, add shared text/JSON helpers, patch obvious Memory Seed text-write gaps, document the contract, and add regression tests.
Non-goals: Phase 1 does not implement `memory-seed encoding check`, `memory-seed encoding repair`, CI/static implicit-encoding enforcement, or mirrored Memory Trace repair commands.
Dependencies: Completed follow-up plan
`docs/2_Todo/completed/utf8-encoding-doctor-and-static-check-plan.md`.
Acceptance criteria: `.editorconfig`, `.gitattributes`, README encoding policy, shared helper tests, explicit JSON/text writes in core generated config paths, and MCP Unicode-preserving output are present.

Completion summary: Phase 1 shipped a shared `memory_seed.text_files` helper for UTF-8/LF/NFC text and Unicode-preserving JSON, added `.editorconfig` and `.gitattributes`, documented the policy, patched obvious generated config/session/routing writes, and added non-ASCII round-trip tests. The original source proposal is retained below for provenance.

## Purpose

MemorySeed and MemoryTrace store text-heavy artifacts: Markdown memory files, YAML frontmatter, JSON metadata, logs, summaries, and MCP payloads. These files may contain curly quotes, em dashes, non-English names, currency symbols, copied terminal output, and emojis.

To prevent mojibake, all project-owned text files must use one explicit encoding standard.

## Canonical Encoding Standard

MemorySeed and MemoryTrace must use:

```text
Encoding: UTF-8
BOM: no BOM
Line endings: LF
Unicode normalization: NFC
```

This applies to project-owned text artifacts, including:

```text
*.md
*.memory.md
*.json
*.yaml
*.yml
*.toml
*.txt
*.log
*.csv
```

Binary files, images, SQLite databases, and external attachments are excluded unless explicitly converted into text.

---

## Core Requirements

## R1. All text file reads must specify UTF-8

Do this:

```python
path.read_text(encoding="utf-8")
```

or:

```python
with open(path, "r", encoding="utf-8") as file:
    content = file.read()
```

Do not do this:

```python
path.read_text()
open(path)
```

Rationale: platform defaults differ. Windows systems may use a legacy code page, which can corrupt UTF-8 content when read incorrectly.

---

## R2. All text file writes must specify UTF-8 and LF newlines

Do this:

```python
path.write_text(content, encoding="utf-8", newline="\n")
```

or:

```python
with open(path, "w", encoding="utf-8", newline="\n") as file:
    file.write(content)
```

Do not do this:

```python
path.write_text(content)
open(path, "w")
```

---

## R3. Use central file I/O helpers

Create a shared file I/O module and require MemorySeed/MemoryTrace code to use it for project-owned text files.

Suggested location:

```text
src/memory_seed/io/text_files.py
```

or, if shared by both packages:

```text
src/memory_common/io/text_files.py
```

Suggested implementation:

```python
from __future__ import annotations

import unicodedata
from pathlib import Path


CANONICAL_ENCODING = "utf-8"
CANONICAL_NEWLINE = "\n"


def normalize_text(text: str) -> str:
    \"\"\"Normalize project-owned text before writing to disk.\"\"\"
    return unicodedata.normalize("NFC", text)


def read_text_file(path: Path) -> str:
    \"\"\"Read a project-owned text file as UTF-8.\"\"\"
    return path.read_text(encoding=CANONICAL_ENCODING)


def write_text_file(path: Path, content: str) -> None:
    \"\"\"Write a project-owned text file as UTF-8 without BOM and with LF newlines.\"\"\"
    normalized = normalize_text(content)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        normalized,
        encoding=CANONICAL_ENCODING,
        newline=CANONICAL_NEWLINE,
    )


def append_text_file(path: Path, content: str) -> None:
    \"\"\"Append to a project-owned text file as UTF-8 without relying on defaults.\"\"\"
    normalized = normalize_text(content)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding=CANONICAL_ENCODING, newline=CANONICAL_NEWLINE) as file:
        file.write(normalized)
```

---

## R4. YAML frontmatter must preserve Unicode

YAML frontmatter should not escape human-readable Unicode unnecessarily.

Recommended PyYAML behaviour:

```python
yaml.safe_dump(
    data,
    allow_unicode=True,
    sort_keys=False,
)
```

---

## R5. JSON must preserve Unicode

JSON files should be written as UTF-8 with readable Unicode.

Do this:

```python
json.dumps(data, ensure_ascii=False, indent=2)
```

Avoid this for project-owned JSON:

```python
json.dumps(data)
```

The default is valid JSON, but it may escape non-ASCII characters and reduce readability.

---

## R6. MCP stdio boundaries must use UTF-8

For MCP stdio communication, treat incoming and outgoing JSON as UTF-8 text.

If manually handling streams, ensure the process uses UTF-8 explicitly.

Suggested guard for Python entrypoints:

```python
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
```

Apply this carefully because stdio behaviour may also be controlled by the MCP host. The main requirement is that MemorySeed/MemoryTrace should not intentionally encode/decode MCP JSON with a legacy platform encoding.

---

## R7. CLI output should avoid encoding fragility

CLI output should support UTF-8, but important meaning should not depend on decorative characters.

Prefer:

```text
Stopped 3 memory-seed processes.
```

Avoid making important status depend on symbols such as:

```text
[ok]
[x]
->
```

Symbols can still be used sparingly, but plain-text wording must remain clear.

---

## R8. Tests must include non-ASCII text

Add regression tests using characters that commonly expose mojibake problems:

```text
Jean Nathan's memory - résumé GBP EUR café naïve São Paulo 中文 عربى rocket
```

Required test cases:

1. Markdown memory write/read round trip.
2. YAML frontmatter write/read round trip.
3. JSON metadata write/read round trip.
4. Append-to-memory-file round trip.
5. CLI command output does not crash with non-ASCII memory content.
6. Windows-compatible path and file handling test where practical.

Example test:

```python
from pathlib import Path

from memory_seed.io.text_files import read_text_file, write_text_file


def test_utf8_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "2026-07-07.memory.md"
    original = "Jean Nathan's memory - résumé GBP EUR café naïve São Paulo 中文 عربى rocket"

    write_text_file(path, original)

    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf") is False

    loaded = read_text_file(path)
    assert loaded == original
```

---

## R9. CI must block implicit encoding

Add a static check that fails if project code uses unsafe text I/O.

Flag these patterns:

```text
open(path)
open(path, "r")
open(path, "w")
Path.read_text()
Path.write_text(...)
```

Allowed exceptions:

1. Binary mode, such as `open(path, "rb")`.
2. Third-party generated code.
3. Explicitly documented compatibility shims.
4. Tests intentionally checking unsafe behaviour.

Suggested tooling options:

```text
ruff custom rule where possible
grep-based CI check
pre-commit hook
unit test using ast parsing
```

Simple grep-style starter check:

```bash
grep -R "read_text()" src tests && exit 1
grep -R "write_text(" src tests | grep -v "encoding=" && exit 1
grep -R "open(.*[\"']w" src tests | grep -v "encoding=" && exit 1
grep -R "open(.*[\"']r" src tests | grep -v "encoding=" && exit 1
```

A Python AST-based check is preferred long-term because grep can produce false positives.

---

## R10. Repository config should declare UTF-8

Add or update `.editorconfig`:

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.md]
trim_trailing_whitespace = false
```

This helps editors write files in UTF-8 and normalize line endings.

---

## R11. Documentation must state the encoding contract

Add a short section to the README or developer docs:

```markdown
## Text Encoding

MemorySeed writes project-owned text files as UTF-8 without BOM and LF line endings.

All Markdown memory files, YAML frontmatter, JSON metadata, and logs should be read and written with explicit `encoding="utf-8"`.

Do not rely on platform-default encodings.
```

---

## R12. Add an optional encoding doctor command

Add an optional repair/check command:

```bash
memory-seed encoding check
memory-seed encoding repair --dry-run
memory-seed encoding repair
```

Equivalent MemoryTrace commands:

```bash
memory-trace encoding check
memory-trace encoding repair --dry-run
memory-trace encoding repair
```

The check command should:

1. Scan project-owned text files.
2. Detect invalid UTF-8.
3. Detect UTF-8 BOM.
4. Report likely mojibake sequences.
5. Report CRLF line endings if LF is required.
6. Never modify files unless repair is explicitly requested.

Potential mojibake indicators:

```text
UTF-8 lead sequence
Latin-1 supplement marker
Common mojibake marker: U+00E2 followed by malformed quote/dash text
Common mojibake marker: U+00C3 followed by Latin-1 supplement characters
Common mojibake marker: U+00C2 before punctuation or symbols
Replacement character: U+FFFD
Unexpected BOM: U+FEFF at file start
```

Repair should be conservative. It should create a backup or require a Git-clean working tree before modifying files.

---

## Agent Skill: UTF-8 File Handling

Use this section as an agent/Codex skill or development instruction.

```markdown
# Skill: UTF-8 File Handling for MemorySeed and MemoryTrace

## Rule

All project-owned text files in MemorySeed and MemoryTrace must be read and written as UTF-8 without BOM, with LF line endings, and with NFC Unicode normalization.

## Applies To

- Markdown memory files
- YAML frontmatter
- JSON metadata
- TOML config
- TXT/log text output
- CSV text exports
- MCP text payload serialization

## Required Behaviour

When editing MemorySeed or MemoryTrace code:

1. Never use `open(...)` for text mode without `encoding="utf-8"`.
2. Never use `Path.read_text()` without `encoding="utf-8"`.
3. Never use `Path.write_text(...)` without `encoding="utf-8"` and `newline="\n"`.
4. Use shared text I/O helpers where available.
5. Use `json.dumps(..., ensure_ascii=False)` for project-owned JSON.
6. Use `yaml.safe_dump(..., allow_unicode=True)` for YAML/frontmatter.
7. Add or update tests with non-ASCII text when changing file I/O.
8. Preserve readable Unicode in memory files.
9. Do not introduce Windows code-page assumptions.
10. Do not convert Unicode text to ASCII escape sequences unless required by an external protocol.

## Review Checklist

Before completing a change, check:

- [ ] No implicit text file reads.
- [ ] No implicit text file writes.
- [ ] New text files are UTF-8 without BOM.
- [ ] Markdown/YAML/JSON round trips preserve curly quotes, dashes, accents, currency symbols, and emoji.
- [ ] Tests include at least one non-ASCII sample.
- [ ] CLI/MCP output remains readable on Windows, macOS, and Linux.
```

---

## Recommended Codex Implementation Prompt

Implement a UTF-8 encoding policy for MemorySeed and MemoryTrace.

Requirements:

- Add a documented encoding policy for all project-owned text files.
- Use UTF-8 without BOM, LF line endings, and NFC Unicode normalization.
- Add shared text I/O helpers for read/write/append operations.
- Replace implicit `open`, `Path.read_text`, and `Path.write_text` usage in project-owned text paths.
- Ensure JSON writes use `ensure_ascii=False`.
- Ensure YAML/frontmatter writes use `allow_unicode=True`.
- Add `.editorconfig` rules for UTF-8 and LF.
- Add tests covering Markdown, YAML, JSON, and append round trips with non-ASCII text.
- Add a static check or pre-commit/CI guard that blocks implicit text encoding usage.
- Optionally add `memory-seed encoding check` and `memory-seed encoding repair --dry-run`.
- Mirror relevant behaviour in `memory-trace`.
- Do not silently repair mojibake unless the user explicitly asks for repair.
- Make repair commands conservative and backup-aware.

Use this sample string in tests:

```text
Jean Nathan's memory - résumé GBP EUR café naïve São Paulo 中文 عربى rocket
```

---

## Conclusion

A skill alone is not enough. The robust solution is:

```text
1. Repository encoding policy
2. Shared UTF-8 file I/O helpers
3. Tests with non-ASCII round trips
4. CI/static checks blocking implicit encodings
5. Optional encoding doctor/repair command
6. Agent skill reminding Codex and other agents of the rules
```

This combination prevents most mojibake from entering MemorySeed/MemoryTrace and gives users a safe way to detect or repair older affected files.
