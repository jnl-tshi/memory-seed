import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.semantic_cache import extract_memory_chunks, rank_session_memory
from memory_seed.topics import (
    TOPIC_SLUG_RE,
    check_topics,
    expand_topic_filter,
    load_topic_index,
)


def _entry(title, entry_id, body, topics=None):
    lines = [f"## {title}", "", "```yaml", f"entry_id: {entry_id}", "user_initials: JN", "agent_type: codex"]
    if topics:
        lines.append("topics:")
        lines.extend(f"  - {slug}" for slug in topics)
    lines += ["```", "", body, ""]
    return "\n".join(lines)


class TopicsTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-topics-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def write_index(self, cwd, text):
        memory = cwd / ".memory-seed"
        memory.mkdir(parents=True, exist_ok=True)
        (memory / "topics.yaml").write_text(text, encoding="utf-8")

    def write_day(self, cwd, *entries):
        sessions = cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-07-01.md").write_text("# Log\n\n" + "\n".join(entries), encoding="utf-8")

    VOCAB = (
        "schema_version: 1\n"
        "topics:\n"
        "  - slug: retrieval\n"
        "    label: Retrieval\n"
        "    description: Search and ranking.\n"
        "    status: active\n"
        "    aliases: [search, ranking]\n"
        "  - slug: old-theme\n"
        "    label: Old Theme\n"
        "    status: deprecated\n"
        "    aliases: []\n"
    )

    def test_load_topic_index_parses_records_and_aliases(self):
        cwd = self.make_project()
        self.write_index(cwd, self.VOCAB)

        index = load_topic_index(cwd)

        self.assertTrue(index.exists)
        self.assertEqual(index.schema_version, "1")
        self.assertEqual([r.slug for r in index.topics], ["retrieval", "old-theme"])
        self.assertEqual(index.topics[0].aliases, ("search", "ranking"))
        self.assertEqual(index.topics[1].status, "deprecated")
        self.assertEqual(index.resolution()["search"], "retrieval")

    def test_chunks_parse_entry_topics(self):
        cwd = self.make_project()
        self.write_day(cwd, _entry("2026-07-01 09:00 - A", "ms-a0000000", "body.", topics=["retrieval", "search"]))

        chunks = extract_memory_chunks(cwd, granularity="entry")

        self.assertEqual(chunks[0].topics, ("retrieval", "search"))

    def test_topics_filter_is_opt_in_and_alias_expanded(self):
        cwd = self.make_project()
        self.write_index(cwd, self.VOCAB)
        self.write_day(
            cwd,
            _entry("2026-07-01 09:00 - Canonical", "ms-a0000000", "cache work.", topics=["retrieval"]),
            _entry("2026-07-01 10:00 - Alias", "ms-b0000000", "cache work.", topics=["search"]),
            _entry("2026-07-01 11:00 - Other", "ms-c0000000", "cache work.", topics=["old-theme"]),
        )

        unfiltered = rank_session_memory("cache", cwd, top_k=10)
        self.assertEqual(len(unfiltered), 3)

        expanded = expand_topic_filter(cwd, ["ranking"])  # alias in -> canonical + all aliases match
        filtered = rank_session_memory("cache", cwd, top_k=10, topics=expanded)
        self.assertEqual(
            sorted(r.chunk.entry_id for r in filtered), ["ms-a0000000", "ms-b0000000"]
        )

    def test_check_flags_unknown_and_malformed_and_collisions(self):
        cwd = self.make_project()
        self.write_index(
            cwd,
            "schema_version: 1\n"
            "topics:\n"
            "  - slug: Bad_Slug!\n"
            "    aliases: []\n"
            "  - slug: retrieval\n"
            "    aliases: [retrieval]\n",
        )
        self.write_day(cwd, _entry("2026-07-01 09:00 - A", "ms-a0000000", "x", topics=["nope"]))

        result = check_topics(cwd)

        kinds = [issue.kind for issue in result.issues]
        self.assertIn("malformed-slug", kinds)
        self.assertIn("alias-collision", kinds)
        self.assertIn("unknown-entry-topic", kinds)
        self.assertFalse(result.ok)

    def test_check_warns_on_deprecated_and_count_and_reports_unused(self):
        cwd = self.make_project()
        self.write_index(cwd, self.VOCAB)
        self.write_day(
            cwd,
            _entry("2026-07-01 09:00 - A", "ms-a0000000", "x", topics=["old-theme", "retrieval", "search", "ranking"]),
        )

        result = check_topics(cwd)

        by_kind = {}
        for issue in result.issues:
            by_kind.setdefault(issue.kind, issue)
        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])  # warnings never fail the check
        self.assertEqual(by_kind["deprecated-topic-use"].severity, "warning")
        self.assertEqual(by_kind["topic-count"].severity, "warning")

    def test_check_errors_when_entries_have_topics_but_no_index(self):
        cwd = self.make_project()
        self.write_day(cwd, _entry("2026-07-01 09:00 - A", "ms-a0000000", "x", topics=["anything"]))

        result = check_topics(cwd)

        self.assertFalse(result.ok)
        self.assertIn("missing-index", [issue.kind for issue in result.issues])

    def test_check_passes_on_clean_project_without_topics(self):
        cwd = self.make_project()
        self.write_day(cwd, _entry("2026-07-01 09:00 - A", "ms-a0000000", "x"))

        result = check_topics(cwd)

        self.assertTrue(result.ok)
        self.assertEqual(result.entries_checked, 0)

    def test_slug_regex_matches_user_slug_family(self):
        for good in ("git-workflow", "a", "x_y-z9"):
            self.assertTrue(TOPIC_SLUG_RE.match(good), good)
        for bad in ("Upper", "-lead", "has space", ""):
            self.assertFalse(TOPIC_SLUG_RE.match(bad), bad)


if __name__ == "__main__":
    unittest.main()
