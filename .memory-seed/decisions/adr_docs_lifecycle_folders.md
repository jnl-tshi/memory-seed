---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_docs_lifecycle_folders
title: "Docs taxonomy: folder is lifecycle state"
topics:
  - documentation
  - docs-lifecycle
  - governance-profile
created_at: 2026-08-06T17:15:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Docs taxonomy: folder is lifecycle state

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L105`

### Decision

Document lifecycle state is encoded in folder structure. Incoming material enters `docs/1_Inbox/`, active roadmap items sit in `docs/2_Todo/`, live normative specs occupy `docs/3_Spec/` (with candidates in `draft/`), source research lives in `docs/4_Reference/`, and terminal outcomes occupy `docs/5_Completed/`, `6_Rejected/`, `7_Replaced/`, or `8_Deferred/`.

### Why

Folder structure makes lifecycle state transparent and queryable. The legacy archive `docs/2_Todo/completed/` was retired 2026-07-17, moving its 43 documents and nested structures to `docs/5_Completed/`, ensuring every terminal document sits in a designated lane.

### How it evolved

Control-plane decision recorded and codified in the runtime index. Session decision mse_m0xs623m4cs0kjag:d1 (2026-07-15) captured the seeded docs lifecycle as an unapproved proposal, noting that richer lifecycle behavior requires local proof and non-destructive adoption semantics before becoming reusable seed behavior.

### Constitution

- `constitution:v1#folder-lifecycle` (governing)
- `constitution:v1#metadata-curation` (supporting)

### Awaiting review

- `mse_yfsrahvq87hxkcv9:d1` - Document lifecycle state is encoded in folder structure.

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:15:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#folder-lifecycle",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#metadata-curation",
      "role": "supporting"
    }
  ],
  "event_id": "adre_2690f005ace6a68ec9c3",
  "founding_quote": "Docs taxonomy: `docs/1_Inbox/` holds unassessed incoming material; `docs/2_Todo/` holds active roadmap proposals; `docs/3_Spec/` holds live normative specs (with candidates in `draft/`); `docs/4_Reference/` holds source research; and terminal outcomes live in `docs/5_Completed/`, `6_Rejected/`, `7_Replaced/`, or `8_Deferred/`.",
  "founding_source": ".memory-seed/index.md#L105",
  "source": "derived"
}
```

#### Decision

Document lifecycle state is encoded in folder structure. Incoming material enters `docs/1_Inbox/`, active roadmap items sit in `docs/2_Todo/`, live normative specs occupy `docs/3_Spec/` (with candidates in `draft/`), source research lives in `docs/4_Reference/`, and terminal outcomes occupy `docs/5_Completed/`, `6_Rejected/`, `7_Replaced/`, or `8_Deferred/`.

#### Why

Folder structure makes lifecycle state transparent and queryable. The legacy archive `docs/2_Todo/completed/` was retired 2026-07-17, moving its 43 documents and nested structures to `docs/5_Completed/`, ensuring every terminal document sits in a designated lane.

#### Evolution

Control-plane decision recorded and codified in the runtime index. Session decision mse_m0xs623m4cs0kjag:d1 (2026-07-15) captured the seeded docs lifecycle as an unapproved proposal, noting that richer lifecycle behavior requires local proof and non-destructive adoption semantics before becoming reusable seed behavior.

### revision-accepted - 2026-08-06T21:07:00Z

```json
{
  "event_id": "adre_ef242579bdc912ba0e49",
  "founding_source": ".memory-seed/index.md#L105",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

### revision-proposed - 2026-08-08T19:03:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#folder-lifecycle",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#metadata-curation",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_yfsrahvq87hxkcv9:d1",
  "event_id": "adre_b5ac49d089953ea95bc5",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Document lifecycle state is encoded in folder structure. Incoming material enters `docs/1_Inbox/`, active roadmap items sit in `docs/2_Todo/`, live normative specs occupy `docs/3_Spec/` (with candidates in `draft/`), source research lives in `docs/4_Reference/`, and terminal outcomes occupy `docs/5_Completed/`, `6_Rejected/`, `7_Replaced/`, or `8_Deferred/`.

#### Why

Rests on the session decision that instituted it: "The FOLDER is now the single visible source of truth for a doc's lifecycle state" (mse_yfsrahvq87hxkcv9:d1). This decision made the folder itself the authoritative source for lifecycle state rather than using YAML fields.

#### Evolution

Founded from .memory-seed/index.md#L105; this revision moves the concern off that control-file line onto mse_yfsrahvq87hxkcv9:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.
