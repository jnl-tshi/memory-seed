# 3_Spec/draft — candidate specs (not yet binding)

Draft and candidate contracts. **Only specs in `3_Spec/` (the parent) are normative** and binding on
code; anything here is proposed-for-adoption and must not be treated as authoritative yet. On adoption a
spec moves up to `3_Spec/`; if abandoned it goes to `6_Rejected/`.

**Required YAML:** `spec_binding: draft` or `candidate`.

**Contents physically here:**

- `adr-lifecycle-sidecar-contract.md` - candidate append-only ADR promotion/lifecycle sidecar;
- `derived-read-model-projection-contract.md` - candidate local projection contract;
- `memory-trace-hosted-markdown-settlement-contract.md` - candidate hosted settlement/rebuildability gate;
- `provenance-authority-crosswalk.md` - BG1 steps 1-2: the provenance/authority field inventory and alias
  map. Blocked on one user decision (the shipped `authority_class` value disagrees with the proposed
  vocabulary, and correcting it is a v1 contract break).

Two specs currently in `3_Spec/` are also candidates and are marked `spec_binding: candidate` in place;
they move here in Phase 2 (moving them now would break ~15 inbound links, batched into the P2 path sweep):
- `memory-trace-trail-search-and-graph-ux.md`
- `memory-trace-derived-artifact-provenance-contract.md`
