# Decision reconstruction recovery trial

Status: implementation in progress; no accuracy claim.

The user approved comparing frozen deterministic extraction with semantic
interpretation by existing Codex agents, followed by independent evidence review.
First prove reconstruction; automatic discovery and live integration depend on
the reconstruction gate. Use smaller implementers for bounded tasks.

## Frozen acceptance contract

- At least 30 supported fresh positive cases and 30 independently reviewed hard
  negatives, grouped by actual root/parent lineage and disjoint from all previous
  development and examined test groups. Insufficient data is inconclusive.
- At least 80% complete recovery and 95% precision, with zero observed false
  acceptance or wrong-actor errors. Missing material conditions or invented reasons
  fail equivalence. Abstentions count as misses; extra/duplicate outputs count.
- Two independent masked reviews, with conflicts non-passing; two model runs must
  each pass. Freeze inputs, prompt, model configuration and outputs before scoring.
- Existing 14 examined cases are regression-only. Oracle anchors measure
  reconstruction, never autonomous discovery or marker placement.
- Up to three development revisions; stop after two without improvement.

## Implementation

1. Reuse source coordinates and inert draft semantics. Add a bounded semantic
   request/response boundary and deterministic quote/actor/order validation.
   Retain components and process each coordinate once per configuration.
2. Add an offline packet/replay harness: freeze cases, export extractor-only
   packets, import actual responses, run the control on identical evidence,
   freeze outputs, then expose gold to reviewers. Never fabricate missing runs.
3. Aggregate only independently judged outputs with explicit denominators,
   eligibility, lineage and completeness. Keep raw evidence outside Git.
4. Only after the gate passes, connect retained extraction to event polling and
   evaluate automatic discovery on separately annotated fresh streams.

Tests precede behavior changes. Synthetic adversarial cases validate mechanics;
they cannot substitute for fresh reviewed natural cases. Capture chronology,
attribution, conditional acceptance, unresolved references, source mutations,
malformed responses, repeated coordinates and unavailable inference are covered.

## Boundaries

Experimental hosted code only. No provider API integration, training, OAuth,
deployment, automatic promotion, or public raw transcript storage. Codex model
execution uses the existing service context, not fully local inference.
Root owns coordination, session records and integration; independent agents own
bounded implementation or review tasks. Preserve earlier reports and dirty worktrees.

## Authority and rationale

Builds on the evidence-first, inert-draft contract in mse_8kng1s965494hgsv:d1;
refines mse_ad9xz2f1kpyygw9b's retained-state and semantic-comparison contract.
Preserves the Constitution's evidence, attribution, edition authority and bounded
automation requirements. Semantic interpretation is an experimental comparison,
not a production provider selection or a change to memory authority.

Confirmed cause: narrow action/issue regexes gate outputs; message-wide tentative
or question detection suppresses candidates; spaCy features are diagnostic only.
Hypothesis: source-grounded semantic interpretation can recover natural phrasing
while conservative validation and review retain attribution and acceptance safety.
Effective failed-independent-hypothesis threshold: three.
