"""Decision S: source following (selectors.source_references)."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from memory_seed.retrieval import (
    SOURCE_REFERENCE_MAX_TOKENS,
    _retrieval_corpus_revision,
    resolve_retrieval_spec,
)
from memory_seed.retrieval_profiles import load_retrieval_profile
from memory_seed.retrieval_spec import normalize_retrieval_spec_v2, retrieval_spec_fingerprint
from memory_seed.task_packet import project_constitution

DECISION = "mse_srcfollow01:d1"

SESSION = """## 2026-08-01 09:00 - Source following decision

```yaml
entry_id: mse_srcfollow01
user_initials: JN
agent_type: claude
project_path: .
subproject_path: null
```

### Decision

- D: Follow cited sources one hop.
- R: Cited plans carry the decision's context.
- S: `docs/plan.md#rollout-steps`
- S: `docs/whole.md`
- S: `docs/plan.md#no-such-heading`
- S: `.memory-seed/agent-rules.md`
- S: `docs/CONSTITUTION.md#2-invariants`
- S: `docs/7_Replaced/old-plan.md`
- S: `docs/diagram.png`
- S: `docs/absent.md`
- S: `docs/huge.md`
"""

PLAN = """# Plan

## Background

Context that is not cited.

## Rollout Steps

1. Ship behind a flag.
2. Measure.

### Detail

Nested detail stays in the section.

## Later

Not part of the cited section.
"""


class SourceReferenceFollowingTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="memory-seed-source-refs-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        files = {
            "docs/CONSTITUTION.md": "# Constitution\n\n## 2. Invariants\n\nMarkdown is authoritative.\n",
            "docs/plan.md": PLAN,
            "docs/whole.md": "# Whole\n\nCited without an anchor.\n",
            "docs/7_Replaced/old-plan.md": "# Old\n\nSuperseded.\n",
            "docs/diagram.png": "not markdown",
            "docs/huge.md": "# Huge\n\n" + ("word " * (SOURCE_REFERENCE_MAX_TOKENS * 2)) + "\n",
            ".memory-seed/agent-rules.md": "# Rules\n",
            ".memory-seed/sessions/2026-08-01.md": SESSION,
        }
        for relative, text in files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        for args in (("init", "-b", "main"), ("config", "user.email", "t@example.com"),
                     ("config", "user.name", "T"), ("add", "."), ("commit", "-m", "fixture")):
            subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)

    def spec(self, *, follow=True):
        selectors = {"pinned": [{"kind": "decision", "id": DECISION, "reason": "Fixture decision."}]}
        if follow is not None:
            selectors["source_references"] = follow
        return {
            "schema": "memory-seed/retrieval-spec",
            "version": 2,
            "required": {
                "constitution": True,
                "related_decisions": {"depth": 1},
                "evidence": {"mode": "latest"},
            },
            "selectors": selectors,
        }

    def warning_codes(self, pack):
        return {(item["code"], item["detail"].split(" -> ", 1)[1].split(":", 1)[0]) for item in pack["warnings"]}

    def test_off_is_absent_and_byte_identical_to_the_prior_spec(self):
        off = normalize_retrieval_spec_v2(self.spec(follow=False))
        omitted = normalize_retrieval_spec_v2(self.spec(follow=None))
        self.assertNotIn("source_references", off["selectors"])
        self.assertEqual(retrieval_spec_fingerprint(off), retrieval_spec_fingerprint(omitted))
        self.assertTrue(normalize_retrieval_spec_v2(self.spec())["selectors"]["source_references"])

        pack = resolve_retrieval_spec(self.spec(follow=False), self.root)
        self.assertNotIn("source_reference_constitution_anchors", pack)
        self.assertFalse(any(item["source"].startswith("docs/plan") for item in pack["evidence"]))

    def test_follows_anchored_and_whole_sources_once_with_digests(self):
        pack = resolve_retrieval_spec(self.spec(), self.root)
        by_id = {item["id"]: item for item in pack["evidence"]}

        section = by_id["docs/plan.md#rollout-steps"]
        self.assertEqual(section["kind"], "markdown")
        self.assertEqual(section["selected_by"], ["optional.source_references"])
        self.assertEqual(section["line_range"], [7, 15])  # through "### Detail", stops at "## Later"
        self.assertIn(f"cited by {DECISION} S: source", section["reasons"])
        self.assertTrue(section["content_digest"].startswith("sha256:"))
        self.assertIn("docs/whole.md", by_id)
        # The missing slug falls back to the whole file, which the anchored
        # section does not duplicate because they are different identities.
        self.assertIn("docs/plan.md", by_id)
        self.assertEqual(sum(1 for item in pack["evidence"] if item["id"] == "docs/whole.md"), 1)

        self.assertEqual(pack["source_reference_constitution_anchors"], ["2-invariants"])
        self.assertFalse(any(item["id"].startswith("docs/CONSTITUTION.md#") for item in pack["evidence"]))

    def test_every_unfollowed_reference_is_reported(self):
        pack = resolve_retrieval_spec(self.spec(), self.root)
        codes = self.warning_codes(pack)
        self.assertIn(("source_ref_anchor_missing", "docs/plan.md#no-such-heading"), codes)
        self.assertIn(("source_ref_excluded", ".memory-seed/agent-rules.md"), codes)
        self.assertIn(("source_ref_retired", "docs/7_Replaced/old-plan.md"), codes)
        self.assertIn(("source_ref_non_markdown", "docs/diagram.png"), codes)
        self.assertIn(("source_ref_missing", "docs/absent.md"), codes)
        self.assertIn(("source_ref_over_cap", "docs/huge.md"), codes)
        ids = {item["id"] for item in pack["evidence"]}
        for excluded in (".memory-seed/agent-rules.md", "docs/7_Replaced/old-plan.md", "docs/huge.md"):
            self.assertNotIn(excluded, ids)

    def test_resolution_is_deterministic(self):
        first = resolve_retrieval_spec(self.spec(), self.root)
        second = resolve_retrieval_spec(self.spec(), self.root)
        self.assertEqual(first["fingerprint"], second["fingerprint"])

    def test_followed_file_joins_the_corpus_revision_only_when_on(self):
        on = normalize_retrieval_spec_v2(self.spec())
        off = normalize_retrieval_spec_v2(self.spec(follow=False))
        before_on = _retrieval_corpus_revision(self.root, on)
        before_off = _retrieval_corpus_revision(self.root, off)
        (self.root / "docs" / "whole.md").write_text("# Whole\n\nEdited.\n", encoding="utf-8")
        self.assertNotEqual(_retrieval_corpus_revision(self.root, on).split(":")[-1], before_on.split(":")[-1])
        self.assertEqual(_retrieval_corpus_revision(self.root, off).split(":")[-1], before_off.split(":")[-1])

    def test_v2_profiles_default_on_and_v1_profiles_are_unchanged(self):
        repo = Path(__file__).resolve().parents[1]
        for profile in ("adr-review", "architecture", "bug-investigation", "implementation", "refactoring", "research"):
            with self.subTest(profile=profile):
                v1 = load_retrieval_profile(profile, 1, repo)
                v2 = load_retrieval_profile(profile, 2, repo)
                self.assertNotIn("source_references", v1["selectors"])
                self.assertTrue(v2["selectors"]["source_references"])
                off = load_retrieval_profile(
                    profile, 2, repo, overrides={"selectors": {"source_references": False}})
                self.assertEqual(retrieval_spec_fingerprint(off), retrieval_spec_fingerprint(v1))


class ConstitutionSourceAnchorProjectionTests(unittest.TestCase):
    CONSTITUTION = "\n".join([
        "# Constitution",
        "",
        "**Version:** 2.2 — **RATIFIED 2026-09-23** by JNL.",
        "",
        "## 2. Invariants",
        "",
        "<!-- constitution-ref: constitution:v2#ownership -->",
        "1. Users own their memory.",
        "<!-- constitution-ref: constitution:v2#append-only -->",
        "2. The past is append-only.",
        "",
        "## 3. Principles",
        "",
        "<!-- constitution-ref: constitution:v2#minimal-context -->",
        "Minimal but sufficient context.",
    ])

    def dispatch(self):
        return {
            "objective": "zzzz",
            "project_context": {"non_goals": [], "task_fit": "qqqq"},
            "execution": {"capability_tier": "balanced", "acceptance_observables": []},
            "constitution_refs": [],
        }

    def materialized(self):
        return [{"kind": "constitution", "id": "docs/CONSTITUTION.md", "source": "docs/CONSTITUTION.md",
                 "content": self.CONSTITUTION}]

    def test_heading_anchor_selects_whole_clauses_not_the_full_document(self):
        projection = project_constitution(self.dispatch(), self.materialized(), ["2-invariants"])
        self.assertEqual(projection["mode"], "anchored_clauses")
        self.assertEqual(
            [clause["ref"] for clause in projection["clauses"]],
            ["constitution:v2#ownership", "constitution:v2#append-only"],
        )
        self.assertTrue(all("decision S: Constitution anchor" in clause["selection_reason"]
                            for clause in projection["clauses"]))

    def test_clause_ref_anchor_and_unmatched_anchor(self):
        projection = project_constitution(self.dispatch(), self.materialized(), ["minimal-context", "nowhere"])
        self.assertEqual([clause["ref"] for clause in projection["clauses"]], ["constitution:v2#minimal-context"])
        self.assertEqual(projection["unmatched_source_anchors"], ["nowhere"])

    def test_no_anchors_keeps_existing_behaviour(self):
        projection = project_constitution(self.dispatch(), self.materialized())
        self.assertEqual(projection["mode"], "full_document_fallback")
        self.assertNotIn("unmatched_source_anchors", projection)


if __name__ == "__main__":
    unittest.main()
