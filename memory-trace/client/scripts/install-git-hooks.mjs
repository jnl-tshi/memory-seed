#!/usr/bin/env node
// Install the Mermaid pre-commit hook into this repo's git hooks directory.
//
// Git hooks live under .git/ and are not version-controlled, so the hook cannot
// just be committed - it has to be installed. This mirrors how Memory Seed
// installs its prepare-commit-msg shim: idempotent, and it refuses to clobber a
// pre-commit hook it did not write. Run it with `npm run hooks:install`.

import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync, chmodSync, mkdirSync } from "node:fs";
import { isAbsolute, join } from "node:path";

const MARKER = "# memory-trace-mermaid-precommit";
const HOOK = `#!/bin/sh
${MARKER}
# Block a commit that stages a diagram sidecar whose Mermaid will not parse -
# the class of defect links check cannot see. Installed by
# memory-trace/client/scripts/install-git-hooks.mjs. Best-effort: skips cleanly
# when node or the Trace client's deps (mermaid, jsdom) are absent, so it never
# blocks a commit in a checkout that has not set the client up.
staged=$(git diff --cached --name-only --diff-filter=ACM -- .memory-seed/sessions/diagrams)
[ -z "$staged" ] && exit 0
if ! command -v node >/dev/null 2>&1; then
  echo "pre-commit: node not found; skipping the Mermaid sidecar check."
  exit 0
fi
root=$(git rev-parse --show-toplevel)
node "$root/memory-trace/client/scripts/check-sidecar-mermaid.mjs" $staged
`;

function git(args) {
  return execFileSync("git", args, { encoding: "utf8" }).trim();
}

function hooksDir() {
  // --git-path resolves the right hooks dir even in a linked worktree or when
  // core.hooksPath is set. It may come back relative to the toplevel.
  const path = git(["rev-parse", "--git-path", "hooks"]);
  if (isAbsolute(path)) return path;
  return join(git(["rev-parse", "--show-toplevel"]), path);
}

function main() {
  const dir = hooksDir();
  mkdirSync(dir, { recursive: true });
  const hookPath = join(dir, "pre-commit");

  if (existsSync(hookPath) && !readFileSync(hookPath, "utf8").includes(MARKER)) {
    console.error(`pre-commit: a hook this installer did not write already exists at\n  ${hookPath}\nLeaving it untouched. Merge the Mermaid check in by hand if you want both.`);
    process.exit(1);
  }

  writeFileSync(hookPath, HOOK, { mode: 0o755 });
  try {
    chmodSync(hookPath, 0o755);
  } catch {
    // chmod is a no-op on Windows; git still runs the hook via sh.
  }
  console.log(`pre-commit: installed the Mermaid sidecar check at\n  ${hookPath}`);
}

main();
