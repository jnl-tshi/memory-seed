# Task Packet calibration harness

This experiment measures the same project-specific question under three context conditions:

1. `no_memory` — task only; no Memory Seed evidence or tools;
2. `memory_tools` — task plus a four-tool, read-only Memory Seed surface, without a prepared packet;
3. `compiled_packet` — task plus the deterministic compiled Task Packet and the same tools for bounded fallback.

The first milestone is deliberately small. It proves bundle reconstruction, strict arm isolation, independent
tool-call logging, Hermes-to-LM-Studio execution, provider-reported usage capture, and mechanical scoring on
one development fixture. It does not calibrate the six Retrieval Profiles or establish production thresholds.

## Local smoke flow

No model call is made by `prepare.py`.

```powershell
python experiments/task-packet-calibration/prepare.py `
  --tasks experiments/task-packet-calibration/tasks/development.json `
  --task-id TPC-DEV-001 `
  --output $env:TEMP\memory-seed-tpc-bundle

lms load qwen/qwen3.5-9b --context-length 65536 `
  --identifier qwen3.5-9b-calibration --yes

python experiments/task-packet-calibration/run.py `
  --bundle $env:TEMP\memory-seed-tpc-bundle `
  --arm compiled_packet `
  --model qwen3.5-9b-calibration `
  --output $env:TEMP\memory-seed-tpc-run.json

python experiments/task-packet-calibration/score.py `
  --run $env:TEMP\memory-seed-tpc-run.json `
  --tasks experiments/task-packet-calibration/tasks/development.json `
  --gold experiments/task-packet-calibration/tasks/development.gold.json `
  --packet $env:TEMP\memory-seed-tpc-bundle\task-packet.json `
  --output $env:TEMP\memory-seed-tpc-score.json
```

Each run uses a throwaway `HERMES_HOME`, disables built-in toolsets, strips common cloud-provider
credentials from the child environment, and pins MCP reads to the fixture corpus. The MCP facade exposes
only `memory_search`, `memory_get_chunk`, `memory_adrs_list`, and `memory_adr_show`. It records calls from
the actual tool boundary rather than trusting the subject's self-report.

Hermes 0.20.5 refuses local one-shot models loaded below 65,536 tokens, so the smoke uses that configured
window even though the packet is much smaller. On this Windows host, the sandbox blocks the Proactor event
loop's overlapped subprocess pipes; the bridge selects the MCP SDK's supported Selector/Popen fallback.
The experiment server is marked `trust: full` because the facade itself is the enforced boundary: it
publishes only four read-only schemas, pins every `cwd`, and rejects every other tool. Hermes 0.20.5's live
trust classifier does not recognize MCP SDK v2's snake-case `read_only_hint` attribute.

To verify the protocol surface without making a model call:

```powershell
& "$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\python.exe" `
  experiments/task-packet-calibration/probe_mcp_transport.py `
  --command "$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\python.exe" `
  experiments/task-packet-calibration/mcp_wrapper.py `
  --fixture $env:TEMP\memory-seed-tpc-bundle\runtime `
  --audit-log $env:TEMP\memory-seed-tpc-probe.jsonl
```

`hermes_bridge.py` reads prompts from files because a compiled packet can exceed the Windows process
argument limit. Hermes remains the model/tool-loop runner; LM Studio remains the local inference server.

The completed M0 measurements and limitations are in [`M0_SMOKE_FINDINGS.md`](M0_SMOKE_FINDINGS.md).

## Approval boundary

`PREREGISTRATION.md` is currently draft. Development smoke runs are allowed and cannot establish a
calibration result. Do not run or score the sealed holdout until the preregistration, task population,
model pins, repetition count, and stopping rules are frozen and explicitly approved.
