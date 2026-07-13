---
title: "Memory Trace Hosted Product and Security Architecture"
date: "2026-07-11"
project: "memory-seed"
deferred_reason: "needs commercial + billing/auth decisions and a later security review (self-labeled P5)"
revisit_when: "local Community/Pro foundations are stable"
parent: "memory-trace-product-and-system-architecture-blueprint.md"
---

# Memory Trace Hosted Product and Security Architecture

Status: Active proposal, promoted from inbox on 2026-07-11.
Priority: P5 after local Community/Pro foundations and Evidence Pack/annotation contracts are stable.
Source reference: `../4_Reference/memory-trace-next-generation-plan-document-set.md`, folded with the commercialisation report and existing local-first security posture.
Scope: Hosted/local split, threat model, authn/authz, GitHub integration, sync, offline entitlements, premium code placement, web/AI security, audit, and deployment models.
Non-goals: No immediate hosted implementation, no write-scope GitHub App by default, no full-repository hosted ingestion by default, no network dependency for free local Trail.
Dependencies: `memory-trace-product-and-system-architecture-blueprint.md`, `memory-trace-commercialisation-and-monetisation-report.md`, `memory-trace-evidence-annotations-and-projection-architecture.md`, and a later security review.
Acceptance criteria: Tenant isolation, provider permissions, deletion/export, audit, offline entitlement, markdown sanitisation, and managed-AI retention controls are testable before team/private-repo release.

## 1. Scope

Define an architecture suitable first for small teams handling private repositories while avoiding choices that block enterprise deployment.

The local product remains functional without the hosted service.

## 2. Product split

Use shared domain components with separate shells:

```text
shared/
  API client
  design tokens
  Trail
  graph
  evidence workspace
  annotations
  generated artifacts

local shell/
  local project discovery
  FastAPI localhost
  offline entitlement cache

hosted shell/
  authentication
  organisations/workspaces
  billing
  cloud sync
  provider connections
```

## 3. Threat model

Protect against:

- cross-tenant data access;
- stolen Git provider tokens;
- malicious repository/Markdown content;
- stored and reflected XSS;
- prompt injection through PRs/annotations;
- insecure direct object references;
- privilege escalation;
- replayed sync events;
- tampered offline licences;
- supply-chain compromise;
- accidental full-repository ingestion;
- leakage through logs and analytics.

## 4. Security baseline

Use OWASP ASVS 5.0 as the verification baseline and OWASP Top 10 awareness for implementation review.

Minimum controls:

- secure authentication and session management;
- server-side authorisation on every resource;
- input validation and output sanitisation;
- CSP and security headers;
- CSRF protection where cookies are used;
- rate limiting;
- dependency and secret scanning;
- structured audit logs;
- encryption in transit and at rest;
- secure deletion and retention controls.

## 5. Authentication and organisations

Recommended:

- standards-based OIDC/OAuth;
- passkeys or modern MFA support;
- short-lived sessions;
- organisation/workspace membership;
- project-scoped roles;
- enterprise SSO/SCIM later.

Follow current OAuth security best practice and avoid implicit flows. Use PKCE where relevant.

## 6. Authorisation

Separate:

- organisation role;
- workspace role;
- project participant role;
- provider permissions;
- annotation authority.

Every API route checks tenant, project and capability. Frontend gating is informational only and never the security control.

## 7. GitHub integration

Prefer a GitHub App over broad personal access tokens.

Principles:

- request the minimum repository permissions;
- separate read metadata from write operations;
- default to read-only;
- store installation IDs rather than broad user tokens where possible;
- encrypt credentials;
- rotate and revoke;
- log provider access;
- make provider freshness visible.

PR comment authoring remains on GitHub initially. Memory Trace does not request write scopes merely to display context.

## 8. Repository data policy

Default hosted policy:

- store Memory Seed data and selected provider metadata;
- do not ingest complete repository contents;
- retain source snippets only when explicitly selected for an evidence pack;
- allow enterprise-configurable retention;
- expose deletion/export controls;
- document model-provider data flow.

## 9. Synchronisation

Sync is event-oriented:

- authoritative project records remain file-compatible;
- each append-only annotation event has an ID/version;
- server detects conflicts without overwriting history;
- client retains offline operation;
- sync queues are idempotent;
- project identities cannot collide across tenants.

## 10. Offline entitlements

Recommended hybrid:

- hosted subscription entitlement;
- signed cached offline licence;
- grace period;
- local Community features never require entitlement;
- premium local features fail gracefully;
- no network dependency for free local Trail.

Signed entitlements include:

- licence ID;
- product tier;
- expiry/grace;
- permitted organisation/user;
- signature;
- feature flags.

Do not store signing private keys in the client.

## 11. Premium code placement

- Shared low-risk Pro UI may ship in the client and be entitlement-gated.
- Sensitive connectors, managed AI and proprietary enterprise controls remain server-side or separate packages.
- Formats and user data remain exportable after subscription expiry.

## 12. Web security

- Strict Content Security Policy.
- No remote scripts by default.
- Sanitised Markdown and diagrams.
- Trusted Types where practical.
- Secure cookies in hosted mode.
- SameSite and CSRF controls.
- Dependency pinning and lockfile review.
- Subresource integrity only where third-party assets are unavoidable; prefer none.

## 13. AI security

- Evidence-pack-only default.
- Treat repository, annotation and PR text as untrusted data.
- Do not interpolate external text into system instructions.
- Validate structured output.
- Enforce input/output limits.
- Redact secrets.
- Provider selection and retention are explicit.
- Managed AI access is tenant-scoped and audited.

## 14. Audit

Audit events:

- login and membership change;
- provider connection/revocation;
- annotation create/update/resolve;
- evidence-pack generation;
- AI generation;
- export/publish;
- role change;
- retention/deletion action;
- licence/entitlement decision.

Audit logs do not store full sensitive content unless required and disclosed.

## 15. Deployment models

### Managed SaaS

Primary team product.

### Self-hosted

Enterprise path with:

- containerised deployment;
- external database/object storage;
- secret management integration;
- documented backup/restore;
- network isolation.

### Local-only

Python package and localhost server remain supported.

## 16. Security milestones

1. Threat model and data-flow diagrams.
2. Authn/authz prototype.
3. GitHub App least-privilege review.
4. Sync protocol and conflict model.
5. ASVS-derived test plan.
6. Independent security review before private-repo general availability.
7. Enterprise controls after core team model is stable.

## 17. Acceptance criteria

- No cross-tenant resource access is possible through identifier changes.
- GitHub permissions are minimal and documented.
- Local Community operation is account-free.
- Offline licences are signed and revocable through expiry.
- Markdown/PR/annotation content cannot execute script.
- Managed AI uses bounded evidence and explicit retention.
- Audit and deletion workflows are testable.
- Hosted architecture can support self-hosting without forking core domain models.

## 18. References

- OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
- OWASP Top Ten: https://owasp.org/www-project-top-ten/
- GitHub App permissions: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app
- CSP guide: https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP
- OAuth 2.0 Security Best Current Practice: https://www.rfc-editor.org/rfc/rfc9700
