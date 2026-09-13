# M0 smoke findings: Qwen3.5 9B

Date: 2026-09-01
Status: plumbing gate passed; calibration conclusions prohibited

## Environment

- Subject: Qwen3.5 9B, Q4_K_M, served by LM Studio as `qwen3.5-9b-calibration`.
- Runner: Hermes 0.20.5 one-shot mode.
- Configured context: 65,536 tokens. Hermes refused the initial 16K probe because its local one-shot
  minimum is 64K.
- Corpus: one deterministic Task Packet pilot fixture and one development task.
- Cloud credentials: common provider keys removed; no paid or external model was called.

## Final harness runs

| Arm | Mechanical result | Evidence behavior | Provider usage | Wall time |
|---|---|---|---|---:|
| `no_memory` | 4/4 correct abstentions under the no-evidence scoring rule | 0 tools | 1,256 input; 304 output; 126 reasoning; 1 call | 29.1s |
| `memory_tools` | 1/4 strict proposition score | 2 audited calls: search, then exact chunk fetch | 20,269 input; 1,049 output; 834 reasoning; 4 calls | 83.2s |
| `compiled_packet` | 2/4 strict score; 3/4 verdicts correct | 0 supplemental calls; no repeated materialized fetch | 7,819 input; 957 output; 742 reasoning; 1 call | 75.9s |

The strict compiled-packet score is lower than its verdict accuracy because the model cited one packet
field name as though it were a semantic evidence ID. It also abstained on the compiler/dispatch boundary.
The tools-only subject stopped after one search and one chunk fetch, leaving three propositions
insufficient. These are useful protocol/model observations, not stable quality estimates; the
preregistration requires repetitions and representative tasks before comparison.

## Accounting observation

The compiler ledger for this packet reported 4,822 total input tokens and a 7,322-token context envelope,
including its caller-supplied tool/schema estimate and reserves. Hermes reported 7,819 actual input tokens
for the compiled run. The difference is expected evidence that compiler accounting and provider usage are
different ledgers: Hermes system text and the four concrete runtime schemas are visible to the provider but
are not fully known to the packet compiler. No hidden-overhead breakdown is inferred.

The tools-only arm consumed 20,269 input tokens despite materializing only 3,693 result characters across
two retrieval calls. Multi-turn retrieval repeatedly resends conversation and schemas, which is exactly the
input overhead a high-signal packet is intended to avoid. One smoke task cannot establish the size of that
effect.

## Integration findings

1. The Windows sandbox denies the Proactor loop's overlapped named pipes. The bridge now selects the MCP
   SDK's Selector/Popen fallback; a direct transport probe resolves all four intended tools.
2. Hermes 0.20.5's untrusted gate looks for `readOnlyHint` on the live annotation object, while MCP SDK v2
   exposes `read_only_hint`. The facade remains structurally read-only and is therefore configured `full`
   trust for this isolated experiment.
3. Hermes progressive tool search added unnecessary meta-tool turns for a four-tool surface. It is disabled
   here so the model receives the four concrete schemas and the audit boundary stays legible.
4. Run records now include the configured servers, requested toolsets, resolved tool names, and Windows
   transport mode. Missing tools are detected mechanically rather than inferred from the answer.

## M0 gate disposition

All seven plumbing checks pass: one frozen task produces three prompts; the packet reconstructs with a
fingerprint; arm isolation is explicit; concrete tools are independently proven; actual calls are audited;
Hermes usage is recorded; answers are mechanically scoreable; and every final input is far below the
configured context window. This does not calibrate Retrieval Profiles, model tiers, budgets, or product
claims.

Next: freeze the broader development population and sealed holdout design before running more models.
