# Unscored Codex Broker Smoke Result

Date: 2026-08-04
Run ID: `codex-CTX-01-adr-mcp-workflow-r1-729a3496d3`
Scope: `CTX-01` / `adr-mcp-workflow` / repetition `1`
Pin: `gpt-5.6-luna`, `codex-cli 0.146.0`, reasoning effort `medium`
Scored: no

## Outcome

The one authorized smoke finished with `smoke_integrity_failure`. Codex exposed
the expected `context_fixture` tools and attempted `memory_search`,
`memory_adrs_check`, and `memory_adrs_list`, but the client cancelled each call
before it reached the broker. The broker therefore recorded zero tool calls.
Codex then invoked its built-in `list_mcp_resources`, which was outside the
experiment allowlist and correctly caused the fail-closed integrity result.

The cause was a missing Codex MCP approval override. The server had an exact
`enabled_tools` allowlist, but `approval_policy="never"` auto-rejected tool calls
whose MCP approval mode still required interaction. The provider was not retried.
The one-shot machine-local claim remains consumed.

## Safety observations

- Parent `.memory-seed` store unchanged: yes.
- Immutable fixture unchanged: yes.
- Authenticated broker teardown verified: yes.
- Direct filesystem retrieval observed: no.
- Repository scored `runs/` created: no.
- Broker bearer token retained in artifacts: no.

The run used 70,661 input tokens (55,040 cached) and 755 output tokens. It did
not retrieve ADR evidence, so it is excluded from all accuracy and context-size
comparisons.

## Offline remediation

The broker configuration now sets
`mcp_servers.context_fixture.default_tools_approval_mode="approve"`. This
pre-approves only the exact read-only tools already named by `enabled_tools`;
the broker independently enforces the same allowlist and forced fixture working
directory. Provider-free strict-config, broker, harness, collection, scoring,
security, and protocol checks pass after the change. Scored execution remains
blocked and this smoke was not repeated.

## Retained artifact fingerprints

The raw redacted artifacts remain outside the repository in OS-temporary
storage. Their SHA-256 fingerprints are:

- `RUN_MANIFEST.json`: `8b15ba633b92735d24950fb4527e08a320de906cc239a9aa7b7dbae440ce8bdc`
- `transcript.jsonl`: `a02669c60c0e21761a357e7241dcb6aed7546680912496475f77bd4009c42211`
- `final_answer.txt`: `c6af9ba3c3f300017a8e816576f194a5214c7cc16238c62da355f318f7c71ede`
