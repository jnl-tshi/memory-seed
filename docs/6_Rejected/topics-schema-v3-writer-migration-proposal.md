---
tags:
  - proposal
  - topics
  - memory-seed
status: "rejected 2026-08-26 (JNL) - no observed second-project need"
priority: "n/a"
next_action: "none - revisit only if a real second-project signal appears (see closing note)"
---

# `topics.yaml` schema v3 writer / migration — scope and gap check

## Where this comes from

`memory_seed/topics.py` has read schema_version 3 (`area:`/`activity:` zone sections, children
nested by indentation, `axis`/`parent` derived from position rather than stated) since
`02b409cd` (2026-08-18, "topics: add recursive schema v3 reader"). A parallel, less complete
version of the same idea was drafted the same day an hour earlier on the abandoned
`claude/refactor/topics-yaml-v3` branch and was superseded before merge — see the session log
review that produced this doc. **The reader is done and shipped. No writer exists.**

This project's own `.memory-seed/topics.yaml` is already `schema_version: 3` — it was hand
migrated directly, because `topics.yaml` is deploy-once and this repo only has one copy to
convert. `topics.py` has never had a programmatic writer for the vocabulary file at all: every
topic the corpus has ever gained was added by a human or agent editing the YAML by hand (the
topic swarm skill only *suggests* candidate topics — see `.memory-seed/skills/topic_swarm.md`
§"Never write without this approval" — it never writes `topics.yaml` itself, and no CLI
subcommand beyond the read-only `topics list` touches the file).

So "the writer" is not a gap in this repo's own operation — it is a **feature that does not
exist yet for any project**: a `memory-seed topics migrate` command that converts another
project's v1/v2 `topics.yaml` into v3 without hand-editing. Whether to build it now is a scope
question, not an engineering blocker; see "Open decision" at the end.

## Gap check against the abandoned branch's interpretation

The branch that lost the merge (`05d7d998`) carried two ideas the shipped reader (`02b409cd`)
does **not** have. Both matter to a future writer, so they need an explicit decision rather than
silently reappearing or silently staying dropped:

1. **`derive_topic_label(slug)`** — the branch derived `label:` from the slug (hyphen-split,
   capitalized) whenever that reproduced the authored label byte-for-byte, and only kept an
   explicit `label:` for the 15 slugs (of 69) it couldn't reach. The shipped reader has **no**
   derivation: `_topic_record` reads `label` as a plain field, defaulting to `""` if absent — it
   never falls back to the slug. **Gap:** a v3 file produced by a naive writer that omits `label:`
   the way the branch intended would silently read every such topic with an empty label today.
   A writer must either (a) always emit an explicit `label:` for every node — the reader-symmetric,
   zero-risk choice — or (b) the reader gains its own derivation first, in which case the writer
   can omit it exactly where the branch did. **Recommendation: (a).** Label derivation is a
   nice-to-have compaction, not a correctness requirement, and the reader's current stricter
   contract (unknown detail keys are a parse `TopicIssue`, not silently accepted — see
   `_scan_v3_records`'s `unknown-topic-detail` check) suggests the shipped design leans toward
   "state everything explicitly, validate the shape" rather than "infer what's missing."
2. **`topics_equivalent(left, right)`** — the branch's slug-keyed before/after comparison,
   deliberately *not* positional (regrouping into zones legitimately reorders a file without
   changing its vocabulary). This does not exist anywhere in the shipped code. **Gap:** there is
   currently no reusable assertion that a migration lost nothing. A migration writer needs this
   exact building block — it must be re-authored against the shipped `TopicRecord`/`TopicIndex`
   shapes (the branch's version predates `TopicIssue` and the stricter v3 dataclass fields), not
   copied from the dead branch.

No other divergence changes writer scope: the shipped reader's zone/nesting model (2-space `- `
list items were rejected by the branch's design too; both agree axis and parent are structural,
never restated) matches what the branch intended.

## What the migration actually has to solve

Converting a v2 file (`axis:`/`parent:` fields already present, per `hierarchical-topic-vocabulary-proposal.md`'s
schema_version 2 step 1) into v3's zone/nesting shape is **mechanical**: group roots by their
existing `axis:` value into the corresponding zone section, nest children under their existing
`parent:` by indentation, drop the now-redundant `axis:`/`parent:` fields, emit `label:` for
every node per the recommendation above.

Converting a **v1** file (no `axis:`/`parent:` at all — everything flat) to v3 is **not**
mechanical: v3 requires every root to sit in a zone and nothing in a v1 file states which zone
a topic belongs to. That classification step is exactly what
`hierarchical-topic-vocabulary-proposal.md`'s "Build order" steps 1–2 already scope (declare axis
for every existing slug, reclassify aliases that are really children) as a *human-reviewed*
pass, not an automatic one. **A v1 file must go through that axis/parent declaration pass before
a v3 migration can run at all — `topics migrate` should refuse a bare v1 file rather than guess
zone membership, and point at that proposal's build order instead of guessing.**

## Proposed scope

1. **`memory-seed topics migrate schema-v3 [--dry-run]`** (new `migrate` subcommand family,
   alongside the existing `sessions-layout`/`sessions-month-layout` migrations in `cli.py`).
   - Input: a v2 file (`axis:`/`parent:` present on every relevant record). Refuses v1 input with
     a message pointing at the axis-declaration proposal; refuses a file already at v3 as a no-op
     rather than an error.
   - Output: a v3 file — zone sections in a stable order (`area` before `activity`, matching the
     existing convention), roots then children nested by their `parent:` chain, `label:` always
     explicit, `axis:`/`parent:` fields dropped.
2. **Re-author `topics_equivalent`** against the shipped `TopicRecord`/`TopicIndex`/`TopicIssue`
   shapes as the write gate: refuse to write unless `topics_equivalent(before, after)` reports no
   differences. This is the same shape of promise `session merge-branch`'s fuse dry-run makes
   before a structural write — prove nothing is lost before committing the new form.
3. **Round-trip test**: migrate a fixture v2 file, re-read the result with `load_topic_index`,
   assert zero `parse_issues` and `topics_equivalent` reports no differences against the
   original read. Add a second fixture covering the 15-slug label-mismatch case so an explicit
   `label:` survives migration unchanged even where it diverges from the slug.
4. **Idempotency test**: running migrate twice produces byte-identical output the second time
   (no-op on an already-v3 file, per above).
5. **Docs**: `hierarchical-topic-vocabulary-proposal.md`'s "Build order" gets a note that its
   step 1 (schema_version 2, flat axis/parent fields) is now a prerequisite stepping-stone to v3
   rather than a terminal state, once this ships.

Deliberately out of scope here: any *writer* for adding new topics one at a time (`topics add`).
Nothing in the current corpus or the topic-swarm skill calls for that — topics are added by hand
today, rarely, and one command replacing a rare hand-edit is not the problem this proposal
solves. If that changes, it is a separate proposal.

## Open decision

Is this worth building now? The only project that has ever needed a v1/v2 → v3 conversion is
this repo, and it already did that conversion by hand. The feature's actual audience is other
projects that deploy `memory-seed` and are still holding a v1/v2 file — an audience this repo
cannot directly observe. **Recommendation: park behind a real signal** (a second project
reporting hand-migration pain, or this project's own vocabulary work resuming under
`hierarchical-topic-vocabulary-proposal.md`'s still-open steps 2–7) rather than building it
speculatively. Recorded here so the scope exists and the two identified gaps (label derivation,
`topics_equivalent`) are captured before the branch that raised them is deleted.

## Closing note — REJECTED 2026-08-26 (JNL)

Ruled directly rather than parked: no migration tool is needed, because no other project
currently deploys `memory-seed` and needs the v1/v2 → v3 conversion, so building it has no
observed benefit. Moved to `6_Rejected/` as the record of *why not*. The scope and the two
gaps above (no label derivation in the shipped v3 reader, no shipped `topics_equivalent`
write-gate) remain accurate if a genuine second-project need ever surfaces later.
