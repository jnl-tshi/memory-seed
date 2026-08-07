"""Found ADRs for two unclaimed lineage chains surfaced by `lineage_chains.py`.

Both were approved by JNL from the chain report. Each lands `proposed` - acceptance is JNL's gate,
and a head is exactly the kind of claim that gate exists for.

Head selection: the NEWEST decision in the chain, because that is what "current" means in this
model. The remaining members attach as `supporting_decisions` rather than `predecessors` - a
predecessor needs a `link:<head>:<kind>:<member>` assertion matching a real edge between that exact
pair, and the chain's edges connect members to each other rather than all to the head. Supporting
carries the evidence without asserting lineage the sidecars do not record.

Usage:  python experiments/adr-campaign/found_chain_adrs.py [--commit]
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from memory_seed.adr import ConstitutionRef, check_adrs, promote_decision  # noqa: E402

ADRS = [
    dict(
        adr_id="adr_mcp_integration_surface",
        source_entry_id="mse_vzsef0fmpsde2jh4", source_decision="d1",
        title="MCP integration: per-agent config placement, upsert semantics, and a gated write surface",
        topics=("mcp-tools", "cli"),
        decision=(
            "Each agent's MCP config goes where that agent actually reads it - Claude in "
            "project-root `.mcp.json`, Codex in `.codex/config.toml` - written on init "
            "unconditionally rather than gated on a PATH probe. Merges upsert: a matching command "
            "is overwritten, a different one under the same key is left alone. The MCP write "
            "surface is gated, with `memory_session_append` the only authoring path, inheriting "
            "the same write-time guards as the CLI."
        ),
        why=(
            "Config placement is per-agent because each vendor discovers servers differently, and "
            "writing to the wrong file fails silently. Upsert-on-matching-command protects a "
            "user's own server that happens to share our key while still keeping ours current. "
            "Unconditional write avoids a PATH probe that is wrong at init time anyway. The write "
            "surface is gated because an ungated pair let MCP writes bypass guards the CLI "
            "enforced - the write-surface parity rule."
        ),
        evolution=(
            "Founded from an 11-decision lineage chain, entirely `mcp-tools`, running 2026-05-29 "
            "to 2026-07-19: unconditional write and hook-time detection, then upsert semantics, "
            "then per-vendor placement for Claude and Codex, then the gated write surface."
        ),
        supporting_decisions=(
            "ms-4c8e2a17:d1", "ms-4c8e2a17:d2", "ms-4c8e2a17:d4", "ms-7b3f1e92:d3",
            "ms-6a09aea8:d1", "ms-2cd452e4:d1", "ms-2cd452e4:d2", "mse_81v7vk4x5ys3k2n0:d3",
        ),
        constitution_refs=(
            ConstitutionRef("constitution:v1#ownership", "governing"),
            ConstitutionRef("constitution:v1#write-surface-parity", "supporting"),
        ),
    ),
    dict(
        adr_id="adr_skill_registry_and_generic_skills",
        source_entry_id="mse_542z3qn0azma9mmx", source_decision="d1",
        title="Skills route through a deterministic registry, and seeded skills are written generic",
        topics=("skill-architecture", "control-plane"),
        decision=(
            "`.memory-seed/skills/index.md` is the deterministic trigger registry: a fresh agent "
            "evaluates one map rather than loading every runbook, and new capabilities are routed "
            "by adding a registry entry rather than by prose scattered across skills. A skill "
            "shipped in the seed is written generic - no hardcoded paths, no machine-specific "
            "locations - so it is reusable in any project that installs it."
        ),
        why=(
            "Trigger prose inside each skill cannot be evaluated without reading every skill, "
            "which is the cost the registry removes; moving trigger logic into `agent-rules.md` "
            "was rejected for making the operating contract too large and less extensible. "
            "Generic seed content is the same principle applied to the skill body: a runbook "
            "carrying one machine's paths is a runbook only that machine can run."
        ),
        evolution=(
            "Founded from a 4-decision lineage chain, entirely `skill-architecture`, running "
            "2026-05-26 to 2026-07-07: the seeded trigger registry, then registry entries as the "
            "way capabilities are added, then the generic-content rule for seeded skills. This "
            "concern was independently identified as missing on 2026-08-07 while routing "
            "`governing_adr`, where 12 skills were left unrouted for want of an ADR covering skill "
            "architecture itself."
        ),
        supporting_decisions=(
            "ms-0bd3d8b2:d1", "mse_vexkm8da35zj856x:d1", "mse_fp32yxbxy3k3r5x1:d1",
        ),
        constitution_refs=(
            ConstitutionRef("constitution:v1#single-source", "governing"),
            ConstitutionRef("constitution:v1#markdown-authority", "supporting"),
        ),
    ),
]

COMMON = dict(user_initials="JNL", agent_type="claude", source="derived")


def main() -> int:
    commit = "--commit" in sys.argv
    failed = 0
    for i, spec in enumerate(ADRS):
        kwargs = {**spec, **COMMON, "timestamp": f"2026-08-07T22:{i:02d}:00Z"}
        dry = promote_decision(REPO, dry_run=True, **kwargs)
        print(f"{'OK ' if dry.ok else 'REFUSED'} {spec['adr_id']:<38} "
              f"head={spec['source_entry_id']}:{spec['source_decision']} "
              f"supporting={len(spec['supporting_decisions'])}")
        if not dry.ok:
            failed += 1
            for issue in dry.issues[:3]:
                print(f"      {issue}")
            continue
        if commit:
            real = promote_decision(REPO, **kwargs)
            if not real.ok:
                failed += 1
                print(f"      WRITE FAILED {real.issues[:2]}")
            else:
                print(f"      written -> status {real.current_status}")
    if commit:
        ok, issues = check_adrs(REPO)
        print("adr check:", ok, issues[:4])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
