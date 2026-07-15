import contextlib
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.cli import main
from memory_seed.topics import suggest_topics_from_file


class TopicsSuggestTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-topics-suggest-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def write_index(self, cwd, text):
        memory = cwd / ".memory-seed"
        memory.mkdir(parents=True, exist_ok=True)
        (memory / "topics.yaml").write_text(text, encoding="utf-8")

    def write_day(self, cwd, name="2026-07-01.md"):
        sessions = cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / name).write_text("# Log\n", encoding="utf-8")

    def run_cli(self, cwd, *argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        previous = os.getcwd()
        os.chdir(cwd)
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(list(argv))
        finally:
            os.chdir(previous)
        return code, stdout.getvalue(), stderr.getvalue()

    VOCAB = (
        "schema_version: 1\n"
        "topics:\n"
        "  - slug: retrieval\n"
        "    label: Retrieval\n"
        "    description: Search, ranking, cache, query, and retrieval behavior.\n"
        "    status: active\n"
        "    aliases: [search, ranking]\n"
        "  - slug: git-workflow\n"
        "    label: Git Workflow\n"
        "    description: Branch, merge, rebase, and commit flow.\n"
        "    status: active\n"
        "    aliases: [branching]\n"
        "  - slug: old-theme\n"
        "    label: Old Theme\n"
        "    description: Legacy ranking work.\n"
        "    status: deprecated\n"
        "    aliases: [legacy-ranking]\n"
    )
    MANY_MATCHES_VOCAB = (
        "schema_version: 1\n"
        "topics:\n"
        "  - slug: alpha-topic\n"
        "    label: Alpha Topic\n"
        "    description: Alpha signal.\n"
        "    status: active\n"
        "    aliases: []\n"
        "  - slug: beta-topic\n"
        "    label: Beta Topic\n"
        "    description: Beta signal.\n"
        "    status: active\n"
        "    aliases: []\n"
        "  - slug: gamma-topic\n"
        "    label: Gamma Topic\n"
        "    description: Gamma signal.\n"
        "    status: active\n"
        "    aliases: []\n"
        "  - slug: delta-topic\n"
        "    label: Delta Topic\n"
        "    description: Delta signal.\n"
        "    status: active\n"
        "    aliases: []\n"
        "  - slug: epsilon-topic\n"
        "    label: Epsilon Topic\n"
        "    description: Epsilon signal.\n"
        "    status: active\n"
        "    aliases: []\n"
    )

    def test_suggest_topics_ranks_active_matches_with_alias_evidence(self):
        cwd = self.make_project()
        self.write_index(cwd, self.VOCAB)
        source = cwd / "retrieval-ranking-notes.md"
        source.write_text(
            "We should improve cache ranking and query retrieval before the next branch merge.\n",
            encoding="utf-8",
        )

        resolved, suggestions = suggest_topics_from_file(source, cwd=cwd)

        self.assertEqual(resolved, source)
        self.assertEqual([item.topic.slug for item in suggestions], ["retrieval", "git-workflow"])
        self.assertGreater(suggestions[0].score, suggestions[1].score)
        self.assertIn("aliases", suggestions[0].matched_fields)
        self.assertIn("ranking", suggestions[0].matched_terms)
        self.assertIn(("aliases", ("ranking",)), suggestions[0].evidence)

    def test_suggest_is_deterministic_and_skips_deprecated_topics(self):
        cwd = self.make_project()
        self.write_index(cwd, self.VOCAB)
        source = cwd / "legacy-ranking.md"
        source.write_text("Legacy ranking notes moved to the new retrieval path.\n", encoding="utf-8")

        first = suggest_topics_from_file(source, cwd=cwd)[1]
        second = suggest_topics_from_file(source, cwd=cwd)[1]

        self.assertEqual(first, second)
        self.assertEqual([item.topic.slug for item in first], ["retrieval"])

    def test_suggest_returns_no_match_when_no_topic_text_overlaps(self):
        cwd = self.make_project()
        self.write_index(cwd, self.VOCAB)
        source = cwd / "garden.txt"
        source.write_text("Tomatoes, basil, and watering schedule.\n", encoding="utf-8")

        _, suggestions = suggest_topics_from_file(source, cwd=cwd)

        self.assertEqual(suggestions, ())

    def test_suggest_tie_breaks_by_slug_ascending(self):
        cwd = self.make_project()
        self.write_index(
            cwd,
            "schema_version: 1\n"
            "topics:\n"
            "  - slug: alpha-topic\n"
            "    label: Shared Term\n"
            "    description: Shared term.\n"
            "    status: active\n"
            "    aliases: []\n"
            "  - slug: beta-topic\n"
            "    label: Shared Term\n"
            "    description: Shared term.\n"
            "    status: active\n"
            "    aliases: []\n",
        )
        source = cwd / "shared-term.md"
        source.write_text("Shared term.\n", encoding="utf-8")

        _, suggestions = suggest_topics_from_file(source, cwd=cwd)

        self.assertEqual([item.topic.slug for item in suggestions], ["alpha-topic", "beta-topic"])

    def test_suggest_code_like_source_keeps_evidence_terms_clean(self):
        cwd = self.make_project()
        self.write_index(cwd, self.VOCAB)
        source = cwd / "memory_seed_retrieval.py"
        source.write_text(
            "from memory_seed.retrieval import rank_session_memory\n"
            "cache_ranking.append('.topics')\n"
            "QUERY_CACHE = '/tmp/retrieval.py'\n",
            encoding="utf-8",
        )

        _, suggestions = suggest_topics_from_file(source, cwd=cwd)

        self.assertEqual(suggestions[0].topic.slug, "retrieval")
        evidence_terms = {term for _, terms in suggestions[0].evidence for term in terms}
        self.assertIn("retrieval", evidence_terms)
        self.assertIn("ranking", evidence_terms)
        self.assertNotIn(".topics", evidence_terms)
        self.assertNotIn("memory_seed.retrieval", evidence_terms)
        self.assertTrue(all(not term.startswith(".") for term in evidence_terms))
        self.assertTrue(all("." not in term and "/" not in term for term in evidence_terms))

    def test_cli_suggest_prints_ranked_reasons_and_paste_ready_snippet(self):
        cwd = self.make_project()
        self.write_index(cwd, self.VOCAB)
        source = cwd / "notes.md"
        source.write_text("Branch merge and cache ranking need cleanup.\n", encoding="utf-8")

        code, stdout, stderr = self.run_cli(cwd, "topics", "suggest", "--from", "notes.md")

        self.assertEqual(code, 0, stderr)
        self.assertEqual(stderr, "")
        self.assertIn("Suggested topics for notes.md:", stdout)
        self.assertIn("retrieval", stdout)
        self.assertIn("git-workflow", stdout)
        self.assertIn("why:", stdout)
        self.assertIn("Paste into the entry's YAML:", stdout)
        self.assertIn("topics:\n  - retrieval\n  - git-workflow", stdout)

    def test_cli_suggest_paste_ready_block_is_capped_at_three_topics(self):
        cwd = self.make_project()
        self.write_index(cwd, self.MANY_MATCHES_VOCAB)
        source = cwd / "alpha-beta-gamma-delta-epsilon.md"
        source.write_text("alpha beta gamma delta epsilon\n", encoding="utf-8")

        code, stdout, stderr = self.run_cli(cwd, "topics", "suggest", "--from", "alpha-beta-gamma-delta-epsilon.md")

        self.assertEqual(code, 0, stderr)
        self.assertEqual(stderr, "")
        self.assertIn("topics:\n  - alpha-topic\n  - beta-topic\n  - delta-topic", stdout)
        self.assertNotIn("  - epsilon-topic", stdout.split("Paste into the entry's YAML:\n", 1)[1])
        self.assertEqual(stdout.split("Paste into the entry's YAML:\n", 1)[1].count("\n  - "), 3)

    def test_cli_suggest_errors_for_missing_file(self):
        cwd = self.make_project()
        self.write_index(cwd, self.VOCAB)

        code, stdout, stderr = self.run_cli(cwd, "topics", "suggest", "--from", "missing.md")

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("missing.md does not exist", stderr)

    def test_cli_suggest_errors_for_directory_input(self):
        cwd = self.make_project()
        self.write_index(cwd, self.VOCAB)
        source_dir = cwd / "notes"
        source_dir.mkdir()

        code, stdout, stderr = self.run_cli(cwd, "topics", "suggest", "--from", "notes")

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("is a directory", stderr)

    def test_cli_suggest_errors_for_missing_malformed_and_empty_index(self):
        cwd = self.make_project()
        source = cwd / "notes.md"
        source.write_text("cache ranking\n", encoding="utf-8")

        code, _, stderr = self.run_cli(cwd, "topics", "suggest", "--from", "notes.md")
        self.assertEqual(code, 1)
        self.assertIn(".memory-seed/topics.yaml does not exist", stderr)

        self.write_index(cwd, "schema_version: 1\ntopics:\n  - slug: Bad!\n")
        code, _, stderr = self.run_cli(cwd, "topics", "suggest", "--from", "notes.md")
        self.assertEqual(code, 1)
        self.assertIn("malformed-slug", stderr)

        self.write_index(cwd, "schema_version: 1\ntopics:\n")
        code, _, stderr = self.run_cli(cwd, "topics", "suggest", "--from", "notes.md")
        self.assertEqual(code, 1)
        self.assertIn("defines no topics", stderr)

    def test_cli_suggest_errors_for_binary_and_invalid_utf8_input(self):
        cwd = self.make_project()
        self.write_index(cwd, self.VOCAB)
        binary = cwd / "image.bin"
        binary.write_bytes(b"\x00\x01topic")

        code, _, stderr = self.run_cli(cwd, "topics", "suggest", "--from", "image.bin")
        self.assertEqual(code, 1)
        self.assertIn("looks like a binary file", stderr)

        broken = cwd / "broken.md"
        broken.write_bytes(b"\xffranking")
        code, _, stderr = self.run_cli(cwd, "topics", "suggest", "--from", "broken.md")
        self.assertEqual(code, 1)
        self.assertIn("not valid UTF-8", stderr)

    def test_cli_suggest_does_not_write_project_files(self):
        cwd = self.make_project()
        self.write_index(cwd, self.VOCAB)
        self.write_day(cwd)
        source = cwd / "notes.md"
        source.write_text("Cache ranking and retrieval.\n", encoding="utf-8")
        before = {path.relative_to(cwd).as_posix(): path.read_bytes() for path in cwd.rglob("*") if path.is_file()}

        code, stdout, stderr = self.run_cli(cwd, "topics", "suggest", "--from", "notes.md")

        self.assertEqual(code, 0, stderr)
        self.assertIn("retrieval", stdout)
        after = {path.relative_to(cwd).as_posix(): path.read_bytes() for path in cwd.rglob("*") if path.is_file()}
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
