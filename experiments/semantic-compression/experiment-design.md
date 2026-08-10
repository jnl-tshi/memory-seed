# Experiment design (Stage 1 measured; Stage 2 planned, not yet preregistered)

## Corpus and sampling

The source is the decision-granularity corpus returned by `memory_seed.retrieval.load_corpus` from Git
revision `54de83ca7f3e279f1199b721e6aa1bec825e04ac`, materialized with `git archive` into a temporary
directory. The generator checks the recorded corpus-manifest fingerprint before writing results.
Legacy entry-only chunks are excluded. A deterministic SHA-256 ordering selects 100 decisions while
round-robin sampling across text-length quintiles prevents a short-only convenience sample. The
dataset records corpus identity, source paths, line spans, dates, lengths, topics, and known lifecycle
fields. `relationship-pairs.json` records the exact labels, train/test split, and per-arm scores used to
reconstruct relationship metrics.

## Representations

All derived fields are verbatim source spans. No paraphrasing occurs in Stage 1:

1. `raw`: full decision text.
2. `core`: first sentence in `D:` (fallback: first sentence in the chunk).
3. `core_why`: core plus first sentence in `R:` when present.
4. `core_why_constraint`: core/why plus distinct sentences with explicit modality, negation, or
   scope markers.
5. `labeled_spans`: typed `claim`, `because`, and `constraint` labels applied to the same spans.

Constraints are drawn only from accepted `D:`/`R:` material; rejected `A:` alternatives cannot become a
constraint. This design isolates the value of selection and labels. The labeled-span arm is not a rich
semantic representation or an upper bound, and it does not claim extractive spans are optimal summaries.

## Stage 1 tasks

### Retrieval

The Stage 1 query is the decision heading with its `D<n> -` prefix removed, so this task is narrowly
**heading-derived findability**, not general paraphrase retrieval. The generated metrics record how
often the exact query occurs in raw text (currently 9/100); Stage 2 supplies independently worded
queries. To prevent metadata leakage,
ranking chunks have blank titles, heading paths, topics/tags, and lexical-term metadata; only
representation text is ranked.
Memory Seed's existing BM25F ranker runs with semantic and recency signals disabled. Report
Recall@1/3/5, MRR@all, nDCG@5, and token proxy.

### Relationship detection

Fully resolved authored decision edges with both source and target ordinals form positive pairs when
both ends are in the decision corpus. Unscoped and entry-level links are excluded rather than
projected onto sibling decisions. Deterministic same-date/topic
unlabeled candidates are preferred, making
them lexically harder than random pairs. Cosine TF-IDF similarity is the deliberately simple
detector. A temporal 70/30 split by sampled source (no source appears in both partitions) selects the
F1-maximizing threshold on train and reports precision, recall, F1, and apparent false-positive rate
on test. IDF is transductive over the full indexed corpus, matching Memory Seed's query-time setting.
This is **known-edge versus sampled-unlabeled discrimination**, not semantic relationship truth or
relation-type classification: missing authored edges are not proven negatives.

### Context efficiency

Report representation-body UTF-8 bytes divided by four as a transparent token proxy. This excludes
source-reference/provenance and fallback overhead, which Stage 2 must add before any build decision.
The composite is normalized:

`utility / relative_context`, where utility is MRR and relative context is mean arm tokens divided
by raw mean tokens. Raw measurements remain primary; the composite cannot override a fidelity fail.

## Stage 2 tasks (planned; not yet preregistered, required before production recommendation)

The measured `lean-draft-*` feasibility pilot is **not** this confirmatory Stage 2. It tests a derived
decision-block preview on 30 query/review targets, with model-assisted query authoring and fidelity
ratings. Queries were hash-pinned before ranking; the corpus was already revision/fingerprint pinned.
The selector hash was added after the first scored run, so it protects reproducibility now but cannot
substantiate a pre-outcome selector freeze. The candidate audit hid arm labels, but source matching and
candidate form made the raw arm recognizable. It does not test naturally authored drafts, human
readers, whole-entry size, or delayed recall. See
`lean-draft-design.md` and `lean-draft-results.md`.

- Blinded comprehension questions: decided, why, constraint, affected component, behavior change.
- Two independent fidelity judgments per item/arm: unsupported addition, omission, modality,
  certainty, scope, causality, terminology, contradiction hiding.
- Fixed model, prompt, decoding parameters, and randomized arm order.
- Human adjudication of disagreements and at least 20% double annotation.
- Any future richer representation must use the same model and source context as B-D.

Critical fidelity errors are unsupported additions or changes to modality, certainty, scope,
causality, negation, or contradiction status. Terminology simplification and non-critical omission
are reported separately. The proposed eligibility gates are:

- comprehension accuracy is non-inferior to raw within an absolute 5 percentage-point margin;
- critical fidelity-error rate is no more than 2 percentage points above raw;
- the paired 95% bootstrap confidence interval (10,000 resamples by decision) for each difference
  does not cross its non-inferiority margin;
- at least 20 decisions are double-annotated for all arms, with Cohen's kappa reported per binary
  fidelity category and all disagreements adjudicated blind to arm aggregate scores.

Semantic fidelity is a hard gate: an ineligible representation cannot win on efficiency.

The Stage 2 prompt, independently worded item set, model/version pin, decoding parameters, randomization
seed, annotation instrument, and adjudication protocol are not yet frozen. This section is a planning
contract, not a preregistration.

## Controls and limitations

- Canonical files are read-only.
- No production retrieval configuration changes.
- No sidecar or ontology is introduced.
- Stage 1 retrieval queries are mechanically derived and may favor wording preserved from headings.
- Existing links are authored historical relations, not exhaustive semantic gold; relationship
  precision/FPR are diagnostic labels against synthetic unlabeled candidates only.
- Stage 1 cannot establish human/agent comprehension or paraphrase fidelity.

## Existing overlap and architectural boundary

- `retrieval.load_corpus()` is the canonical reader because it applies link/topic sidecars and
  retractions; direct `extract_memory_chunks()` experiments are not suitable baselines.
- `MemoryChunk` already supplies decision identity, topics, and scoped decision edges.
- ADR Current views already provide approval-gated concise syntheses for standing architectural
  concerns. A generic persisted compression must not compete with that authority.
- If Stage 2 succeeds, the lowest-conflict first integration is an ephemeral retrieval/Evidence-Pack
  projection carrying the decision ref and exact source spans—not a new canonical or authoritative
  sidecar.
