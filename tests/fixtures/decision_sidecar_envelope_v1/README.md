# DecisionSidecarEnvelope v1 golden cases

These fixtures freeze the M0 contract in
`docs/3_Spec/draft/decision-sidecar-envelope-contract.md`. M1 writer and fuse tests must use them without
changing their semantic outcome.

| Fixture | Expected result |
|---|---|
| `complete-write.yaml` | accepts one entry with write-time topic, link, diagram, and promoted ADR lens |
| `parallel-branches.yaml` | accepts and canonically orders non-overlapping branch records |
| `duplicate.yaml` | deduplicates byte-identical records |
| `divergent.yaml` | rejects one identity with different content |
| `missing-parent.yaml` | rejects a sidecar whose parent entry is not in base or source plan |
| `competing-adr-transition.yaml` | rejects two transitions from the same current ADR decision |
