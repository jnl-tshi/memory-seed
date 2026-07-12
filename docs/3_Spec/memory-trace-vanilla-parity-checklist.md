---
title: "Memory Trace Vanilla Parity Checklist"
date: "2026-07-11"
project: "memory-seed"
status: "active-parity-gate"
parent: "../2_Todo/memory-trace-next-generation-implementation-roadmap.md"
---

# Memory Trace Vanilla Parity Checklist

Status: Active parity gate - Phase 0 deliverable of the next-generation roadmap.
Scope: Every user-observable behaviour of the vanilla Memory Trace frontend as of 2026-07-11
(branch `claude-feature-phase0-baseline`). The React migration (Phases 2-5) may not retire the
vanilla fallback until each item below is reproduced or an explicit divergence is approved by the
product owner and recorded here.
Evidence: screenshots in `../4_Reference/memory-trace-phase0-baseline/`, golden fixture
`memory-trace/tests/fixtures/trail-golden-48.json`, measurements in
`../4_Reference/memory-trace-phase0-baseline/README.md`.

Marking: `[ ]` = not yet reproduced in React; check items only from the React app, never from
vanilla (this document starts all-unchecked by design).

## Topbar and global chrome

- [ ] Brand block, runtime chip (project label + entry count)
- [ ] Search box always present; ranked dropdown anchors beneath it
- [ ] Tabs: Trail (first, default view), Graph (second); no Timeline or Search tab
- [ ] Theme toggle (dark/light) persisted; five accent palettes persisted
- [ ] Sidebar and reader collapse toggles persisted (`ml:leftCollapsed`/`ml:rightCollapsed`)
- [ ] Stored view preference persisted; legacy stored "timeline"/"search" values migrate to Trail
- [ ] "/" focuses the search box from anywhere; Escape leaves it
- [ ] Focus, caret, and in-flight keystrokes survive every re-render (no focus-steal bug class)
- [ ] Scroll positions of every scrollable pane survive re-render (left pane, reader, trail)
- [ ] Pane resizers between the three panes; responsive stacking below 860px

## Search as a function over the current view

- [ ] Debounced (180ms) server-side ranked search: sections and files match, not just titles
- [ ] Ranked dropdown: top 10 with date/time + matched-section counts; "+N more highlighted"
      overflow line; empty state names the query and filters
- [ ] Match set highlights IN PLACE - results are never a separate destination view
- [ ] Trail: match rows get an accent marker dot; misses dim to 0.45 opacity; SVG dots dim to
      0.35 fill; structure (lanes, forks, day groups) never disappears under a query
- [ ] Graph: match nodes keep full presence and earn a label; misses and their edges dim
- [ ] Viewbar fragment on both views: match count (with `+` when capped at 50), previous/next
      cycling chips, clear chip
- [ ] Enter / Shift+Enter cycle matches in Trail order (newest first), wrapping; Escape closes
      the dropdown first, then blurs
- [ ] Dropdown click or cycling: selects the entry, reopens a collapsed reader, scrolls the
      Trail row into view, grows the Trail window in whole steps when the target is older
- [ ] Click-away closes the dropdown; query and markers persist; refocusing a non-empty box
      reopens it
- [ ] Clearing (chip) empties the live input too (focus-preservation must not resurrect text)
- [ ] Best-match subsection: reader highlights and scrolls to the matched heading with a
      "Best match:" note; typing alone never selects or navigates
- [ ] Filters (agent/user/topic/date/granularity) constrain the match set

## Trail (primary surface - git-graph timeline)

- [ ] Newest-first fixed-height rows (30px) with day separator rows sharing the grid
- [ ] One lane per branch via fork-to-merge occupancy intervals (not just entry rows)
- [ ] Lane allocation: time-ordered - main pinned to lane 0, then oldest-first by newest-entry
      row (compactness, then older-end tie-breaks), so older/compact branches take inner lanes
      and newer branches stack outward
- [ ] Lane colors: the first four lanes each cycle a pack of three bright colors across
      daisy-chained branches (12 unique colors); lanes 5+ pin to their pack's middle color
- [ ] Text indentation follows the lane silhouette: each row's time/title starts just right of
      the rightmost lane alive at that row (day-separator rows included), via fork-to-merge
      envelope occupancy
- [ ] Daisy-chaining: branches whose occupancy touches only at a shared junction row share a
      lane; the trunk column (lane 0) is main's alone
- [ ] Golden fixture reproduced: `trail-golden-48.json` (items order, laneOf, spans, linkRows incl. `estimated`; regenerate with `tests/fixtures/regen_trail_golden.py`)
- [ ] Rounded-elbow routing (radius 7) for every lane change: connectors, arcs, no sharp turns
- [ ] Commit-accurate fork/merge connectors: anchors from `Memory-Entry` trailer merge events
      (`graph.branches`/`graph.merges`), time-interpolated to fractional trunk rows and clamped
      newer-than-content; trunk merge rings (hover = sha+subject, click selects the merged work);
      a branch whose NEWEST entry is unmerged dangles open; pre-trailer branches fall back to the
      positional heuristic flagged "estimated" on hover; entries with no recorded branch get dots
      but never lines
- [ ] Dashed phantom trunk: a dimmed dashed spine on lane 0 from the top edge to main's newest
      displayed node (only when main has nodes in view and isn't already at the top)
- [ ] Adjacent lifecycle short-hops: a supersedes/evolves edge between adjacent node rows renders
      as a short direct hop beside the dots; routed relationship lanes only for distant edges
- [ ] Reader: "Authored in" vs "Merged to main by" commit split; prose reflow (hard-wrapped
      source lines joined into logical blocks; fenced code preserved verbatim)
- [ ] Worktree switcher: header dropdown from `/api/worktrees` (hidden for single checkouts),
      switching reloads runtime/facets/view against the chosen checkout's memory
- [ ] Serving: asset `?v=` tags content-hashed at serve time; `--static-root` /
      `MEMORY_TRACE_STATIC_ROOT` serves another checkout's UI assets
- [ ] Evidence-based main inference: pre-branching no-branch entries whose capturing commit is
      on main's first-parent chain render on main's lane (`branch_inferred`); recorded branches
      never overridden; uncommitted no-branch entries stay unattached
- [ ] Relationship zone left of main: tinted band, three always-dotted lanes ordered
      replaces | evolves | related (related innermost); dash cadence "6 4" for all types
- [ ] Lifecycle arcs: pastel resting colors with soft arrowheads; selection saturates touched
      routes; opacity grammar 0.9 resting / 0.5 dimmed-under-focus / 0.95 touched
- [ ] Two-rule related model: related routes draw only for cross-branch pairs touched by the
      selection; ALL same-branch related context renders as row brackets - full 3px bracket =
      outbound citations, pastel 2px bracket = inbound mentions + one-hop second-order
      (same branch only)
- [ ] Commit packaging: right-edge gray bracket on rows sharing the selected entry's commit
      (left edge = semantics, right edge = packaging)
- [ ] Two-stage selection: first click saturates + reveals related; second click mutes back to
      pastel with an inset accent ring pinning the row AND the reader header; third restores
- [ ] Branch tip labels at each branch's newest visible row, colored per branch
- [ ] Recent window (60 rows) + "Load older" stepping by 60; window growth preserved on jump
- [ ] Edge legend in the viewbar (replaces / evolves / related-on-select)
- [ ] Directional labels: source "replaces"/"evolves"/"relates to" target (never inverted)

## Graph (secondary surface)

- [ ] Force-directed layout: Fruchterman-Reingold repulsion + sparse attraction (related edges
      + top-3 topic neighbours; date proximity only boosts, never links) + collision pass
- [ ] Deterministic hash-seeded start; positions cached per dataset (pan/hover never recompute)
- [ ] Pan (drag), zoom (wheel 0.45-2.6), Fit view, Reset view
- [ ] Hover: neighbourhood highlight, others dim; click selects (nearest-node hit area)
- [ ] Progressive labels: top-15 by size + hover + selection + search matches only
- [ ] Node size toggle: connectivity (links) vs importance_score; selected node enlarged
- [ ] Edge-type chips toggling related / topic / agent / day; supersedes drawn dashed with
      arrowhead, never conflated with related
- [ ] Scope: All entries / Neighborhood (selected entry, depth 1)
- [ ] Agent-colored nodes (stable hash palette)

## Reader (right pane)

- [ ] Header: date/time + agent, title, chunk id; pinned ring when selection is muted
- [ ] Entry section chips + rendered markdown body
- [ ] Commit section: short SHA + subject + sibling entry link-cards, "Only entry in this
      commit.", or "Not yet committed." while tracking
- [ ] Decision diagrams: built-in offline flowchart/sequence renderer; anything else degrades
      to the raw Mermaid source, never a blank frame
- [ ] Linked Memories (related + backlinks) and Suggestions link-cards navigate on click
- [ ] Raw Metadata grid
- [ ] Best-match subsection highlight + scroll (see search section)

## Sidebar (left pane)

- [ ] Entry/chunk metric cards
- [ ] Saved Views presets as (query, view) pairs: Recent work -> Trail; Design decisions ->
      query over Trail; Related graph -> Graph
- [ ] Filters: agent select, user select, date from/to (seeded from corpus bounds),
      granularity segmented control, reset
- [ ] Topic chips capped at 12 behind "+N more"; active topic toggles off
- [ ] Collapsible sections with persisted open state
- [ ] Applied-filter chips in every viewbar, removable at point of use; date chips only when
      the range differs from corpus bounds

## Server contract (consumed by the frontend)

- [ ] `/api/runtime`, `/api/facets`, `/api/search`, `/api/graph`, `/api/chunks/{id}`
      (`/api/timeline` exists but is frontend-unused; Phase 1 decides its fate)
- [ ] Graph responses carry `branch`, `branch_inferred`, `agent`, `topics`, `connectivity`,
      `importance_score`, `datetime`
- [ ] Chunk responses carry `commit`, `commit_entry_ids`, `commit_entries`, `commit_tracking`
      (diff-derived commit map; oldest commit wins across rewrites)
- [ ] Search responses carry `entry_id`, `matched_sections`, `best_match_chunk_id`, scores
- [ ] Known caps to preserve or consciously change: graph node limit 1000 (a 10k corpus
      renders its newest 1000 - the Trail meta reads "of 1000"), UI search limit 50
