"""Retrieval resolution stays fast without weakening confinement or change detection."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from memory_seed import retrieval
from memory_seed.retrieval import RetrievalSpecResolutionError, resolve_retrieval_spec
from memory_seed.retrieval_spec import normalize_retrieval_spec_v2
from memory_seed.semantic_cache import extract_memory_chunks

SPEC = {
    "schema": "memory-seed/retrieval-spec",
    "version": 2,
    "required": {"constitution": True, "related_decisions": {"depth": 1}, "evidence": {"mode": "latest"}},
}


def pinned(decision):
    return SPEC | {"selectors": {"pinned": [{"kind": "decision", "id": decision, "reason": "Fixture."}]}}


SESSION = """## 2026-08-01 09:00 - Deadline fixture

```yaml
entry_id: mse_deadline001
user_initials: JN
agent_type: claude
project_path: .
subproject_path: null
```

### Decision

- D: Resolve `retrieval_spec` quickly.
- R: Large corpora hit the deadline.
"""


class RetrievalDeadlineTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="memory-seed-deadline-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        (self.root / "docs").mkdir()
        (self.root / "docs" / "CONSTITUTION.md").write_text("# Constitution\n\nRules.\n", encoding="utf-8")
        sessions = self.root / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True)
        (sessions / "2026-08-01.md").write_text(SESSION, encoding="utf-8")

    def test_lexical_terms_opt_out_only_empties_that_field(self):
        full = extract_memory_chunks(self.root)
        lean = extract_memory_chunks(self.root, lexical_terms=False)
        self.assertTrue(full[0].lexical_terms)
        self.assertEqual(lean[0].lexical_terms, ())
        self.assertEqual(full[0].text, lean[0].text)
        # The opt-out is scoped to its call: a later default call is unaffected.
        self.assertTrue(extract_memory_chunks(self.root)[0].lexical_terms)

    def test_default_reader_detects_a_change_during_resolution(self):
        session = self.root / ".memory-seed" / "sessions" / "2026-08-01.md"
        original = retrieval._build_retrieval_plan
        calls = {"n": 0}

        def edit_during_first_attempt(*args, **kwargs):
            plan = original(*args, **kwargs)
            calls["n"] += 1
            if calls["n"] == 1:
                session.write_text(SESSION + "\n- Edited mid-resolution.\n", encoding="utf-8")
            return plan

        with mock.patch.object(retrieval, "_build_retrieval_plan", edit_during_first_attempt):
            pack = resolve_retrieval_spec(pinned("mse_deadline001:d1"), self.root)
        self.assertEqual(calls["n"], 2)
        normalized = normalize_retrieval_spec_v2(pinned("mse_deadline001:d1"))
        self.assertEqual(pack["corpus_revision"], retrieval._retrieval_corpus_revision(self.root, normalized))

    @unittest.skipUnless(sys.platform == "win32", "directory junctions are Windows-only")
    def test_junction_escaping_the_runtime_is_refused(self):
        outside = Path(tempfile.mkdtemp(prefix="memory-seed-deadline-outside-"))
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        (outside / "2026-08-02.md").write_text("# outside\n", encoding="utf-8")
        link = self.root / ".memory-seed" / "sessions" / "linked"
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True)
        if result.returncode != 0:
            self.skipTest("could not create a junction")
        self.addCleanup(lambda: os.rmdir(link))
        with self.assertRaises(RetrievalSpecResolutionError) as escaped:
            resolve_retrieval_spec(pinned("mse_deadline001:d1"), self.root)
        self.assertEqual(escaped.exception.code, "forbidden_path")

    def test_resolution_meets_the_default_deadline_on_this_repository(self):
        repo = Path(__file__).resolve().parents[1]
        pack = resolve_retrieval_spec(pinned("mse_nw47r0vpcj5tr2pj:d1"), repo)
        self.assertTrue(pack["evidence"])


if __name__ == "__main__":
    unittest.main()
