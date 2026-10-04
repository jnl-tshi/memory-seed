---
memory-system-version: 2.23
tags:
  - hosted
  - postgresql
  - data-model
  - migration
  - authority
  - sdd
status: accepted
priority: P0
next_action: "Complete the R0 full-corpus field and actor inventory with zero unknowns, then dispatch R1A through the SDD Task Packet loop."
programme: hosted-memory-mvp
---

# Hosted PostgreSQL Data Model and Authority-Transfer Plan

Status: **ACCEPTED EXECUTION PLAN.** This is the canonical bounded plan for the PostgreSQL substrate,
full-corpus parity migration, and gradual transfer from local Markdown authority to the hosted service. It
refines P0.3, P0.4, and the P1 pilot in the
[Hosted Memory MVP Programme](hosted-memory-mvp-programme.md); that programme remains the product-level
authority.

## Outcome and non-negotiable boundary

Build the hosted SQL surface as a complete, testable shadow of the existing Memory Seed corpus before it
becomes authoritative. The transition is gradual:

```text
local_authoritative -> shadowing -> cutover_ready -> hosted_authoritative
```

There are no dual authoritative writers and no opportunistic dual writes. Local Markdown remains authoritative
through R0-R5. Hosted PostgreSQL becomes the primary surface only at the R6 P1 pilot gate, after an explicit
lead approval binds the exact import manifest, restore proof, and authority epoch. Returning authority to local
is a separate, explicit reverse-transfer operation.

The import is semantic-lossless for the full historical corpus, not only the current curated-record slice.
Every useful existing session-log metadata field, ADR and Constitution relationship, topic/alias assignment,
diagram reference, provenance coordinate, participant identity, validation receipt, and lifecycle edge is
either mapped to a named hosted column/table or classified as intentionally non-authoritative. An unclassified
field or actor blocks cutover.

## Design-discovery record

Design Discovery v2 was run for schema, security, migration, and multi-user-session concerns. Evidence Pack
fingerprint: `sha256:71f81ae632ce7a551bad4e439521df7c3b6a295b40ede84386ee7e951139a0db`.
The pack was partial because the bounded retrieval limit omitted lower-ranked candidates, so R0 also requires
a mechanical field-and-actor inventory of the complete corpus.

The authority assessment applies these constraints to the plan decision:

- governed by the ratified append-only, ownership, hosted-removal, Markdown-authority, provenance,
  retrieval-transparency, evidence-first, topic-vocabulary, draft-format, edge-kind, trust-first, and ADR-ledger
  clauses;
- builds on `adr_markdown_substrate`, `adr_session_decision_authority`, `adr_topic_authority`,
  `adr_decision_identity`, `adr_derived_precedence`, `adr_draft_format`, and
  `adr_entry_id_scheme`;
- preserves edge confidence as supporting provenance;
- carries forward the owner-only raw-evidence and content-free tombstone decision
  (`mse_ad2jp0msr78je6zw:d4`) and the backup/purge contract
  (`mse_bhg24h2901ehjajt:d1`);
- uses packet-verified governance and source-following rules from
  `mse_yz25a19sdq9akxmh:d1` and `mse_yz25a19sdq9akxmh:d2` for every SDD handoff.

## PostgreSQL foundation

- PostgreSQL 18 is the initial engine. The local development image and the pgvector extension are pinned by
  immutable image digest in R1; pgvector's current stable target is 0.8.6.
- One PostgreSQL schema, `memory_seed`, holds the hosted model.
- Migrations are forward-only yoyo migrations under `hosted/migrations/`; reusable SQL lives under
  `hosted/sql/`. Application access uses psycopg 3, `psycopg_pool`, and plain SQL.
- Internal primary keys are UUIDv7. Public APIs use opaque, random, type-prefixed identifiers. Imported
  `mse_*` identities and other canonical source IDs remain stable external identities rather than being
  rewritten into new hosted IDs.
- Stable vocabularies use seeded reference tables, not PostgreSQL enums, so additions remain deployable without
  enum migration coupling.
- Every tenant-owned child has `tenant_id`, and tenant/project relationships use composite foreign keys where
  needed so a foreign identifier cannot cross a tenant boundary accidentally.
- All timestamps are `timestamptz` in UTC. Mutable rows carry `created_at`, `updated_at`, and
  `row_version`; immutable ledgers carry `created_at` only.
- Exact uniqueness is tenant-scoped unless the identifier is deliberately global. Delegation targets use
  explicit foreign keys to their permitted scope.
- PostgreSQL 18 `WITHOUT OVERLAPS` constraints are used only for time-bounded authorities where overlapping
  intervals are semantically invalid.

## Security and transaction contract

Every tenant/project table has row-level security enabled and forced. The schema owner is `NOLOGIN`; the
application role owns no tables and has neither `BYPASSRLS` nor superuser capability. Public read models are
`security_invoker` views.

At transaction start the data-access layer sets validated, transaction-local context with
`set_config(..., true)`: tenant, member, agent principal, request ID, and authority epoch. Policies fail
closed when context is absent or malformed. Autocommit is forbidden for application data access. Pool checkout
and return behavior is tested to prove context cannot leak between requests; the implementation may use reset
hooks or targeted cleanup, but must not assume that an unconditional `DISCARD ALL` is correct for every pool.

RLS tests connect as the real application role and generate a matrix across tenants, projects, memberships,
owner-only raw evidence, curated sharing, delegation, tombstones, and operator denial. Catalog lint fails when a
tenant table lacks forced RLS, a policy, a composite containment constraint, or an allowed view posture.

## Authority fencing and concurrency

`projects.authority_state` and `projects.authority_epoch` are the database fencing token. Every INSERT,
UPDATE, and DELETE path checks the expected epoch. A writer locks the project row `FOR SHARE`; a cutover or
reverse transfer takes the conflicting project-row lock, validates the manifest, advances the epoch, and commits
the new state atomically. Lifecycle transitions also take transaction-scoped advisory locks keyed by project.
Longer multi-step freezes use a monotonic token and never rely on a process-local mutex.

Mutation functions, grants, and triggers jointly enforce immutability. Current-version pointers may be null
inside a transaction while a version is installed, but deferred constraints/triggers require a valid current
version at commit. Assertion status is derived from later assertions and lifecycle edges; prior assertions are
not destructively updated to manufacture history.

## Canonical bytes and idempotency

Canonical digests use UTF-8, NFC normalization, LF line endings, RFC 8785 JSON, fixed UTC timestamp rendering,
an explicit absent-versus-null rule, and a stored `digest_version`. Import, export, event, evidence, record
version, and authority receipts bind their canonical digest.

Every externally retryable mutation has an idempotency key plus request digest. Reusing a key with a different
digest is a conflict. Event `source_sequence` is assigned by the capture client within one capture session;
payloads carry a schema version. Audit rows are written atomically with the governed mutation. A tamper-evident
audit hash chain is intentionally deferred until the ordinary audit model is operating.

Exports and final-delta cutover reads use one `SERIALIZABLE READ ONLY DEFERRABLE` consistent snapshot. Normal
event ingestion and retrieval do not pretend that page-by-page reads are a database snapshot.

## Data model

All tables live in `memory_seed`. Columns below are the minimum contractual shape; R1/R2 may add operational
columns only when they preserve these ownership and authority boundaries.

### Identity and access

| Table | Required columns and constraints |
| --- | --- |
| `tenants` | `id`, `public_id`, `slug`, `display_name`, `status_id`, timestamps; unique slug/public ID |
| `members` | `id`, `public_id`, `display_name`, `status_id`, timestamps |
| `member_identities` | `id`, `member_id`, `provider_id`, `provider_subject`, `login_hint`, timestamps; unique provider subject |
| `tenant_memberships` | `tenant_id`, `member_id`, `role_id`, `status_id`, validity period, timestamps; non-overlapping active grants |
| `projects` | `tenant_id`, `id`, `public_id`, `slug`, `display_name`, `authority_state_id`, `authority_epoch`, `active_constitution_version_id`, timestamps |
| `project_memberships` | `tenant_id`, `project_id`, `member_id`, `role_id`, `status_id`, validity period, timestamps |
| `delegations` | `tenant_id`, `id`, `project_id`, `grantor_member_id`, `grantee_member_id`, `scope_type_id`, `scope_record_id`, `permission_id`, validity period, `revoked_at`, `reason` |
| `agent_principals` | `tenant_id`, `id`, `project_id`, `member_id`, `client_id`, `agent_type_id`, `display_name`, `status_id`, timestamps |

JNL maps to the current member principal. Claude and Codex remain separate agent principals; their actions are
not collapsed into the member identity.

### Authority transfer and import

| Table | Required columns and constraints |
| --- | --- |
| `project_authority_transitions` | `tenant_id`, `id`, `project_id`, `from_state_id`, `to_state_id`, `from_epoch`, `to_epoch`, `manifest_digest`, `requested_by_member_id`, `approved_by_member_id`, `started_at`, `committed_at`, `failed_at`, `failure_code` |
| `authority_receipts` | `tenant_id`, `id`, `project_id`, `transition_id`, `receipt_type_id`, `canonical_digest`, `digest_version`, `payload_json`, `created_at` |
| `project_migration_locks` | `tenant_id`, `project_id`, `lock_token`, `authority_epoch`, `holder_id`, `expires_at`, `created_at` |
| `import_runs` | `tenant_id`, `id`, `project_id`, `source_revision`, `source_manifest_digest`, `mode_id`, `status_id`, counts, timestamps |
| `import_objects` | `tenant_id`, `import_run_id`, `source_kind_id`, `source_locator`, `source_digest`, `target_kind_id`, `target_id`, `result_id`, `error_code` |
| `import_checkpoints` | `tenant_id`, `import_run_id`, `checkpoint_kind_id`, `cursor_json`, `objects_seen`, `checkpoint_digest`, `created_at` |
| `import_field_decisions` | `tenant_id`, `id`, `source_field`, `source_shape`, `classification_id`, `target_table`, `target_column`, `transform_version`, `rationale`, `approved_by_member_id`, `approved_at` |
| `external_identifiers` | `tenant_id`, `id`, `project_id`, `namespace_id`, `external_id`, `entity_kind_id`, `entity_id`, `source_locator`; unique namespace/external ID |

### Capture and raw events

| Table | Required columns and constraints |
| --- | --- |
| `integrations` | `tenant_id`, `id`, `project_id`, `provider_id`, `installation_ref`, `status_id`, credential reference, timestamps |
| `repositories` | `tenant_id`, `id`, `project_id`, `provider_id`, `provider_repo_id`, `canonical_url`, `default_branch`, timestamps |
| `capture_sessions` | `tenant_id`, `id`, `project_id`, `owner_member_id`, `agent_principal_id`, `client_session_id`, `started_at`, `ended_at`, `last_source_sequence`, `payload_schema_version` |
| `branch_identities` | `tenant_id`, `id`, `project_id`, `repository_id`, `canonical_name`, timestamps |
| `branch_observations` | `tenant_id`, `id`, `capture_session_id`, `branch_identity_id`, `observed_name`, `head_commit_sha`, `observed_at` |
| `events` | `tenant_id`, `id`, `project_id`, `capture_session_id`, `source_sequence`, `event_type_id`, `authorship_id`, `occurred_at`, `received_at`, `payload_schema_version`, `payload_json`, canonical digest fields, idempotency fields; unique session/sequence |
| `event_gap_reports` | `tenant_id`, `id`, `capture_session_id`, expected/observed sequence bounds, `status_id`, timestamps |
| `ingest_diagnostics` | `tenant_id`, `id`, `capture_session_id`, `event_id`, `severity_id`, `code`, `detail_json`, `created_at` |

The adapter's local SQLite queue remains non-authoritative transport state and is never treated as a second
hosted database.

### Evidence and source artifacts

| Table | Required columns and constraints |
| --- | --- |
| `evidence_items` | `tenant_id`, `id`, `project_id`, `owner_member_id`, `capture_session_id`, `kind_id`, `availability_id`, `content_ciphertext`, `content_digest`, `digest_version`, `purged_at`, timestamps |
| `evidence_spans` | `tenant_id`, `id`, `evidence_item_id`, `ordinal`, byte/line/message coordinates, `span_digest` |
| `project_artifacts` | `tenant_id`, `id`, `project_id`, `artifact_kind_id`, `canonical_path`, `revision`, `content_digest`, `metadata_json`, timestamps |
| `record_evidence_links` | `tenant_id`, `record_id`, `record_version_id`, `evidence_item_id`, `evidence_span_id`, `link_role_id`, `created_at` |
| `record_artifact_links` | `tenant_id`, `record_id`, `record_version_id`, `artifact_id`, `line_start`, `line_end`, `link_role_id` |
| `record_validations` | `tenant_id`, `id`, `record_version_id`, `validator_kind_id`, `status_id`, `evidence_digest`, `detail_json`, `created_at` |
| `repository_commits` | `tenant_id`, `repository_id`, `commit_sha`, `parent_shas`, `authored_at`, `committed_at`, `metadata_json` |
| `record_commit_links` | `tenant_id`, `record_id`, `record_version_id`, `repository_id`, `commit_sha`, `link_role_id` |

A privacy purge nulls protected content while retaining the evidence row, canonical digest, availability state,
and authorized audit metadata. Raw content remains visible only to its owner and the narrowly scoped curator
principal; leads and operators do not gain raw-content access.

### Curated memory and assertions

| Table | Required columns and constraints |
| --- | --- |
| `memory_entries` | `tenant_id`, `id`, `project_id`, `external_entry_id`, `entry_date`, `title`, `source_path`, `source_ordinal`, `current_version_id`, timestamps |
| `memory_records` | `tenant_id`, `id`, `project_id`, `entry_id`, `external_record_id`, `record_type_id`, `ordinal`, `current_version_id`, `visibility_id`, timestamps |
| `record_versions` | `tenant_id`, `id`, `record_id`, `version_number`, `title`, `body_markdown`, `scope_markdown`, `rationale_markdown`, `alternatives_markdown`, `disposition_id`, canonical digest fields, actor and timestamps; immutable |
| `record_origins` | `tenant_id`, `record_id`, `origin_kind_id`, `member_id`, `agent_principal_id`, `source_event_id`, `provenance_id`, `created_at` |
| `artifact_lineage_assertions` | `tenant_id`, `id`, `record_version_id`, `artifact_id`, `assertion_kind_id`, `confidence`, `asserted_by_id`, `created_at` |
| `record_tombstones` | `tenant_id`, `record_id`, `reason_id`, `requested_by_member_id`, `authorized_by_member_id`, `removed_at`, `prior_digest`; no title/body |
| `relationship_assertions` | `tenant_id`, `id`, `project_id`, `source_record_id`, `target_record_id`, `relationship_kind_id`, `confidence`, `origin_id`, `asserted_at`, `retracted_by_assertion_id` |
| `topic_assertions` | `tenant_id`, `id`, `record_id`, `topic_id`, `assertion_kind_id`, `confidence`, `origin_id`, `asserted_at`, `retracted_by_assertion_id` |
| `topics` | `tenant_id`, `id`, `project_id`, `slug`, `display_name`, `description`, `status_id`, timestamps |
| `topic_aliases` | `tenant_id`, `topic_id`, `alias`, `normalized_alias`, `origin_id`, timestamps |

The initial curated record types are Decision and Documentation only. A generic Fact record is not introduced.

### Governance and diagrams

| Table | Required columns and constraints |
| --- | --- |
| `constitutions` | `tenant_id`, `id`, `project_id`, `public_id`, `name`, `current_version_id`, timestamps |
| `constitution_versions` | `tenant_id`, `id`, `constitution_id`, `version_label`, `status_id`, `body_markdown`, canonical digest fields, ratifier and timestamps |
| `constitution_clauses` | `tenant_id`, `id`, `constitution_version_id`, `anchor`, `ordinal`, `title`, `body_markdown`, `content_digest` |
| `adrs` | `tenant_id`, `id`, `project_id`, `adr_id`, `title`, `status_id`, `current_event_id`, timestamps |
| `adr_memberships` | `tenant_id`, `adr_id`, `record_id`, `membership_kind_id`, `added_at`, `removed_at` |
| `adr_events` | `tenant_id`, `id`, `adr_id`, `event_kind_id`, `record_id`, `payload_json`, `occurred_at`; immutable |
| `diagram_artifacts` | `tenant_id`, `id`, `project_id`, `source_path`, `diagram_kind_id`, `source_digest`, `render_digest`, `metadata_json`, timestamps |

Future semantic diagram grounding belongs in `diagram_groundings`, but that table is deferred until a real
grounding workflow exists.

### Guarded workflows

| Table | Required columns and constraints |
| --- | --- |
| `submissions` | `tenant_id`, `id`, `project_id`, submitter principal, `submission_kind_id`, `request_digest`, `idempotency_key`, `status_id`, timestamps |
| `accepted_writes` | `tenant_id`, `id`, `submission_id`, `record_id`, `record_version_id`, `authority_epoch`, `accepted_by_member_id`, `accepted_at` |
| `pending_mutations` | `tenant_id`, `id`, `project_id`, `mutation_kind_id`, target, `request_digest`, `required_permission_id`, `expires_at`, `status_id`, timestamps |
| `approval_decisions` | `tenant_id`, `id`, `pending_mutation_id`, `member_id`, `decision_id`, `confirmation_channel_id`, `attestation_digest`, `decided_at` |
| `curator_jobs` | `tenant_id`, `id`, `project_id`, `job_kind_id`, source bounds, `status_id`, timestamps |
| `curator_runs` | `tenant_id`, `id`, `curator_job_id`, `model_ref`, `prompt_digest`, `input_manifest_digest`, `status_id`, usage and timestamps |
| `curator_suggestions` | `tenant_id`, `id`, `curator_run_id`, `suggestion_kind_id`, `payload_json`, `confidence`, `status_id`, timestamps |
| `suggestion_citations` | `tenant_id`, `suggestion_id`, evidence/artifact coordinates, `citation_role_id`, `citation_digest` |
| `validation_results` | `tenant_id`, `id`, subject kind/id, `validator_id`, `status_id`, `detail_json`, `created_at` |

### Retrieval and operations

| Table | Required columns and constraints |
| --- | --- |
| `embedding_models` | `id`, `provider`, `model_name`, `model_revision`, `dimensions`, `distance_metric_id`, `status_id`, timestamps |
| `record_embeddings` | `tenant_id`, `project_id`, `record_version_id`, `embedding_model_id`, `embedding`, `source_digest`, timestamps; one current vector per model/version |
| `search_documents` | `tenant_id`, `project_id`, `record_version_id`, lexical document, normalized text, `source_digest`, timestamps |
| `retention_policies` | `tenant_id`, `id`, `project_id`, `data_class_id`, `retention_interval`, `purge_mode_id`, `version`, timestamps |
| `retention_events` | `tenant_id`, `id`, `policy_id`, target kind/id, `event_kind_id`, before/after availability, digests, actor and `occurred_at` |
| `export_runs` | `tenant_id`, `id`, `project_id`, `authority_epoch`, snapshot metadata, manifest digest, status and timestamps |
| `export_receipts` | `tenant_id`, `id`, `export_run_id`, `artifact_kind_id`, `artifact_digest`, `record_count`, `created_at` |
| `audit_events` | `tenant_id`, `id`, `project_id`, request/actor/agent identifiers, `action_id`, target kind/id, `authority_epoch`, `request_digest`, `outcome_id`, `detail_json`, `occurred_at` |

pgvector supports mixed model dimensions by storing a general vector value and building one partial expression
index per active model/dimension. HNSW indexes must respect pgvector's 2,000-dimension limit. Filtered retrieval
under RLS uses iterative scans where appropriate. Every index choice requires measured recall/latency tests
against exact search; no approximate index becomes authoritative by default.

## Workstreams and gates

### R0 — plan, crosswalk, and orchestration

- Record this plan and integrate it with the programme, Next Steps, and runtime active state.
- Generate a complete source-field and actor inventory from existing Markdown/session metadata.
- Produce the import crosswalk and representative fixtures.
- Exit: the plan compiles into ordered Task Packets; every useful source field and actor is mapped or explicitly
  classified, with zero unknowns.

### R1 — secure PostgreSQL foundation

1. Pin PostgreSQL/pgvector environment and establish yoyo migrations.
2. Create roles, seeded catalogs, schema conventions, and identity/project tables.
3. Implement the transaction-scoped context data-access layer, forced RLS, and authority-epoch mutation guard.
4. Add generated RLS matrix, catalog lint, migration, and pool-reset tests.

Exit: migrations apply from empty and upgrade fixtures; all security tests run as the real app role; missing
context and cross-tenant access fail closed.

### R2 — corpus core and parity

1. Freeze the complete field/actor crosswalk and golden import fixtures.
2. Create curated-memory, governance, diagram, provenance, and external-identity tables.
3. Implement canonical digesting and the repeatable shadow importer.
4. Implement consistent-snapshot export.
5. Run full-corpus property and semantic parity tests, including governance/diagram metadata.

Exit: repeated imports are idempotent, a full historical corpus round-trips without semantic loss, and the
shadow database can be discarded and rebuilt from the same source manifest.

### R3 — authority-transfer rehearsal

1. Enforce epoch checks on every mutation.
2. Implement project/advisory locks and transition receipts.
3. Implement final delta, cutover, failed-cutover rollback, reverse transfer, and restore procedures.
4. Run concurrency races and a tested database restore.

Exit: stale writers are fenced, a cutover cannot overlap an accepted write, failures leave Markdown
authoritative, reverse transfer is explicit, and restore succeeds before authority can move.

### R4 — capture and evidence

1. Land versioned event ingestion with client-assigned per-session sequence numbers and idempotent retries.
2. Land owner-only evidence, spans, gap reports, diagnostics, and retention/purge behavior.
3. Prove digest-bound replay, RLS privacy, tombstone, and retention behavior.

Exit: accepted replay is complete and deterministic, raw evidence never crosses owners, and purged content is
unavailable while its permitted digest/audit trail remains.

### R5 — P0.4 useful loop

1. Land submissions, pending mutations, human-confirmed approvals, and accepted-write receipts.
2. Land the curator job/run/suggestion/citation ledger.
3. Land lexical/vector projections and transparent retrieval.
4. Expose the smallest MCP flow: submit one explicit decision, approve it, retrieve it with provenance.
5. Run end-to-end negative controls for tenant, privacy, delegation, idempotency, and stale epochs.

Exit: one authenticated useful loop works locally against PostgreSQL and returns the accepted Decision with its
evidence, authority epoch, and visible lifecycle status.

### R6 — P1 pilot and gradual cutover

R6 is not an SDD implementation task and cannot start automatically. Move to managed PostgreSQL, rehearse
backup/restore there, compare the final shadow import, and obtain explicit lead approval naming the exact source
manifest digest and next authority epoch. Only then advance `cutover_ready -> hosted_authoritative`. The hosted
service becomes the primary surface at that moment; local Markdown changes to an export/read-only compatibility
surface for that project.

## SDD orchestration

R0 is direct orchestrator-owned documentation and control-plane work. R1-R5 each run in a separate
Memory Seed worktree/branch and are integrated strictly in order. Within each workstream, execute tasks
sequentially using Subagent-Driven Development:

1. compile one writing Task Packet with `task-packet from-plan --handoff sdd`;
2. dispatch a fresh implementer for that task;
3. dispatch an independent reviewer against the task's acceptance observables and diff;
4. allow no more than five implement/review repair rounds;
5. integrate the accepted task before dispatching the next dependent task;
6. after the workstream tasks pass, run one whole-branch frontier review before the Memory Seed integration gate.

Superpowers SDD scratch remains under ignored `.superpowers/sdd/`. At execution start, verify a compatible
Superpowers release (`>=6.2.0,<7.0.0`); if unavailable, retain the same sequential implementer/reviewer protocol
through Memory Seed Fan-Out. Workers never edit session memory, the programme, this plan, or authority policy;
the orchestrator owns those shared files and integrates branch-local session entries with
`memory-seed session merge-branch`.

Branch order:

| Workstream | Branch intent | Ordered SDD tasks |
| --- | --- | --- |
| R1 | `codex/feature/hosted-postgres-foundation` | environment/migrations -> roles/catalogs/schema conventions -> transaction/RLS DAL -> catalog/security tests |
| R2 | `codex/feature/hosted-corpus-parity` | crosswalk/fixtures -> curated/governance schema -> importer/digests -> exporter -> full-corpus/property parity |
| R3 | `codex/feature/hosted-authority-transfer` | epoch/mutation guards -> locks/transitions -> export/final-delta/reverse transfer -> restore/concurrency |
| R4 | `codex/feature/hosted-capture-evidence` | event ingestion -> evidence/RLS/retention -> replay/privacy tests |
| R5 | `codex/feature/hosted-useful-loop` | submissions/approvals -> curator ledger -> retrieval projections -> MCP loop -> end-to-end tests |

## Verification matrix

- migrations: empty install, every supported upgrade path, forward-only failure recovery, schema dump diff;
- security: generated RLS role/tenant/project matrix, forced-RLS catalog lint, pool context leakage tests;
- concurrency: accepted-write/cutover races, stale epoch writes, advisory lock ordering, failed and reversed cutover;
- parity: field inventory completeness, canonical digest vectors, import idempotency, property round-trip, complete
  historical corpus comparison;
- privacy/retention: owner-only raw evidence, curator-only machine read, purge/tombstone behavior, backup restore;
- retrieval: exact versus approximate recall, filtered RLS recall, mixed-dimension index coverage;
- operations: consistent-snapshot export, manifest binding, tested restore, immutable authority receipts;
- product: authenticated P0.4 submission/approval/retrieval loop with negative controls.

## Replan conditions

Stop and return to R0 if a source field or actor cannot be classified, an ownership boundary requires elevated
raw access, PostgreSQL cannot enforce a required invariant without application trust, canonical bytes differ
between import/export implementations, a migration requires destructive contraction before cutover, or an SDD
task would need to cross workstream edit ownership. R6 must also stop if the final shadow manifest, restore
receipt, or requested authority epoch differs from the item approved by the lead.

## Executable Task Packet plan

The block below is the dispatch authority for R1-R5. Execute one task at a time with the SDD review loop above. R6 is absent by design.

```json
{
  "schema": "memory-seed/plan-dispatch",
  "version": 1,
  "defaults": {
    "constitution_refs": [
      "constitution:v2#markdown-authority",
      "constitution:v2#ownership",
      "constitution:v2#append-only",
      "constitution:v2#hosted-curated-removal",
      "constitution:v2#provenance",
      "constitution:v2#trust-first"
    ],
    "project_context": {
      "project_type_and_purpose": "Memory Seed is a local-first, Markdown-authoritative memory system with a separately governed hosted team edition. This plan builds and proves the PostgreSQL substrate before hosted authority is permitted.",
      "relevant_subsystem": "The hosted PostgreSQL schema and migrations, complete Markdown/session corpus importer/exporter, authority transitions, capture/evidence service, and guarded MCP useful loop.",
      "task_fit": "R1-R5 are ordered SDD tasks. Each task gets a fresh implementer, an independent task review, and no authority beyond its edit ownership.",
      "downstream_use": "After each workstream receives a whole-branch frontier review, R6 may begin only with a new explicit pilot approval for the exact manifest, restore receipt, and authority epoch.",
      "non_goals": [
        "Do not cut over authority, introduce dual writes, start the managed pilot, add a generic Fact record, or implement an audit hash chain in R1-R5."
      ]
    },
    "execution": {
      "role": "worker",
      "persona": "none",
      "capability_tier": "balanced",
      "forbidden_files": [
        ".memory-seed/policy.md",
        ".memory-seed/index.md",
        ".memory-seed/sessions",
        "docs/2_Todo/hosted-postgresql-data-model-and-authority-transfer-plan.md",
        "docs/2_Todo/hosted-memory-mvp-programme.md",
        "docs/2_Todo/0_NEXT_STEPS.md"
      ],
      "output_contract": [
        "Return the lite return contract with changed files, verification, unresolved risks, and no session-memory edits.",
        "Stop at the named task boundary; do not begin a dependent task or authority cutover."
      ]
    },
    "retrieval": {
      "profile": "implementation",
      "profile_version": 1,
      "overrides": {
        "selectors": {
          "pinned": [
            {
              "kind": "decision",
              "id": "mse_2w2dyj7bzk18j1dd:d1",
              "reason": "User-approved PostgreSQL model, parity, authority-transfer, and SDD scope.",
              "required": true
            }
          ]
        },
        "filters": {
          "paths": [
            "docs/2_Todo/hosted-postgresql-data-model-and-authority-transfer-plan.md"
          ],
          "topics": []
        },
        "limits": {
          "max_entries": 30,
          "max_tokens": 12000
        },
        "output": {
          "include_resolution_trace": true,
          "include_excerpts": false
        }
      }
    },
    "budget": {
      "supplemental_input_tokens": 2500,
      "output_tokens": 5000,
      "over_soft_cap": "fail",
      "over_soft_cap_reason": null
    },
    "memory_update_policy": "orchestrator"
  },
  "objectives": {
    "R1A": "Pin PostgreSQL and pgvector, establish yoyo migrations, database roles, seeded catalogs, and identity/access schema.",
    "R1B": "Implement transaction-local context, forced RLS, pool reset, epoch guards, and the generated security matrix.",
    "R2A": "Inventory every source field and actor, create golden fixtures, and add curated, governance, diagram, provenance, and external-ID schema.",
    "R2B": "Implement canonical digests, repeatable shadow import, consistent-snapshot export, and complete corpus parity tests.",
    "R3A": "Enforce authority epochs on every mutation and implement project locks, advisory locks, transitions, and immutable receipts.",
    "R3B": "Implement final delta, cutover failure recovery, reverse transfer, and restore; prove the concurrency races.",
    "R4A": "Land versioned idempotent event ingestion plus owner-only evidence, spans, gaps, diagnostics, retention, and purge.",
    "R4B": "Prove digest-bound replay, sequence-gap handling, privacy isolation, tombstones, and purge availability.",
    "R5A": "Land submissions, approvals, curator ledger, transparent retrieval projections, and the authenticated MCP useful loop.",
    "R5B": "Prove the P0.4 useful loop and tenant, privacy, delegation, idempotency, stale-epoch, and vector-recall negatives."
  },
  "implementation_plan": {
    "approval_reference": "mse_2w2dyj7bzk18j1dd:d1",
    "tasks": [
      {
        "id": "R1A",
        "acceptance_observables": [
          "Pin PostgreSQL and pgvector, establish yoyo migrations, database roles, seeded catalogs, and identity/access schema. The named verification passes and the task stays inside its workstream authority boundary."
        ],
        "edit_ownership": [
          {
            "path": "hosted/pyproject.toml",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/compose.yaml",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/migrations/001_foundation.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/sql/roles.sql",
            "line_range": [
              1,
              1
            ]
          }
        ],
        "dependencies": [],
        "evidence_references": [
          "mse_2w2dyj7bzk18j1dd:d1"
        ],
        "verification": [
          "docker compose -f hosted/compose.yaml config",
          "python -m pytest tests/hosted/test_migrations.py tests/hosted/test_catalogs.py -q"
        ],
        "replan_conditions": [
          "a source field, actor, ownership rule, or transition cannot be represented without semantic loss",
          "the task needs a later workstream's files or changes the approved authority boundary"
        ]
      },
      {
        "id": "R1B",
        "acceptance_observables": [
          "Implement transaction-local context, forced RLS, pool reset, epoch guards, and the generated security matrix. The named verification passes and the task stays inside its workstream authority boundary."
        ],
        "edit_ownership": [
          {
            "path": "hosted/db/context.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/db/pool.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/sql/rls.sql",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/sql/mutation_guards.sql",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "tests/hosted/test_rls.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "tests/hosted/test_catalog_lint.py",
            "line_range": [
              1,
              1
            ]
          }
        ],
        "dependencies": [
          "R1A"
        ],
        "evidence_references": [
          "mse_2w2dyj7bzk18j1dd:d1"
        ],
        "verification": [
          "python -m pytest tests/hosted/test_rls.py tests/hosted/test_pool_context.py tests/hosted/test_catalog_lint.py -q"
        ],
        "replan_conditions": [
          "a source field, actor, ownership rule, or transition cannot be represented without semantic loss",
          "the task needs a later workstream's files or changes the approved authority boundary"
        ]
      },
      {
        "id": "R2A",
        "acceptance_observables": [
          "Inventory every source field and actor, create golden fixtures, and add curated, governance, diagram, provenance, and external-ID schema. The named verification passes and the task stays inside its workstream authority boundary."
        ],
        "edit_ownership": [
          {
            "path": "hosted/importing/crosswalk.yaml",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/importing/actors.yaml",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/migrations/002_corpus_core.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "tests/fixtures/hosted_import/manifest.json",
            "line_range": [
              1,
              1
            ]
          }
        ],
        "dependencies": [
          "R1B"
        ],
        "evidence_references": [
          "mse_2w2dyj7bzk18j1dd:d1"
        ],
        "verification": [
          "python -m pytest tests/hosted/test_import_crosswalk.py tests/hosted/test_corpus_schema.py -q"
        ],
        "replan_conditions": [
          "a source field, actor, ownership rule, or transition cannot be represented without semantic loss",
          "the task needs a later workstream's files or changes the approved authority boundary"
        ]
      },
      {
        "id": "R2B",
        "acceptance_observables": [
          "Implement canonical digests, repeatable shadow import, consistent-snapshot export, and complete corpus parity tests. The named verification passes and the task stays inside its workstream authority boundary."
        ],
        "edit_ownership": [
          {
            "path": "hosted/importing/canonical.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/importing/importer.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/exporting/exporter.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "tests/hosted/test_corpus_parity.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "tests/hosted/test_round_trip.py",
            "line_range": [
              1,
              1
            ]
          }
        ],
        "dependencies": [
          "R2A"
        ],
        "evidence_references": [
          "mse_2w2dyj7bzk18j1dd:d1"
        ],
        "verification": [
          "python -m pytest tests/hosted/test_importer.py tests/hosted/test_exporter.py tests/hosted/test_corpus_parity.py tests/hosted/test_round_trip.py -q"
        ],
        "replan_conditions": [
          "a source field, actor, ownership rule, or transition cannot be represented without semantic loss",
          "the task needs a later workstream's files or changes the approved authority boundary"
        ]
      },
      {
        "id": "R3A",
        "acceptance_observables": [
          "Enforce authority epochs on every mutation and implement project locks, advisory locks, transitions, and immutable receipts. The named verification passes and the task stays inside its workstream authority boundary."
        ],
        "edit_ownership": [
          {
            "path": "hosted/migrations/003_authority_transfer.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/db/authority.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/db/transitions.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/sql/authority_locks.sql",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "tests/hosted/test_epoch_guards.py",
            "line_range": [
              1,
              1
            ]
          }
        ],
        "dependencies": [
          "R2B"
        ],
        "evidence_references": [
          "mse_2w2dyj7bzk18j1dd:d1"
        ],
        "verification": [
          "python -m pytest tests/hosted/test_epoch_guards.py tests/hosted/test_authority_transitions.py -q"
        ],
        "replan_conditions": [
          "a source field, actor, ownership rule, or transition cannot be represented without semantic loss",
          "the task needs a later workstream's files or changes the approved authority boundary"
        ]
      },
      {
        "id": "R3B",
        "acceptance_observables": [
          "Implement final delta, cutover failure recovery, reverse transfer, and restore; prove the concurrency races. The named verification passes and the task stays inside its workstream authority boundary."
        ],
        "edit_ownership": [
          {
            "path": "hosted/authority/cutover.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/authority/reverse.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/authority/restore.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "tests/hosted/test_authority_concurrency.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "tests/hosted/test_restore.py",
            "line_range": [
              1,
              1
            ]
          }
        ],
        "dependencies": [
          "R3A"
        ],
        "evidence_references": [
          "mse_2w2dyj7bzk18j1dd:d1"
        ],
        "verification": [
          "python -m pytest tests/hosted/test_cutover.py tests/hosted/test_authority_concurrency.py tests/hosted/test_restore.py -q"
        ],
        "replan_conditions": [
          "a source field, actor, ownership rule, or transition cannot be represented without semantic loss",
          "the task needs a later workstream's files or changes the approved authority boundary"
        ]
      },
      {
        "id": "R4A",
        "acceptance_observables": [
          "Land versioned idempotent event ingestion plus owner-only evidence, spans, gaps, diagnostics, retention, and purge. The named verification passes and the task stays inside its workstream authority boundary."
        ],
        "edit_ownership": [
          {
            "path": "hosted/migrations/004_capture_evidence.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/events/ingest.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/evidence/store.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/evidence/retention.py",
            "line_range": [
              1,
              1
            ]
          }
        ],
        "dependencies": [
          "R3B"
        ],
        "evidence_references": [
          "mse_2w2dyj7bzk18j1dd:d1"
        ],
        "verification": [
          "python -m pytest tests/hosted/test_event_ingest.py tests/hosted/test_evidence_privacy.py tests/hosted/test_retention.py -q"
        ],
        "replan_conditions": [
          "a source field, actor, ownership rule, or transition cannot be represented without semantic loss",
          "the task needs a later workstream's files or changes the approved authority boundary"
        ]
      },
      {
        "id": "R4B",
        "acceptance_observables": [
          "Prove digest-bound replay, sequence-gap handling, privacy isolation, tombstones, and purge availability. The named verification passes and the task stays inside its workstream authority boundary."
        ],
        "edit_ownership": [
          {
            "path": "tests/hosted/test_event_replay.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "tests/hosted/test_evidence_privacy.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "tests/hosted/test_retention.py",
            "line_range": [
              1,
              1
            ]
          }
        ],
        "dependencies": [
          "R4A"
        ],
        "evidence_references": [
          "mse_2w2dyj7bzk18j1dd:d1"
        ],
        "verification": [
          "python -m pytest tests/hosted/test_event_replay.py tests/hosted/test_evidence_privacy.py tests/hosted/test_retention.py -q"
        ],
        "replan_conditions": [
          "a source field, actor, ownership rule, or transition cannot be represented without semantic loss",
          "the task needs a later workstream's files or changes the approved authority boundary"
        ]
      },
      {
        "id": "R5A",
        "acceptance_observables": [
          "Land submissions, approvals, curator ledger, transparent retrieval projections, and the authenticated MCP useful loop. The named verification passes and the task stays inside its workstream authority boundary."
        ],
        "edit_ownership": [
          {
            "path": "hosted/migrations/005_guarded_retrieval.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/workflows/approvals.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/curator/ledger.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/retrieval/search.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "hosted/mcp/tools.py",
            "line_range": [
              1,
              1
            ]
          }
        ],
        "dependencies": [
          "R4B"
        ],
        "evidence_references": [
          "mse_2w2dyj7bzk18j1dd:d1"
        ],
        "verification": [
          "python -m pytest tests/hosted/test_guarded_writes.py tests/hosted/test_curator_ledger.py tests/hosted/test_retrieval.py tests/hosted/test_mcp_loop.py -q"
        ],
        "replan_conditions": [
          "a source field, actor, ownership rule, or transition cannot be represented without semantic loss",
          "the task needs a later workstream's files or changes the approved authority boundary"
        ]
      },
      {
        "id": "R5B",
        "acceptance_observables": [
          "Prove the P0.4 useful loop and tenant, privacy, delegation, idempotency, stale-epoch, and vector-recall negatives. The named verification passes and the task stays inside its workstream authority boundary."
        ],
        "edit_ownership": [
          {
            "path": "tests/hosted/test_useful_loop_e2e.py",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "tests/hosted/test_vector_recall.py",
            "line_range": [
              1,
              1
            ]
          }
        ],
        "dependencies": [
          "R5A"
        ],
        "evidence_references": [
          "mse_2w2dyj7bzk18j1dd:d1"
        ],
        "verification": [
          "python -m pytest tests/hosted/test_useful_loop_e2e.py tests/hosted/test_vector_recall.py -q"
        ],
        "replan_conditions": [
          "a source field, actor, ownership rule, or transition cannot be represented without semantic loss",
          "the task needs a later workstream's files or changes the approved authority boundary"
        ]
      }
    ],
    "test_strategy": {
      "tests": [
        "tests/hosted/test_migrations.py",
        "tests/hosted/test_rls.py",
        "tests/hosted/test_corpus_parity.py",
        "tests/hosted/test_authority_concurrency.py",
        "tests/hosted/test_event_replay.py",
        "tests/hosted/test_evidence_privacy.py",
        "tests/hosted/test_vector_recall.py",
        "tests/hosted/test_useful_loop_e2e.py"
      ],
      "alternative_checks": [
        "PostgreSQL catalog lint and schema dump review",
        "exact-versus-approximate retrieval recall report",
        "tested backup restore receipt"
      ],
      "exceptions": [],
      "tests_before_behavior_change": true,
      "behavior_changes": true
    }
  }
}
```
