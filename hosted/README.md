# Hosted feasibility experiments

`hosted/` is deliberately outside the OSS `memory_seed` package. It may reuse semantic contracts, but it has
no import back-edge into the local runtime and is not included in wheels, sdists, or console scripts.

## P0.2 decision capture

The `capture/` package is an experimental, fail-closed adapter for validated Codex desktop JSONL rollouts.
It preserves source coordinates and accessible payloads in a disposable SQLite queue, handles completed-line
checkpoints, replay, rotation, leases, and pause/resume gaps, and emits inert decision drafts only.

`curator/advisory.py` is an offline, provider-neutral contract for secondary review of an *already accepted*
write-agent decision. It compares the claim with a caller-provided, permission-filtered set of existing
decisions and current topics first. A specific unanswered source question is required before it opens the
dialogue-only, twenty-turn window. Advice can cite exact accepted-claim, existing-record, or disclosed-source
quotes, and always requires review. It neither accepts a hosted write nor authenticates a member, retrieves
candidate records, queues a job, shares raw evidence, or applies suggestions. The separate hosted SQL service
remains unbuilt.

Run targeted tests:

```powershell
python -m pytest tests/test_mcp_decision_mark.py tests/test_hosted_decision_capture.py tests/test_p02_incremental.py tests/test_p02_corpus.py tests/test_decision_marking_control_plane.py experiments/decision-chat-alignment/test_align_decisions.py
```

Run the owner-local historical diagnostic without printing raw evidence (this does not establish prospective recall or semantic equivalence):

```powershell
python -m hosted.evaluation.run_p02 --codex-home "$env:USERPROFILE\.codex" --output hosted/evaluation/revision-diagnostics
```

The live adapter accepts only the explicitly listed CLI versions in `capture/codex_rollout.py`. Unknown versions,
events before validated session metadata, and malformed shapes produce diagnostics or fail closed. It never attempts
to expose encrypted or hidden reasoning.

The optional spaCy dependency is isolated under `experiments/spacy/`. Without it, the parser reports the
deterministic rules-only backend. Neither backend can promote a draft; a curator must verify evidence, actor,
and atomicity.

The revised parser caches per-message components during one stepped replay. It does not yet maintain
that state across live polling calls. A draft closes only with source-grounded issue, action, scope,
and user acceptance; unresolved references remain incomplete. Explicit lifecycle boundary flags stop
expansion but are not yet inferred from tool events. Generic reference resolution and evolving/replacing
decision generation remain open work. See the [current plan](../docs/2_Todo/codex-capture-feasibility-plan.md).

The original `evaluation/results` directory is frozen. Revised reports distinguish oracle-anchor
turn-envelope coverage from genuine detection recall, and leave unmeasured recall/semantic gates null.
No lexical similarity threshold can certify equivalent meaning. The authenticated trial remains unstarted.
The [semantic review rubric](evaluation/SEMANTIC-REVIEW.md) defines the required field-by-field comparison.
