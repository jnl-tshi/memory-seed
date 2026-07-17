---
title: "OpenSSF Scorecard — expected results and solo-maintainer caps"
date: "2026-07-17"
project: "memory-seed"
kind: report
related:
  - "docs/2_Todo/openssf-credibility-proposals.md"
---

# OpenSSF Scorecard — expected results and solo-maintainer caps

The Scorecard workflow (`.github/workflows/scorecard.yml`) publishes results to the Scorecard API and
uploads SARIF to code scanning. This note records which checks are addressed, which are **capped by the
project's honest shape** (one maintainer), and which wait on user-side settings — so a middling score is
read correctly rather than as neglect.

## Addressed in-repo (2026-07-17)

| Check | How |
|---|---|
| Token-Permissions | every workflow defaults to `contents: read`; elevated grants are per-job (`id-token: write` on publish, `security-events: write` for SARIF) |
| Pinned-Dependencies | every third-party action pinned to a full commit SHA, resolved from upstream tags |
| Security-Policy | `SECURITY.md` (private vulnerability reporting, threat model, release verification) |
| CI-Tests | `verify.yml` on push + PR (core suite, Trace suite, link integrity, React build) |
| SAST | CodeQL workflow, python + javascript-typescript, push/PR/weekly |
| Dangerous-Workflow | no `pull_request_target`, no script injection from untrusted inputs |
| Packaging | PyPI via OIDC Trusted Publishing |

## Capped by being solo-maintained — documented, not faked

- **Code-Review** — there is no second human; review is self-review plus the automated gate
  (`CONTRIBUTING.md` states this plainly). The check will score low; inventing rubber-stamp reviews to
  raise it would defeat its point.
- **Contributors** — a single-org contributor pool scores low by definition.

## Waiting on user-side settings (documented click-paths, agent cannot toggle)

- **Branch-Protection** — requires configuring protection on `main` (*Settings → Branches*) and adopting
  `integration_mode: pr`; an explicit project decision, not a repo file.
- **Maintained / Vulnerabilities** — improve with normal activity and Dependabot/security updates
  settings.

## Not pursued

- **Fuzzing** — no fuzz harness; a Markdown-parsing CLI has a real but modest fuzzing surface, and
  OSS-Fuzz integration is out of proportion for now.
- **Signed-Releases** — PyPI attestations via Trusted Publishing cover provenance (see `SECURITY.md`
  "Verifying a release"); GitHub release-asset signing is not separately implemented.
