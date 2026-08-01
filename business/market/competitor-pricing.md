---
title: "Memory Seed Competitor Pricing"
status: active
last_reviewed: "2026-08-01"
next_review_due: "2026-09-01"
confidence: medium
---

# Memory Seed competitor pricing

## Purpose and current conclusion

This dossier records public pricing for the ten-company landscape and normalizes only genuinely
comparable groups. Prices are USD, checked 2026-08-01. Taxes, custom enterprise contracts, infrastructure,
and external model charges are excluded unless noted.

Current anchors:

- Free or open-source entry is the category norm.
- The median lowest fixed paid subscription is **$19/month**.
- The typical production/team band is approximately **$100-$249/month**.
- Published ingestion/retention pricing clusters around **$2-$10 per million tokens**.

## Published pricing

| Competitor | Free or self-hosted route | Published paid pricing | Public range |
|---|---|---|---:|
| Unblocked | 21-day trial; no permanent free plan observed | Code Review $23/user/month; Platform $35/user/month; annual equivalents $19 and $29; Enterprise custom | $19-$35/user/month |
| Pieces | Free plan | Pro $18.99/month or $169.99/year ($14.17/month equivalent) | $0-$18.99/month |
| Agiflow | Free for two seats and three projects | Team $9/seat/month or $7 annually; remote execution overage $0.09/hour | $0-$9/seat/month plus usage |
| Acontext | Apache-2.0 self-hosting | No numeric managed-cloud price found | $0 self-hosted; cloud unpublished |
| Cognee | Free cloud workspace/allowance and open source | $2.50 per 1M processed tokens; $5/additional workspace; Enterprise custom | $0 to usage-based |
| Hindsight | MIT self-hosting and cloud credits | Retain $10/M tokens; Recall $0.75/M; Reflect $0.05/call; Iris Extract $7.50/M; storage $0.25/M/month | $0 to usage-based |
| Zep | Free prototyping tier | Flex $125/month or $104 annual equivalent; Flex Plus $375 or $312; overages; Enterprise custom | $0-$375/month plus overages |
| Supermemory | Free allowance | Pro $19/month; Max $100; Scale $399; additional standard processing about $5/M tokens | $0-$399/month plus usage |
| Mem0 | Free Hobby plan and open source | Starter $19/month; Pro $249; Enterprise custom | $0-$249/month |
| Honcho | AGPL-3.0 self-hosting | $2/M ingested tokens; advanced chat $0.001-$0.50/query | $0 to usage-based |

Public plan pages change frequently. Re-check the vendor source before using a row in an external
document or pricing decision.

## Normalized calculations

### Lowest month-to-month fixed subscription

Comparable inputs: 23, 18.99, 9, 125, 19, 19.

| Statistic | Result |
|---|---:|
| Average | **$35.67/month** |
| Median | **$19/month** |
| Range | **$9-$125/month** |

Using Unblocked Platform at $35 instead of Code Review produces a **$37.67** average and unchanged
**$19** median.

### Cheapest annual-billing equivalents

Comparable inputs: 19, 14.17, 7, 104, 19, 19. Mem0 and Supermemory have no lower annual figure
recorded, so their monthly prices are retained.

| Statistic | Result |
|---|---:|
| Average | **$30.36/month** |
| Median | **$19/month** |
| Range | **$7-$104/month** |

### Highest published non-enterprise fixed tier

Comparable inputs: 35, 18.99, 9, 375, 399, 249.

| Statistic | Result |
|---|---:|
| Average | **$181.00/month** |
| Median | **$142.00/month** |
| Range | **$9-$399/month** |

### Core token ingestion or retention

Directional inputs: Honcho 2.00, Cognee 2.50, Supermemory 5.00, Hindsight Retain 10.00 dollars per
million tokens.

| Statistic | Result |
|---|---:|
| Average | **$4.88/M tokens** |
| Median | **$3.75/M tokens** |
| Range | **$2-$10/M tokens** |

The operations and token definitions differ, so this is a pricing signal rather than an equivalent
unit-cost comparison.

## Pricing interpretation for Memory Seed

Internal hypothesis, not a published competitor fact:

- Open-source/local core.
- $19-$29 individual hosted tier.
- $99-$249 team tier.
- Separately priced enterprise governance, deployment, and support.
- Usage pricing only where infrastructure cost and customer value both scale with use.

## Unresolved validation questions

- Which plans convert developers into durable paid teams rather than short-lived trials?
- Do buyers prefer per-seat, per-project, or usage pricing for shared project memory?
- What gross margin follows from managed indexing, retrieval, and model calls?
- Which governance capabilities support enterprise pricing above the self-serve tiers?
- How should local-only users contribute economically without undermining adoption?

## Related dossiers

- [Competitor landscape](competitor-landscape.md)
- [Market size](market-size.md)
- [Developer project-memory wedge](../wedges/developer-project-memory.md)

## Source register

All checked 2026-08-01:

- [Unblocked pricing](https://www.unblocked.com/pricing)
- [Pieces pricing](https://pieces.app/pricing)
- [Agiflow pricing](https://agiflow.io/pricing)
- [Acontext](https://acontext.io/)
- [Cognee pricing](https://www.cognee.ai/)
- [Hindsight pricing](https://vectorize.io/hindsight/pricing)
- [Zep pricing](https://www.getzep.com/pricing)
- [Supermemory pricing](https://supermemory.ai/pricing)
- [Mem0 pricing](https://mem0.ai/pricing)
- [Honcho pricing](https://honcho.dev/pricing)

## Change log

- **2026-08-01:** Created the living pricing dossier, normalized fixed and token-metered groups, and
  recorded the initial Memory Seed pricing hypothesis.

