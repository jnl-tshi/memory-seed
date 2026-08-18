import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import amend_topic_sidecar, check_session_links
from memory_seed.retrieval import entry_topic_sidecars


ENTRY_ID = "mse_0123456789abcdef"


class TopicAmendTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-topic-amend-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        memory = self.cwd / ".memory-seed"
        (memory / "sessions").mkdir(parents=True)
        (memory / "topics.yaml").write_text(
            """schema_version: 3
topics:
  area:
    graph:
      aliases: []
    schema:
      aliases: [model]
  activity:
    feature-build:
      aliases: []
    testing:
      aliases: []
""",
            encoding="utf-8",
        )
        (memory / "sessions" / "2026-07-01.md").write_text(
            f"""## 2026-07-01 09:00 - Two decisions

```yaml
entry_id: {ENTRY_ID}
user_initials: JN
agent_type: codex
```

### Summary

- Fixture.

### Decisions

#### D1 - First

- D: First.
- R: Because.

#### D2 - Second

- D: Second.
- R: Because.
""",
            encoding="utf-8",
        )
        sidecar = memory / "sessions" / "topics" / "2026-07" / "2026-07-01.md"
        sidecar.parent.mkdir(parents=True)
        sidecar.write_text(
            f"""---
tags:
  - session-log-topics
topic_date: 2026-07-01
---

## 2026-07-01 10:00 - Initial attribution

```yaml
entry_id: {ENTRY_ID}
source: derived
topics:
  area:
    - schema:d1
    - graph:d2
  activity:
    - feature-build:d1
    - testing:d2
```
""",
            encoding="utf-8",
        )

    def test_amend_restates_siblings_and_latest_snapshot_wins(self):
        result = amend_topic_sidecar(
            cwd=self.cwd,
            entry_id=ENTRY_ID,
            decision="d1",
            area="graph",
            activities=["testing"],
            reason="comment audit corrects the decision's area",
        )

        self.assertTrue(result.ok, result.issues)
        self.assertTrue(result.written)
        self.assertEqual(result.timestamp, "2026-07-01 10:01")
        sidecar = result.path.read_text(encoding="utf-8")
        self.assertIn("## 2026-07-01 10:00 - Initial attribution", sidecar)
        self.assertIn("## 2026-07-01 10:01 - Amend decision topics", sidecar)
        self.assertIn("source: human-amendment", sidecar)
        read = entry_topic_sidecars(self.cwd)[ENTRY_ID]
        self.assertEqual(read["decision_topics"], (("d1", "graph"), ("d2", "graph"), ("d1", "testing"), ("d2", "testing")))
        self.assertTrue(check_session_links(cwd=self.cwd).ok, check_session_links(cwd=self.cwd).issues)

    def test_amend_rejects_an_alias_without_writing(self):
        result = amend_topic_sidecar(
            cwd=self.cwd,
            entry_id=ENTRY_ID,
            decision="d1",
            area="model",
            activities=["testing"],
            reason="must use the canonical topic",
        )

        self.assertFalse(result.ok)
        self.assertIn("alias", " ".join(result.issues))
        sidecar = self.cwd / ".memory-seed" / "sessions" / "topics" / "2026-07" / "2026-07-01.md"
        self.assertNotIn("Amend decision topics", sidecar.read_text(encoding="utf-8"))

    def test_dry_run_has_no_write_and_renders_the_complete_snapshot(self):
        result = amend_topic_sidecar(
            cwd=self.cwd,
            entry_id=ENTRY_ID,
            decision="d1",
            area="graph",
            activities=["testing"],
            reason="preview the correction",
            dry_run=True,
        )

        self.assertTrue(result.ok, result.issues)
        self.assertFalse(result.written)
        self.assertIn("- graph:d2", result.rendered)
        self.assertNotIn("Amend decision topics", result.path.read_text(encoding="utf-8"))
