import json
import shutil
import tempfile
import unittest
from pathlib import Path

from memory_trace.evidence import build_timeline_evidence_pack

BASE = "mse_aaaaaaaaaaaaaaaa"
EVOLVE = "mse_bbbbbbbbbbbbbbbb"
REPLACE = "mse_cccccccccccccccc"
REVIEW = "mse_dddddddddddddddd"


def _entry(
    title: str,
    entry_id: str,
    body: str,
    *,
    agent: str = "codex",
    related: list[str] | None = None,
    supersedes: list[str] | None = None,
    evolves: list[str] | None = None,
    topics: list[str] | None = None,
    branch: str | None = None,
) -> str:
    lines = [
        f"## {title}",
        "",
        "```yaml",
        f"entry_id: {entry_id}",
        "user_initials: JN",
        f"agent_type: {agent}",
        "project_path: .",
        "subproject_path: null",
    ]
    if branch:
        lines.append(f"branch: {branch}")
    if topics:
        lines.append("topics:")
        lines.extend(f"  - {topic}" for topic in topics)
    if related:
        lines.append("related_entries:")
        lines.extend(f"  - {item}" for item in related)
    if supersedes:
        lines.append("supersedes:")
        lines.extend(f"  - {item}" for item in supersedes)
    if evolves:
        lines.append("evolves:")
        lines.extend(f"  - {item}" for item in evolves)
    lines += [
        "```",
        "",
        body,
        "",
        "### Decision",
        "",
        f"- D: {entry_id} decision.",
        "",
        "### Tests",
        "",
        f"- T: {entry_id} tests passed.",
        "",
    ]
    return "\n".join(lines)


class EvidencePackTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        temp_root = Path(tempfile.mkdtemp(prefix="memory-seed-evidence-pack-"))
        self.addCleanup(lambda: shutil.rmtree(temp_root, ignore_errors=True))
        self.cwd = temp_root / "evidence-pack-workspace"
        self._write_session(
            "2026-06/2026-06-01.md",
            _entry(
                "2026-06-01 09:00 - Base timeline entry",
                BASE,
                "Base timeline body with #timeline context.",
                topics=["timeline"],
            ),
        )
        self._write_session(
            "2026-06/2026-06-02.md",
            _entry(
                "2026-06-02 10:00 - Evolve timeline entry",
                EVOLVE,
                "Evolve timeline body with #timeline and #graph context.",
                agent="claude",
                related=[BASE],
                evolves=[BASE],
                topics=["timeline", "graph"],
                branch="feature/evolve",
            ),
        )
        self._write_session(
            "2026-06/2026-06-03.md",
            _entry(
                "2026-06-03 11:00 - Replace timeline entry",
                REPLACE,
                "Replace timeline body with #timeline and #graph context.",
                supersedes=[BASE],
                topics=["timeline", "graph"],
            ),
        )
        self._write_session(
            "2026-06/2026-06-04.md",
            _entry(
                "2026-06-04 12:00 - Review graph entry",
                REVIEW,
                "Review graph body with #graph context.",
                related=[EVOLVE],
                topics=["graph"],
                branch="feature/evolve",
            ),
        )
        self._write_link_sidecar(
            "2026-06/2026-06-04.md",
            "2026-06-04 12:30",
            "Review late edge",
            REVIEW,
            evolves=[REPLACE],
        )
        self._write_diagram_sidecar(
            "2026-06/2026-06-02.md",
            "2026-06-02 10:15",
            "Timeline evolve diagram",
            EVOLVE,
        )

    def _write_session(self, relative_path: str, content: str) -> None:
        path = self.cwd / ".memory-seed" / "sessions" / Path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\ntags:\n  - session-log\n---\n\n" + content, encoding="utf-8")

    def _write_link_sidecar(
        self,
        relative_path: str,
        heading_time: str,
        title: str,
        entry_id: str,
        *,
        related: list[str] | None = None,
        supersedes: list[str] | None = None,
        evolves: list[str] | None = None,
    ) -> None:
        path = self.cwd / ".memory-seed" / "sessions" / "links" / Path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"## {heading_time} - {title}",
            "",
            "```yaml",
            f"entry_id: {entry_id}",
        ]
        if related:
            lines.append("related_entries:")
            lines.extend(f"  - {item}" for item in related)
        if supersedes:
            lines.append("supersedes:")
            lines.extend(f"  - {item}" for item in supersedes)
        if evolves:
            lines.append("evolves:")
            lines.extend(f"  - {item}" for item in evolves)
        lines += ["```", ""]
        path.write_text("\n".join(lines), encoding="utf-8")

    def _write_diagram_sidecar(self, relative_path: str, heading_time: str, title: str, entry_id: str) -> None:
        path = self.cwd / ".memory-seed" / "sessions" / "diagrams" / Path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    f"## {heading_time} - {title}",
                    "",
                    "```yaml",
                    f"entry_id: {entry_id}",
                    "```",
                    "",
                    "```mermaid",
                    "flowchart TD",
                    "  A --> B",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def test_build_timeline_evidence_pack_is_runtime_root_stable(self):
        nested = self.cwd / "memory-trace"
        nested.mkdir(parents=True, exist_ok=True)

        root_pack = build_timeline_evidence_pack(self.cwd)
        nested_pack = build_timeline_evidence_pack(nested)

        self.assertEqual(root_pack, nested_pack)

    def test_build_timeline_evidence_pack_snapshot(self):
        pack = build_timeline_evidence_pack(self.cwd)
        rendered = json.dumps(pack, sort_keys=True, indent=2)
        fixture = (
            Path(__file__).resolve().parent / "fixtures" / "evidence-pack" / "timeline-linked.json"
        ).read_text(encoding="utf-8").rstrip("\n")
        self.assertEqual(rendered, fixture)

    def test_build_timeline_evidence_pack_filters_by_topic_and_agent(self):
        pack = build_timeline_evidence_pack(self.cwd, topic="graph", agent="codex")

        self.assertEqual([entry["entry_id"] for entry in pack["entries"]], [REPLACE, REVIEW])
        self.assertEqual(
            pack["graph"]["edges"],
            [{"source": REVIEW, "target": REPLACE, "type": "evolves"}],
        )
        self.assertEqual(
            pack["missing_evidence"],
            [
                {
                    "entry_id": REPLACE,
                    "kind": "referenced_entry_not_in_pack",
                    "reason": "excluded_by_filters",
                    "referenced_entry_id": BASE,
                    "referenced_entry_title": None,
                    "relation_types": ["supersedes"],
                },
                {
                    "entry_id": REVIEW,
                    "kind": "referenced_entry_not_in_pack",
                    "reason": "excluded_by_filters",
                    "referenced_entry_id": EVOLVE,
                    "referenced_entry_title": None,
                    "relation_types": ["related"],
                },
            ],
        )

    def test_build_timeline_evidence_pack_is_deterministic(self):
        first = build_timeline_evidence_pack(self.cwd, generated_at=None)
        second = build_timeline_evidence_pack(self.cwd, generated_at=None)

        self.assertEqual(
            json.dumps(first, sort_keys=True, separators=(",", ":")),
            json.dumps(second, sort_keys=True, separators=(",", ":")),
        )
        self.assertEqual(first["pack_fingerprint"], second["pack_fingerprint"])

    def test_build_timeline_evidence_pack_reports_empty_selection(self):
        pack = build_timeline_evidence_pack(self.cwd, date_from="2026-07-01", date_to="2026-07-02")

        self.assertEqual(pack["entries"], [])
        self.assertEqual(pack["chunks"], [])
        self.assertEqual(pack["graph"]["edges"], [])
        self.assertIn({"kind": "no_entries_match_selection"}, pack["missing_evidence"])

    def test_build_timeline_evidence_pack_reports_missing_references(self):
        pack = build_timeline_evidence_pack(
            self.cwd,
            topic="graph",
            agent="codex",
            entry_ids=[REVIEW, "mse_missingggggggg"],
        )

        self.assertEqual([entry["entry_id"] for entry in pack["entries"]], [REVIEW])
        self.assertIn({"kind": "requested_entry_missing", "entry_id": "mse_missingggggggg"}, pack["missing_evidence"])
        self.assertIn(
            {
                "kind": "referenced_entry_not_in_pack",
                "entry_id": REVIEW,
                "referenced_entry_id": EVOLVE,
                "relation_types": ["related"],
                "reason": "excluded_by_filters",
                "referenced_entry_title": None,
            },
            pack["missing_evidence"],
        )
        self.assertIn(
            {
                "kind": "referenced_entry_not_in_pack",
                "entry_id": REVIEW,
                "referenced_entry_id": REPLACE,
                "relation_types": ["evolves"],
                "reason": "outside_selection",
                "referenced_entry_title": "2026-06-03 11:00 - Replace timeline entry",
            },
            pack["missing_evidence"],
        )
