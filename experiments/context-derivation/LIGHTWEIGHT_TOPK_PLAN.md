# Lightweight Top-K Decision-to-ADR Experiment

Status: **APPROVED FOR IMPLEMENTATION; SCORED EXECUTION STILL OWNER-GATED**

## Global constraints

- Keep every addition experiment-only. Do not change production MCP, retrieval, ADR, Constitution, index, or ranking contracts.
- Measure K only at 1, 3, and 5. K is an offline metric, never an MCP field.
- Rank-selected canonical decision IDs are ADR roots. Relevance bands remain diagnostic-only while `relevance_calibrated` is false.
- A query is recalled only when all required entry-point decisions are within K.
- Select the smallest K with at least 95% complete-query recall and 100% ADR closure, authority, status, typed-edge, and related-safety gates.
- Subject answers come only from a pinned local instruction SLM and pinned Luna. Terra/Sol may orchestrate or review but never answer subject tasks.
- Mechanical scoring is authoritative. An LLM judge cannot repair or override a mechanical failure.
- Scored runs, model downloads, and provider calls remain fail-closed behind explicit owner approval and frozen manifests.

## Task 1 - Freeze the 60-query corpus and gold

- Expand the 12 revision-scoped benchmark tasks into five deterministic, independently worded query variants each.
- Add versioned experiment schemas/manifests for query variants and exact task-to-gold inheritance.
- Keep gold outside subject run directories; query rows may identify only their base task and fixture, never required answer refs.
- Validate exactly 60 unique query IDs in stable order, five per task, with stable fingerprints and no gold leakage.
- Preserve CTX-06 and CTX-09 ADR-to-Constitution pairing and CTX-12 as the missing-evidence negative control.
- Add fixture/query determinism and schema tests.

## Task 2 - Implement complete-query Top-K and ADR-closure scoring

- Evaluate production-default decision ranking for every query at K=1,3,5; keep lexical-only as a diagnostic arm.
- Compute complete-query recall, individual decision recall, MRR, first-hit rank, stable ordering, latency, and token proxy.
- For each required decision within K, resolve all ADR membership including historical, pending, rejected, and curated predecessor decisions.
- Verify every matching ADR current head, status, required typed path, and revision-scoped Constitution binding.
- Treat any missing authority, incorrect status/edge, Constitution mismatch, or `related` leakage as a hard failure even when recall passes.
- Select the smallest passing K; return no recommendation if K=5 fails.
- Reject empty denominators, incomplete shards, derived/implicit Constitution gold, and vacuous passes.
- Add focused unit and reducer tests for single, multi-decision, shared-ADR, historical-head, pending, rejected, related-only, and missing-evidence cases.

## Task 3 - Add local-SLM and Luna subject harnesses

- Add experiment-only provider adapters behind one subject-run interface.
- Local protocol ladder: `qwen2.5:0.5b`, then `qwen2.5:1.5b`, then `qwen2.5:3b`; select the lightest model that completes the protocol probe. The installed `qwen2.5-coder:1.5b-base` is ineligible.
- The protocol probe checks schema-valid JSON, included-evidence citations, required fields, no undeclared tools/filesystem, context fit, and completion stability. It does not promote a model for content errors.
- Pin local model name, Ollama digest/version, quantization, context window, and decoding settings. Pin the provider-reported Luna ID/version after an unscored connectivity probe.
- Materialize three immutable arms: `decision-only`, `adr-current`, and `adr-constitution` with lower-ranked compact references.
- Freeze exactly 60 queries x 3 arms x 2 subject models = 360 subject cells, one run per cell, in deterministic order.
- Give every run an isolated output directory and no repository access. Fixed packets expose no retrieval tools.
- Record transcripts, answer JSON, model/runtime pins, duration, token usage/proxy, protocol failures, and context fingerprint.
- Do not invoke or download any model during unit tests.

## Task 4 - Score, report, and validate the integrated experiment

- Mechanically score evidence sufficiency, ADR IDs, authoritative refs, statuses, typed edges, Constitution refs, citations, and abstention.
- Require independently for local and Luna: at least 90% complete correctness on `adr-constitution`, 100% authority/status, 100% missing-evidence abstention, zero related leakage, and resolvable material citations.
- Compare the three arms; `adr-constitution` must be no worse than `adr-current` or `decision-only`.
- Permit Terra orchestration and a preregistered Sol review subset for explanation quality only; store those verdicts separately from mechanical scores.
- Generate per-K tables, task-family failures, local-versus-Luna results, context-token and latency distributions, exclusions, and an explicit minimum-capability conclusion.
- Run the complete context-derivation tests, repeat determinism checks, validate manifests/fingerprints, run ESR, and commit without launching a scored run, pushing, or opening a PR.
