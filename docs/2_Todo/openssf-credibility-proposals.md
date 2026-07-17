---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - security
  - supply-chain
  - openssf
---

# OpenSSF credibility proposals (4 tracks)

Status: **IN-REPO SLICE SHIPPED 2026-07-17** (JNL greenlit the implementation plan after the
checkpoint this line used to gate). Landed: G0 `SECURITY.md`, `CONTRIBUTING.md`, CodeQL + Scorecard
workflows, README badges, SHA-pinned + least-privilege `verify.yml`/`publish.yml` (G1 itself was
delivered by `verify.yml`, 2026-07-17, codex). Sigstore/SLSA (Proposals 3–4) are documented in
`SECURITY.md` "Verifying a release", confirmed at the next cut. **Open user actions:** private
vulnerability reporting toggle, G2 (`integration_mode: pr` + branch protection), bestpractices.dev
submission.
Priority: P2 — credibility/adoption; low runtime blast radius (additive governance files + CI +
workflow change; no change to Memory Seed's runtime behaviour or public API).
Source: User request 2026-07-13 following an OpenSSF overview ("which programs should Memory Seed be
considered for to improve credibility"), then "create proposals for all 4."
Scope: Position Memory Seed for four OpenSSF-aligned credibility signals on a shared SECURITY.md + CI
foundation, and adopt a PR/branch-protection workflow.
Non-goals: **Alpha-Omega** funding (reserved for already-critical, widely-depended-on projects — not
a fit for a new niche tool); **GUAC / package-analysis / Criticality Score / S2C2F** (consumer /
analysis tooling and frameworks, not badges a project earns). No runtime/API changes.

## Locked decisions (user, 2026-07-13 Q&A)
1. **The four tracks:** Best Practices Badge, Scorecard, Sigstore signed-provenance, SLSA.
   `SECURITY.md` is the shared prerequisite, written first (folded into the Badge/Scorecard work,
   not a fifth track).
2. **Vulnerability disclosure:** GitHub **private vulnerability reporting** (no email published).
3. **Review model:** adopt a **PR-based flow with branch protection on `main`** — this replaces the
   direct-merge-to-local-`main` flow and **requires pushing feature branches + PRs to origin** as a
   standing part of this initiative.
4. **CI:** minimal — **ubuntu-latest × Python 3.11**, running the core (413) and memory-trace (97)
   suites on `push` + `pull_request`.

## Shared groundwork (prerequisites for all four)

### G0 — `SECURITY.md` (repo root)
A vulnerability-disclosure policy pointing at GitHub private vulnerability reporting, a
supported-versions table, and a short threat model drawn from the existing posture: public-memory
hygiene (no secrets/credentials/unnecessary PII in memory or logs); hooks are read-only and cannot
exfiltrate; PyPI publish uses OIDC Trusted Publishing + a manual `pypi`-environment approval gate.
Required/checked by **both** the Badge and Scorecard — the single cheapest, highest-signal file.
- **Needs user:** enable *Settings → Security → Private vulnerability reporting* (I give the exact
  click-path; I cannot toggle a GitHub setting).

### G1 — CI test workflow (`.github/workflows/ci.yml`)
`ubuntu-latest × Python 3.11`; installs the package with the `trace` extra; runs `pytest tests` and
`pytest memory-trace/tests` on `push` + `pull_request`. Emits the green status check that branch
protection will require and that the Badge/Scorecard **CI-Tests** check rewards.
- **Risk noted:** the suite is Windows-developed (Git Bash, Windows-encoding handling). The first
  Ubuntu run may surface platform issues (path separators, CRLF, temp-dir cleanup); the plan budgets
  a fix pass before wiring it as a required check.

### G2 — PR + branch-protection workflow (via the integration-mode foundation)
Rather than a bespoke one-off switch, this repo adopts the PR flow by **declaring
`integration_mode: pr`** per the shipped
[`configurable-integration-mode-plan.md`](../5_Completed/configurable-integration-mode-plan.md). The
agent + tooling then follow it: feature branch → push origin → PR → required CI
green → merge on GitHub. Branch protection on `main`: require a PR, require the `ci` status check.
Solo maintainer: a second-reviewer requirement is not achievable, so code review stays self-review —
**documented, not faked**. A declared `pr` mode is the standing push authorization.
- **Foundation status:** all configurable integration-mode phases shipped 2026-07-15. This proposal is
  no longer blocked on tooling; changing this repository to `integration_mode: pr` remains an explicit
  project decision, and branch protection remains a user-administered GitHub setting.
- **Needs user:** configure branch protection on `main` (*Settings → Branches*; I provide the exact
  settings).

## Proposal 1 — OpenSSF Best Practices Badge (target: passing)
Memory Seed already meets most *passing* criteria (FLOSS license, public VCS, `CHANGELOG` release
notes, automated tests, OIDC-signed releases). Gaps to close: `SECURITY.md` (G0), visible CI (G1), a
`CONTRIBUTING.md` describing the contribution/review process, and the "static analysis" +
"know-secure-design" criteria (satisfied by adding CodeQL in Proposal 2 and citing the practice).
Register at `bestpractices.dev` (GitHub OAuth), fill the questionnaire, add the badge to `README`.
- **Acceptance:** passing badge earned; badge on `README`. Silver/gold assessed later (some silver
  criteria — e.g. 2-person review — are solo-capped).
- **Needs user:** create the `bestpractices.dev` entry — **I draft every answer; you click submit.**

## Proposal 2 — OpenSSF Scorecard
Add `ossf/scorecard-action` (scheduled + on push to `main`) publishing to the Scorecard API, plus the
Scorecard badge on `README`. Remediate the closeable checks: **Token-Permissions** (minimal
`permissions:` in every workflow), **Pinned-Dependencies** (pin action SHAs), **Security-Policy**
(G0), **CI-Tests** (G1), **Dangerous-Workflow**, **SAST** (add CodeQL). **Branch-Protection /
Code-Review** improve via G2 (score capped for a solo maintainer — documented).
- **Acceptance:** scorecard-action runs; badge on `README`; a short doc noting which checks are
  solo-capped and why.
- **Needs user:** none beyond G2.

## Proposal 3 — Sigstore signed provenance (PEP 740 attestations)
`publish.yml` already uses Trusted Publishing (`id-token: write`, `pypa/gh-action-pypi-publish`),
which emits PEP 740 / Sigstore attestations **by default** — verify it is not disabled. Document that
releases are Sigstore-signed and add a "verifying a release" section (checking attestations on PyPI).
Largely already in place.
- **Acceptance:** a released artifact shows verified attestations on PyPI; docs explain verification.
- **Needs user:** none (confirm at the next release cut).

## Proposal 4 — SLSA Build Level 3 provenance
Builds on Proposal 3: the Trusted-Publishing + attestations flow yields SLSA build provenance from a
hosted, isolated GitHub Actions build. Document the achieved level (target **Build L3**), add a SLSA
claim/badge to `README`, and reference the verification steps. If any gap to L3 exists (e.g. a
non-isolated build step), state it honestly rather than overclaiming.
- **Acceptance:** a documented, defensible SLSA Build L3 claim tied to the attestation flow; claim on
  `README`.
- **Needs user:** none.

## Sequencing
`G0` + `G1` first (they unblock everything). Then `G2` (needs `ci` to exist as the required check).
Then Proposals 1–2 (depend on G0/G1/G2). Proposals 3–4 are mostly documentation over the existing
Trusted-Publishing flow and can land in parallel.

## Division of labour (honest boundary)
- **I do** (in-repo files): `SECURITY.md`, `CONTRIBUTING.md`, `ci.yml`, the Scorecard workflow +
  CodeQL, `README` badges, `publish.yml` hardening (pin SHAs, minimal `permissions:`, confirm
  attestations), and every drafted answer for the badge questionnaire.
- **You do** (GitHub/PyPI settings I cannot change): enable Private Vulnerability Reporting; configure
  branch protection on `main`; create/submit the `bestpractices.dev` entry (I draft, you submit);
  authorize origin pushes for the PR flow.
