# Proposal: Task Packet Budget Accounting And Skill Layering

## Status

Implemented for Memory Seed 2.25.0 on 2026-11-09 after JNL approved the proposal and the implementation
defaults. Task Dispatch/Packet v3 now provides the budgeted skill/persona manifest while v1 and v2 remain
compatible.

The accepted implementation decisions were: use a new v3 schema; share one skill/persona reserve with
separate ledger measurements; permit only compile-time-declared, digest-pinned late loads; record
deterministic debit estimates in existing packet telemetry; and keep governance independently loadable at
zero debit. The original proposal and rejected alternatives remain below as the design record.

## Recommendation

Keep one context envelope and make its costs visible in four non-overlapping layers:

1. **Packet core**: the serialized packet, fixed host instructions, and tool schemas already measured
   by the input ledger.
2. **Worker governance**: embedded orientation-lite plus digest-pinned full governance that remains
   loadable on demand outside the supplemental reserve.
3. **Selected skills**: at most one persona and the objective-triggered skills resolved from the
   existing merged registry, pinned by digest and budgeted before dispatch.
4. **Supplemental evidence**: unplanned but authorized gap reads, debited at runtime from the existing
   supplemental-input reserve.

The packet compiler should estimate and reserve layers 1-3 before dispatch, then report observed
runtime debits for layers 2-4 without pretending those estimates are provider token usage. A skill is
loaded only when its registry trigger matches the bounded objective or a later explicit trigger fires.
Task Dispatch v2 read scope authorizes files; it does not order every authorized file into the initial
context.

## Evidence And Authority

### Verified current state

- Task Packet already measures `serialized_packet_input_tokens`, fixed instructions, tool schemas,
  supplemental input reserve, output/reasoning reserve, and governance subsets. The total context
  envelope is checked against target, soft-cap, and shard-threshold bands.
- Dispatch budget presently has one input reserve, `supplemental_input_tokens`; it has no distinct
  skill allowance and the packet has no inspectable skill-selection ledger.
- Packet v2 embeds orientation-lite, pins `agent-rules.md` and delegated `session_logging.md`, and loads
  full governance only through a digest-verified path that never spends the supplemental reserve.
  Packet v1 continues to embed full rules.
- A worker receives its Task Packet, at most one domain persona, and objective-triggered skills. It
  skips primary-session orientation and broad project loading.
- The deterministic skill registry order is universal `skills/index.md`, then project-owned
  `skills/index.local.md`; the merged nearest-runtime registry precedes inherited parent registries.
  Local entries replace, disable, or append without creating a second trigger authority.
- Task Dispatch v2 distinguishes exact working inputs, reference inputs, and `do_not_load`; Dispatch v1
  makes no read-scope guarantee.

### Discovery record

Design Discovery assessed every required authority item. It found no conflicts and required no living
ADR outcome.

| Authority | Relation | Consequence for this proposal |
|---|---|---|
| Constitution `append-only`, `minimal-context`, `path-of-least-resistance`, `prove-automation`, `single-source`, `markdown-authority`, `topic-vocabulary` | governed-by | Preserve auditable history, expose the smallest sufficient context, keep Markdown registries authoritative, and prove any future automation. |
| MSI-023 explicit Dispatch v2 read scope (`mse_7da2dwpntn4arc3r:d1`) | builds-on | Working/reference lists authorize reads; they are not an eager preload instruction. `do_not_load` remains absolute. |
| MSI-027 project skill overlay (`mse_vgz0z3tknm5mwz1k:d1`) | builds-on | Resolve skills through the existing universal/local/nearest/inherited order; add no parallel selector. |
| Digest-pinned governance load (`mse_r0k9nzhaxqp31hwx:d1`) | builds-on | Full governance remains independently loadable and cannot be starved by skill or evidence reserves. |
| Orientation-lite budget revision (`mse_t7hc53kavrs8hx0m:d1`) | builds-on | Ordinary work uses lite guidance; full rules load only on defined triggers. |
| Lazy skill extraction (`mse_7p3q9r2t5v8w1x6z:d1`) | builds-on | Keep startup rules compact and procedural detail lazy. |
| Worker context contract (`mse_9q4b7twk2p6mx1rz:d1`) | builds-on | Retain Packet + at most one persona + objective-triggered skills as the worker envelope. |
| Proactive history discipline (`mse_3114hmpcsyz9ftp1:d1`) | related | The design consulted durable rationale before proposing a change; it does not alter the schema. |
| MCP decision-envelope ADR and CLI authoring cleanup | no-edge | Neither defines context budgets or skill selection. |

Evidence Pack fingerprint:
`sha256:1bccecbf15febbcb310416f2f6cf86ec07d329408e527141442a50c0178adb1e`.

## D1 - Budget One Envelope Without Double Counting

### Accounting model

The current envelope equation remains the compatibility anchor:

```text
total_input = serialized_packet + fixed_instructions + tool_schemas + supplemental_reserve
total_context = total_input + output_reasoning_reserve
```

MSI-025 should refine the inspectable composition of those terms, not invent a second total. The
serialized packet contains the planned core, governance references, and selected-skill pins. Those
embedded records are subsets of `serialized_packet_input_tokens`, just as the current materialized
governance measurements are. Their content-load allowances are separate reserved inputs:

```text
planned_input = serialized_packet + fixed_instructions + tool_schemas
                + skill_input_reserve + supplemental_input_reserve
total_context = planned_input + output_reasoning_reserve
```

`skill_input_reserve` is only for the content of selected skills and the one selected persona.
`supplemental_input_reserve` remains only for later gap evidence. Full governance loads are measured
separately and remain non-debiting because safety rules cannot compete with task evidence.

### Proposed dispatch shape

A future schema revision may extend `budget` as follows; names are illustrative until implementation
planning fixes the version and migration:

```json
{
  "budget": {
    "skill_input_tokens": 6000,
    "supplemental_input_tokens": 4000,
    "output_tokens": 8000,
    "over_soft_cap": "fail"
  }
}
```

The compiler, not the plan author, derives skill estimates. The author supplies a ceiling. A ceiling of
zero is valid only when the resolved skill set and persona are both empty. The compiler fails before
dispatch when selected content exceeds the ceiling; it does not silently move the excess into the
supplemental reserve.

### Proposed packet ledger

The existing `input_ledger` remains canonical and gains inspectable subset/reserve records rather than
a sibling accounting system:

```json
{
  "selected_skill_manifest_tokens": 420,
  "selected_skill_content_reserve_tokens": 5400,
  "supplemental_input_reserve_tokens": 4000,
  "component_measurements": {
    "selected_skill_manifest_tokens": {
      "accounting_scope": "subset_of_serialized_packet_input_tokens"
    }
  }
}
```

Every estimate records the estimator identifier already used by the packet. Estimates describe the
compiled envelope only. They must never be labelled as billed, provider-observed, cached, or actual
usage. If runtime telemetry is added later, it records observed bytes and the same deterministic token
estimate beside event type and digest; provider usage remains a separate optional source.

### Runtime debit rules

| Load | Authorization | Debit |
|---|---|---|
| Orientation-lite embedded in packet v2 | Packet compiler | Already within serialized packet |
| Selected persona or selected skill | Pinned selection manifest | Skill reserve |
| Full `agent-rules.md` / `session_logging.md` | Existing governance trigger and digest pin | No skill or supplemental debit; report separately |
| Working/reference gap evidence | Dispatch v2 read scope plus supplemental-fetch rules | Supplemental reserve |
| A newly triggered installed skill not selected at compile time | Registry match plus unused skill reserve and digest pin | Skill reserve; otherwise stop and recompile/re-authorize |
| `do_not_load` path | Never | Refuse before any debit |

Debits are digest-addressed and idempotent within one packet activation: loading the same pinned bytes
twice does not charge twice. A changed digest is not the same item and must fail stale rather than use a
remaining reserve.

### Failure behavior

- `skill_budget_exceeded`: selected skill/persona estimates exceed the declared skill ceiling.
- `supplemental_budget_exceeded`: retain the current meaning for evidence gap reads only.
- `unselected_skill`: a runtime trigger names an installed registry skill absent from the packet manifest
  and no authorized reserve path exists.
- Existing `stale_governance`, `missing_governance_reference`, `invalid_governance_reference`, soft-cap,
  and shard-required failures keep their meaning.

Failures should name estimated required, remaining, estimator, source, and digest where available. A
budget failure cannot broaden read scope, write scope, capability tier, or `over_soft_cap` authority.

## D2 - Resolve And Load Skills In Explicit Layers

### Layer model

| Layer | Contents | Selection time | Authority |
|---|---|---|---|
| L0: host envelope | Provider/system instructions and tool schemas | Host/session creation | Host; measured inputs only |
| L1: packet core | Objective, scope, acceptance, evidence pins, orientation-lite | Compile time | Task Dispatch and packet compiler |
| L2: governance | Full rules referenced by orientation-lite triggers | Runtime on defined trigger | Digest-pinned governance files |
| L3: task skills | At most one persona plus objective-triggered skills | Compile time; bounded late trigger allowed | Merged skill registry and installed files |
| L4: evidence | Authorized working/reference gap reads | Runtime | Dispatch v2 read scope and retrieval rules |

The numbers express load order, not authority rank. A later layer cannot override an earlier scope or
safety decision. In particular, a skill cannot add writable files, remove a `do_not_load` path, change
the objective, or grant integration/release authority.

### Selection algorithm

1. Resolve the nearest runtime and merge its universal registry with its optional local overlay.
2. Evaluate that merged registry before any inherited parent registry, preserving existing replacement,
   disable, and append semantics.
3. Match triggers against the bounded objective, handoff, declared validation, and known artifact types.
   Do not scan broad project state merely to discover more skills.
4. Select at most one domain persona. Persona and orchestration role remain separate axes.
5. Canonicalize selections in registry order, resolve each installed file, and record path, source
   runtime, byte count, digest, deterministic token estimate, and trigger reason.
6. Refuse missing core skills. For unavailable optional skills, preserve the existing doctor/provisioning
   warning contract; the compiler must not invent or fetch a substitute.
7. Check the skill ceiling and total context band before emitting the packet.

The packet carries only the selection manifest and content explicitly chosen for eager delivery. The
manifest is not a second registry: it is a compiled, digest-pinned result with provenance. Changing the
registry or selected bytes after compilation makes the pin stale; it does not mutate the packet.

### Read-scope interaction

- `execution.read_inputs.working` and `.reference` are the complete task-file read authority for Dispatch
  v2, not a mandate to embed all listed files.
- Installed control-plane skills and pinned governance are loaded through their dedicated packet paths;
  they are not smuggled in as task reference files.
- Any path in `execution.do_not_load` wins over a task-file or skill-derived request. A future compiler
  should also refuse a selected project-local skill whose file itself is explicitly forbidden.
- Dispatch v1 remains compatible and makes no new read-scope promise. A future skill-budget feature
  should require an explicit newer dispatch/packet version rather than backfilling guarantees into v1.

### Late triggers

Some skills become necessary only after a refusal or artifact discovery. A late load is allowed only
when all of these are true:

1. the already-resolved registry contains the trigger;
2. the skill was installed and digest-pinned in an eligible late-load manifest at compile time;
3. the path does not conflict with `do_not_load`;
4. the remaining skill reserve covers the content; and
5. loading it does not change task authority.

Otherwise the worker stops with a structured reason and the orchestrator decides whether to compile a
new packet. Late loading may spend reserved context; it may not silently replan.

## Compatibility And Migration

- Packet/Dispatch v1 remain byte- and behavior-compatible. They gain no synthetic skill selection or
  read-scope guarantees.
- Current v2 packets remain valid under their present ledger. The feature should use a versioned optional
  extension or a new packet/dispatch version; implementation planning must choose one after fixture-based
  fingerprint analysis.
- Existing `supplemental_input_tokens` retains its evidence-gap meaning. It is never silently divided or
  reinterpreted for old packets.
- Existing governance pins and zero-debit governance load remain unchanged.
- Existing registry and `index.local.md` merge semantics remain unchanged.
- Existing CLI/MCP compile, preview, render, activation, and commit verification surfaces must agree on
  canonical selection and budget identity before migration is accepted.

## Rejected Alternatives

### Charge skills to the supplemental reserve

Rejected because planned procedure would compete with unplanned evidence, hiding both costs and
reintroducing the starvation problem already solved for governance.

### Embed every matching skill eagerly

Rejected because trigger authorization does not prove immediate need. It would make lazy skills
effectively always-on and penalize bounded tasks.

### Put skill names directly in plans as authority

Rejected because it would create a second trigger registry. Plans may record expected selections for
review, but the compiled result must come from the merged registry and installed files.

### Treat read-scope lists as preload lists

Rejected because MSI-023 distinguishes authorization from use. Eagerly loading every working and
reference file would defeat minimal-context routing.

### Infer actual model usage from deterministic estimates

Rejected because estimated text tokens are not provider billing or observed context consumption. The
ledger must keep those concepts explicitly separate.

## Approval Questions

JNL approval is required before implementation planning. The approval should settle:

1. whether the schema uses an optional v2 extension or a new Dispatch/Packet version;
2. whether late-load eligibility pins all installed matching skills or only a bounded declared subset;
3. whether the persona shares the skill reserve or receives a separately visible sub-allocation; and
4. whether runtime debit events belong in existing packet telemetry now or in a later observability task.

## Acceptance For A Future Implementation

A future implementation is acceptable only when tests-first fixtures prove all of the following:

- skill manifest and budget calculations are deterministic across CLI and MCP surfaces;
- selected-manifest bytes are counted once, while skill content and supplemental reserves remain
  distinct;
- full governance loads still succeed with zero debit to both reserves;
- selected and late-triggered skills obey registry order, overlay semantics, digest pins, and
  `do_not_load`;
- old v1 and current v2 fixtures preserve their canonical bytes and fingerprints unless an explicitly
  approved version migration says otherwise;
- soft-cap, shard, stale-pin, missing-core, skill-budget, and supplemental-budget failures are stable and
  actionable;
- live/seed twins, docs, doctor, encoding, package smoke, serial tests, and parallel tests pass; and
- telemetry calls estimates estimates and never claims provider-observed usage without provider evidence.

MSI-025/MSI-026 shipped through the v3 compiler, CLI, MCP, renderer, telemetry, hook, and live/seed skill
surfaces described above.
