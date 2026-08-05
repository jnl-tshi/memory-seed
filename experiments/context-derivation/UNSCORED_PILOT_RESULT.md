# Unscored Pilot Result

This one-shot pilot did not pass its gate. It produced no scored recommendation, and the full live trial was not launched.

- Output: `os-temp://memory-seed-context-pilot-7249d318eca748c4aecc261fe70375f3`
- Launches: 8 of 8 canonical cells, with zero retries
- Complete task correctness: 2 of 8 cells
- Claude: 2 of 4 correct. Both fixed-packet cells were correct (`retrieval-v1-packet` and `adr-candidate-packet`). Its two interactive MCP cells were harness-invalid because the command disabled all tools; both made zero tool calls.
- Codex: 0 of 4 correct. Subject noncompliance is unresolved; this result does not establish a cause.
- Protocol observation: all eight cells produced schema-valid final answers, but every recorded tool sequence was empty.
- Containment: no breach. Parent-store, fixture, experiment, and gold snapshots remained unchanged; all provider processes exited successfully and none timed out.
- Claim checker: `per_cell_claims_complete: false` was a false negative. All eight marker files existed, but Windows text-mode writing produced `consumed\r\n` while the exact checker required `consumed\n`.
- Usage: 60,970 input tokens total (median 3,714.5); 2,684 output tokens total (median 407.5); 57,969 ms summed subject latency (median 6,226.5 ms).
- Claude usage: 8 input tokens, 1,826 output tokens, 27,484 ms summed latency, 6,773.5 ms median latency.
- Codex usage: 60,962 input tokens, 858 output tokens, 30,485 ms summed latency, 5,594.5 ms median latency.
- Cost: unavailable. Every cell reported `cost_usd: null`; zero must not be inferred.
- One-shot status: consumed. This pilot cannot be replayed under the same claim.

The evidence supports correcting the portable claim bytes, Claude MCP tool exposure, zero-call interactive classification, and null cost aggregation before any further live execution. It does not support a production recommendation or a full launch.
