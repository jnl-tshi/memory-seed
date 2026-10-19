# Hosted import inventory and crosswalk

R0 freezes the source vocabulary that the hosted PostgreSQL import must preserve before schema work begins. The inventory is evidence, not a second authority: the local edition remains Markdown-authoritative until a later, explicit cutover gate.

## Artifacts

- `inventory.json` records the 2.24.0 release-checkpoint census: 108 session files, 1,290 session headings, 67 living ADRs with 290 events, 1,489 link assertions, 1,183 topic assertions, 117 diagram assertions, 30 Constitution clause anchors, and 115 archived files. It also records the complete observed field and actor vocabularies.
- `crosswalk.yaml` is JSON-compatible YAML. Every observed field has an explicit authority classification and PostgreSQL destination. Structural containers are the only entries allowed to have no column target.
- `actors.yaml` keeps member identity, agent identity, authorship, provenance source, and legacy display labels separate. The legacy `USER` placeholder is preserved but cannot grant access.
- `inventory.py` rescans live Markdown using the repository's canonical session-layout iterator and a dependency-free lexical block reader. The lexical reader intentionally accepts historical sidecars containing unquoted colons that generic YAML parsers reject.
- `tests/fixtures/hosted_import/manifest.json` hash-locks representative typed, legacy, sidecar, ADR, topic, Constitution, actor, and archive fixtures.

## Authority-sensitive mappings

- Session decisions become immutable records and versions; raw Markdown and source coordinates remain available for provenance.
- ADR event ledgers map to append-only `adr_events`; the current ADR view is classified as a derived projection.
- Topic sidecars map to `topic_assertions`. Inline session topics are retained only as superseded authored metadata and cannot become topic authority.
- Relationship provenance and evidence map with the assertion, and derived assertions cannot silently supersede write-time assertions.
- Archives map to immutable `project_artifacts` and never enter live authority merely because they were discovered.

Run the R0 contract check with:

```text
python -m pytest tests/hosted/test_import_inventory.py -q
```

The suite also injects an unknown metadata field and proves that validation rejects it. This guards against a false green result from an incomplete detector.
