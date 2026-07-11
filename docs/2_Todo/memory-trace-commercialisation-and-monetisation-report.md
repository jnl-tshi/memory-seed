---
title: "Memory Trace Commercialisation and Monetisation Report"
date: "2026-07-11"
project: "memory-seed"
status: "research-backed-proposal"
parent: "memory-trace-product-and-system-architecture-blueprint.md"
---

# Memory Trace Commercialisation and Monetisation Report

Status: Active commercial strategy proposal, promoted from inbox on 2026-07-11.
Priority: P4 for product packaging/pricing decisions after local product value is demonstrable.
Source reference: `../4_Reference/memory-trace-next-generation-plan-document-set.md`, informed by `../4_Reference/memory-seed-market-fit-report.md`.
Scope: Commercial wedge, free/paid boundary, tier hypotheses, AI economics, validation plan, metrics, and monetisation risks.
Non-goals: No final pricing, no billing implementation, no claim of demonstrated product-market fit, no paywall on the core local Trail.
Dependencies: `memory-trace-product-and-system-architecture-blueprint.md`, `memory-trace-hosted-product-and-security-architecture.md`, and real usage/interview validation.
Acceptance criteria: Community/Pro/Team/Enterprise boundaries are validated with users, local Trail remains free, managed AI economics are explicit, and analytics remain opt-in/content-free.

## 1. Market conclusion

Memory Seed has strong market-problem fit and a credible product-market-fit hypothesis. It does not yet have usage, retention or willingness-to-pay evidence sufficient to claim product-market fit.

The commercial wedge is:

> Git-native institutional memory for software projects worked on by humans and AI agents.

Memory Seed supplies the durable substrate. Memory Trace is the visible product and likely monetisation surface.

## 2. Primary segment

Primary target:

- small engineering teams using multiple coding agents.

Secondary target:

- AI-forward agencies and consultancies.

Adoption wedge:

- individual AI-native developers.

Buyer/user distinction:

| Role | Value |
|---|---|
| Developer | Search, Trail and evidence inspection |
| Tech lead | Decision lineage, PR evidence and unresolved requests |
| Manager | Project updates, risks and handover |
| Agency owner | Client reporting and project continuity |
| Security/admin | Access, audit and retention |

## 3. Should the Trail be free?

### Recommendation

Do not place the entire local Trail behind a paywall.

The Trail is the product's clearest differentiation and the main reason users will maintain structured Memory Seed history. A paywall before the user experiences that value would restrict adoption and make market validation harder.

The stronger model is:

- free local single-project Trail;
- paid advanced analysis, cross-project features and generation;
- paid hosted collaboration and integrations;
- metered managed AI;
- enterprise security and deployment.

### Comparable models

Obsidian makes its local application free without limits and monetises Sync and Publish. Its paid services add synchronisation, history, collaboration and web publishing.

Raycast keeps core productivity features free and charges for Pro AI, cloud sync, expanded limits and team administration.

PostHog keeps broad core value inside a generous free tier, then charges for scale, more projects, longer retention and usage.

These examples support charging for convenience, scale, collaboration and variable-cost services rather than hiding the core local experience.

## 4. Recommended tiers

## 4.1 Community

- local single-project Trail;
- complete local history;
- search-to-Trail navigation;
- basic graph;
- evidence workspace;
- local decision annotations;
- offline operation;
- no account;
- MCP integration;
- basic local export.

The last-seven-days/last-five-active-days range is a default viewport, not a hard limit.

## 4.2 Pro

- cross-project search and dashboard;
- saved views;
- advanced range and decision comparison;
- advanced graph modes;
- local/BYOK summarisation;
- project updates;
- presentation generation;
- premium templates;
- richer exports;
- personal sync if commercially viable.

Initial pricing hypothesis:

- £/€/$8–15 monthly;
- £/€/$80–120 annually.

This must be validated through interviews and trials.

## 4.3 Team

- hosted workspaces;
- synchronisation;
- authenticated participant roles;
- shared annotations;
- notifications and assignments;
- GitHub live integration;
- cached/snapshotted PR timelines;
- shared reports;
- managed AI allowance;
- cross-project search;
- audit history.

Initial pricing hypothesis:

- £/€/$15–25 per active user monthly;
- optional workspace minimum.

## 4.4 Enterprise

- SSO/SCIM;
- self-hosting;
- private provider support;
- GitHub Enterprise/GitLab/Azure DevOps;
- retention and data residency;
- policy controls;
- advanced audit;
- contractual support.

## 5. Open-source boundary

Recommended:

### Open

- Memory Seed core;
- file formats and graph contracts;
- local Memory Trace Community client;
- local FastAPI server;
- basic Trail/graph/search;
- annotation format;
- deterministic evidence-pack format.

### Commercial

- hosted control plane;
- organisation/workspace management;
- synchronisation service;
- managed integrations;
- managed AI;
- advanced team workflows;
- enterprise governance.

Some advanced local Pro modules may be commercially licensed, but the authoritative formats must remain portable and readable without a subscription.

## 6. AI economics

### Local model/BYOK

Charge for capability in Pro/Team, not per token when the user supplies compute or keys.

### Managed AI

Use:

- included monthly allowance;
- transparent credit usage;
- metered overage or packs;
- no metering for deterministic file formatting after generation.

## 7. Revenue sequencing

### Before cloud

A Pro licence can monetise:

- advanced local comparison;
- cross-project features;
- local/BYOK summaries;
- report/presentation generation.

### After cloud

Team/Cloud is the strongest long-term commercial path because collaboration, provider integrations and managed security have higher willingness to pay.

## 8. Validation plan

Before fixing pricing:

1. Interview 10–15 AI-native developers.
2. Interview 5–10 engineering leads/agencies.
3. Observe Trail usage on real projects.
4. Test free versus Pro feature descriptions.
5. Offer paid design-partner access.
6. Track activation, repeated weekly use and export/report use.

Correct success statement before evidence:

> Strong problem-solution hypothesis, under validation.

## 9. Product metrics

Local opt-in, content-free metrics:

- first successful project load;
- Trail search used;
- search result inspected;
- graph neighbourhood opened;
- annotation created;
- evidence pack built;
- report/presentation exported;
- performance timings.

Hosted metrics:

- weekly active projects;
- active seats;
- reports generated;
- GitHub integrations connected;
- annotation resolution time;
- retention by team cohort.

Never capture repository content or filenames in analytics.

## 10. Risks

- A free Trail could reduce individual licence conversion.
- A paid Trail could prevent adoption and trust.
- Open-source local code makes strict client-side gating weak.
- Managed AI margins may fluctuate.
- Enterprise security work is expensive.
- Scope can sprawl into project management and agent orchestration.

Mitigation: monetise high-value workflow outcomes, not access to users' own local history.

## 11. Recommended decision

Proceed with:

- Community local Trail free;
- Pro advanced local analysis and generation;
- Team hosted collaboration and Git integration;
- Enterprise security/self-hosting;
- managed AI metered separately.

Revisit the boundary after real usage evidence.

## 12. Official pricing references reviewed

- Obsidian pricing: https://obsidian.md/pricing
- Raycast pricing: https://www.raycast.com/pricing
- PostHog pricing: https://posthog.com/pricing
- Sentry pricing: https://sentry.io/pricing/
- GitKraken pricing: https://www.gitkraken.com/pricing
