# Identifier-lane score audit

## Frozen run

- Score commit: `8e4adb94f7d37306ac4f771320150cce9b2431ba`.
- Frozen corpus revision: `54de83ca7f3e279f1199b721e6aa1bec825e04ac`.
- Corpus fingerprint: `sha256:ab68ed673415ccf53cc9674476a6f0b49ec2f0cb782cfbc8a26d156d2a64ae00`.
- Target selection: `sha256:0fed7e7afb0e3d5bc599786e773c005cf46fd1a59068fe90b1bb65008ff3dfbc`.
- Selector: `sha256:06f7c52844a578066deb829948ff4d6611a81bb36ed636799bb7512ef28740a6`.
- Queries: `sha256:6bb711f0b3f87c675f624e0704d26c17a30eff4da160926b2aea825f5759ed22`.
- Review receipt: `sha256:940b5c05a233ce3bde0200cd3288740754ef117b80ce30b748daf1cf3244beea`.
- The score ran once into a new temporary directory. The raw outputs were copied into this directory
  without regeneration.

The completion manifest verifies:

- `identifier-lane-metrics.json`: `sha256:db850bad6b4e85033affd8d3b468ab8631c0995eec1ba762515c4ebd63fece92`.
- `identifier-lane-results.md`: `sha256:d33c8d5e90595f740765585b1184e88cfe7171ea287bbf67d8ae42319fafc9bc`.

## Instrument audit

The result is not another dead-treatment null.

- The synthetic raw-versus-normalized `rare_symbol.py` sensitivity control passed.
- Every exact-identifier query reached its target through the normalized current, authored, and union
  lexical fields.
- Normalized-current changed 12 full rankings and 31 target scores; normalized-authored changed 14
  full rankings and 31 target scores; normalized-union changed 18 full rankings and 31 target scores.
- Raw current lexical terms remained inert: zero lexical-field exposure and zero ranking or target-score
  changes, reproducing the normalization defect on fresh data.

The treatments therefore reached the shipped BM25F scorer and changed scores/orderings. They did not
change the target ranks used by MRR.

## Result

| Arm | Semantic MRR | Exact-identifier MRR | Full-order changes vs body |
|---|---:|---:|---:|
| Raw body only | 0.957 | 1.000 | 0 |
| Raw body + current terms | 0.957 | 1.000 | 0 |
| Raw body + normalized current terms | 0.957 | 1.000 | 12 |
| Raw body + normalized authored terms | 0.957 | 1.000 | 14 |
| Raw body + normalized union terms | 0.957 | 1.000 | 18 |

All normalized arms are mechanically classified `no-improvement`. Their exact-identifier MRR effect is
`0.000` against both controls with a `[0.000, 0.000]` paired interval. Semantic MRR is unchanged and
passes the non-inferiority gate.

## Interpretation

The exact-identifier task saturated: body BM25 ranked all 30 targets first without a lexical side field.
That is consistent with the complete canonical body containing the source-authored identifier used in each
query, but this run did not include an identifier-masked control that isolates the cause. The normalized
fields added score and ordering information below the target but could not improve an already perfect
target rank.

This establishes a narrow result: **on this 100-decision frozen corpus, adding normalized identifier
fields does not improve retrieval when the complete raw decision body is ranked and the query contains an
exact source identifier**. It does not establish that identifier fields are useless for much larger
corpora, truncated/bodyless indexes, aliases, misspellings, or identifier-free paraphrases.

No production normalization change is justified by this run. The defect is real, but fixing it adds no
measured user-facing retrieval benefit on the tested current surface.

## Cumulative decision

Together with the earlier front-door runs:

- automatic compact selection had a lower semantic-MRR point estimate and failed its non-inferiority
  margin; a same-model, arm-label-hidden audit with recognizable raw text also flagged critical fidelity
  errors, so that finding is not human-reader evidence;
- the safer verbatim D/R/A front door retained 97.8% of answer spans (all required spans for 96.7% of
  queries) but missed its 20% median context reduction gate, and query-specific evidence cost more
  context without adding oracle answer-span coverage, although it did improve exact query-identifier
  visibility from 17/20 to 20/20;
- normalized identifier fields changed the scorer but did not improve target retrieval over the raw body.

The first two diagnostics reused the same 30-target development set. Only the identifier-lane diagnostic
used a fresh entry-disjoint target/query holdout, so these are complementary ablations rather than three
independent replications.

The useful carry-forward is therefore conservative: keep the complete DRAFT decision canonical and
rankable, preserve exact identifiers in authored evidence, and pursue smaller drafts through natural
authoring discipline and a future human comprehension/recall test—not automatic semantic deletion or a
new production sidecar.
