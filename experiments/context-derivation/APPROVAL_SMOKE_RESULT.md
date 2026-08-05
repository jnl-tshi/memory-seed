# Unscored Codex Approval Smoke Result

Date: 2026-08-05
Run ID: `codex-CTX-01-approval-smoke-r1-bb895fe3a1`
Scope: `CTX-01` / `approval-smoke` / repetition `1`
Pin: `gpt-5.6-luna`, `codex-cli 0.146.0`, reasoning effort `low`
Scored: no

## Outcome

The single authorized approval-mode smoke passed on its first and only provider
call. Codex called `memory_adrs_list` exactly once with an empty arguments object,
the broker delivered a successful response, and Codex returned exactly
`{"smoke":"approval-mode"}`. No retry was attempted or permitted; the separate
machine-local one-shot claim is consumed.

This confirms that the scoped
`mcp_servers.context_fixture.default_tools_approval_mode="approve"` override
fixes the prior automatic cancellation while leaving the broker's exact
read-only allowlist in control.

## Safety observations

- Parent `.memory-seed` store unchanged: yes.
- Immutable fixture unchanged: yes.
- Authenticated broker teardown verified: yes.
- Exact broker record: one successful `memory_adrs_list({})` call.
- Undeclared tool calls observed: none.
- Direct filesystem retrieval observed: no.
- Repository scored `runs/` created: no.
- Broker bearer token or raw MCP arguments retained in artifacts: no.
- Harness integrity failures: none.

The run used 33,618 input tokens, of which 23,808 were cached, and 427 output
tokens, including 296 reasoning-output tokens. This is 52% fewer input tokens
than the failed medium-effort broker smoke, while remaining an unscored protocol
check rather than an accuracy result.

## Offline gates

Before the live call, 86 context-derivation tests plus 6 subtests passed. The
approval smoke additionally rejects missing, extra, failed, non-empty-argument,
and oversized-response tool calls; rejects any final answer other than the exact
expected JSON object; strips raw MCP arguments from approval-smoke artifacts;
and remains structurally excluded from collection and scoring. Independent
protocol and security reviews were clean after the fixes.

The 288 scored subject runs and 96 blind judge calls remain blocked pending a
separate user decision.

## Retained artifact fingerprints

The redacted artifacts remain outside the repository in OS-temporary storage.
Their SHA-256 fingerprints are:

- `RUN_MANIFEST.json`: `92c15f3441f8f23c3fa68ade7ef313f5d0a6ae8193c65b9bc1cd3155458f2397`
- `transcript.jsonl`: `a4d935efebe591ed8bd0df9e3e4b8097ed97c375c2481f8da688dc7b2bb8ac90`
- `final_answer.txt`: `b2519cb49f6c86b81267996698e34c6509d3a4784f95770ec275173236d62bfd`
