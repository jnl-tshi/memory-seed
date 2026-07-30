# Task 2 — M1 resolver and MCP vertical slice report

## Result

Completed and committed as:

```text
7b1c1bcc774a270caf915195baff97b2e3a757fa
feat: add retrieval spec M1 resolver
```

The implementation stays on `codex/feature/retrieval-specification-m0-m1` in the owned worktree at
base `fca2d8c93db66a14ad215127589958089afd6c57`.

## Architecture decisions

1. **One read-only service owns preview and resolution.**
   `preview_retrieval_spec()` and `resolve_retrieval_spec()` share normalization, reader invocation,
   candidate generation, ordering, limits, timeout checks, and the two-attempt corpus-revision gate in
   `memory_seed/retrieval.py`. CLI and MCP are thin adapters over that service.
2. **The resolver reuses canonical local readers and never calls ranking.**
   Session entries come from `extract_memory_chunks()`; topic attribution comes from
   `augment_chunks_with_topic_sidecars()` plus `expand_topic_filter()`; relationship traversal comes from
   `augment_chunks_with_link_sidecars()` plus `build_related_entry_graph()`; path evidence reuses the
   canonical session `F:` parser; Constitution and directly requested Markdown are read only from
   runtime-scoped canonical paths. No `search_memory()`, `rank_session_memory()`, semantic provider, or
   Trace module participates.
3. **Every emitted ref is Markdown-fetchable.**
   Session/decision evidence carries a canonical entry/decision `ref`, its Markdown `source`, line range,
   and a `fetch` recipe for `memory_get_chunk`. Constitution/direct-Markdown refs carry a runtime-relative
   path and line range. Non-Markdown path filters select session Markdown that cites the path; source files
   themselves are never emitted as evidence.
4. **Ordering and limits are deterministic.**
   Candidates follow the frozen order: required first, graph distance, newest session date, stable ref.
   Limits use a fixed provider-independent UTF-8 byte proxy, `ceil(bytes / 4)`. Truncation produces
   `completeness: "partial"` plus a warning; a limit that removes all coverage for any required clause
   fails with `required_limit_exceeded`.
5. **The corpus revision is content-addressed and race checked.**
   Revision identity combines Git HEAD when present with SHA-256 over the exact local Markdown families
   and topic index the resolver reads. Resolution compares start/end revisions, retries once at a fresh
   revision, then fails `corpus_changed`. Forbidden or out-of-runtime requested paths are excluded before
   revision hashing, so the revision reader cannot read outside scope.
6. **Packs are ephemeral.**
   Resolve returns the pack inline. No pack ID, cache, registry, persistence, or MCP `get` tool was added.
   `validate_evidence_pack()` is a local integrity seam for current-revision, effective-spec fingerprint,
   ordered-ref fingerprint, and fetchability checks; it stores nothing.
7. **M1 remains inline only.**
   The two MCP tools accept only `spec` and `cwd`. No profile, named-spec, composition, override, Task
   Packet schema, Trace, or provider API was introduced.

## Exact external payloads

### MCP preview

Tool:

```text
memory_retrieval_spec_preview
```

Input:

```json
{"spec": {"schema": "memory-seed/retrieval-spec", "version": 1, "...": "..."}, "cwd": "."}
```

Success:

```json
{
  "ok": true,
  "preview": {
    "preview_schema": "memory-seed/retrieval-spec-preview",
    "preview_version": 1,
    "resolver_version": 1,
    "valid": true,
    "corpus_revision": "git:<sha>:sha256:<digest>",
    "effective_spec": {},
    "effective_spec_fingerprint": "sha256:<digest>",
    "candidate_count": 0,
    "selected_count": 0,
    "omitted_count": 0,
    "token_estimate": 0,
    "warnings": [],
    "plan": [],
    "revision_attempt": 1,
    "write_surface": "read-only; no Evidence Pack created"
  }
}
```

`effective_spec`, counts, warnings, and plan contain the actual normalized values/results. Preview never
contains `pack_schema` and creates no pack.

### MCP resolve

Tool:

```text
memory_retrieval_spec_resolve
```

Input is the same inline-only `{"spec": {...}, "cwd": "."}` shape.

Success:

```json
{
  "ok": true,
  "pack": {
    "pack_schema": "memory-seed/evidence-pack",
    "pack_version": 1,
    "resolver_version": 1,
    "corpus_revision": "git:<sha>:sha256:<digest>",
    "effective_spec": {},
    "effective_spec_fingerprint": "sha256:<digest>",
    "completeness": "complete",
    "warnings": [],
    "evidence": [],
    "resolution_trace": [],
    "token_estimate": 0,
    "fingerprint": "sha256:<digest>"
  }
}
```

Each evidence item has exactly:

```json
{
  "ref": "mse_example:d1",
  "kind": "decision",
  "source": ".memory-seed/sessions/2026-07/2026-07-29.md",
  "line_range": [1, 20],
  "chunk_id": "mse_example",
  "session_date": "2026-07-29",
  "graph_distance": 1,
  "selected_by": ["required.related_decisions"],
  "reasons": ["related decision graph distance 1"],
  "token_estimate": 100,
  "fetch": {
    "tool": "memory_get_chunk",
    "arguments": {"chunk_id": "mse_example"}
  },
  "excerpt": null
}
```

Constitution/direct-Markdown evidence uses `chunk_id: null`, a canonical Markdown path as `ref`/`source`,
and `fetch: {"path", "line_start", "line_end"}`. `excerpt` is a string only when the frozen output flag
requests it.

### Error

Both MCP tools return:

```json
{
  "ok": false,
  "error": {
    "code": "invalid_spec|missing_required|forbidden_path|required_limit_exceeded|timeout|corpus_changed|...",
    "message": "...",
    "stage": "...",
    "completed_stages": [],
    "details": {}
  }
}
```

### CLI preview and canonical JSON

```text
memory-seed retrieval-spec preview --spec-file retrieval-spec.json --cwd .
```

The CLI prints the same preview wrapper as canonical compact UTF-8 JSON. Retrieval MCP tool text is also
canonical compact JSON (sorted keys and compact separators); the focused parity test compares the actual
JSON-RPC text bytes with CLI stdout at one corpus revision.

## Files changed

- `memory_seed/retrieval.py`
  - shared resolver/preview service
  - deterministic candidate model, ordering, limits, corpus revision/retry, timeout seam
  - Evidence Pack formatter/fingerprint and stale/fetchability validation
- `memory_seed/mcp_server.py`
  - inline-only preview/resolve tool schemas and adapters
  - canonical compact JSON text for the two retrieval tools
- `memory_seed/cli.py`
  - read-only `retrieval-spec preview --spec-file ... --cwd ...`
- `tests/test_retrieval_spec_resolver.py`
  - M1 synthetic corpus and acceptance/failure tests
- `tests/fixtures/retrieval-spec/m1-expected-pack.json`
  - frozen ordered refs and pack identity
- `docs/2_Todo/declarative-retrieval-specification-proposal.md`
  - inline-only Task Packet example, payload/error shape, deferred API boundary, review next action

No `.memory-seed/**`, dependency manifest, Trace, ranking implementation, profile/composition, or
unrelated file changed.

## Verification

### Final targeted gate

```text
$ python -m pytest tests/test_retrieval_spec.py tests/test_retrieval_spec_resolver.py \
    tests/test_retrieval.py tests/test_mcp_server.py tests/test_cli_help.py \
    tests/test_mcp_validation.py -q -p no:cacheprovider
119 passed, 17 subtests passed in 22.34s
```

The focused M1-only rerun after the frozen ordered-ref fixture:

```text
16 passed, 13 subtests passed in 1.99s
```

### Real repository topic-sidecar fixture through MCP

```json
{
  "ok": true,
  "refs": 16,
  "tokens": 11967,
  "completeness": "partial",
  "fingerprint": "sha256:e09a4ffe479388fff34d3485f2cd0c758a6a695e6088ebd5c900849f74f67dd0"
}
```

It is bounded by the fixture's 30-entry/12,000-token limits. The current real vocabulary does not define
`worktree-integration`, so the pack reports that warning; `session-fuse`, path evidence, link traversal,
and Constitution evidence still resolve. The broad current corpus yields 576 deterministic omissions,
reported as truncation rather than hidden.

### Root suite

```text
$ python -m pytest tests -q -p no:cacheprovider
4 failed, 797 passed, 1 skipped, 34 subtests passed in 212.16s
```

The four failures are outside the changed surface:

1. `test_links_check_skips_commit_existence_in_shallow_clone` — known Windows sandbox failure:
   Git `sh.exe` fails `CreateFileMapping ... Win32 error 5` during a local shallow clone.
2. Three `test_project_lifecycle.py` assertions concerning the pre-existing
   `graphify_analysis.md` seed/package-data/list mismatch.

Baseline classification: `git diff --quiet
fca2d8c93db66a14ad215127589958089afd6c57..7b1c1bcc774a270caf915195baff97b2e3a757fa`
passes for every involved source/test path (`memory_seed/core.py`, `pyproject.toml`,
`memory_seed/seed/.memory-seed/skills/graphify_analysis.md`, `tests/test_project_lifecycle.py`, and
`tests/test_links_check.py`). Therefore the exact code/data exercised by all four failures is
baseline-identical; no M1 file participates. The shallow-clone failure also matches the project's
already-recorded Windows sandbox constraint. I did not create another worktree solely to rerun those
identical paths.

A repository-wide bare `pytest` additionally collects `memory-trace/tests` and stopped with 21 collection
errors because this isolated worktree does not install `memory_trace` on `sys.path`. M1 deliberately does
not depend on Trace; the authoritative root-package suite above was rerun separately.

### Documentation and diff

```text
$ python -m memory_seed.cli docs check
Docs lifecycle OK (189 file(s) checked).
14 warning(s) - incomplete, not broken.

$ git diff --check
(no output)
```

All 14 documentation warnings are pre-existing incomplete-metadata warnings in unrelated active docs.

## No-write validation

- `test_preview_and_resolve_do_not_write_authoritative_memory` snapshots every file and byte under the
  synthetic `.memory-seed/` before preview/resolve and asserts exact equality afterward.
- The real repository MCP resolution was run after implementation; Git status remained clean after the
  commit, and no `.memory-seed/**` path appears in the commit.
- The resolution path calls only readers, hashing, local Git `rev-parse`, and pure formatting. It has no
  `write_text`, `write_bytes`, `open(..., write)`, directory creation, deletion, cache, or provider call.

## Self-review

- Confirmed every changed file is in the Task 2 allowed list.
- Confirmed the M0 normalizer remains the only schema authority and unsupported/deferred clauses still
  fail before selection.
- Confirmed `memory_search` code and ranking calls are untouched; existing retrieval/MCP parity tests pass.
- Confirmed both topic and link sidecar channels participate in the fixture, with authored and inferred
  topic provenance preserved by the existing readers.
- Confirmed forbidden control-directory and symlink-escape paths fail closed before file reading.
- Confirmed pack fingerprint identity includes schema/version, resolver version, corpus revision,
  effective-spec fingerprint, and ordered canonical refs.
- Confirmed stale validation recomputes effective-spec fingerprint, current corpus revision, pack
  fingerprint, source existence, and chunk fetchability.
- Confirmed profiles/named specs/Task Packet enforcement/Trace/providers/cache/get remain absent from tool
  schemas and code paths.

## Concerns

- Non-blocking corpus warning: the checked-in topic-sidecar request names `worktree-integration`, which is
  not currently in this repository's controlled vocabulary. The resolver reports it rather than silently
  accepting it, and the other declared selectors make the real pack usable.
- Non-blocking tooling limitation: Graphify structural extraction could not create ignored
  `graphify-out/` in this worktree because of a local Windows ACL (`WinError 5`), so structural review used
  Semble/direct source inspection plus the test suite.
- The broader root-suite failures listed above are baseline/environment issues, not M1 regressions.

## Fix round 1

Commit:

```text
e46c54b667e435296785f6cd0c158609c5489576
fix: enforce retrieval adapter contracts
```

### Finding 1 — runtime rejection of unsupported MCP arguments

- Added an exact runtime allowlist for both Retrieval Specification MCP tools: only `spec` and `cwd` are
  accepted.
- Raw JSON-RPC arguments such as `profile: "deferred"` and `unknown: 1` now return
  `ok: false`, `error.code: "invalid_arguments"`, and
  `details.unsupported_arguments: ["profile", "unknown"]`.
- Validation runs before reading `spec` and before calling preview/resolve. The behavior test patches the
  corresponding service function, sends raw JSON-RPC to both tools, and asserts the service was not
  called. This proves executable behavior rather than only inspecting `additionalProperties: false`.

### Finding 2 — exact CLI/MCP canonical JSON bytes

- Replaced CLI `print()` calls with `sys.stdout.write()` / `sys.stderr.write()`. No platform line ending is
  appended.
- The parity test no longer calls `.strip()`. It compares the complete CLI text to the complete MCP
  JSON-RPC tool text, compares their UTF-8 bytes, and asserts the CLI payload ends with neither `\r` nor
  `\n`.
- Both successful preview surfaces now return the exact canonical JSON document, with no trailing byte.

### Finding 3 — deadline covers revision hashing and final payload construction

- `_stable_retrieval_plan()` now carries the original start time forward and checks the deadline
  immediately after end-revision hashing.
- Preview checks again after building its final payload.
- Resolve checks again after building all evidence records and computing the pack fingerprint. A deadline
  crossed only during that final work now fails with `code: "timeout"` at `stage: "pack_format"` instead
  of returning a pack.
- The deterministic clock test keeps calls 1–9 inside the deadline (including the end-revision check) and
  crosses it only on call 10 after pack construction, proving the former gap is closed without a network,
  provider, or sleep.

### Commands and output

```text
$ python -m pytest tests/test_retrieval_spec_resolver.py -q -p no:cacheprovider
11 passed, 2 subtests passed in 2.08s

$ python -m pytest tests/test_retrieval_spec.py tests/test_retrieval_spec_resolver.py \
    tests/test_retrieval.py tests/test_mcp_server.py tests/test_cli_help.py \
    tests/test_mcp_validation.py -q -p no:cacheprovider
121 passed, 19 subtests passed in 23.31s

$ git diff --check
(no output)
```

Only `memory_seed/cli.py`, `memory_seed/mcp_server.py`, `memory_seed/retrieval.py`, and
`tests/test_retrieval_spec_resolver.py` changed in this fix round. No memory, ranking, Trace, profile,
composition, dependency, or unrelated surface changed.

## Final whole-branch repair

### Design decisions

1. **M0 remains the sole schema authority, and its frozen normal form is idempotent.**
   `normalize_retrieval_spec()` now accepts the normal form's explicit
   `optional.sessions: null` and empty normalized topic/path lists. Omitted sessions still normalize to
   `null`; empty filters still select nothing; canonical JSON and fingerprint input are unchanged.
   Preview, resolve, and pack validation can therefore safely re-normalize the effective spec.
2. **Topic selection follows canonical sidecar precedence without losing decision attribution.**
   Resolver roots now preserve `(entry_id, decision_ordinal)` selectors. A non-empty topic sidecar is the
   current authority; authored entry topics are consulted only when no sidecar attribution exists. A
   `topic:d1` attribution seeds only `d1`, and traversal cycles cannot re-admit another decision from the
   same precisely filtered root.
3. **Related-decision traversal composes entry and decision graphs locally.**
   Link-sidecar augmentation now retains canonical `MemoryChunk.decision_edges`. The M1 resolver keeps the
   existing bidirectional `RelatedEntryNode` traversal for bare entry edges and layers deterministic
   forward/inverse decision-edge traversal over it, honoring both source and target ordinals. The shared
   entry graph and ranking implementation were not changed.
4. **Fetch recipes and token bounds describe the same bytes.**
   Decision evidence now emits canonical Markdown path/line recipes for the exact decision section and
   estimates that fetched slice, instead of estimating a decision and fetching its entry chunk. Entry,
   Constitution, and direct-Markdown evidence retain their appropriate canonical recipes. The pack total
   remains the sum of per-item UTF-8 `ceil(bytes / 4)` proxies, and multiple decisions never duplicate one
   entry-level chunk fetch.
5. **Lifecycle wording stays active and manual-merge truthful.**
   The plan and proposal now say M0/M1 are implemented on a review branch, the bounded repair is complete,
   whole-branch re-review remains, and landing requires explicit user approval for manual merge. Neither
   document claims merge, landing, or shipping. Generated Todo/front-door indexes were regenerated from
   that state.

### Exact commands and output

```text
$ python -m memory_seed.cli worktree guard --agent codex --write-intent
Classification: owned-worktree
Severity: ok
Safe to write: yes
HEAD: 340d365b6cef05a633d1c2c098d6370faa80964f
Dirty: no

$ python -B -m pytest tests/test_retrieval_spec.py tests/test_retrieval_spec_resolver.py -q -p no:cacheprovider
23 passed, 15 subtests passed in 4.05s

$ python -B -m pytest tests/test_retrieval_spec.py tests/test_retrieval_spec_resolver.py \
    tests/test_retrieval.py tests/test_mcp_server.py tests/test_cli_help.py \
    tests/test_mcp_validation.py -q -p no:cacheprovider
126 passed, 19 subtests passed in 52.83s

$ python -B -m memory_seed.cli docs index
Regenerated:
  - docs/2_Todo/README.md
  - docs/README.md

$ python -B -m memory_seed.cli docs index --check
Docs index is current.

$ python -B -m memory_seed.cli docs check
Docs lifecycle OK (189 file(s) checked).
14 warning(s) - incomplete, not broken.

$ git diff --check
(no output)

$ git diff --name-only -- .memory-seed
(no output)
```

The focused gate includes the exact raw CLI/MCP canonical-byte parity regression. It also includes the
existing retrieval tests that exercise `memory_search`; no search/ranking symbol changed in this repair.
The new regressions directly cover normalized-spec preview/resolve, authoritative sidecar precedence,
decision-only topic selection, decision-sidecar depth traversal, exact target ordinals, fetch/token
agreement, aggregate bounds, and duplicate entry-fetch prevention.

### Residual concerns

- `docs check` still reports the same 14 incomplete-metadata warnings in unrelated Todo documents; it
  exits successfully and reports no broken lifecycle state.
- The fixed UTF-8 byte proxy is intentionally tokenizer/provider independent. It is now exact with respect
  to the bytes named by each fetch recipe, but it remains a proxy rather than a provider token count.
- Profiles, composition, Trace, cache/get, providers, Task Packet schema binding, and advanced selectors
  remain intentionally deferred. The branch remains manual-merge only and is not landed or shipped.
