# ADR campaign S1 - findings

Ran 2026-08-06/07. Goal: put this project where `bootstrap` would have put it - one living ADR per
architectural concern, bound to the Constitution, with index and policy demoted to maps that point
at them.

## Outcome

| | count |
|---|---|
| Concerns enumerated (control-file harvest) | 34 |
| ADRs written by the campaign | 34 (+1 proven in Phase 0) |
| Corpus total | 38 (3 pre-existing, untouched) |
| Status: accepted / rejected | 36 / 2 |
| Founding-sourced (control-file line) | 34 |
| Carrying >=1 governing constitution binding | 35 |
| Session decisions attached as evidence | 24 |
| Index bullets carrying an ADR pointer | 21 |
| Policy rules carrying a governing-ADR pointer | 8 |

The 2 rejected are decided-and-rejected history recorded deliberately - topology-community
detection (measured and closed) and the scored topic auto-backfill (piloted twice, aborted). An
ADR corpus that only records what was adopted loses exactly the reasoning most likely to be
re-litigated.

## The free baseline was recorded, and it lost

Bar set before any spend: *one ADR per lifecycle chain, title = newest decision's title, no model
calls.* Connected components over evolves/replaces (filtered to edge_confidence >= 0.7) produced
**27 chains, dominated by a single 293-entry component** - the corpus is too densely linked for
components to segment concerns. The control-file harvest wins on face validity. Recording this
matters more than the result: it is the same "define the free baseline before spending tokens"
discipline that correctly killed the first topic-swarm gate at 0.613 vs a 0.52 constant guess.

## The pilot gate fired, and the diagnosis was the point

Run 1 - 4 haiku workers, brief v1, 34 concerns:

- **22/34 ADRs survived (65%)**
- **2/17 attachments survived (12%)**

Both failure modes were **defects in my brief, not worker failure**:

1. **6 drops: constitution slugs used as topics.** The brief rendered both vocabularies into one
   payload with identical shape, so `authority`/`provenance`/`append-only` landed in `topics:`.
2. **6 drops: quote tails drifted.** Every failed `source_quote` matched the file exactly for its
   opening clause and diverged later - long quotes wrap across lines and get mis-transcribed.
3. **15 attachment drops**, mostly invented or truncated entry ids (`mse_42e8zzd7`, 8 chars where
   real ids are 16). Workers were recalling refs rather than reading them.

Run 2 - brief v2 (vocabularies separated, quotes capped at 40-120 chars within one line, and
**verified candidate refs rendered into each payload**), opus workers, the 12 dropped concerns:

- **12/12 ADRs survived**
- **20/20 attachments survived**

**This is not a haiku-vs-opus measurement.** Three things changed at once - model tier, brief, and
the closed candidate-ref list. The confound is real and no model-tier claim can be drawn from it.
If the comparison matters later, re-run brief v2 on haiku; my read is that the candidate-ref list
did most of the work, because "recall an entry_id from memory" is the exact task small models were
failing and the exact task that list removes.

One worker died mid-run on a session limit; its 6 concerns were drafted by the orchestrator and
put through the identical validator (6/6, 8/8 attachments). Recorded because their provenance
differs from the rest even though the gate did not.

## Validator decisions worth knowing

Two refinements over a flat drop-everything rule, both applied deliberately:

1. **The unit of judgement is (concern, claim).** Each ADR has ONE core claim, grounded by
   `source_quote` and mandatory, plus 0-3 optional attachments. An ungrounded attachment drops
   alone; an ungrounded core drops the ADR. Precedent: the link campaign dropped 142 ungrounded
   edges individually rather than voiding whole worker batches.
2. **`#L<n>` on `source_file` is notation, not substance** - stripped (9 cases), with the bare path
   still required to be an assigned source. Precedent: the link campaign normalised 117 redundant
   ordinals rather than dropping them.

## Map sync

- **6 index bullets thinned** to descriptive pointers (one-line digest + ADR link).
- **23 refs appended** without thinning: policy rules keep their text inline by design (policy is
  Always Read and must stay self-sufficient), and index bullets over 400 chars are likely bundling
  decisions no ADR covers - thinning those would silently drop the uncovered ones.
- **3 unresolved**: `adr_experiment_isolation`, `adr_topic_vocabulary`, `adr_worktree_convention`.
  Their grounding quotes span line wraps, so no single bullet matched uniquely. Left untouched -
  drop-never-repair applies to my own sync too. These need a hand pass.

The bundling limit is the honest constraint here: the index is only ~19% thinned. Finishing the
job means splitting bundled bullets, which is a judgement pass, not a mechanical one.

## Gates

`adr check`, `links check` (158 files), `topics check`, `docs check` all green. Full suite
1086 pass. The three sha256-pinned ADRs byte-unchanged, verified against `real-current.json`.

One test needed correcting: `test_live_adrs_have_no_extension_fields` globbed every live ADR and
asserted none carried the new fields - true when only the three pre-extension records existed,
wrong once the campaign wrote 35 that legitimately use them. Rescoped to the pinned three, which
is where the omit-empty guarantee actually binds.

## What this leaves for S2-S4

- **S2**: the lineage-linked review gate already exists. The gap is relevance surfacing for
  decisions with no lifecycle link, plus new-ADR proposal at write time. 35 topic-tagged, bound
  ADRs are the input that makes matching possible.
- **S3**: `bootstrap` founds Constitution + ADRs on a fresh project. The founding-source mechanism
  was built for this, not for the backfill - a new project has no session corpus at all.
- **S4**: ESR reads `constitution_refs` off the ledger via `iter_adrs` and audits them against the
  anchors. Both halves now exist to compare.

## Cost this creates

Every future lifecycle-linked session write now hits the mandatory zero-write ADR review gate,
because 38 ADRs claim membership over a growing share of the corpus. That is the living-document
design working as specified - but it is a real, permanent friction change for every session from
here, and it started the moment these were accepted.
