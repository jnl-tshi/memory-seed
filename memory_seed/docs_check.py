"""`memory-seed docs check` - read-only lifecycle enforcement over `docs/`.

The check half of the document-lifecycle system's Phase 2 tooling, mirroring
`links check`/`esr`. It enforces the one rule the lane system rests on: **the
folder a document lives in is its state**. There is deliberately no
folder-vs-status rule to check, because no `status:` field mirrors the folder -
they cannot disagree if only one of them exists.

Why this exists: the 2026-07-17 lane migration moved 43 documents and rewrote
~85 relative links with **no gate to prove it worked**, so a throwaway checker
had to be written to validate it. That is the gap this closes.

Severity is deliberate, not uniform:

* **error** - something is *wrong now*: a link that does not resolve, a
  lifecycle pointer aimed at a file that does not exist, a spec whose declared
  binding contradicts the folder it sits in. These are broken facts.
* **warning** - something is *incomplete*: missing secondary YAML. Backfilling
  it is separate, still-open Phase 2 work, so failing on it would make the
  check red for a known-unfinished task and train people to ignore it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import unquote

_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)

# Non-lane folders that are legitimate, mirroring docs/README.md's allowlist.
# Anything else under docs/ is either a lane or a mistake.
SIDE_FOLDER_ALLOWLIST: frozenset[str] = frozenset(
    {
        "5_Completed/agent-templates",
        "4_Reference/memory-trace-phase0-baseline",
        "4_Reference/archived",
        "3_Spec/draft",
        "3_Spec/deprecated",
    }
)

LANES: frozenset[str] = frozenset(
    {
        "1_Inbox",
        "2_Todo",
        "3_Spec",
        "4_Reference",
        "5_Completed",
        "6_Rejected",
        "7_Superseded",
        "8_Deferred",
    }
)

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class DocIssue:
    file: str
    kind: str
    detail: str
    severity: Severity = "error"


@dataclass(frozen=True)
class DocsCheckResult:
    issues: tuple[DocIssue, ...]
    files_checked: int

    @property
    def errors(self) -> tuple[DocIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "error")

    @property
    def warnings(self) -> tuple[DocIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "warning")

    @property
    def ok(self) -> bool:
        return not self.errors


def _frontmatter(text: str) -> dict[str, str]:
    from .core import _parse_frontmatter_scalars

    match = _FRONTMATTER.match(text)
    if not match:
        return {}
    return _parse_frontmatter_scalars(match.group(1))


def _lane_of(rel: Path) -> str | None:
    parts = rel.parts
    return parts[0] if parts and parts[0] in LANES else None


def _check_links(md: Path, docs_root: Path, text: str, rel: str) -> list[DocIssue]:
    issues: list[DocIssue] = []
    for match in _LINK.finditer(text):
        target = match.group(1).strip()
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        bare = unquote(target.split("#")[0].strip())
        if not bare:
            continue
        if not (md.parent / bare).resolve().exists():
            issues.append(
                DocIssue(rel, "broken-link", f"link target does not resolve: {target}")
            )
    return issues


def _check_pointer(
    md: Path, docs_root: Path, front: dict[str, str], key: str, rel: str
) -> list[DocIssue]:
    """A lifecycle pointer may name a doc path or a `mse_`/`ms-` entry id. Only
    path-shaped values are resolvable here; entry ids are `links check`'s job."""
    value = front.get(key)
    if not value or not value.endswith(".md"):
        return []
    for base in (md.parent, docs_root, docs_root.parent):
        if (base / value).exists():
            return []
    return [DocIssue(rel, "dangling-pointer", f"{key} does not resolve: {value}")]


def check_docs(cwd: str | Path = ".") -> DocsCheckResult:
    """Validate the docs lifecycle. Read-only; writes nothing."""
    root = Path(cwd).resolve()
    docs_root = root / "docs"
    if not docs_root.is_dir():
        return DocsCheckResult(issues=(), files_checked=0)

    issues: list[DocIssue] = []
    checked = 0
    seen_dirs: set[str] = set()

    for md in sorted(docs_root.rglob("*.md")):
        rel_path = md.relative_to(docs_root)
        rel = rel_path.as_posix()
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            issues.append(DocIssue(rel, "unreadable", str(exc)))
            continue
        checked += 1

        issues.extend(_check_links(md, docs_root, text, rel))

        lane = _lane_of(rel_path)
        if lane is None:
            # A top-level doc (CONSTITUTION.md, README.md) is not lane-managed.
            if len(rel_path.parts) > 1:
                folder = rel_path.parent.as_posix()
                if folder not in seen_dirs:
                    seen_dirs.add(folder)
                    issues.append(
                        DocIssue(
                            rel, "off-lane-folder", f"{folder} is neither a lane nor allowlisted"
                        )
                    )
            continue

        # Nested folders inside a lane must be on the allowlist.
        if len(rel_path.parts) > 2:
            folder = rel_path.parent.as_posix()
            if folder not in SIDE_FOLDER_ALLOWLIST and folder not in seen_dirs:
                seen_dirs.add(folder)
                issues.append(
                    DocIssue(rel, "off-allowlist-folder", f"{folder} is not on the side-folder allowlist")
                )

        if rel_path.name == "README.md":
            continue  # lane index, not a lifecycle document

        front = _frontmatter(text)

        if lane == "2_Todo" and rel_path.name != "0_NEXT_STEPS.md":
            missing = [k for k in ("priority", "next_action") if k not in front]
            if missing:
                issues.append(
                    DocIssue(
                        rel,
                        "missing-todo-yaml",
                        f"active work should declare {', '.join(missing)}",
                        severity="warning",
                    )
                )

        if lane == "7_Superseded":
            if "superseded_by" not in front:
                issues.append(
                    DocIssue(
                        rel,
                        "missing-superseded-by",
                        "a superseded doc should point at what replaced it",
                        severity="warning",
                    )
                )
            issues.extend(_check_pointer(md, docs_root, front, "superseded_by", rel))

        if lane == "4_Reference" and rel_path.parent.name == "archived":
            issues.extend(_check_pointer(md, docs_root, front, "extracted_into", rel))

        if lane == "3_Spec":
            binding = front.get("spec_binding")
            sub = rel_path.parts[1] if len(rel_path.parts) > 2 else None
            expected = {"draft": {"draft", "candidate"}, "deprecated": {"deprecated"}}.get(
                sub or "", {"live", "candidate"}
            )
            if binding and binding not in expected:
                issues.append(
                    DocIssue(
                        rel,
                        "spec-binding-mismatch",
                        f"spec_binding: {binding} contradicts its folder "
                        f"({sub or '3_Spec'} expects one of {sorted(expected)})",
                    )
                )

    return DocsCheckResult(issues=tuple(issues), files_checked=checked)


def format_docs_check(result: DocsCheckResult) -> str:
    if not result.files_checked:
        return "No docs/ directory found."
    lines: list[str] = []
    for issue in result.warnings:
        lines.append(f"  [warning] [{issue.kind}] {issue.file}: {issue.detail}")
    if result.ok:
        lines.append(f"Docs lifecycle OK ({result.files_checked} file(s) checked).")
        if result.warnings:
            lines.append(f"{len(result.warnings)} warning(s) - incomplete, not broken.")
        return "\n".join(lines)
    lines.append(
        f"Docs lifecycle: {len(result.errors)} error(s) across {result.files_checked} file(s):"
    )
    for issue in result.errors:
        lines.append(f"  [{issue.kind}] {issue.file}: {issue.detail}")
    return "\n".join(lines)
