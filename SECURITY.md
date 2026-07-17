# Security Policy

## Reporting a vulnerability

Please report suspected vulnerabilities through
[GitHub private vulnerability reporting](https://github.com/jnl-tshi/memory-seed/security/advisories/new)
("Report a vulnerability" on the repository's Security tab). Reports go privately to the maintainer;
please do not open a public issue for a security problem.

You can expect an acknowledgement within 7 days. There is no bug bounty.

## Supported versions

Memory Seed is pre-1.0-style tooling with a single release line: fixes land on the newest release only.

| Version | Supported |
|---|---|
| latest release (currently 2.x) | ✅ |
| anything older | ❌ upgrade first |

## Threat model (short form)

Memory Seed is a **local-first CLI/MCP tool**: the core runs with no server, no database, and no network.
The main surfaces and the postures behind them:

- **Session memory is plain Markdown in your repository.** Treat it as public-by-default: the
  `memory_hygiene` guidance forbids secrets, credentials, and unnecessary PII in memory or logs, and
  nothing in Memory Seed transmits it anywhere.
- **Hooks are read-only.** The seeded git/session hooks inspect and annotate; they are not an
  exfiltration or execution surface.
- **The optional Memory Trace UI is local.** It binds to localhost, reads a rebuildable SQLite
  projection derived from your Markdown, and has no write path to session history.
- **Publishing is gated.** PyPI releases use OIDC Trusted Publishing (no long-lived tokens) from an
  isolated GitHub Actions build, and the final push waits on a manual `pypi`-environment approval.
- **CI tokens are least-privilege.** Workflows default to `contents: read`; the only elevated grants are
  `id-token: write` on the publish job (OIDC) and `security-events: write` where SARIF is uploaded.
  Third-party actions are pinned to full commit SHAs.

## Verifying a release

Releases are built and published via `pypa/gh-action-pypi-publish` with Trusted Publishing, which
generates [PEP 740](https://peps.python.org/pep-0740/) / Sigstore attestations by default. To verify:

1. Open the file list for a release on PyPI (`https://pypi.org/project/memory-seed/#files`) and check
   the distribution shows **verified attestations** naming this repository's `publish.yml` workflow as
   the trusted publisher.
2. Or verify offline with [`pypi-attestations`](https://pypi.org/project/pypi-attestations/):
   `python -m pypi_attestations verify pypi --repository https://github.com/jnl-tshi/memory-seed <dist-file-url>`.

Provenance claim, stated conservatively: the build runs on ephemeral, hosted GitHub Actions runners from
a workflow in this repository, with OIDC-bound attestations — the shape of **SLSA Build L3** provenance.
The claim is confirmed against the attestations of each release at cut time rather than asserted ahead
of it.
