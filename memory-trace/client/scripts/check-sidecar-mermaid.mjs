#!/usr/bin/env node
// Parse every Mermaid block in the diagram sidecars through the REAL Mermaid
// parser, so a diagram that will not render is caught before it is committed -
// the exact class of defect (`;` in a sequence message, `--` inside an edge
// label) that `links check` cannot see, because it validates a sidecar's
// STRUCTURE and never parses the Mermaid.
//
// mermaid.parse() runs HTML labels (`<br/>`, and every real sidecar uses them)
// through DOMPurify, which needs a `window` to initialise - without one it
// throws "DOMPurify.addHook is not a function" on almost every diagram. So a
// DOM is set up before mermaid is imported. jsdom is a dev-only dependency;
// render() is never called, only parse(), so this stays lightweight. mermaid
// resolves from the Trace client's node_modules because this file lives under
// client/scripts/.
//
// Two entry points: import { checkSidecars } for a test, or run it as a CLI
// (no args = sweep every sidecar; args = check just those files, which is how
// the pre-commit hook passes the staged ones). Exit 1 on any parse failure.

import { execFileSync } from "node:child_process";
import { readFileSync, readdirSync } from "node:fs";
import { join, resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";

const MERMAID_BLOCK = /```mermaid\r?\n([\s\S]*?)```/g;
const SIDECAR_DIR = ".memory-seed/sessions/diagrams";

function repoRoot() {
  try {
    return execFileSync("git", ["rev-parse", "--show-toplevel"], { encoding: "utf8" }).trim();
  } catch {
    return process.cwd();
  }
}

function discoverSidecars(root) {
  const out = [];
  const walk = (dir) => {
    let entries;
    try {
      entries = readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      const path = join(dir, entry.name);
      if (entry.isDirectory()) walk(path);
      else if (entry.name.endsWith(".md")) out.push(path);
    }
  };
  walk(join(root, ...SIDECAR_DIR.split("/")));
  return out;
}

function mermaidBlocks(text) {
  const blocks = [];
  MERMAID_BLOCK.lastIndex = 0;
  let match;
  while ((match = MERMAID_BLOCK.exec(text)) !== null) blocks.push(match[1]);
  return blocks;
}

/**
 * Parse every Mermaid block in `files`. Returns { skipped, failures, blockCount }.
 * `skipped` is true when mermaid could not be imported (a non-Trace checkout);
 * callers treat that as a pass, never a block.
 */
export async function checkSidecars(files) {
  // A DOM must exist BEFORE mermaid is imported (DOMPurify captures `window`
  // at module-eval time). Reuse an existing one - a vitest jsdom env already
  // has it - and only spin up jsdom in bare node. No DOM and no jsdom means we
  // cannot parse reliably, so skip rather than raise false failures.
  if (typeof globalThis.window === "undefined") {
    try {
      const { JSDOM } = await import("jsdom");
      const dom = new JSDOM("<!doctype html><body></body>");
      globalThis.window = dom.window;
      globalThis.document = dom.window.document;
    } catch {
      return { skipped: true, failures: [], blockCount: 0 };
    }
  }
  let mermaid;
  try {
    mermaid = (await import("mermaid")).default;
  } catch {
    return { skipped: true, failures: [], blockCount: 0 };
  }
  const failures = [];
  let blockCount = 0;
  for (const file of files) {
    let text;
    try {
      text = readFileSync(file, "utf8");
    } catch {
      continue;
    }
    const blocks = mermaidBlocks(text);
    for (let index = 0; index < blocks.length; index++) {
      blockCount++;
      try {
        await mermaid.parse(blocks[index]);
      } catch (error) {
        failures.push({
          file,
          block: index + 1,
          firstLine: (blocks[index].trim().split("\n")[0] || "").slice(0, 64),
          error: String(error && error.message).split("\n")[0],
        });
      }
    }
  }
  return { skipped: false, failures, blockCount };
}

async function main() {
  const root = repoRoot();
  const isSidecar = (path) => resolve(path).replace(/\\/g, "/").includes(`/${SIDECAR_DIR}/`);
  const passed = process.argv.slice(2).filter((arg) => arg.endsWith(".md"));
  const files = passed.length
    ? passed.map((arg) => resolve(arg)).filter(isSidecar)
    : discoverSidecars(root);

  if (files.length === 0) process.exit(0);

  const { skipped, failures, blockCount } = await checkSidecars(files);
  if (skipped) {
    console.warn("check-sidecar-mermaid: mermaid is not installed here, skipping the parse check.");
    process.exit(0);
  }
  if (failures.length > 0) {
    console.error(`\n✖ ${failures.length} unparseable Mermaid block(s) - this commit would ship a broken diagram:\n`);
    for (const failure of failures) {
      console.error(`  ${relative(root, failure.file)}  (block ${failure.block})  [${failure.firstLine}]`);
      console.error(`    ${failure.error}`);
    }
    console.error("\nFix the diagram (see .memory-seed/skills/compact_mermaid_diagrams.md) or unstage it, then commit again.\n");
    process.exit(1);
  }
  console.log(`✓ ${blockCount} Mermaid block(s) parse across ${files.length} sidecar file(s).`);
  process.exit(0);
}

// Run as a CLI only when invoked directly, so importing checkSidecars is inert.
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  void main();
}
