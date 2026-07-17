# 7_Superseded — replaced, with a forward pointer

Documents that were valid but have been replaced by a newer one. Kept so the reasoning trail stays
intact; each points forward to what replaced it.

**Required YAML:** `superseded_by:` (doc path or session entry id), `superseded_on:`.

**Contents** (reclassified 2026-07-14):

- `claude-proposal-synergy-evaluation.md`, `codex-proposal-synergy-evaluation.md` — the two per-agent
  cross-proposal reviews (2.13-era snapshots). Every proposal they weighed has since shipped and both
  self-declare "no further research loop is open," so they are superseded by the shipped work plus the
  refreshed `2_Todo/0_NEXT_STEPS.md`.

The P2 migration (2026-07-17) moved the whole `2_Todo/completed/` archive into `5_Completed/` as-is and
retired the folder. Docs there marked "SOURCE RESOLVED / folded into <canonical>" may still deserve
reclassification into this lane — that is a per-doc judgement call, deliberately not folded into the
mechanical migration.
