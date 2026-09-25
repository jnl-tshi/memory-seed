# Merge-maintained Graphify project index

This is an optional, derived index. Markdown and Git remain authoritative. It
uses stock Graphify's local structural parser, not an LLM, and makes no hosted
API call. It does **not** infer Memory Seed decision relations such as
`supersedes` or `evolves` from prose.

## Pilot

The disposable `pilot.py` probe used Graphify 0.9.29 to build two linked
Markdown files, edit a heading while retaining a link to an unchanged file,
rename the linked file, and delete the source. All assertions passed. A full
build of the original docs-plus-Memory-Seed corpus took approximately 21
seconds in the isolated worktree and produced 6,137 nodes, 6,369 edges, and
372 source documents. Its relations were `contains` and `references`; no
semantic pass ran. These are one-machine observations of the prior scope, not
performance guarantees for the wider project scope below.

## Scope and refresh

`.graphifyignore` selects visible project Markdown and supported source code
throughout the tree, including active `docs/`, `experiments/`, `business/`,
demo, and package/test folders. Every dot-prefixed path component is excluded,
including `.memory-seed/`; session logs and decisions are retrieved through
Memory Seed, not duplicated in this project graph. Generated graph output,
dependency/build directories, binary assets, and bulky data formats such as
JSON, JSONL, and CSV are excluded. The deterministic adapter applies the same
visible-path and format boundary. Memory Seed ships a passive scope template
for new projects and preserves a project's existing `.graphifyignore` on init
and update. `graphify_merge_refresh: true` in `.memory-seed/project.yaml` is
still the separate opt-in switch; other projects do not build automatically.

After `memory-seed session merge-branch` successfully commits a local merge,
the adapter compares `HEAD` with the last successfully indexed commit. It
uses `git diff --no-renames` so a rename supplies both a deleted and an added
path. It passes selected changed files to Graphify's structural updater,
leaving unchanged graph contributions in place. If the baseline is absent,
corrupt, not an ancestor of `HEAD`, or the scope file changes, it rebuilds the
selected corpus. If
only unrelated files changed, it advances the freshness marker without
running Graphify. The generated index and marker live in ignored
`graphify-out/` and are local to each checkout.

The adapter builds in a temporary output directory and publishes the graph
only after validating the result. If Graphify is missing, times out, fails, or
produces out-of-scope/empty output, the merge **stays committed**, the last
usable graph is retained where possible, and CLI/MCP integration returns a
warning. The marker does not advance on failure.

Check freshness before relying on the graph:

```text
python -m memory_seed.graphify_refresh status
python -m memory_seed.graphify_refresh refresh
python -m memory_seed.graphify_refresh query "What links these documents?"
```

The query wrapper refuses stale results, including when selected project files or
the scope file have uncommitted changes. Direct `graphify query` bypasses this
guard, so callers that need a freshness guarantee must use the wrapper or
check `status` first. The explicit `refresh` command is for recovery after a
failed update; it refuses uncommitted selected changes. The adapter is attached
to Memory Seed's local merge operation, not arbitrary `git merge` or remote PR
merges.

## Fork approval gate

This implementation has **not** created, modified, installed, or published a
Graphify fork. It calls the installed upstream `graphify.watch._rebuild_code`
from Graphify's own Python environment. That interface is private and may
change; failure is deliberately warning-only. If a reproducible upstream
defect or interface change cannot be handled safely by this narrow adapter,
record the case and the smallest proposed fork patch, then stop for explicit
user approval before any fork work.
