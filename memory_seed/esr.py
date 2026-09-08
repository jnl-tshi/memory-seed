"""End-of-session-routine mechanical preflight (``memory-seed esr``).

One read-only pass over every deterministic end-of-turn check, so the routine
costs one command instead of a dozen exploratory calls, and a skipped step is
impossible to hide: every section prints even when clean. Judgment stays with
the agent - this reports, it never fixes.

Sections:
- integrity: ``links check`` (the only section that can fail the exit code)
- topics: controlled-vocabulary check
- link_gaps: ``link audit`` scoped to the session date (lifecycle sweep input)
- worktrees: per-worktree branch / commits-ahead-of-integration / dirty count
  (stale-sweep candidates are the merged-and-clean ones), plus physical agent
  worktree directories that Git no longer registers
- seed_twins: live skill vs ``memory_seed/seed`` twin drift - only meaningful
  in the control-plane development repo itself, where the twins ship from;
  ordinary projects adapt their live skills freely and are never flagged.
- adr_sweep_candidates: same-area decision-lineage chains with missing ADR
  coverage, each carrying an advisory recommendation for human review
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

SESSION_DATE_IN_PATH_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\.md$")
DECISION_ORDINAL_RE = re.compile(r"d\d+")

from .core import check_session_links, read_integration_mode, read_merge_trigger, resolve_runtime
from .corpus_cache import CorpusSnapshot, inspect_corpus_cache
from .topics import check_topics, load_topic_index


@dataclass(frozen=True)
class WorktreePosture:
    path: str
    branch: str | None
    ahead: int | None
    dirty: int | None
    is_primary: bool

    @property
    def stale_candidate(self) -> bool:
        return not self.is_primary and self.ahead == 0 and self.dirty == 0


@dataclass(frozen=True)
class WorktreeResidue:
    path: str
    namespace: str
    git_file_present: bool


@dataclass
class EsrReport:
    session_date: str
    integration_mode: str = "local-merge"
    merge_trigger: str = "automatic"
    integrity_ok: bool = True
    integrity_issues: list[str] = field(default_factory=list)
    topics_ok: bool = True
    topics_issues: list[str] = field(default_factory=list)
    link_gaps: list[dict[str, Any]] = field(default_factory=list)
    open_link_stubs: int = 0
    # Backlog AGE, not just size. Both sweeps below find work every session but
    # only a deliberate campaign clears it, so a raw count reads as steady state
    # while the oldest item quietly rots - the link backlog cleared on
    # 2026-08-07 had been accumulating since 2026-07-21 and nothing said so.
    # Deliberately a count plus a date and NO verdict, for the same reason
    # `diagram_*` below is a count: the threshold at which a backlog earns a
    # campaign depends on cost and corpus state this report cannot see.
    oldest_open_link_stub: str | None = None
    topic_attribution_gaps: int = 0
    oldest_topic_attribution_gap: str | None = None
    # Vocabulary REQUESTS awaiting adjudication: `proposed_topic` values written
    # at decision granularity. They are never topics and cannot become one by
    # being used, so the only way they ever get considered is by being surfaced
    # here with the decision that asked as evidence.
    proposed_topics: list[str] = field(default_factory=list)
    worktrees: list[WorktreePosture] = field(default_factory=list)
    worktree_residues: list[WorktreeResidue] = field(default_factory=list)
    worktrees_available: bool = False
    seed_twins_checked: bool = False
    seed_twin_drift: list[str] = field(default_factory=list)
    docs_checked: bool = False
    docs_ok: bool = True
    docs_errors: list[str] = field(default_factory=list)
    docs_warning_count: int = 0
    # Semantic ranking degrades to lexical when the provider cannot load, and
    # `search_memory` reports that only inside a result payload nobody reads.
    # It went unnoticed here for an unknown stretch: memory-seed was installed
    # without its one declared dependency, so every search ranked lexically
    # while claiming a semantic provider. A preflight that prints even when
    # clean is the right home for "the thing you believe is on is off".
    semantic_available: bool = True
    semantic_provider: str | None = None
    semantic_unavailable_reason: str | None = None
    # Decision-diagram coverage. Deliberately a COUNT, not a verdict: a keyword
    # heuristic for "this entry needed a diagram" was prototyped against the
    # real corpus and flagged 35% of all entries - matching "worktree" in a
    # passing validation line, "topology" in a feature name. A check that fires
    # on one entry in three teaches its reader to skip it, and guessing the
    # judgement would contradict this module's own rule that judgment stays
    # with the agent. The bare fact is enough: the convention lapsed for five
    # days and 131 entries with nothing anywhere reporting it.
    diagrams_today: int = 0
    entries_today: int = 0
    last_diagram_date: str | None = None
    entries_since_last_diagram: int = 0
    # ADR diagram REVIEW STATE, not coverage (JNL, 2026-08-07). An ADR is looked
    # at once for whether it deserves a diagram and the verdict is recorded - a
    # diagram, or `diagram_status: not_applicable`. When the ADR later evolves
    # onto a new decision that tick is cleared and another look is owed.
    #
    # Deliberately never a gate. An earlier attempt made a missing answer fail
    # `adrs check`, which broke five test fixtures that create ADRs to exercise
    # unrelated contract rules - and, worse, would have failed for any DOWNSTREAM
    # project with ADRs the moment it upgraded, over a convention it never
    # adopted. Reframing coverage as review state dissolves that: an unreviewed
    # ADR is simply unreviewed, and only this report cares.
    adrs_total: int = 0
    adrs_without_diagram_answer: int = 0
    adrs_needing_diagram_rereview: int = 0
    # Skill -> governing ADR routing. A skill says what to DO; the ADR says
    # what is AUTHORITATIVE. Unrouted, an agent can act on a skill that a
    # rejection has since overtaken - which happened on 2026-08-07.
    skills_without_governing_adr: list[str] = field(default_factory=list)
    skills_with_dangling_governing_adr: list[str] = field(default_factory=list)
    # ADRs carrying no decision at all, with ranked candidates to attach.
    adr_attachment_candidates: list[str] = field(default_factory=list)
    # ADRs whose authoritative head (or an attached non-head member) has an
    # agreed `refines` successor - the concern's current form moved, the ADR
    # did not. Flag only; a head moves by authored revision and nothing else.
    adr_head_reviews: list[str] = field(default_factory=list)
    # Inverse ADR coverage: same-area lineage chains that no ADR claims, weak
    # two-decision pairs, and claimed chains that grew beyond their recorded
    # membership. Every item carries an advisory recommendation; this report
    # never creates an ADR, attaches a member, or moves an authoritative head.
    adr_sweep_candidates: list[dict[str, Any]] = field(default_factory=list)
    corpus_cache: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    temporal_lineage: dict[str, Any] = field(default_factory=dict)
    reflection: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_date": self.session_date,
            "integration_mode": self.integration_mode,
            "merge_trigger": self.merge_trigger,
            "integrity": {"ok": self.integrity_ok, "issues": self.integrity_issues},
            "topics": {"ok": self.topics_ok, "issues": self.topics_issues},
            "link_gaps": self.link_gaps,
            "open_link_stubs": self.open_link_stubs,
            "oldest_open_link_stub": self.oldest_open_link_stub,
            "topic_attribution_gaps": self.topic_attribution_gaps,
            "proposed_topics": self.proposed_topics,
            "oldest_topic_attribution_gap": self.oldest_topic_attribution_gap,
            "provenance": self.provenance,
            "temporal_lineage": self.temporal_lineage,
            "reflection": self.reflection,
            "worktrees": {
                "available": self.worktrees_available,
                "entries": [
                    {
                        "path": w.path,
                        "branch": w.branch,
                        "ahead": w.ahead,
                        "dirty": w.dirty,
                        "is_primary": w.is_primary,
                        "stale_candidate": w.stale_candidate,
                    }
                    for w in self.worktrees
                ],
                "residues": [
                    {
                        "path": residue.path,
                        "namespace": residue.namespace,
                        "git_file_present": residue.git_file_present,
                    }
                    for residue in self.worktree_residues
                ],
            },
            "seed_twins": {"checked": self.seed_twins_checked, "drift": self.seed_twin_drift},
            "docs": {
                "checked": self.docs_checked,
                "ok": self.docs_ok,
                "errors": self.docs_errors,
                "warning_count": self.docs_warning_count,
            },
            "semantic": {
                "available": self.semantic_available,
                "provider": self.semantic_provider,
                "unavailable_reason": self.semantic_unavailable_reason,
            },
            "diagrams": {
                "today": self.diagrams_today,
                "entries_today": self.entries_today,
                "last_sidecar_date": self.last_diagram_date,
                "entries_since_last_sidecar": self.entries_since_last_diagram,
                "adrs_total": self.adrs_total,
                "adrs_without_diagram_answer": self.adrs_without_diagram_answer,
                "adrs_needing_diagram_rereview": self.adrs_needing_diagram_rereview,
                "skills_without_governing_adr": self.skills_without_governing_adr,
                "skills_with_dangling_governing_adr": self.skills_with_dangling_governing_adr,
            },
            "adr_attachment_candidates": self.adr_attachment_candidates,
            "adr_head_reviews": self.adr_head_reviews,
            "adr_sweep_candidates": self.adr_sweep_candidates,
            "corpus_cache": self.corpus_cache,
        }


def _adr_attachment_candidates(
    cwd: Path, memory_dir: Path, limit: int = 10, *, snapshot: CorpusSnapshot | None = None,
) -> list[str]:
    """Ranked attachment candidates for ADRs carrying no decision at all.

    TWO PASSES, deliberately, because they fail in opposite directions.

    GATED - topics decide membership, the ranker decides order. This is the
    split `link audit` already uses, and the 2026-08-07 attachment review
    measured the case for it: topic overlap surfaced 5 of 5 approved picks out
    of ~1050 topiced decisions, while every topic-derived SCORER ranked those
    picks at chance. Topics answer "could this be relevant"; `search_memory`
    answers "which one first". Neither does the other's job.

    UNGATED - the same query with no topic filter at all. A gated pass can only
    ever return decisions inside the ADR's own topic family, so a genuinely
    related decision that was attributed to a different area is invisible to it
    by construction, however relevant its text. That should be rare; being rare
    is not the same as being impossible, and a filter that silently cannot see a
    class of answer needs a companion that can. Anything ranking well here but
    absent from the gated pass is marked STRAY - it is either a real attachment
    the topic family would have hidden, or a sign the ADR's topics are wrong.

    The top SCORE carries information and is printed: a tight high cluster means
    the corpus holds the decision, a weak top score means it does not.
    Candidates only - attaching moves an ADR head and is never done by a report.
    """
    try:
        import yaml

        from .retrieval import entry_topic_sidecars, search_memory

        decisions_dir = memory_dir / "decisions"
        if not decisions_dir.is_dir():
            return []
        ref_re = re.compile(r"(?:mse_[a-z0-9]+|ms-[a-z0-9]+):d[0-9]+")
        front_re = re.compile(r"\A---\s*\n(.*?)^---\s*\n", re.MULTILINE | re.DOTALL)
        decision_re = re.compile(r"### Decision\n\n(.*?)\n\n", re.DOTALL)
        word_re = re.compile(r"[a-zA-Z][a-zA-Z_-]{3,}")
        stop = {
            "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "with", "is",
            "are", "be", "that", "this", "it", "as", "by", "from", "not", "never", "only",
        }

        topic_index = load_topic_index(cwd)
        alias = topic_index.resolution()
        topics_of: dict[str, set[str]] = {}
        for entry_id, record in entry_topic_sidecars(cwd).items():
            for ordinal, slug in record.get("decision_topics", ()):
                if ordinal:
                    topics_of.setdefault(f"{entry_id}:{ordinal}", set()).add(alias.get(slug, slug))

        pending = [
            (path, text)
            for path in sorted(decisions_dir.glob("*.md"))
            if not ref_re.search(text := path.read_text(encoding="utf-8"))
        ]
        if not pending:
            return []

        lines: list[str] = []
        for path, text in pending[:limit]:
            front = front_re.match(text)
            meta = (yaml.safe_load(front.group(1)) if front else {}) or {}
            adr_topics = {alias.get(t, t) for t in (meta.get("topics") or [])}
            decision = decision_re.search(text)
            query = " ".join(
                word
                for word in word_re.findall(
                    f"{meta.get('title') or path.stem} {decision.group(1) if decision else ''}"
                )
                if word.lower() not in stop
            )[:400]

            ranked = search_memory(
                query, cwd=cwd, top_k=40, granularity="decision", snapshot=snapshot,
            )["results"]
            gated = [r for r in ranked if adr_topics & topics_of.get(r["chunk_id"], set())]
            gated_ids = {r["chunk_id"] for r in gated[:3]}
            stray = [r for r in ranked if r["chunk_id"] not in gated_ids][:2]

            if not (gated or stray):
                continue
            lines.append(f"- {path.stem}" + ("" if adr_topics else "  (ADR carries no topics)"))
            for row in gated[:3]:
                shared = sorted(adr_topics & topics_of.get(row["chunk_id"], set()))
                lines.append(f"    [{row['score']:>5.1f}] {row['chunk_id']}  {row['date']}  shared: {', '.join(shared)}")
            for row in stray:
                lines.append(f"    [{row['score']:>5.1f}] {row['chunk_id']}  {row['date']}  STRAY - outside the ADR's topic family")
        if len(pending) > limit:
            lines.append(f"  ({len(pending) - limit} further ADR(s) not shown)")
        return lines
    except Exception:  # noqa: BLE001 - a report must never fail the preflight it rides in
        return []


def _decision_ref_parts(ref: str | None) -> tuple[str, str | None] | None:
    """Split a decision ref into (entry_id, ordinal-or-None), or None if it is not one.

    `founding:<source>` is a PLACEHOLDER head meaning "this concern as recorded
    in the control file", not a decision in the lineage graph - the state
    machine special-cases it in the descent rule for exactly that reason. Split
    it naively and it yields entry_id `founding`, which resolves to nothing and
    would quietly answer "no successor" for every founded ADR.

    A missing ordinal stays None rather than becoming `d1`: the spine's own
    default knows whether the entry holds one decision (`d1`) or several (`""`),
    and hardcoding d1 here would fabricate precision on a multi-decision entry.
    """
    if not ref or ref.startswith("founding:"):
        return None
    entry_id, _, ordinal = ref.partition(":")
    if not entry_id:
        return None
    return entry_id, (ordinal.strip().lower() or None)


def _render_decision_key(key: tuple[str, str]) -> str:
    entry_id, ordinal = key
    return f"{entry_id}:{ordinal}" if ordinal else entry_id


def _adr_sweep_candidates(
    cwd: Path, *, snapshot: CorpusSnapshot | None = None,
) -> list[dict[str, Any]]:
    """Find decision-lineage concerns whose ADR coverage needs review.

    This is the supported form of the inverse-coverage experiment first run in
    ``experiments/adr-campaign/lineage_chains.py``. It deliberately asks the
    opposite question from ``_adr_attachment_candidates``: not "which decision
    belongs to this empty ADR?", but "which same-area decision chain has no ADR?"

    Mechanical discovery stays separate from judgment. Three-or-more-member
    unclaimed chains receive a review-for-promotion recommendation; two-member
    pairs receive a weaker architectural-review recommendation; claimed chains
    with unnamed members receive an attach-or-split review. Recommendations are
    derived advice, never mutations or authority.
    """
    try:
        import collections

        from .adr import adr_membership, current_proposal, iter_adrs
        from .retrieval import augment_chunks_with_link_sidecars, entry_topic_sidecars
        from .semantic_cache import build_refines_spine, extract_memory_chunks

        chunks = (
            snapshot.chunks("entry", "augmented") if snapshot is not None
            else augment_chunks_with_link_sidecars(
                extract_memory_chunks(cwd, granularity="entry"), cwd
            )
        )
        if not chunks:
            return []
        spine = build_refines_spine(chunks)

        def canonical_ref(ref: str) -> str | None:
            entry_id, _, ordinal = ref.strip().partition(":")
            if not entry_id:
                return None
            key = spine.key(entry_id, ordinal or None)
            # A bare ref on a multi-decision entry is ambiguous. The experiment
            # dropped it rather than guessing; the standing check does too.
            return _render_decision_key(key) if key[1] else None

        area: dict[str, set[str]] = collections.defaultdict(set)
        for entry_id, record in entry_topic_sidecars(cwd).items():
            for ordinal, slug in record.get("decision_area", ()):
                if ordinal:
                    area[f"{entry_id}:{ordinal}"].add(slug)
        if not area:
            return []

        claims: dict[str, set[str]] = collections.defaultdict(set)
        for record in iter_adrs(cwd):
            refs = set(adr_membership(record))
            for event in record.events:
                refs.update(event.supporting_decisions or ())
            proposal = current_proposal(record)
            if proposal:
                refs.update(proposal.supporting_decisions or ())
            for raw_ref in refs:
                ref = canonical_ref(raw_ref)
                if ref:
                    claims[ref].add(record.adr_id)

        same_area_edges: set[tuple[str, str]] = set()
        for chunk in chunks:
            if not chunk.entry_id:
                continue
            for edge in chunk.decision_edges:
                kind, source_ordinal, target_entry = edge[0], edge[1], edge[2]
                if kind not in {"evolves", "replaces"}:
                    continue
                target_ordinal = edge[3] if len(edge) > 3 else ""
                newer = canonical_ref(
                    f"{chunk.entry_id}:{source_ordinal}" if source_ordinal else chunk.entry_id
                )
                older = canonical_ref(
                    f"{target_entry}:{target_ordinal}" if target_ordinal else target_entry
                )
                if not newer or not older or not (area.get(newer, set()) & area.get(older, set())):
                    continue
                same_area_edges.add((older, newer))
        if not same_area_edges:
            return []

        parent: dict[str, str] = {}

        def find(node: str) -> str:
            parent.setdefault(node, node)
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        for older, newer in same_area_edges:
            older_root, newer_root = find(older), find(newer)
            if older_root != newer_root:
                parent[newer_root] = older_root
        groups: dict[str, list[str]] = collections.defaultdict(list)
        for node in list(parent):
            groups[find(node)].append(node)

        metadata = {
            chunk.entry_id: str(chunk.entry_datetime or chunk.session_date or "")
            for chunk in chunks
            if chunk.entry_id
        }

        def member_sort(ref: str) -> tuple[str, str]:
            return metadata.get(ref.split(":", 1)[0], ""), ref

        candidates: list[dict[str, Any]] = []
        for component in groups.values():
            if len(component) < 2:
                continue
            members = sorted(component, key=member_sort)
            owners = sorted({adr for ref in members for adr in claims.get(ref, set())})
            unnamed = [ref for ref in members if not claims.get(ref)]
            area_counts = collections.Counter(slug for ref in members for slug in area.get(ref, set()))
            areas = [slug for slug, _count in area_counts.most_common()]
            primary_area = areas[0] if areas else "unknown"
            component_set = set(members)
            component_edges = {
                (older, newer)
                for older, newer in same_area_edges
                if older in component_set and newer in component_set
            }
            roots = component_set - {newer for _older, newer in component_edges}
            heads = component_set - {older for older, _newer in component_edges}
            root = min(roots or component_set, key=member_sort)
            head = max(heads or component_set, key=member_sort)

            if owners and unnamed:
                kind = "grown-chain"
                recommendation = {
                    "action": "review-membership-or-split",
                    "target": head,
                    "rationale": (
                        f"{len(unnamed)} of {len(members)} same-area lineage members are not "
                        "claimed; decide whether they extend the existing concern or form a new ADR."
                    ),
                    "advisory": True,
                }
            elif owners:
                continue
            elif len(members) >= 3:
                kind = "unclaimed-chain"
                recommendation = {
                    "action": "review-for-adr-promotion",
                    "target": head,
                    "rationale": (
                        f"{len(members)} lineage-linked decisions share area {primary_area} and no "
                        "ADR claims any member."
                    ),
                    "advisory": True,
                }
            else:
                kind = "unclaimed-pair"
                recommendation = {
                    "action": "architectural-review-before-promotion",
                    "target": head,
                    "rationale": (
                        f"Two lineage-linked decisions share area {primary_area}, but a pair alone "
                        "is weak evidence for founding an ADR."
                    ),
                    "advisory": True,
                }

            candidates.append({
                "kind": kind,
                "area": primary_area,
                "areas": areas,
                "root": root,
                "head": head,
                "length": len(members),
                "members": members,
                "claimed_by": owners,
                "unclaimed_members": unnamed,
                "recommendation": recommendation,
            })

        kind_order = {"unclaimed-chain": 0, "grown-chain": 1, "unclaimed-pair": 2}
        return sorted(
            candidates,
            key=lambda item: (
                kind_order[item["kind"]], -item["length"], item["area"], item["root"]
            ),
        )
    except Exception:  # noqa: BLE001 - advisory ESR section must fail open
        return []


def _adr_head_reviews(cwd: Path, *, snapshot: CorpusSnapshot | None = None) -> list[str]:
    """ADRs whose authoritative head has an agreed `refines` successor.

    A mechanical fact, reported the way `needs-diagram-review` reports a diagram
    invalidated by evolution: if the decision an ADR is headed by has been
    refined, the concern's current form has moved and the ADR has not. Measured
    on 2026-08-09 over 109 agreed-refines edges and 57 ADRs: 3 heads and 3
    non-head members - a queue that gets read, not a firehose.

    FLAG ONLY, and the wording says so. Nothing moves an ADR head but an
    authored `revision-proposed` + `revision-accepted` pair
    (`feedback_machine_edges_never_move_heads`: one 0.75 machine edge moved an
    ADR onto an unrelated concern in a single hop). The flag is answered either
    way - a revision, or a recorded reviewed-no-change - so an ADR that
    genuinely still holds is retired from the queue by a review, not by silence.

    The walk runs to the chain's TERMINUS, not one hop: an ADR two refinements
    behind is further behind, not differently behind.
    """
    try:
        from .adr import adr_membership, iter_adrs

        records = list(iter_adrs(cwd))
        if not records:
            # Ahead of the corpus pass, deliberately: most projects (and nearly
            # every ESR test) carry no ADRs and should not pay a full chunk
            # extraction to be told so.
            return []

        from .retrieval import augment_chunks_with_link_sidecars
        from .semantic_cache import build_refines_spine, extract_memory_chunks

        # Never `extract_memory_chunks` alone - the sidecar augmentation is
        # where an edge authored in a link sidecar (most of them) becomes
        # visible at all.
        chunks = (
            snapshot.chunks("entry", "augmented") if snapshot is not None
            else augment_chunks_with_link_sidecars(extract_memory_chunks(cwd, granularity="entry"), cwd)
        )
        spine = build_refines_spine(chunks)

        primary: list[str] = []
        secondary: list[str] = []
        for record in records:
            state = record.state
            # A superseded ADR still carries its last head; it is retired, and
            # asking for a revision on it is noise.
            if state.superseded_by:
                continue
            head = state.authoritative_decision
            if not head:
                # An ADR still only proposed has no authority to be behind. The
                # member pass below would otherwise report its own pending
                # decision as "secondary - the authoritative head is unchanged".
                continue
            parts = _decision_ref_parts(head)
            heads = spine.head(*parts) if parts else ()
            for key in heads:
                primary.append(
                    f"ADR {record.adr_id}: head {head} has current form "
                    f"{_render_decision_key(key)} - propose a revision or record "
                    "reviewed-no-change"
                )
            if heads:
                # The secondary line's parenthetical would be false here, and
                # the ADR is already queued for the stronger reason.
                continue
            # The ADR's other attached decisions: every proposed ref plus the
            # predecessors a proposal declared. `revision_statuses` alone is the
            # wrong set - it never holds a predecessor, and on the live corpus
            # it finds none of the three measured non-head hits. A REJECTED ref
            # is attached to nothing and is skipped.
            for ref in sorted(adr_membership(record)):
                if ref == head or state.revision_statuses.get(ref) == "rejected":
                    continue
                parts = _decision_ref_parts(ref)
                if not parts:
                    continue
                for key in spine.head(*parts):
                    secondary.append(
                        f"ADR {record.adr_id}: member {ref} has current form "
                        f"{_render_decision_key(key)} (secondary - the "
                        "authoritative head is unchanged)"
                    )
        return primary + secondary
    except Exception:  # noqa: BLE001 - a report must never fail the preflight it rides in
        return []


def _skill_governance(memory_dir: Path, known_adrs: set[str]) -> tuple[list[str], list[str]]:
    """Skills that name no governing ADR, and skills naming one that does not resolve.

    A skill says what to DO; the ADR says what is currently AUTHORITATIVE for
    that concern. Nothing connected the two, and on 2026-08-07 that cost real
    work: `topic_swarm.md` documents its own pilot abort in convincing detail,
    so it reads as complete - while `adr_topic_backfill_rejected` held the
    actual standing. An agent that reads the skill and acts is not being
    careless; it has no route to the authority. This is the same `rule -> ADR ->
    constitution clause` chain the ADR campaign gave `policy.md`, applied to the
    other half of the control plane.

    Reported, never enforced: a project may legitimately run skills with no ADR
    corpus at all.
    """
    skills_dir = memory_dir / "skills"
    if not skills_dir.is_dir():
        return [], []
    missing, dangling = [], []
    for path in sorted(skills_dir.glob("*.md")):
        if path.name == "index.md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        front = re.match(r"\A---\s*\n(.*?)^---\s*\n", text, re.MULTILINE | re.DOTALL)
        found = re.search(r"^governing_adr:\s*(\S+)\s*$", front.group(1), re.M) if front else None
        if not found:
            missing.append(path.name)
        elif known_adrs and found.group(1) not in known_adrs:
            dangling.append(f"{path.name} -> {found.group(1)}")
    return missing, dangling


def _proposed_topic_requests(memory_dir: Path) -> list[str]:
    """``<slug> (requested by <entry_id>:<dN>)`` for every open vocabulary request.

    Read straight from the `proposed_topics:` key in topic sidecars rather than
    through a topic reader, deliberately: a request must never travel with the
    resolvable slugs, or something downstream will eventually treat it as one.
    """
    topics_dir = memory_dir / "sessions" / "topics"
    if not topics_dir.is_dir():
        return []
    requests: list[str] = []
    for path in sorted(topics_dir.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for block in re.finditer(r"```yaml\n(.*?)```", text, re.S):
            body = block.group(1)
            entry = re.search(r"entry_id:\s*(\S+)", body)
            region = re.search(r"^proposed_topics:\s*\n((?:[ \t]+\S.*\n)+)", body, re.M)
            if not (entry and region):
                continue
            axis = ""
            for line in region.group(1).splitlines():
                stripped = line.strip()
                if stripped.rstrip(":") in ("area", "activity") and stripped.endswith(":"):
                    axis = stripped.rstrip(":")
                    continue
                if not stripped.startswith("-"):
                    continue
                slug, _, ordinal = stripped[1:].strip().partition(":")
                who = f"{entry.group(1)}:{ordinal}" if ordinal else entry.group(1)
                requests.append(f"{slug} [{axis or 'axis not declared'}] (requested by {who})")
    return sorted(set(requests))


def _topic_attribution_gaps(
    cwd: str | Path, *, snapshot: CorpusSnapshot | None = None,
) -> tuple[int, str | None]:
    """Decisions whose Area+Activity is not attributed AT DECISION GRANULARITY,
    where keying would actually add information.

    Not counted: a single-decision entry carrying entry-level Area+Activity.
    Its `dN` and its bare form denote the same thing, so keying it is the topic
    analogue of `redundant-decision-ref` - noise, not coverage. Counted: a
    multi-decision entry whose decisions can only inherit one shared list, and
    any decision with no Area+Activity from either source.

    Returns (count, oldest session date). Silent (0, None) on any failure - a
    reminder must never be able to fail the preflight it rides in.
    """
    try:
        from .retrieval import entry_topic_sidecars
        from .semantic_cache import extract_memory_chunks
        from .topics import load_topic_index

        index = load_topic_index(cwd)
        resolution = index.resolution()
        canon = lambda slug: resolution.get(slug, slug)  # noqa: E731
        both_axes = lambda slugs: {"area", "activity"} <= {  # noqa: E731
            index.axis_of(canon(slug)) for slug in slugs
        }

        keyed: dict[tuple[str, str], set[str]] = {}
        entry_level: dict[str, set[str]] = {}
        for entry_id, record in entry_topic_sidecars(cwd).items():
            for ordinal, slug in record.get("decision_topics", ()):
                target = keyed.setdefault((entry_id, ordinal), set()) if ordinal else entry_level.setdefault(entry_id, set())
                target.add(canon(slug))
            for slug in record.get("topics", ()):
                entry_level.setdefault(entry_id, set()).add(canon(slug))
        entries = snapshot.chunks("entry", "raw") if snapshot is not None else extract_memory_chunks(cwd, granularity="entry")
        for chunk in entries:
            if chunk.entry_id:
                for slug in (getattr(chunk, "topics", None) or ()):
                    entry_level.setdefault(chunk.entry_id, set()).add(canon(slug))

        decisions = [
            (chunk.session_date.isoformat(), chunk.entry_id, ordinal)
            for chunk in (snapshot.chunks("decision", "raw") if snapshot is not None else extract_memory_chunks(cwd, granularity="decision"))
            if chunk.entry_id
            and DECISION_ORDINAL_RE.fullmatch(ordinal := (chunk.chunk_id or "").rsplit(":", 1)[-1])
        ]
        per_entry: dict[str, int] = {}
        for _date, entry_id, _ordinal in decisions:
            per_entry[entry_id] = per_entry.get(entry_id, 0) + 1

        gap_dates = []
        for session_date, entry_id, ordinal in decisions:
            if both_axes(keyed.get((entry_id, ordinal), set())):
                continue
            if both_axes(entry_level.get(entry_id, set())) and per_entry[entry_id] < 2:
                continue
            gap_dates.append(session_date)
        return len(gap_dates), min(gap_dates) if gap_dates else None
    except Exception:  # noqa: BLE001 - a reminder never fails the preflight
        return 0, None


def _entry_dates(memory_dir: Path) -> dict[str, str]:
    """``{entry_id: YYYY-MM-DD}`` for every session entry.

    Diagram sidecars are keyed by entry_id, so counting "today's entries that
    carry one" needs the reverse map. Skips the links/ and diagrams/ subtrees,
    which live under sessions/ but are not session logs.
    """
    import re

    dates: dict[str, str] = {}
    sessions = memory_dir / "sessions"
    if not sessions.is_dir():
        return dates
    for path in sorted(sessions.rglob("*.md")):
        if "links" in path.parts or "diagrams" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in re.finditer(r"^## (\d{4}-\d{2}-\d{2}) \d{2}:\d{2} - ", text, flags=re.M):
            nxt = text.find("\n## ", match.end())
            body = text[match.end(): nxt if nxt > 0 else len(text)]
            entry = re.search(r"entry_id:\s*(\S+)", body)
            if entry:
                dates[entry.group(1)] = match.group(1)
    return dates


def _git_lines(root: Path, *args: str, timeout: int = 30) -> list[str] | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.splitlines()


def _integration_ref(root: Path) -> str | None:
    for ref in ("main", "master"):
        if _git_lines(root, "rev-parse", "--verify", "--quiet", ref) is not None:
            return ref
    return None


def _worktree_posture(root: Path) -> tuple[bool, list[WorktreePosture]]:
    lines = _git_lines(root, "worktree", "list", "--porcelain")
    if lines is None:
        return False, []
    integration = _integration_ref(root)
    postures: list[WorktreePosture] = []
    current: dict[str, Any] = {}

    def flush(is_primary: bool) -> None:
        if not current.get("path"):
            return
        wt_path = Path(current["path"])
        branch = current.get("branch")
        ahead: int | None = None
        dirty: int | None = None
        if integration and branch and branch != integration:
            ahead_lines = _git_lines(root, "log", "--oneline", f"{integration}..{branch}")
            ahead = len(ahead_lines) if ahead_lines is not None else None
        elif branch == integration:
            ahead = 0
        status_lines = _git_lines(wt_path, "status", "--short")
        dirty = len([line for line in status_lines if line.strip()]) if status_lines is not None else None
        postures.append(
            WorktreePosture(
                path=str(wt_path),
                branch=branch,
                ahead=ahead,
                dirty=dirty,
                is_primary=is_primary,
            )
        )

    first = True
    for raw in lines:
        line = raw.rstrip()
        if not line:
            flush(is_primary=first and not postures)
            first = False
            current = {}
            continue
        if line.startswith("worktree "):
            current = {"path": line[len("worktree "):].strip()}
        elif line.startswith("branch "):
            ref = line[len("branch "):].strip()
            current["branch"] = ref.rsplit("/", 1)[-1] if "/" in ref else ref
        elif line == "detached":
            current["branch"] = None
    flush(is_primary=not postures)
    return True, postures


def _normalised_path(path: Path) -> str:
    """Stable path identity using the host filesystem's case semantics."""
    return os.path.normcase(os.path.abspath(path))


def _worktree_storage_root(root: Path) -> Path:
    """Return the primary checkout root even when ESR runs in a worktree."""
    lines = _git_lines(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not lines:
        lines = _git_lines(root, "rev-parse", "--git-common-dir")
    if not lines:
        return root
    common_dir = Path(lines[0].strip())
    if not common_dir.is_absolute():
        common_dir = root / common_dir
    common_dir = common_dir.resolve(strict=False)
    return common_dir.parent if common_dir.name == ".git" else root


def _worktree_residues(root: Path, postures: list[WorktreePosture]) -> list[WorktreeResidue]:
    """Find physical agent worktree directories Git no longer registers.

    This is deliberately read-only and shallow. A residue candidate is not
    deletion authority: ESR surfaces the physical-vs-registered mismatch and
    the End Of Turn runbook owns the audit and consent gate.
    """
    storage_root = _worktree_storage_root(root)
    registered = {_normalised_path(Path(posture.path)) for posture in postures}
    residues: list[WorktreeResidue] = []
    for owner in ("claude", "codex", "gemini", "cursor"):
        namespace = storage_root / f".{owner}" / "worktrees"
        if not namespace.is_dir():
            continue
        try:
            children = sorted(namespace.iterdir(), key=lambda item: item.name.casefold())
        except OSError:
            continue
        for child in children:
            try:
                is_directory = child.is_dir()
            except OSError:
                continue
            if not is_directory or _normalised_path(child) in registered:
                continue
            residues.append(
                WorktreeResidue(
                    path=str(child.resolve(strict=False)),
                    namespace=f".{owner}/worktrees",
                    git_file_present=(child / ".git").is_file(),
                )
            )
    return residues


def _seed_twin_drift(root: Path) -> tuple[bool, list[str]]:
    """Live-vs-seed skill drift, control-plane dev repo only.

    The seed twins live inside the memory_seed package source; a project that
    merely INSTALLED memory-seed has no ``memory_seed/seed`` directory at its
    root, and its live skills legitimately diverge (project adaptations) - so
    the check is skipped entirely outside the dev repo.
    """
    seed_skills = root / "memory_seed" / "seed" / ".memory-seed" / "skills"
    live_skills = root / ".memory-seed" / "skills"
    if not seed_skills.is_dir() or not live_skills.is_dir():
        return False, []
    drift: list[str] = []
    for seed_file in sorted(seed_skills.glob("*.md")):
        # The skills registry legitimately diverges: the live index also
        # registers project-local persona skills that never ship with the
        # seed. Only the skill BODIES are twinned.
        if seed_file.name == "index.md":
            continue
        live_file = live_skills / seed_file.name
        if not live_file.exists():
            drift.append(f"{seed_file.name}: seed twin exists, live skill missing")
            continue
        try:
            if seed_file.read_text(encoding="utf-8") != live_file.read_text(encoding="utf-8"):
                drift.append(f"{seed_file.name}: live and seed twin differ")
        except (OSError, UnicodeDecodeError) as exc:
            drift.append(f"{seed_file.name}: unreadable ({exc})")
    return True, drift


def esr_report(cwd: str | Path = ".", *, session_date: str | None = None) -> EsrReport:
    from .retrieval import audit_link_gaps

    runtime = resolve_runtime(cwd)
    root = runtime.workspace_root
    day = session_date or date.today().isoformat()
    report = EsrReport(session_date=day)
    report.integration_mode = read_integration_mode(root)
    report.merge_trigger = read_merge_trigger(root)
    inspection = inspect_corpus_cache(cwd)
    snapshot = inspection.snapshot
    report.corpus_cache = inspection.to_dict()

    # These are advisory checks.  Sidecars are independently validated and a
    # failed projection must never make ordinary ESR unrelatedly destructive.
    try:
        from .cli import provenance_audit_all

        report.provenance = provenance_audit_all(cwd)
    except Exception as exc:  # noqa: BLE001 - ESR reports failures, it does not hide them
        report.provenance = {"ok": False, "sidecars": [], "error": str(exc)}

    try:
        import hashlib

        from .semantic_cache import extract_memory_chunks
        from .temporal_lineage import GITIGNORE_ENTRY, refresh_temporal_lineage

        decisions: list[dict[str, Any]] = []
        for chunk in extract_memory_chunks(cwd, granularity="decision"):
            if not chunk.entry_datetime or not chunk.chunk_id:
                continue
            decisions.append({
                "decision_ref": chunk.chunk_id,
                "source_digest": "sha256:" + hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
                "claimed_timestamp": chunk.entry_datetime.isoformat(),
                "source_path": chunk.source_path,
                "needle": chunk.text,
            })
        ignore = root / ".gitignore"
        ignored = ignore.is_file() and GITIGNORE_ENTRY in ignore.read_text(encoding="utf-8").splitlines()
        if ignored:
            report.temporal_lineage = refresh_temporal_lineage(root, decisions)
            report.temporal_lineage["classifications"] = {
                ref: {
                    "relative_order": value.get("relative_order"),
                    "claimed_timestamp_relation": value.get("claimed_timestamp_relation"),
                    "calendar_time": value.get("calendar_time"),
                }
                for ref, value in report.temporal_lineage.get("decisions", {}).items()
                if isinstance(value, dict)
            }
        else:
            report.temporal_lineage = {
                "git_available": None, "cache_status": "cache-unignored",
                "cache_published": False, "decisions": {}, "recomputed": [item["decision_ref"] for item in decisions],
                "instruction": f"add {GITIGNORE_ENTRY} to .gitignore before temporal cache publication",
            }
    except Exception as exc:  # noqa: BLE001 - this is an audit surface
        report.temporal_lineage = {"git_available": False, "cache_status": "unavailable", "error": str(exc), "decisions": {}}

    links = check_session_links(cwd=cwd, snapshot=snapshot)
    report.integrity_ok = links.ok
    report.integrity_issues = [
        f"{issue.file}: {issue.kind}: {issue.detail}"
        for issue in links.issues
        if issue.severity == "error"
    ]
    stub_files = [
        issue.file for issue in links.issues if issue.kind == "sidecar-unclassified-stub"
    ]
    report.open_link_stubs = len(stub_files)
    # A link sidecar is filed under its SOURCE entry's session date, so the
    # filename IS the age of the work waiting - no entry lookup needed.
    stub_dates = sorted(
        match.group(1)
        for match in (SESSION_DATE_IN_PATH_RE.search(path) for path in stub_files)
        if match
    )
    report.oldest_open_link_stub = stub_dates[0] if stub_dates else None

    gaps, oldest_gap = _topic_attribution_gaps(cwd, snapshot=snapshot)
    report.topic_attribution_gaps = gaps
    report.oldest_topic_attribution_gap = oldest_gap
    report.proposed_topics = _proposed_topic_requests(runtime.memory_dir)

    topics = check_topics(cwd=cwd)
    report.topics_ok = topics.ok
    report.topics_issues = [
        f"{issue.severity}: {issue.kind}: {issue.detail}" + (f" ({issue.source})" if issue.source else "")
        for issue in topics.issues
    ]

    for gap in audit_link_gaps(cwd=cwd, session_date=day, top_k=3, snapshot=snapshot):
        report.link_gaps.append(
            {
                "entry_id": gap.entry_id,
                "title": gap.title,
                "candidates": [
                    {
                        "entry_id": cand.entry_id,
                        "title": cand.title,
                        "shared_files": list(cand.shared_files),
                        "shared_topics": list(cand.shared_topics),
                        "shared_title_terms": list(cand.shared_title_terms),
                        # The one ranking term a reader cannot verify by eye, so it
                        # travels with the evidence rather than staying implicit in
                        # the order. `None` when semantic ranking was unavailable.
                        "semantic_score": cand.semantic_score,
                        "already_related": cand.already_related,
                        "ungated": cand.ungated,
                        # Chain position constrains the verdict space (interior:
                        # related-only; replaced never appears - substitute_for
                        # names what the offered replacement stands in for).
                        "chain_position": cand.chain_position,
                        "refines_taken_by": cand.refines_taken_by,
                        "current_form": cand.current_form,
                        "substitute_for": cand.substitute_for,
                    }
                    for cand in gap.candidates
                ],
            }
        )

    report.worktrees_available, report.worktrees = _worktree_posture(root)
    if report.worktrees_available:
        report.worktree_residues = _worktree_residues(root, report.worktrees)
    report.seed_twins_checked, report.seed_twin_drift = _seed_twin_drift(root)

    try:
        from .reflection_operations import run_reflection_operation
        report.reflection = run_reflection_operation("board_view", {"cwd": str(root)})
    except Exception as exc:  # ESR must surface reflection faults without hiding other checks.
        report.reflection = {"ok": False, "items": [], "error": str(exc)}

    from .docs_check import check_docs

    docs = check_docs(root)
    report.docs_checked = docs.files_checked > 0
    report.docs_ok = docs.ok
    report.docs_errors = [f"{i.file}: {i.kind}: {i.detail}" for i in docs.errors]
    report.docs_warning_count = len(docs.warnings)

    # Probe the embedding provider the way search does, so the preflight
    # reports the ranking the NEXT search will actually get. Imported here
    # rather than at module scope: esr must stay importable in a lightweight
    # install where the provider's dependency is absent - which is exactly the
    # situation this check exists to report.
    from .retrieval import resolve_semantic_provider

    provider, name, reason = resolve_semantic_provider("preflight")
    report.semantic_available = provider is not None
    report.semantic_provider = name
    report.semantic_unavailable_reason = reason

    # Diagram coverage: how many of today's entries carry a sidecar, and when
    # the last one anywhere was written. The second number is the one that
    # matters - a run of empty days is invisible from inside any single day.
    # Read through the sanctioned sidecar reader rather than re-parsing the
    # files here: it already owns both the month-grouped and legacy-flat
    # layouts, and a second hand-rolled parser is how the two drift apart.
    from .retrieval import entry_diagram_sidecars

    sidecars = entry_diagram_sidecars(cwd)
    report.last_diagram_date = max(
        (str(meta.get("heading_datetime", ""))[:10] for meta in sidecars.values() if meta),
        default=None,
    ) or None
    today_entries = {
        entry_id
        for entry_id, meta in _entry_dates(runtime.memory_dir).items()
        if meta == report.session_date
    }
    report.entries_today = len(today_entries)
    report.diagrams_today = sum(1 for entry_id in today_entries if entry_id in sidecars)
    # How far the practice has drifted, counted the only way that needs no
    # judgment: entries logged since the last diagram was written. NOT "entries
    # that owed one" - the heuristic for that was prototyped and rejected (see
    # the field comment). A date alone reads as recent at a glance; "42 entries
    # since" is the same fact with its weight attached.
    if report.last_diagram_date:
        report.entries_since_last_diagram = sum(
            1
            for entry_id, entry_date in _entry_dates(runtime.memory_dir).items()
            if entry_date > report.last_diagram_date and entry_id not in sidecars
        )

    from .core import known_adr_ids
    from .retrieval import adr_diagram_sidecars

    adr_ids = known_adr_ids(cwd)
    answered = set(adr_diagram_sidecars(cwd))
    report.adrs_total = len(adr_ids)
    report.adrs_without_diagram_answer = len(adr_ids - answered)
    # A cleared tick shows up as the `needs-diagram-review` warning links check
    # raises when an answer's file date no longer matches the ADR's head.
    report.adrs_needing_diagram_rereview = sum(
        1 for issue in links.issues if issue.kind == "needs-diagram-review"
    )
    report.skills_without_governing_adr, report.skills_with_dangling_governing_adr = _skill_governance(
        runtime.memory_dir, adr_ids
    )
    report.adr_attachment_candidates = _adr_attachment_candidates(
        Path(cwd).resolve(), runtime.memory_dir, snapshot=snapshot,
    )
    report.adr_head_reviews = _adr_head_reviews(Path(cwd).resolve(), snapshot=snapshot)
    report.adr_sweep_candidates = _adr_sweep_candidates(
        Path(cwd).resolve(), snapshot=snapshot,
    )
    return report


def format_esr_report(report: EsrReport) -> str:
    lines: list[str] = [f"ESR preflight — session {report.session_date}", ""]

    lines.append("## Corpus cache")
    cache = report.corpus_cache
    if cache:
        lines.append(
            f"{cache.get('health', 'missing')} — schema {cache.get('schema_status', 'unreadable')}; "
            f"equivalence {cache.get('equivalence', 'not-comparable')}"
        )
        if cache.get("reconstruction_required"):
            lines.append("- live source reconstruction used; persistent cache was not trusted")
    else:
        lines.append("missing — no cache inspection available")
    lines.append("")

    lines.append("## Progressive provenance")
    provenance = report.provenance
    if provenance.get("ok", True):
        lines.append(f"OK — {provenance.get('sidecar_count', 0)} sidecar(s) audited.")
    else:
        lines.append("ATTENTION — append-only or Git reference evidence needs review.")
        for sidecar in provenance.get("sidecars", []):
            if not sidecar.get("ok"):
                lines.append(f"- {sidecar.get('path')}: {sidecar.get('error', 'unverified reference')}")
    temporal = report.temporal_lineage
    lines.append(
        f"Temporal lineage: {temporal.get('cache_status', 'not-run')}"
        + (f"; recomputed {len(temporal.get('recomputed', []))}" if isinstance(temporal.get('recomputed'), list) else "")
    )
    if temporal.get("instruction"):
        lines.append(f"- {temporal['instruction']}")
    classifications = temporal.get("classifications", {})
    if classifications:
        for ref, classification in sorted(classifications.items()):
            lines.append(
                f"- {ref}: {classification.get('relative_order')}; "
                f"{classification.get('claimed_timestamp_relation')}; "
                f"calendar {classification.get('calendar_time')}"
            )
    lines.append("")

    lines.append("## Reflection Board v1")
    reflection = report.reflection
    if reflection.get("error"):
        lines.append(f"ATTENTION — reflection inspection unavailable: {reflection['error']}")
    elif not reflection.get("items"):
        lines.append("No active Reflection Board v1 ledgers.")
    else:
        for item in reflection["items"]:
            detail = item.get("diagnostic") or {}
            suffix = f" — {detail.get('code')}: {detail.get('message')}" if detail else ""
            lines.append(f"- {item.get('status')}: {item.get('path')}{suffix}")
            for receipt in item.get("missing_receipts", []):
                lines.append(f"  Missing {receipt['kind']} receipt: {receipt.get('record_id', receipt.get('closed_record_id'))} ({receipt['chain_id']})")
    lines.append("")

    lines.append("## Semantic ranking")
    if report.semantic_available:
        lines.append(f"OK — {report.semantic_provider}")
    else:
        # Named as a degradation, not an error: search still answers, it just
        # answers lexically. The distinction matters because this is not a
        # failure anyone will notice from the results themselves.
        lines.append(f"DEGRADED — ranking is lexical only ({report.semantic_provider})")
        lines.append(f"- reason: {report.semantic_unavailable_reason}")
        lines.append("- a full install restores it: python -m pip install memory-seed")
    lines.append("")

    lines.append("## Decision diagrams")
    if report.diagrams_today:
        lines.append(f"{report.diagrams_today} of today's {report.entries_today} entries carry a sidecar.")
    else:
        # No verdict on whether one was warranted - that judgement is the
        # agent's. The lapse this exists to surface is only visible as a RUN of
        # empty days, which no single day's view shows.
        lines.append(f"None of today's {report.entries_today} entries carry a sidecar.")
        if report.last_diagram_date:
            since = (
                f" ({report.entries_since_last_diagram} entries logged since)"
                if report.entries_since_last_diagram
                else ""
            )
            lines.append(f"- last sidecar anywhere: {report.last_diagram_date}{since}")
        else:
            lines.append("- no diagram sidecar exists in this project yet")
        lines.append(
            "- session_logging.md: when a positive trigger is present and no sidecar is written, "
            "state the reason under A: or Follow-up"
        )
    if report.adrs_total:
        reviewed = report.adrs_total - report.adrs_without_diagram_answer
        lines.append(f"- ADR diagram review: {reviewed} of {report.adrs_total} reviewed")
        if report.adrs_without_diagram_answer:
            lines.append(
                f"  - {report.adrs_without_diagram_answer} never reviewed (record a diagram, or "
                "`diagram_status: not_applicable` if there is no shape to draw)"
            )
        if report.adrs_needing_diagram_rereview:
            lines.append(
                f"  - {report.adrs_needing_diagram_rereview} evolved since review; the answer no "
                "longer matches the ADR's current authority and is owed another look"
            )
    lines.append("")

    lines.append("## Integrity (links check)")
    if report.integrity_ok:
        lines.append("OK")
    else:
        lines.extend(f"- {issue}" for issue in report.integrity_issues)
    lines.append("")

    lines.append("## Topics")
    if report.topics_ok:
        lines.append("OK")
    else:
        lines.extend(f"- {issue}" for issue in report.topics_issues)
    if report.topic_attribution_gaps:
        oldest = f", oldest {report.oldest_topic_attribution_gap}" if report.oldest_topic_attribution_gap else ""
        lines.append(
            f"Decisions without decision-keyed area+activity, corpus-wide: "
            f"{report.topic_attribution_gaps}{oldest} (topic_swarm.md backfills these)."
        )
    if report.proposed_topics:
        lines.append(f"Vocabulary requests awaiting adjudication: {len(report.proposed_topics)}.")
        lines.extend(f"- {request}" for request in report.proposed_topics)
        lines.append(
            "  Rule each: add to topics.yaml, or decline. A request never becomes a slug by being used."
        )
    lines.append("")

    lines.append("## Lifecycle link gaps (today's entries)")
    oldest = f", oldest {report.oldest_open_link_stub}" if report.oldest_open_link_stub else ""
    lines.append(f"Open classification stubs: {report.open_link_stubs}.")
    if report.open_link_stubs:
        lines.append(f"Corpus-wide, not just today{oldest} (link_swarm.md judges these at scale).")
    if not report.link_gaps:
        lines.append("None — no unlinked structural neighbours.")
    else:
        for gap in report.link_gaps:
            lines.append(f"- {gap['entry_id']}  {gap['title']}")
            for cand in gap["candidates"]:
                evidence = []
                # An ungated candidate leads with that fact - it carries no
                # overlap the reader can check. `.get` for the same reason as
                # shared_title_terms below.
                if cand.get("ungated"):
                    evidence.append("UNGATED - semantic rank only")
                # Chain position next - it changes what may be recorded at all.
                # `.get` for replay of pre-field payloads, like the rest.
                if cand.get("chain_position") == "interior":
                    evidence.append(
                        f"INTERIOR - related-only (refines taken by {cand.get('refines_taken_by')}; "
                        f"chain lives at {cand.get('current_form')})"
                    )
                if cand.get("substitute_for"):
                    evidence.append(f"substitute for replaced {cand['substitute_for']}")
                # Title terms lead - see the matching comment in cli.py. Read
                # with `.get` because an ESR payload written before this field
                # existed must still render rather than KeyError on replay.
                if cand.get("shared_title_terms"):
                    evidence.append(f"terms: {', '.join(cand['shared_title_terms'])}")
                if cand["shared_files"]:
                    evidence.append(f"files: {', '.join(cand['shared_files'])}")
                if cand["shared_topics"]:
                    evidence.append(f"topics: {', '.join(cand['shared_topics'])}")
                if cand["already_related"]:
                    evidence.append("already related — consider a lifecycle upgrade")
                lines.append(f"    -> {cand['entry_id']}  {cand['title']}")
                if evidence:
                    lines.append(f"       {' | '.join(evidence)}")
    lines.append("")

    lines.append("## Integration mode")
    if report.integration_mode == "pr":
        lines.append("pr — integrate via push + pull request (declared push authorization for that flow).")
    else:
        lines.append("local-merge — integrate via `session merge-branch` into local main; no push.")
    if report.merge_trigger == "manual":
        lines.append("merge_trigger: manual — HOLD; landing needs `--user-approved` (MCP integrate declines).")
    else:
        lines.append("merge_trigger: automatic — may land at a stable, tested stopping point (local merge / open PR only).")
    lines.append("")

    lines.append("## Worktrees")
    if not report.worktrees_available:
        lines.append("Not a git repository (or git unavailable) — nothing to sweep.")
    elif len(report.worktrees) <= 1 and not report.worktree_residues:
        lines.append("Only the primary checkout — nothing to sweep.")
    else:
        for wt in report.worktrees:
            if wt.is_primary:
                lines.append(f"- {wt.path}  [{wt.branch or 'detached'}]  primary")
                continue
            ahead = "?" if wt.ahead is None else wt.ahead
            dirty = "?" if wt.dirty is None else wt.dirty
            marker = "  STALE CANDIDATE (merged + clean)" if wt.stale_candidate else ""
            lines.append(f"- {wt.path}  [{wt.branch or 'detached'}]  ahead: {ahead}  dirty: {dirty}{marker}")
        if report.worktree_residues:
            lines.append("Unregistered physical directories — audit before removal:")
            for residue in report.worktree_residues:
                metadata = ".git pointer present" if residue.git_file_present else ".git pointer absent"
                lines.append(
                    f"- {residue.path}  [{residue.namespace}]  "
                    f"ORPHAN RESIDUE CANDIDATE ({metadata})"
                )
    lines.append("")

    lines.append("## Docs lifecycle")
    if not report.docs_checked:
        lines.append("No docs/ directory — skipped.")
    elif report.docs_ok:
        suffix = f" ({report.docs_warning_count} warning(s) — incomplete, not broken)" if report.docs_warning_count else ""
        lines.append(f"OK — links, lifecycle pointers, and spec bindings agree with the lanes{suffix}.")
    else:
        lines.extend(f"- {item}" for item in report.docs_errors)
    lines.append("")

    if report.adr_attachment_candidates:
        lines.append("## ADR attachment candidates")
        lines.append("ADRs with no decision attached. Topics gate membership and the ranker orders;")
        lines.append("a second UNGATED pass catches decisions the topic family cannot see (STRAY).")
        lines.append("A weak top score means the corpus has no good match. Attaching moves an ADR head.")
        lines.extend(report.adr_attachment_candidates)
        lines.append("")

    if report.adr_head_reviews:
        lines.append("## ADR review queue")
        lines.append(
            "A `refines` successor on an ADR's head is a mechanical fact, not a verdict: the "
            "concern's current form moved and the ADR did not. Nothing here moves a head - "
            "answer each with an authored revision, or by recording reviewed-no-change."
        )
        lines.append(
            "Revision: author the successor decision as a session entry, then `memory-seed adr "
            "revise --adr-id <id> --decision-ref <new-decision> ...` and `memory-seed adr transition "
            "--adr-id <id> --status accepted ...`."
        )
        lines.append(
            "Reviewed-no-change without a new decision: `memory-seed adr reviewed --adr-id <id> "
            "--entry <existing-entry-id> --reason <text>` (MCP: `memory_adr_reviewed`). A "
            "lifecycle-linked append may instead answer the `memory_session_append` review gate "
            'with `{"adr_id": ..., "outcome": "no-change", "reason": ...}`.'
        )
        lines.extend(report.adr_head_reviews)
        lines.append("")

    lines.append("## ADR sweep candidates")
    lines.append(
        "Inverse coverage over same-area decision lineage. Discovery and recommendations are "
        "derived and advisory; nothing here creates an ADR, attaches a member, or moves a head."
    )
    if not report.adr_sweep_candidates:
        lines.append("None — no unclaimed pair/chain or grown-chain coverage gap was found.")
    else:
        labels = {
            "unclaimed-chain": "UNCLAIMED CHAIN",
            "grown-chain": "GROWN CHAIN",
            "unclaimed-pair": "UNCLAIMED PAIR",
        }
        for item in report.adr_sweep_candidates:
            recommendation = item["recommendation"]
            lines.append(
                f"- {labels[item['kind']]} — {item['area']} — {item['length']} decisions — "
                f"{item['root']} -> {item['head']}"
            )
            lines.append(
                f"  Recommendation: {recommendation['action']} at {recommendation['target']} "
                f"(advisory)."
            )
            lines.append(f"  Basis: {recommendation['rationale']}")
            if item["claimed_by"]:
                lines.append(f"  Claimed by: {', '.join(item['claimed_by'])}")
            lines.append(f"  Members: {', '.join(item['members'])}")
    lines.append("")

    lines.append("## Skill governance")
    if report.skills_with_dangling_governing_adr:
        lines.append("Skills naming an ADR that does not resolve:")
        lines.extend(f"- {item}" for item in report.skills_with_dangling_governing_adr)
    if report.skills_without_governing_adr:
        lines.append(
            f"{len(report.skills_without_governing_adr)} skill(s) name no governing_adr - an agent "
            "reading them has no route to what is currently authoritative:"
        )
        lines.extend(f"- {name}" for name in report.skills_without_governing_adr)
    if not (report.skills_without_governing_adr or report.skills_with_dangling_governing_adr):
        lines.append("OK - every skill names a governing ADR that resolves")
    lines.append("")

    lines.append("## Seed twins")
    if not report.seed_twins_checked:
        lines.append("Not the control-plane dev repo — skipped.")
    elif not report.seed_twin_drift:
        lines.append("OK — live skills match their seed twins.")
    else:
        lines.extend(f"- {item}" for item in report.seed_twin_drift)

    return "\n".join(lines)
