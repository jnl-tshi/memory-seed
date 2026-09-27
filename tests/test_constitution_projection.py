"""Clause-level Constitution selection: the shared cascade and its resolver use."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from memory_seed.constitution_projection import (
    STAGE_ANCHOR,
    STAGE_BINDING,
    STAGE_KEYWORD,
    STAGE_SOURCE,
    STAGE_TOPIC,
    ConstitutionProjectionError,
    derived_topic_clause_map,
    parse_constitution,
    select_clauses,
)
from memory_seed.retrieval import resolve_retrieval_spec, validate_evidence_pack
from memory_seed.retrieval_spec import (
    RetrievalSpecValidationError,
    normalize_retrieval_spec_v2,
    retrieval_spec_fingerprint,
)

CONSTITUTION = """# Constitution

**Version:** 2.0 — **RATIFIED 2026-09-05**

## 2. Invariants

<!-- constitution-ref: constitution:v2#markdown-authority -->
Markdown is the source of truth; every index is a derived projection.

<!-- constitution-ref: constitution:v2#append-only -->
Session history is append-only.

## 3. Principles

<!-- constitution-ref: constitution:v2#evidence-first -->
Retrieval returns evidence before conclusions.

<!-- constitution-ref: constitution:v2#lexical-normalization -->
<!-- constitution-topics: retrieval -->
Keyword matching folds case and width before scoring.

## 11. Governance

<!-- constitution-ref: constitution:v2#control-plane-precedence -->
Control files outrank session evidence.

### Version log

| Version | Change |
|---|---|
| 2.0 | Retrieval vocabulary everywhere in this log. |
"""


def adr(adr_id, topics, *bindings):
    event = SimpleNamespace(
        constitution_refs=tuple(SimpleNamespace(ref=ref, role=role) for ref, role in bindings)
    )
    return SimpleNamespace(adr_id=adr_id, topics=tuple(topics), events=[event])


class ParseTests(unittest.TestCase):
    def setUp(self):
        self.document = parse_constitution(CONSTITUTION, "docs/CONSTITUTION.md")

    def test_clauses_stop_at_headings_so_the_version_log_is_never_a_clause(self):
        refs = [clause.ref for clause in self.document.clauses]
        self.assertEqual(len(refs), 5)
        last = self.document.by_ref()["constitution:v2#control-plane-precedence"]
        self.assertNotIn("Version log", last.content)
        self.assertEqual(last.heading, "## 11. Governance")

    def test_topics_marker_is_read_and_does_not_move_clause_ownership(self):
        clause = self.document.by_ref()["constitution:v2#lexical-normalization"]
        self.assertEqual(clause.authored_topics, ("retrieval",))
        stripped = parse_constitution(
            CONSTITUTION.replace("<!-- constitution-topics: retrieval -->\n", ""),
            "docs/CONSTITUTION.md",
        )
        self.assertEqual([c.ref for c in stripped.clauses], [c.ref for c in self.document.clauses])
        self.assertEqual(
            clause.content.replace("<!-- constitution-topics: retrieval -->\n", ""),
            stripped.by_ref()[clause.ref].content,
        )

    def test_legacy_names_resolve_to_the_current_anchor(self):
        self.assertEqual(
            self.document.current_ref("constitution:v1#append-only"),
            "constitution:v2#append-only",
        )

    def test_unratified_document_is_refused(self):
        with self.assertRaises(ConstitutionProjectionError):
            parse_constitution("# Constitution\n\n<!-- constitution-ref: constitution:v2#x -->\nX\n", "c.md")


class CascadeTests(unittest.TestCase):
    def setUp(self):
        self.document = parse_constitution(CONSTITUTION, "docs/CONSTITUTION.md")

    def refs(self, selection):
        return [item.clause.ref for item in selection.selected]

    def test_explicit_anchors_are_exclusive_and_fail_closed(self):
        selection = select_clauses(
            self.document,
            anchors=["constitution:v1#append-only"],
            adr_bindings=[("constitution:v2#evidence-first", "adr_x", "governing")],
            keywords=["retrieval"],
        )
        self.assertEqual(self.refs(selection), ["constitution:v2#append-only"])
        self.assertEqual(selection.mode, "explicit_anchors")
        self.assertIn(STAGE_ANCHOR, selection.selected[0].stages)
        with self.assertRaises(ConstitutionProjectionError):
            select_clauses(self.document, anchors=["constitution:v2#missing"])

    def test_named_adr_bindings_are_mandated_even_over_the_cap(self):
        selection = select_clauses(
            self.document,
            adr_bindings=[
                ("constitution:v1#markdown-authority", "adr_a", "governing"),
                ("constitution:v2#append-only", "adr_b", "supporting"),
            ],
            ranked_cap=1,
        )
        self.assertEqual(
            self.refs(selection),
            ["constitution:v2#markdown-authority", "constitution:v2#append-only"],
        )
        self.assertTrue(all(STAGE_BINDING in item.stages for item in selection.selected))

    def test_ranked_stages_stop_at_the_cap(self):
        selection = select_clauses(
            self.document,
            related_adr_bindings=[
                ("constitution:v2#evidence-first", "adr_r", "governing"),
                ("constitution:v2#append-only", "adr_r", "supporting"),
            ],
            ranked_cap=20,
        )
        # the first ranked clause is always admitted; the second exceeds the cap
        self.assertEqual(self.refs(selection), ["constitution:v2#evidence-first"])

    def test_topic_map_joins_adr_topics_with_bindings_plus_authored_tags(self):
        mapping = derived_topic_clause_map(
            self.document,
            [adr("adr_r", ["retrieval"], ("constitution:v1#evidence-first", "governing"))],
        )
        self.assertEqual(mapping["retrieval"]["constitution:v2#evidence-first"]["governing"], 1)
        self.assertEqual(mapping["retrieval"]["constitution:v2#lexical-normalization"]["authored"], 1)
        selection = select_clauses(self.document, topics=["retrieval"], topic_map=mapping)
        self.assertEqual(
            self.refs(selection),
            ["constitution:v2#evidence-first", "constitution:v2#lexical-normalization"],
        )
        self.assertTrue(all(STAGE_TOPIC in item.stages for item in selection.selected))

    def test_keywords_rank_clause_text_and_skip_the_version_log(self):
        selection = select_clauses(self.document, keywords=["case folding keyword"])
        self.assertEqual(self.refs(selection), ["constitution:v2#lexical-normalization"])
        self.assertIn(STAGE_KEYWORD, selection.selected[0].stages)

    def test_source_anchor_naming_one_clause_is_mandated_a_section_is_ranked(self):
        exact = select_clauses(self.document, source_anchors=["append-only"], ranked_cap=1)
        self.assertEqual(self.refs(exact), ["constitution:v2#append-only"])
        self.assertIn(STAGE_SOURCE, exact.selected[0].stages)
        section = select_clauses(self.document, source_anchors=["3-principles"], ranked_cap=15)
        self.assertEqual(self.refs(section), ["constitution:v2#evidence-first"])
        self.assertEqual(select_clauses(self.document, source_anchors=["nope"]).unmatched_source_anchors, ["nope"])

    def test_nothing_selected_means_fallback_whole(self):
        selection = select_clauses(self.document, keywords=["sourdough"])
        self.assertTrue(selection.fallback)
        self.assertEqual(selection.selected, [])


SESSION = """## 2026-09-01 09:00 - Retrieval decision

```yaml
entry_id: mse_clauseproj01
user_initials: JN
agent_type: claude
project_path: .
subproject_path: null
topics:
  - retrieval
```

### Decision

- D: Rank evidence before summarising.
- R: Readers verify the evidence.
"""

class LiveConstitutionTests(unittest.TestCase):
    """This repository's Constitution: every clause is reachable by a topic."""

    def test_every_live_clause_is_reached_and_authored_tags_are_vocabulary(self):
        from memory_seed.constitution_projection import topic_map_report

        report = topic_map_report(Path(__file__).resolve().parents[1])
        self.assertTrue(report["ok"])
        self.assertEqual(report["unreached_clauses"], [])
        self.assertEqual(report["unknown_authored_topics"], [])

    def test_topic_markers_change_no_clause_text(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "docs" / "CONSTITUTION.md").read_text(encoding="utf-8")
        import re

        stripped = re.sub(r"(?m)^[ \t]*<!-- constitution-topics:[^>]*-->\n", "", text)
        live = parse_constitution(text, "docs/CONSTITUTION.md")
        bare = parse_constitution(stripped, "docs/CONSTITUTION.md")
        self.assertEqual([c.ref for c in live.clauses], [c.ref for c in bare.clauses])
        for clause in live.clauses:
            self.assertEqual(
                re.sub(r"(?m)^[ \t]*<!-- constitution-topics:[^>]*-->\n", "", clause.content + "\n"),
                bare.by_ref()[clause.ref].content + "\n",
            )


class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="memory-seed-clauses-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        files = {
            "docs/CONSTITUTION.md": CONSTITUTION,
            ".memory-seed/sessions/2026-09/2026-09-01.md": SESSION,
            ".memory-seed/topics.yaml": (
                "schema_version: 2\ntopics:\n  - slug: retrieval\n    description: Retrieval.\n    axis: area\n"
            ),
        }
        for relative, text in files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        for args in (("init", "-b", "main"), ("config", "user.email", "t@example.com"),
                     ("config", "user.name", "T"), ("add", "."), ("commit", "-m", "fixture")):
            subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)

    def spec(self, **extra):
        spec = {
            "schema": "memory-seed/retrieval-spec",
            "version": 2,
            "required": {
                "constitution": True,
                "related_decisions": {"depth": 1},
                "evidence": {"mode": "latest"},
            },
            "filters": {"topics": ["retrieval"]},
        }
        spec.update(extra)
        return spec

    def test_new_fields_absent_keep_the_canonical_spec_bytes(self):
        base = normalize_retrieval_spec_v2(self.spec())
        explicit_defaults = normalize_retrieval_spec_v2(
            self.spec(
                constitution={"mode": "clauses", "ranked_cap": 4000},
                selectors={"pinned_roots": False, "related_adrs": False},
            )
        )
        self.assertNotIn("constitution", base)
        self.assertEqual(retrieval_spec_fingerprint(base), retrieval_spec_fingerprint(explicit_defaults))
        with self.assertRaises(RetrievalSpecValidationError):
            normalize_retrieval_spec_v2(self.spec(constitution={"mode": "whole", "keywords": ["x"]}))

    def test_pack_carries_clauses_not_the_whole_document(self):
        pack = resolve_retrieval_spec(
            self.spec(constitution={"keywords": ["conclusions"]}), self.root
        )
        clauses = [item for item in pack["evidence"] if item["kind"] == "constitution"]
        self.assertEqual(
            [item["id"] for item in clauses],
            ["constitution:v2#evidence-first", "constitution:v2#lexical-normalization"],
        )
        self.assertEqual(pack["constitution"]["selection_mode"], "cascade")
        self.assertEqual(pack["constitution"]["ratified_version"], "2.0")
        self.assertEqual(
            pack["constitution"]["clause_headings"]["constitution:v2#evidence-first"],
            "## 3. Principles",
        )
        validate_evidence_pack(pack, self.root)

    def test_unmatched_cascade_falls_back_to_the_whole_document_with_a_warning(self):
        pack = resolve_retrieval_spec(
            self.spec(filters={"topics": ["sourdough"]}, selectors={"pinned": [
                {"kind": "decision", "id": "mse_clauseproj01:d1", "reason": "fixture"}]}),
            self.root,
        )
        whole = [item for item in pack["evidence"] if item["kind"] == "constitution"]
        self.assertEqual([item["id"] for item in whole], ["docs/CONSTITUTION.md"])
        self.assertIn("constitution_whole_fallback", {item["code"] for item in pack["warnings"]})
        self.assertEqual(pack["constitution"]["selection_mode"], "fallback_whole")

    def test_whole_mode_opts_out(self):
        pack = resolve_retrieval_spec(self.spec(constitution={"mode": "whole"}), self.root)
        self.assertNotIn("constitution", pack)
        self.assertEqual(
            [item["id"] for item in pack["evidence"] if item["kind"] == "constitution"],
            ["docs/CONSTITUTION.md"],
        )

    def test_missing_explicit_anchor_fails_closed(self):
        from memory_seed.retrieval import RetrievalSpecResolutionError

        with self.assertRaises(RetrievalSpecResolutionError) as caught:
            resolve_retrieval_spec(
                self.spec(constitution={"anchors": ["constitution:v2#missing"]}), self.root
            )
        self.assertEqual(caught.exception.stage, "constitution_clauses")

    def test_related_adrs_join_by_topic_and_lend_their_bindings(self):
        from memory_seed.adr import ConstitutionRef, promote_decision

        result = promote_decision(
            self.root,
            adr_id="adr_retrieval_evidence",
            source_entry_id="mse_clauseproj01",
            source_decision="d1",
            title="Evidence before conclusions",
            topics=["retrieval"],
            user_initials="JN",
            agent_type="claude",
            source="derived",
            reason="fixture",
            impact="fixture",
            constitution_refs=[ConstitutionRef(ref="constitution:v2#append-only", role="governing")],
        )
        self.assertTrue(result.ok, result.issues)
        pack = resolve_retrieval_spec(self.spec(selectors={"related_adrs": True}), self.root)
        adrs = [item for item in pack["evidence"] if item["kind"] == "adr"]
        self.assertEqual([item["id"] for item in adrs], ["adr_retrieval_evidence"])
        self.assertIn("selectors.related_adrs", adrs[0]["selected_by"])
        self.assertEqual(adrs[0]["model_selection_reasons"], [])
        clause = next(item for item in pack["evidence"] if item["id"] == "constitution:v2#append-only")
        self.assertIn("constitution.adr_bindings", clause["selected_by"])
        validate_evidence_pack(pack, self.root)

    def test_pinned_roots_expand_from_a_pinned_decision(self):
        pinned = [{"kind": "decision", "id": "mse_clauseproj01:d1", "reason": "fixture"}]
        pack = resolve_retrieval_spec(
            self.spec(filters={"topics": []}, selectors={"pinned": pinned, "pinned_roots": True}),
            self.root,
        )
        decision = next(item for item in pack["evidence"] if item["id"] == "mse_clauseproj01:d1")
        self.assertIn("required.related_decisions", decision["selected_by"])


if __name__ == "__main__":
    unittest.main()
