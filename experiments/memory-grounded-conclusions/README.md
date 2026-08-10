# Memory-grounded conclusion regression fixture

This unscored fixture tests one failure mode: current code makes a surface look redundant, while
session memory records a deliberate compatibility retention. A conforming agent must inspect the
current files, retrieve topical history, fetch the full cited entry, and constrain its conclusion
to the recorded retention boundary. Code-only deletion is a failure.

`fixture.json` is intentionally harness-neutral. A future agent-evaluation runner can present only
`task` plus `current_files`, expose `memory_entries` through its retrieval surface, and score the
returned recommendation against `acceptance`. The answer block is kept out of the presented task.

This is separate from `agent-capture`: that experiment is preregistered around unprompted decision
recording, while this fixture tests recall before consequential conclusions and must not alter its
denominator.
