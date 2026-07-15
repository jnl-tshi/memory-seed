---
title: "Memory Trace Structural Graph Enrichment Provider Proposal"
date: "2026-07-15"
project: "memory-seed"
status: "promoted-to-todo"
priority: "P1"
recommended_target: "docs/2_Todo/memory-trace-structural-graph-enrichment-provider-proposal.md"
related:
  - "docs/2_Todo/memory-trace-product-and-system-architecture-blueprint.md"
  - "docs/2_Todo/memory-trace-next-generation-implementation-roadmap.md"
  - "docs/3_Spec/graph-edge-contract.md"
  - "docs/2_Todo/memory-trace-graph-visualisation-and-temporal-topology-proposal.md"
  - "docs/2_Todo/memory-provenance-and-authority-taxonomy-proposal.md"
---

# Memory Trace Structural Graph Enrichment Provider Proposal

Status: **PROMOTED to `2_Todo`** 2026-07-15 (active, but sequenced after native graph/workspace foundations).
Priority: P1 as a Memory Trace direction; optional tail after native B0b acceptance.
Source: Downloaded proposal set supplied by JNL on 2026-07-15.
Next action: Defer implementation until B0a contracts and B0b native graph/workspace implementation are accepted; then define the provider-neutral contract and pilot `code-review-graph` as optional enrichment.

## 1. Executive decision

Memory Trace should introduce an optional, provider-neutral structural-code graph enrichment layer.

The recommended initial provider is **code-review-graph**, integrated as an external derived projection rather than a canonical Memory Seed dependency.

The strategic ordering is:

1. finish the native Memory Seed graph experience using canonical memory and Git relationships;
2. define a stable `StructuralGraphProvider` contract;
3. pilot code-review-graph as the first production candidate;
4. retain Graphify as a visual and extraction benchmark rather than the default provider;
5. evaluate SCIP later as a compiler-accurate precision provider;
6. build a native Tree-sitter implementation only if packaging, stability, or strategic-control evidence justifies the maintenance cost.

The integration must preserve one authority rule:

> External code graphs provide derived observations about repository structure. They never redefine or silently mutate Memory Seed’s authored decision graph.

## 1.1 Constitutional fit

Five-question contribution:

- **Retrieval:** links decisions and commits to bounded file, symbol, dependant, and test evidence.
- **Validation:** contract fixtures, revision checks, comparison pilots, confidence classes, and failure-mode tests gate provider adoption.
- **Trust:** every structural claim exposes provider, version, revision, confidence, authority class, and source location.
- **Application:** supports evidence inspection and impact analysis without turning Memory Seed into a code-intelligence platform.
- **Capture is explicitly excluded:** provider observations never create authored entries or canonical lifecycle edges.

Invariant guards: providers are optional and offline-capable where supported; Memory Seed remains fully usable without them; provider stores are disposable projections; external identities are namespaced; provider data cannot alter canonical ranking until exposed and real-corpus validated; and failures degrade to the native graph.

## 2. Problem and opportunity

Memory Trace currently explains project evolution through entries, decisions, topics, branches, commits, lifecycle relationships, and documents. It does not yet provide a strong structural bridge from a decision to the code entities that implement it.

The desired enriched path is:

```text
Decision
  → implemented_by → Commit
  → changes → File
  → contains → Symbol
  → calls / imports / implements → Symbol
  → tested_by → Test
```

This enables workflows that a generic memory graph cannot answer alone:

- Which code implements this decision?
- What depends on the changed symbols?
- Which tests cover the implementation?
- Which architectural subsystem does the work belong to?
- Which parts of the codebase changed without explanatory memory?
- Which old decisions refer to files or symbols that no longer exist?

The enrichment layer should improve the graph, inspector, Evidence Packs, link suggestions, and impact analysis without turning Memory Seed into a general code-intelligence platform.

## 3. Authority boundaries

### 3.1 Memory Seed remains authoritative for

- authored memory entries;
- decisions and deterministic anchors;
- `related_entries`;
- `supersedes` and `superseded_by`;
- `evolves` and `evolved_by`;
- topics and controlled vocabulary;
- continuity mappings;
- branch labels;
- commit references;
- project participants and authority;
- append-only annotations.

### 3.2 Git remains authoritative for

- commits;
- branches and merge relationships;
- changed paths;
- revision identities;
- commit timestamps;
- repository-relative history.

### 3.3 Structural providers supply derived observations for

- files;
- classes, functions, methods, interfaces, and other symbols;
- containment;
- imports;
- calls;
- inheritance;
- implementations;
- references;
- dependency injection;
- tests and test relationships;
- execution flows;
- impact radius;
- code communities.

### 3.4 Memory Trace owns the projection join

Memory Trace joins canonical and provider-derived data into a read model. It must preserve authority and provenance on every node and edge.

## 4. Candidate evaluation

### 4.1 code-review-graph

#### Strengths

- Python implementation aligns with Memory Seed’s runtime.
- SQLite-backed persistent graph aligns with Memory Trace’s projection architecture.
- Uses directed graph semantics.
- Provides typed nodes for files, classes, functions, types, and tests.
- Provides typed edges including calls, imports, inheritance, implementation, containment, testing, references, and dependencies.
- Records file path, source line, confidence, confidence tier, and update time.
- Supports incremental file-hash-based updates.
- Supports impact radius and subgraph extraction.
- Broad language support through Tree-sitter parsers.
- Can operate locally without an external graph database.

#### Weaknesses

- It is a product and internal schema, not a stable graph interchange standard.
- Qualified identities currently include absolute paths and must be normalised.
- Cross-file call resolution may be heuristic.
- Its wider MCP, review, risk, and wiki features exceed Memory Trace’s immediate need.
- Upstream schema and behaviour may change.

#### Conclusion

Best first provider because its architecture and use cases most closely match Memory Trace’s local, derived, incremental graph needs.

### 4.2 Graphify

#### Strengths

- Simple graph export.
- Broad source coverage.
- Tree-sitter extraction for code.
- Community detection and reports.
- Explicit confidence classes such as extracted and inferred.
- Strong standalone visualisation using vis-network.
- Useful for rapid proof of concept.

#### Weaknesses

- Internal analysis uses an undirected NetworkX graph.
- Broad document and rationale extraction overlaps with Memory Seed’s authoritative domain.
- Generic concept identities are less suitable for stable revision-aware code links.
- Multimodal and document processing can introduce model-provider and privacy considerations.
- Its graph semantics are broader and less precise than the desired code-only enrichment layer.

#### Conclusion

Retain as a prototype, UX benchmark, and comparative adapter. Do not select it as the default production provider.

### 4.3 SCIP

#### Strengths

- Language-agnostic index protocol.
- Compiler or language-server-derived definitions, references, and implementations.
- Strong source ranges and symbol identities.
- High precision for supported languages.

#### Weaknesses

- SCIP is an index format, not a complete graph product.
- Requires language-specific indexer orchestration.
- Does not directly provide community detection, impact analysis, or a complete call graph in every language.
- Adds operational and packaging complexity.

#### Conclusion

Use later as a precision provider for selected languages, particularly where Tree-sitter name resolution proves insufficient.

### 4.4 Native Tree-sitter provider

#### Strengths

- Full control over identities and schema.
- Exact alignment with Memory Trace’s provider contract.
- No dependency on an external project’s internals.
- Can remain narrowly scoped.

#### Weaknesses

- Tree-sitter parsing is only the beginning.
- Requires language-specific extraction queries, import resolution, call resolution, incremental invalidation, grammar packaging, testing, and long-term maintenance.
- Risks diverting effort from Memory Trace’s differentiated decision and evidence workflows.

#### Conclusion

Keep as a strategic fallback, not the first implementation.

### 4.5 Codebase-Memory and related research systems

These are useful architecture and evaluation references, particularly for persistent code graphs, community discovery, and token-efficient agent navigation. Current maturity and integration stability are insufficient for the first production dependency.

## 5. Provider-neutral architecture

```text
Memory Seed canonical services
  entries
  decisions
  topics
  lifecycle graph
  commit references
          |
          v
Memory Trace graph projection
  canonical nodes and edges
  Git evidence
  provider joins
  freshness and provenance
          ^
          |
StructuralGraphProvider
  code-review-graph
  Graphify adapter
  SCIP adapter
  future native provider
```

The frontend must never query a provider-specific database directly.

## 6. StructuralGraphProvider contract

Recommended conceptual interface:

```text
StructuralGraphProvider
  provider_info()
  status(repository, revision)
  build(repository, revision, scope)
  update(repository, revision, changed_paths)
  nodes(scope, filters)
  edges(scope, filters)
  neighbourhood(node_id, depth, edge_types)
  impact(node_ids_or_paths, depth, limits)
  search(query, node_types, limit)
  close()
```

### 6.1 Provider status

```text
provider_id
provider_version
schema_version
status: unavailable | building | current | stale | partial | failed
indexed_revision
current_revision
indexed_at
changed_paths_since_index
supported_languages
warnings
```

### 6.2 Node model

```text
id
namespace
node_type
label
qualified_name
repository_relative_path
source_range
language
provider
provider_version
repository_revision
authority_class
confidence
observed_at
stale
attributes
```

### 6.3 Edge model

```text
id
source
target
edge_type
directed
provider
provider_version
repository_revision
authority_class
confidence
confidence_tier
source_path
source_range
evidence_refs
observed_at
stale
attributes
```

## 7. Stable identity model

External provider identities must be converted into Memory Trace-owned namespaced identifiers.

Examples:

```text
memory:entry:<entry_id>
memory:decision:<anchor_id>
git:commit:<sha>
code:file:memory_seed/retrieval.py
code:symbol:memory_seed/retrieval.py::search
provider:github:pr:<number>
```

Absolute paths must never become durable graph identities.

Normalisation rules:

1. resolve the repository root;
2. convert paths to repository-relative POSIX form;
3. retain provider-qualified symbol names in attributes;
4. build Memory Trace identity from relative path, symbol kind, and provider-stable qualification;
5. record the indexed revision separately;
6. maintain aliases for continuity mappings and detected renames where evidence exists.

## 8. Revision and freshness model

A structural graph represents a particular repository state. It must never be presented without revision context.

Required display state:

```text
Code graph revision: main@a81f25c
Current revision: main@b7639de
Status: stale
Changed paths since index: 17
```

Initial supported scopes:

- current working tree;
- current `HEAD`;
- selected branch head;
- selected pull-request head.

Historical graph reconstruction should be deferred. When a user selects an old decision, the UI must explicitly distinguish:

```text
Decision date: 2026-02-11
Displayed code graph: current HEAD
Historical structural snapshot: unavailable
```

## 9. Confidence and provenance

Provider edges must remain visibly distinct from authored Memory Seed relationships.

The canonical crosswalk and actionability rules are owned by
[`memory-provenance-and-authority-taxonomy-proposal.md`](memory-provenance-and-authority-taxonomy-proposal.md).
This proposal supplies provider-specific candidates; it must not create a parallel trust vocabulary.

Suggested authority classes:

```text
authored
computed_canonical
git_derived
provider_extracted
provider_resolved
provider_inferred
generated
```

Suggested styling:

| Authority | Appearance |
|---|---|
| Authored Memory Seed edge | Strong semantic colour, solid |
| Canonical computed inverse | Strong semantic colour, lighter |
| Git-derived link | Solid neutral or Git-specific style |
| Provider extracted | Solid, medium opacity |
| Provider resolved heuristic | Solid or lightly dashed, confidence shown |
| Provider inferred | Dashed, lower opacity |

Provider confidence must not alter Memory Seed’s canonical `importance_score` until it has been exposed, measured, and validated against fixtures.

## 10. Provider scope and exclusions

The first provider integration should be code-only.

Include:

- application source;
- tests;
- schemas;
- infrastructure definitions;
- configuration where parser support is meaningful.

Exclude by default:

- `.memory-seed/`;
- session files;
- decision sidecars;
- generated reports;
- build outputs;
- vendored dependencies;
- virtual environments;
- lockfile internals unless specifically required;
- binary and media files.

This prevents duplication of Memory Seed concepts and limits unnecessary indexing cost.

## 11. Installation and dependency isolation

The provider must remain optional.

Recommended options:

### External detection

Memory Trace detects whether a compatible provider command or package is available and offers setup guidance.

### Optional extra

```text
pip install "memory-seed[trace-codegraph]"
```

The default `memory-seed[trace]` installation should not inherit the provider’s dependencies.

Provider version must be pinned within a supported range, and adapter contract fixtures must detect breaking changes.

## 12. Storage model

Provider databases remain separate from Memory Trace’s own projection.

```text
~/.cache/memory-trace/<project>/trace.sqlite
~/.cache/memory-trace/<project>/providers/code-review-graph.sqlite
~/.cache/memory-trace/<project>/provider-state.json
```

Rules:

- no provider database is authoritative;
- databases remain outside the repository by default;
- deletion degrades to rebuild;
- provider migrations never rewrite Memory Seed Markdown;
- provider corruption cannot remove authored memory;
- stored revisions and provider versions are mandatory.

## 13. Initial enriched workflows

### 13.1 Decision-to-implementation

```text
Decision
  → Commit
  → Changed file
  → Changed symbol
  → Neighbouring symbols
```

This is the highest-priority workflow.

### 13.2 Impact lens

For selected files or symbols, show:

- callers;
- callees;
- imports;
- dependants;
- implementations;
- affected tests;
- community;
- related decisions and commits.

### 13.3 Decision coverage diagnostics

Expose diagnostics such as:

- highly connected code with no linked decision history;
- major decisions with no implementation evidence;
- files repeatedly changed without explanatory memory;
- outdated decisions referencing removed artifacts;
- code communities with little or no documentation.

These remain suggestions and diagnostics, not silent graph mutations.

### 13.4 Drift detection

Combine continuity and provider data to flag:

- renamed files referenced under old paths;
- removed symbols referenced by active decisions;
- superseded implementation still linked as current;
- new replacement code without a corresponding evolution or supersession record.

### 13.5 Code-aware link suggestions

Potential evidence signals:

- shared file;
- shared symbol;
- same code community;
- caller and callee relationship;
- same affected test surface;
- same commit or pull request.

Suggestions must require explicit author action before becoming Memory Seed relationships.

### 13.6 Evidence Packs

Allow Evidence Packs to include bounded structural subgraphs:

```text
Decision → Commit → File → Symbol → Dependants → Tests
```

Every material structural claim must cite provider, revision, and source location.

## 14. Integration with topology and time

Provider-derived code communities can enrich topology colouring, but Memory Trace remains responsible for community labels and colour stabilisation.

Temporal values for code nodes should be Git-derived:

- last relevant change at selected revision;
- introduction commit where available;
- provider observation time as a freshness field, not the semantic code date.

Code nodes should participate in temporal drift only when their date semantics are known and displayed.

## 15. Initial provider adapter scope

The code-review-graph adapter should initially expose only:

### Node types

- File;
- Class;
- Function or method;
- Type or interface;
- Test.

### Edge types

- `CONTAINS`;
- `CALLS`;
- `IMPORTS_FROM`;
- `INHERITS`;
- `IMPLEMENTS`;
- `TESTED_BY`;
- `REFERENCES` where confidence is sufficient.

Defer:

- embeddings;
- generated wiki content;
- refactoring actions;
- risk scoring;
- autonomous writes;
- provider-specific visualisation;
- provider-specific MCP features not required by Memory Trace.

## 16. API strategy

Recommended versioned resources:

```text
GET /api/v1/providers
GET /api/v1/providers/{provider_id}/status
POST /api/v1/providers/{provider_id}/index
GET /api/v1/structural/nodes
GET /api/v1/structural/edges
GET /api/v1/structural/neighbourhood/{node_id}
POST /api/v1/structural/impact
GET /api/v1/graph/projection
```

The primary Graph view should consume a merged projection endpoint rather than assembling canonical and provider graphs in React.

## 17. Testing strategy

### Contract fixtures

- provider status fixture;
- node fixture;
- edge fixture;
- stale index fixture;
- unsupported language fixture;
- provider unavailable fixture;
- path normalisation fixture;
- revision mismatch fixture.

### Repository fixtures

Use small repositories containing:

- direct calls;
- ambiguous same-name functions;
- cross-file imports;
- inheritance and interfaces;
- tests;
- renames;
- deleted files;
- multiple languages;
- generated files and excluded directories.

### Comparison pilot

Run code-review-graph and Graphify over the same representative repositories and compare:

- extraction completeness;
- false relationships;
- path and symbol stability;
- incremental update time;
- adapter complexity;
- provider failure behaviour;
- graph usefulness in the Memory Trace UI.

SCIP can be added to the comparison for supported languages where precision matters.

## 18. Implementation phases

This provider tail begins only after native B0b graph/workspace acceptance. It is not part of the pre-React B0a gate and cannot block the local canonical graph.

### Phase A — provider contract

- define provider models;
- define authority and confidence classes;
- define path and identity normalisation;
- add provider status UI;
- create contract fixtures.

### Phase B — code-review-graph pilot

- implement external process or library adapter;
- index representative repositories;
- expose file and symbol neighbourhoods;
- keep feature behind a flag.

### Phase C — decision-to-code join

- join decisions to commits;
- join commits to changed paths;
- resolve paths to provider file and symbol nodes;
- expose revision and confidence.

### Phase D — impact and Evidence Packs

- add impact endpoint;
- show affected tests and dependants;
- add bounded structural evidence to Evidence Packs.

### Phase E — comparative provider spike

- implement minimal Graphify adapter;
- evaluate SCIP for Python and TypeScript or other priority languages;
- document quality and operational differences.

### Phase F — production decision

- select supported provider set;
- define compatibility policy;
- decide whether a native fallback is justified;
- publish installation and privacy documentation.

## 19. Acceptance criteria

- Memory Trace works fully without any structural provider.
- Provider installation remains optional.
- Memory Seed canonical graph semantics remain unchanged.
- External nodes and edges expose provider, version, revision, confidence, and source location.
- Absolute filesystem paths do not become durable identities.
- Stale indexes are visibly marked.
- Current code graphs are not presented as historical snapshots.
- Decision-to-commit-to-file-to-symbol navigation works for representative fixtures.
- Impact results include bounded dependants and tests.
- Provider failures degrade gracefully to the native graph.
- Provider-derived evidence never silently creates authored Memory Seed edges.

## 20. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Upstream schema changes | Adapter boundary, pinned compatibility range, contract fixtures |
| Absolute-path instability | Repository-relative namespaced IDs |
| Heuristic false call edges | Preserve confidence tier and source evidence |
| Provider becomes mandatory | Optional installation and graceful absence |
| Current graph mistaken for historical code | Revision banner and explicit snapshot status |
| Duplicate document concepts | Code-only indexing scope and `.memory-seed` exclusion |
| Index becomes stale | Revision comparison and provider status |
| Provider feature creep | Restrict first adapter to nodes, edges, neighbourhood, and impact |
| Privacy or model leakage | Prefer local deterministic code extraction and document exclusions |

## 21. Final recommendation

Use code-review-graph as the first optional structural enrichment provider behind a Memory Trace-owned contract.

Graphify should inform the visual design and remain a useful comparison adapter. SCIP should be evaluated later for compiler-accurate symbol evidence. A native implementation should remain a fallback rather than an immediate commitment.

This approach gives Memory Trace a practical structural graph quickly while protecting the project’s core differentiation: inspectable, typed, evidence-linked project memory rather than generic code intelligence.
