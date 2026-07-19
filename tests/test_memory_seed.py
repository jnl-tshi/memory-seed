import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

from memory_seed.core import (
    MEMORY_DIR_NAME,
    PACKAGE_ROOT,
    SEED_FILES,
    CORE_SKILL_NAMES,
    OPTIONAL_SKILL_NAMES,
    SKILL_PROFILES,
    add_skill,
    check_session_links,
    compact_sessions,
    doctor,
    generate_session_entry_id,
    get_version,
    init_project,
    iter_session_documents,
    migrate_session_month_layout,
    migrate_session_layout,
    resolve_runtime,
    remove_skill,
    session_fuse,
    session_merge_branch,
    session_open_pr,
    session_prepare_pr_branch,
    session_target,
    skill_status,
    update_project,
)


class MemorySeedTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_version_reads_reusable_control_plane_version(self):
        self.assertEqual(get_version(), "2.19")

    def test_read_integration_mode_defaults_parses_and_fails_open(self):
        from memory_seed.core import DEFAULT_INTEGRATION_MODE, read_integration_mode

        cwd = self.make_project()
        mseed = cwd / MEMORY_DIR_NAME
        mseed.mkdir(parents=True, exist_ok=True)

        # Absent file -> default (legacy/unconfigured behaves as before).
        self.assertEqual(read_integration_mode(cwd), "local-merge")
        # Present file without the key -> default.
        (mseed / "project.yaml").write_text(
            "participants:\n  - slug: jean\n    initials: JN\n", encoding="utf-8"
        )
        self.assertEqual(read_integration_mode(cwd), "local-merge")
        # Declared pr (alongside other keys).
        (mseed / "project.yaml").write_text(
            "integration_mode: pr\nparticipants:\n  - slug: jean\n    initials: JN\n", encoding="utf-8"
        )
        self.assertEqual(read_integration_mode(cwd), "pr")
        # Explicit local-merge.
        (mseed / "project.yaml").write_text("integration_mode: local-merge\n", encoding="utf-8")
        self.assertEqual(read_integration_mode(cwd), "local-merge")
        # Unrecognised value fails open to the default, not the garbage.
        (mseed / "project.yaml").write_text("integration_mode: octopus\n", encoding="utf-8")
        self.assertEqual(read_integration_mode(cwd), DEFAULT_INTEGRATION_MODE)
        # Quoted value is accepted.
        (mseed / "project.yaml").write_text('integration_mode: "pr"\n', encoding="utf-8")
        self.assertEqual(read_integration_mode(cwd), "pr")

    def test_suggest_integration_mode_uses_collaborator_signal(self):
        import json
        import unittest.mock

        from memory_seed.core import suggest_integration_mode

        cwd = self.make_project()
        self._init_git_project(cwd)
        self._git(cwd, "remote", "add", "origin", "https://example.com/org/repo.git")

        with unittest.mock.patch(
            "memory_seed.core._gh_text",
            side_effect=[
                (0, "gh version 2.0.0", ""),
                (0, "", ""),
                (
                    0,
                    json.dumps(
                        {
                            "nameWithOwner": "org/repo",
                            "defaultBranchRef": {"name": "main"},
                            "branchProtectionRules": [],
                        }
                    ),
                    "",
                ),
                (0, "[]", ""),
                (0, json.dumps([{"login": "alice"}, {"login": "bob"}]), ""),
            ],
        ):
            mode, reason = suggest_integration_mode(cwd)

        self.assertEqual(mode, "pr")
        self.assertIn("more than one collaborator", reason)

    def test_suggest_integration_mode_fails_open_on_bad_gh_responses(self):
        import json
        import unittest.mock

        from memory_seed.core import suggest_integration_mode

        cwd = self.make_project()
        self._init_git_project(cwd)
        self._git(cwd, "remote", "add", "origin", "https://example.com/org/repo.git")

        with self.subTest("malformed json"):
            with unittest.mock.patch(
                "memory_seed.core._gh_text",
                side_effect=[
                    (0, "gh version 2.0.0", ""),
                    (0, "", ""),
                    (
                        0,
                        json.dumps(
                            {
                                "nameWithOwner": "org/repo",
                                "defaultBranchRef": {"name": "main"},
                                "branchProtectionRules": [],
                            }
                        ),
                        "",
                    ),
                    (0, "{not-json", ""),
                    (0, "{still-not-json", ""),
                ],
            ):
                mode, reason = suggest_integration_mode(cwd)
            self.assertEqual(mode, "local-merge")
            self.assertIn("no team PR signals", reason)

        with self.subTest("failing collaborator query"):
            with unittest.mock.patch(
                "memory_seed.core._gh_text",
                side_effect=[
                    (0, "gh version 2.0.0", ""),
                    (0, "", ""),
                    (
                        0,
                        json.dumps(
                            {
                                "nameWithOwner": "org/repo",
                                "defaultBranchRef": {"name": "main"},
                                "branchProtectionRules": [],
                            }
                        ),
                        "",
                    ),
                    (0, "[]", ""),
                    (1, "", "boom"),
                ],
            ):
                mode, reason = suggest_integration_mode(cwd)
            self.assertEqual(mode, "local-merge")
            self.assertIn("no team PR signals", reason)

    def test_integration_mode_contract_has_live_seed_parity(self):
        pairs = (
            (
                Path(".memory-seed/agent-rules.md"),
                Path("memory_seed/seed/.memory-seed/agent-rules.md"),
            ),
            (
                Path(".memory-seed/project-bootstrap.md"),
                Path("memory_seed/seed/.memory-seed/project-bootstrap.md"),
            ),
            (
                Path(".memory-seed/skills/agent_collaboration.md"),
                Path("memory_seed/seed/.memory-seed/skills/agent_collaboration.md"),
            ),
            (
                Path(".memory-seed/skills/session_logging.md"),
                Path("memory_seed/seed/.memory-seed/skills/session_logging.md"),
            ),
        )
        for live, seed in pairs:
            self.assertEqual(live.read_text(encoding="utf-8"), seed.read_text(encoding="utf-8"))

        rules = pairs[0][0].read_text(encoding="utf-8")
        collaboration = pairs[2][0].read_text(encoding="utf-8")
        bootstrap = pairs[1][0].read_text(encoding="utf-8")
        self.assertIn("integration_mode", rules)
        self.assertIn("local-merge", rules)
        self.assertIn("normal non-force push and PR", rules)
        self.assertIn("integration_artifact", collaboration)
        self.assertIn("from the task branch", collaboration)
        self.assertIn("human confirms", bootstrap)
        self.assertIn("never silently changed", bootstrap)

    def test_write_integration_mode_refuses_unreadable_existing_config(self):
        import unittest.mock

        from memory_seed.core import write_integration_mode

        cwd = self.make_project()
        config = cwd / MEMORY_DIR_NAME / "project.yaml"
        config.parent.mkdir(parents=True, exist_ok=True)
        original_bytes = b"participants:\n  - slug: jean\n"
        config.write_bytes(original_bytes)
        original_read_text = Path.read_text

        def fail_config_read(path, *args, **kwargs):
            if path == config:
                raise OSError("simulated read failure")
            return original_read_text(path, *args, **kwargs)

        with unittest.mock.patch.object(Path, "read_text", new=fail_config_read):
            with self.assertRaisesRegex(ValueError, "cannot read existing"):
                write_integration_mode(cwd, "pr")

        self.assertEqual(config.read_bytes(), original_bytes)

    def test_entry_body_format_issues_flags_malformed_draft(self):
        from memory_seed.core import entry_body_format_issues as fmt

        # Well-formed shapes produce no issues.
        self.assertEqual(fmt("### Decision\n\n- D: chose X\n- R: because Y"), [])
        self.assertEqual(fmt("### Summary\n\n- a plain note, no DRAFT"), [])  # DRAFT not forced
        self.assertEqual(
            fmt("### Decisions\n\n#### D1 - a\n\n- D: x\n- R: y\n\n#### D2 - b\n\n- D: z\n- R: w"), []
        )
        # Nested '- R:' under an inline '- D1:' under '### Decisions' is a valid,
        # readable style - must NOT false-positive as 'D without R'.
        self.assertEqual(fmt("### Decisions\n\n- D1: a\n  - R: reason\n  - F: file"), [])

        # Bare labels (no '- ') and no heading.
        bare = fmt("D: chose X\nR: because Y")
        self.assertTrue(any("not list items" in i for i in bare))
        self.assertTrue(any("no '### Decision'" in i for i in bare))
        # Several decisions crammed under a singular '### Decision'.
        self.assertTrue(
            any("singular '### Decision'" in i for i in fmt("### Decision\n\n- D1: a\n- R: y\n- D2: b\n- R: z"))
        )
        # A decision with no reason.
        self.assertTrue(any("no reason (R:)" in i for i in fmt("### Decision\n\n- D: only a decision")))

    def test_decision_density_advisory_warns_but_never_errors(self):
        from memory_seed.core import check_session_links

        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        three = (
            "## 2026-06-01 09:00 - Batched\n\n```yaml\nentry_id: ms-aaaaaaaa\n```\n\n"
            "### Decisions\n\n"
            "#### D1 - one\n\n- D: a\n- R: r\n\n"
            "#### D2 - two\n\n- D: b\n- R: r\n\n"
            "#### D3 - three\n\n- D: c\n- R: r\n"
        )
        (sessions / "2026-06-01.md").write_text(three, encoding="utf-8")

        result = check_session_links(cwd=cwd)

        # A well-formed entry can still be worth splitting: advise, never fail.
        self.assertTrue(result.ok)
        self.assertEqual([i.severity for i in result.issues], ["warning"])
        self.assertEqual(result.issues[0].kind, "entry-decision-density")
        self.assertIn("3 decisions", result.issues[0].detail)

    def test_decision_density_advisory_is_quiet_below_the_threshold(self):
        from memory_seed.core import check_session_links

        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        two = (
            "## 2026-06-01 09:00 - One deliberation\n\n```yaml\nentry_id: ms-aaaaaaaa\n```\n\n"
            "### Decisions\n\n"
            "#### D1 - one\n\n- D: a\n- R: r\n\n"
            "#### D2 - two\n\n- D: b\n- R: r\n"
        )
        (sessions / "2026-06-01.md").write_text(two, encoding="utf-8")

        result = check_session_links(cwd=cwd)

        # Two decisions settled together is the sanctioned multi-decision shape.
        self.assertTrue(result.ok)
        self.assertEqual(result.issues, [])

    def test_future_timestamp_advisory_warns_but_never_errors(self):
        from memory_seed.core import check_session_links

        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        future = (
            "## 2126-01-01 09:00 - Stamped a century ahead\n\n"
            "```yaml\nentry_id: ms-aaaaaaaa\n```\n\n"
            "### Decision\n\n- D: a\n- R: r\n"
        )
        (sessions / "2126-01-01.md").write_text(future, encoding="utf-8")

        result = check_session_links(cwd=cwd)

        # A drifted stamp is a smell, never an integrity failure: historical
        # corpora may contain known drifted-but-published entries and
        # append-only forbids restamping them.
        self.assertTrue(result.ok)
        self.assertEqual([i.severity for i in result.issues], ["warning"])
        self.assertEqual(result.issues[0].kind, "entry-future-timestamp")
        self.assertIn("ms-aaaaaaaa", result.issues[0].detail)
        self.assertIn("2126-01-01 09:00", result.issues[0].detail)

    def test_future_timestamp_advisory_grace_window_and_past_are_quiet(self):
        from datetime import datetime, timedelta

        from memory_seed.core import check_entry_timestamp_advisories

        now = datetime(2026, 7, 18, 22, 0)

        def text_at(stamp):
            return (
                f"## {stamp:%Y-%m-%d %H:%M} - Entry\n\n"
                "```yaml\nentry_id: mse_aaaaaaaaaaaaaaaa\n```\n\n"
                "### Summary\n\n- a note\n"
            )

        # Past and present stamps are the normal case.
        self.assertEqual(check_entry_timestamp_advisories(text_at(now - timedelta(hours=2)), now=now), [])
        self.assertEqual(check_entry_timestamp_advisories(text_at(now), now=now), [])
        # Inside (and exactly at) the clock-skew grace window: quiet.
        self.assertEqual(check_entry_timestamp_advisories(text_at(now + timedelta(minutes=10)), now=now), [])
        # Beyond the grace window: flagged, attributed to the entry id.
        flagged = check_entry_timestamp_advisories(text_at(now + timedelta(minutes=11)), now=now)
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0][0], "mse_aaaaaaaaaaaaaaaa")
        self.assertIn("in the future", flagged[0][1])

    def test_future_timestamp_advisory_flags_only_the_drifted_entry(self):
        from datetime import datetime, timedelta

        from memory_seed.core import check_entry_timestamp_advisories

        now = datetime(2026, 7, 18, 22, 0)
        future = now + timedelta(hours=2)
        text = (
            "## 2026-07-18 09:00 - Fine\n\n```yaml\nentry_id: ms-aaaaaaaa\n```\n\n"
            "### Summary\n\n- ok\n\n"
            f"## {future:%Y-%m-%d %H:%M} - Drifted\n\n```yaml\nentry_id: ms-bbbbbbbb\n```\n\n"
            "### Summary\n\n- stamped ahead\n"
        )

        flagged = check_entry_timestamp_advisories(text, now=now)

        self.assertEqual([entry_id for entry_id, _ in flagged], ["ms-bbbbbbbb"])

    def test_decision_density_never_blocks_session_append(self):
        from memory_seed.core import entry_body_advisories, entry_body_format_issues

        body = (
            "### Decisions\n\n"
            "#### D1 - one\n\n- D: a\n- R: r\n\n"
            "#### D2 - two\n\n- D: b\n- R: r\n\n"
            "#### D3 - three\n\n- D: c\n- R: r\n"
        )

        # The write-time gate must stay silent; only the advisory path speaks.
        # session append calls entry_body_format_issues and refuses on any hit.
        self.assertEqual(entry_body_format_issues(body), [])
        self.assertEqual(len(entry_body_advisories(body)), 1)

    def test_decision_count_reads_both_entry_styles(self):
        from memory_seed.core import entry_body_decision_count

        headings = "#### D1 - a\n\n- D: x\n- R: y\n\n#### D2 - b\n\n- D: z\n- R: y\n"
        bullets = "### Decision\n\n- D: only one\n- R: y\n"

        # '#### Dn' subsections win; older '- D:' bullets are the fallback, so
        # the count is not inflated by counting both in the same entry.
        self.assertEqual(entry_body_decision_count(headings), 2)
        self.assertEqual(entry_body_decision_count(bullets), 1)
        self.assertEqual(entry_body_decision_count("### Summary\n\n- just a note\n"), 0)

    def test_links_check_flags_malformed_entry_format(self):
        from memory_seed.core import check_session_links

        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        good = "## 2026-06-01 09:00 - Good\n\n```yaml\nentry_id: ms-aaaaaaaa\n```\n\n### Decision\n\n- D: x\n- R: y\n"
        (sessions / "2026-06-01.md").write_text(good, encoding="utf-8")
        self.assertTrue(check_session_links(cwd=cwd).ok)

        bad = "## 2026-06-02 09:00 - Bad\n\n```yaml\nentry_id: ms-bbbbbbbb\n```\n\nD: bare label\nR: reason\n"
        (sessions / "2026-06-02.md").write_text(bad, encoding="utf-8")
        result = check_session_links(cwd=cwd)
        self.assertFalse(result.ok)
        fmt_issues = [i for i in result.issues if i.kind == "malformed-entry-format"]
        self.assertTrue(fmt_issues)
        self.assertTrue(any("ms-bbbbbbbb" in i.detail for i in fmt_issues))

    def test_the_body_lint_sees_past_a_code_fence_in_the_body(self):
        # Regression: the body used to be split on fences[1], but the metadata
        # opener is '```yaml' and never equals a bare '```', so fences[1] was
        # really the opening fence of a code block in the BODY - everything
        # before it was discarded and the DRAFT lint audited only the tail. Any
        # entry quoting code was therefore exempt from the format check. This
        # entry's violation sits ahead of its code block, so it is only visible
        # if the body is anchored to the metadata closer.
        from memory_seed.core import check_entry_format

        text = (
            "## 2026-06-05 09:00 - Quotes code after a bad DRAFT body\n\n"
            "```yaml\nentry_id: ms-ffffffff\n```\n\n"
            "### Decision\n\n- D: A decision with no reason.\n\n"
            "```\nsome illustrative snippet\n```\n"
        )

        findings = check_entry_format(text)

        self.assertTrue(
            any("R is mandatory" in issue for _, issue in findings),
            "a code fence in the body must not hide the DRAFT lint from the body above it",
        )

    def test_links_check_flags_an_unclosed_metadata_fence(self):
        # The exact shape a bad three-way merge left in the corpus: git anchored
        # on the line-identical `topics:`/`related_entries:` run every entry
        # shares, spliced the first entry's body away and stranded its fence.
        # links check PASSED that file - the ids still regexed out of raw text -
        # and only the fuse's stricter parser objected. This pins the gap.
        from memory_seed.core import check_session_links

        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        corrupted = (
            "## 2026-06-03 11:33 - Stranded by a merge\n\n"
            "```yaml\n"
            "entry_id: ms-cccccccc\n"
            "topics:\n  - memory-trace\n"
            "## 2026-06-03 12:02 - The entry that swallowed it\n\n"
            "```yaml\nentry_id: ms-dddddddd\n```\n\n"
            "### Decision\n\n- D: x\n- R: y\n"
        )
        (sessions / "2026-06-03.md").write_text(corrupted, encoding="utf-8")

        result = check_session_links(cwd=cwd)

        self.assertFalse(result.ok)
        fence_issues = [i for i in result.issues if i.kind == "malformed-entry-yaml"]
        self.assertTrue(fence_issues, "an unclosed metadata fence must be an error")
        self.assertTrue(any("ms-cccccccc" in i.detail for i in fence_issues))
        # The intact entry that followed it is not collateral.
        self.assertFalse(any("ms-dddddddd" in i.detail for i in fence_issues))

    def test_a_yaml_example_in_the_body_is_not_an_unclosed_fence(self):
        # The discriminating case. Entries legitimately quote YAML in their
        # prose, so a fence-balance count across the whole block would flag
        # well-formed history. The check anchors to the FIRST opener after the
        # heading and asks only whether that one closes.
        from memory_seed.core import check_session_links

        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        with_example = (
            "## 2026-06-04 09:00 - Quotes YAML in its body\n\n"
            "```yaml\nentry_id: ms-eeeeeeee\n```\n\n"
            "### Decision\n\n- D: Documented the shape.\n- R: Future readers need it.\n\n"
            "```yaml\ntopics:\n  - example\n```\n"
        )
        (sessions / "2026-06-04.md").write_text(with_example, encoding="utf-8")

        result = check_session_links(cwd=cwd)

        self.assertFalse([i for i in result.issues if i.kind == "malformed-entry-yaml"])

    def test_a_legacy_entry_with_no_metadata_block_is_left_alone(self):
        # The corpus's first two days predate the metadata convention (15 such
        # entries). Append-only forbids retrofitting published history, so their
        # absence of a fence must stay silent rather than red the whole check.
        from memory_seed.core import check_session_links

        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        legacy = "## 2026-05-19 20:35 - Before metadata existed\n\n- Just a note.\n"
        (sessions / "2026-05-19.md").write_text(legacy, encoding="utf-8")

        result = check_session_links(cwd=cwd)

        self.assertFalse([i for i in result.issues if i.kind == "malformed-entry-yaml"])

    # --- A-P3 session integrity validation (memory-seed links check) ---

    def _per_user_session(self, cwd, date, user, *, fm_user=None, fm_date=None,
                          schema="2", hash_id=None, entries=("ms-aaaaaaaa",), extra_fm=""):
        d = cwd / MEMORY_DIR_NAME / "sessions" / date
        d.mkdir(parents=True, exist_ok=True)
        fm = ["---", f"schema_version: {schema}", f"session_date: {fm_date or date}"]
        if hash_id is not None:
            fm.append(f"hash_id: {hash_id}")
        fm += [f"user: {fm_user or user}", "created_at: 2026-06-13T00:00:00Z"]
        if extra_fm:
            fm.append(extra_fm)
        fm.append("---")
        body = []
        for eid in entries:
            body += ["", f"## {date} 09:00 - entry", "", "```yaml", f"entry_id: {eid}", "```", "", "- note"]
        (d / f"{user}.md").write_text("\n".join(fm + body) + "\n", encoding="utf-8")

    def test_links_check_clean_per_user_repo_is_ok(self):
        cwd = self.make_project()
        self._per_user_session(cwd, "2026-06-13", "jean", hash_id="msm_" + "a" * 32, entries=("ms-11111111",))
        self._per_user_session(cwd, "2026-06-13", "amina", hash_id="msm_" + "b" * 32, entries=("ms-22222222",))

        result = check_session_links(cwd=cwd)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])
        self.assertEqual(result.files_checked, 2)

    def test_links_check_detects_duplicate_entry_id(self):
        cwd = self.make_project()
        self._per_user_session(cwd, "2026-06-13", "jean", hash_id="msm_" + "a" * 32, entries=("ms-deadbeef",))
        self._per_user_session(cwd, "2026-06-13", "amina", hash_id="msm_" + "b" * 32, entries=("ms-deadbeef",))

        result = check_session_links(cwd=cwd)

        self.assertFalse(result.ok)
        self.assertTrue(any(i.kind == "duplicate-entry-id" and "ms-deadbeef" in i.detail for i in result.issues))

    def test_links_check_detects_frontmatter_user_and_date_mismatch(self):
        cwd = self.make_project()
        self._per_user_session(cwd, "2026-06-13", "jean", fm_user="bob", fm_date="2026-06-14",
                               hash_id="msm_" + "a" * 32, entries=("ms-33333333",))

        kinds = {i.kind for i in check_session_links(cwd=cwd).issues}

        self.assertIn("user-mismatch", kinds)
        self.assertIn("date-mismatch", kinds)

    def test_links_check_detects_bad_schema_and_missing_hash(self):
        cwd = self.make_project()
        self._per_user_session(cwd, "2026-06-13", "jean", schema="9", hash_id=None, entries=("ms-44444444",))

        kinds = {i.kind for i in check_session_links(cwd=cwd).issues}

        self.assertIn("unsupported-schema-version", kinds)
        self.assertIn("missing-hash-id", kinds)

    def test_links_check_detects_duplicate_hash_id(self):
        cwd = self.make_project()
        self._per_user_session(cwd, "2026-06-13", "jean", hash_id="msm_" + "c" * 32, entries=("ms-55555555",))
        self._per_user_session(cwd, "2026-06-14", "jean", hash_id="msm_" + "c" * 32, entries=("ms-66666666",))

        kinds = {i.kind for i in check_session_links(cwd=cwd).issues}

        self.assertIn("duplicate-hash-id", kinds)

    def test_links_check_detects_dangling_related_refs(self):
        cwd = self.make_project()
        self._per_user_session(
            cwd, "2026-06-13", "jean", hash_id="msm_" + "a" * 32, entries=("ms-77777777",),
            extra_fm="related_entries:\n  - ms-99999999\nrelated_memories:\n  - msm_" + "f" * 32,
        )

        kinds = {i.kind for i in check_session_links(cwd=cwd).issues}

        self.assertIn("dangling-related-entry", kinds)
        self.assertIn("dangling-related-memory", kinds)

    def test_links_check_resolves_valid_related_refs(self):
        cwd = self.make_project()
        # jean references amina's entry + file hash, both of which exist.
        self._per_user_session(cwd, "2026-06-13", "amina", hash_id="msm_" + "b" * 32, entries=("ms-88888888",))
        self._per_user_session(
            cwd, "2026-06-13", "jean", hash_id="msm_" + "a" * 32, entries=("ms-77777777",),
            extra_fm="related_entries:\n  - ms-88888888\nrelated_memories:\n  - msm_" + "b" * 32,
        )

        result = check_session_links(cwd=cwd)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])

    def test_links_check_validates_entry_level_related_entries_for_old_and_new_ids(self):
        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions" / "2026-06-13"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "jean.md").write_text(
            "\n".join(
                [
                    "---",
                    "schema_version: 2",
                    "session_date: 2026-06-13",
                    "hash_id: msm_" + "a" * 32,
                    "user: jean",
                    "created_at: 2026-06-13T00:00:00Z",
                    "---",
                    "",
                    "## 2026-06-13 09:00 - first",
                    "",
                    "```yaml",
                    "entry_id: mse_0123456789abcdef",
                    "related_entries:",
                    "  - ms-88888888",
                    "```",
                    "",
                    "- note",
                    "",
                    "## 2026-06-13 10:00 - second",
                    "",
                    "```yaml",
                    "entry_id: ms-88888888",
                    "related_entries:",
                    "  - mse_ffffffffffffffff",
                    "```",
                    "",
                    "- note",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual(
            [issue.kind for issue in issues],
            ["dangling-related-entry"],
            [issue.__dict__ for issue in issues],
        )
        self.assertIn("mse_ffffffffffffffff", issues[0].detail)

    def test_links_check_validates_entry_level_related_entries_in_legacy_flat_files(self):
        # Regression test: entry-level related_entries used to only be scanned
        # for per-user-day files, silently skipping legacy-flat sessions/*.md
        # (this repo's own layout) - a dangling ref there passed with ok=True.
        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-06-13.md").write_text(
            "\n".join(
                [
                    "---",
                    "tags: [session-log]",
                    "session_date: 2026-06-13",
                    "---",
                    "",
                    "## 2026-06-13 09:00 - flat entry",
                    "",
                    "```yaml",
                    "entry_id: mse_0123456789abcdef",
                    "user_initials: JN",
                    "related_entries:",
                    "  - mse_ffffffffffffffff",
                    "```",
                    "",
                    "- note",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual(
            [issue.kind for issue in issues],
            ["dangling-related-entry"],
            [issue.__dict__ for issue in issues],
        )
        self.assertIn("mse_ffffffffffffffff", issues[0].detail)

    def test_links_check_resolves_valid_related_entries_in_legacy_flat_files(self):
        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-06-13.md").write_text(
            "\n".join(
                [
                    "## 2026-06-13 09:00 - first",
                    "",
                    "```yaml",
                    "entry_id: mse_0123456789abcdef",
                    "```",
                    "",
                    "## 2026-06-13 10:00 - second",
                    "",
                    "```yaml",
                    "entry_id: mse_ffffffffffffffff",
                    "related_entries:",
                    "  - mse_0123456789abcdef",
                    "```",
                    "",
                    "- note",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        result = check_session_links(cwd=cwd)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])

    def _flat_session(self, cwd, filename, *entry_specs):
        """Write a flat session file from (heading, entry_id, supersedes) specs."""
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        for heading, entry_id, supersedes in entry_specs:
            lines += [f"## {heading}", "", "```yaml", f"entry_id: {entry_id}"]
            if supersedes:
                lines.append("supersedes:")
                lines.extend(f"  - {ref}" for ref in supersedes)
            lines += ["```", "", "- note", ""]
        (sessions / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_links_check_accepts_backward_supersedes(self):
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - original", "mse_0123456789abcdef", ()),
            ("2026-06-13 10:00 - replacement", "mse_ffffffffffffffff", ("mse_0123456789abcdef",)),
        )

        result = check_session_links(cwd=cwd)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])

    def test_links_check_flags_dangling_supersedes(self):
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - only", "mse_0123456789abcdef", ("mse_zzzzzzzzzzzzzzzz",)),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["dangling-supersedes"], [i.__dict__ for i in issues])
        self.assertIn("mse_zzzzzzzzzzzzzzzz", issues[0].detail)

    def test_links_check_flags_postdating_supersedes(self):
        # Forward-only guard: an earlier entry may not supersede a later one.
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - earlier", "mse_0123456789abcdef", ("mse_ffffffffffffffff",)),
            ("2026-06-13 10:00 - later", "mse_ffffffffffffffff", ()),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["supersedes-postdates"], [i.__dict__ for i in issues])
        self.assertIn("mse_ffffffffffffffff", issues[0].detail)

    def test_links_check_flags_self_supersedes(self):
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - self", "mse_0123456789abcdef", ("mse_0123456789abcdef",)),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["self-supersedes"], [i.__dict__ for i in issues])

    def test_links_check_guards_non_crockford_entry_yaml_refs(self):
        # Regression: real corpus ids include o/u/i/l (outside the strict
        # Crockford charset), e.g. codex-authored entries. A ref to one used to
        # be silently skipped by the extractor - bypassing the dangling and
        # forward-only guards while the graph still drew the edge.
        loose = "mse_37fpcovvuniqzlxk"  # contains o, u, i, l
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - earlier", "mse_0123456789abcdef", (loose,)),
            (f"2026-06-13 10:00 - later", loose, ()),
        )

        issues = check_session_links(cwd=cwd).issues

        # The earlier entry supersedes the LATER loose-id entry: the forward-only
        # guard must now see and reject it instead of silently passing.
        self.assertEqual([i.kind for i in issues], ["supersedes-postdates"], [i.__dict__ for i in issues])
        self.assertIn(loose, issues[0].detail)

    def test_links_check_flags_dangling_ref_to_non_crockford_id(self):
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - only", "mse_0123456789abcdef", ("mse_gonevvuniqzlxkoo",)),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["dangling-supersedes"], [i.__dict__ for i in issues])

    def test_cli_session_entry_id_reproduces_canonical_id(self):
        import contextlib
        import io
        import sys as _sys
        from unittest import mock as _mock

        from memory_seed.cli import main as cli_main

        argv = [
            "memory-seed", "session", "entry-id",
            "--timestamp", "2026-07-12 12:15",
            "--title", "Fuse Codex branches and align Trace packaging docs",
            "--user-initials", "JNL",
            "--agent-type", "codex",
        ]
        buffer = io.StringIO()
        with _mock.patch.object(_sys, "argv", argv), contextlib.redirect_stdout(buffer):
            exit_code = cli_main()

        self.assertEqual(exit_code, 0)
        # Deterministic: this metadata tuple reproduces a real corpus id.
        self.assertEqual(buffer.getvalue().strip(), "mse_kq3ba0cy9nkpqkm0")

    # --- Link sidecars: late-authored lifecycle edges join the same checks ---

    def _link_sidecar(
        self,
        cwd,
        file_date,
        source_entry,
        *,
        supersedes=(),
        evolves=(),
        classify_pending=False,
        heading_time="10:00",
    ):
        """Write a link sidecar block keyed to ``source_entry`` under
        sessions/links/<month>/<file_date>.md."""
        d = cwd / MEMORY_DIR_NAME / "sessions" / "links" / file_date[:7]
        d.mkdir(parents=True, exist_ok=True)
        lines = [f"## {file_date} {heading_time} - edge", "", "```yaml", f"entry_id: {source_entry}"]
        if classify_pending:
            lines.append("classify_pending: true")
        for key, refs in (("supersedes", supersedes), ("evolves", evolves)):
            if refs:
                lines.append(f"{key}:")
                lines.extend(f"  - {ref}" for ref in refs)
        lines += ["```", ""]
        (d / f"{file_date}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_links_check_accepts_backward_supersedes_in_sidecar(self):
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - original", "mse_0123456789abcdef", ()),
            ("2026-06-13 10:00 - replacement", "mse_ffffffffffffffff", ()),
        )
        self._link_sidecar(cwd, "2026-06-13", "mse_ffffffffffffffff", supersedes=("mse_0123456789abcdef",))

        result = check_session_links(cwd=cwd)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])

    def test_links_check_reports_unclassified_sidecar_stub_as_warning(self):
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 10:00 - pending classification", "mse_ffffffffffffffff", ()),
        )
        self._link_sidecar(
            cwd,
            "2026-06-13",
            "mse_ffffffffffffffff",
            classify_pending=True,
        )
        diagram = cwd / MEMORY_DIR_NAME / "sessions" / "diagrams" / "2026-06" / "2026-06-13.md"
        diagram.parent.mkdir(parents=True)
        diagram.write_text(
            "\n".join(
                [
                    "## 2026-06-13 10:00 - unrelated diagram metadata",
                    "",
                    "```yaml",
                    "entry_id: mse_ffffffffffffffff",
                    "classify_pending: true",
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

        result = check_session_links(cwd=cwd)

        pending = [issue for issue in result.issues if issue.kind == "sidecar-unclassified-stub"]
        self.assertTrue(result.ok)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].severity, "warning")
        self.assertIn("/sessions/links/", pending[0].file)

        import contextlib
        import io
        import os

        from memory_seed.cli import main as cli_main

        stdout = io.StringIO()
        stderr = io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(cwd)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = cli_main(["links", "check"])
        finally:
            os.chdir(previous)
        self.assertEqual(exit_code, 0)
        self.assertIn("[warning] [sidecar-unclassified-stub]", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_links_check_accepts_backward_evolves_in_sidecar(self):
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - base", "mse_0123456789abcdef", ()),
            ("2026-06-13 10:00 - refinement", "mse_ffffffffffffffff", ()),
        )
        self._link_sidecar(cwd, "2026-06-13", "mse_ffffffffffffffff", evolves=("mse_0123456789abcdef",))

        self.assertTrue(check_session_links(cwd=cwd).ok)

    def test_links_check_flags_dangling_supersedes_in_sidecar(self):
        cwd = self.make_project()
        self._flat_session(cwd, "2026-06-13.md", ("2026-06-13 10:00 - only", "mse_ffffffffffffffff", ()))
        self._link_sidecar(cwd, "2026-06-13", "mse_ffffffffffffffff", supersedes=("mse_zzzzzzzzzzzzzzzz",))

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["dangling-supersedes"], [i.__dict__ for i in issues])

    def test_links_check_flags_postdating_supersedes_in_sidecar(self):
        # Forward-only guard covers sidecar edges too, attributed to the SOURCE
        # entry's timestamp: an earlier entry may not supersede a later one.
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - earlier", "mse_0123456789abcdef", ()),
            ("2026-06-13 10:00 - later", "mse_ffffffffffffffff", ()),
        )
        self._link_sidecar(cwd, "2026-06-13", "mse_0123456789abcdef", supersedes=("mse_ffffffffffffffff",))

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["supersedes-postdates"], [i.__dict__ for i in issues])

    def test_links_check_flags_orphan_link_sidecar(self):
        cwd = self.make_project()
        self._flat_session(cwd, "2026-06-13.md", ("2026-06-13 09:00 - only", "mse_0123456789abcdef", ()))
        self._link_sidecar(cwd, "2026-06-13", "mse_ffffffffffffffff", supersedes=("mse_0123456789abcdef",))

        kinds = [i.kind for i in check_session_links(cwd=cwd).issues]

        self.assertIn("orphan-link-sidecar", kinds)

    def test_links_check_flags_link_sidecar_date_mismatch(self):
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - original", "mse_0123456789abcdef", ()),
            ("2026-06-13 10:00 - replacement", "mse_ffffffffffffffff", ()),
        )
        # Source entry logged 2026-06-13, block filed under 2026-06-14.
        self._link_sidecar(cwd, "2026-06-14", "mse_ffffffffffffffff", supersedes=("mse_0123456789abcdef",))

        kinds = [i.kind for i in check_session_links(cwd=cwd).issues]

        self.assertIn("link-sidecar-date-mismatch", kinds)

    def test_links_check_flags_malformed_link_sidecar(self):
        cwd = self.make_project()
        self._flat_session(cwd, "2026-06-13.md", ("2026-06-13 09:00 - only", "mse_0123456789abcdef", ()))
        links = cwd / MEMORY_DIR_NAME / "sessions" / "links" / "2026-06"
        links.mkdir(parents=True, exist_ok=True)
        (links / "not-a-date.md").write_text("## whatever\n", encoding="utf-8")

        kinds = [i.kind for i in check_session_links(cwd=cwd).issues]

        self.assertIn("malformed-link-sidecar", kinds)

    def test_link_show_reflects_sidecar_edges(self):
        """`link show` must union late-authored link-sidecar edges into the
        effective graph (computed inverse included), matching what
        retrieval/MCP/Trace read - not just the raw entry-YAML edges."""
        import contextlib
        import io
        import os
        import sys as _sys
        from unittest import mock as _mock

        from memory_seed.cli import main as cli_main

        cwd = self.make_project()
        base = "mse_0123456789abcdef"
        refinement = "mse_ffffffffffffffff"
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - base", base, ()),
            ("2026-06-13 10:00 - refinement", refinement, ()),
        )
        # Recorded ONLY in a link sidecar (not in either entry's YAML).
        self._link_sidecar(cwd, "2026-06-13", refinement, evolves=(base,))

        def run(entry_id):
            buffer = io.StringIO()
            prev = os.getcwd()
            os.chdir(cwd)  # the link handler resolves cwd from Path(".")
            try:
                with _mock.patch.object(_sys, "argv", ["memory-seed", "link", "show", entry_id]), \
                        contextlib.redirect_stdout(buffer):
                    code = cli_main()
            finally:
                os.chdir(prev)
            return code, buffer.getvalue()

        code_ref, out_ref = run(refinement)
        code_base, out_base = run(base)

        self.assertEqual(code_ref, 0, out_ref)
        self.assertEqual(code_base, 0, out_base)
        # The sidecar evolves edge is visible from both ends of the graph.
        self.assertIn(f"evolves (1): {base}", out_ref)
        self.assertIn(f"evolved_by (1): {refinement}", out_base)

    def _flat_session_raw(self, cwd, filename, text):
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / filename).write_text(text, encoding="utf-8")

    def _entry_yaml(self, heading, entry_id, *yaml_lines):
        lines = [f"## {heading}", "", "```yaml", f"entry_id: {entry_id}", *yaml_lines, "```", "", "- note", ""]
        return "\n".join(lines)

    def test_links_check_accepts_backward_evolves(self):
        cwd = self.make_project()
        self._flat_session_raw(
            cwd,
            "2026-06-13.md",
            self._entry_yaml("2026-06-13 09:00 - original", "mse_0123456789abcdef")
            + self._entry_yaml(
                "2026-06-13 10:00 - refinement", "mse_ffffffffffffffff", "evolves:", "  - mse_0123456789abcdef"
            ),
        )

        result = check_session_links(cwd=cwd)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])

    def test_links_check_flags_dangling_evolves(self):
        cwd = self.make_project()
        self._flat_session_raw(
            cwd,
            "2026-06-13.md",
            self._entry_yaml("2026-06-13 09:00 - only", "mse_0123456789abcdef", "evolves:", "  - mse_zzzzzzzzzzzzzzzz"),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["dangling-evolves"], [i.__dict__ for i in issues])
        self.assertIn("mse_zzzzzzzzzzzzzzzz", issues[0].detail)

    def test_links_check_flags_postdating_evolves(self):
        cwd = self.make_project()
        self._flat_session_raw(
            cwd,
            "2026-06-13.md",
            self._entry_yaml("2026-06-13 09:00 - earlier", "mse_0123456789abcdef", "evolves:", "  - mse_ffffffffffffffff")
            + self._entry_yaml("2026-06-13 10:00 - later", "mse_ffffffffffffffff"),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["evolves-postdates"], [i.__dict__ for i in issues])

    def test_links_check_flags_self_evolves(self):
        cwd = self.make_project()
        self._flat_session_raw(
            cwd,
            "2026-06-13.md",
            self._entry_yaml("2026-06-13 09:00 - self", "mse_0123456789abcdef", "evolves:", "  - mse_0123456789abcdef"),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["self-evolves"], [i.__dict__ for i in issues])

    def test_links_check_flags_evolves_cycle_between_same_minute_entries(self):
        # Same-minute entries defeat the postdates ordering, so the DFS cycle
        # guard has to catch a mutual evolves pair - within the evolves kind
        # only, never mixed with supersedes edges.
        cwd = self.make_project()
        self._flat_session_raw(
            cwd,
            "2026-06-13.md",
            self._entry_yaml("2026-06-13 09:00 - a", "mse_aaaaaaaaaaaaaaaa", "evolves:", "  - mse_bbbbbbbbbbbbbbbb")
            + self._entry_yaml("2026-06-13 09:00 - b", "mse_bbbbbbbbbbbbbbbb", "evolves:", "  - mse_aaaaaaaaaaaaaaaa"),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertIn("evolves-cycle", [i.kind for i in issues], [i.__dict__ for i in issues])
        cycle_issue = next(i for i in issues if i.kind == "evolves-cycle")
        self.assertIn("evolution cycle", cycle_issue.detail)

    def test_links_check_flags_authored_inverse_fields(self):
        # Append-only enforcement: the computed inverses live only in the
        # derived read layer; a stored key is a named integrity error, not a
        # silently ignored no-op.
        cwd = self.make_project()
        self._flat_session_raw(
            cwd,
            "2026-06-13.md",
            self._entry_yaml("2026-06-13 09:00 - a", "mse_0123456789abcdef", "evolved_by:", "  - mse_ffffffffffffffff")
            + self._entry_yaml("2026-06-13 10:00 - b", "mse_ffffffffffffffff", "superseded_by:", "  - mse_0123456789abcdef"),
        )

        issues = check_session_links(cwd=cwd).issues

        kinds = [i.kind for i in issues]
        self.assertEqual(kinds.count("authored-inverse-field"), 2, [i.__dict__ for i in issues])
        details = " ".join(i.detail for i in issues if i.kind == "authored-inverse-field")
        self.assertIn("evolved_by", details)
        self.assertIn("superseded_by", details)

    def test_links_check_accepts_valid_continuity_blocks(self):
        cwd = self.make_project()
        self._flat_session_raw(
            cwd,
            "2026-06-13.md",
            self._entry_yaml(
                "2026-06-13 09:00 - lineage", "mse_0123456789abcdef",
                "continuity:",
                "  - kind: rename",
                "    from: memory_seed/lense.py",
                "    to: memory_trace/lense.py",
                "  - kind: migration",
                "    from: .AGENTS/",
                "    to: .memory-seed/",
                "  - kind: removal",
                "    from: memory-seed lense command",
            ),
        )

        result = check_session_links(cwd=cwd)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])

    def test_links_check_flags_every_malformed_continuity_shape(self):
        cwd = self.make_project()
        self._flat_session_raw(
            cwd,
            "2026-06-13.md",
            self._entry_yaml(
                "2026-06-13 09:00 - lineage", "mse_0123456789abcdef",
                "continuity:",
                "  - kind: refactor",           # unknown kind
                "    from: a",
                "  - kind: rename",             # rename without to
                "    from: b",
                "  - kind: removal",            # removal with to
                "    from: c",
                "    to: d",
                "  - kind: migration",          # missing from
                "    to: e",
            ),
        )

        issues = check_session_links(cwd=cwd).issues

        kinds = [i.kind for i in issues]
        self.assertEqual(kinds.count("malformed-continuity"), 4, [i.__dict__ for i in issues])
        details = " ".join(i.detail for i in issues)
        self.assertIn("refactor", details)
        self.assertIn("has no to", details)
        self.assertIn("must not have to", details)
        self.assertIn("has no from", details)

    def _flat_session_with_commits(self, cwd, *hashes):
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        lines = ["## 2026-06-13 09:00 - entry", "", "```yaml", "entry_id: mse_0123456789abcdef", "commits:"]
        lines.extend(f"  - {h}" for h in hashes)
        lines += ["```", "", "- note", ""]
        (sessions / "2026-06-13.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _git_repo_with_commit(self, cwd, message="initial"):
        import subprocess

        subprocess.run(["git", "-C", str(cwd), "init", "-q"], check=True, capture_output=True)
        (cwd / "README.txt").write_text("x", encoding="utf-8")
        subprocess.run(["git", "-C", str(cwd), "add", "-A"], check=True, capture_output=True)
        subprocess.run(
            [
                "git", "-C", str(cwd),
                "-c", "user.name=test", "-c", "user.email=test@example.com",
                "-c", "commit.gpgsign=false",
                "commit", "-q", "-m", message,
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(["git", "-C", str(cwd), "branch", "-M", "main"], check=True, capture_output=True)
        head = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
        return head

    def test_links_check_flags_malformed_commit_hash_without_git(self):
        # Format validation applies even outside a git repo; existence is skipped.
        cwd = self.make_project()
        self._flat_session_with_commits(cwd, "abc123")

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["malformed-commit-hash"], [i.__dict__ for i in issues])
        self.assertIn("abc123", issues[0].detail)

    def test_links_check_skips_commit_existence_without_git(self):
        cwd = self.make_project()
        self._flat_session_with_commits(cwd, "a" * 40)

        result = check_session_links(cwd=cwd)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])

    def test_links_check_validates_commit_existence_in_git_repo(self):
        cwd = self.make_project()
        head = self._git_repo_with_commit(cwd)
        self._flat_session_with_commits(cwd, head, "f" * 40)

        issues = check_session_links(cwd=cwd).issues

        # The real HEAD passes; the fabricated hash is flagged.
        self.assertEqual([i.kind for i in issues], ["unknown-commit"], [i.__dict__ for i in issues])
        self.assertIn("f" * 40, issues[0].detail)

    def test_links_check_skips_commit_existence_in_shallow_clone(self):
        import subprocess

        cwd = self.make_project()
        self._git_repo_with_commit(cwd)
        # A shallow clone (what CI checkouts default to) genuinely lacks
        # historical commits: "no such commit" is indistinguishable from
        # "outside the fetched window", so unknown-commit must not fire.
        shallow = Path(tempfile.mkdtemp(prefix="mseed-shallow-"))
        self.addCleanup(lambda: shutil.rmtree(shallow, ignore_errors=True))
        subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1",
             cwd.as_uri().replace("file:///", "file:///"), str(shallow / "clone")],
            check=True, capture_output=True, timeout=60,
        )
        clone = shallow / "clone"
        self._flat_session_with_commits(clone, "f" * 40)

        result = check_session_links(cwd=clone)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])

    def test_find_trailer_commits_scans_memory_entry_trailer(self):
        from memory_seed.core import find_trailer_commits

        cwd = self.make_project()
        head = self._git_repo_with_commit(cwd, message="fix thing\n\nMemory-Entry: mse_0123456789abcdef")

        hits = find_trailer_commits(cwd, "mse_0123456789abcdef")
        misses = find_trailer_commits(cwd, "mse_ffffffffffffffff")

        self.assertEqual(len(hits), 1, hits)
        self.assertTrue(hits[0].startswith(head))
        self.assertEqual(misses, [])

    def test_find_trailer_commits_returns_none_outside_git(self):
        from memory_seed.core import find_trailer_commits

        cwd = self.make_project()

        self.assertIsNone(find_trailer_commits(cwd, "mse_0123456789abcdef"))

    def test_commit_reference_ids_unions_field_and_trailer_deduped(self):
        from memory_seed.core import commit_reference_ids

        cwd = self.make_project()
        head = self._git_repo_with_commit(
            cwd, message="do thing\n\nMemory-Entry: mse_0123456789abcdef"
        )
        # The field lists the trailered HEAD (dedup case) plus one other SHA.
        ids = commit_reference_ids(cwd, "mse_0123456789abcdef", (head, "b" * 40))

        # HEAD appears in both the field and the trailer scan but counts once.
        self.assertEqual(ids, {head, "b" * 40})

    def test_commit_reference_ids_field_only_outside_git(self):
        from memory_seed.core import commit_reference_ids

        cwd = self.make_project()  # no .git
        ids = commit_reference_ids(cwd, "mse_0123456789abcdef", ("a" * 40, "notasha"))

        # Trailer scan skips (no git); only the well-formed field SHA survives.
        self.assertEqual(ids, {"a" * 40})

    def test_branch_status_warns_on_dirty_main(self):
        from memory_seed.core import branch_status

        cwd = self.make_project()
        self._git_repo_with_commit(cwd)
        (cwd / "README.txt").write_text("changed", encoding="utf-8")

        status = branch_status(cwd=cwd)

        self.assertTrue(status.is_git_repo)
        self.assertEqual(status.branch, "main")
        self.assertTrue(status.is_integration_branch)
        self.assertTrue(status.dirty)
        self.assertTrue(any("task branch" in warning for warning in status.warnings))
        self.assertIn("--no-ff", status.recommendation)

    def test_branch_status_recognizes_feature_branch(self):
        import subprocess
        from memory_seed.core import branch_status

        cwd = self.make_project()
        self._git_repo_with_commit(cwd)
        subprocess.run(
            ["git", "-C", str(cwd), "switch", "-c", "feature-topic"],
            check=True,
            capture_output=True,
        )

        status = branch_status(cwd=cwd)

        self.assertTrue(status.is_git_repo)
        self.assertEqual(status.branch, "feature-topic")
        self.assertFalse(status.is_integration_branch)
        self.assertFalse(status.dirty)
        self.assertIn("merge --no-ff", status.recommendation)

    def test_branch_status_handles_non_git_directory(self):
        from memory_seed.core import branch_status

        cwd = self.make_project()

        status = branch_status(cwd=cwd)

        self.assertFalse(status.is_git_repo)
        self.assertIn("Not a Git repository", status.recommendation)

    def test_worktree_guard_passes_owned_and_blocks_foreign_namespace(self):
        import subprocess
        from memory_seed.core import worktree_guard

        cwd = self.make_project()
        memory = cwd / MEMORY_DIR_NAME
        memory.mkdir()
        (memory / "project.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "worktrees:",
                    "  namespaces:",
                    "    codex: .CODEX/WORKTREES",
                    "    claude: .claude/worktrees",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        self._git_repo_with_commit(cwd)
        codex_wt = cwd / ".codex" / "worktrees" / "task with spaces"
        claude_wt = cwd / ".claude" / "worktrees" / "task"
        codex_wt.parent.mkdir(parents=True)
        claude_wt.parent.mkdir(parents=True)
        subprocess.run(
            ["git", "-C", str(cwd), "worktree", "add", "-q", "-b", "codex/task", str(codex_wt)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(cwd), "worktree", "add", "-q", "-b", "claude/task", str(claude_wt)],
            check=True,
            capture_output=True,
        )

        owned = worktree_guard(cwd=codex_wt, agent_type="Codex", write_intent=True)
        foreign = worktree_guard(cwd=claude_wt, agent_type="codex", write_intent=True)

        self.assertTrue(owned.ok, owned)
        self.assertEqual(owned.classification, "owned-worktree")
        self.assertTrue(owned.safe_to_write)
        self.assertEqual(owned.actual_namespace_owner, "codex")
        self.assertFalse(foreign.ok)
        self.assertEqual(foreign.classification, "foreign-worktree")
        self.assertFalse(foreign.safe_to_write)
        self.assertEqual(foreign.actual_namespace_owner, "claude")

    def test_worktree_guard_root_checkout_requires_explicit_override_for_writes(self):
        from memory_seed.core import worktree_guard

        cwd = self.make_project()
        self._git_repo_with_commit(cwd)

        read_only = worktree_guard(cwd=cwd, agent_type="codex")
        blocked = worktree_guard(cwd=cwd, agent_type="codex", write_intent=True)
        allowed = worktree_guard(cwd=cwd, agent_type="codex", write_intent=True, allow_root_write=True)

        self.assertTrue(read_only.ok)
        self.assertEqual(read_only.classification, "root-checkout")
        self.assertFalse(blocked.ok)
        self.assertEqual(blocked.severity, "block")
        self.assertTrue(allowed.ok)
        self.assertEqual(allowed.classification, "root-checkout")

    def test_worktree_guard_unmanaged_write_policy_can_block(self):
        import subprocess
        from memory_seed.core import worktree_guard

        cwd = self.make_project()
        memory = cwd / MEMORY_DIR_NAME
        memory.mkdir()
        (memory / "project.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "worktrees:",
                    "  unmanaged_write_policy: block",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        self._git_repo_with_commit(cwd)
        unmanaged = cwd / "scratch worktrees" / "task"
        unmanaged.parent.mkdir(parents=True)
        subprocess.run(
            ["git", "-C", str(cwd), "worktree", "add", "-q", "-b", "scratch/task", str(unmanaged)],
            check=True,
            capture_output=True,
        )

        status = worktree_guard(cwd=unmanaged, agent_type="codex", write_intent=True)

        self.assertFalse(status.ok)
        self.assertEqual(status.classification, "unmanaged-worktree")
        self.assertEqual(status.severity, "block")

    def test_worktree_guard_uses_project_namespace_overrides(self):
        import subprocess
        from memory_seed.core import worktree_guard

        cwd = self.make_project()
        memory = cwd / MEMORY_DIR_NAME
        memory.mkdir()
        (memory / "project.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "worktrees:",
                    "  namespaces:",
                    "    codex: custom spaces/codex",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        self._git_repo_with_commit(cwd)
        custom = cwd / "custom spaces" / "codex" / "task"
        custom.parent.mkdir(parents=True)
        subprocess.run(
            ["git", "-C", str(cwd), "worktree", "add", "-q", "-b", "codex/custom-task", str(custom)],
            check=True,
            capture_output=True,
        )

        status = worktree_guard(cwd=custom, agent_type="codex", write_intent=True)

        self.assertTrue(status.ok, status)
        self.assertEqual(status.classification, "owned-worktree")
        self.assertEqual(status.expected_namespace, "custom spaces/codex")

    def test_links_check_flags_supersedes_cycle_between_same_minute_entries(self):
        # Same-minute entries slip past the postdates comparison; the DFS
        # cycle guard is what catches a mutual supersession there.
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - first", "mse_0123456789abcdef", ("mse_ffffffffffffffff",)),
            ("2026-06-13 09:00 - second", "mse_ffffffffffffffff", ("mse_0123456789abcdef",)),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertIn("supersedes-cycle", [i.kind for i in issues], [i.__dict__ for i in issues])
        cycle_issue = next(i for i in issues if i.kind == "supersedes-cycle")
        self.assertIn("mse_0123456789abcdef", cycle_issue.detail)
        self.assertIn("mse_ffffffffffffffff", cycle_issue.detail)

    def test_doctor_summarizes_session_integrity_issues(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        self._per_user_session(cwd, "2026-06-13", "jean", fm_user="bob", hash_id="msm_" + "a" * 32, entries=("ms-12121212",))

        result = doctor(cwd=cwd)

        self.assertTrue(any("integrity issue" in w for w in result.warnings))
        self.assertTrue(result.control_plane_ok)  # non-fatal

    def test_doctor_summarizes_encoding_and_static_text_io_issues(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        (cwd / "bad.md").write_bytes(b"alpha\r\n")
        package = cwd / "package"
        package.mkdir()
        (package / "bad.py").write_bytes(b"open('notes.md')\n")

        result = doctor(cwd=cwd)

        warning = next(w for w in result.warnings if "encoding issue" in w)
        self.assertIn("2 encoding issue(s)", warning)
        self.assertIn("memory-seed encoding check", warning)
        self.assertTrue(result.control_plane_ok)

    def test_version_at_least_orders_versions_numerically(self):
        from memory_seed.core import _version_at_least

        self.assertTrue(_version_at_least("2.2", "2.2"))   # equal
        self.assertTrue(_version_at_least("2.3", "2.2"))   # newer
        self.assertTrue(_version_at_least("2.10", "2.9"))  # multi-digit, not string compare
        self.assertFalse(_version_at_least("2.1", "2.2"))  # older
        self.assertFalse(_version_at_least(None, "2.2"))   # missing -> treat as older
        self.assertFalse(_version_at_least("garbage", "2.2"))  # unparseable -> older

    def test_init_dry_run_reports_seed_files_without_writing(self):
        cwd = self.make_project()

        result = init_project(cwd=cwd, dry_run=True)

        self.assertFalse(result.changed)
        self.assertEqual(result.created, [])
        expected = [
            seed_file.destination
            for seed_file in SEED_FILES
            if not seed_file.destination.startswith(".memory-seed/skills/")
            or Path(seed_file.destination).name in set(CORE_SKILL_NAMES) | {"index.md"}
        ]
        self.assertEqual(
            sorted(result.planned),
            sorted(expected),
        )
        self.assertFalse((cwd / "AGENTS.md").exists())
        self.assertFalse((cwd / ".memory-seed").exists())

    def test_init_dry_run_does_not_require_force_when_files_exist(self):
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text("existing", encoding="utf-8")

        result = init_project(cwd=cwd, dry_run=True)

        self.assertFalse(result.changed)
        self.assertEqual((cwd / "AGENTS.md").read_text(encoding="utf-8"), "existing")

    def test_init_writes_only_reusable_seed_files(self):
        cwd = self.make_project()

        result = init_project(cwd=cwd)

        self.assertTrue(result.changed)
        for seed_file in SEED_FILES:
            if (
                seed_file.destination.startswith(".memory-seed/skills/")
                and Path(seed_file.destination).name in OPTIONAL_SKILL_NAMES
            ):
                continue
            self.assertTrue(
                (cwd / seed_file.destination).exists(),
                f"{seed_file.destination} should exist",
            )
        self.assertFalse((cwd / ".memory-seed" / "index.md").exists())
        self.assertFalse((cwd / ".memory-seed" / "policy.md").exists())
        self.assertTrue((cwd / ".memory-seed" / "agent-rules.md").exists())
        self.assertTrue((cwd / ".memory-seed" / "project-bootstrap.md").exists())
        self.assertTrue((cwd / ".memory-seed" / "skills").is_dir())
        self.assertTrue((cwd / ".memory-seed" / "sessions").is_dir())
        self.assertTrue((cwd / ".memory-seed" / "archive").is_dir())
        # .AGENTS is the legacy directory. On case-insensitive filesystems (Windows),
        # it resolves to the same path as our new .agents/ folder. Verify via resolve_runtime
        # that the active runtime is .memory-seed/, not the legacy .AGENTS/ fallback.
        from memory_seed.core import resolve_runtime
        runtime = resolve_runtime(cwd)
        self.assertFalse(runtime.legacy)
        # .agents/ persona templates are seeded; registry is bootstrap-generated (absent after bare init)
        self.assertTrue((cwd / ".agents" / "README.md").exists())
        self.assertTrue((cwd / ".agents" / "developer.md").exists())
        self.assertTrue((cwd / ".agents" / "solo-founder.md").exists())
        self.assertFalse((cwd / ".agents" / "_registry.yaml").exists())

    def test_init_merges_into_foreign_routing_file_without_force(self):
        # A pre-existing foreign entry-point file (no frontmatter, e.g. a host's
        # own AGENTS.md) no longer blocks init: we inject our routing block and
        # leave the host's content intact, never overwrite.
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text("# Foreign Tool\n\nhost content\n", encoding="utf-8")

        result = init_project(cwd=cwd)

        self.assertTrue(result.changed)
        text = (cwd / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("host content", text)
        self.assertIn("<!-- BEGIN memory-seed", text)
        self.assertIn("AGENTS.md", result.created)
        # No backup/overwrite of a foreign file.
        self.assertEqual(result.backed_up, [])

    def test_init_force_does_not_clobber_foreign_routing_file(self):
        # --force does not license destroying host content: a foreign routing
        # file is still merged, not backed up + overwritten.
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text("# Foreign Tool\n\nhost content\n", encoding="utf-8")

        result = init_project(cwd=cwd, force=True)

        text = (cwd / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("host content", text)
        self.assertIn("<!-- BEGIN memory-seed", text)
        self.assertEqual(result.backed_up, [])

    def test_init_force_backs_up_existing_owned_files_before_replacement(self):
        # An owned routing file (carries our frontmatter) is the case --force
        # backs up + replaces wholesale.
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text(
            "---\nmemory-system-version: 1.0\n---\n\nold owned entry\n", encoding="utf-8"
        )

        result = init_project(cwd=cwd, force=True)

        self.assertTrue(result.changed)
        self.assertEqual(len(result.backed_up), 1)
        self.assertTrue(result.backed_up[0].startswith(".memory-seed/backups/"))
        self.assertIn("old owned entry", (cwd / result.backed_up[0]).read_text(encoding="utf-8"))
        self.assertIn(
            f"memory-system-version: {get_version()}",
            (cwd / "AGENTS.md").read_text(encoding="utf-8"),
        )
        self.assertIn(".memory-seed/backups/", (cwd / ".gitignore").read_text(encoding="utf-8"))

    def test_init_force_preserves_existing_gitignore_when_adding_backup_ignore(self):
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text(
            "---\nmemory-system-version: 1.0\n---\n\nold owned entry\n", encoding="utf-8"
        )
        (cwd / ".gitignore").write_text("dist/\n", encoding="utf-8")

        init_project(cwd=cwd, force=True)

        gitignore = (cwd / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("dist/\n", gitignore)
        self.assertEqual(gitignore.count(".memory-seed/backups/"), 1)

    def test_doctor_reports_missing_and_version_mismatched_control_plane_files(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        gemini = cwd / "GEMINI.md"
        gemini.write_text(
            gemini.read_text(encoding="utf-8").replace(get_version(), "1.1"),
            encoding="utf-8",
        )
        (cwd / "CLAUDE.md").unlink()

        result = doctor(cwd=cwd)

        self.assertFalse(result.ok)
        self.assertFalse(result.control_plane_ok)
        self.assertFalse(result.bootstrap_complete)
        self.assertEqual(result.missing, ["CLAUDE.md"])
        self.assertEqual(
            sorted(result.bootstrap_missing),
            [".memory-seed/index.md", ".memory-seed/policy.md"],
        )
        self.assertEqual(
            result.version_mismatches,
            [{"file": "GEMINI.md", "expected": get_version(), "actual": "1.1"}],
        )

    def test_doctor_distinguishes_bootstrap_completeness_from_control_plane_health(self):
        cwd = self.make_project()
        init_project(cwd=cwd)

        result = doctor(cwd=cwd)

        self.assertFalse(result.ok)
        self.assertTrue(result.control_plane_ok)
        self.assertFalse(result.bootstrap_complete)
        self.assertEqual(result.missing, [])
        self.assertEqual(result.version_mismatches, [])
        self.assertEqual(
            sorted(result.bootstrap_missing),
            [".memory-seed/index.md", ".memory-seed/policy.md"],
        )

        (cwd / ".memory-seed" / "index.md").write_text("# Runtime Index\n", encoding="utf-8")
        (cwd / ".memory-seed" / "policy.md").write_text("# Runtime Policy\n", encoding="utf-8")

        complete = doctor(cwd=cwd)

        self.assertTrue(complete.ok)
        self.assertTrue(complete.control_plane_ok)
        self.assertTrue(complete.bootstrap_complete)
        self.assertEqual(complete.bootstrap_missing, [])

    def test_session_entry_id_uses_80_bit_mse_format_and_is_metadata_deterministic(self):
        first = generate_session_entry_id(
            timestamp="2026-05-26 18:54",
            title="Bootstrap-generated memory and semantic MCP",
            user_initials="JN",
            agent_type="codex",
            project_path=".",
            subproject_path=None,
        )
        second = generate_session_entry_id(
            timestamp="2026-05-26 18:54",
            title="Bootstrap-generated memory and semantic MCP",
            user_initials="JN",
            agent_type="codex",
            project_path=".",
            subproject_path=None,
        )

        self.assertEqual(first, second)
        self.assertRegex(first, r"^mse_[0-9a-hjkmnp-tv-z]{16}$")
        self.assertEqual(len(first), len("mse_") + 16)

    def test_reusable_seed_docs_are_self_contained(self):
        checked = [
            Path("AGENTS.md"),
            Path(".memory-seed/agent-rules.md"),
            Path(".memory-seed/project-bootstrap.md"),
            Path("memory_seed/seed/AGENTS.md"),
            Path("memory_seed/seed/.memory-seed/agent-rules.md"),
            Path("memory_seed/seed/.memory-seed/project-bootstrap.md"),
        ]
        forbidden = ("v1.4", "Memory Seed v1.4", "context.md", "style.md")

        for path in checked:
            content = path.read_text(encoding="utf-8")
            for term in forbidden:
                self.assertNotIn(term, content, f"{path} should not reference {term}")
            self.assertNotIn(".memory-seed/backups/", content)

    def test_update_refreshes_control_plane_and_preserves_generated_memory(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        # Owned (frontmatter) but old: the case update backs up + replaces wholesale.
        (cwd / "AGENTS.md").write_text(
            "---\nmemory-system-version: 1.0\n---\n\nold agent entry\n", encoding="utf-8"
        )
        (cwd / "CLAUDE.md").unlink()
        (cwd / ".memory-seed" / "index.md").write_text(
            "project facts",
            encoding="utf-8",
        )

        result = update_project(cwd=cwd)

        self.assertTrue(result.changed)
        self.assertIn("CLAUDE.md", result.created)
        self.assertTrue(any(path.endswith("/AGENTS.md") for path in result.backed_up))
        self.assertIn(
            f"memory-system-version: {get_version()}",
            (cwd / "AGENTS.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            f"memory-system-version: {get_version()}",
            (cwd / "CLAUDE.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (cwd / ".memory-seed" / "index.md").read_text(encoding="utf-8"),
            "project facts",
        )
        self.assertIn(".memory-seed/backups/", (cwd / ".gitignore").read_text(encoding="utf-8"))

    def test_update_preserves_declared_integration_mode(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        project_config = cwd / MEMORY_DIR_NAME / "project.yaml"
        project_config.write_text("integration_mode: pr\n", encoding="utf-8")

        update_project(cwd=cwd)

        self.assertEqual(project_config.read_text(encoding="utf-8"), "integration_mode: pr\n")

    def test_update_archives_replaced_control_plane_files_by_old_version(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        agents = cwd / "AGENTS.md"
        agents.write_text(
            agents.read_text(encoding="utf-8").replace(get_version(), "1.4"),
            encoding="utf-8",
        )

        result = update_project(cwd=cwd)

        self.assertTrue(result.changed)
        archived = cwd / ".memory-seed" / "archive" / "1.4" / "AGENTS.md"
        self.assertIn(".memory-seed/archive/1.4/AGENTS.md", result.archived)
        self.assertTrue(archived.exists())
        self.assertIn("memory-system-version: 1.4", archived.read_text(encoding="utf-8"))

    def test_update_does_not_downgrade_newer_control_plane_files(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        agents = cwd / "AGENTS.md"
        # Simulate a project on a newer control plane than this tool ships.
        agents.write_text(
            agents.read_text(encoding="utf-8").replace(
                f"memory-system-version: {get_version()}",
                "memory-system-version: 9.9",
            ),
            encoding="utf-8",
        )

        result = update_project(cwd=cwd)

        # The newer file must be left untouched: no overwrite, no archive.
        self.assertIn("memory-system-version: 9.9", agents.read_text(encoding="utf-8"))
        self.assertNotIn("AGENTS.md", result.created)
        self.assertFalse(any("AGENTS.md" in archived for archived in result.archived))

    def test_update_merges_into_foreign_routing_file_without_clobbering(self):
        # Replaces the retired "versionless -> archive + overwrite" behavior:
        # a foreign (host-owned, no-frontmatter) entry-point file is now merged,
        # never destroyed. This is the fail-safe direction when ownership is
        # unprovable.
        cwd = self.make_project()
        init_project(cwd=cwd)
        agents = cwd / "AGENTS.md"
        agents.write_text("# HyperFrames Project\n\nhost rules here\n", encoding="utf-8")

        result = update_project(cwd=cwd)

        self.assertTrue(result.changed)
        text = agents.read_text(encoding="utf-8")
        self.assertIn("host rules here", text)
        self.assertIn("<!-- BEGIN memory-seed", text)
        self.assertIn("AGENTS.md", result.created)
        # Foreign file is not archived/overwritten.
        self.assertEqual(result.archived, [])
        self.assertFalse(list((cwd / ".memory-seed" / "archive").glob("unknown-*/AGENTS.md")))

    def test_update_resyncs_existing_routing_block_in_place(self):
        # The "second merge": a foreign file already carrying an old routing block
        # has only that block replaced in place; host content is untouched and
        # there is exactly one block.
        cwd = self.make_project()
        init_project(cwd=cwd)
        agents = cwd / "AGENTS.md"
        agents.write_text(
            "# HyperFrames Project\n\nhost rules here\n\n"
            "<!-- BEGIN memory-seed v=2.7 (managed block) -->\n"
            "stale routing text\n"
            "<!-- END memory-seed -->\n",
            encoding="utf-8",
        )

        result = update_project(cwd=cwd)

        text = agents.read_text(encoding="utf-8")
        self.assertIn("host rules here", text)
        self.assertNotIn("stale routing text", text)
        self.assertIn("agent-rules.md", text)  # current block body
        self.assertEqual(text.count("<!-- BEGIN memory-seed"), 1)
        self.assertEqual(text.count("<!-- END memory-seed -->"), 1)
        self.assertIn("AGENTS.md", result.created)

    def test_update_foreign_routing_merge_is_idempotent(self):
        # Once the current block is present, a second update reports no change
        # for that file (content-equality gate, like the JSON merges).
        cwd = self.make_project()
        init_project(cwd=cwd)
        agents = cwd / "AGENTS.md"
        agents.write_text("# HyperFrames Project\n\nhost rules here\n", encoding="utf-8")

        update_project(cwd=cwd)
        before = agents.read_text(encoding="utf-8")
        result = update_project(cwd=cwd)

        self.assertEqual(agents.read_text(encoding="utf-8"), before)
        self.assertNotIn("AGENTS.md", result.created)

    def test_merge_routing_stanza_resyncs_on_body_change_only(self):
        # The no-churn guarantee: the block is rewritten only when its body
        # differs, not on a bare version bump (the block carries no version).
        from memory_seed.core import _merge_routing_stanza

        cwd = self.make_project()
        f = cwd / "HOST.md"
        f.write_text("# Host\n\nhost content\n", encoding="utf-8")

        self.assertTrue(_merge_routing_stanza(f))            # injected
        self.assertFalse(_merge_routing_stanza(f))           # identical -> no write
        # A different stanza body forces an in-place re-sync.
        changed = "<!-- BEGIN memory-seed -->\nnew body\n<!-- END memory-seed -->"
        self.assertTrue(_merge_routing_stanza(f, changed))
        self.assertFalse(_merge_routing_stanza(f, changed))
        self.assertIn("host content", f.read_text(encoding="utf-8"))

    def test_update_dry_run_reports_seed_files_without_writing(self):
        cwd = self.make_project()
        (cwd / "AGENTS.md").write_text("old agent entry", encoding="utf-8")

        result = update_project(cwd=cwd, dry_run=True)

        self.assertFalse(result.changed)
        self.assertEqual(result.created, [])
        self.assertEqual(result.backed_up, [])
        expected = [
            seed_file.destination
            for seed_file in SEED_FILES
            if not seed_file.destination.startswith(".memory-seed/skills/")
            or Path(seed_file.destination).name in set(CORE_SKILL_NAMES) | {"index.md"}
        ]
        self.assertEqual(
            sorted(result.planned),
            sorted(expected),
        )
        self.assertEqual((cwd / "AGENTS.md").read_text(encoding="utf-8"), "old agent entry")

    def test_init_installs_minimal_core_skills_and_records_ignored_optionals(self):
        cwd = self.make_project()

        result = init_project(cwd=cwd)

        installed = {p.name for p in (cwd / ".memory-seed" / "skills").glob("*.md")}
        self.assertIn("session_logging.md", installed)
        self.assertIn("history_retrieval.md", installed)
        self.assertIn("memory_doctor.md", installed)
        self.assertNotIn("code_search.md", installed)
        self.assertNotIn("proposal_lifecycle.md", installed)
        self.assertNotIn("docs/inbox/.gitkeep", result.created)
        self.assertNotIn("docs/reference/.gitkeep", result.created)
        project_yaml = (cwd / ".memory-seed" / "project.yaml").read_text(encoding="utf-8")
        self.assertIn("skills:", project_yaml)
        self.assertIn("selected:", project_yaml)
        self.assertIn("ignored:", project_yaml)
        self.assertIn("code_search.md", project_yaml)
        self.assertTrue(doctor(cwd=cwd).control_plane_ok)

    def test_init_profile_installs_profile_skills_and_docs_lifecycle(self):
        cwd = self.make_project()

        result = init_project(cwd=cwd, skill_profiles={"coding", "planning"})

        installed = {p.name for p in (cwd / ".memory-seed" / "skills").glob("*.md")}
        self.assertIn("code_search.md", installed)
        self.assertIn("local_compilation.md", installed)
        self.assertIn("data_architecture.md", installed)
        self.assertIn("proposal_lifecycle.md", installed)
        self.assertTrue((cwd / "docs" / "inbox" / ".gitkeep").exists())
        self.assertTrue((cwd / "docs" / "todo" / ".gitkeep").exists())
        self.assertTrue((cwd / "docs" / "todo" / "completed" / ".gitkeep").exists())
        self.assertTrue((cwd / "docs" / "reference" / ".gitkeep").exists())
        self.assertIn("docs/inbox/.gitkeep", result.created)
        self.assertIn("docs/reference/.gitkeep", result.created)
        project_yaml = (cwd / ".memory-seed" / "project.yaml").read_text(encoding="utf-8")
        self.assertIn("coding", project_yaml)
        self.assertIn("planning", project_yaml)

    def test_update_respects_ignored_optional_skills(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        self.assertFalse((cwd / ".memory-seed" / "skills" / "code_search.md").exists())

        result = update_project(cwd=cwd)

        self.assertFalse((cwd / ".memory-seed" / "skills" / "code_search.md").exists())
        self.assertNotIn(".memory-seed/skills/code_search.md", result.created)
        self.assertTrue(doctor(cwd=cwd).control_plane_ok)

    def test_legacy_project_without_skills_block_preserves_installed_optionals(self):
        cwd = self.make_project()
        init_project(cwd=cwd, skill_profiles=set(SKILL_PROFILES))
        project_yaml = cwd / ".memory-seed" / "project.yaml"
        project_yaml.write_text("agents:\n  - codex\n", encoding="utf-8")
        self.assertTrue((cwd / ".memory-seed" / "skills" / "code_search.md").exists())

        result = update_project(cwd=cwd)

        self.assertTrue((cwd / ".memory-seed" / "skills" / "code_search.md").exists())
        self.assertNotIn(".memory-seed/skills/code_search.md", result.created)

    def test_skill_add_and_remove_update_files_registry_and_state(self):
        cwd = self.make_project()
        init_project(cwd=cwd)

        added = add_skill(cwd=cwd, name="planning")

        self.assertTrue(added["changed"])
        self.assertTrue((cwd / ".memory-seed" / "skills" / "proposal_lifecycle.md").exists())
        self.assertTrue((cwd / "docs" / "inbox" / ".gitkeep").exists())
        self.assertTrue((cwd / "docs" / "reference" / ".gitkeep").exists())
        registry = (cwd / ".memory-seed" / "skills" / "index.md").read_text(encoding="utf-8")
        self.assertIn("skill: proposal_lifecycle.md", registry)
        self.assertIn("planning", (cwd / ".memory-seed" / "project.yaml").read_text(encoding="utf-8"))

        removed = remove_skill(cwd=cwd, skill="proposal_lifecycle.md")

        self.assertTrue(removed["changed"])
        self.assertFalse((cwd / ".memory-seed" / "skills" / "proposal_lifecycle.md").exists())
        self.assertFalse((cwd / "docs" / "reference" / ".gitkeep").exists())
        registry = (cwd / ".memory-seed" / "skills" / "index.md").read_text(encoding="utf-8")
        self.assertNotIn("skill: proposal_lifecycle.md", registry)
        self.assertTrue(any(path.endswith("proposal_lifecycle.md") for path in removed["backed_up"]))
        self.assertFalse(any("proposal_lifecycle.md" in w for w in doctor(cwd=cwd).warnings))

    def test_skill_status_reports_profiles_installed_and_ignored(self):
        cwd = self.make_project()
        init_project(cwd=cwd, skill_profiles={"coding"})

        status = skill_status(cwd=cwd)

        self.assertIn("session_logging.md", status["core"])
        self.assertIn("code_search.md", status["installed_optional"])
        self.assertIn("proposal_lifecycle.md", status["ignored"])
        self.assertEqual(status["profiles"]["coding"], list(SKILL_PROFILES["coding"].skills))
        self.assertEqual(set(status["available_optional"]), set(OPTIONAL_SKILL_NAMES))

    def test_skill_architecture_is_optional_governance_profile_skill(self):
        cwd = self.make_project()

        init_project(cwd=cwd, skill_profiles={"governance"})

        self.assertNotIn("skill_architecture.md", CORE_SKILL_NAMES)
        self.assertIn("skill_architecture.md", OPTIONAL_SKILL_NAMES)
        self.assertEqual(SKILL_PROFILES["governance"].skills, ("skill_architecture.md",))
        self.assertTrue((cwd / ".memory-seed" / "skills" / "skill_architecture.md").exists())
        registry = (cwd / ".memory-seed" / "skills" / "index.md").read_text(encoding="utf-8")
        self.assertIn("skill: skill_architecture.md", registry)
        self.assertIn("governance", (cwd / ".memory-seed" / "project.yaml").read_text(encoding="utf-8"))

    def test_update_does_nothing_when_control_plane_is_current(self):
        cwd = self.make_project()
        init_project(cwd=cwd)

        result = update_project(cwd=cwd)

        self.assertFalse(result.changed)
        self.assertEqual(result.created, [])
        self.assertEqual(result.backed_up, [])
        self.assertFalse((cwd / ".memory-seed" / "backups").exists())

    def test_update_uses_yaml_version_instead_of_full_file_comparison(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        agents = cwd / "AGENTS.md"
        agents.write_text(
            agents.read_text(encoding="utf-8") + "\nLocal same-version note.\n",
            encoding="utf-8",
        )

        result = update_project(cwd=cwd)

        self.assertFalse(result.changed)
        self.assertEqual(result.backed_up, [])
        self.assertIn("Local same-version note.", agents.read_text(encoding="utf-8"))

    def test_update_refreshes_reusable_runtime_procedure_files(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        rules = cwd / ".memory-seed" / "agent-rules.md"
        rules.write_text("old runtime rules", encoding="utf-8")

        result = update_project(cwd=cwd)

        self.assertTrue(result.changed)
        self.assertIn(".memory-seed/agent-rules.md", result.created)
        self.assertTrue(
            any(path.endswith("/.memory-seed/agent-rules.md") for path in result.backed_up)
        )
        self.assertIn(f"memory-system-version: {get_version()}", rules.read_text(encoding="utf-8"))

    def test_control_plane_files_report_current_version(self):
        for seed_file in SEED_FILES:
            if not seed_file.source.suffix == ".md":
                continue
            if seed_file.destination.startswith(".agents/"):
                continue  # agent personas are project-local, not version-tracked control plane
            content = seed_file.source.read_text(encoding="utf-8")
            self.assertIn(f"memory-system-version: {get_version()}", content, seed_file.destination)

    def test_repo_root_control_plane_files_match_version(self):
        # Guards the recurring release trap: the frontmatter version-bump sed is
        # scoped to memory_seed/seed/ and .memory-seed/, so it silently skips
        # this self-hosting repo's own root routing files (AGENTS/CLAUDE/GEMINI.md).
        # doctor() catches the drift at runtime; this pins it in the suite so a
        # missed root file fails CI instead of shipping (happened in 2.2.3 / 2.3.0).
        repo_root = Path(__file__).resolve().parent.parent
        expected = f"memory-system-version: {get_version()}"
        for seed_file in SEED_FILES:
            if not seed_file.source.suffix == ".md":
                continue
            if seed_file.destination.startswith(".agents/"):
                continue  # agent personas are project-local, not version-tracked control plane
            live = repo_root / seed_file.destination
            self.assertTrue(live.exists(), f"missing live control-plane file: {seed_file.destination}")
            self.assertIn(expected, live.read_text(encoding="utf-8"), seed_file.destination)

    def test_seed_files_use_memory_seed_runtime(self):
        destinations = sorted(seed_file.destination for seed_file in SEED_FILES)

        self.assertEqual(
            destinations,
            [
                ".agents/README.md",
                ".agents/content-creator.md",
                ".agents/copywriter.md",
                ".agents/developer.md",
                ".agents/researcher.md",
                ".agents/sales-rep.md",
                ".agents/solo-founder.md",
                ".claude/commands/esr.md",
                ".claude/commands/situate.md",
                ".gemini/commands/esr.toml",
                ".gemini/commands/situate.toml",
                ".github/copilot-instructions.md",
                ".memory-seed/agent-rules.md",
                ".memory-seed/archive/.gitkeep",
                ".memory-seed/hooks/memory-retrieval-check.py",
                ".memory-seed/hooks/prepare-commit-msg.py",
                ".memory-seed/hooks/session-log-check.py",
                ".memory-seed/hooks/session-start-context.py",
                ".memory-seed/project-bootstrap.md",
                ".memory-seed/sessions/.gitkeep",
                ".memory-seed/skills/agent_collaboration.md",
                ".memory-seed/skills/code_search.md",
                ".memory-seed/skills/compact_mermaid_diagrams.md",
                ".memory-seed/skills/copywriter-conversion.md",
                ".memory-seed/skills/data_architecture.md",
                ".memory-seed/skills/document_ingestion.md",
                ".memory-seed/skills/docx_render_windows.md",
                ".memory-seed/skills/end_of_turn.md",
                ".memory-seed/skills/history_retrieval.md",
                ".memory-seed/skills/index.md",
                ".memory-seed/skills/local_compilation.md",
                ".memory-seed/skills/memory_consolidation.md",
                ".memory-seed/skills/memory_doctor.md",
                ".memory-seed/skills/memory_hygiene.md",
                ".memory-seed/skills/office_document_editing.md",
                ".memory-seed/skills/orientation.md",
                ".memory-seed/skills/proposal_lifecycle.md",
                ".memory-seed/skills/release_publishing.md",
                ".memory-seed/skills/risk_signaling.md",
                ".memory-seed/skills/security_triage.md",
                ".memory-seed/skills/session_logging.md",
                ".memory-seed/skills/skill_architecture.md",
                ".memory-seed/skills/subproject_runtime.md",
                ".memory-seed/topics.yaml",
                "AGENTS.md",
                "CLAUDE.md",
                "GEMINI.md",
            ],
        )

    def test_package_data_includes_all_seed_files(self):
        pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        package_data = set(pyproject["tool"]["setuptools"]["package-data"]["memory_seed"])
        expected = {
            seed_file.source.relative_to(PACKAGE_ROOT).as_posix()
            for seed_file in SEED_FILES
        }

        self.assertEqual(expected - package_data, set())

    def test_seed_toml_files_parse_without_bom(self):
        for seed_file in SEED_FILES:
            if seed_file.source.suffix != ".toml":
                continue
            data = seed_file.source.read_bytes()
            self.assertFalse(
                data.startswith(b"\xef\xbb\xbf"),
                f"{seed_file.destination} must be UTF-8 without BOM",
            )
            parsed = tomllib.loads(data.decode("utf-8"))
            self.assertIsInstance(parsed, dict)

    def test_update_does_not_overwrite_customized_agent_persona(self):
        cwd = self.make_project()
        init_project(cwd=cwd)
        persona = cwd / ".agents" / "developer.md"
        persona.write_text(persona.read_text(encoding="utf-8") + "\n## Custom Section\nProject-specific rule.\n", encoding="utf-8")

        result = update_project(cwd=cwd)

        self.assertNotIn(".agents/developer.md", result.created)
        self.assertIn("Custom Section", persona.read_text(encoding="utf-8"))

    def test_init_installs_esr_command_for_claude_and_gemini_only(self):
        # The /esr end-of-session command ships only for agents with a verified
        # repo-level command mechanism; Codex/Cursor invoke the routine via
        # agent-rules.md instead.
        for agents, claude_cmd, gemini_cmd in (
            ({"claude"}, True, False),
            ({"gemini"}, False, True),
            ({"claude", "gemini"}, True, True),
            ({"codex"}, False, False),
        ):
            cwd = self.make_project()
            init_project(cwd=cwd, agents=agents)
            self.assertEqual((cwd / ".claude" / "commands" / "esr.md").exists(), claude_cmd, agents)
            self.assertEqual((cwd / ".gemini" / "commands" / "esr.toml").exists(), gemini_cmd, agents)

    def test_update_keeps_gemini_command_deploy_once_but_refreshes_claude_command(self):
        # The Gemini TOML command cannot carry a version marker, so it is
        # deploy-once (never overwritten); the Claude .md command is version-
        # tracked and refreshes on update.
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude", "gemini"})
        gem = cwd / ".gemini" / "commands" / "esr.toml"
        claude = cwd / ".claude" / "commands" / "esr.md"
        gem.write_text(gem.read_text(encoding="utf-8") + "\n# local tweak\n", encoding="utf-8")
        claude.write_text("stale claude command", encoding="utf-8")

        result = update_project(cwd=cwd)

        # Gemini command preserved (deploy-once); Claude command refreshed.
        self.assertIn("# local tweak", gem.read_text(encoding="utf-8"))
        self.assertNotIn(".gemini/commands/esr.toml", result.created)
        self.assertIn(".claude/commands/esr.md", result.created)
        self.assertIn(f"memory-system-version: {get_version()}", claude.read_text(encoding="utf-8"))

    def test_resolve_runtime_prefers_nearest_memory_seed(self):
        cwd = self.make_project()
        root_runtime = cwd / MEMORY_DIR_NAME
        subproject = cwd / "apps" / "mobile"
        sub_runtime = subproject / MEMORY_DIR_NAME
        root_runtime.mkdir(parents=True)
        sub_runtime.mkdir(parents=True)
        nested = subproject / "src"
        nested.mkdir()

        resolved = resolve_runtime(nested)

        self.assertEqual(resolved.workspace_root, subproject.resolve())
        self.assertEqual(resolved.memory_dir, sub_runtime.resolve())
        self.assertFalse(resolved.legacy)

    def test_resolve_runtime_falls_back_to_legacy_agents(self):
        cwd = self.make_project()
        legacy = cwd / ".AGENTS"
        legacy.mkdir()
        nested = cwd / "packages" / "core"
        nested.mkdir(parents=True)

        resolved = resolve_runtime(nested)

        self.assertEqual(resolved.workspace_root, cwd.resolve())
        self.assertEqual(resolved.memory_dir, legacy.resolve())
        self.assertTrue(resolved.legacy)

    # --- compact tests ---

    def _make_sessions(self, cwd, entries):
        sessions_dir = cwd / MEMORY_DIR_NAME / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in entries.items():
            path = sessions_dir / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def test_iter_session_documents_discovers_legacy_and_per_user_sessions(self):
        cwd = self.make_project()
        self._make_sessions(cwd, {
            "2026-06-20.md": "## Legacy\n",
            "2026-06-21/jean.md": "## Jean\n",
            "2026-06-21/amina.md": "## Amina\n",
            "2026-06/2026-06-22.md": "## Month flat\n",
            "2026-06/2026-06-23/jean.md": "## Month Jean\n",
            "2026-07/2026-06-24.md": "## Month mismatch\n",
            "2026-07/2026-06-24/jean.md": "## Month user mismatch\n",
            "2026-06-21/README.md": "## Not a user\n",
            "2026-06-21/Bad_User.md": "## Invalid slug\n",
            "not-a-date/theo.md": "## Invalid date\n",
            "2026-06-22.md/readme.md": "## Invalid layout\n",
        })

        docs = list(iter_session_documents(cwd / MEMORY_DIR_NAME / "sessions"))

        self.assertEqual(
            [(doc.session_date, doc.user, doc.layout, doc.path.name) for doc in docs],
            [
                ("2026-06-20", None, "legacy-flat", "2026-06-20.md"),
                ("2026-06-21", "amina", "per-user-day", "amina.md"),
                ("2026-06-21", "jean", "per-user-day", "jean.md"),
                ("2026-06-22", None, "month-flat", "2026-06-22.md"),
                ("2026-06-23", "jean", "month-user", "jean.md"),
            ],
        )

    def test_session_target_uses_month_grouped_path_without_configured_user(self):
        cwd = self.make_project()
        (cwd / MEMORY_DIR_NAME / "sessions").mkdir(parents=True)

        target = session_target(cwd=cwd, date_str="2026-06-21")

        self.assertEqual(
            target.path,
            cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21.md",
        )
        self.assertIsNone(target.user)
        self.assertEqual(target.layout, "month-flat")

    def test_session_target_uses_environment_user_before_local_config(self):
        import os
        from unittest.mock import patch

        cwd = self.make_project()
        local = cwd / MEMORY_DIR_NAME / "local.yaml"
        local.parent.mkdir(parents=True)
        local.write_text("user: amina\n", encoding="utf-8")
        self._write_participants(cwd)

        with patch.dict(os.environ, {"MEMORY_SEED_USER": "jean"}):
            target = session_target(cwd=cwd, date_str="2026-06-21")

        self.assertEqual(target.user, "jean")
        self.assertEqual(
            target.path,
            cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21" / "jean.md",
        )
        self.assertEqual(target.layout, "month-user")

    def test_session_target_stays_flat_with_fewer_than_two_participants(self):
        cwd = self.make_project()
        local = cwd / MEMORY_DIR_NAME / "local.yaml"
        local.parent.mkdir(parents=True)
        local.write_text("user: jean\n", encoding="utf-8")

        # No participants: file at all -> flat.
        target = session_target(cwd=cwd, date_str="2026-06-21")
        self.assertIsNone(target.user)
        self.assertEqual(target.layout, "month-flat")

        # Exactly one participant -> still flat; a configured user alone isn't
        # enough to fragment the log, since there's no second author to
        # collide with yet.
        (cwd / MEMORY_DIR_NAME / "project.yaml").write_text(
            "participants:\n  - slug: jean\n    initials: JN\n", encoding="utf-8"
        )
        target = session_target(cwd=cwd, date_str="2026-06-21")
        self.assertIsNone(target.user)
        self.assertEqual(target.layout, "month-flat")

    def test_session_target_switches_to_per_user_with_two_participants(self):
        cwd = self.make_project()
        local = cwd / MEMORY_DIR_NAME / "local.yaml"
        local.parent.mkdir(parents=True)
        local.write_text("user: jean\n", encoding="utf-8")
        self._write_participants(cwd)

        target = session_target(cwd=cwd, date_str="2026-06-21")

        self.assertEqual(target.user, "jean")
        self.assertEqual(target.layout, "month-user")

    def test_session_target_explicit_user_bypasses_participant_gate(self):
        cwd = self.make_project()

        target = session_target(cwd=cwd, date_str="2026-06-21", explicit_user="jean")

        self.assertEqual(target.user, "jean")
        self.assertEqual(target.layout, "month-user")

    def test_session_target_create_initializes_per_user_file_once(self):
        cwd = self.make_project()

        target = session_target(cwd=cwd, date_str="2026-06-21", explicit_user="jean", create=True)
        first = target.path.read_text(encoding="utf-8")
        target.path.write_text(first + "\n## 2026-06-21 12:00 - Existing\n\nbody\n", encoding="utf-8")
        session_target(cwd=cwd, date_str="2026-06-21", explicit_user="jean", create=True)

        text = target.path.read_text(encoding="utf-8")
        self.assertIn("schema_version: 2", text)
        self.assertIn("session_date: 2026-06-21", text)
        self.assertIn("hash_id: msm_", text)
        self.assertIn("user: jean", text)
        self.assertIn("## 2026-06-21 12:00 - Existing", text)
        self.assertEqual(text.count("schema_version: 2"), 1)

    def test_session_target_rejects_invalid_user_slug(self):
        cwd = self.make_project()

        with self.assertRaises(ValueError):
            session_target(cwd=cwd, date_str="2026-06-21", explicit_user="Bad_User")

    def test_session_target_rejects_invalid_session_date(self):
        cwd = self.make_project()

        with self.assertRaises(ValueError):
            session_target(cwd=cwd, date_str="2026-13-40")

    def _write_participants(self, cwd):
        cfg = cwd / MEMORY_DIR_NAME / "project.yaml"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "participants:",
                    "  - slug: jean",
                    "    initials: JN",
                    "    display_name: Jean",
                    "  - slug: amina",
                    "    initials: AM",
                    "    display_name: Amina",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def _write_flat_session(self, cwd, date_str="2026-06-21"):
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        path = sessions / f"{date_str}.md"
        path.write_text(
            "\n".join(
                [
                    "# 2026-06-21",
                    "",
                    "## 2026-06-21 09:00 - Jean entry",
                    "",
                    "```yaml",
                    "entry_id: ms-11111111",
                    "user_initials: JN",
                    "agent_type: codex",
                    "```",
                    "",
                    "- Jean body.",
                    "",
                    "## 2026-06-21 10:00 - Amina entry",
                    "",
                    "```yaml",
                    "entry_id: mse_0123456789abcdef",
                    "user_initials: AM",
                    "agent_type: codex",
                    "```",
                    "",
                    "- Amina body.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def test_migrate_sessions_layout_dry_run_plans_without_writing(self):
        cwd = self.make_project()
        self._write_participants(cwd)
        flat = self._write_flat_session(cwd)

        result = migrate_session_layout(cwd=cwd, dry_run=True)

        self.assertFalse(result.changed)
        self.assertEqual(result.planned, ["2026-06-21.md -> 2026-06/2026-06-21/amina.md", "2026-06-21.md -> 2026-06/2026-06-21/jean.md"])
        self.assertEqual(result.issues, [])
        self.assertTrue(flat.exists())
        self.assertFalse((cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21" / "jean.md").exists())

    def test_migrate_sessions_layout_apply_splits_entries_and_backs_up_source(self):
        cwd = self.make_project()
        self._write_participants(cwd)
        flat = self._write_flat_session(cwd)

        result = migrate_session_layout(cwd=cwd)

        self.assertTrue(result.changed)
        self.assertFalse(flat.exists())
        self.assertEqual(result.migrated, ["2026-06/2026-06-21/amina.md", "2026-06/2026-06-21/jean.md"])
        self.assertEqual(len(result.backed_up), 1)
        backup = cwd / result.backed_up[0]
        self.assertTrue(backup.exists())
        jean = (cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21" / "jean.md").read_text(encoding="utf-8")
        amina = (cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21" / "amina.md").read_text(encoding="utf-8")
        self.assertIn("schema_version: 2", jean)
        self.assertIn("hash_id: msm_", jean)
        self.assertIn("user: jean", jean)
        self.assertIn("entry_id: ms-11111111", jean)
        self.assertNotIn("entry_id: mse_0123456789abcdef", jean)
        self.assertIn("entry_id: mse_0123456789abcdef", amina)
        self.assertTrue(check_session_links(cwd=cwd).ok)

    def test_migrate_sessions_layout_is_idempotent_after_apply(self):
        cwd = self.make_project()
        self._write_participants(cwd)
        self._write_flat_session(cwd)

        migrate_session_layout(cwd=cwd)
        result = migrate_session_layout(cwd=cwd)

        self.assertFalse(result.changed)
        self.assertEqual(result.planned, [])
        self.assertEqual(result.migrated, [])
        self.assertEqual(result.issues, [])

    def test_migrate_sessions_layout_blocks_unknown_initials_without_writing(self):
        cwd = self.make_project()
        self._write_participants(cwd)
        flat = self._write_flat_session(cwd)
        text = flat.read_text(encoding="utf-8").replace("user_initials: AM", "user_initials: ZZ")
        flat.write_text(text, encoding="utf-8")

        result = migrate_session_layout(cwd=cwd)

        self.assertFalse(result.changed)
        self.assertEqual(result.migrated, [])
        self.assertTrue(result.issues)
        self.assertIn("ZZ", result.issues[0])
        self.assertTrue(flat.exists())
        self.assertFalse((cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21" / "jean.md").exists())

    def test_migrate_sessions_layout_blocks_duplicate_participant_initials(self):
        cwd = self.make_project()
        self._write_participants(cwd)
        cfg = cwd / MEMORY_DIR_NAME / "project.yaml"
        cfg.write_text(
            cfg.read_text(encoding="utf-8")
            + "  - slug: other-jean\n"
            + "    initials: JN\n",
            encoding="utf-8",
        )
        flat = self._write_flat_session(cwd)

        result = migrate_session_layout(cwd=cwd)

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("duplicate participant initials JN", result.issues[0])
        self.assertTrue(flat.exists())

    def test_migrate_sessions_layout_appends_to_existing_user_file_when_safe(self):
        cwd = self.make_project()
        self._write_participants(cwd)
        self._write_flat_session(cwd)
        existing = session_target(cwd=cwd, date_str="2026-06-21", explicit_user="jean", create=True).path
        existing.write_text(existing.read_text(encoding="utf-8") + "## 2026-06-21 08:00 - Existing\n\n- Existing body.\n", encoding="utf-8")

        result = migrate_session_layout(cwd=cwd)

        self.assertTrue(result.changed)
        jean = existing.read_text(encoding="utf-8")
        self.assertIn("## 2026-06-21 08:00 - Existing", jean)
        self.assertIn("entry_id: ms-11111111", jean)
        self.assertEqual(jean.count("hash_id: msm_"), 1)

    def _write_old_diagram_sidecar(self, cwd, date_str="2026-06-21", entry_id="ms-11111111"):
        diagrams = cwd / MEMORY_DIR_NAME / "sessions" / "diagrams"
        diagrams.mkdir(parents=True, exist_ok=True)
        path = diagrams / f"{date_str}.md"
        path.write_text(
            "\n".join(
                [
                    "---",
                    "tags:",
                    "  - session-log-diagrams",
                    f"diagram_date: {date_str}",
                    "---",
                    "",
                    f"## {date_str} 09:00 - Diagram",
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
        return path

    def test_migrate_sessions_month_layout_dry_run_plans_without_writing(self):
        cwd = self.make_project()
        flat = self._write_flat_session(cwd)
        self._per_user_session(cwd, "2026-06-22", "jean", hash_id="msm_" + "c" * 32, entries=("ms-33333333",))
        diagram = self._write_old_diagram_sidecar(cwd)

        result = migrate_session_month_layout(cwd=cwd, dry_run=True)

        self.assertFalse(result.changed)
        self.assertEqual(
            result.planned,
            [
                "2026-06-21.md -> 2026-06/2026-06-21.md",
                "2026-06-22/jean.md -> 2026-06/2026-06-22/jean.md",
                "diagrams/2026-06-21.md -> diagrams/2026-06/2026-06-21.md",
            ],
        )
        self.assertEqual(result.issues, [])
        self.assertTrue(flat.exists())
        self.assertTrue(diagram.exists())
        self.assertFalse((cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21.md").exists())

    def test_migrate_sessions_month_layout_apply_moves_sources_and_backs_up(self):
        cwd = self.make_project()
        flat = self._write_flat_session(cwd)
        self._per_user_session(cwd, "2026-06-22", "jean", hash_id="msm_" + "c" * 32, entries=("ms-33333333",))
        diagram = self._write_old_diagram_sidecar(cwd)

        result = migrate_session_month_layout(cwd=cwd)

        self.assertTrue(result.changed)
        self.assertEqual(
            result.migrated,
            [
                "2026-06/2026-06-21.md",
                "2026-06/2026-06-22/jean.md",
                "diagrams/2026-06/2026-06-21.md",
            ],
        )
        self.assertFalse(flat.exists())
        self.assertFalse((cwd / MEMORY_DIR_NAME / "sessions" / "2026-06-22" / "jean.md").exists())
        self.assertFalse(diagram.exists())
        self.assertEqual(len(result.backed_up), 3)
        for backup in result.backed_up:
            self.assertTrue((cwd / backup).exists())
        moved_flat = (cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21.md").read_text(encoding="utf-8")
        moved_user = (cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-22" / "jean.md").read_text(encoding="utf-8")
        moved_diagram = (cwd / MEMORY_DIR_NAME / "sessions" / "diagrams" / "2026-06" / "2026-06-21.md").read_text(encoding="utf-8")
        self.assertIn("entry_id: ms-11111111", moved_flat)
        self.assertIn("hash_id: msm_" + "c" * 32, moved_user)
        self.assertIn("```mermaid", moved_diagram)
        self.assertTrue(check_session_links(cwd=cwd).ok)

    def test_migrate_sessions_month_layout_is_idempotent_after_apply(self):
        cwd = self.make_project()
        self._write_flat_session(cwd)

        migrate_session_month_layout(cwd=cwd)
        result = migrate_session_month_layout(cwd=cwd)

        self.assertFalse(result.changed)
        self.assertEqual(result.planned, [])
        self.assertEqual(result.migrated, [])
        self.assertEqual(result.issues, [])

    def test_migrate_sessions_month_layout_appends_to_existing_target_when_safe(self):
        cwd = self.make_project()
        flat = self._write_flat_session(cwd)
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "## 2026-06-21 08:00 - Existing\n\n```yaml\nentry_id: ms-existing\n```\n\n- Existing.\n",
            encoding="utf-8",
        )

        result = migrate_session_month_layout(cwd=cwd)

        self.assertTrue(result.changed)
        self.assertFalse(flat.exists())
        text = target.read_text(encoding="utf-8")
        self.assertIn("entry_id: ms-existing", text)
        self.assertIn("entry_id: ms-11111111", text)
        self.assertIn("entry_id: mse_0123456789abcdef", text)

    def test_migrate_sessions_month_layout_blocks_duplicate_target_entry_ids(self):
        cwd = self.make_project()
        flat = self._write_flat_session(cwd)
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-06" / "2026-06-21.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("## Existing\n\n```yaml\nentry_id: ms-11111111\n```\n", encoding="utf-8")

        result = migrate_session_month_layout(cwd=cwd)

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("ms-11111111", result.issues[0])
        self.assertTrue(flat.exists())

    def _git(self, cwd, *args):
        import subprocess

        return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True)

    def _init_git_project(self, cwd):
        self._git(cwd, "init", "-q")
        self._git(cwd, "config", "user.name", "Test User")
        self._git(cwd, "config", "user.email", "test@example.com")
        self._git(cwd, "config", "commit.gpgsign", "false")
        self._git(cwd, "branch", "-M", "main")

    def _commit_all(self, cwd, message):
        self._git(cwd, "add", "-A")
        self._git(cwd, "commit", "-q", "-m", message)

    def _write_grouped_session(self, cwd, date, entry_id, *, branch, title="Entry", time="09:00", body="- Body."):
        path = cwd / MEMORY_DIR_NAME / "sessions" / date[:7] / f"{date}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    "---",
                    "tags:",
                    "  - session-log",
                    "  - memory-seed",
                    f"session_date: {date}",
                    "---",
                    "",
                    f"## {date} {time} - {title}",
                    "",
                    "```yaml",
                    f"entry_id: {entry_id}",
                    "user_initials: JN",
                    "agent_type: codex",
                    f"branch: {branch}",
                    "```",
                    "",
                    body,
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return path

    def _write_legacy_session(self, cwd, date, entry_id, *, branch, title="Entry", time="09:00"):
        path = cwd / MEMORY_DIR_NAME / "sessions" / f"{date}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    "---",
                    "tags:",
                    "  - session-log",
                    "  - memory-seed",
                    f"session_date: {date}",
                    "---",
                    "",
                    f"## {date} {time} - {title}",
                    "",
                    "```yaml",
                    f"entry_id: {entry_id}",
                    "user_initials: JN",
                    "agent_type: codex",
                    f"branch: {branch}",
                    "```",
                    "",
                    "- Branch body.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return path

    def _write_legacy_diagram(self, cwd, date, entry_id, title="Entry"):
        path = cwd / MEMORY_DIR_NAME / "sessions" / "diagrams" / f"{date}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    "---",
                    "tags:",
                    "  - session-log-diagrams",
                    f"diagram_date: {date}",
                    "---",
                    "",
                    f"## {date} 09:00 - {title}",
                    "",
                    "```yaml",
                    f"entry_id: {entry_id}",
                    "```",
                    "",
                    "```mermaid",
                    "graph TD",
                    "  A[Branch] --> B[Main]",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return path

    def test_session_fuse_dry_run_reports_branch_only_entries_without_writing(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_legacy_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-fuse")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        self.assertFalse(result.changed)
        self.assertEqual(result.issues, [])
        self.assertEqual(
            result.planned_entries,
            ["mse_1111111111111111 2026-07-11 09:00 -> .memory-seed/sessions/2026-07/2026-07-11.md"],
        )
        self.assertFalse((cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-11.md").exists())

    def test_session_fuse_treats_h2_heading_in_body_as_content_not_an_entry(self):
        # Regression for the divergent entry-grammar incident: `session append`
        # accepted a body containing an `## Summary` heading, but the fuse path
        # (via the old broad `^##` boundary regex) split it into a phantom
        # ID-less entry and blocked the merge. One strict timestamped grammar
        # now governs both, so the heading is body content.
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_grouped_session(
            cwd,
            "2026-07-11",
            "mse_1111111111111111",
            branch="feature-fuse",
            body="- Body.\n\n## Summary\n\nAn h2 heading inside the body, not a new entry.",
        )
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        # Exactly one planned entry; no phantom ID-less record, no blocking issue.
        self.assertEqual(result.issues, [])
        self.assertEqual(len(result.planned_entries), 1)
        self.assertIn("mse_1111111111111111", result.planned_entries[0])

    def test_session_fuse_apply_requires_in_progress_merge(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_legacy_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-fuse")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse", apply=True)

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("in-progress git merge", result.issues[0])

    def test_session_fuse_apply_normalizes_paths_and_imports_sidecars(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_legacy_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-fuse")
        self._write_legacy_diagram(cwd, "2026-07-11", "mse_1111111111111111")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")
        self._git(cwd, "merge", "--no-ff", "--no-commit", "feature-fuse")

        result = session_fuse(cwd=cwd, branch="feature-fuse", apply=True)

        self.assertTrue(result.changed)
        self.assertEqual(result.issues, [])
        self.assertFalse((cwd / MEMORY_DIR_NAME / "sessions" / "2026-07-11.md").exists())
        self.assertFalse((cwd / MEMORY_DIR_NAME / "sessions" / "diagrams" / "2026-07-11.md").exists())
        grouped = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-11.md"
        grouped_diagram = cwd / MEMORY_DIR_NAME / "sessions" / "diagrams" / "2026-07" / "2026-07-11.md"
        self.assertIn("entry_id: mse_1111111111111111", grouped.read_text(encoding="utf-8"))
        self.assertIn("branch: feature-fuse", grouped.read_text(encoding="utf-8"))
        self.assertIn("```mermaid", grouped_diagram.read_text(encoding="utf-8"))
        self.assertTrue(check_session_links(cwd=cwd).ok)

    def test_session_fuse_apply_separates_entries_with_one_blank_line(self):
        # Regression: the chronological rewriter used to join rstripped entries
        # with a single "\n", butting each "## " heading against the previous
        # entry's last line and wrecking the log's readability on every fuse.
        cwd = self.make_project()
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-10.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            self._grouped_session_text("2026-07-10", [("09:00", "Base", "mse_aaaaaaaaaaaaaaaa", "main")]),
            encoding="utf-8",
        )
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        target.write_text(
            self._grouped_session_text(
                "2026-07-10",
                [
                    ("09:00", "Base", "mse_aaaaaaaaaaaaaaaa", "main"),
                    ("10:00", "Branch entry", "mse_bbbbbbbbbbbbbbbb", "feature-fuse"),
                ],
            ),
            encoding="utf-8",
        )
        self._commit_all(cwd, "branch appends")
        self._git(cwd, "switch", "main")
        self._git(cwd, "merge", "--no-ff", "--no-commit", "feature-fuse")

        result = session_fuse(cwd=cwd, branch="feature-fuse", apply=True)

        self.assertEqual(result.issues, [])
        text = target.read_text(encoding="utf-8")
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("## ") and index > 0:
                self.assertEqual(
                    lines[index - 1].strip(), "",
                    f"heading at line {index + 1} has no blank line before it: {lines[index - 1]!r}",
                )
        # Exactly one blank line between entries, never a run of them.
        self.assertIn("\n\n## 2026-07-10 10:00", text)
        self.assertNotIn("\n\n\n", text)

    def test_session_fuse_allows_sidecar_for_existing_base_entry(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_legacy_diagram(cwd, "2026-07-10", "mse_0123456789abcdef")
        self._commit_all(cwd, "add sidecar")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        self.assertEqual(result.issues, [])
        self.assertEqual(
            result.planned_sidecars,
            ["mse_0123456789abcdef 2026-07-10 09:00 -> .memory-seed/sessions/diagrams/2026-07/2026-07-10.md"],
        )

    def test_session_fuse_blocks_orphan_sidecar(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_legacy_diagram(cwd, "2026-07-11", "mse_1111111111111111")
        self._commit_all(cwd, "orphan sidecar")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("without a parent entry", result.issues[0])

    def test_session_fuse_blocks_sidecar_without_entry_id(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        sidecar = self._write_legacy_diagram(cwd, "2026-07-10", "mse_0123456789abcdef")
        sidecar.write_text(sidecar.read_text(encoding="utf-8").replace("entry_id: mse_0123456789abcdef\n", ""), encoding="utf-8")
        self._commit_all(cwd, "malformed sidecar")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("diagram sidecar block", result.issues[0])
        self.assertIn("has no entry_id", result.issues[0])

    def test_session_fuse_blocks_session_entry_without_entry_id(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        session = self._write_legacy_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-fuse")
        session.write_text(session.read_text(encoding="utf-8").replace("entry_id: mse_1111111111111111\n", ""), encoding="utf-8")
        self._commit_all(cwd, "malformed session")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("session entry", result.issues[0])
        self.assertIn("has no entry_id", result.issues[0])

    def test_session_fuse_ignores_unchanged_base_entries_without_entry_id(self):
        # Regression: fuse must scope branch-side validation to the branch's changed files, not the
        # whole corpus. A legacy pre-schema entry with no entry_id sitting unchanged on the base tree
        # (e.g. migrated from .AGENTS/) previously blocked every fuse on this repo.
        cwd = self.make_project()
        legacy = cwd / MEMORY_DIR_NAME / "sessions" / "2026-05" / "2026-05-17.md"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(
            "---\ntags:\n  - session-log\nsession_date: 2026-05-17\n---\n\n"
            "## 2026-05-17 09:00 - Legacy entry\n\nNo YAML block and no entry_id.\n",
            encoding="utf-8",
        )
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_legacy_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-fuse")
        self._commit_all(cwd, "feature session")  # legacy file untouched on the branch
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        # The unchanged legacy no-entry_id file is outside the branch diff, so it must not block...
        self.assertEqual(result.issues, [])
        # ...and the genuine branch entry is still planned.
        self.assertEqual(
            result.planned_entries,
            ["mse_1111111111111111 2026-07-11 09:00 -> .memory-seed/sessions/2026-07/2026-07-11.md"],
        )

    def test_session_fuse_reads_non_ascii_branch_entry(self):
        # Regression for the Windows cp1252 crash: git show of a non-ASCII session file must decode
        # as UTF-8. Applies the fuse and asserts the exact non-ASCII body round-trips byte-for-byte -
        # a cp1252 read would either crash or mojibake it, so this guards decoding, not just "no crash".
        non_ascii_body = "- Decision — kept the “fuse” contract \U0001f9e0 café."
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_grouped_session(
            cwd,
            "2026-07-11",
            "mse_2222222222222222",
            branch="feature-fuse",
            body=non_ascii_body,
        )
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")
        self._git(cwd, "merge", "--no-ff", "--no-commit", "feature-fuse")

        result = session_fuse(cwd=cwd, branch="feature-fuse", apply=True)

        self.assertEqual(result.issues, [])
        self.assertTrue(result.changed)
        grouped = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-11.md"
        self.assertIn(non_ascii_body, grouped.read_text(encoding="utf-8"))

    def test_session_fuse_blocks_non_utf8_branch_session_file(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        bad = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07-11.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_bytes(b"## 2026-07-11 09:00 - Bad bytes\n\n```yaml\nentry_id: mse_badbadbadbadbad\nbranch: feature-fuse\n```\n\n\xff\n")
        self._commit_all(cwd, "invalid utf8 session")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        self.assertFalse(result.changed)
        self.assertEqual(result.planned_entries, [])
        self.assertTrue(result.issues)
        self.assertIn("could not decode .memory-seed/sessions/2026-07-11.md as UTF-8", result.issues)

    def test_session_fuse_blocks_when_diff_fails(self):
        # Regression: a git diff failure (e.g. unrelated histories / no merge-base) must surface an
        # issue, not collapse to an empty change set that silently filters out every branch entry
        # and reports success importing nothing.
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "--orphan", "feature-orphan")
        self._write_legacy_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-orphan")
        self._commit_all(cwd, "orphan session")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-orphan")

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("could not compute changed session files", result.issues[0])

    def test_session_fuse_blocks_branch_field_mismatch(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_legacy_session(cwd, "2026-07-11", "mse_1111111111111111", branch="main")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("expected feature-fuse", result.issues[0])

    def test_session_fuse_blocks_existing_entry_edits(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main", body="- Original.")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main", body="- Edited.")
        self._commit_all(cwd, "edit existing")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("existing entry_id modified", result.issues[0])

    def _grouped_session_text(self, date, entries):
        lines = [
            "---",
            "tags:",
            "  - session-log",
            "  - memory-seed",
            f"session_date: {date}",
            "---",
            "",
        ]
        for time, title, entry_id, branch in entries:
            lines += [
                f"## {date} {time} - {title}",
                "",
                "```yaml",
                f"entry_id: {entry_id}",
                "user_initials: JN",
                "agent_type: codex",
                f"branch: {branch}",
                "```",
                "",
                f"- Body for {title}.",
                "",
            ]
        return "\n".join(lines)

    def test_session_merge_branch_commits_clean_merge_end_to_end(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        self._write_grouped_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-merge")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertEqual(result.issues, [])
        self.assertTrue(result.committed)
        self.assertFalse(result.merge_in_progress)
        self.assertFalse((cwd / ".git" / "MERGE_HEAD").exists())
        parents = self._git(cwd, "log", "--merges", "-1", "--format=%P").stdout.split()
        self.assertEqual(len(parents), 2)
        grouped = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-11.md"
        self.assertIn("entry_id: mse_1111111111111111", grouped.read_text(encoding="utf-8"))
        # Working tree fully committed: nothing staged or dirty afterwards.
        self.assertEqual(self._git(cwd, "status", "--short").stdout.strip(), "")

    def test_session_merge_branch_leaves_non_session_conflicts_in_progress(self):
        cwd = self.make_project()
        (cwd / "notes.txt").write_text("base\n", encoding="utf-8")
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        (cwd / "notes.txt").write_text("branch change\n", encoding="utf-8")
        self._commit_all(cwd, "branch edit")
        self._git(cwd, "switch", "main")
        (cwd / "notes.txt").write_text("main change\n", encoding="utf-8")
        self._commit_all(cwd, "main edit")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertFalse(result.committed)
        self.assertTrue(result.merge_in_progress)
        self.assertEqual(result.conflicts, ["notes.txt"])
        # The merge must be left in progress for manual resolution, not aborted.
        self.assertTrue((cwd / ".git" / "MERGE_HEAD").exists())

    def test_session_merge_branch_fixes_out_of_order_landing(self):
        # The bug this command exists for: both sides append to the same dated
        # file after a shared ancestor, and a raw git merge would land the
        # branch's earlier-timestamped entry after base's later one (or leave
        # conflict markers). The wrapper must produce a chronological file.
        cwd = self.make_project()
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-12.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entry_a = ("09:00", "Base entry", "mse_aaaaaaaaaaaaaaaa", "main")
        entry_b = ("10:00", "Later main entry", "mse_bbbbbbbbbbbbbbbb", "main")
        entry_c = ("09:30", "Branch entry", "mse_cccccccccccccccc", "feature-merge")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a]), encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_c]), encoding="utf-8")
        self._commit_all(cwd, "branch appends 09:30")
        self._git(cwd, "switch", "main")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_b]), encoding="utf-8")
        self._commit_all(cwd, "main appends 10:00")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertEqual(result.issues, [])
        self.assertTrue(result.committed)
        text = target.read_text(encoding="utf-8")
        self.assertNotIn("<<<<<<<", text)
        pos_a = text.find("## 2026-07-12 09:00")
        pos_c = text.find("## 2026-07-12 09:30")
        pos_b = text.find("## 2026-07-12 10:00")
        self.assertTrue(0 <= pos_a < pos_c < pos_b, f"order wrong: a={pos_a} c={pos_c} b={pos_b}")
        # The committed tree matches the working tree (fuse result was staged).
        committed = self._git(cwd, "show", "HEAD:.memory-seed/sessions/2026-07/2026-07-12.md").stdout
        self.assertEqual(committed, text)

    def _concurrent_session_branches(self, cwd, *, gitattributes=None):
        """Base and branch both append to one dated file after a shared
        ancestor - the shape that produced the 2026-07-19 corruption. Returns
        the target path, with `main` checked out and `feature-merge` ready."""
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-12.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entry_a = ("09:00", "Base entry", "mse_aaaaaaaaaaaaaaaa", "main")
        entry_b = ("10:00", "Later main entry", "mse_bbbbbbbbbbbbbbbb", "main")
        entry_c = ("09:30", "Branch entry", "mse_cccccccccccccccc", "feature-merge")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a]), encoding="utf-8")
        if gitattributes is not None:
            (cwd / ".gitattributes").write_text(gitattributes, encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_c]), encoding="utf-8")
        self._commit_all(cwd, "branch appends 09:30")
        self._git(cwd, "switch", "main")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_b]), encoding="utf-8")
        self._commit_all(cwd, "main appends 10:00")
        return target

    # The repo ships `.memory-seed/sessions/** -merge` so git cannot line-merge
    # session files. These two pin both halves of that guard.
    NO_MERGE_ATTR = ".memory-seed/sessions/** -merge\n"

    def test_session_merge_branch_still_fuses_under_the_no_merge_attribute(self):
        # The guard must not break the sanctioned path. `-merge` makes git
        # conflict on the session file, but session_merge_branch resets
        # branch-touched session paths to base and rebuilds from parsed records,
        # so a session-only conflict is expected input, not a failure.
        cwd = self.make_project()
        target = self._concurrent_session_branches(cwd, gitattributes=self.NO_MERGE_ATTR)

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertEqual(result.issues, [])
        self.assertTrue(result.committed)
        text = target.read_text(encoding="utf-8")
        self.assertNotIn("<<<<<<<", text)
        pos_a = text.find("## 2026-07-12 09:00")
        pos_c = text.find("## 2026-07-12 09:30")
        pos_b = text.find("## 2026-07-12 10:00")
        self.assertTrue(0 <= pos_a < pos_c < pos_b, f"order wrong: a={pos_a} c={pos_c} b={pos_b}")
        committed = self._git(cwd, "show", "HEAD:.memory-seed/sessions/2026-07/2026-07-12.md").stdout
        self.assertEqual(committed, text)

    def test_the_no_merge_attribute_stops_git_line_merging_session_files(self):
        # The other half: a raw `git merge` - the bypass that caused the
        # corruption - must now fail loudly instead of silently splicing
        # entries. Without the attribute git merges these cleanly by position;
        # with it, the file conflicts and demands the structural merge.
        import subprocess

        cwd = self.make_project()
        self._concurrent_session_branches(cwd, gitattributes=self.NO_MERGE_ATTR)

        merged = subprocess.run(
            ["git", "-C", str(cwd), "merge", "--no-ff", "--no-commit", "feature-merge"],
            capture_output=True, text=True,
        )

        self.assertNotEqual(merged.returncode, 0, "a raw line-merge of session files must not succeed")
        conflicted = self._git(cwd, "diff", "--name-only", "--diff-filter=U").stdout.split()
        self.assertIn(".memory-seed/sessions/2026-07/2026-07-12.md", conflicted)

    def _false_anchor_branches(self, cwd, *, gitattributes=None):
        """The 2026-07-19 corruption shape: two entries whose `topics:` /
        `related_entries:` scaffolding is byte-identical, appended concurrently.
        Those shared lines are what git anchors on."""
        def entry(time, title, eid):
            return (
                f"## 2026-07-19 {time} - {title}\n\n"
                f"```yaml\nentry_id: mse_{eid}\n"
                "topics:\n  - memory-trace\n  - ui-design\n"
                "related_entries:\n  - mse_zzzzzzzzzzzzzzzz\n```\n\n"
                f"### Decision\n\n- D: {title}\n- R: {title}\n\n"
            )

        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-19.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        base = entry("09:00", "Base", "a" * 16)
        target.write_text(base, encoding="utf-8")
        if gitattributes is not None:
            (cwd / ".gitattributes").write_text(gitattributes, encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        target.write_text(base + entry("11:33", "BranchOne", "c" * 16), encoding="utf-8")
        self._commit_all(cwd, "branch appends 11:33")
        self._git(cwd, "switch", "main")
        target.write_text(base + entry("12:02", "MainOne", "b" * 16), encoding="utf-8")
        self._commit_all(cwd, "main appends 12:02")
        return target

    def test_without_the_attribute_git_interleaves_the_conflict_dangerously(self):
        # Control, and the actual mechanism behind the 2026-07-19 corruption.
        # Git does not merge these silently - it does something worse: it
        # anchors on the byte-identical topics:/related_entries: scaffolding,
        # treats those lines as AGREED content outside the markers, and splits
        # one logical conflict into two interleaved regions. The result has
        # fewer closing fences than entries, so stripping the markers and
        # re-splitting on '##' headings - the obvious hand-resolution, and the
        # one that caused the incident - strands a fence and splices bodies.
        import subprocess

        cwd = self.make_project()
        target = self._false_anchor_branches(cwd)

        subprocess.run(
            ["git", "-C", str(cwd), "merge", "--no-ff", "--no-commit", "feature-merge"],
            capture_output=True, text=True,
        )
        text = target.read_text(encoding="utf-8")

        self.assertGreater(text.count("<<<<<<<"), 1, "the danger is interleaving: >1 conflict region")
        # The shared scaffolding escaped the markers entirely, so the two
        # entries now share a single metadata fence between them.
        both_headings = text.count("## 2026-07-19 11:33") and text.count("## 2026-07-19 12:02")
        self.assertTrue(both_headings, "both entries are present...")
        stripped = "\n".join(
            ln for ln in text.splitlines()
            if not ln.startswith(("<<<<<<<", "=======", ">>>>>>>"))
        )
        from memory_seed.core import check_entry_metadata_fences
        self.assertTrue(
            check_entry_metadata_fences(stripped),
            "...and naive marker-stripping yields the unclosed fence links check now catches",
        )

    def test_the_attribute_keeps_the_conflicted_file_structurally_intact(self):
        # With the guard, the same merge conflicts as a UNIT: git writes no
        # markers into the file at all, so no entry is ever left half-formed.
        # The structural merge is then the only way forward.
        import subprocess

        from memory_seed.core import check_entry_metadata_fences

        cwd = self.make_project()
        target = self._false_anchor_branches(cwd, gitattributes=self.NO_MERGE_ATTR)

        merged = subprocess.run(
            ["git", "-C", str(cwd), "merge", "--no-ff", "--no-commit", "feature-merge"],
            capture_output=True, text=True,
        )
        text = target.read_text(encoding="utf-8")

        self.assertNotEqual(merged.returncode, 0)
        self.assertEqual(text.count("<<<<<<<"), 0, "no markers spliced into the file")
        self.assertFalse(check_entry_metadata_fences(text), "every entry left well formed")

    def test_session_merge_branch_fails_closed_before_merge_on_modified_entry(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main", body="- Original.")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main", body="- Edited.")
        self._commit_all(cwd, "edit existing")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertFalse(result.committed)
        self.assertTrue(result.issues)
        self.assertIn("existing entry_id modified", result.issues[0])
        # Blocked at the fuse dry-run gate: the git merge must never have started.
        self.assertFalse(result.merge_in_progress)
        self.assertFalse((cwd / ".git" / "MERGE_HEAD").exists())

    def test_session_merge_branch_refuses_dirty_working_tree_naming_paths(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        self._write_grouped_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-merge")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")
        (cwd / "uncommitted.txt").write_text("dirty\n", encoding="utf-8")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertFalse(result.committed)
        self.assertTrue(result.issues)
        self.assertIn("working tree is not clean", result.issues[0])
        self.assertIn("uncommitted.txt", result.issues[0])
        self.assertFalse((cwd / ".git" / "MERGE_HEAD").exists())

    def test_session_merge_branch_stamps_memory_entry_trailers(self):
        # Approved trailer plan (2026-07-11): the merge commit carries one
        # Memory-Entry trailer per fused entry, below git's prepared merge
        # message, and find_trailer_commits resolves each entry to it. The
        # wider lowercase ids other agents emit (e.g. 20-hex codex ids) are
        # stamped too; base entries are never claimed.
        from memory_seed.core import find_trailer_commits

        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-12.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entries = [
            ("09:00", "Branch entry one", "mse_1111111111111111", "feature-merge"),
            ("10:00", "Branch entry two", "mse_3ca332874c2bce263fd2", "feature-merge"),
        ]
        target.write_text(self._grouped_session_text("2026-07-12", entries), encoding="utf-8")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertEqual(result.issues, [])
        self.assertTrue(result.committed)
        self.assertEqual(
            result.stamped_entries,
            ["mse_1111111111111111", "mse_3ca332874c2bce263fd2"],
        )
        message = self._git(cwd, "log", "-1", "--format=%B").stdout
        # Git's prepared message is preserved above the trailer block.
        self.assertTrue(message.startswith("Merge branch 'feature-merge'"))
        self.assertIn("Memory-Entry: mse_1111111111111111", message)
        self.assertIn("Memory-Entry: mse_3ca332874c2bce263fd2", message)
        # The base entry was never part of the fuse and is never claimed.
        self.assertNotIn("mse_0123456789abcdef", message)
        merge_sha = self._git(cwd, "rev-parse", "HEAD").stdout.strip()
        for entry_id in ("mse_1111111111111111", "mse_3ca332874c2bce263fd2"):
            hits = find_trailer_commits(cwd, entry_id)
            self.assertIsNotNone(hits)
            self.assertIn(merge_sha, [hit.split()[0] for hit in hits])

    def test_session_merge_branch_stamps_no_trailers_without_fuse_imports(self):
        # A merge whose branch touched no session files fuses nothing and must
        # leave git's prepared merge message untouched.
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        (cwd / "notes.txt").write_text("base\n", encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        (cwd / "notes.txt").write_text("branch change\n", encoding="utf-8")
        self._commit_all(cwd, "branch edit")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertEqual(result.issues, [])
        self.assertTrue(result.committed)
        self.assertEqual(result.stamped_entries, [])
        message = self._git(cwd, "log", "-1", "--format=%B").stdout
        self.assertNotIn("Memory-Entry:", message)

    def test_session_merge_branch_never_stamps_malformed_entry_ids(self):
        # A malformed id must not poison the trailer channel: the entry still
        # fuses, but no Memory-Entry line is written for it.
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-12.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entries = [
            ("09:00", "Good entry", "mse_1111111111111111", "feature-merge"),
            ("10:00", "Weird id entry", "mse_UPPER!!invalid", "feature-merge"),
        ]
        target.write_text(self._grouped_session_text("2026-07-12", entries), encoding="utf-8")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertTrue(result.committed)
        self.assertEqual(result.stamped_entries, ["mse_1111111111111111"])
        message = self._git(cwd, "log", "-1", "--format=%B").stdout
        self.assertIn("Memory-Entry: mse_1111111111111111", message)
        self.assertNotIn("mse_UPPER!!invalid", message)

    def test_session_merge_branch_dry_run_reports_plan_without_merging(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        self._write_grouped_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-merge")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge", dry_run=True)

        self.assertFalse(result.committed)
        self.assertEqual(result.issues, [])
        self.assertEqual(
            result.planned_entries,
            ["mse_1111111111111111 2026-07-11 09:00 -> .memory-seed/sessions/2026-07/2026-07-11.md"],
        )
        self.assertFalse((cwd / ".git" / "MERGE_HEAD").exists())
        self.assertFalse((cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-11.md").exists())
        self.assertEqual(self._git(cwd, "log", "--merges", "-1", "--format=%P").stdout.strip(), "")

    def test_session_prepare_pr_branch_commits_chronological_merge_on_task_branch(self):
        cwd = self.make_project()
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-12.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entry_a = ("09:00", "Base entry", "mse_aaaaaaaaaaaaaaaa", "main")
        entry_b = ("10:00", "Later main entry", "mse_bbbbbbbbbbbbbbbb", "main")
        entry_c = ("09:30", "Branch entry", "mse_cccccccccccccccc", "feature-pr")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a]), encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-pr")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_c]), encoding="utf-8")
        self._commit_all(cwd, "branch appends 09:30")
        self._git(cwd, "switch", "main")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_b]), encoding="utf-8")
        self._commit_all(cwd, "main appends 10:00")
        self._git(cwd, "switch", "feature-pr")

        result = session_prepare_pr_branch(cwd=cwd, branch="feature-pr", base_branch="main")

        self.assertEqual(result.issues, [])
        self.assertEqual(result.conflicts, [])
        self.assertTrue(result.ready)
        self.assertTrue(result.changed)
        self.assertIsNotNone(result.prep_commit)
        text = target.read_text(encoding="utf-8")
        pos_a = text.find("## 2026-07-12 09:00")
        pos_c = text.find("## 2026-07-12 09:30")
        pos_b = text.find("## 2026-07-12 10:00")
        self.assertTrue(0 <= pos_a < pos_c < pos_b, f"order wrong: a={pos_a} c={pos_c} b={pos_b}")
        self.assertNotIn("<<<<<<<", text)
        message = self._git(cwd, "log", "-1", "--format=%B").stdout
        self.assertTrue(message.startswith("Merge branch 'main' into feature-pr"))
        self.assertIn("Memory-Entry: mse_cccccccccccccccc", message)

    def test_session_prepare_pr_branch_refuses_dirty_tree_naming_paths(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-pr")
        (cwd / "dirty.txt").write_text("dirty\n", encoding="utf-8")

        result = session_prepare_pr_branch(cwd=cwd, branch="feature-pr", base_branch="main")

        self.assertFalse(result.ready)
        self.assertTrue(result.issues)
        self.assertIn("working tree is not clean", result.issues[0])
        self.assertIn("dirty.txt", result.issues[0])
        self.assertFalse((cwd / ".git" / "MERGE_HEAD").exists())

    def test_session_prepare_pr_branch_prefers_origin_main_when_local_main_is_stale(self):
        cwd = self.make_project()
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-12.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entry_a = ("09:00", "Base entry", "mse_aaaaaaaaaaaaaaaa", "main")
        entry_b = ("10:00", "Origin main entry", "mse_bbbbbbbbbbbbbbbb", "main")
        entry_c = ("09:30", "Branch entry", "mse_cccccccccccccccc", "feature-pr")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a]), encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        base_sha = self._git(cwd, "rev-parse", "HEAD").stdout.strip()
        self._git(cwd, "switch", "-c", "feature-pr")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_c]), encoding="utf-8")
        self._commit_all(cwd, "branch appends 09:30")
        self._git(cwd, "switch", "main")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_b]), encoding="utf-8")
        self._commit_all(cwd, "main appends 10:00")
        origin_main_sha = self._git(cwd, "rev-parse", "HEAD").stdout.strip()
        # Deliberately stale local main while origin/main stays newer.
        self._git(cwd, "switch", "feature-pr")
        self._git(cwd, "update-ref", "refs/heads/main", base_sha)
        self._git(cwd, "update-ref", "refs/remotes/origin/main", origin_main_sha)
        self._git(cwd, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")

        result = session_prepare_pr_branch(cwd=cwd, branch="feature-pr")

        self.assertEqual(result.issues, [])
        self.assertTrue(result.ready)
        text = target.read_text(encoding="utf-8")
        self.assertIn("mse_bbbbbbbbbbbbbbbb", text)
        pos_c = text.find("## 2026-07-12 09:30")
        pos_b = text.find("## 2026-07-12 10:00")
        self.assertTrue(0 <= pos_c < pos_b, f"origin/main was not used: c={pos_c} b={pos_b}")

    def test_session_prepare_pr_branch_leaves_non_session_conflicts_in_progress(self):
        cwd = self.make_project()
        (cwd / "notes.txt").write_text("base\n", encoding="utf-8")
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-pr")
        (cwd / "notes.txt").write_text("branch change\n", encoding="utf-8")
        self._commit_all(cwd, "branch edit")
        self._git(cwd, "switch", "main")
        (cwd / "notes.txt").write_text("main change\n", encoding="utf-8")
        self._commit_all(cwd, "main edit")
        self._git(cwd, "switch", "feature-pr")

        result = session_prepare_pr_branch(cwd=cwd, branch="feature-pr", base_branch="main")

        self.assertFalse(result.ready)
        self.assertTrue(result.merge_in_progress)
        self.assertEqual(result.conflicts, ["notes.txt"])
        self.assertTrue((cwd / ".git" / "MERGE_HEAD").exists())

    def test_session_open_pr_dry_run_returns_pr_body_plan(self):
        import unittest.mock

        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-pr")
        self._write_grouped_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-pr")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "remote", "add", "origin", "https://example.com/owner/repo.git")

        def fake_gh(_root, args):
            if tuple(args) == ("--version",):
                return 0, "gh version 2.0.0", ""
            if tuple(args) == ("auth", "status"):
                return 0, "", ""
            self.fail(f"unexpected gh call: {args!r}")

        with unittest.mock.patch("memory_seed.core._gh_text", side_effect=fake_gh):
            result = session_open_pr(cwd=cwd, branch="feature-pr", base_branch="main", dry_run=True)

        self.assertEqual(result.issues, [])
        self.assertFalse(result.opened)
        self.assertTrue(result.dry_run)
        self.assertEqual(result.pr_title, "Integrate feature-pr into main")
        self.assertIsNotNone(result.pr_body)
        self.assertIn("memory-seed session prepare-pr --branch feature-pr --base-branch main", result.pr_body)
        self.assertIn("mse_1111111111111111", result.pr_body)
        self.assertFalse(result.pushed)
        self.assertFalse(result.pr_created)
        self.assertEqual(self._git(cwd, "status", "--short").stdout.strip(), "")

    def test_session_open_pr_refreshes_remote_base_before_preparing_and_pushing(self):
        import subprocess
        import unittest.mock

        cwd = self.make_project()
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-12.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entry_a = ("09:00", "Base entry", "mse_aaaaaaaaaaaaaaaa", "main")
        entry_b = ("10:00", "Fresh remote entry", "mse_bbbbbbbbbbbbbbbb", "main")
        entry_c = ("09:30", "Branch entry", "mse_cccccccccccccccc", "feature-pr")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a]), encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        base_sha = self._git(cwd, "rev-parse", "HEAD").stdout.strip()

        remote = self.make_project() / "origin.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True, capture_output=True, text=True)
        self._git(cwd, "remote", "add", "origin", str(remote))
        self._git(cwd, "update-ref", "refs/remotes/origin/main", base_sha)

        self._git(cwd, "switch", "-q", "-c", "feature-pr")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_c]), encoding="utf-8")
        self._commit_all(cwd, "branch appends 09:30")

        self._git(cwd, "switch", "-q", "main")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_b]), encoding="utf-8")
        self._commit_all(cwd, "fresh remote main")
        fresh_remote_sha = self._git(cwd, "rev-parse", "HEAD").stdout.strip()
        self._git(cwd, "switch", "-q", "feature-pr")
        self._git(cwd, "update-ref", "refs/heads/main", base_sha)

        from memory_seed import core as core_module

        original_git_text = core_module._git_text
        git_commands = []

        def fake_git(root, args):
            git_commands.append(tuple(args))
            if tuple(args) == (
                "fetch",
                "--no-tags",
                "origin",
                "refs/heads/main:refs/remotes/origin/main",
            ):
                self._git(cwd, "update-ref", "refs/remotes/origin/main", fresh_remote_sha)
                return 0, ""
            if tuple(args) == ("push", "--set-upstream", "origin", "feature-pr"):
                return 0, ""
            return original_git_text(root, args)

        def fake_gh(_root, args):
            if tuple(args) == ("--version",):
                return 0, "gh version 2.0.0", ""
            if tuple(args) == ("auth", "status"):
                return 0, "", ""
            if tuple(args[:2]) == ("pr", "create"):
                return 0, "https://example.test/owner/repo/pull/1", ""
            self.fail(f"unexpected gh call: {args!r}")

        with unittest.mock.patch("memory_seed.core._git_text", side_effect=fake_git), unittest.mock.patch(
            "memory_seed.core._gh_text", side_effect=fake_gh
        ):
            result = session_open_pr(cwd=cwd, branch="feature-pr", base_branch="main")

        self.assertTrue(result.opened)
        self.assertTrue(result.pushed)
        self.assertTrue(result.pr_created)
        self.assertEqual(result.issues, [])
        pushed_text = target.read_text(encoding="utf-8")
        pos_c = pushed_text.find("## 2026-07-12 09:30")
        pos_b = pushed_text.find("## 2026-07-12 10:00")
        self.assertTrue(0 <= pos_c < pos_b, "fresh origin/main was not prepared before push")
        self.assertIn(("fetch", "--no-tags", "origin", "refs/heads/main:refs/remotes/origin/main"), git_commands)
        self.assertIn(("push", "--set-upstream", "origin", "feature-pr"), git_commands)
        self.assertFalse(any("--force" in args or "-f" in args for args in git_commands))

    def test_session_open_pr_refuses_failed_base_refresh_before_branch_modification(self):
        import unittest.mock

        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-q", "-c", "feature-pr")
        self._write_grouped_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-pr")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "remote", "add", "origin", str(cwd / "missing-origin.git"))
        before = self._git(cwd, "rev-parse", "HEAD").stdout.strip()

        def fake_gh(_root, args):
            if tuple(args) == ("--version",):
                return 0, "gh version 2.0.0", ""
            if tuple(args) == ("auth", "status"):
                return 0, "", ""
            self.fail(f"unexpected gh call: {args!r}")

        with unittest.mock.patch("memory_seed.core._gh_text", side_effect=fake_gh):
            result = session_open_pr(cwd=cwd, branch="feature-pr", base_branch="main")

        self.assertFalse(result.opened)
        self.assertFalse(result.pushed)
        self.assertTrue(result.issues)
        self.assertIn("could not refresh origin/main", result.issues[0])
        self.assertEqual(before, self._git(cwd, "rev-parse", "HEAD").stdout.strip())
        self.assertEqual(self._git(cwd, "status", "--short").stdout.strip(), "")

    def test_session_open_pr_refuses_unauthenticated_gh_before_modifying_branch(self):
        import unittest.mock

        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-pr")
        self._write_grouped_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-pr")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "remote", "add", "origin", "https://example.com/owner/repo.git")
        before = self._git(cwd, "rev-parse", "HEAD").stdout.strip()

        def fake_gh(_root, args):
            if tuple(args) == ("--version",):
                return 0, "gh version 2.0.0", ""
            if tuple(args) == ("auth", "status"):
                return 1, "", "not logged in"
            self.fail(f"unexpected gh call: {args!r}")

        with unittest.mock.patch("memory_seed.core._gh_text", side_effect=fake_gh):
            result = session_open_pr(cwd=cwd, branch="feature-pr", base_branch="main", dry_run=False)

        self.assertFalse(result.opened)
        self.assertTrue(result.issues)
        self.assertIn("gh is not authenticated", result.issues[0])
        self.assertEqual(before, self._git(cwd, "rev-parse", "HEAD").stdout.strip())
        self.assertEqual(self._git(cwd, "status", "--short").stdout.strip(), "")

    def test_compact_returns_headings_from_recent_sessions(self):
        cwd = self.make_project()
        today = __import__("datetime").date.today().isoformat()
        self._make_sessions(cwd, {
            f"{today}.md": "## First heading\n\nSome text.\n\n## Second heading\n\nMore text.\n",
        })

        result = compact_sessions(cwd=cwd, days=7)

        self.assertEqual(result.sessions_scanned, [f"{today}.md"])
        self.assertEqual(result.headings[today], ["First heading", "Second heading"])
        self.assertIn("Some text.", result.full_text)
        self.assertEqual(result.date_range, (today, today))

    def test_compact_respects_day_filter(self):
        cwd = self.make_project()
        self._make_sessions(cwd, {
            "2020-01-01.md": "## Old entry\n\nOld text.\n",
            "2099-12-31.md": "## Future entry\n\nFuture text.\n",
        })

        result = compact_sessions(cwd=cwd, days=7)

        self.assertEqual(result.sessions_scanned, ["2099-12-31.md"])
        self.assertNotIn("Old text.", result.full_text)

    def test_compact_all_includes_every_session(self):
        cwd = self.make_project()
        self._make_sessions(cwd, {
            "2020-01-01.md": "## Old entry\n",
            "2099-12-31.md": "## Future entry\n",
        })

        result = compact_sessions(cwd=cwd, scan_all=True)

        self.assertEqual(len(result.sessions_scanned), 2)
        self.assertIn("2020-01-01.md", result.sessions_scanned)
        self.assertIn("2099-12-31.md", result.sessions_scanned)

    def test_compact_all_includes_legacy_and_per_user_sessions(self):
        cwd = self.make_project()
        self._make_sessions(cwd, {
            "2026-06-20.md": "## Legacy entry\n\nLegacy text.\n",
            "2026-06-21/jean.md": "## Jean entry\n\nJean text.\n",
        })

        result = compact_sessions(cwd=cwd, scan_all=True)

        self.assertEqual(result.sessions_scanned, ["2026-06-20.md", "2026-06-21/jean.md"])
        self.assertEqual(result.headings["2026-06-20"], ["Legacy entry"])
        self.assertEqual(result.headings["2026-06-21/jean.md"], ["Jean entry"])
        self.assertIn("Legacy text.", result.full_text)
        self.assertIn("Jean text.", result.full_text)
        self.assertEqual(result.date_range, ("2026-06-20", "2026-06-21"))

    def test_compact_empty_sessions_returns_empty_result(self):
        cwd = self.make_project()

        result = compact_sessions(cwd=cwd)

        self.assertEqual(result.sessions_scanned, [])
        self.assertEqual(result.headings, {})
        self.assertEqual(result.full_text, "")
        self.assertIsNone(result.date_range)

    def test_compact_ignores_non_date_filenames(self):
        cwd = self.make_project()
        today = __import__("datetime").date.today().isoformat()
        self._make_sessions(cwd, {
            f"{today}.md": "## Valid\n",
            "notes.md": "## Should be ignored\n",
            "readme.txt": "not a session",
        })

        result = compact_sessions(cwd=cwd, days=7)

        self.assertEqual(result.sessions_scanned, [f"{today}.md"])
        self.assertNotIn("Should be ignored", result.full_text)


class HookMergeTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-hooks-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_init_installs_retrieval_hooks_for_all_agents(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        claude = json.loads((cwd / ".claude" / "settings.json").read_text())
        self.assertIn("UserPromptSubmit", claude["hooks"])
        self.assertIn(
            "memory-retrieval-check.py",
            claude["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"],
        )

        codex = json.loads((cwd / ".codex" / "hooks.json").read_text())
        self.assertIn("UserPromptSubmit", codex["hooks"])

        # Gemini's prompt-submit event is BeforeAgent; it has no UserPromptSubmit.
        gemini = json.loads((cwd / ".gemini" / "settings.json").read_text())
        self.assertIn("BeforeAgent", gemini["hooks"])
        self.assertNotIn("UserPromptSubmit", gemini["hooks"])
        self.assertIn(
            "memory-retrieval-check.py",
            gemini["hooks"]["BeforeAgent"][0]["hooks"][0]["command"],
        )

        cursor = json.loads((cwd / ".cursor" / "hooks.json").read_text())
        self.assertIn("sessionStart", cursor["hooks"])
        self.assertIn(
            "memory-retrieval-check.py",
            cursor["hooks"]["sessionStart"][0]["command"],
        )

    def test_gemini_session_log_hook_uses_afteragent_not_stop(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        gemini = json.loads((cwd / ".gemini" / "settings.json").read_text())
        self.assertIn("AfterAgent", gemini["hooks"])
        self.assertNotIn("Stop", gemini["hooks"])
        self.assertIn(
            "session-log-check.py",
            gemini["hooks"]["AfterAgent"][0]["hooks"][0]["command"],
        )

    def test_strip_gemini_dead_hooks_removes_ours_preserves_foreign(self):
        import json
        from memory_seed.core import _strip_gemini_dead_hooks

        cwd = self.make_project()
        settings = cwd / ".gemini" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            json.dumps({
                "hooks": {
                    "Stop": [
                        {"hooks": [{"type": "command", "command": "python3 .memory-seed/hooks/session-log-check.py --gemini"}]},
                        {"hooks": [{"type": "command", "command": "some-foreign-tool"}]},
                    ],
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": "python3 .memory-seed/hooks/memory-retrieval-check.py --gemini"}]},
                    ],
                }
            }),
            encoding="utf-8",
        )

        self.assertTrue(_strip_gemini_dead_hooks(cwd))
        data = json.loads(settings.read_text())
        # Our UserPromptSubmit entry was the only one -> event removed entirely.
        self.assertNotIn("UserPromptSubmit", data["hooks"])
        # Foreign Stop entry preserved; our Stop entry removed.
        stop_cmds = [h["command"] for g in data["hooks"]["Stop"] for h in g["hooks"]]
        self.assertEqual(stop_cmds, ["some-foreign-tool"])
        # Idempotent: nothing of ours left to strip.
        self.assertFalse(_strip_gemini_dead_hooks(cwd))

    def test_retrieval_hook_merges_are_idempotent(self):
        from memory_seed.core import (
            _merge_claude_retrieval_hook,
            _merge_cursor_retrieval_hook,
        )

        cwd = self.make_project()
        self.assertTrue(_merge_claude_retrieval_hook(cwd))
        self.assertFalse(_merge_claude_retrieval_hook(cwd))
        self.assertTrue(_merge_cursor_retrieval_hook(cwd))
        self.assertFalse(_merge_cursor_retrieval_hook(cwd))

    def test_grouped_hook_updates_stale_command(self):
        import json
        from memory_seed.core import _merge_grouped_hook

        cwd = self.make_project()
        config = cwd / ".claude" / "settings.json"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            json.dumps({
                "hooks": {
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": "python3 .memory-seed/hooks/memory-retrieval-check.py --old-flag"}]}
                    ]
                }
            }),
            encoding="utf-8",
        )

        new_command = "python3 .memory-seed/hooks/memory-retrieval-check.py"
        result = _merge_grouped_hook(config, "UserPromptSubmit", new_command, "memory-retrieval-check.py")
        self.assertTrue(result)

        data = json.loads(config.read_text())
        commands = [
            h["command"]
            for g in data["hooks"]["UserPromptSubmit"]
            for h in g.get("hooks", [])
        ]
        self.assertEqual(commands, [new_command])  # updated in place, no duplicate

    def test_cursor_event_hook_updates_stale_command(self):
        import json
        from memory_seed.core import _merge_cursor_event_hook

        cwd = self.make_project()
        config = cwd / ".cursor" / "hooks.json"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            json.dumps({
                "version": 1,
                "hooks": {
                    "sessionStart": [
                        {"command": "python3 .memory-seed/hooks/memory-retrieval-check.py --cursor --old-flag"}
                    ]
                }
            }),
            encoding="utf-8",
        )

        new_command = "python3 .memory-seed/hooks/memory-retrieval-check.py --cursor"
        result = _merge_cursor_event_hook(config, "sessionStart", new_command, "memory-retrieval-check.py")
        self.assertTrue(result)

        data = json.loads(config.read_text())
        commands = [e["command"] for e in data["hooks"]["sessionStart"]]
        self.assertEqual(commands, [new_command])  # updated in place, no duplicate

    def test_init_installs_session_start_hooks_for_all_agents(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        claude = json.loads((cwd / ".claude" / "settings.json").read_text())
        self.assertIn("SessionStart", claude["hooks"])
        self.assertIn(
            "session-start-context.py",
            claude["hooks"]["SessionStart"][0]["hooks"][0]["command"],
        )

        codex = json.loads((cwd / ".codex" / "hooks.json").read_text())
        self.assertIn("SessionStart", codex["hooks"])
        self.assertIn(
            "--codex",
            codex["hooks"]["SessionStart"][0]["hooks"][0]["command"],
        )

        gemini = json.loads((cwd / ".gemini" / "settings.json").read_text())
        self.assertIn("SessionStart", gemini["hooks"])

        # Cursor fires both reminders at sessionStart; both scripts must be present.
        cursor = json.loads((cwd / ".cursor" / "hooks.json").read_text())
        cursor_cmds = [e["command"] for e in cursor["hooks"]["sessionStart"]]
        self.assertTrue(any("session-start-context.py" in c for c in cursor_cmds))
        self.assertTrue(any("memory-retrieval-check.py" in c for c in cursor_cmds))

    def test_init_installs_copilot_mcp_and_prompt_hook(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        mcp = json.loads((cwd / ".github" / "mcp.json").read_text())
        server = mcp["mcpServers"]["memory-seed"]
        self.assertEqual(server["type"], "stdio")
        self.assertEqual(server["command"], "uvx")
        self.assertIn("memory-seed-mcp", server["args"])
        self.assertEqual(server["tools"], ["*"])

        hook = json.loads((cwd / ".github" / "hooks" / "memory-seed.json").read_text())
        self.assertEqual(hook["version"], 1)
        entry = hook["hooks"]["sessionStart"][0]
        self.assertEqual(entry["type"], "prompt")
        self.assertIn("AGENTS.md", entry["prompt"])
        self.assertIn("five newest applicable", entry["prompt"])
        self.assertIn("Do NOT use memory_search", entry["prompt"])
        self.assertIn(".memory-seed/sessions/", entry["prompt"])

    def test_copilot_merges_are_idempotent(self):
        from memory_seed.core import _merge_copilot_mcp, _merge_copilot_startup_hook

        cwd = self.make_project()
        self.assertTrue(_merge_copilot_mcp(cwd))
        self.assertFalse(_merge_copilot_mcp(cwd))
        self.assertTrue(_merge_copilot_startup_hook(cwd))
        self.assertFalse(_merge_copilot_startup_hook(cwd))

    def test_copilot_mcp_preserves_foreign_server(self):
        import json
        from memory_seed.core import _merge_copilot_mcp

        cwd = self.make_project()
        mcp_path = cwd / ".github" / "mcp.json"
        mcp_path.parent.mkdir(parents=True, exist_ok=True)
        mcp_path.write_text(
            json.dumps({"mcpServers": {"memory-seed": {"command": "other-tool"}}}),
            encoding="utf-8",
        )

        self.assertFalse(_merge_copilot_mcp(cwd))  # foreign entry left untouched
        data = json.loads(mcp_path.read_text())
        self.assertEqual(data["mcpServers"]["memory-seed"]["command"], "other-tool")

    def test_init_installs_vscode_mcp_under_servers_key(self):
        import json
        from memory_seed.core import _merge_vscode_mcp

        cwd = self.make_project()
        init_project(cwd=cwd)

        mcp = json.loads((cwd / ".vscode" / "mcp.json").read_text())
        # VS Code uses the "servers" key, not "mcpServers".
        self.assertIn("servers", mcp)
        self.assertNotIn("mcpServers", mcp)
        server = mcp["servers"]["memory-seed"]
        self.assertEqual(server["type"], "stdio")
        self.assertEqual(server["command"], "uvx")
        self.assertIn("memory-seed-mcp", server["args"])
        # Idempotent.
        self.assertFalse(_merge_vscode_mcp(cwd))

    def test_init_installs_copilot_instructions_router(self):
        cwd = self.make_project()
        init_project(cwd=cwd)

        router = cwd / ".github" / "copilot-instructions.md"
        self.assertTrue(router.exists())
        text = router.read_text(encoding="utf-8")
        self.assertIn("GitHub Copilot Instructions", text)
        self.assertIn("AGENTS.md", text)


class SessionLogOrderingHookTests(unittest.TestCase):
    SCRIPT = Path("memory_seed/seed/.memory-seed/hooks/session-log-check.py").resolve()

    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-order-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        (path / ".memory-seed" / "sessions").mkdir(parents=True)
        return path

    def _flat_target(self, cwd, day):
        path = cwd / ".memory-seed" / "sessions" / day[:7] / f"{day}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _user_target(self, cwd, day, user):
        path = cwd / ".memory-seed" / "sessions" / day[:7] / day / f"{user}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _write_two_participants(self, cwd):
        (cwd / ".memory-seed" / "project.yaml").write_text(
            "participants:\n"
            "  - slug: jean\n"
            "    initials: JN\n"
            "  - slug: amina\n"
            "    initials: AM\n",
            encoding="utf-8",
        )

    def _run(self, cwd):
        import subprocess
        import sys

        return subprocess.run(
            [sys.executable, str(self.SCRIPT)],
            cwd=cwd,
            capture_output=True,
            text=True,
        ).stdout

    def _run_with_env(self, cwd, extra_env):
        import os
        import subprocess
        import sys

        env = os.environ.copy()
        env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(self.SCRIPT)],
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
        ).stdout

    def test_out_of_order_entries_trigger_warning(self):
        import datetime

        cwd = self.make_project()
        today = datetime.date.today().isoformat()
        self._flat_target(cwd, today).write_text(
            f"## {today} 02:00 - later\n\ntext\n\n## {today} 01:45 - earlier\n\ntext\n",
            encoding="utf-8",
        )
        self.assertIn("ORDER WARNING", self._run(cwd))

    def test_in_order_entries_do_not_trigger_order_warning(self):
        import datetime

        cwd = self.make_project()
        today = datetime.date.today().isoformat()
        self._flat_target(cwd, today).write_text(
            f"## {today} 01:45 - earlier\n\ntext\n\n## {today} 02:00 - later\n\ntext\n",
            encoding="utf-8",
        )
        self.assertNotIn("ORDER WARNING", self._run(cwd))

    def test_staleness_fires_when_no_session_file(self):
        cwd = self.make_project()
        out = self._run(cwd)
        self.assertIn("SESSION LOG REMINDER", out)

    def test_staleness_fires_when_last_entry_is_old(self):
        import datetime

        cwd = self.make_project()
        # Use a timestamp 30 min in the past (> the 15 min staleness threshold)
        # relative to the actual clock, so the test is not brittle near midnight
        # where a hardcoded early-morning time would read as a future entry.
        old = datetime.datetime.now() - datetime.timedelta(minutes=30)
        day = old.strftime("%Y-%m-%d")
        stamp = old.strftime("%H:%M")
        self._flat_target(cwd, day).write_text(
            f"## {day} {stamp} - old entry\n\ntext\n",
            encoding="utf-8",
        )
        self.assertIn("SESSION LOG REMINDER", self._run(cwd))

    def test_staleness_silent_when_recent_entry(self):
        import datetime

        cwd = self.make_project()
        now = datetime.datetime.now()
        today = now.strftime("%Y-%m-%d")
        recent_time = now.strftime("%H:%M")
        self._flat_target(cwd, today).write_text(
            f"## {today} {recent_time} - recent entry\n\ntext\n",
            encoding="utf-8",
        )
        self.assertNotIn("SESSION LOG REMINDER", self._run(cwd))

    def test_staleness_not_defeated_by_file_mtime(self):
        import datetime
        import os

        cwd = self.make_project()
        old = datetime.datetime.now() - datetime.timedelta(minutes=30)
        day = old.strftime("%Y-%m-%d")
        stamp = old.strftime("%H:%M")
        session_file = self._flat_target(cwd, day)
        session_file.write_text(
            f"## {day} {stamp} - old entry\n\ntext\n",
            encoding="utf-8",
        )
        # Touch the file to update mtime to now — simulating what git commit does.
        os.utime(session_file, None)
        # Staleness check should still fire because the entry heading is old.
        self.assertIn("SESSION LOG REMINDER", self._run(cwd))

    def test_user_scoped_staleness_ignores_other_users_recent_entry(self):
        import datetime

        cwd = self.make_project()
        self._write_two_participants(cwd)
        now = datetime.datetime.now()
        today = now.strftime("%Y-%m-%d")
        self._user_target(cwd, today, "amina").write_text(
            f"## {today} {now.strftime('%H:%M')} - Amina recent\n\ntext\n",
            encoding="utf-8",
        )

        out = self._run_with_env(cwd, {"MEMORY_SEED_USER": "jean"})

        self.assertIn("SESSION LOG REMINDER", out)
        self.assertIn(f".memory-seed/sessions/{today[:7]}/{today}/jean.md", out)
        self.assertNotIn(f".memory-seed/sessions/{today}.md", out)

    def test_user_scoped_order_warning_checks_only_selected_file(self):
        import datetime

        cwd = self.make_project()
        self._write_two_participants(cwd)
        today = datetime.date.today().isoformat()
        self._user_target(cwd, today, "jean").write_text(
            f"## {today} 02:00 - later\n\ntext\n\n## {today} 01:45 - earlier\n\ntext\n",
            encoding="utf-8",
        )
        self._user_target(cwd, today, "amina").write_text(
            f"## {today} 01:00 - amina\n\ntext\n",
            encoding="utf-8",
        )

        out = self._run_with_env(cwd, {"MEMORY_SEED_USER": "jean"})

        self.assertIn("ORDER WARNING", out)
        self.assertIn(f".memory-seed/sessions/{today[:7]}/{today}/jean.md", out)

    def _write_stale_entry(self, cwd, minutes_ago=30):
        import datetime

        old = datetime.datetime.now() - datetime.timedelta(minutes=minutes_ago)
        day = old.strftime("%Y-%m-%d")
        stamp = old.strftime("%H:%M")
        self._flat_target(cwd, day).write_text(
            f"## {day} {stamp} - old entry\n\ntext\n",
            encoding="utf-8",
        )

    def test_first_stale_check_uses_base_wording_not_escalated(self):
        cwd = self.make_project()
        self._write_stale_entry(cwd)

        out = self._run(cwd)

        self.assertIn("SESSION LOG REMINDER", out)
        self.assertNotIn("repeated", out)

    def test_second_consecutive_stale_check_escalates_wording(self):
        cwd = self.make_project()
        self._write_stale_entry(cwd)

        self._run(cwd)
        out = self._run(cwd)

        self.assertIn("SESSION LOG REMINDER (repeated - 2 checks in a row", out)
        self.assertIn("discipline failure", out)

    def test_escalation_count_keeps_climbing_across_repeated_misses(self):
        cwd = self.make_project()
        self._write_stale_entry(cwd)

        self._run(cwd)
        self._run(cwd)
        out = self._run(cwd)

        self.assertIn("3 checks in a row", out)

    def test_escalation_resets_once_a_new_entry_is_logged(self):
        import datetime

        cwd = self.make_project()
        self._write_stale_entry(cwd)
        self._run(cwd)
        self._run(cwd)

        # Simulate the agent complying: append a fresh entry before the next check.
        now = datetime.datetime.now()
        today = now.strftime("%Y-%m-%d")
        target = self._flat_target(cwd, today)
        existing = target.read_text(encoding="utf-8") if target.exists() else ""
        target.write_text(
            existing + f"\n## {today} {now.strftime('%H:%M')} - caught up\n\ntext\n",
            encoding="utf-8",
        )

        out = self._run(cwd)

        self.assertEqual(out.strip(), "")

    def test_state_file_written_under_memory_seed_directory(self):
        import json

        cwd = self.make_project()
        self._write_stale_entry(cwd)

        self._run(cwd)

        state_path = cwd / ".memory-seed" / ".session-log-check-state"
        self.assertTrue(state_path.exists())
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["consecutive_misses"], 1)

    def test_corrupt_state_file_fails_open(self):
        cwd = self.make_project()
        self._write_stale_entry(cwd)
        (cwd / ".memory-seed" / ".session-log-check-state").write_text(
            "not valid json {{{", encoding="utf-8"
        )

        out = self._run(cwd)

        self.assertIn("SESSION LOG REMINDER", out)
        self.assertNotIn("repeated", out)


class McpMergeTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-mcp-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_init_installs_mcp_for_claude(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        # Claude Code reads project-scope MCP servers from .mcp.json, not settings.json.
        data = json.loads((cwd / ".mcp.json").read_text())
        self.assertIn("memory-seed", data["mcpServers"])
        entry = data["mcpServers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])
        self.assertNotIn("type", entry)

        # The dead settings.json mcpServers block must not be created.
        settings = json.loads((cwd / ".claude" / "settings.json").read_text())
        self.assertNotIn("mcpServers", settings)

    def test_init_installs_mcp_for_cursor(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        data = json.loads((cwd / ".cursor" / "mcp.json").read_text())
        self.assertIn("memory-seed", data["mcpServers"])
        entry = data["mcpServers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])
        self.assertNotIn("type", entry)

    def test_init_installs_mcp_for_gemini(self):
        import json

        cwd = self.make_project()
        init_project(cwd=cwd)

        data = json.loads((cwd / ".gemini" / "settings.json").read_text())
        self.assertIn("memory-seed", data["mcpServers"])
        entry = data["mcpServers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])

    def test_mcp_merges_are_idempotent(self):
        from memory_seed.core import (
            _merge_claude_mcp,
            _merge_cursor_mcp,
            _merge_gemini_mcp,
            _merge_codex_mcp,
        )

        cwd = self.make_project()
        self.assertTrue(_merge_claude_mcp(cwd))
        self.assertFalse(_merge_claude_mcp(cwd))
        self.assertTrue(_merge_cursor_mcp(cwd))
        self.assertFalse(_merge_cursor_mcp(cwd))
        self.assertTrue(_merge_gemini_mcp(cwd))
        self.assertFalse(_merge_gemini_mcp(cwd))
        self.assertTrue(_merge_codex_mcp(cwd))
        self.assertFalse(_merge_codex_mcp(cwd))

    def test_mcp_merge_updates_stale_args(self):
        import json

        cwd = self.make_project()
        mcp_path = cwd / ".mcp.json"
        # Legacy bare-command form (pre-uvx) under our key must migrate forward.
        mcp_path.write_text(
            json.dumps({"mcpServers": {"memory-seed": {"command": "memory-seed-mcp", "args": ["--old"]}}}),
            encoding="utf-8",
        )

        from memory_seed.core import _merge_claude_mcp
        result = _merge_claude_mcp(cwd)
        self.assertTrue(result)

        data = json.loads(mcp_path.read_text())
        entry = data["mcpServers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])

    def test_mcp_merge_preserves_unrelated_mcp_server(self):
        import json

        cwd = self.make_project()
        mcp_path = cwd / ".mcp.json"
        mcp_path.write_text(
            json.dumps({"mcpServers": {"other-server": {"command": "other-cmd", "args": []}}}),
            encoding="utf-8",
        )

        from memory_seed.core import _merge_claude_mcp
        _merge_claude_mcp(cwd)

        data = json.loads(mcp_path.read_text())
        self.assertIn("other-server", data["mcpServers"])
        self.assertEqual(data["mcpServers"]["other-server"]["command"], "other-cmd")
        self.assertIn("memory-seed", data["mcpServers"])

    def test_mcp_merge_preserves_foreign_server_on_our_key(self):
        # Distinct from test_mcp_merge_preserves_unrelated_mcp_server above: here a
        # *foreign* server squats memory-seed's own key, not an unrelated key. The
        # is_ours guard must leave it untouched rather than overwriting it -
        # _merge_vscode_mcp is deliberately not covered here (different container
        # key, "servers" not "mcpServers"; copilot/codex already prove the pattern
        # generalizes via their own dedicated tests).
        import json

        from memory_seed.core import _merge_claude_mcp, _merge_cursor_mcp, _merge_gemini_mcp

        cases = [
            (_merge_claude_mcp, Path(".mcp.json")),
            (_merge_cursor_mcp, Path(".cursor/mcp.json")),
            (_merge_gemini_mcp, Path(".gemini/settings.json")),
        ]
        for merge_fn, rel_path in cases:
            with self.subTest(fn=merge_fn.__name__):
                cwd = self.make_project()
                mcp_path = cwd / rel_path
                mcp_path.parent.mkdir(parents=True, exist_ok=True)
                mcp_path.write_text(
                    json.dumps({"mcpServers": {"memory-seed": {"command": "some-other-server", "args": []}}}),
                    encoding="utf-8",
                )

                self.assertFalse(merge_fn(cwd))

                data = json.loads(mcp_path.read_text())
                self.assertEqual(data["mcpServers"]["memory-seed"]["command"], "some-other-server")

    def test_strip_removes_legacy_claude_settings_mcp(self):
        import json

        cwd = self.make_project()
        settings = cwd / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        # A project seeded by 2.2.0-2.3.0: dead mcpServers block alongside a real hook.
        settings.write_text(
            json.dumps(
                {
                    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "keep-me"}]}]},
                    "mcpServers": {
                        "memory-seed": {
                            "command": "uvx",
                            "args": ["--from", "memory-seed", "memory-seed-mcp", "--stdio"],
                            "type": "stdio",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        from memory_seed.core import _strip_claude_settings_mcp
        self.assertTrue(_strip_claude_settings_mcp(cwd))

        data = json.loads(settings.read_text())
        self.assertNotIn("mcpServers", data)  # dead block removed, empty parent pruned
        self.assertEqual(data["hooks"]["Stop"][0]["hooks"][0]["command"], "keep-me")  # rest preserved
        self.assertFalse(_strip_claude_settings_mcp(cwd))  # idempotent

    def test_strip_preserves_foreign_settings_mcp(self):
        import json

        cwd = self.make_project()
        settings = cwd / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        # A different server squatting our key must not be deleted.
        settings.write_text(
            json.dumps({"mcpServers": {"memory-seed": {"command": "some-other-server", "args": []}}}),
            encoding="utf-8",
        )

        from memory_seed.core import _strip_claude_settings_mcp
        self.assertFalse(_strip_claude_settings_mcp(cwd))
        data = json.loads(settings.read_text())
        self.assertEqual(data["mcpServers"]["memory-seed"]["command"], "some-other-server")

    def test_gemini_mcp_merge_preserves_existing_hooks(self):
        import json

        cwd = self.make_project()
        gemini_path = cwd / ".gemini" / "settings.json"
        gemini_path.parent.mkdir(parents=True, exist_ok=True)
        gemini_path.write_text(
            json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "existing"}]}]}}),
            encoding="utf-8",
        )

        from memory_seed.core import _merge_gemini_mcp
        _merge_gemini_mcp(cwd)

        data = json.loads(gemini_path.read_text())
        self.assertIn("memory-seed", data["mcpServers"])
        self.assertIn("Stop", data["hooks"])
        self.assertEqual(data["hooks"]["Stop"][0]["hooks"][0]["command"], "existing")

    def test_init_installs_mcp_for_codex(self):
        import tomllib

        cwd = self.make_project()
        init_project(cwd=cwd)

        # Codex reads project-scope MCP servers from .codex/config.toml.
        data = tomllib.loads((cwd / ".codex" / "config.toml").read_text(encoding="utf-8"))
        self.assertIn("memory-seed", data["mcp_servers"])
        entry = data["mcp_servers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])

    def test_codex_mcp_merge_updates_stale_args(self):
        import tomllib

        cwd = self.make_project()
        config_path = cwd / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # Legacy bare-command form (pre-uvx) under our key must migrate forward.
        config_path.write_text(
            '[mcp_servers.memory-seed]\n'
            'command = "memory-seed-mcp"\n'
            'args = ["--old"]\n',
            encoding="utf-8",
        )

        from memory_seed.core import _merge_codex_mcp
        self.assertTrue(_merge_codex_mcp(cwd))

        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        entry = data["mcp_servers"]["memory-seed"]
        self.assertEqual(entry["command"], "uvx")
        self.assertEqual(entry["args"], ["--from", "memory-seed", "memory-seed-mcp", "--stdio"])

    def test_codex_mcp_merge_preserves_existing_config(self):
        import tomllib

        cwd = self.make_project()
        config_path = cwd / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # Unrelated setting + comment + a foreign MCP server must all survive.
        config_path.write_text(
            "# my codex config\n"
            'model = "gpt-5-codex"\n'
            "\n"
            "[mcp_servers.other]\n"
            'command = "other-cmd"\n'
            'args = []\n',
            encoding="utf-8",
        )

        from memory_seed.core import _merge_codex_mcp
        self.assertTrue(_merge_codex_mcp(cwd))

        text = config_path.read_text(encoding="utf-8")
        self.assertIn("# my codex config", text)  # comment preserved
        data = tomllib.loads(text)
        self.assertEqual(data["model"], "gpt-5-codex")  # unrelated setting preserved
        self.assertEqual(data["mcp_servers"]["other"]["command"], "other-cmd")  # foreign server kept
        self.assertIn("memory-seed", data["mcp_servers"])  # ours appended

    def test_codex_mcp_merge_preserves_foreign_server_on_our_key(self):
        import tomllib

        cwd = self.make_project()
        config_path = cwd / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # A different server squatting our key must not be overwritten.
        config_path.write_text(
            "[mcp_servers.memory-seed]\n"
            'command = "some-other-server"\n'
            "args = []\n",
            encoding="utf-8",
        )

        from memory_seed.core import _merge_codex_mcp
        self.assertFalse(_merge_codex_mcp(cwd))
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(data["mcp_servers"]["memory-seed"]["command"], "some-other-server")

    def test_doctor_warns_when_codex_hooks_without_mcp(self):
        from memory_seed.core import doctor, _merge_codex_mcp

        cwd = self.make_project()
        init_project(cwd=cwd)
        # Simulate a project that has Codex hooks but no MCP registration yet.
        (cwd / ".codex" / "config.toml").unlink()

        result = doctor(cwd=cwd)
        self.assertTrue(any("Codex" in w for w in result.warnings))
        self.assertTrue(result.control_plane_ok)  # warning is non-fatal

        # After re-registering, the warning clears.
        _merge_codex_mcp(cwd)
        self.assertFalse(any("Codex" in w for w in doctor(cwd=cwd).warnings))

    def test_doctor_warns_on_stale_manual_codex_mcp(self):
        from memory_seed.core import doctor, _merge_codex_mcp, _codex_mcp_status

        cwd = self.make_project()
        init_project(cwd=cwd)  # healthy control plane, so the non-fatal check is meaningful
        config_path = cwd / ".codex" / "config.toml"
        # Ours but stale, written as dotted keys -> no standard header to anchor a
        # rewrite. Update must no-op, and doctor must NOT stay silent about it.
        config_path.write_text(
            'mcp_servers.memory-seed.command = "memory-seed-mcp"\n'
            'mcp_servers.memory-seed.args = ["--old"]\n',
            encoding="utf-8",
        )

        self.assertEqual(_codex_mcp_status(cwd), "stale-manual")
        self.assertFalse(_merge_codex_mcp(cwd))  # safe no-op, not a corruption

        result = doctor(cwd=cwd)
        self.assertTrue(any("non-standard TOML form" in w for w in result.warnings))
        self.assertTrue(result.control_plane_ok)  # non-fatal

    def test_doctor_warns_on_stale_fixable_codex_mcp(self):
        from memory_seed.core import doctor, _merge_codex_mcp, _codex_mcp_status

        cwd = self.make_project()
        config_path = cwd / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # Ours but stale, standard header form -> update can migrate it.
        config_path.write_text(
            "[mcp_servers.memory-seed]\n"
            'command = "memory-seed-mcp"\n'
            'args = ["--old"]\n',
            encoding="utf-8",
        )

        self.assertEqual(_codex_mcp_status(cwd), "stale-fixable")
        result = doctor(cwd=cwd)
        self.assertTrue(any("outdated memory-seed MCP entry" in w for w in result.warnings))

        # update migrates it; warning then clears and status is current.
        self.assertTrue(_merge_codex_mcp(cwd))
        self.assertEqual(_codex_mcp_status(cwd), "current")
        self.assertFalse(any("Codex" in w for w in doctor(cwd=cwd).warnings))

    def test_codex_mcp_status_current_and_foreign_are_quiet(self):
        from memory_seed.core import doctor, _merge_codex_mcp, _codex_mcp_status

        cwd = self.make_project()
        # current
        _merge_codex_mcp(cwd)
        self.assertEqual(_codex_mcp_status(cwd), "current")
        self.assertFalse(any("Codex" in w for w in doctor(cwd=cwd).warnings))

        # foreign: a different server squatting our key
        (cwd / ".codex" / "config.toml").write_text(
            "[mcp_servers.memory-seed]\n"
            'command = "some-other-server"\n'
            "args = []\n",
            encoding="utf-8",
        )
        self.assertEqual(_codex_mcp_status(cwd), "foreign")
        self.assertFalse(any("Codex" in w for w in doctor(cwd=cwd).warnings))

    def test_doctor_warns_on_orphan_skill_not_in_registry(self):
        from memory_seed.core import doctor

        cwd = self.make_project()
        init_project(cwd=cwd)

        # A freshly seeded project's skills are all registered: no orphan warning.
        self.assertFalse(
            any("orphan skill" in w for w in doctor(cwd=cwd).warnings)
        )

        # Drop a skill runbook that is not referenced by skills/index.md.
        orphan = cwd / ".memory-seed" / "skills" / "ghost_skill.md"
        orphan.write_text(
            "---\nmemory-system-version: 2.7\n---\n\n# Ghost Skill\n",
            encoding="utf-8",
        )

        result = doctor(cwd=cwd)
        self.assertTrue(
            any("ghost_skill.md" in w and "orphan skill" in w for w in result.warnings)
        )
        self.assertTrue(result.control_plane_ok)  # warning is non-fatal

        # Registering it in the trigger registry clears the warning.
        registry = cwd / ".memory-seed" / "skills" / "index.md"
        registry.write_text(
            registry.read_text(encoding="utf-8")
            + "\n  - skill: ghost_skill.md\n    required: false\n",
            encoding="utf-8",
        )
        self.assertFalse(
            any("ghost_skill.md" in w for w in doctor(cwd=cwd).warnings)
        )

    def test_doctor_warns_on_local_user_with_no_matching_participant(self):
        from memory_seed.core import doctor

        cwd = self.make_project()
        init_project(cwd=cwd)

        # No local user configured at all: no warning (that's the SessionStart
        # hook's job, not doctor's).
        self.assertFalse(any("participants:" in w for w in doctor(cwd=cwd).warnings))

        (cwd / MEMORY_DIR_NAME / "local.yaml").write_text("user: jean\n", encoding="utf-8")

        # Local user configured but project.yaml has no participants: entry
        # for it at all -> warn.
        result = doctor(cwd=cwd)
        self.assertTrue(any("jean" in w and "participants:" in w for w in result.warnings))
        self.assertTrue(result.control_plane_ok)  # warning is non-fatal

        # A participants: entry for a *different* slug still leaves jean
        # unmatched -> still warns.
        (cwd / MEMORY_DIR_NAME / "project.yaml").write_text(
            "participants:\n  - slug: amina\n    initials: AM\n", encoding="utf-8"
        )
        result = doctor(cwd=cwd)
        self.assertTrue(any("jean" in w and "participants:" in w for w in result.warnings))

        # Adding the matching participant entry clears the warning.
        (cwd / MEMORY_DIR_NAME / "project.yaml").write_text(
            "participants:\n"
            "  - slug: amina\n    initials: AM\n"
            "  - slug: jean\n    initials: JN\n",
            encoding="utf-8",
        )
        self.assertFalse(any("participants:" in w for w in doctor(cwd=cwd).warnings))

    def test_doctor_warns_when_runtime_exists_but_routing_file_is_foreign(self):
        from memory_seed.core import doctor, _merge_routing_stanza

        cwd = self.make_project()
        init_project(cwd=cwd)

        # Fresh project: our AGENTS.md routes into the runtime, no route warning.
        self.assertFalse(any("route into" in w for w in doctor(cwd=cwd).warnings))

        # Replace it with a foreign file: neither our frontmatter nor our block.
        (cwd / "AGENTS.md").write_text("# Foreign Tool\n\nhost only\n", encoding="utf-8")
        result = doctor(cwd=cwd)
        self.assertTrue(
            any("AGENTS.md" in w and "route into" in w for w in result.warnings)
        )
        # Non-fatal, and not counted as a version mismatch (host owns the file).
        self.assertTrue(result.control_plane_ok)
        self.assertFalse(any(m["file"] == "AGENTS.md" for m in result.version_mismatches))

        # Injecting our managed block clears the warning.
        _merge_routing_stanza(cwd / "AGENTS.md")
        self.assertFalse(
            any("AGENTS.md" in w and "route into" in w for w in doctor(cwd=cwd).warnings)
        )


class RetrievalCheckPathTests(unittest.TestCase):
    SCRIPT = Path("memory_seed/seed/.memory-seed/hooks/memory-retrieval-check.py").resolve()

    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-retrieval-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        (path / ".memory-seed").mkdir()
        return path

    def _run(self, cwd, extra_env=None):
        import subprocess
        import sys
        import os

        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(self.SCRIPT)],
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
        ).stdout

    def test_mcp_found_message_mentions_memory_search(self):
        import os
        import stat

        cwd = self.make_project()
        # Create a dummy memory-seed-mcp binary on PATH
        bin_dir = cwd / "bin"
        bin_dir.mkdir()
        fake_bin = bin_dir / "memory-seed-mcp"
        fake_bin.write_text("#!/usr/bin/env python3\n")
        fake_bin.chmod(fake_bin.stat().st_mode | stat.S_IEXEC)

        out = self._run(cwd, extra_env={"PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", "")})
        self.assertIn("memory_search", out)
        self.assertNotIn("uv tool install", out)

    def test_mcp_missing_message_mentions_install(self):
        cwd = self.make_project()
        out = self._run(cwd, extra_env={"PATH": ""})
        self.assertIn("uv tool install", out)
        self.assertNotIn("memory_search MCP tool", out)


class CliHelpTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-cli-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def _run(self, argv):
        import contextlib
        import io

        from memory_seed.cli import main

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(argv)
        return code, buffer.getvalue()

    def _git_repo_with_commit(self, cwd):
        import subprocess

        subprocess.run(["git", "-C", str(cwd), "init", "-q"], check=True, capture_output=True)
        (cwd / "README.txt").write_text("x", encoding="utf-8")
        subprocess.run(["git", "-C", str(cwd), "add", "-A"], check=True, capture_output=True)
        subprocess.run(
            [
                "git", "-C", str(cwd),
                "-c", "user.name=test", "-c", "user.email=test@example.com",
                "-c", "commit.gpgsign=false",
                "commit", "-q", "-m", "initial",
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(["git", "-C", str(cwd), "branch", "-M", "main"], check=True, capture_output=True)

    def test_help_command_lists_all_commands(self):
        code, out = self._run(["help"])
        self.assertEqual(code, 0)
        for command in ("init", "update", "compact", "doctor", "version", "migrate", "help"):
            self.assertIn(command, out)
        self.assertIn("Keeping Memory Seed current", out)

    def test_no_command_prints_help(self):
        code, out = self._run([])
        self.assertEqual(code, 0)
        self.assertIn("Keeping Memory Seed current", out)

    def test_lense_command_is_a_deprecation_shim_to_memory_trace(self):
        # The review UI moved behind the optional `trace` extra and the
        # `memory-trace` command. When the extra is not installed (as in the
        # core-only test env), `memory-seed lense` points the user there and
        # exits non-zero - core ships no web stack.
        import contextlib
        import io
        import sys
        from unittest import mock

        from memory_seed.cli import main

        # Simulate the core-only environment deterministically: memory_trace
        # ships in the wheel (only fastapi is the extra), so on a dev machine
        # with the extra installed this test would otherwise take the
        # with-trace path and even start a real server. None in sys.modules
        # makes the service import raise ImportError in every environment.
        stderr = io.StringIO()
        with mock.patch.dict(
            sys.modules, {"memory_trace": None, "memory_trace.service": None}
        ):
            with contextlib.redirect_stderr(stderr):
                code = main(["lense", "--no-open"])
        self.assertEqual(code, 1)
        self.assertIn("memory-trace", stderr.getvalue())
        self.assertIn("moved", stderr.getvalue())

    def test_lense_open_both_is_forwarded_to_trace_service(self):
        import sys
        import types
        from unittest import mock

        from memory_seed.cli import main

        run_server = mock.Mock(return_value=0)
        trace_module = types.ModuleType("memory_trace")
        service_module = types.ModuleType("memory_trace.service")
        service_module.run_server = run_server

        with mock.patch.dict(
            sys.modules,
            {"memory_trace": trace_module, "memory_trace.service": service_module},
        ):
            code = main(["lense", "--open-both"])

        self.assertEqual(code, 0)
        self.assertTrue(run_server.call_args.args[0].open_both)

    def test_skills_list_shows_profiles_and_current_state(self):
        import os

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            self.assertEqual(self._run(["init", "--agents", "codex", "--profile", "coding"])[0], 0)
            code, out = self._run(["skills", "list"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Core skills:", out)
        self.assertIn("Installed optional skills:", out)
        self.assertIn("Ignored optional skills:", out)
        self.assertIn("Profiles:", out)
        self.assertIn("coding:", out)
        self.assertIn("code_search.md", out)
        self.assertIn("proposal_lifecycle.md", out)

    def test_skills_add_remove_and_ignored_cli(self):
        import os

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            self.assertEqual(self._run(["init", "--agents", "codex", "--no-skill-prompt"])[0], 0)
            self.assertEqual(self._run(["skills", "add", "proposal_lifecycle.md"])[0], 0)
            self.assertTrue((project / ".memory-seed" / "skills" / "proposal_lifecycle.md").exists())
            self.assertEqual(self._run(["skills", "remove", "proposal_lifecycle.md"])[0], 0)
            self.assertFalse((project / ".memory-seed" / "skills" / "proposal_lifecycle.md").exists())
            code, out = self._run(["skills", "ignored"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("proposal_lifecycle.md", out)

    def test_skills_add_rejects_unknown_name(self):
        import contextlib
        import io
        import os

        from memory_seed.cli import main

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            self.assertEqual(self._run(["init", "--agents", "codex", "--no-skill-prompt"])[0], 0)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = main(["skills", "add", "not-a-skill"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 1)
        self.assertIn("Unknown skill or profile", stderr.getvalue())

    def test_init_reports_selected_and_ignored_agents(self):
        import os

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            code, out = self._run(["init", "--agents", "codex", "--no-skill-prompt"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Installed agents: codex", out)
        self.assertIn("Ignored agents:", out)
        self.assertIn("claude", out)
        self.assertIn("gemini", out)
        self.assertNotIn("Ignored agents: (none)", out)

    def test_init_accepts_no_agent_prompt_flag(self):
        import os

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            code, out = self._run(["init", "--no-agent-prompt", "--no-skill-prompt"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Installed agents:", out)
        self.assertIn("Ignored agents: (none)", out)

    def test_init_can_opt_out_of_all_agents(self):
        import os

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            code, out = self._run(["init", "--agents", "none", "--no-skill-prompt"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Installed agents: (none)", out)
        self.assertIn("Ignored agents:", out)
        self.assertFalse((project / "CLAUDE.md").exists())
        self.assertFalse((project / "GEMINI.md").exists())
        self.assertFalse((project / ".codex").exists())
        self.assertTrue((project / "AGENTS.md").exists())
        self.assertTrue((project / ".memory-seed" / "agent-rules.md").exists())
        self.assertIn("agents:\n", (project / ".memory-seed" / "project.yaml").read_text(encoding="utf-8"))

    def test_branch_status_cli_warns_on_dirty_main(self):
        import os
        import subprocess

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            subprocess.run(["git", "init", "-q"], check=True, capture_output=True)
            (project / "README.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(
                [
                    "git", "-c", "user.name=test", "-c", "user.email=test@example.com",
                    "-c", "commit.gpgsign=false", "commit", "-q", "-m", "initial",
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "branch", "-M", "main"], check=True, capture_output=True)
            (project / "README.txt").write_text("changed", encoding="utf-8")
            code, out = self._run(["branch", "status"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Branch: main", out)
        self.assertIn("Dirty: yes", out)
        self.assertIn("task branch", out)
        self.assertIn("--no-ff", out)

    def test_branch_status_cli_json_reports_feature_branch(self):
        import json
        import os
        import subprocess

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            subprocess.run(["git", "init", "-q"], check=True, capture_output=True)
            (project / "README.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(
                [
                    "git", "-c", "user.name=test", "-c", "user.email=test@example.com",
                    "-c", "commit.gpgsign=false", "commit", "-q", "-m", "initial",
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "branch", "-M", "main"], check=True, capture_output=True)
            subprocess.run(["git", "switch", "-c", "feature-topic"], check=True, capture_output=True)
            code, out = self._run(["branch", "status", "--json"])
        finally:
            os.chdir(cwd)

        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["branch"], "feature-topic")
        self.assertFalse(data["is_integration_branch"])
        self.assertIn("merge --no-ff", data["recommendation"])

    def test_worktree_guard_cli_blocks_root_write_intent_without_override(self):
        import os

        project = self.make_project()
        self._git_repo_with_commit(project)
        cwd = Path.cwd()
        try:
            os.chdir(project)
            code, out = self._run(["worktree", "guard", "--agent", "codex", "--write-intent"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 1)
        self.assertIn("Classification: root-checkout", out)
        self.assertIn("Safe to write: no", out)
        self.assertIn("--allow-root-write", out)

    def test_worktree_guard_cli_json_reports_owned_worktree(self):
        import json
        import os
        import subprocess

        project = self.make_project()
        self._git_repo_with_commit(project)
        worktree = project / ".codex" / "worktrees" / "cli-task"
        worktree.parent.mkdir(parents=True)
        subprocess.run(
            ["git", "-C", str(project), "worktree", "add", "-q", "-b", "codex/cli-task", str(worktree)],
            check=True,
            capture_output=True,
        )
        cwd = Path.cwd()
        try:
            os.chdir(worktree)
            code, out = self._run(["worktree", "guard", "--agent", "codex", "--write-intent", "--json"])
        finally:
            os.chdir(cwd)

        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["classification"], "owned-worktree")
        self.assertTrue(data["safe_to_write"])

    def test_worktree_status_cli_without_agent_is_read_only_observation(self):
        import json
        import os
        import subprocess

        project = self.make_project()
        self._git_repo_with_commit(project)
        worktree = project / ".codex" / "worktrees" / "status-task"
        worktree.parent.mkdir(parents=True)
        subprocess.run(
            ["git", "-C", str(project), "worktree", "add", "-q", "-b", "codex/status-task", str(worktree)],
            check=True,
            capture_output=True,
        )
        cwd = Path.cwd()
        try:
            os.chdir(worktree)
            code, out = self._run(["worktree", "status", "--json"])
        finally:
            os.chdir(cwd)

        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["classification"], "owned-worktree")
        self.assertEqual(data["actual_namespace_owner"], "codex")
        self.assertFalse(data["write_intent"])

    def test_interactive_init_prompts_for_agent_opt_out(self):
        import contextlib
        import io
        import os
        import unittest.mock

        from memory_seed.cli import main

        class TtyInput(io.StringIO):
            def isatty(self):
                return True

        project = self.make_project()
        cwd = Path.cwd()
        stdout = io.StringIO()
        try:
            os.chdir(project)
            with contextlib.redirect_stdout(stdout), unittest.mock.patch(
                "sys.stdin", TtyInput("none\nnone\n")
            ):
                code = main(["init"])
        finally:
            os.chdir(cwd)

        out = stdout.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("Which agent integrations should be installed?", out)
        self.assertIn("Recommended default: all", out)
        self.assertIn("Installed agents: (none)", out)
        self.assertIn("Selected optional skills: (none)", out)

    def test_init_refuses_unreadable_existing_integration_config_without_overwrite(self):
        import contextlib
        import io
        import os
        import unittest.mock

        from memory_seed.cli import main

        project = self.make_project()
        config = project / MEMORY_DIR_NAME / "project.yaml"
        config.parent.mkdir(parents=True, exist_ok=True)
        original_bytes = b"participants:\n  - slug: jean\n"
        config.write_bytes(original_bytes)
        original_read_text = Path.read_text

        def fail_config_read(path, *args, **kwargs):
            if path == config:
                raise OSError("simulated read failure")
            return original_read_text(path, *args, **kwargs)

        cwd = Path.cwd()
        stderr = io.StringIO()
        try:
            os.chdir(project)
            with contextlib.redirect_stderr(stderr), unittest.mock.patch.object(
                Path, "read_text", new=fail_config_read
            ):
                code = main(["init", "--no-agent-prompt", "--no-skill-prompt"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 1)
        self.assertIn("cannot read existing", stderr.getvalue())
        self.assertEqual(config.read_bytes(), original_bytes)

    def test_init_noninteractive_writes_default_integration_mode(self):
        import os

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            code, _out = self._run(["init", "--no-agent-prompt", "--no-skill-prompt"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        config = (project / ".memory-seed" / "project.yaml").read_text(encoding="utf-8")
        self.assertIn("integration_mode: local-merge", config)

    def test_init_honors_explicit_integration_mode_flag(self):
        import os

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            code, _out = self._run(["init", "--no-agent-prompt", "--no-skill-prompt", "--integration-mode", "pr"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        config = (project / ".memory-seed" / "project.yaml").read_text(encoding="utf-8")
        self.assertIn("integration_mode: pr", config)

    def test_interactive_init_prompts_for_integration_mode_suggestion(self):
        import contextlib
        import io
        import os
        import unittest.mock

        from memory_seed.cli import main

        class TtyInput(io.StringIO):
            def isatty(self):
                return True

        project = self.make_project()
        cwd = Path.cwd()
        stdout = io.StringIO()
        try:
            os.chdir(project)
            with contextlib.redirect_stdout(stdout), unittest.mock.patch(
                "sys.stdin", TtyInput("\n")
            ), unittest.mock.patch(
                "memory_seed.cli.suggest_integration_mode",
                return_value=("pr", "GitHub reports more than one collaborator"),
            ):
                code = main(["init", "--no-agent-prompt", "--no-skill-prompt"])
        finally:
            os.chdir(cwd)

        out = stdout.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("How should branch work be integrated?", out)
        self.assertIn("Suggested: pr (GitHub reports more than one collaborator)", out)
        config = (project / ".memory-seed" / "project.yaml").read_text(encoding="utf-8")
        self.assertIn("integration_mode: pr", config)

    def test_init_preserves_declared_integration_mode_without_reprompt(self):
        import contextlib
        import io
        import os
        import unittest.mock

        from memory_seed.cli import main

        class TtyInput(io.StringIO):
            def isatty(self):
                return True

        project = self.make_project()
        memory_dir = project / ".memory-seed"
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / "project.yaml").write_text(
            "integration_mode: pr\nparticipants:\n  - slug: jean\n    initials: JN\n",
            encoding="utf-8",
        )
        cwd = Path.cwd()
        stdout = io.StringIO()
        try:
            os.chdir(project)
            with contextlib.redirect_stdout(stdout), unittest.mock.patch(
                "sys.stdin", TtyInput("")
            ), unittest.mock.patch("memory_seed.cli.suggest_integration_mode") as suggest_mode:
                code = main(["init", "--no-agent-prompt", "--no-skill-prompt"])
        finally:
            os.chdir(cwd)

        out = stdout.getvalue()
        self.assertEqual(code, 0)
        suggest_mode.assert_not_called()
        self.assertNotIn("How should branch work be integrated?", out)
        config = (project / ".memory-seed" / "project.yaml").read_text(encoding="utf-8")
        self.assertIn("integration_mode: pr", config)

    def test_session_integrate_cli_dispatches_pr_mode(self):
        import os
        import unittest.mock

        from memory_seed.core import SessionOpenPrResult

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            with unittest.mock.patch("memory_seed.cli.read_integration_mode", return_value="pr"), unittest.mock.patch(
                "memory_seed.cli.session_open_pr",
                return_value=SessionOpenPrResult(
                    opened=False,
                    dry_run=True,
                    base_branch="main",
                    source_branch="feature-pr",
                    pr_title="Integrate feature-pr into main",
                    pr_body="planned body",
                    planned_entries=["mse_1111111111111111 2026-07-11 09:00 -> .memory-seed/sessions/2026-07/2026-07-11.md"],
                ),
            ):
                code, out = self._run(["session", "integrate", "--branch", "feature-pr", "--dry-run"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Integration mode: pr", out)
        self.assertIn("Prepared entry:", out)
        self.assertIn("PR title: Integrate feature-pr into main", out)
        self.assertIn("Dry run - no push or PR performed.", out)

    def test_session_integrate_cli_dispatches_local_merge_mode(self):
        import os
        import unittest.mock

        from memory_seed.core import SessionMergeBranchResult

        project = self.make_project()
        cwd = Path.cwd()
        try:
            os.chdir(project)
            with unittest.mock.patch("memory_seed.cli.read_integration_mode", return_value="local-merge"), unittest.mock.patch(
                "memory_seed.cli.session_merge_branch",
                return_value=SessionMergeBranchResult(
                    committed=False,
                    planned_entries=["mse_1111111111111111 2026-07-11 09:00 -> .memory-seed/sessions/2026-07/2026-07-11.md"],
                ),
            ):
                code, out = self._run(["session", "integrate", "--branch", "feature-merge", "--dry-run"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Integration mode: local-merge", out)
        self.assertIn("Would import: mse_1111111111111111", out)
        self.assertIn("Dry run - no merge performed.", out)

    def test_user_set_show_clear_and_session_target(self):
        import contextlib

        cwd = Path.cwd()
        project = Path(tempfile.mkdtemp(prefix="memory-seed-cli-user-"))
        self.addCleanup(lambda: shutil.rmtree(project, ignore_errors=True))
        (project / ".memory-seed" / "sessions").mkdir(parents=True)
        # Per-user session targeting only activates with 2+ participants
        # registered; a lone configured user stays on the flat layout.
        (project / ".memory-seed" / "project.yaml").write_text(
            "participants:\n"
            "  - slug: jean\n"
            "    initials: JN\n"
            "  - slug: amina\n"
            "    initials: AM\n",
            encoding="utf-8",
        )

        try:
            import os

            os.chdir(project)
            self.assertEqual(self._run(["user", "set", "jean"])[0], 0)
            local = project / ".memory-seed" / "local.yaml"
            self.assertIn("user: jean", local.read_text(encoding="utf-8"))
            self.assertIn(".memory-seed/local.yaml", (project / ".gitignore").read_text(encoding="utf-8"))

            code, out = self._run(["user", "show"])
            self.assertEqual(code, 0)
            self.assertIn("jean", out)

            code, out = self._run(["session", "target"])
            self.assertEqual(code, 0)
            self.assertRegex(out.strip(), r"\.memory-seed/sessions/\d{4}-\d{2}/\d{4}-\d{2}-\d{2}/jean\.md$")

            code, out = self._run(["session", "target", "--create"])
            self.assertEqual(code, 0)
            target = project / out.strip()
            self.assertTrue(target.exists())
            created = target.read_text(encoding="utf-8")
            self.assertIn("schema_version: 2", created)
            self.assertIn("user: jean", created)
            self.assertIn("hash_id: msm_", created)

            self.assertEqual(self._run(["user", "clear"])[0], 0)
            self.assertFalse(local.exists())
        finally:
            os.chdir(cwd)

    def test_migrate_sessions_layout_cli_dry_run(self):
        import os

        cwd = Path.cwd()
        project = Path(tempfile.mkdtemp(prefix="memory-seed-cli-migrate-"))
        self.addCleanup(lambda: shutil.rmtree(project, ignore_errors=True))
        (project / ".memory-seed" / "sessions").mkdir(parents=True)
        (project / ".memory-seed" / "project.yaml").write_text(
            "participants:\n"
            "  - slug: jean\n"
            "    initials: JN\n",
            encoding="utf-8",
        )
        (project / ".memory-seed" / "sessions" / "2026-06-21.md").write_text(
            "## 2026-06-21 09:00 - Entry\n\n"
            "```yaml\n"
            "entry_id: ms-11111111\n"
            "user_initials: JN\n"
            "```\n\n"
            "- Body.\n",
            encoding="utf-8",
        )

        try:
            os.chdir(project)
            code, out = self._run(["migrate", "sessions-layout", "--dry-run"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Would migrate: 2026-06-21.md -> 2026-06/2026-06-21/jean.md", out)
        self.assertIn("No files changed.", out)

    def test_migrate_sessions_month_layout_cli_dry_run(self):
        import os

        cwd = Path.cwd()
        project = Path(tempfile.mkdtemp(prefix="memory-seed-cli-month-migrate-"))
        self.addCleanup(lambda: shutil.rmtree(project, ignore_errors=True))
        (project / ".memory-seed" / "sessions").mkdir(parents=True)
        (project / ".memory-seed" / "sessions" / "2026-06-21.md").write_text(
            "## 2026-06-21 09:00 - Entry\n\n"
            "```yaml\n"
            "entry_id: ms-11111111\n"
            "user_initials: JN\n"
            "```\n\n"
            "- Body.\n",
            encoding="utf-8",
        )

        try:
            os.chdir(project)
            code, out = self._run(["migrate", "sessions-month-layout", "--dry-run"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Would migrate: 2026-06-21.md -> 2026-06/2026-06-21.md", out)
        self.assertIn("No files changed.", out)

    def test_session_fuse_cli_dry_run_reports_imports(self):
        import os
        import subprocess

        cwd = Path.cwd()
        project = Path(tempfile.mkdtemp(prefix="memory-seed-cli-fuse-"))
        self.addCleanup(lambda: shutil.rmtree(project, ignore_errors=True))
        sessions = project / ".memory-seed" / "sessions"
        grouped = sessions / "2026-07"
        grouped.mkdir(parents=True, exist_ok=True)
        (grouped / "2026-07-10.md").write_text(
            "---\n"
            "tags:\n"
            "  - session-log\n"
            "  - memory-seed\n"
            "session_date: 2026-07-10\n"
            "---\n\n"
            "## 2026-07-10 09:00 - Base\n\n"
            "```yaml\n"
            "entry_id: mse_0123456789abcdef\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "branch: main\n"
            "```\n\n"
            "- Base.\n",
            encoding="utf-8",
        )

        try:
            os.chdir(project)
            subprocess.run(["git", "init", "-q"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)
            subprocess.run(["git", "config", "commit.gpgsign", "false"], check=True, capture_output=True)
            subprocess.run(["git", "branch", "-M", "main"], check=True, capture_output=True)
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-q", "-m", "base"], check=True, capture_output=True)
            subprocess.run(["git", "switch", "-c", "feature-fuse"], check=True, capture_output=True)
            (sessions / "2026-07-11.md").write_text(
                "---\n"
                "tags:\n"
                "  - session-log\n"
                "  - memory-seed\n"
                "session_date: 2026-07-11\n"
                "---\n\n"
                "## 2026-07-11 09:00 - Feature\n\n"
                "```yaml\n"
                "entry_id: mse_1111111111111111\n"
                "user_initials: JN\n"
                "agent_type: codex\n"
                "branch: feature-fuse\n"
                "```\n\n"
                "- Feature.\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-q", "-m", "feature"], check=True, capture_output=True)
            subprocess.run(["git", "switch", "main"], check=True, capture_output=True)
            code, out = self._run(["session", "fuse", "--branch", "feature-fuse"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Would import: mse_1111111111111111", out)
        self.assertIn(".memory-seed/sessions/2026-07/2026-07-11.md", out)

    def test_session_merge_branch_cli_dry_run_reports_plan(self):
        import os
        import subprocess

        cwd = Path.cwd()
        project = Path(tempfile.mkdtemp(prefix="memory-seed-cli-merge-branch-"))
        self.addCleanup(lambda: shutil.rmtree(project, ignore_errors=True))
        sessions = project / ".memory-seed" / "sessions"
        grouped = sessions / "2026-07"
        grouped.mkdir(parents=True, exist_ok=True)
        (grouped / "2026-07-10.md").write_text(
            "---\n"
            "tags:\n"
            "  - session-log\n"
            "  - memory-seed\n"
            "session_date: 2026-07-10\n"
            "---\n\n"
            "## 2026-07-10 09:00 - Base\n\n"
            "```yaml\n"
            "entry_id: mse_0123456789abcdef\n"
            "user_initials: JN\n"
            "agent_type: codex\n"
            "branch: main\n"
            "```\n\n"
            "- Base.\n",
            encoding="utf-8",
        )

        try:
            os.chdir(project)
            subprocess.run(["git", "init", "-q"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)
            subprocess.run(["git", "config", "commit.gpgsign", "false"], check=True, capture_output=True)
            subprocess.run(["git", "branch", "-M", "main"], check=True, capture_output=True)
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-q", "-m", "base"], check=True, capture_output=True)
            subprocess.run(["git", "switch", "-c", "feature-merge"], check=True, capture_output=True)
            (grouped / "2026-07-11.md").write_text(
                "---\n"
                "tags:\n"
                "  - session-log\n"
                "  - memory-seed\n"
                "session_date: 2026-07-11\n"
                "---\n\n"
                "## 2026-07-11 09:00 - Feature\n\n"
                "```yaml\n"
                "entry_id: mse_1111111111111111\n"
                "user_initials: JN\n"
                "agent_type: codex\n"
                "branch: feature-merge\n"
                "```\n\n"
                "- Feature.\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-q", "-m", "feature"], check=True, capture_output=True)
            subprocess.run(["git", "switch", "main"], check=True, capture_output=True)
            code, out = self._run(["session", "merge-branch", "--branch", "feature-merge", "--dry-run"])
        finally:
            os.chdir(cwd)

        self.assertEqual(code, 0)
        self.assertIn("Would import: mse_1111111111111111", out)
        self.assertIn("Dry run - no merge performed.", out)


class SessionStartContextHookTests(unittest.TestCase):
    SCRIPT = Path("memory_seed/seed/.memory-seed/hooks/session-start-context.py").resolve()

    def make_project(self, sessions=None):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-startup-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        sdir = path / ".memory-seed" / "sessions"
        sdir.mkdir(parents=True)
        for name, body in (sessions or {}).items():
            target = sdir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        return path

    def _run(self, cwd, *args):
        import subprocess
        import sys

        return subprocess.run(
            [sys.executable, str(self.SCRIPT), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
        ).stdout

    def _run_with_env(self, cwd, extra_env, *args):
        import os
        import subprocess
        import sys

        env = os.environ.copy()
        env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(self.SCRIPT), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
        ).stdout

    def test_injects_five_newest_entries_and_startup_directive(self):
        import json

        cwd = self.make_project({
            "2026-01-01.md": (
                "## 2026-01-01 08:00 - Excluded old work\n\ndrop me\n\n"
                "## 2026-01-01 09:00 - Prior context\n\nkeep prior\n"
            ),
            "2026-02-02.md": (
                "## 2026-02-02 10:00 - First entry\n\nbody A\n\n"
                "## 2026-02-02 11:00 - Second entry\n\nbody B\n\n"
                "## 2026-02-02 12:00 - Third entry\n\nbody C\n\n"
                "## 2026-02-02 14:30 - Latest entry title\n\nthe newest body\n"
            ),
        })

        out = self._run(cwd)
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]

        self.assertIn("`AGENTS.md`", context)
        self.assertIn("Read the five newest applicable entries", context)
        self.assertIn("Newest 5 session entries", context)
        # The window spans files when the newest file has fewer than five entries.
        self.assertIn(".memory-seed/sessions/2026-02-02.md", context)
        self.assertIn(".memory-seed/sessions/2026-01-01.md", context)
        self.assertIn("2026-01-01 09:00 - Prior context", context)
        self.assertNotIn("Excluded old work", context)
        self.assertNotIn("drop me", context)
        self.assertIn("2026-02-02 10:00 - First entry", context)
        self.assertIn("2026-02-02 14:30 - Latest entry title", context)
        self.assertIn("the newest body", context)
        self.assertIn("Use memory_search only for topical questions", context)

    def test_cursor_uses_additional_context_field(self):
        import json

        cwd = self.make_project({"2026-02-02.md": "## 2026-02-02 10:00 - X\n\nb\n"})
        out = self._run(cwd, "--cursor")
        data = json.loads(out)
        self.assertIn("additional_context", data)
        self.assertNotIn("hookSpecificOutput", data)
        self.assertIn("`AGENTS.md`", data["additional_context"])

    def test_all_dynamic_agent_outputs_include_startup_directive(self):
        import json

        cwd = self.make_project({"2026-02-02.md": "## 2026-02-02 10:00 - X\n\nb\n"})
        cases = (
            ((), lambda data: data["hookSpecificOutput"]["additionalContext"]),
            (("--codex",), lambda data: data["hookSpecificOutput"]["additionalContext"]),
            (("--gemini",), lambda data: data["hookSpecificOutput"]["additionalContext"]),
            (("--cursor",), lambda data: data["additional_context"]),
        )
        for args, context_from in cases:
            with self.subTest(agent=args or ("claude",)):
                context = context_from(json.loads(self._run(cwd, *args)))
                self.assertIn("`AGENTS.md`", context)
                self.assertIn("five newest applicable entries", context)

    def test_caps_long_latest_entry(self):
        import json

        big = "## 2026-02-02 10:00 - Huge\n\n" + ("x" * 5000) + "\n"
        cwd = self.make_project({"2026-02-02.md": big})
        out = self._run(cwd)
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("truncated", context)

    def test_empty_sessions_dir_still_emits_startup_directive(self):
        import json

        cwd = self.make_project({})
        (cwd / ".memory-seed" / "local.yaml").write_text("user: jean\n", encoding="utf-8")
        context = json.loads(self._run(cwd))["hookSpecificOutput"]["additionalContext"]
        self.assertIn("`AGENTS.md`", context)
        self.assertIn("No applicable session entries were found yet.", context)

    def test_missing_sessions_dir_still_emits_startup_directive(self):
        import json

        path = Path(tempfile.mkdtemp(prefix="memory-seed-startup-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        context = json.loads(self._run(path))["hookSpecificOutput"]["additionalContext"]
        self.assertIn("`AGENTS.md`", context)
        self.assertIn("No applicable session entries were found yet.", context)

    def test_ignores_non_date_filenames(self):
        import json

        cwd = self.make_project({
            "2026-02-02.md": "## 2026-02-02 10:00 - Real\n\nb\n",
            "notes.md": "## Should be ignored\n\nignored\n",
        })
        out = self._run(cwd)
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("2026-02-02.md", context)
        self.assertNotIn("Should be ignored", context)

    def _write_participants(self, cwd, count=2):
        slugs = [("jean", "JN"), ("amina", "AM"), ("theo", "TH")][:count]
        lines = ["participants:"]
        for slug, initials in slugs:
            lines.append(f"  - slug: {slug}")
            lines.append(f"    initials: {initials}")
        (cwd / ".memory-seed" / "project.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_user_context_injects_active_user_and_lists_contributors(self):
        import json

        cwd = self.make_project({
            "2026-02-02/jean.md": (
                "## 2026-02-02 10:00 - Jean first\n\nbody A\n\n"
                "## 2026-02-02 14:30 - Jean latest\n\njean newest body\n"
            ),
            "2026-02-02/amina.md": "## 2026-02-02 11:00 - Amina work\n\namina body\n",
            "2026-02-01/jean.md": "## 2026-02-01 09:00 - Jean older\n\nold body\n",
        })
        self._write_participants(cwd)

        out = self._run_with_env(cwd, {"MEMORY_SEED_USER": "jean"})
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]

        self.assertIn("Source: .memory-seed/sessions/2026-02-02/jean.md", context)
        self.assertIn("jean newest body", context)
        self.assertIn("Co-contributor session files for 2026-02-02:", context)
        self.assertIn(".memory-seed/sessions/2026-02-02/amina.md (1 entry)", context)
        self.assertNotIn("amina body", context)

    def test_configured_user_ignored_with_fewer_than_two_participants(self):
        import json

        # A per-user file exists, but with no participants: registered the
        # env-var user should be gated back to flat lookup - and since there's
        # no flat file either, the hook reports no applicable entries.
        cwd = self.make_project({
            "2026-02-02/jean.md": "## 2026-02-02 10:00 - Jean entry\n\nbody\n",
        })
        out = self._run_with_env(cwd, {"MEMORY_SEED_USER": "jean"})
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("No applicable session entries were found yet.", context)
        self.assertNotIn("jean body", context)

        # With exactly one participant registered, still gated to flat.
        self._write_participants(cwd, count=1)
        out = self._run_with_env(cwd, {"MEMORY_SEED_USER": "jean"})
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("No applicable session entries were found yet.", context)

        # A flat file is found once gated back, even though a per-user file
        # for the same date also exists.
        flat = cwd / ".memory-seed" / "sessions" / "2026-02-02.md"
        flat.write_text("## 2026-02-02 09:00 - Flat entry\n\nflat body\n", encoding="utf-8")
        out = self._run_with_env(cwd, {"MEMORY_SEED_USER": "jean"})
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Source: .memory-seed/sessions/2026-02-02.md", context)
        self.assertIn("flat body", context)

    def test_explicit_user_arg_bypasses_participant_gate(self):
        import json

        cwd = self.make_project({
            "2026-02-02/jean.md": "## 2026-02-02 10:00 - Jean entry\n\njean body\n",
        })
        out = self._run(cwd, "--user=jean")
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("jean body", context)

    def test_identity_offer_fires_once_then_never_again(self):
        cwd = self.make_project({})

        first = self._run(cwd).strip()
        self.assertIn("No local Memory Seed identity is configured", first)
        self.assertIn("AGENTS.md", first)
        self.assertTrue((cwd / ".memory-seed" / ".identity-offer-stamp").exists())

        second = self._run(cwd).strip()
        self.assertIn("AGENTS.md", second)
        self.assertNotIn("No local Memory Seed identity is configured", second)

    def test_identity_offer_skipped_when_user_already_configured(self):
        cwd = self.make_project({})
        (cwd / ".memory-seed" / "local.yaml").write_text("user: jean\n", encoding="utf-8")

        self.assertIn("AGENTS.md", self._run(cwd))
        self.assertFalse((cwd / ".memory-seed" / ".identity-offer-stamp").exists())

    def test_identity_offer_appended_alongside_project_state(self):
        cwd = self.make_project({"2026-02-02.md": "## 2026-02-02 10:00 - X\n\nb\n"})

        out = self._run(cwd)
        self.assertIn("No local Memory Seed identity is configured", out)
        self.assertIn("Newest 1 session entry", out)

    def test_markdown_heading_in_body_is_not_an_entry_boundary(self):
        import json

        # A "## " line inside an entry body (e.g. a quoted heading) must not be
        # parsed as an entry boundary, or the latest-entry extraction would start
        # from it and drop the real entry's content above it.
        cwd = self.make_project({
            "2026-02-02.md": (
                "## 2026-02-02 10:00 - Real entry\n\n"
                "Here is an example heading we quote:\n\n"
                "## Not A Real Entry Heading\n\n"
                "real entry trailing content\n"
            ),
        })
        out = self._run(cwd)
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]

        # The quoted heading stays inside the one real entry rather than
        # becoming a second context entry.
        self.assertIn("Newest 1 session entry", context)
        self.assertEqual(context.count("## 2026-02-02 10:00 - Real entry"), 1)
        self.assertIn("Here is an example heading we quote", context)
        self.assertIn("real entry trailing content", context)

    def test_seed_and_live_hook_match(self):
        live = Path(".memory-seed/hooks/session-start-context.py")
        seed = Path("memory_seed/seed/.memory-seed/hooks/session-start-context.py")
        self.assertEqual(
            live.read_text(encoding="utf-8"),
            seed.read_text(encoding="utf-8"),
        )

    def test_seed_and_live_agent_rules_match(self):
        live = Path(".memory-seed/agent-rules.md")
        seed = Path("memory_seed/seed/.memory-seed/agent-rules.md")
        self.assertEqual(
            live.read_text(encoding="utf-8"),
            seed.read_text(encoding="utf-8"),
        )


class AgentSelectionTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-agents-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    # --- resolve_agents ---
    def test_resolve_agents_flag_parsing_and_validation(self):
        from memory_seed.core import resolve_agents, KNOWN_AGENTS

        self.assertEqual(resolve_agents("claude,codex", isatty=False), {"claude", "codex"})
        self.assertEqual(resolve_agents("claude codex", isatty=False), {"claude", "codex"})
        self.assertEqual(resolve_agents("all", isatty=False), set(KNOWN_AGENTS))
        self.assertEqual(resolve_agents("none", isatty=False), set())
        # No flag, non-TTY -> all (backward-compatible default).
        self.assertEqual(resolve_agents(None, isatty=False), set(KNOWN_AGENTS))
        # Interactive empty response -> all.
        self.assertEqual(resolve_agents(None, isatty=True, prompt_response=""), set(KNOWN_AGENTS))
        self.assertEqual(resolve_agents(None, isatty=True, prompt_response="none"), set())
        self.assertEqual(resolve_agents(None, isatty=True, prompt_response="gemini"), {"gemini"})
        with self.assertRaises(ValueError):
            resolve_agents("claude,bogus", isatty=False)

    # --- selective init ---
    def test_init_with_subset_installs_only_selected(self):
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude", "codex"})

        self.assertTrue((cwd / "AGENTS.md").exists())
        self.assertTrue((cwd / "CLAUDE.md").exists())
        self.assertTrue((cwd / ".claude" / "settings.json").exists())
        self.assertTrue((cwd / ".codex" / "hooks.json").exists())
        self.assertTrue((cwd / ".mcp.json").exists())
        # Deselected agents leave no trace.
        self.assertFalse((cwd / "GEMINI.md").exists())
        self.assertFalse((cwd / ".gemini").exists())
        self.assertFalse((cwd / ".github").exists())
        self.assertFalse((cwd / ".cursor").exists())
        # Agent-agnostic core always present.
        self.assertTrue((cwd / ".memory-seed" / "agent-rules.md").exists())
        self.assertTrue((cwd / ".agents" / "developer.md").exists())
        # Selection persisted.
        from memory_seed.core import selected_agents
        self.assertEqual(selected_agents(cwd), {"claude", "codex"})
        self.assertTrue((cwd / ".memory-seed" / "project.yaml").exists())

    def test_init_all_agents_writes_skill_state_project_yaml(self):
        # Default all-agent selection stays dynamic, but new init writes skill
        # selection state so ignored optional skills are not re-added on update.
        cwd = self.make_project()
        init_project(cwd=cwd)
        self.assertTrue((cwd / ".memory-seed" / "project.yaml").exists())
        from memory_seed.core import read_project_agents, KNOWN_AGENTS, selected_agents
        self.assertIsNone(read_project_agents(cwd))
        self.assertEqual(selected_agents(cwd), set(KNOWN_AGENTS))

    def test_doctor_ignores_deselected_agent_files(self):
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude", "codex"})
        result = doctor(cwd=cwd)
        # GEMINI.md is intentionally absent; doctor must not flag it.
        self.assertNotIn("GEMINI.md", result.missing)
        self.assertEqual(result.missing, [])
        self.assertFalse(any("Codex" in w for w in result.warnings))

    def test_update_does_not_readd_deselected_agents(self):
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude", "codex"})
        update_project(cwd=cwd)
        self.assertFalse((cwd / "GEMINI.md").exists())
        self.assertFalse((cwd / ".gemini").exists())
        self.assertFalse((cwd / ".github").exists())

    # --- add / remove ---
    def test_add_agent_installs_and_persists(self):
        from memory_seed.core import add_agent, selected_agents

        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude"})
        res = add_agent(cwd=cwd, agent="gemini")
        self.assertTrue(res["changed"])
        self.assertTrue((cwd / "GEMINI.md").exists())
        self.assertTrue((cwd / ".gemini" / "settings.json").exists())
        self.assertEqual(selected_agents(cwd), {"claude", "gemini"})
        # Adding an already-installed agent is a no-op.
        self.assertFalse(add_agent(cwd=cwd, agent="gemini")["changed"])

    def test_remove_agent_strips_ours_preserves_foreign_and_backs_up(self):
        import json
        from memory_seed.core import remove_agent, selected_agents

        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude", "codex"})
        # Inject foreign content into Claude's settings.
        settings = cwd / ".claude" / "settings.json"
        data = json.loads(settings.read_text())
        data["permissions"] = {"allow": ["Bash"]}
        settings.write_text(json.dumps(data))

        res = remove_agent(cwd=cwd, agent="claude")
        self.assertTrue(res["changed"])
        self.assertTrue(res["backed_up"])  # something was backed up
        # Routing file + ours-only .mcp.json gone.
        self.assertFalse((cwd / "CLAUDE.md").exists())
        self.assertFalse((cwd / ".mcp.json").exists())
        # Foreign content preserved; file NOT deleted.
        self.assertTrue(settings.exists())
        self.assertEqual(list(json.loads(settings.read_text()).keys()), ["permissions"])
        self.assertEqual(selected_agents(cwd), {"codex"})

    def test_remove_not_installed_is_noop(self):
        from memory_seed.core import remove_agent
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"claude"})
        res = remove_agent(cwd=cwd, agent="gemini")
        self.assertFalse(res["changed"])

    def test_remove_last_agent_warns_and_is_zero_state(self):
        from memory_seed.core import remove_agent, selected_agents, read_project_agents
        cwd = self.make_project()
        init_project(cwd=cwd, agents={"codex"})
        res = remove_agent(cwd=cwd, agent="codex")
        self.assertTrue(res["warning"])
        # Zero-agents is a real state (empty set), distinct from unconfigured (None).
        self.assertEqual(read_project_agents(cwd), set())
        self.assertEqual(selected_agents(cwd), set())
        # doctor expects no agent files and is clean.
        self.assertEqual(doctor(cwd=cwd).missing, [])

    def test_remove_codex_preserves_foreign_toml(self):
        import tomllib
        from memory_seed.core import remove_agent

        cwd = self.make_project()
        init_project(cwd=cwd, agents={"codex"})
        cfg = cwd / ".codex" / "config.toml"
        # Surround our block with foreign TOML: a top-level key before, a foreign
        # MCP table after. Exercises the line-based stripper's "delete to next [".
        cfg.write_text(
            'model = "gpt-x"\n\n'
            + cfg.read_text(encoding="utf-8")
            + '\n[mcp_servers.other]\ncommand = "foo"\nargs = []\n',
            encoding="utf-8",
        )

        remove_agent(cwd=cwd, agent="codex")

        self.assertTrue(cfg.exists())
        text = cfg.read_text(encoding="utf-8")
        self.assertNotIn("[mcp_servers.memory-seed]", text)
        self.assertIn('model = "gpt-x"', text)
        self.assertIn("[mcp_servers.other]", text)
        parsed = tomllib.loads(text)  # still valid TOML
        self.assertNotIn("memory-seed", parsed.get("mcp_servers", {}))
        self.assertIn("other", parsed.get("mcp_servers", {}))

    def test_remove_from_unconfigured_project_writes_remaining(self):
        from memory_seed.core import remove_agent, selected_agents, KNOWN_AGENTS

        cwd = self.make_project()
        init_project(cwd=cwd)  # all agents, project.yaml contains skill state only
        self.assertTrue((cwd / ".memory-seed" / "project.yaml").exists())

        res = remove_agent(cwd=cwd, agent="gemini")
        self.assertTrue(res["changed"])
        self.assertEqual(selected_agents(cwd), set(KNOWN_AGENTS) - {"gemini"})
        self.assertTrue((cwd / ".memory-seed" / "project.yaml").exists())
        self.assertFalse((cwd / "GEMINI.md").exists())

    def test_project_yaml_parser_fails_open(self):
        from memory_seed.core import read_project_agents
        cwd = self.make_project()
        (cwd / ".memory-seed").mkdir(parents=True)
        cfg = cwd / ".memory-seed" / "project.yaml"
        # Malformed / unrelated content with no agents: key -> None (treated as all).
        cfg.write_text("schema_version: 1\nusers:\n  - jean\n", encoding="utf-8")
        self.assertIsNone(read_project_agents(cwd))
        # Inline list form is parsed; unknown slugs ignored.
        cfg.write_text("agents: [claude, bogus, codex]\n", encoding="utf-8")
        self.assertEqual(read_project_agents(cwd), {"claude", "codex"})

    def test_project_yaml_participants_coexist_with_agent_selection(self):
        from memory_seed.core import read_project_participants, selected_agents
        cwd = self.make_project()
        (cwd / ".memory-seed").mkdir(parents=True)
        (cwd / ".memory-seed" / "project.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "project_id: memory-seed",
                    "agents:",
                    "  - claude",
                    "  - codex",
                    "participants:",
                    "  - slug: jean",
                    "    initials: JN",
                    "    display_name: Jean",
                    "  - slug: amina",
                    "    initials: AM",
                    "    display_name: Amina",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        participants = read_project_participants(cwd)

        self.assertEqual(selected_agents(cwd), {"claude", "codex"})
        self.assertEqual([p.slug for p in participants], ["jean", "amina"])
        self.assertEqual([p.initials for p in participants], ["JN", "AM"])
        self.assertEqual(participants[0].display_name, "Jean")

    def test_write_project_agents_preserves_participants_block(self):
        from memory_seed.core import read_project_participants, selected_agents, write_project_agents
        cwd = self.make_project()
        (cwd / ".memory-seed").mkdir(parents=True)
        cfg = cwd / ".memory-seed" / "project.yaml"
        cfg.write_text(
            "schema_version: 1\n"
            "project_id: memory-seed\n"
            "participants:\n"
            "  - slug: jean\n"
            "    initials: JN\n"
            "    display_name: Jean\n"
            "agents:\n"
            "  - claude\n",
            encoding="utf-8",
        )

        write_project_agents(cwd, {"codex"})

        self.assertEqual(selected_agents(cwd), {"codex"})
        self.assertEqual([(p.slug, p.initials, p.display_name) for p in read_project_participants(cwd)], [("jean", "JN", "Jean")])
        text = cfg.read_text(encoding="utf-8")
        self.assertIn("participants:\n  - slug: jean\n    initials: JN\n    display_name: Jean", text)

    def test_project_yaml_participants_fail_open(self):
        from memory_seed.core import read_project_participants
        cwd = self.make_project()
        (cwd / ".memory-seed").mkdir(parents=True)
        (cwd / ".memory-seed" / "project.yaml").write_text(
            "participants:\n"
            "  - slug: Jean\n"
            "    initials: JN\n"
            "  - initials: AM\n",
            encoding="utf-8",
        )

        self.assertEqual(read_project_participants(cwd), [])


if __name__ == "__main__":
    unittest.main()
