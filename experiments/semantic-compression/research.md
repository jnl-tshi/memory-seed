# Focused research review

The practical lesson is to borrow evaluation ideas, not import a general semantic formalism.

| Method | What it extracts | Advantage | Limitation / complexity | Memory Seed relevance |
|---|---|---|---|---|
| Semantic Role Labeling | Predicate and argument roles | Compact predicate-argument structure | Pipeline errors propagate; modality, attribution, negation, and cross-sentence scope need explicit preservation | Useful only as a possible structured-arm feature |
| Open Information Extraction | Open-domain relation tuples | Schema-light propositions | Qualifiers, negation, modality, and context are frequent failure points | High-complexity diagnostic, not a minimum or oracle upper bound |
| Atomic fact / claim decomposition | Source-checkable propositions | Enables per-claim support checks | Scores are sensitive to the decomposition method itself; normative/modal claims are not simple facts | Directly motivates source-grounded fidelity checks |
| Argument mining | Claims, premises, and support/attack relations | Separates assertion from rationale | Domain adaptation and relation annotation are expensive | `D:`/`R:` provide candidate units, not an inferred support relation |
| RST / discourse relations | Relations between discourse units | Models rationale and elaboration | Multiple valid analyses and parser inconsistency | Too rich for the first experiment |
| DRT / formal discourse semantics | Discourse referents, conditions, scope, and reference | Handles cross-sentence reference and scope in principle | High formalism, parser, and maintenance cost | High-complexity diagnostic only; graph frameworks such as AMR are a separate family |
| Controlled natural language | Restricted, predictable prose | Human readable and machine friendlier | Requires authoring discipline or lossy rewriting | A compact source-grounded sentence may capture its benefit |
| Subject-action-object heuristic triples | Simple propositions | Cheap and interpretable | Deliberately lossy: modality, rationale, and multi-clause structure disappear | Useful diagnostic only; closely related to simple OpenIE tuples |
| Theme/rheme | Clause point of departure and its development | Offers a weak salience heuristic | Discourse-dependent; neither element guarantees the document's central contribution | Supports testing `core`, not adopting a schema |
| Natural Semantic Metalanguage | Explications using semantic primes and molecules | Cross-linguistic explanatory discipline | Requires manual analysis and a distinct linguistic-theory commitment | Unsuitable for automatic technical-memory normalization |
| Knowledge-graph proposition extraction | Canonical entities and typed, provenance-bearing relations | Supports graph queries | Requires identity resolution, relation vocabulary, provenance, temporal updates, and conflict handling | Explicitly outside scope unless simpler arms fail |

Key sources:

- Sadeddine, Opitz, and Suchanek, *A Survey of Meaning Representations – From Theory to Practical
  Utility* (NAACL 2024): compares formal frameworks and their practical ecosystems.
  <https://aclanthology.org/2024.naacl-long.159/>
- Min et al., *FActScore* (EMNLP 2023): decomposes text into atomic facts and scores support against
  evidence. <https://aclanthology.org/2023.emnlp-main.741/>
- Wanner et al., *A Closer Look at Claim Decomposition* (2024): shows factuality results can be
  sensitive to the decomposition method, so extraction error must not be attributed to the source.
  <https://arxiv.org/abs/2403.11903>
- Jindal et al., *PriMeSRL-Eval* (EACL 2023): demonstrates that stricter end-to-end SRL evaluation
  changes apparent quality and rankings because upstream errors propagate.
  <https://aclanthology.org/2023.findings-eacl.134/>
- Niklaus et al., *A Survey on Open Information Extraction* (COLING 2018): reviews proposition
  extraction and known evaluation limitations. <https://aclanthology.org/C18-1326/>
- Lawrence and Reed, *Argument Mining: A Survey* (Computational Linguistics 2019): covers claim,
  premise, and inference extraction. <https://aclanthology.org/J19-4006/>
- Kuhn, *A Survey and Classification of Controlled Natural Languages* (Computational Linguistics
  2014): characterizes the precision/expressiveness/naturalness/simplicity tradeoff.
  <https://aclanthology.org/J14-1005/>
- Zeldes et al., *eRST* (Computational Linguistics 2025): explains why discourse structures may be
  graph-like and multi-relational rather than a single clean tree.
  <https://aclanthology.org/2025.cl-1.3/>
- Kamp and Reyle, *From Discourse to Logic* (1993): the foundational detailed account of DRT.
- Halliday and Matthiessen, *Halliday's Introduction to Functional Grammar* (2014): source for
  Theme as point of departure and Rheme as development.
- Goddard, *Natural Semantic Metalanguage: The State of the Art* (2008): semantic explication uses
  a constrained metalanguage; subsequent NSM work includes both primes and semantic molecules. It
  is a theory-guided manual analysis, not a cheap automatic normalizer.
  <https://doi.org/10.1075/slcs.102.05god>
- Hogan et al., *Knowledge Graphs* (ACM Computing Surveys 2021): surveys graph construction,
  identity, schema, quality, and refinement concerns. <https://doi.org/10.1145/3447772>

LLM claim decomposition is an arm under evaluation, not reference truth. Stage 2 must score its
coverage, granularity, source entailment, and source-span traceability separately before using its
outputs to score any downstream task; decomposition error must be measured separately from source
support rather than attributed to the generated-text model.

Research conclusion: Memory Seed already has an unusually strong prior in its authored `D/R/A`
sections. The cheapest meaningful test is therefore a field-and-span ablation. Importing SRL, RST,
DRT, or a knowledge graph before that test would confound semantic value with infrastructure.
