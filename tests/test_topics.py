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

    def test_check_validates_decision_qualified_authored_topics_per_decision(self):
        cwd = self.make_project()
        self.write_index(cwd, self.VOCAB)
        self.write_day(
            cwd,
            _entry(
                "2026-07-01 09:00 - A",
                "ms-a0000000",
                "body.",
                topics=["retrieval:d1", "search:d1", "ranking:d1", "retrieval:d2"],
            ),
        )

        result = check_topics(cwd)

        self.assertTrue(result.ok, [issue.__dict__ for issue in result.issues])
        self.assertNotIn("unknown-entry-topic", [issue.kind for issue in result.issues])
        self.assertNotIn("topic-count", [issue.kind for issue in result.issues])

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

    def test_inferred_only_entries_are_counted_separately_and_not_validated_here(self):
        # Coverage widens; authorship does not. `entries_checked` must keep
        # meaning "a human wrote these", so an entry whose topics come only from
        # a sidecar is reported on its own axis. Validation stays in `links
        # check` - a second validator here would drift from the first, so even a
        # slug outside the vocabulary raises nothing on this surface.
        cwd = self.make_project()
        self.write_day(
            cwd,
            _entry("2026-07-01 09:00 - A", "ms-a0000000", "x", topics=["retrieval"]),
            _entry("2026-07-01 10:00 - B", "ms-b0000000", "y"),
        )
        self.write_index(cwd, self.VOCAB)
        sidecar = cwd / ".memory-seed" / "sessions" / "topics" / "2026-07" / "2026-07-01.md"
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar.write_text(
            "## 2026-07-01 11:00 - topics\n\n```yaml\nentry_id: ms-b0000000\ntopics:\n"
            "  - not-in-the-vocabulary:d1\n```\n",
            encoding="utf-8",
        )

        result = check_topics(cwd)

        self.assertEqual(result.entries_checked, 1)  # only the authored one
        self.assertEqual(result.entries_with_inferred_topics_only, 1)
        self.assertNotIn("unknown-entry-topic", [issue.kind for issue in result.issues])

    def test_slug_regex_matches_user_slug_family(self):
        for good in ("git-workflow", "a", "x_y-z9"):
            self.assertTrue(TOPIC_SLUG_RE.match(good), good)
        for bad in ("Upper", "-lead", "has space", ""):
            self.assertFalse(TOPIC_SLUG_RE.match(bad), bad)

    # --- Hierarchy: axis + parent (schema_version 2) ---

    HIER = (
        "schema_version: 2\n"
        "topics:\n"
        "  - slug: memory-trace\n"
        "    axis: area\n"
        "    aliases: [memory-trace-ui]\n"
        "  - slug: trail\n"
        "    axis: area\n"
        "    parent: memory-trace\n"
        "    aliases: [timeline]\n"
        "  - slug: trail-lanes\n"
        "    parent: trail\n"
        "    aliases: []\n"
        "  - slug: documentation\n"
        "    axis: activity\n"
        "    aliases: []\n"
    )

    def test_axis_and_parent_parse_and_ancestors_walk_up(self):
        cwd = self.make_project()
        self.write_index(cwd, self.HIER)

        index = load_topic_index(cwd)
        by = {t.slug: t for t in index.topics}

        self.assertEqual(by["trail"].axis, "area")
        self.assertEqual(by["trail"].parent, "memory-trace")
        # Depth is not capped at two: a grandchild walks the whole chain.
        self.assertEqual(index.ancestors("trail-lanes"), ("trail", "memory-trace"))
        self.assertEqual(index.ancestors("memory-trace"), ())

    def test_axis_is_inherited_from_the_nearest_declaring_ancestor(self):
        # `trail-lanes` declares no axis; it is an area because its parent chain says so.
        cwd = self.make_project()
        self.write_index(cwd, self.HIER)

        index = load_topic_index(cwd)

        self.assertEqual(index.axis_of("trail-lanes"), "area")
        self.assertEqual(index.axis_of("documentation"), "activity")
        self.assertEqual(index.axis_of("nonexistent"), "")

    def test_filter_expands_down_to_descendants_but_never_up_to_parents(self):
        # Only the most specific slug is stored, so filtering on a parent must
        # reach its children -- and filtering on a child must NOT drag in the
        # parent's broader population.
        cwd = self.make_project()
        self.write_index(cwd, self.HIER)

        parent = expand_topic_filter(cwd, ["memory-trace"])
        child = expand_topic_filter(cwd, ["trail"])

        self.assertIn("trail", parent)
        self.assertIn("trail-lanes", parent, "expansion must reach a grandchild")
        self.assertIn("timeline", parent, "a descendant's aliases match too")
        self.assertNotIn("memory-trace", child, "expansion must never run upward")
        self.assertIn("trail-lanes", child)

    def test_a_parent_cycle_does_not_hang_the_walk(self):
        # A cycle is a vocabulary defect, but resolution must terminate rather
        # than spin -- this is read on every search.
        cwd = self.make_project()
        self.write_index(
            cwd,
            "schema_version: 2\ntopics:\n"
            "  - slug: a\n    parent: b\n    aliases: []\n"
            "  - slug: b\n    parent: a\n    aliases: []\n",
        )

        index = load_topic_index(cwd)

        self.assertEqual(index.ancestors("a"), ("b",))

    def test_a_parent_cycle_is_reported_as_a_validation_error(self):
        # `ancestors()` terminating rather than raising is what makes a cycle
        # SILENT, so validation is the only place it can surface. Reported once
        # per cycle, not once per member: three slugs in a three-cycle are one
        # defect, and three copies would bury it.
        cwd = self.make_project()
        self.write_index(
            cwd,
            "schema_version: 2\ntopics:\n"
            "  - slug: a\n    parent: b\n    aliases: []\n"
            "  - slug: b\n    parent: c\n    aliases: []\n"
            "  - slug: c\n    parent: a\n    aliases: []\n"
            "  - slug: fine\n    aliases: []\n",
        )

        result = check_topics(cwd)

        cycles = [i for i in result.issues if i.kind == "parent-cycle"]
        self.assertEqual(len(cycles), 1, [i.detail for i in cycles])
        self.assertEqual(cycles[0].severity, "error")
        self.assertFalse(result.ok)
        for slug in ("a", "b", "c"):
            self.assertIn(slug, cycles[0].detail)
        # The walk still terminates -- detection must not have cost that.
        self.assertEqual(len(load_topic_index(cwd).ancestors("a")), 2)

    def test_a_self_parent_is_a_cycle(self):
        cwd = self.make_project()
        self.write_index(cwd, "schema_version: 2\ntopics:\n  - slug: a\n    parent: a\n    aliases: []\n")

        result = check_topics(cwd)

        self.assertEqual(len([i for i in result.issues if i.kind == "parent-cycle"]), 1)

    def test_an_acyclic_hierarchy_reports_no_cycle(self):
        # The negative half: without it, code that reported every parent chain
        # as a cycle would pass the tests above.
        cwd = self.make_project()
        self.write_index(cwd, self.HIER)

        result = check_topics(cwd)

        self.assertNotIn("parent-cycle", [i.kind for i in result.issues])

    def test_a_schema_version_1_vocabulary_is_completely_unaffected(self):
        # The whole of step 1 is additive. A vocabulary that declares no axis and
        # no parent must resolve, expand and validate exactly as it did before.
        cwd = self.make_project()
        self.write_index(cwd, self.VOCAB)

        index = load_topic_index(cwd)

        self.assertEqual([t.axis for t in index.topics], ["", ""])
        self.assertEqual([t.parent for t in index.topics], ["", ""])
        self.assertEqual(index.ancestors("retrieval"), ())
        self.assertEqual(index.descendants("retrieval"), ())
        self.assertEqual(index.axis_of("retrieval"), "")
        # Alias expansion is byte-for-byte what it was: canonical plus aliases.
        self.assertEqual(expand_topic_filter(cwd, ["retrieval"]), {"retrieval", "search", "ranking"})

    # --- Recursive mapping tree (schema_version 3) ---

    V3 = """schema_version: 3
topics:
  area:
    memory-trace:
      label: Memory Trace
      description: Review interface.
      status: active
      aliases: [memory-trace-ui]
      children:
        trail:
          label: Trail
          description: Timeline view.
          status: active
          aliases:
            - timeline
          children:
            trail-lanes:
              label: Trail Lanes
              description: Lane assignment.
              status: active
              aliases: []
  activity:
    documentation:
      label: Documentation
      description: Public docs.
      status: active
      aliases: []
"""

    V2_EQUIVALENT = """schema_version: 2
topics:
  - slug: memory-trace
    label: Memory Trace
    description: Review interface.
    status: active
    axis: area
    aliases: [memory-trace-ui]
  - slug: trail
    label: Trail
    description: Timeline view.
    status: active
    parent: memory-trace
    aliases: [timeline]
  - slug: trail-lanes
    label: Trail Lanes
    description: Lane assignment.
    status: active
    parent: trail
    aliases: []
  - slug: documentation
    label: Documentation
    description: Public docs.
    status: active
    axis: activity
    aliases: []
"""

    def test_v3_mapping_tree_derives_axis_parent_and_arbitrary_depth(self):
        cwd = self.make_project()
        self.write_index(cwd, self.V3)

        index = load_topic_index(cwd)
        by = {topic.slug: topic for topic in index.topics}

        self.assertEqual(index.schema_version, "3")
        self.assertEqual([topic.slug for topic in index.topics], [
            "memory-trace", "trail", "trail-lanes", "documentation"
        ])
        self.assertEqual(by["memory-trace"].axis, "area")
        self.assertEqual(by["trail"].axis, "")
        self.assertEqual(by["trail"].parent, "memory-trace")
        self.assertEqual(by["trail-lanes"].parent, "trail")
        self.assertEqual(by["trail"].aliases, ("timeline",))
        self.assertEqual(index.ancestors("trail-lanes"), ("trail", "memory-trace"))
        self.assertEqual(index.axis_of("trail-lanes"), "area")
        self.assertEqual(index.axis_of("documentation"), "activity")
        self.assertEqual(index.parse_issues, ())

    def test_v2_and_v3_normalize_to_identical_topic_records(self):
        v2 = self.make_project()
        v3 = self.make_project()
        self.write_index(v2, self.V2_EQUIVALENT)
        self.write_index(v3, self.V3)

        before = {topic.slug: topic for topic in load_topic_index(v2).topics}
        after = {topic.slug: topic for topic in load_topic_index(v3).topics}

        self.assertEqual(before, after)
        self.assertEqual(expand_topic_filter(v2, ["memory-trace"]), expand_topic_filter(v3, ["memory-trace"]))

    def test_v3_rejects_redundant_structure_and_malformed_children(self):
        cwd = self.make_project()
        self.write_index(
            cwd,
            """schema_version: 3
topics:
  area:
    root:
      axis: area
      children: []
      aliases: []
""",
        )

        result = check_topics(cwd)
        kinds = {issue.kind for issue in result.issues}

        self.assertFalse(result.ok)
        self.assertIn("redundant-topic-structure", kinds)
        self.assertIn("malformed-topic-children", kinds)

    def test_v3_rejects_list_records_unknown_axes_and_duplicate_slugs(self):
        cwd = self.make_project()
        self.write_index(
            cwd,
            """schema_version: 3
topics:
  subject:
    ignored: {}
  area:
    shared:
      aliases: []
    - slug: old-list-record
  activity:
    shared:
      aliases: []
""",
        )

        result = check_topics(cwd)
        kinds = [issue.kind for issue in result.issues]

        self.assertFalse(result.ok)
        self.assertIn("invalid-topic-axis", kinds)
        self.assertIn("malformed-topic-node", kinds)
        self.assertIn("duplicate-slug", kinds)

    def test_unknown_topic_schema_is_reported_without_guessing_a_shape(self):
        cwd = self.make_project()
        self.write_index(cwd, "schema_version: 4\ntopics:\n  area:\n    retrieval:\n      aliases: []\n")

        index = load_topic_index(cwd)
        result = check_topics(cwd)

        self.assertEqual(index.topics, ())
        self.assertFalse(result.ok)
        self.assertIn("unsupported-topic-schema", [issue.kind for issue in result.issues])


if __name__ == "__main__":
    unittest.main()
