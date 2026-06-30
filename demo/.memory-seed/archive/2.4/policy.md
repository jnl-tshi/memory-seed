---
memory-system-version: 2.4
tags:
  - memory-seed
  - runtime-policy
  - sub-project
  - demo
---

# Demo Sub-Project Runtime Policy

## Scope

Behavioral constraints for the `demo/` HyperFrames sub-project. Inherits root policy (`../.memory-seed/policy.md`). Local constraints below override parent only where explicitly noted.

## Local Constraints

- Always run `npm run check` after editing `index.html`. Fix all errors before reporting the composition ready.
- Do not commit `demo/node_modules/` or `demo/memory-seed-demo.mp4` to git.
- Keep `demo/CLAUDE.md` intact — it is the HyperFrames skill routing file, not a memory-seed routing file.
- Do not overwrite `demo/AGENTS.md` or `demo/CLAUDE.md` with memory-seed init output.
- Treat the rendered MP4 as a build artifact: generate it locally, host it separately.
- Do not embed secrets, credentials, private account details, or proprietary information into the composition or session logs.

## Inherited from Parent

All constraints from root `.memory-seed/policy.md` apply, including safety, destructive-operation checks, and public memory hygiene rules.
