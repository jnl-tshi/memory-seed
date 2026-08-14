# Fresh-Claude decision replay v1: observable rationale exposure

This corrected three-arm pilot follows the first two-arm instrument run. It distinguishes whether
historical rationale is absent, merely available through normal Memory Seed routing, or explicitly
pushed into the subject's context.

The historical source, task defect, and frozen behavioral grader are unchanged. The v1 harness adds an
opaque context receipt, transcript-level manipulation checks, randomized execution order, and separate
implementation/validation timing. Read [PREREGISTRATION.md](PREREGISTRATION.md) before running it.

## Conditions

The labels `A`, `B`, and `C` are randomly assigned and sealed:

1. `no-dated-memory`: dated session documents removed; no supplemental rationale;
2. `historical-available`: complete pre-fix dated sessions available through normal routing;
3. `relevant-rationale-pushed`: dated sessions removed; the bounded pre-fix entry that flags the
   quality-report path-join defect is supplied explicitly.

The no-memory and pushed arms share the same empty dated-session state, so their contrast isolates the
task-relevant rationale packet. The available arm tests the product-level retrieval path.

## Verify and prepare

From the live repository:

```powershell
python experiments/decision-replay/claude-quality-report-v1/verify_harness.py
python experiments/decision-replay/claude-quality-report-v1/prepare.py --seed 20260814
```

Preparation prints a public manifest, a sealed receipt, three fixture paths, and randomized execution
order. By default they live under the operating-system temporary directory so OneDrive cannot lock an
ignored artifact directory. Do not open the sealed receipt before all subjects have stopped and all raw
transcripts exist.

If any Claude process exits non-zero, the runner stops before launching the next label and marks the
run invalid. Do not resume it; prepare a new run ID so a provider or harness failure cannot create an
asymmetric order effect.

## Run the fresh subjects

The runner launches one new headless Claude session per fixture in the blinded randomized order and
stores JSONL transcripts, timing/checksum metadata, and blinded grade/audit JSON for each arm. It pins
each fixture's MCP server to that fixture's historical code, excludes user-level MCP servers/settings,
and preserves both the CLI event stream and Claude's canonical timestamped session transcript:

```powershell
python experiments/decision-replay/claude-quality-report-v1/run.py `
  --manifest <public-manifest-path> `
  --model opus --effort high
```

For manual interactive execution, start one genuinely fresh session in each fixture and give each the
same prompt:

```text
Read EXPERIMENT_CONTEXT.md first, then read TASK.md and implement it. Stay inside this repository and obey its experimental constraints.
```

Save each transcript as `<label>-transcript.jsonl`, create corresponding runner metadata, and run the
blinded grade/audit commands below before using the combined summarizer. Do not let subjects inspect
another fixture, this harness, or the sealed receipt.

## Grade and audit before reveal

The correctness gate remains the v0 grader's frozen schema v2:

```powershell
python experiments/decision-replay/claude-quality-report-v0/grade.py --json C:\path\to\fixture-A
python experiments/decision-replay/claude-quality-report-v1/audit.py `
  --fixture C:\path\to\fixture-A `
  --transcript <artifacts-path>/A-transcript.jsonl `
  --json
```

Repeat for all labels and preserve those outputs as `<label>-grade.json` and `<label>-audit.json` in the
artifact directory; the automatic runner already does this. The audit reports whether Claude requested
the context file, received its opaque receipt, repeated that receipt in the final answer, encountered
the relevant entry ID in model-facing context, and claimed to rely on it. It also reports elapsed time,
time to the last structured `Edit`/`Write` tool call, the post-edit tail, messages, tools, output tokens,
and validation-command breadth. The edit split is unavailable when a subject edits through a shell.

After all three blinded grade/audit outputs exist, reveal and combine them:

```powershell
python experiments/decision-replay/claude-quality-report-v1/summarize.py `
  --receipt <sealed-receipt-path> `
  --artifacts <artifacts-path> `
  --output <artifacts-path>/result.json
```

This is still a corrected pilot with one subject per condition. A repeatable scored study requires
multiple fresh subjects per arm; no single timing difference is a general Memory Seed effect.

## Prior instrument record

The original pair and its adjudication remain unchanged under
[`../claude-quality-report-v0/RESULT-20260813T204539Z.md`](../claude-quality-report-v0/RESULT-20260813T204539Z.md).
