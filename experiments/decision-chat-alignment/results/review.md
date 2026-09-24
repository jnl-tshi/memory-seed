# Decision-to-chat alignment review

Sample: 50 decisions; seed `20260924`; candidate sessions start within 72h before the decision (plus 2h clock drift);
source window `+/-2` turns around the strongest turn.

## 1. ms-5c3b8e12:d2 - No match

- Decision timestamp: `2026-05-29T13:50:00+00:00`
- Decision source: `.memory-seed/sessions/2026-05/2026-05-29.md:203`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Ship the control-plane version bump as a separate patch release (2.2.1) rather than rolling it into 2.2.0.
- R: 2.2.0 was already published. The version bump is a mechanical change with clear standalone value — it enables `memory-seed update` to propagate DRAFT improvements to existing projects.
- F: `core.py` VERSION, all 26 seed/installed `.md` frontmatter files, `pyproject.toml`, `tests/test_memory_seed.py`.
```

## 2. ms-a8d0fc47:d1 - No match

- Decision timestamp: `2026-06-14T07:33:00+00:00`
- Decision source: `.memory-seed/sessions/2026-06/2026-06-14.md:18`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Shipped 2.6.0 as three logical commits on `main` (`0249b0a` release product + control plane; `6a7efe9` docs/todo roadmap; `31bd1e6` dogfood configs + session logs), tagged `v2.6.0`, pushed, created the GitHub Release. `demo/` left untracked per convention. User approved the `pypi` manual-approval gate; PyPI went 2.5.0 → 2.6.0.
- R: User chose "2.6.0 (no bump)" + "split into logical commits". The publish.yml `pypi` environment gate is the user's to approve (irreversible OIDC push), which they did.
- A: Single squashed release commit (rejected — user wanted logical history).
- F: CHANGELOG.md (folded the Unreleased agent-selective bullet into 2.6.0, kept an empty `## Unreleased` placeholder for the public-docs test), plus the full 2.6.0 tree.
- T: 128 tests green; `doctor` healthy before tag.
```

## 3. ms-b72e3d40:d1 - No match

- Decision timestamp: `2026-05-29T14:19:00+00:00`
- Decision source: `.memory-seed/sessions/2026-05/2026-05-29.md:267`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Change `_MCP_SERVER_ARGS` to `["--from", "memory-seed", "memory-seed-mcp", "--stdio"]`.
- R: `uvx memory-seed-mcp` treats `memory-seed-mcp` as a PyPI package name and fails with "not found in registry". The PyPI package is `memory-seed`; `--from memory-seed` tells uvx which package provides the script. Verified with live MCP handshake — server responded correctly.
- A: `uvx memory-seed-mcp` (no --from) — fails; bare `memory-seed-mcp` — PATH-dependent, fails in Claude Code.
- F: `memory_seed/core.py`, `.claude/settings.json`, `.cursor/mcp.json`, `.gemini/settings.json`.
```

## 4. mse_0d1tkp3nhnw4edra:d1 - No match

- Decision timestamp: `2026-09-06T15:15:00+00:00`
- Decision source: `.memory-seed/sessions/2026-09/2026-09-06.md:481`
- Candidate session: `01a05ef9-96eb-7232-a0d7-71cf48d55c3a`
- Conversation timestamp: `2026-09-03T21:34:22.473000+00:00`
- Source: `.codex/sessions/2026/09/03/rollout-2026-09-03T22-34-22-01a06931-bcab-7d21-aa13-6797877d7f87.jsonl`
- Evidence: score 0.199; TF-IDF 0.029; phrase 3 tokens; time 8.2h; actor compatible
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: no sufficiently similar conversation window in the temporal candidate set
- Second best: `01a05ef9-96eb-7232-a0d7-71cf48d55c3a` (score 0.199; TF-IDF 0.029; phrase 3 tokens; time 8.2h; actor compatible)

Decision record:

```text
- D: Write DRAFT decisions in plain language by default, define necessary technical terms, preserve the context needed to understand or challenge the decision, and remove repetition or ornamental jargon.
- R: Compact durable memory is easier to retrieve and use, but brevity must not erase constraints, uncertainty, or decisive reasoning.
- A: A rigid word limit was rejected because the necessary detail varies by decision and mechanical truncation could remove meaning.
- F: `.memory-seed/skills/session_logging.md`; `memory_seed/seed/.memory-seed/skills/session_logging.md`.
- T: Live and Seed bytes match; focused session-schema tests and `git diff --check` pass.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..3`
- JSONL ordinals `[5, 9, 13, 14, 21, 28, 36, 37, 44, 51, 58, 64, 71, 78, 85, 92, 103, 124, 134, 146, 147, 157, 176, 183, 190, 197, 204, 211, 218, 225, 232, 243, 250, 264, 271, 275, 276, 291, 298, 307, 322, 323, 330, 337, 348, 355, 362, 369, 376, 387, 394, 401, 413, 420, 424, 425, 432, 447, 454, 462, 463, 470, 477, 485]`
- messages `64`; SHA-256 `8fb7d90c53ee5409c6854fd06924d2466717595a873f7e4ed68ce8752171dc5e`

## 5. mse_0jqvb23gtregyt6t:d1 - No match

- Decision timestamp: `2026-07-28T08:30:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-28.md:107`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: `TraceService.ontology()` emits `{axis: [OntologyNode, ...]}` where a node is
  `{id, name, count, total, children}` - the same shape at every depth. Added to the `Facets` model and
  the v1 contract; `openapi.v1.json` and `types.ts` regenerated.
- R: The client could not build a tree from what was served. `topic_roots` answers "which root owns this
  slug" and **deliberately collapses everything between**, so there were no parent edges and no axis - a
  navigator has to draw exactly what that map throws away.
  Keyed BY AXIS rather than returned as one forest because the axes answer different questions and are
  navigated one at a time. JNL's requirement that "additional ontology types could be added later by
  extending the toggle" is then literally true: a third axis is a third key, and the toggle is built from
  `Object.keys`.
  **`total` rather than `count` is what the UI shows.** Selecting a node returns its whole subtree, so
  printing the node's own count beside a parent whose children hold most of the corpus would make the
  number disagree with the result it produces. `memory-trace` reads 200, not 78.
  Aliases are excluded: they are spellings, not concepts, and listing `memory-trace-ui` beside
  `memory-trace` offers two doors into one room.
- F: `memory-trace/memory_trace/service.py`, `models.py`, `tests/contract/{openapi.v1.json,types.ts}`.
- T: Live `/api/v1/facets` serves 18 area roots and 12 activity roots, three levels deep
  (`memory-trace > panes > inspector`).
```

## 6. mse_1gcbzv5w9cgw7bga:d1 - No match

- Decision timestamp: `2026-07-20T17:49:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-20.md:1137`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Added two tests to `tests/test_session_schema.py` asserting seed-side consistency in both
  directions: every `- skill: <name>` in the seed trigger registry has both a file under
  `memory_seed/seed/.memory-seed/skills/` and a `SeedFile` destination in `core.SEED_FILES`; and every
  `.memory-seed/skills/*.md` destination in `SEED_FILES` (excluding `index.md`, which is the registry
  itself) is registered. Two module-level helpers extract the name lists.
- R: This closes the gap that let `developer-rendered-ui-debugging.md` ship as a registry entry with no
  installed file - a fresh `memory-seed init` wrote a trigger map pointing at a skill it never
  installed. The existing `test_universal_registry_entries_have_live_and_seed_skill_files` *looks* like
  it covers direction 1, but its `if "persona:" in body: continue` skips exactly the persona entries
  the defect lived in, and it never consults `SEED_FILES` at all. The new tests deliberately drop that
  skip and are seed-only: the skip is legitimate for the live runtime (optional/persona skills are
  installed conditionally) but wrong for the seed, which ships everything unconditionally. Left the
  live-runtime side to the existing test rather than widening it.
- A: Considered the derived-list refactor the gap really argues for - adding a skill still needs manual
  edits in five places (`SEED_FILES`, `pyproject.toml` package-data, the expected-destinations list in
  `test_memory_seed.py`, `SKILL_PROFILES`, `SKILL_DESCRIPTIONS`). Out of scope here; the test makes the
  most damaging of those five drift loud, and the refactor stays a separate call.
- F: `tests/test_session_schema.py` (only changed file; uncommitted).
- T: `python -m pytest tests -q` - 641 passed, 14 subtests passed. A green run proves nothing on its own
  here, since all three legs are currently consistent, so verified the tests actually bite by mutating
  each leg in isolation and confirming the matching assertion fires: (A) `SeedFile` entry removed ->
  fails on the `SEED_FILES` assert; (B) seed skill file deleted -> fails on the exists assert;
  (C) registry entry removed -> fails the reverse-direction test. All restored. The restore script's
  `write_text` silently converted three files from LF to CRLF (invisible to `git diff`, which
  normalises); caught it in `git status` and rewrote the bytes.
```

## 7. mse_25zzy3cmdjgrsf69:d4 - No match

- Decision timestamp: `2026-07-26T20:14:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-26.md:2237`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: `licensing` was promoted to a child of `tooling-evaluation` despite the flag that licensing is not
  a kind of tooling evaluation, and `audit` was moved from an alias of `documentation` to an alias of
  the new child `functionality-audit`. `design-evaluation` was promoted as the less lossy of two
  imperfect options, with a note that it is the first candidate to move if an `evaluation` parent is
  ever earned.
- R: Both calls turned on reading the actual entries rather than the slug names. The parent's own
  description says "External tool/library assessment and licensing checks", and the single entry
  writing `licensing` ("Triage dev-tools reel: adopt Fontjoy, reference fffuel and 21st.dev") is
  licence triage of external tools - exactly what the parent claims. For `audit`, the one entry that
  wrote it wrote `functionality-audit` alongside it in the same list, which is the corpus itself saying
  they are the same concept. `design-evaluation`'s entry is an internal design, so its parent's name is
  genuinely narrower than the family it collects - but as a child the term survives and re-parenting is
  a one-line edit, whereas as an alias it is discarded at every read.
- A: Flag `licensing` as wrong like the other three - rejected once the entry contradicted the
  suspicion.
- F: `.memory-seed/topics.yaml`
- T: The four judgment calls that turned on entry evidence (`licensing`, `audit`, `design-evaluation`,
  `topics`) were each checked against the authored `topics:` list and title of every entry using them;
  two of the four contradicted the incoming suspicion.
```

## 8. mse_4jbfzs490zcy9q06:d1 - No match

- Decision timestamp: `2026-08-31T16:44:00+00:00`
- Decision source: `.memory-seed/sessions/2026-08/2026-08-31.md:399`
- Candidate session: `01a0586d-acdd-7712-a9ac-cc47d26de49f`
- Conversation timestamp: `2026-08-31T15:26:17.993000+00:00`
- Source: `.codex/sessions/2026/08/31/rollout-2026-08-31T16-26-17-01a0586d-acdd-7712-a9ac-cc47d26de49f.jsonl`
- Evidence: score 0.186; TF-IDF 0.020; phrase 2 tokens; time 1.2h; actor compatible
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: no sufficiently similar conversation window in the temporal candidate set
- Second best: `01a0586d-acdd-7712-a9ac-cc47d26de49f` (score 0.186; TF-IDF 0.020; phrase 2 tokens; time 1.2h; actor compatible)

Decision record:

```text
- D: Standardized `context_load: packet`, a 100-250-token project frame, the six packet fields, orchestrator-materialized ADR/decision/policy/implementation evidence, all-inclusive worker token accounting, bounded supplemental retrieval, and orchestrator-owned durable memory with a guarded `worker_checkpoint` exception. Kept these as conventions rather than validated Task Packet API fields.
- R: Workers need targeted answer-bearing evidence without inherited discussion or broad fact-finding, while retaining equivalent task-applicable retrieval tools for bounded gaps. The current M1 resolver API is already sufficient to materialize the evidence and should not be broadened before pilot evidence justifies a schema change.
- A: Full-session preload was rejected because it spends context on discovery and inherited discussion. Schema-enforced packet fields or new MCP methods were rejected because the pilots can validate the procedure through existing inline preview/resolve surfaces.
- F: `.memory-seed/skills/agent_collaboration.md`, `memory_seed/seed/.memory-seed/skills/agent_collaboration.md`, `docs/2_Todo/declarative-retrieval-specification-proposal.md`, and `tests/test_session_schema.py`.
- T: Focused convention test, live/seed parity test, documentation check, and `git diff --check` passed. Independent task review approved the corrected two-commit range at `ce972a464001b7b7afbbb6032ecaddbee7bcf46a`.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..1`
- JSONL ordinals `[5, 9, 12, 18, 24, 30, 37]`
- messages `7`; SHA-256 `2d2ea1c6ab0b9aece90c823f19ed2e0b34bb1d1acfa3f7a7d6d344fbaf1b298c`

## 9. mse_76r59d5yxcqy0kb8:d2 - Low

- Decision timestamp: `2026-07-07T22:18:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-07.md:335`
- Candidate session: `019f3d0f-e0d9-7f33-a335-ee1a679f0137`
- Conversation timestamp: `2026-07-07T14:51:23.674000+00:00`
- Source: `.codex/sessions/2026/07/07/rollout-2026-07-07T15-51-23-019f3d0f-e0d9-7f33-a335-ee1a679f0137.jsonl`
- Evidence: score 0.230; TF-IDF 0.019; phrase 1 tokens; time 7.4h; branch match; actor compatible
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision wording may be rewritten, synthesized across turns, or weakly distinctive
- Second best: `none`

Decision record:

```text
- D: Add a shared `memory_seed.text_files` helper, `.editorconfig`, `.gitattributes`, README/changelog/audit documentation, MCP Unicode-preserving JSON output, and non-ASCII round-trip tests.
- R: Windows/default-code-page drift and BOMs were already observable in active files; central helpers plus repository config reduce future mojibake without adding the larger repair command yet.
- A: Did not implement `memory-seed encoding check` or `encoding repair`; those need conservative scan rules, backup behavior, and more tests.
- F: `.editorconfig`, `.gitattributes`, `memory_seed/text_files.py`, `memory_seed/core.py`, `memory_seed/cli.py`, `memory_seed/mcp_server.py`, `tests/test_text_files.py`, `tests/test_session_schema.py`, `README.md`, `CHANGELOG.md`, `docs/2_Todo/memory-seed-trace-upgrade-shutdown-plan.md`, `docs/2_Todo/completed/memory-seed-utf8-encoding-policy-phase-1.md`, `docs/2_Todo/utf8-encoding-doctor-and-static-check-plan.md`, `docs/2_Todo/NEXT_STEPS.md`, `docs/3_Spec/functionality-audit.md`.
- T: `python -m unittest discover -s tests` passed (247 tests); `python -m memory_seed.cli doctor` passed; `python -m memory_seed.cli links check` passed; `git diff --check origin/main...HEAD` passed; `PYTHONPATH=memory-trace python -m unittest discover -s memory-trace/tests` passed (33 tests).
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..1`
- JSONL ordinals `[3, 6]`
- messages `2`; SHA-256 `4fc484aac8442e745b33d500a243e955582f8356331791f33d60ec3f8685fda6`

## 10. mse_7twxefmtphr30604:d1 - Low

- Decision timestamp: `2026-07-16T07:51:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-16.md:185`
- Candidate session: `019f64ba-a828-7a83-909d-bef0998afdab`
- Conversation timestamp: `2026-07-15T07:43:07.213000+00:00`
- Source: `.codex/sessions/2026/07/15/rollout-2026-07-15T08-43-07-019f64ba-a828-7a83-909d-bef0998afdab.jsonl`
- Evidence: score 0.263; TF-IDF 0.035; phrase 3 tokens; time 8.1h; identifiers graph/workspace; actor compatible
- Unique: `False`
- Ambiguity: competitive second session
- Diagnostic failure mode: multiple conversations discuss similar material
- Second best: `019f64ba-a828-7a83-909d-bef0998afdab` (score 0.263; TF-IDF 0.035; phrase 3 tokens; time 8.1h; identifiers graph/workspace; actor compatible)

Decision record:

```text
- D: Treat the B0a shell slice as the completed first increment of the pre-React graph/workspace track; keep its branch-visible `--no-ff` merge and preserve its fused session evidence.
- R:
  - The workspace controls, fresh-worktree handling, specification update, and regression coverage form one coherent and validated workstream.
  - The repository is configured for local integration, so no remote push or PR is appropriate.
- F: Local merge commit `eae91d6ec339a69f8d9ad4e7616e518443e6508f`; fused `mse_eaxj1wwfse1weh18`; removed the merged local feature branch.
- T: `python -m unittest discover -s memory-trace/tests -p 'test_*.py'` passed 123 tests; `memory-seed links check`, `memory-seed topics check`, and `git diff --check` passed with pre-existing warnings only.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..1`
- JSONL ordinals `[3, 6, 11, 12, 19, 20, 24, 34, 35, 40, 41, 46, 51, 57, 58, 62, 66, 73, 74, 78, 83, 102, 103, 108, 112, 116, 120, 124, 126, 131, 136, 141, 146, 151, 156, 162, 163, 172, 176, 180, 184, 189, 190, 194, 204, 205, 210, 211, 215, 218, 223, 232, 237, 238, 242, 249]`
- messages `56`; SHA-256 `8606d6e1fed67e193d3b319895ca8884e6dddc6d27601584495584e7a1c6e5ef`

## 11. mse_8vvw4cq8y114tarw:d3 - No match

- Decision timestamp: `2026-07-22T22:04:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-22.md:1969`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Link distance is removed as a control and fixed at 150 (the old cose `idealEdgeLength`).
- R: JNL's call: repel, link and centre are what a graph like this needs. Link distance and link
  force are two ways of telling a reader the same thing - both change how close connected nodes sit -
  and offering both invites fiddling with two dials that fight each other. Obsidian ships four; that
  does not make four right for this graph.
```

## 12. mse_992a3jfxfpnecpst:d1 - No match

- Decision timestamp: `2026-07-12T23:13:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-13.md:25`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: no sufficiently similar conversation window in the temporal candidate set
- Second best: `none`

Decision record:

```text
- D: Cleaned the remaining Codex worktrees from this repository by removing the three clean `.codex/worktrees/` directories after Git deregistered them: `codex-docs-agent-worktree-namespace-guard`, `codex-memory-trace-extra`, and `codex-docs-trace-release-strategy-cleanup`.
- R: The first two were fully merged stale candidates, and the cleanup branch was clean with its useful docs already reconciled onto `main`; removing the worktree directories reduces stale-agent workspace confusion without deleting branch refs.
- A: `git worktree remove` deregistered the Codex worktrees but Windows denied directory and metadata deletion, so the leftover `.codex/worktrees/*` and `.git/worktrees/*` Codex directories were removed after verifying each absolute path stayed inside this repository. Claude worktrees and Claude metadata were left untouched.
- F: `.codex/worktrees/codex-docs-agent-worktree-namespace-guard`, `.codex/worktrees/codex-memory-trace-extra`, `.codex/worktrees/codex-docs-trace-release-strategy-cleanup`, `.git/worktrees/codex-docs-agent-worktree-namespace-guard`, `.git/worktrees/codex-memory-trace-extra`, `.git/worktrees/codex-docs-trace-release-strategy-cleanup`.
- T: `git worktree list --porcelain` now shows only the primary `main` worktree and the locked Claude worktree; `.codex/worktrees` is empty; `git status --short --branch` remains clean on `main`.
```

## 13. mse_9h3a9wybc2p0sfb6:d1 - Low

- Decision timestamp: `2026-09-14T01:31:00+00:00`
- Decision source: `.memory-seed/sessions/2026-09/2026-09-14.md:25`
- Candidate session: `01a09d7b-e85d-7032-9aa3-eaae80a389ce`
- Conversation timestamp: `2026-09-14T01:15:38.688000+00:00`
- Source: `.codex/sessions/2026/09/14/rollout-2026-09-14T02-15-38-01a09d7b-e85d-7032-9aa3-eaae80a389ce.jsonl`
- Evidence: score 0.367; TF-IDF 0.098; phrase 4 tokens; time 0.3h; identifiers agents.md, codex/hooks.json, hooks.json; actor compatible
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision wording may be rewritten, synthesized across turns, or weakly distinctive
- Second best: `01a09d55-63ec-7b60-b798-70d6e888b869` (score 0.304; TF-IDF 0.082; phrase 4 tokens; time 1.0h; identifiers agents.md, codex/hooks.json; actor compatible)

Decision record:

```text
- D: Add project-local Context Mode callbacks for SessionStart, UserPromptSubmit, Stop, PostToolUse, and PreCompact, plus a bounded AGENTS.md routing section; intentionally leave PreToolUse absent.
- R: Context Mode only saves tokens when agents route large or unpredictable analysis through its MCP tools, while PostToolUse and prompt/turn capture provide the event stream needed for compaction continuity. Excluding PreToolUse avoids rewriting or denying ordinary shell, patch, search, write, and MCP operations.
- A: Enabling the full bundled plugin hook set was rejected for this repair because its broad PreToolUse matcher is more invasive than the user requested. Relying on PostToolUse and PreCompact alone was also rejected because it supplies no startup routing or post-compaction restoration.
- F: `AGENTS.md`, `.codex/hooks.json`.
- T: Parsed hooks.json as JSON; git diff whitespace check passed; verified exactly one advisory routing block, five Context Mode lifecycle hooks, six preserved Memory Seed hooks, no PreToolUse hook, and a successful Context Mode SessionStart routing response.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..1`
- JSONL ordinals `[5, 13, 14, 21, 28, 35, 42, 48, 55, 62, 71, 72, 79, 86, 93, 100, 107, 114, 121, 128, 135, 142, 149, 156, 163, 170, 177, 185, 186, 193, 200, 207, 214, 221, 228, 235, 242, 250, 251, 258, 265, 274, 280, 286, 293, 302, 303, 310, 316, 323, 330, 337, 343, 350, 358, 367, 375, 376, 383, 394, 401, 408, 415, 422, 429, 436, 446, 447, 454, 460, 467, 474, 481, 488, 495, 503, 510, 518, 519, 529]`
- messages `80`; SHA-256 `c6a4b764a3bb9c651d9cd22f20a9a29a257d641de57bae87ce7891cd99e272b0`

## 14. mse_9m2jk06hgx7ctrm1:d2 - No match

- Decision timestamp: `2026-07-05T01:27:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-05.md:174`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Updated `3.0-plan.md`'s status header and Recommended Sequencing: item 4 (graph edge contract)
  is done as of 2026-07-04 (`docs/graph-edge-contract.md`); the two remaining items — related-entries
  P2 (needs sign-off + acceptance criteria; mutation surface) and Pillar B distribution — are
  explicitly marked BLOCKED on user decisions. Mermaid node updated to match (semantic freshness per
  the Mermaid guidance principle).
- R: Goal rule: shipped 2.9–2.15 work must not be reopened; unscoped work must not be coded.
- F: `docs/todo/3.0-plan.md`.
```

## 15. mse_a0bxp5n1wcnsjxvw:d2 - No match

- Decision timestamp: `2026-07-15T17:05:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-15.md:575`
- Candidate session: `019f64ba-a828-7a83-909d-bef0998afdab`
- Conversation timestamp: `2026-07-15T07:43:07.213000+00:00`
- Source: `.codex/sessions/2026/07/15/rollout-2026-07-15T08-43-07-019f64ba-a828-7a83-909d-bef0998afdab.jsonl`
- Evidence: score 0.199; TF-IDF 0.015; phrase 2 tokens; time 6.7h; identifiers b0a/b0b; actor compatible
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: no sufficiently similar conversation window in the temporal candidate set
- Second best: `019f64ba-a828-7a83-909d-bef0998afdab` (score 0.199; TF-IDF 0.015; phrase 2 tokens; time 6.7h; identifiers b0a/b0b; actor compatible)

Decision record:

```text
- D: Add a non-binding candidate hosted settlement contract: project-owned hosted writes become durable only in append-only Markdown/YAML; concurrent conflicts are explicit; queues are idempotent; hosted project-memory projections must pass wipe/rebuild equivalence; complete export and local continuation survive expiry.
- R: Constitution Invariant #6 applies to hosted collaboration as well as local caches. Provider-owned evidence and server-owned authentication/billing remain separate authority domains rather than project-memory truth.
- A: Hosted implementation remains deferred. The candidate contract requires an explicit tier decision, security review, fixture proof, maintainer approval, and promotion into `3_Spec/`.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..1`
- JSONL ordinals `[3, 6, 11, 12, 19, 20, 24, 34, 35, 40, 41, 46, 51, 57, 58, 62, 66, 73, 74, 78, 83, 102, 103, 108, 112, 116, 120, 124, 126, 131, 136, 141, 146, 151, 156, 162, 163, 172, 176, 180, 184, 189, 190, 194, 204, 205, 210, 211, 215, 218, 223, 232, 237, 238, 242, 249]`
- messages `56`; SHA-256 `8606d6e1fed67e193d3b319895ca8884e6dddc6d27601584495584e7a1c6e5ef`

## 16. mse_a0bxp5n1wcnsjxvw:d4 - Low

- Decision timestamp: `2026-07-15T17:05:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-15.md:587`
- Candidate session: `019f64ba-a828-7a83-909d-bef0998afdab`
- Conversation timestamp: `2026-07-15T07:43:07.213000+00:00`
- Source: `.codex/sessions/2026/07/15/rollout-2026-07-15T08-43-07-019f64ba-a828-7a83-909d-bef0998afdab.jsonl`
- Evidence: score 0.279; TF-IDF 0.036; phrase 2 tokens; time 6.7h; identifiers b0a/b0b, docs/2_todo/0_next_steps.md, docs/2_todo/memory-trace-graph-and-workspace-proposal-set-index.md, docs/2_todo/memory-trace-next-generation-coverage-matrix.md, docs/2_todo/memory-trace-next-generation-implementation-roadmap.md; actor compatible
- Unique: `False`
- Ambiguity: competitive second session
- Diagnostic failure mode: multiple conversations discuss similar material
- Second best: `019f64ba-a828-7a83-909d-bef0998afdab` (score 0.279; TF-IDF 0.036; phrase 2 tokens; time 6.7h; identifiers b0a/b0b, docs/2_todo/0_next_steps.md, docs/2_todo/memory-trace-graph-and-workspace-proposal-set-index.md, docs/2_todo/memory-trace-next-generation-coverage-matrix.md, docs/2_todo/memory-trace-next-generation-implementation-roadmap.md; actor compatible)

Decision record:

```text
- D: Update the next-steps brief, Phase 0-10 roadmap, coverage matrix, architecture blueprint, annotation/provider plans, deferred hosted plan, draft-spec index, and docs front door to one sequence and lifecycle state.
- R: Agents read these surfaces as planning authority; leaving graph-after-React, hosted-as-active, or no-proposals-promoted statements would reintroduce contradictory instructions.
- F: `docs/2_Todo/0_NEXT_STEPS.md`, `docs/2_Todo/memory-provenance-and-authority-taxonomy-proposal.md`, `docs/2_Todo/memory-quality-metrics-v0-proposal.md`, `docs/2_Todo/memory-trace-evidence-annotations-and-projection-architecture.md`, `docs/2_Todo/memory-trace-graph-and-workspace-proposal-set-index.md`, `docs/2_Todo/memory-trace-graph-visualisation-and-temporal-topology-proposal.md`, `docs/2_Todo/memory-trace-next-generation-coverage-matrix.md`, `docs/2_Todo/memory-trace-next-generation-implementation-roadmap.md`, `docs/2_Todo/memory-trace-product-and-system-architecture-blueprint.md`, `docs/2_Todo/memory-trace-structural-graph-enrichment-provider-proposal.md`, `docs/2_Todo/memory-trace-three-region-workspace-and-dockable-inspector-proposal.md`, `docs/3_Spec/draft/README.md`, `docs/3_Spec/draft/memory-trace-hosted-markdown-settlement-contract.md`, `docs/8_Deferred/memory-trace-hosted-product-and-security-architecture.md`, `docs/README.md`.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..1`
- JSONL ordinals `[3, 6, 11, 12, 19, 20, 24, 34, 35, 40, 41, 46, 51, 57, 58, 62, 66, 73, 74, 78, 83, 102, 103, 108, 112, 116, 120, 124, 126, 131, 136, 141, 146, 151, 156, 162, 163, 172, 176, 180, 184, 189, 190, 194, 204, 205, 210, 211, 215, 218, 223, 232, 237, 238, 242, 249]`
- messages `56`; SHA-256 `8606d6e1fed67e193d3b319895ca8884e6dddc6d27601584495584e7a1c6e5ef`

## 17. mse_bfaa3ef75wgccys2:d3 - No match

- Decision timestamp: `2026-07-27T01:24:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-27.md:548`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: The root slot table is built exactly as before; the focused family's members are appended after it.
- R: The first version expanded into the ordered table, and its own test caught the consequence
  immediately: `memory-trace` moved from `#0a9a94` to `#43bdd4` merely because `git-workflow` was
  focused. That is precisely the instability that put colour on the root in the first place — an
  ordered table means an inserted key shifts every slot after it and repaints communities that did not
  change. Appending makes focusing a strictly additive operation.
- A: Sort the whole table with children included — rejected on the same measurement; it is the
  interleaving that does the damage, not the ordering rule.
- F: `memory-trace/client/src/graphCommunities.ts`, `graphCommunities.test.ts`.
```

## 18. mse_bz03mjc3mvxk8t68:d3 - No match

- Decision timestamp: `2026-07-22T00:08:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-22.md:245`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: `test_extracted_lazy_skills_are_registered_seeded_and_standalone` required the literal phrase
  "invisible `~~~` links"; it now requires "`subgraph` Is Not Parsed In Sidecars" and "is the only
  arrow that works".
- R: The test pins representative phrases so a skill cannot be gutted silently. It was pinning the
  exact sentence this change deletes, so it failed by design and the fix is to re-anchor it, not to
  weaken it. The new anchors were chosen to pin the two claims that carry the change — the
  prohibition and the single-arrow rule — so a future edit that quietly reinstates subgraphs trips it.
- A: Left `memory-system-version: 2.19` alone; nothing required a bump and it would be a delta the
  brief did not ask for.
```

## 19. mse_caj7ys6j6zbxp5rk:d1 - Low

- Decision timestamp: `2026-09-19T08:37:00+00:00`
- Decision source: `.memory-seed/sessions/2026-09/2026-09-19.md:102`
- Candidate session: `01a0b600-7c89-70f2-a85a-c57aad5c5b26`
- Conversation timestamp: `2026-09-18T19:31:20.495000+00:00`
- Source: `.codex/sessions/2026/09/18/rollout-2026-09-18T20-31-20-01a0b600-7c89-70f2-a85a-c57aad5c5b26.jsonl`
- Evidence: score 0.384; TF-IDF 0.134; phrase 3 tokens; time 13.1h; identifiers 1.zip, codex/docs/hosted-mvp-programme, docs/1_inbox/memory-seed-hosted-proposals/, docs/1_inbox/memory-seed-proposals, docs/1_inbox/memory-seed-proposals.zip; actor compatible
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision wording may be rewritten, synthesized across turns, or weakly distinctive
- Second best: `01a0b5c8-d457-7373-ba56-a59739634552` (score 0.230; TF-IDF 0.029; phrase 2 tokens; time 14.1h; actor compatible)

Decision record:

```text
- D: After live user confirmation, deleted the two byte-identical proposal ZIP files and the remaining untracked folder containing the same six source documents; `main` then reported a clean working tree. The guarded merge dry-run still refused before creating merge state because the Reflection worktree inventory called `lstat()` on an ignored experiment path whose absolute Windows path is 261 characters.
  - Scope: Primary-checkout cleanup and guarded integration state for `codex/docs/hosted-mvp-programme`.
- F: Removed `docs/1_Inbox/memory-seed-proposals.zip`, `docs/1_Inbox/memory-seed-proposals 1.zip`, and `docs/1_Inbox/memory-seed-hosted-proposals/` from the untracked primary-checkout residue; the six source payloads remain preserved in the branch's archived reference documents.
- T: `git status --short --untracked-files=all` returned no paths after cleanup. Two `session merge-branch --dry-run` attempts refused with `[WinError 3]`; direct reproduction identified `memory_seed/reflection_ledger.py::_check_reflection_worktree` line 2825 and confirmed no `.git/index.lock`, `MERGE_HEAD`, or `MERGE_MSG` was created.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `6..10`
- JSONL ordinals `[2633, 2639, 2640, 2648, 2653, 2660, 2665, 2672, 2675, 2680, 2681, 2690, 2691, 2697, 2703, 2710, 2711, 2722, 2730, 2739, 2740, 2749, 2757, 2765, 2766, 2774, 2784, 2790, 2797, 2798, 2804, 2812, 2820, 2828, 2836, 2844, 2852, 2858, 2865, 2866, 2874, 2882, 2890, 2896, 2904, 2910, 2918, 2926, 2932, 2939, 2940, 2948, 2956, 2968, 2976, 2982, 2990, 3003, 3004, 3012, 3018, 3026, 3034, 3042, 3050, 3056, 3064, 3072, 3080, 3090, 3098, 3105, 3113, 3121, 3129, 3137, 3145, 3151, 3158, 3159, 3165, 3171, 3178, 3179, 3187, 3196, 3204, 3209, 3210, 3220, 3230, 3238, 3248, 3256, 3276, 3277, 3283, 3291, 3299, 3311, 3321, 3332, 3333, 3341, 3349, 3357, 3369, 3381, 3389, 3396, 3404, 3410, 3417, 3419, 3425, 3431, 3438, 3439, 3445, 3453, 3459, 3465, 3472, 3473, 3479, 3485, 3491, 3498, 3499, 3505, 3511, 3517, 3523, 3530, 3531, 3537, 3549, 3557, 3565, 3573, 3581, 3589, 3597, 3603, 3611, 3619, 3627, 3640, 3641, 3647, 3653, 3659, 3669, 3675, 3681, 3690, 3691, 3697, 3703, 3709, 3715, 3722, 3723, 3729, 3735, 3741, 3748, 3749, 3755, 3761, 3767, 3774, 3775, 3781, 3787, 3793, 3800, 3801, 3807, 3813, 3819, 3826, 3827, 3833, 3839, 3845, 3852, 3853, 3859, 3865, 3871, 3878, 3879, 3885, 3891, 3897, 3904, 3905, 3911, 3917, 3923, 3930, 3931, 3937, 3943, 3949, 3956, 3957, 3966, 3967, 3973, 3979, 3985, 3992, 3993, 3999, 4005, 4012, 4013, 4019, 4025, 4032, 4033, 4039, 4045, 4052, 4053, 4059, 4065, 4072, 4073, 4079, 4085, 4092, 4093, 4099, 4105, 4112, 4113, 4119, 4125, 4132, 4133, 4139, 4145, 4151, 4158, 4159, 4165, 4171, 4178, 4179, 4185, 4191, 4198, 4199, 4205, 4211, 4218, 4219, 4225, 4231, 4238, 4239, 4245, 4251, 4258, 4259, 4265, 4271, 4278, 4279, 4285, 4291, 4298, 4299, 4305, 4311, 4318, 4319, 4325, 4331, 4338, 4339, 4345, 4351, 4358, 4359, 4365, 4371, 4378, 4379, 4385, 4391, 4398, 4399, 4405, 4411, 4418, 4419, 4425, 4431, 4438, 4439, 4445, 4451, 4458, 4459, 4465, 4471, 4478, 4479, 4485, 4491, 4498, 4499, 4505, 4511, 4518, 4519, 4525, 4531, 4538, 4539, 4545, 4551, 4558, 4559, 4565, 4571, 4578, 4579, 4585, 4591, 4598, 4599, 4605, 4611, 4618, 4619, 4625, 4631, 4638, 4639, 4645, 4652, 4653, 4659, 4665, 4672, 4673, 4679, 4685, 4692, 4693, 4699, 4705, 4712, 4714, 4720, 4726, 4733, 4734, 4740, 4746, 4753, 4754, 4760, 4767, 4768, 4774, 4780, 4787, 4788, 4794, 4800, 4807, 4808, 4814, 4820, 4827, 4828, 4834, 4840, 4847, 4848, 4854, 4860, 4867, 4868, 4874, 4881, 4882, 4888, 4894, 4901, 4902, 4908, 4914, 4921, 4922, 4928, 4934, 4941, 4942, 4948, 4954, 4961, 4962, 4968, 4977, 4978, 4984, 4990, 4996, 5004, 5012, 5020, 5029, 5030, 5038, 5046, 5054, 5062, 5069, 5077, 5084, 5092, 5104, 5112, 5120, 5129, 5130, 5140, 5153, 5154, 5160, 5166, 5173, 5174, 5180, 5186, 5194, 5200, 5206, 5212, 5219, 5220, 5226, 5232, 5239, 5240, 5246, 5252, 5259, 5260, 5266, 5273, 5280, 5281, 5290, 5291, 5299, 5305, 5311, 5318, 5319, 5325, 5332, 5339, 5345, 5351, 5357, 5364, 5365, 5371, 5377, 5384, 5385, 5391, 5397, 5404, 5405, 5411, 5417, 5424, 5425, 5431, 5440, 5441, 5457, 5467, 5477, 5483, 5489, 5496, 5497, 5504, 5510, 5518, 5519, 5525, 5534, 5540, 5545, 5546, 5555, 5556, 5564, 5571]`
- messages `510`; SHA-256 `77c6bce285580df1c34455f993b0b4a4c899a70b66083b6aa2e83c6b384f057b`

## 20. mse_dc48xabd9c2gg6pa:d1 - No match

- Decision timestamp: `2026-07-22T22:53:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-22.md:2097`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Changed the one message line in the 23:04 sidecar; no amendment entry against the broken one.
- R: `session_logging.md` freezes sidecars against edits "when later decisions supersede the entry" -
  the concern is rewriting history after a decision changes. A `;` that makes a block unparseable is
  not a changed decision; it is a transcription defect that stopped the record rendering *as made*.
  Repairing it makes the sidecar match what was authored, so the freeze rule does not reach it.
- A: The wording is preserved exactly - a comma and "and" in place of the semicolon. Both a comma and
  an em-dash parse; the comma was picked because the surrounding block already spends its em-dashes
  on asides.
```

## 21. mse_ddba1ztxqhasfbwf:d1 - No match

- Decision timestamp: `2026-07-16T22:18:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-16.md:1017`
- Candidate session: `019f64ba-a828-7a83-909d-bef0998afdab`
- Conversation timestamp: `2026-07-15T07:43:07.213000+00:00`
- Source: `.codex/sessions/2026/07/15/rollout-2026-07-15T08-43-07-019f64ba-a828-7a83-909d-bef0998afdab.jsonl`
- Evidence: score 0.207; TF-IDF 0.024; phrase 2 tokens; time 22.6h; identifiers memory-seed/index.md; actor compatible
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: no sufficiently similar conversation window in the temporal candidate set
- Second best: `019f64ba-a828-7a83-909d-bef0998afdab` (score 0.207; TF-IDF 0.024; phrase 2 tokens; time 22.6h; identifiers memory-seed/index.md; actor compatible)

Decision record:

```text
- D: Ratify Constitution v1.1 and make one append-only Markdown ADR sidecar authoritative for ADR
  promotion, stable identity, and lifecycle. Original and decision-update entries own rationale/evidence;
  current status, registries, indexes, databases, and Trace views are derived.
- R:
  - Explicit promotion and a compact lifecycle ledger provide a higher-signal decision corpus than repeated
    semantic inference over chronological entries.
  - Append-only Markdown preserves local ownership, direct human editing, attribution, and immutable source
    entries while allowing decisions to evolve.
- A: Rejected both a derived-only Decision Registry, which loses explicit promotion authority, and the
  original mutable generated YAML snapshot, which duplicated `current_status`, weakened direct editing, and
  could drift from transition evidence.
- F: `docs/CONSTITUTION.md`,
  `docs/5_Completed/constitution-1.1-partitioned-markdown-authority-amendment.md`,
  `docs/3_Spec/draft/adr-lifecycle-sidecar-contract.md`,
  `docs/2_Todo/memory-seed-semantic-record-and-signal-foundation-plan.md`, `.memory-seed/index.md`.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..1`
- JSONL ordinals `[3, 6, 11, 12, 19, 20, 24, 34, 35, 40, 41, 46, 51, 57, 58, 62, 66, 73, 74, 78, 83, 102, 103, 108, 112, 116, 120, 124, 126, 131, 136, 141, 146, 151, 156, 162, 163, 172, 176, 180, 184, 189, 190, 194, 204, 205, 210, 211, 215, 218, 223, 232, 237, 238, 242, 249]`
- messages `56`; SHA-256 `8606d6e1fed67e193d3b319895ca8884e6dddc6d27601584495584e7a1c6e5ef`

## 22. mse_fhdns7vy5pb316q3:d2 - No match

- Decision timestamp: `2026-07-05T19:00:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-05.md:994`
- Candidate session: `019f26b2-9813-7101-ac1c-baa49a3c8ad2`
- Conversation timestamp: `2026-07-03T06:37:53.882000+00:00`
- Source: `.codex/sessions/2026/07/03/rollout-2026-07-03T07-37-53-019f26b2-9813-7101-ac1c-baa49a3c8ad2.jsonl`
- Evidence: score 0.151; TF-IDF 0.024; phrase 2 tokens; time 95.9h; actor compatible
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: no sufficiently similar conversation window in the temporal candidate set
- Second best: `019f26b2-9813-7101-ac1c-baa49a3c8ad2` (score 0.151; TF-IDF 0.024; phrase 2 tokens; time 95.9h; actor compatible)

Decision record:

```text
- D: Moved the two inbox research proposals into completed as resolved source reports and created
  `docs/todo/risk-signaling-and-stop-triggers-plan.md` as the active implementation plan.
- R: The two proposals describe one behavior system: qualitative action tiers plus STOP categories.
  A single lazy-loaded skill is easier to route and avoids duplicating escalation rules.
- A: Did not promote the market-fit report, appendix, UI source learnings, or competitor analysis
  into todo; they remain source/reference material because their actionable recommendations are now
  represented by active or completed plans.
- F: `docs/todo/risk-signaling-and-stop-triggers-plan.md`,
  `docs/todo/completed/confidence-signaling-protocol-proposal.md`,
  `docs/todo/completed/stop-trigger-taxonomy-proposal.md`.
- T: `python -m memory_seed.cli links check` OK (26 files); `python -m memory_seed.cli doctor` OK.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..1`
- JSONL ordinals `[3, 5, 9, 10, 15, 16, 17, 18, 19, 20, 29, 30, 31, 32, 33, 34, 35, 44, 45, 46, 47, 48, 56, 57, 60, 61, 62, 63, 71, 72, 73, 74, 75, 76, 77, 87, 88, 89, 90, 91, 92, 93, 102, 103, 104, 105, 106, 115, 116, 117, 118, 119, 120, 121, 131, 132, 133, 134, 135, 136, 137, 147, 148, 149, 150, 151, 152, 161, 162, 163, 164, 165, 166, 175, 176, 181, 182, 183, 184, 185, 186, 187, 196, 200]`
- messages `84`; SHA-256 `42d894e266951adb499ddeac5618af5b130ddb37dfb0753171356c9eaf24ecfd`

## 23. mse_ftqwacmpv594wvy3:d1 - No match

- Decision timestamp: `2026-08-03T17:11:00+00:00`
- Decision source: `.memory-seed/sessions/2026-08/2026-08-03.md:232`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Create `business/research/field-evidence-log.md` as an append-per-pass living document that records observation and source verbatim before any interpretation, and register it in the research README as distinct from the seven dated reports.
- R: The programme's standing caveat through all seven reports was that no user had been interviewed and every claim was inference. That is no longer true, and the correction needs a home that keeps growing rather than a dated pass that freezes. Separating verbatim quotes from interpretation matters more here than anywhere else in the corpus, because the temptation to read a self-built workaround as validation of a product is exactly the bias the reports spent seven passes guarding against.
- A: Folding the evidence into the wedge dossier was rejected because that document holds the current conclusion, not its provenance, and the research area's own convention is that dated evidence sits beside the dossier it informs. Recording only the favourable findings was rejected explicitly: the log carries the zero-upvote engagement figure and the dissenting comment arguing the problem is workflow discipline rather than missing memory.
- F: `business/research/field-evidence-log.md`, `business/research/README.md`.
- T: All 19 relative links across the research folder resolve.
```

## 24. mse_g3c3tamy9d449w79:d1 - No match

- Decision timestamp: `2026-07-23T07:25:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-23.md:193`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: A viewport claims the wheel only once ACTIVE (a click). Inactive, the wheel scrolls the modal
  body between diagrams. An accent ring plus a "Click to zoom" hint signal the state; Escape releases
  an active diagram before it closes the modal.
- R: Every viewport ate the wheel and zoomed, so you could not scroll from one diagram to the next -
  you were stuck zooming whichever one the pointer was over. Gating on an explicit active state gives
  the wheel back to the list until you ask for zoom.
- A: One active diagram at a time, held in the parent, so activating one releases the rest. A press
  activates and arms a drag in the same gesture; panning waits until active.
```

## 25. mse_g3r6ba77w23c1y3w:d1 - No match

- Decision timestamp: `2026-08-26T22:50:00+00:00`
- Decision source: `.memory-seed/sessions/2026-08/2026-08-26.md:313`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Updated `next_action`/`priority` frontmatter on three docs to reflect decisions already made:
  `adr-attached-decisions-earn-a-diagram-proposal.md` (ACCEPTED 2026-08-07, now blocked on open
  questions 1/2/4 rather than a JNL yes/no), `hierarchical-topic-vocabulary-proposal.md` (ACCEPTED
  2026-07-26/27, steps 1/2/4/6-starter shipped, only the per-project-type starter sub-decision
  still open), `vocabulary-proposal-mode-proposal.md` (SHIPPED 2026-07-27,
  `scripts/propose_topic_children.py` built and run, no follow-up).
- R: Each doc's own body already recorded the ruling/shipment inline (an ACCEPTED blockquote, a
  "settled ... (JNL)" section, or a same-week build), but the YAML frontmatter `next_action` still
  read "JNL to accept or reject" - which is what `docs/2_Todo/README.md`'s generated index
  surfaces, so anyone scanning the index for open JNL decisions would misread three closed items
  as open. Left three genuinely open ones (`topic-discovery-from-evidence.md`,
  `adjudication-queue.md`'s formal sign-off, `memory-index-dry-run-plan.md`'s Verging Labs
  submission call) untouched - no ruling was found for any of them.
- A: Rejected moving the two fully-accepted docs (ADR-diagrams, proposal-mode) out of `2_Todo/`
  into `5_Completed/` - the ADR-diagram proposal is accepted but still has unimplemented follow-on
  work gated on the ADR backlog, and the hierarchical-vocabulary proposal still carries one open
  sub-decision, so neither is fully done; only vocabulary-proposal-mode is unambiguously finished
  but moving one of three related docs alone seemed likely to fragment the set - left as a
  separate call for JNL rather than assumed here.
- F: `docs/2_Todo/adr-attached-decisions-earn-a-diagram-proposal.md`,
  `docs/2_Todo/hierarchical-topic-vocabulary-proposal.md`,
  `docs/2_Todo/vocabulary-proposal-mode-proposal.md`, `docs/2_Todo/README.md` (regenerated).
- T: `memory-seed docs check` - 223 files, 16 pre-existing warnings unchanged, no new ones;
  `memory-seed docs index` regenerated (`2_Todo/README.md`); `memory-seed docs index --check`
  clean.
```

## 26. mse_g705vcrc90z5x41d:d1 - No match

- Decision timestamp: `2026-07-19T19:18:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-19.md:796`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Closed the preview-write minute race JNL spotted: the tool contract, core docstring and twinned
  skills now prescribe echoing a `dry_run`'s returned `timestamp` into the real call, and three tests
  pin the mechanics - the echo survives a minute tick with the previewed id intact and no drift
  warning; omitting it across a tick mints a different id than inspected; a stale echo after another
  entry lands is refused loudly by the chronology guard rather than slotted out of order.
- R: The heading timestamp is minute-resolution and a hash input to the entry_id, so a preview at
  :59 and a write at :01 silently diverge - valid write, wrong bytes relative to what was inspected,
  which defeats the preview's whole fidelity promise. The echo is not authored time: it is the
  server's own stamp, one call older, so the clock discipline holds; and its failure mode is the
  loud chronology refusal, strictly better than the silent divergence it replaces. The dogfooded
  demo had dodged this with the private `_now` test seam agents cannot reach - the sanctioned
  pattern belonged in the contract's own words.
- F: `memory_seed/mcp_server.py`, `memory_seed/core.py`, the twinned
  `history_retrieval.md`/`session_logging.md` pairs.
- T: `tests/test_mcp_session_append.py` - echo survives the tick, no-echo divergence pinned, stale
  echo refused; 52 append/schema tests pass. This entry committed via the echo workflow itself.
```

## 27. mse_gsqy74hz2652y0vj:d1 - No match

- Decision timestamp: `2026-07-16T19:50:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-16.md:844`
- Candidate session: `019f64ba-a828-7a83-909d-bef0998afdab`
- Conversation timestamp: `2026-07-15T07:43:07.213000+00:00`
- Source: `.codex/sessions/2026/07/15/rollout-2026-07-15T08-43-07-019f64ba-a828-7a83-909d-bef0998afdab.jsonl`
- Evidence: score 0.187; TF-IDF 0.022; phrase 2 tokens; time 20.1h; actor compatible
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: no sufficiently similar conversation window in the temporal candidate set
- Second best: `019f64ba-a828-7a83-909d-bef0998afdab` (score 0.187; TF-IDF 0.022; phrase 2 tokens; time 20.1h; actor compatible)

Decision record:

```text
- D: Fit diagrams from their untransformed stage bounds, and centre a linear chain only when it leads into a fork; retain predecessor-based merge placement.
- R: Resetting to 1x left a 1113 by 2064px stage cropped inside a 1113 by 582px viewport. Fork-centred chains shorten the routes into a branch, while globally centring all ranks moved merge nodes away from their incoming-branch midpoint.
- A: A global cross-axis recentering pass was tried and rejected because it broke the established left-to-right merge placement test.
- F: Updated `memory-trace/memory_trace/static/app.js` and `memory-trace/tests/test_service.py`.
- T: The focused static/service suite passed (56 tests). The live tall diagram is fully contained at 27% scale, its single-node ranks align with the branch midpoint, Fit restores that state after zooming, and browser logs contain no warnings or errors.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..1`
- JSONL ordinals `[3, 6, 11, 12, 19, 20, 24, 34, 35, 40, 41, 46, 51, 57, 58, 62, 66, 73, 74, 78, 83, 102, 103, 108, 112, 116, 120, 124, 126, 131, 136, 141, 146, 151, 156, 162, 163, 172, 176, 180, 184, 189, 190, 194, 204, 205, 210, 211, 215, 218, 223, 232, 237, 238, 242, 249]`
- messages `56`; SHA-256 `8606d6e1fed67e193d3b319895ca8884e6dddc6d27601584495584e7a1c6e5ef`

## 28. mse_h0m8czgad9a9htpk:d1 - Low

- Decision timestamp: `2026-09-06T23:42:00+00:00`
- Decision source: `.memory-seed/sessions/2026-09/2026-09-07.md:58`
- Candidate session: `01a05ef9-96eb-7232-a0d7-71cf48d55c3a`
- Conversation timestamp: `2026-09-05T12:50:25.762000+00:00`
- Source: `.codex/sessions/2026/09/05/rollout-2026-09-05T13-50-25-01a0719e-c4cc-7a72-b7ba-d291ce83f937.jsonl`
- Evidence: score 0.307; TF-IDF 0.063; phrase 3 tokens; time 0.2h; identifiers cli/mcp/esr/board, docs/2_todo/reflection-ledger-workstream-evolution-plan.md; actor compatible
- Unique: `False`
- Ambiguity: competitive second session
- Diagnostic failure mode: multiple conversations discuss similar material
- Second best: `01a05ef9-96eb-7232-a0d7-71cf48d55c3a` (score 0.307; TF-IDF 0.063; phrase 3 tokens; time 0.2h; identifiers cli/mcp/esr/board, docs/2_todo/reflection-ledger-workstream-evolution-plan.md; actor compatible)

Decision record:

```text
- D: Keep the standalone parser strict, but require every trusted Git-backed product load to prove a unique append/rebind-only lineage before it returns `normal`; every non-monotonic transition requires one exact ordinary-session cleanup receipt and Git proof pair, even when the final bytes are strict-valid.
- R: Removing tail blocks or all record blocks can preserve predecessor checks in the surviving image. Only complete trusted path history distinguishes a fresh normal ledger from an unauthorised deletion without rewriting surviving bytes.
- A: Rejected an early return on standalone-parser success and a durable compaction index. A bounded derived cache may accelerate a Git/session rescan, but cannot supply proof authority.
- F: `docs/2_Todo/reflection-ledger-workstream-evolution-plan.md`, `docs/2_Todo/README.md`, `docs/README.md`.
- T: Specified real-Git tail, sole/header-only, suffix, repeated-compaction, and CLI/MCP/ESR/board parity fixtures; implementation remains blocked on independent review.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..3`
- JSONL ordinals `[5, 9, 13, 14, 21, 28, 36, 37, 44, 51, 58, 64, 71, 78, 85, 92, 103, 124, 134, 146, 147, 157, 176, 183, 190, 197, 204, 211, 218, 225, 232, 243, 250, 264, 271, 275, 276, 291, 298, 307, 322, 323, 330, 337, 348, 355, 362, 369, 376, 387, 394, 401, 413, 420, 424, 425, 432, 447, 454, 462, 463, 470, 477, 485]`
- messages `64`; SHA-256 `8fb7d90c53ee5409c6854fd06924d2466717595a873f7e4ed68ce8752171dc5e`

## 29. mse_h8tn4qkw2v6x9rdj:d1 - No match

- Decision timestamp: `2026-07-11T14:02:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-11.md:637`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Search stops being a destination view and becomes a function over whichever view is open.
  The Search tab, searchView, and result-list renderers are removed; stored "search" view prefs
  migrate to Trail. The topbar box is now always present; typing runs the server-side ranked
  /api/search (sections and files included, limit 50) and produces (a) a ranked dropdown of the
  top 10 - the next-generation roadmap's "ranked results drawer" shape - and (b) an entry match
  set highlighted IN PLACE: Trail match rows get an accent marker dot while misses dim to 0.45
  (structure never disappears), Graph match nodes keep full presence and earn a label while
  misses dim with the hover grammar. A shared viewbar fragment shows the match count with
  next/previous cycling (Enter / Shift+Enter in the box) and a clear chip. Dropdown clicks and
  cycling jump-select the entry, reopen the reader, scroll the Trail row into view, and grow the
  Trail window in TRAIL_WINDOW_STEP pages when the target is older than the visible window.
  Typing never selects or navigates (the auto-select-first-result behaviour is gone with the
  old focus-steal bug class). Saved-view presets rework to (query, view) pairs; the sort control
  and cursor paging die with the results list.
- R: User direction 2026-07-11: "the search should be a function that happens over the trail
  and the graph." Deliberately shaped like roadmap Phase 3's ranked results drawer and Phase
  4's match markers so the React port copies a settled design.
- A: Fixed during verification: clearing via the x chip while focus sat in the box resurrected
  the stale text, because render()'s focus preservation restores the captured live input value;
  the clear handler now empties the live input before re-rendering.
- F: `memory-trace/memory_trace/static/app.js`, `memory-trace/memory_trace/static/styles.css`,
  `memory-trace/memory_trace/static/index.html`, `memory-trace/tests/test_lense.py`.
- T: 39 tests pass (new search-as-a-function contract test; retirement test extended to the
  Search tab). Live: typing "lane" keeps focus and caret in the box, dropdown shows 10 ranked
  results, 11 match rows dotted + 49 dimmed in the window, 49+ counter; Enter cycles matches;
  graph view dims 237 non-matching nodes and labels 49 matches; deep dropdown jump grew the
  window 60 -> 240 rows and landed selected + visible; Esc closes the dropdown; clear resets
  everything; no console errors.
```

## 30. mse_hexq9x671dww29te:d1 - Low

- Decision timestamp: `2026-07-15T17:53:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-15.md:699`
- Candidate session: `019f64ba-a828-7a83-909d-bef0998afdab`
- Conversation timestamp: `2026-07-15T07:43:07.213000+00:00`
- Source: `.codex/sessions/2026/07/15/rollout-2026-07-15T08-43-07-019f64ba-a828-7a83-909d-bef0998afdab.jsonl`
- Evidence: score 0.282; TF-IDF 0.033; phrase 2 tokens; time 5.9h; identifiers changelog.md, docs/3_spec/functionality-audit.md, memory_seed.cli, readme.md; actor compatible
- Unique: `False`
- Ambiguity: competitive second session
- Diagnostic failure mode: multiple conversations discuss similar material
- Second best: `019f64ba-a828-7a83-909d-bef0998afdab` (score 0.282; TF-IDF 0.033; phrase 2 tokens; time 5.9h; identifiers changelog.md, docs/3_spec/functionality-audit.md, memory_seed.cli, readme.md; actor compatible)

Decision record:

```text
- D: Ship `memory-seed ranking-ab --signal <name> [--query <q> ...] [--json]` as the reusable branch-time gate for default ranking changes. The supersession signal derives every live lineage query, compares off/on at full corpus size, requires each replacement to out-rank the decision it retires, and requires a real no-affected-hit control to remain identical.
- R: Fixtures prove that a mechanism fires, but only the live corpus demonstrates that the intended decision wins without changing unrelated retrieval. Empty query sets, missing directional entries, and missing required controls must fail closed so incomplete evidence cannot produce a green gate.
- A: The inherited branch had registered the parser but not the command dispatch, so the advertised command returned `Unknown command: ranking-ab`; dispatch and exit semantics were completed before integration. An initial fixture expected damping to move a retired entry's rank, but equal-score ordering can leave the rank unchanged even when the score is correctly reduced; the test now asserts score reduction plus the actual contract outcome, replacement above predecessor. Brute-force control-query search was avoided in favour of title-token prefiltering followed by one real ranking verification per candidate.
- F: `memory_seed/ranking_ab.py`, `memory_seed/cli.py`, `tests/test_ranking_ab.py`, `README.md`, `docs/3_Spec/functionality-audit.md`, `CHANGELOG.md`.
- T: `python -m unittest tests.test_ranking_ab` passed 6 tests; `python -m memory_seed.cli ranking-ab --signal supersession_damping --json` passed three live lineages plus the `shipping surfaces profile` no-hit control across 428 entries; `python -m unittest discover -s tests` passed 463 tests with 1 expected skip.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..1`
- JSONL ordinals `[3, 6, 11, 12, 19, 20, 24, 34, 35, 40, 41, 46, 51, 57, 58, 62, 66, 73, 74, 78, 83, 102, 103, 108, 112, 116, 120, 124, 126, 131, 136, 141, 146, 151, 156, 162, 163, 172, 176, 180, 184, 189, 190, 194, 204, 205, 210, 211, 215, 218, 223, 232, 237, 238, 242, 249]`
- messages `56`; SHA-256 `8606d6e1fed67e193d3b319895ca8884e6dddc6d27601584495584e7a1c6e5ef`

## 31. mse_jbv3ctfaxq3pjbwp:d1 - Low

- Decision timestamp: `2026-07-16T09:00:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-16.md:300`
- Candidate session: `019f64ba-a828-7a83-909d-bef0998afdab`
- Conversation timestamp: `2026-07-15T07:43:07.213000+00:00`
- Source: `.codex/sessions/2026/07/15/rollout-2026-07-15T08-43-07-019f64ba-a828-7a83-909d-bef0998afdab.jsonl`
- Evidence: score 0.252; TF-IDF 0.023; phrase 2 tokens; time 9.3h; identifiers b0a/b0b; actor compatible
- Unique: `False`
- Ambiguity: competitive second session
- Diagnostic failure mode: multiple conversations discuss similar material
- Second best: `019f64ba-a828-7a83-909d-bef0998afdab` (score 0.252; TF-IDF 0.023; phrase 2 tokens; time 9.3h; identifiers b0a/b0b; actor compatible)

Decision record:

```text
- D: Use React and TypeScript as the B0b frontend implementation target, with reusable graph and client components for desktop packaging and VS Code webviews; keep each host's shell, filesystem, lifecycle, commands, and layout integration platform-specific.
- R: The React shell is the roadmap's chosen way to avoid duplicating the selected renderer, dockable Inspector, and explicit workspace state. The renderer-neutral projection and versioned API permit reuse without making React, a desktop shell, or a VS Code webview authoritative over Memory Seed semantics.
- A: Do not port the full three-region desktop workspace unchanged into VS Code. Keep the current vanilla SVG client as the fallback until the selected renderer passes B0b parity, accessibility, and offline packaging acceptance.
- F: Architectural decision only; no product source changed.
- T: Re-read the B0a/B0b roadmap and renderer-contract evidence; checked VS Code's official webview and web-extension constraints.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..1`
- JSONL ordinals `[3, 6, 11, 12, 19, 20, 24, 34, 35, 40, 41, 46, 51, 57, 58, 62, 66, 73, 74, 78, 83, 102, 103, 108, 112, 116, 120, 124, 126, 131, 136, 141, 146, 151, 156, 162, 163, 172, 176, 180, 184, 189, 190, 194, 204, 205, 210, 211, 215, 218, 223, 232, 237, 238, 242, 249]`
- messages `56`; SHA-256 `8606d6e1fed67e193d3b319895ca8884e6dddc6d27601584495584e7a1c6e5ef`

## 32. mse_jpfs9yy19bznh18y:d3 - No match

- Decision timestamp: `2026-07-10T04:10:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-10.md:397`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Relabel the `session` group help (it said "inspect session targets" but owns the write-capable
  `fuse` subcommand) and cross-reference the two easily-confused `migrate` subcommands.
- R: CLI-audit findings on their own terms, independent of the MCP work: a verb/scope mismatch and
  a naming-collision discoverability gap.
- F: `memory_seed/cli.py`.
```

## 33. mse_m6amd5db4c7s8sfw:d2 - Low

- Decision timestamp: `2026-07-10T02:28:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-10.md:118`
- Candidate session: `019f26b2-9813-7101-ac1c-baa49a3c8ad2`
- Conversation timestamp: `2026-07-09T17:56:20.981000+00:00`
- Source: `.codex/sessions/2026/07/09/rollout-2026-07-09T18-56-20-019f4805-edd9-7e30-98ea-864077a28874.jsonl`
- Evidence: score 0.277; TF-IDF 0.024; phrase 3 tokens; time 7.5h; identifiers memory-seed/agent-rules.md, schema/layout; branch match; actor compatible
- Unique: `False`
- Ambiguity: competitive second session
- Diagnostic failure mode: multiple conversations discuss similar material
- Second best: `019f26b2-9813-7101-ac1c-baa49a3c8ad2` (score 0.277; TF-IDF 0.024; phrase 3 tokens; time 7.5h; identifiers memory-seed/agent-rules.md, schema/layout; branch match; actor compatible)

Decision record:

```text
- D: Change decision-diagram guidance from optional consideration to positive-trigger behavior for
  branch/merge topology, migrations, schema/layout compatibility flows, multi-agent concurrency,
  command lifecycles, and retrieval/data pipelines.
- R: The old wording correctly discouraged decorative diagrams but was too easy for agents to
  interpret as "skip diagrams unless forced."
- F: `.memory-seed/skills/session_logging.md`, `.memory-seed/skills/end_of_turn.md`,
  `.memory-seed/agent-rules.md`, `memory_seed/seed/.memory-seed/skills/session_logging.md`,
  `memory_seed/seed/.memory-seed/skills/end_of_turn.md`,
  `memory_seed/seed/.memory-seed/agent-rules.md`,
  `.memory-seed/sessions/diagrams/2026-07/2026-07-10.md`.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..1`
- JSONL ordinals `[3, 5, 9, 10, 15, 16, 17, 18, 19, 20, 29, 30, 31, 32, 33, 34, 35, 44, 45, 46, 47, 48, 56, 57, 60, 61, 62, 63, 71, 72, 73, 74, 75, 76, 77, 87, 88, 89, 90, 91, 92, 93, 102, 103, 104, 105, 106, 115, 116, 117, 118, 119, 120, 121, 131, 132, 133, 134, 135, 136, 137, 147, 148, 149, 150, 151, 152, 161, 162, 163, 164, 165, 166, 175, 176, 181, 182, 183, 184, 185, 186, 187, 196, 200]`
- messages `84`; SHA-256 `42d894e266951adb499ddeac5618af5b130ddb37dfb0753171356c9eaf24ecfd`

## 34. mse_m6nrb8v2x05bv0hm:d1 - Medium

- Decision timestamp: `2026-06-28T01:03:00+00:00`
- Decision source: `.memory-seed/sessions/2026-06/2026-06-28.md:222`
- Candidate session: `019f0b5e-267a-7263-8c5c-0f6fb130fe4b`
- Conversation timestamp: `2026-06-27T23:15:47.499000+00:00`
- Source: `.codex/sessions/2026/06/28/rollout-2026-06-28T00-15-47-019f0b5e-267a-7263-8c5c-0f6fb130fe4b.jsonl`
- Evidence: score 0.455; TF-IDF 0.163; phrase 6 tokens; time 1.8h; identifiers 02:03, max-width/truncation, memory_seed/lense_static/app.js, memory_seed/lense_static/styles.css, memory_seed\lense_static\app.js; actor compatible
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: none recorded
- Second best: `019f0a8c-6dfa-72f3-902a-fe8af9bcf875` (score 0.259; TF-IDF 0.046; phrase 6 tokens; time 5.6h; actor compatible)

Decision record:

```text
- D: Use a fixed `bucketMin = 44` for every timeline zoom level and add CSS max-width/truncation plus top/bottom spacing for `.bucket-count` and `.bucket-label`.
- R: The timeline should feel spatially stable when switching granularity, and labels need deterministic space inside compact activity bars.
- F: `memory_seed/lense_static/app.js`, `memory_seed/lense_static/styles.css`, `tests/test_lense.py`.
- T: New frontend regression failed before implementation and passed after; `node --check memory_seed\lense_static\app.js` passed; `python -m unittest discover -s tests` passed 191 tests; live assets served the updated fixed-width and label-spacing rules.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `13..17`
- JSONL ordinals `[976, 980, 985, 989, 990, 991, 992, 993, 1001, 1002, 1007, 1008, 1013, 1014, 1019, 1020, 1024, 1025, 1029, 1030, 1035, 1036, 1037, 1038, 1045, 1046, 1047, 1051, 1055, 1056, 1057, 1063, 1066, 1067, 1072, 1073, 1077, 1079, 1083, 1084, 1085, 1086, 1092, 1093, 1098, 1099, 1104, 1105, 1109, 1110, 1111, 1112, 1119, 1120, 1121, 1127, 1128, 1129, 1135, 1136, 1141, 1142, 1146, 1147, 1151, 1152, 1157, 1158, 1159, 1164, 1165, 1169, 1170, 1176, 1181, 1185, 1186, 1187, 1188, 1194, 1195, 1199, 1200, 1205, 1206, 1210, 1211, 1216, 1217, 1222, 1223, 1224, 1225, 1226, 1233, 1234, 1235, 1236, 1242, 1243, 1247, 1248, 1253, 1258, 1262, 1263, 1264, 1265, 1271, 1272, 1277, 1278, 1279, 1285, 1286, 1291, 1292, 1296, 1297, 1302, 1303, 1307, 1308, 1312, 1313, 1319, 1320, 1321, 1326, 1327, 1333, 1334, 1339, 1340, 1343, 1347, 1358, 1361, 1362, 1367, 1371, 1372, 1377, 1378, 1383, 1384, 1390, 1391, 1395, 1396, 1399, 1405, 1406, 1407, 1413, 1414, 1415, 1420, 1421, 1425, 1426, 1431, 1432, 1433, 1438, 1439, 1443, 1444, 1450, 1455, 1459, 1460, 1461, 1462, 1469, 1470, 1475, 1476, 1481, 1482, 1486, 1487, 1492, 1493, 1497, 1500, 1501, 1506, 1507, 1512, 1513, 1517, 1518, 1519, 1520, 1526, 1527, 1531, 1532, 1536, 1537, 1538, 1543, 1544, 1548, 1549, 1554]`
- messages `207`; SHA-256 `10b3ae56a39014a4b53a406c06d9ba80f538929ed33e46199a6a490fd2dfe811`

## 35. mse_mj4vwfbjdhkej485:d1 - No match

- Decision timestamp: `2026-07-16T20:49:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-16.md:920`
- Candidate session: `019f64ba-a828-7a83-909d-bef0998afdab`
- Conversation timestamp: `2026-07-15T07:43:07.213000+00:00`
- Source: `.codex/sessions/2026/07/15/rollout-2026-07-15T08-43-07-019f64ba-a828-7a83-909d-bef0998afdab.jsonl`
- Evidence: score 0.202; TF-IDF 0.021; phrase 2 tokens; time 21.1h; actor compatible
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: no sufficiently similar conversation window in the temporal candidate set
- Second best: `019f64ba-a828-7a83-909d-bef0998afdab` (score 0.202; TF-IDF 0.021; phrase 2 tokens; time 21.1h; actor compatible)

Decision record:

```text
- D: Treat exact entry navigation, selected-only `evolves` routes, connected-context graph density, fit/zoom controls, curved typed edges, and resilient search/selection as shared Memory Trace behaviour, implemented in the React workspace as well as vanilla.
- R: The React shell is the forward renderer path, so it must inherit validated interaction and readability rules rather than reintroduce previously resolved usability defects.
- A: React Mermaid diagram rendering remains intentionally deferred because the v1 chunk contract exposes diagram metadata rather than a renderer-neutral diagram payload; copying the vanilla parser now would create incompatible duplicate rendering logic.
- F: `memory-trace/client/src/App.tsx`, `memory-trace/client/src/GraphWorkspace.tsx`, `memory-trace/client/src/api.ts`, `memory-trace/client/src/styles.css`, and packaged `memory-trace/memory_trace/static/react/` assets are now integrated on `main`.
- T: The combined `memory-trace/tests` suite passed 140 tests; the React worktree had already passed `npm run typecheck`, `npm run build`, and live packaged-route checks before integration.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..1`
- JSONL ordinals `[3, 6, 11, 12, 19, 20, 24, 34, 35, 40, 41, 46, 51, 57, 58, 62, 66, 73, 74, 78, 83, 102, 103, 108, 112, 116, 120, 124, 126, 131, 136, 141, 146, 151, 156, 162, 163, 172, 176, 180, 184, 189, 190, 194, 204, 205, 210, 211, 215, 218, 223, 232, 237, 238, 242, 249]`
- messages `56`; SHA-256 `8606d6e1fed67e193d3b319895ca8884e6dddc6d27601584495584e7a1c6e5ef`

## 36. mse_n3bw6rkq0e8t2ypc:d1 - No match

- Decision timestamp: `2026-07-11T07:32:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-11.md:55`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Every Trail lane change now uses the gitgraph "rounded" style the user sampled from this
  project in VS Code's Git Graph: straight vertical/horizontal runs with a small quarter-arc
  elbow (new `TRAIL_CORNER = 7`) right at the junction row. Fork/merge connectors dropped their
  long sweeping beziers - the bend sits at the fork/merge row and the rest travels vertically in
  the branch's own lane; relationship routes regained rounded corners at their two lane turns.
  The radius constant documents its bounds (below half the row gap and below one lane width).
- R: User supplied a Git Graph screenshot of this repo: "all the lines should be radius similar
  to this sample... this is visually cleaner." Rounded-elbow is also the default style in VS
  Code Git Graph and gitgraph.js's metro template per the earlier research brief.
- F: `memory-trace/memory_trace/static/app.js`, `memory-trace/memory_trace/static/index.html`.
- T: 38 tests pass. Live: 33 connectors all rounded-elbow paths, zero legacy beziers; screenshot
  matches the sample's junction geometry in dark theme.
```

## 37. mse_ngwdpar27fjad246:d1 - No match

- Decision timestamp: `2026-07-12T10:44:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-12.md:125`
- Candidate session: `019f26b2-9813-7101-ac1c-baa49a3c8ad2`
- Conversation timestamp: `2026-07-09T17:56:20.981000+00:00`
- Source: `.codex/sessions/2026/07/09/rollout-2026-07-09T18-56-20-019f4805-edd9-7e30-98ea-864077a28874.jsonl`
- Evidence: score 0.196; TF-IDF 0.030; phrase 2 tokens; time 63.8h; actor compatible
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: no sufficiently similar conversation window in the temporal candidate set
- Second best: `019f26b2-9813-7101-ac1c-baa49a3c8ad2` (score 0.196; TF-IDF 0.030; phrase 2 tokens; time 63.8h; actor compatible)

Decision record:

```text
- D: Created an active P1 proposal for an agent worktree namespace guard so Codex, Claude, Gemini,
  Cursor, and configured third-party agents can verify that write work is happening inside the
  correct agent-owned worktree namespace before editing files.
- R: Recent multi-agent work hardened branches, session fuse, and MCP readouts, but still left a
  practical gap: a writing agent could start in another agent's worktree or in the root checkout.
  A pre-write guard closes that coordination gap without moving existing worktrees automatically.
- A: No diagram sidecar was added; the turn created a proposal rather than an implemented command
  lifecycle, and the proposal itself records the namespace classifications and implementation order.
- F: `docs/2_Todo/agent-worktree-namespace-guard-plan.md`,
  `docs/2_Todo/0_NEXT_STEPS.md`.
- T: `git diff --check` passed. `python -m memory_seed.cli links check` passed. Initial `python -m
  memory_seed.cli topics check` found missing 2026-07-11 topic vocabulary; fixed in follow-up entry
  `mse_vy8tq90rr4br8a0z`.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..1`
- JSONL ordinals `[3, 5, 9, 10, 15, 16, 17, 18, 19, 20, 29, 30, 31, 32, 33, 34, 35, 44, 45, 46, 47, 48, 56, 57, 60, 61, 62, 63, 71, 72, 73, 74, 75, 76, 77, 87, 88, 89, 90, 91, 92, 93, 102, 103, 104, 105, 106, 115, 116, 117, 118, 119, 120, 121, 131, 132, 133, 134, 135, 136, 137, 147, 148, 149, 150, 151, 152, 161, 162, 163, 164, 165, 166, 175, 176, 181, 182, 183, 184, 185, 186, 187, 196, 200]`
- messages `84`; SHA-256 `42d894e266951adb499ddeac5618af5b130ddb37dfb0753171356c9eaf24ecfd`

## 38. mse_pkd8hbh3qbbahydn:d1 - No match

- Decision timestamp: `2026-07-30T16:37:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-30.md:786`
- Candidate session: `019fadcc-85d6-7142-b038-c6916abbeeb2`
- Conversation timestamp: `2026-07-29T12:14:49.965000+00:00`
- Source: `.codex/sessions/2026/07/29/rollout-2026-07-29T13-14-49-019fadcc-85d6-7142-b038-c6916abbeeb2.jsonl`
- Evidence: score 0.212; TF-IDF 0.027; phrase 3 tokens; time 6.6h; identifiers memory_seed.cli; actor compatible
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: no sufficiently similar conversation window in the temporal candidate set
- Second best: `019fadcc-85d6-7142-b038-c6916abbeeb2` (score 0.212; TF-IDF 0.027; phrase 3 tokens; time 6.6h; identifiers memory_seed.cli; actor compatible)

Decision record:

```text
- D: Classify the adopted ADR as `spec_binding: live` and point proposal references at its canonical `3_Spec/` location.
- R: The Constitution and docs lifecycle define `3_Spec/` as the normative lane; the ADR remains the governing record for the measured rejection of structural community detection.
- A: Moving the ADR to a terminal rejection lane was rejected because it records a binding architectural decision, not a rejected proposal.
- F: `docs/3_Spec/adr-graph-community-detection.md`; `docs/2_Todo/memory-trace-graph-visualisation-and-temporal-topology-proposal.md`.
- T: `python -m memory_seed.cli docs check`; `python -m memory_seed.cli links check`; `python -m memory_seed.cli docs index --check`; `git diff --check`.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..1`
- JSONL ordinals `[5, 9, 13, 14, 18, 24, 25, 30, 34, 39, 40, 44, 48, 53, 58, 62, 67, 76, 83, 84, 89, 93, 97, 106, 110, 115, 119, 124, 133, 142, 147, 156, 162]`
- messages `33`; SHA-256 `5520adf99d56793e30dbd64ba2be42a5ad7a654bc4feec0bcac7105eda7d9cfa`

## 39. mse_ptfk5epzwmqy5stk:d1 - No match

- Decision timestamp: `2026-07-11T20:55:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-11.md:993`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Added `memory_trace/models.py` (Pydantic response models) and six `/api/v1/*` routes
  (`runtime`, `facets`, `search`, `chunks/{id}`, `graph`, `trail`) alongside the existing
  unversioned `/api/*` routes, per roadmap Phase 1 ("versioned API contract"). Every v1 model
  matches an existing `LenseService` dict shape field-for-field (`_chunk_to_api`,
  `_ranked_to_api`/`_rollup_to_api`, `_graph_node`, `_chunk_summary`) - the service itself keeps
  returning plain dicts; `response_model` validates/coerces them. Two fields go beyond what's
  emitted today: `provenance_class` (the full 7-value enum from
  `memory-trace-trail-search-and-graph-ux.md` SS3.2, defaulting to and always emitting
  `authored_memory` - forward-stable typing, no speculative data) and a typed `EdgeType` enum
  covering every kind `_graph_edges()` already produces.
- R: The React client that will eventually consume this doesn't exist yet (Phase 2), so the
  contract models only what the vanilla frontend consumes today plus the two fields the UX/graph
  specs explicitly name as forward deliverables - not the full Phase 6-10 event-class vision
  (no PR/CI/annotation payload fields). `/api/timeline` gets no v1 counterpart: Trail
  (roadmap Phase 4) is its designated successor and nothing consumes it; the legacy endpoint is
  untouched in case that ever changes. `/api/v1/trail` is its own endpoint (fixed to
  `branch,supersedes,evolves,related`, matching `app.js`'s `TRAIL_EDGE_TYPES`) rather than a
  graph parameterization, reflecting the product's Trail-primary hierarchy rather than treating
  Trail as an accessory of the generic graph.
- F: `memory-trace/memory_trace/models.py`, `memory-trace/memory_trace/lense.py`,
  `memory-trace/tests/test_v1_api_contract.py`.
- T: 9 new contract tests (v1/legacy parity, 404 parity, provenance-class default,
  OpenAPI schema exposes named v1 paths/models). Full suites green (core 362, memory-trace 56).
  Live-verified against the real 328-entry corpus: vanilla UI unchanged in the browser,
  `/api/v1/trail` and `/api/v1/graph` return correctly, `/openapi.json` lists all 6 v1 paths and
  every new component schema (`ProvenanceClass`, `EdgeType`, `GraphNode`, `TrailEvent`, ...).
```

## 40. mse_r32k8mk46ky8rdtv:d3 - No match

- Decision timestamp: `2026-08-04T10:33:00+00:00`
- Decision source: `.memory-seed/sessions/2026-08/2026-08-04.md:482`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Close the guard confound registered before the first scored run: `guard_called` was true in
  0 of 60 sessions with a reliable event stream.
- R: It was registered because only L2/L3 carry the contract telling an agent to consult the guard,
  so a block could have masqueraded as scaffolding suppressing capture. With real tool-call events
  it is now visible that agents do not call the guard during ordinary task work at any level, so the
  mechanism cannot be operating. It was carried as open only because the v1 transcript could not
  see tool calls at all.
- A: Leaving it open was declined now that it is genuinely measured rather than merely unobserved.
- F: `business/research/field-evidence-log.md` (E6), `experiments/agent-capture/collect.py`.
- T: `guard_signal_reliable` true for all 60 v2 runs; `guard_called` false in all 60.
```

## 41. mse_s0kh1h39kzdgyk38:d1 - No match

- Decision timestamp: `2026-07-25T21:05:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-25.md:561`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Topic sidecars gain `<slug>:dN` alongside bare slugs, with the ordinal validated against the
  entry's real decisions (`dangling-topic-decision`), a malformed-suffix error
  (`malformed-topic-ref`), a per-decision cap of 3 (`MAX_TOPICS_PER_DECISION`) with the rolled-up
  entry union left uncapped, and the redundancy rule inverted so a decision-keyed slug naming a
  topic the author wrote at entry level reads as enrichment rather than restatement. Bare slugs stay
  legal permanently.
- R: JNL directed building decision-level from the start and scanning the full corpus. Measurement
  settles the sequencing: the backfill is **881 decisions across all 621 entries** either way,
  because the 415 already-topiced entries carry no per-decision attribution, so an entry-level pass
  first would add 206 judgments the decision pass then re-derives. Bare slugs cannot be a migration
  stage because **33 entries record no decision at all** — a note is still about something. Roll-up
  to entry level is required and deliberately inverts the link precedent: `check_topics` and every
  other consumer read entry-level topics, so without it a fully decision-tagged entry still reports
  as topicless. Rolling `graph:d1` up to "partly about graph" invents no claim, whereas rolling
  `A:d1 -> B:d2` up to `A -> B` would.
- A: Entry-level backfill now, decision-level later — rejected: same 881 judgments, plus a second
  written pass. A third mandatory topic axis — previously assessed and rejected; unchanged.
- F: `memory_seed/core.py`, `tests/test_links_check.py` (six tests),
  `docs/3_Spec/draft/decision-level-topic-sidecars.md`, `docs/2_Todo/decision-level-topics-proposal.md`.
- T: 726 backend tests pass; live corpus reports `Session memory integrity OK` (90 files).
```

## 42. mse_sdh0v1jsgxaamax5:d1 - No match

- Decision timestamp: `2026-07-20T15:39:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-20.md:690`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Retired `test_memory_seed.py` (6,533 lines, 287 tests across 8 unrelated `unittest.TestCase`
  classes) - the concentration the audit's own measurements flagged (45% of tests, 78% of wall time in
  one file). Split it into 12 files by an AST-driven script rather than by hand: the 7 already-cohesive
  classes moved verbatim (`test_hook_merge.py`, `test_session_log_ordering_hook.py`, `test_mcp_merge.py`,
  `test_retrieval_check_path.py`, `test_cli_help.py`, `test_session_start_hook.py`,
  `test_agent_selection.py`); the 179-test `MemorySeedTests` grab-bag was further split by a call-graph
  classification of each test (which core API / helper it actually calls, not name-prefix guessing) into
  `test_session_fuse_and_merge.py` (69), `test_links_check.py` (44), `test_project_lifecycle.py` (39),
  `test_session_layout_migration.py` (9), and `test_core_misc.py` (18). Recorded the split, its
  verification, and the next two phases (harness dedup, then the actual content cull) in
  `docs/2_Todo/test-suite-protection-value-audit.md`.
- R: JNL said "Do it" to continuing the audit past the measurement phase, and the tracking doc's own
  Phase 2 already named this as step one - splitting is what makes any later duplication visible within
  a cohesive group instead of buried across 6,400 mixed lines, and it's what the file-count/runtime
  concentration measurement was diagnosing in the first place. Did it as a script, not by hand, because
  179 tests is too much to relocate correctly by eye without a real risk of silently dropping one, and
  because `@pytest.mark.integration` decorators live on a separate AST node (`decorator_list`) from a
  function's own `lineno` - a naive line-range extraction would have silently stripped the marker from
  all 57 integration-tagged tests in this class, quietly undoing the previous session's tiering work.
  Caught that failure mode by testing the script's plan output before generating files, not by
  discovering it after.
- A: Classified tests by what they actually *call* (core API functions, helper methods), not by string
  matching on their names - name prefixes like "the_no_merge_attribute..." or
  "without_the_attribute..." don't share a token with "session_fuse"/"session_merge" but are the exact
  same concern (the `-merge` git attribute), and a prefix-only classifier would have scattered them.
  Accepted duplicated copies of three small pure-Python fixture helpers
  (`_per_user_session`/`_write_participants`/`_git_repo_with_commit`) across 2-3 files rather than
  building a shared module in this same pass - each is used by tests now living in different concern
  files, and building the shared module correctly means verifying every caller's exact expectations,
  which is exactly the kind of work the deferred harness-dedup phase exists for. Did not attempt that
  dedup, or the actual Keep/Consolidate/Replace/Move/Delete content cull, in this pass - both are noted
  as the next two phases, not silently skipped.
- F: Deleted `tests/test_memory_seed.py`. Added `tests/test_hook_merge.py`,
  `tests/test_session_log_ordering_hook.py`, `tests/test_mcp_merge.py`,
  `tests/test_retrieval_check_path.py`, `tests/test_cli_help.py`, `tests/test_session_start_hook.py`,
  `tests/test_agent_selection.py`, `tests/test_session_fuse_and_merge.py`, `tests/test_links_check.py`,
  `tests/test_project_lifecycle.py`, `tests/test_session_layout_migration.py`, `tests/test_core_misc.py`.
  Updated `docs/2_Todo/test-suite-protection-value-audit.md`.
- T: Verified programmatically before deleting the original: the set of 179 `MemorySeedTests` test
  names reconstructed from the 5 new concern files matched the original set exactly, each name exactly
  once. `pytest --collect-only` reported exactly 635 tests both before and after (922 mid-way, with both
  old and new files present, confirming no premature loss). Full suite after the split: 635 passed, 14
  subtests passed - identical tally to before. Fast loop (`-m "not integration"`): 543 passed, 92
  deselected - identical tally, confirming all 57 integration markers that lived in `MemorySeedTests`
  landed intact (46 in `test_session_fuse_and_merge.py`, 7 in `test_cli_help.py`, 3 in
  `test_mcp_merge.py`, 1 in `test_links_check.py`). `docs check` and `links check` clean.
```

## 43. mse_v3q8dwm2knzp61tr:d1 - No match

- Decision timestamp: `2026-07-10T19:35:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-10.md:2452`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: First two units of the autonomous UI goal pass. (1) Scroll-reset bug class fixed:
  `captureCenterScroll` only preserved three center selectors, so left/right panes and the new
  Trail scroller reset on every re-render (the user-reported left-pane facet click bug). New
  `SCROLL_PRESERVE_SELECTORS` covers all six scrollable regions with a comment requiring new
  scroll containers to be registered; contract test pins the full list. (2) Trail now forks like
  a gitgraph: `trail-link` rounded curves connect each task branch's oldest visible row to the
  nearest older main row (fork) and its newest row to the nearest newer main row (merge); open
  branches deliberately dangle - no merge is fabricated. main is pinned to the leftmost lane
  (git-client convention) and no-branch legacy entries no longer allocate a lane.
- R: Goal directive: "when i'm selecting components on the left pane the scroll wheel is
  resetting... do a full check for this type of bug"; "straight lines and forking with nodes...
  much like a gitgraph". Fork/merge targets reflect the real workflow (task branches cut from and
  merged into main via session merge-branch), so no false edges are drawn.
- F: `memory-trace/memory_trace/static/app.js`, `memory-trace/memory_trace/static/index.html`,
  `memory-trace/tests/test_lense.py`.
- T: Live preview: left-pane scrollTop 249->249 across a facet click with filter applied; Trail
  shows 37 fork/merge connectors + 40 lane lines + 2 lifecycle arcs.
```

## 44. mse_wb6d4gmjpmrj0k67:d1 - No match

- Decision timestamp: `2026-07-26T00:22:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-26.md:263`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: `/api/v1/graph/projection` accepts `include_decisions` (default **false**), and `graph()` gains
  `decision_row_scope`. The entry-level surface is byte-identical when the flag is off.
- R: This is NEXT_STEPS item 8 — the fix for entries whose only relationships are decision-level and
  therefore render as orphans, because an entry-per-node view has no row for `B:d2 evolves A:d1` to
  land on. Emitting an entry-level line instead was tried on 2026-07-26 and reverted against
  `test_decision_edges_never_reach_entry_level_consumers`. Asking for rows is legitimate where
  forging an edge is not: the edge terminates on the decision it actually names, and the claim
  grammar v2 forbids ("B evolves A" as an authored entry-level edge) is still never made.
- A: Make it the default — rejected: it changes every existing consumer's granularity for a 9-entry
  tail. Keep forging entry-level edges behind a marker — rejected: the guard tests the edge SET, so a
  label does not make the surface indistinguishable.
- F: `memory-trace/memory_trace/service.py`, `memory-trace/tests/contract/openapi.v1.json`,
  `memory-trace/tests/contract/types.ts`.
```

## 45. mse_wk3e5p73shz4edbb:d1 - Medium

- Decision timestamp: `2026-06-28T00:03:00+00:00`
- Decision source: `.memory-seed/sessions/2026-06/2026-06-28.md:89`
- Candidate session: `019f0b5e-267a-7263-8c5c-0f6fb130fe4b`
- Conversation timestamp: `2026-06-27T23:15:47.499000+00:00`
- Source: `.codex/sessions/2026/06/28/rollout-2026-06-28T00-15-47-019f0b5e-267a-7263-8c5c-0f6fb130fe4b.jsonl`
- Evidence: score 0.477; TF-IDF 0.244; phrase 6 tokens; time 0.8h; identifiers 01:03, api/timeline, assets/styles.css, memory_seed/lense_static/styles.css, memory_seed\lense_static\app.js; actor compatible
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: none recorded
- Second best: `019f0a8c-6dfa-72f3-902a-fe8af9bcf875` (score 0.252; TF-IDF 0.043; phrase 6 tokens; time 4.6h; identifiers api/timeline; actor compatible)

Decision record:

```text
- D: Bound `.center > section` with `height: 100%`, `min-height: 0`, a `44px minmax(0, 1fr)` grid, and `overflow: hidden`.
- R: The timeline viewbar and scroll container are grandchildren of `.center`; the previous grid rows were applied to `.center` itself, leaving `.scroll` without a constrained height and preventing scrolling.
- F: `memory_seed/lense_static/styles.css`, `tests/test_lense.py`.
- T: `python -m unittest discover -s tests` passed 187 tests; `node --check memory_seed\lense_static\app.js` passed; live `/api/timeline?zoom=day&limit=80` returned timeline data and `/assets/styles.css` included the new `.center > section` rule.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `6..10`
- JSONL ordinals `[434, 438, 439, 440, 441, 448, 449, 450, 455, 456, 457, 458, 465, 466, 467, 468, 474, 475, 478, 483, 488, 492, 493, 499, 500, 504, 509, 513, 514, 515, 516, 517, 525, 526, 531, 532, 536, 537, 542, 543, 544, 545, 546, 554, 555, 556, 557, 564, 565, 566, 567, 574, 575, 578, 583, 588, 592, 593, 594, 595, 602, 603, 607, 612, 613, 618, 619, 624, 625, 626, 627, 628, 635, 636, 637, 638, 644, 645, 646, 647, 653, 654, 659, 664, 668, 669, 670, 671, 672, 680, 681, 686, 687, 692, 693, 697, 702, 703, 708, 709, 710, 715, 716, 717, 718, 719, 731, 732, 733, 734, 741, 742, 746, 751, 752, 758, 759, 760, 766, 767, 772, 773, 774, 775, 776, 784, 785, 789]`
- messages `128`; SHA-256 `4dc7846b3a8be628609c8980f59c9f731c701729d2c91714ce59573c6c438cc2`

## 46. mse_xf4bbxff588ytvq4:d1 - Low

- Decision timestamp: `2026-08-18T14:47:00+00:00`
- Decision source: `.memory-seed/sessions/2026-08/2026-08-18.md:228`
- Candidate session: `01a0154b-aab2-7182-97a0-391c4c16c517`
- Conversation timestamp: `2026-08-18T14:34:35.672000+00:00`
- Source: `.codex/sessions/2026/08/18/rollout-2026-08-18T15-34-35-01a0154b-aab2-7182-97a0-391c4c16c517.jsonl`
- Evidence: score 0.234; TF-IDF 0.041; phrase 3 tokens; time 0.2h; actor compatible
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision wording may be rewritten, synthesized across turns, or weakly distinctive
- Second best: `01a01494-2d86-7e43-a07d-1bffb2589f46` (score 0.217; TF-IDF 0.024; phrase 2 tokens; time 3.5h; actor compatible)

Decision record:

```text
- D: Keep condition allocation sealed; advance a subject from receipt collection only after its captured protocol contains the required JSON boolean and, where prescribed, the exact local Memory Seed search and chunk fetch.
- R: The prior pre-flight stopped before candidate edits because the packet example induced a string boolean. The corrected packet must be observed in real use before implementation and no controller repair may turn a noncompliant receipt into a compliant one.
- A: Rejected scoring or revealing the invalidated earlier run, and rejected rerunning a subject whose receipt fails the protocol.
- F: `f/v5-relaunch-20260818-artifacts/` (gitignored raw pilot evidence); `experiments/decision-replay/codex-decision-edge-v5/` (frozen instrument).
- T: A prescribed-retrieval subject returned `required: true`, ran the required fixture-local search and exact chunk fetch, and was advanced in the same fresh session. Three further receipt-only subjects completed without opening the sealed condition map.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `1..2`
- JSONL ordinals `[5, 8, 12, 13, 17, 20, 25, 30, 32, 36, 40, 41, 46, 47, 51, 55, 59, 66, 70, 74, 81, 82, 88, 89, 95, 96, 101, 106, 107, 112, 117, 118, 123]`
- messages `33`; SHA-256 `f856d5e96327f054298c75cd061ffd92f7bea47670336da0a93366a07a4eac66`

## 47. mse_xje157km2m3rfzv0:d2 - No match

- Decision timestamp: `2026-07-17T02:10:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-17.md:426`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Record that `authority_class` already exists and already disagrees with the proposal, and block
  step 3 on an explicit user decision rather than picking a resolution.
- R:
  - BG1 reads as though `authority_class` is unbuilt. It is not: `RendererGraphNode.authority_class`
    exists as a bare `str`, validated only as "non-empty" (`graph_projection.py:218`), emitting
    `canonical_memory` (L120) - a value absent from the proposal's seven-value vocabulary. The authority
    axis is already carrying an undocumented parallel vocabulary, the exact failure BG1 exists to prevent.
  - Fixing it is not additive, which step 3 requires: `openapi.v1.json:1045` publishes the field as
    `"type": "string"`, so enum-constraining it or renaming the value breaks `/api/v1`.
  - An agent should not break a frozen versioned contract unilaterally; the API is versioned precisely so
    this correction has a home.
- A: Four options recorded in crosswalk section 5 - rename+enum in v1, admit `canonical_memory` as a
  synonym, defer the enum to v2, or keep the wire value and map at the boundary. Deliberately not chosen.
- F: `docs/3_Spec/draft/provenance-authority-crosswalk.md`,
  `docs/2_Todo/memory-provenance-and-authority-taxonomy-proposal.md`.
```

## 48. mse_xz2pr6w8g5xkrecx:d1 - No match

- Decision timestamp: `2026-07-27T16:15:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-27.md:1574`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: `lifecycle-edges`, `topic-vocabulary`, `test-suite` and `docs-lifecycle` are area ROOTS, not
  children of the old `memory-seed` slug, which is renamed **`seed-core`** with `memory-seed` kept as an
  alias. Also landed: `trail`, `trace-cache`, `trace-harness`, `panes` under `memory-trace`; `topbar`,
  `navigation`, `inspector`, `diagram-view` under `panes`; `package`, `feature-build`, `testing` as
  roots; `continuity`/`related-entries`/`schema`/`supersession` reparented from `graph` to
  `lifecycle-edges`. `settings` and `workspace-bar` DECLINED - zero agreed entries each.
- R: JNL's ruling, on a conflict I surfaced rather than resolved. `topics.yaml` declares the old slug a
  RESIDUAL area - *"a residual area takes no children by definition: anything specific enough to name is
  by construction not residual"* - and its peers `graph`, `retrieval`, `session-logging`, `mcp-tools`
  are already roots. The measured proposal (four children, 26.7% -> 9.9%) would have contradicted the
  file's own stated design, and the swarm had just measured that design HOLDING: 34 of the 39 entries it
  declined to file under a new area belonged to a different existing root.
  The rename follows from the same argument. `memory-seed` read like the whole package, which is exactly
  what a residual must not read like - it invited every entry with no obvious home and collected 127.
  Known consequence, accepted: filtering `seed-core` no longer reaches the four areas. Under the
  residual reading that is correct - those entries were never ABOUT the residual, they were parked there.
- A: Four children of `memory-seed` as measured - rejected by JNL. Roots without the rename - JNL took
  the third option, the rename being what stops the residual re-collecting.
- F: `.memory-seed/topics.yaml`, `docs/2_Todo/memory-trace-children-proposal.md`.
- T: `Topic vocabulary OK` (69 topics, 476 entries). 779 Seed tests + 213 Trace tests pass. Axis
  inherits to generation 3 (`inspector` -> area via `panes` -> `memory-trace`); `memory-seed` resolves
  to `seed-core`; reach unchanged at 204 / 109.
```

## 49. mse_z61np2tq3zkg01ew:d1 - Medium

- Decision timestamp: `2026-06-27T22:37:00+00:00`
- Decision source: `.memory-seed/sessions/2026-06/2026-06-27.md:112`
- Candidate session: `019f0a8c-6dfa-72f3-902a-fe8af9bcf875`
- Conversation timestamp: `2026-06-27T19:26:43.254000+00:00`
- Source: `.codex/sessions/2026/06/27/rollout-2026-06-27T20-26-43-019f0a8c-6dfa-72f3-902a-fe8af9bcf875.jsonl`
- Evidence: score 0.448; TF-IDF 0.188; phrase 4 tokens; time 3.2h; identifiers 23:37, graph/timeline/data, light/dark, memory-seed/sessions/2026-06-27.md, radix/shadcn-style; actor compatible
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: none recorded
- Second best: `019f0b5e-267a-7263-8c5c-0f6fb130fe4b` (score 0.244; TF-IDF 0.055; phrase 2 tokens; time 0.6h; identifiers light/dark; actor compatible)

Decision record:

```text
- D: Recommend a Radix/shadcn-style token system for theming, Tremor-style analytical surfaces for graph/timeline/data density, and Untitled UI as the Figma-grade design-language reference.
- R: Memory Lense needs compact, technical, themeable application UI rather than a marketing template; the shortlist emphasizes CSS variables, light/dark mode, accent scales, dense data views, and accessible components.
- F: `.memory-seed/sessions/2026-06-27.md`.
- T: Web research only; no source changes.
```

Candidate source window (coordinates only; raw text is in the private audit):

- turns `4..8`
- JSONL ordinals `[243, 247, 248, 249, 250, 256, 257, 258, 264, 265, 266, 267, 268, 276, 277, 278, 279, 286, 287, 288, 289, 296, 297, 298, 299, 300, 308, 311, 312, 313, 317, 320, 325, 330, 334, 335, 340, 341, 342, 346, 349, 354, 359, 363, 386, 387, 388, 392, 395, 400, 405, 409, 410, 411, 415, 418, 423, 428, 432]`
- messages `59`; SHA-256 `f8120064fb7490eba8761ba4ee30d4ea32f0ec38a668fcfb13db5946dc9b1bd3`

## 50. mse_zdw5vvvazqcac1ky:d1 - No match

- Decision timestamp: `2026-07-20T18:47:00+00:00`
- Decision source: `.memory-seed/sessions/2026-07/2026-07-20.md:1241`
- Candidate session: `none`
- Conversation timestamp: `unknown`
- Source: `none`
- Evidence: no candidate
- Unique: `True`
- Ambiguity: none recorded
- Diagnostic failure mode: decision appears to have been created outside retained Codex conversation history
- Second best: `none`

Decision record:

```text
- D: Following the long-horizon roadmap plan set via `/goal`, closed Phase 0's first cheap-parallel item:
  Track A.4, the `memory-seed[lense]`/`memory-seed lense` deprecation window. Applied the recommended
  default from 0_NEXT_STEPS.md's open decision #3 - option (a), announce 2.20 as the drop and remove the
  alias/shim now the window has elapsed - since the plan explicitly called this out as idle only because
  no one had clicked yes.
- R: Removed `pyproject.toml`'s `lense` extra and `cli.py`'s `lense` subparser/handler outright rather than
  soft-deprecating further, since the alias already shipped through its full one-release window (2.16-2.19)
  with removal previously declined once already ("removal never consented" per 0_NEXT_STEPS.md). Replaced
  the two shim-behavior tests in `test_cli_help.py` with one regression test asserting `lense` is now an
  unrecognized argparse choice, so a future accidental re-add would be caught. `memory-trace-distribution-plan.md`
  named this exact removal as its last open obligation, so resolving it also completed that plan - moved it
  `2_Todo` -> `5_Completed` and fixed every citing link across 8 other docs (mix of bare-relative and
  `../lane/` prefixed hrefs, each recomputed for its actual source-file depth rather than blanket-replaced).
- F: `pyproject.toml`, `memory_seed/cli.py`, `tests/test_cli_help.py`, `README.md`,
  `docs/3_Spec/functionality-audit.md` (bumped 2.19 -> 2.20), `CHANGELOG.md` (new "### Removed" under
  Unreleased), `docs/2_Todo/0_NEXT_STEPS.md`, `docs/2_Todo/memory-trace-next-generation-coverage-matrix.md`,
  `docs/5_Completed/memory-trace-distribution-plan.md` (moved), plus link fixes in
  `memory-trace-ai-timeline-summarisation-plan.md`, `session-decision-diagrams-plan.md`, `3.0-plan.md`,
  `memory-explorer-entry-level-ui-results-plan.md`, `memory-trace-product-and-trail-view-plan.md`,
  `memory-trail-renaming-plan.md`, `user-interface-deep-research-report.md`,
  `codex-proposal-synergy-evaluation.md`.
- T: `pytest tests/test_cli_help.py` - 28/28. Full `pytest tests` - 640 passed (was 641; net -1 from
  removing 2 tests and adding 1), 14 subtests passed. `docs index` regenerated the 3 affected lane tables;
  `docs check` - "Docs lifecycle OK (166 file(s) checked)", 15 pre-existing warnings, zero broken-link
  errors after fixing all 24 the move produced. `links check` - "Session memory integrity OK". Merged
  `claude/feature/lense-deprecation-removal` to main, branch deleted.

  Phase 0 of the long-horizon plan continues: next is Track C.2 (ESR persona-usage check,
  propose-and-wait), then the Storybook/Playwright/accessibility work for B0b Trail parity.
```
