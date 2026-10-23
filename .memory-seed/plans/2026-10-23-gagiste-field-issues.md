# Gagiste field issues: implementation plan

Approved by JNL on 2026-10-23 (`mse_fkftgrfefdh715qe:d2`; designs in `:d1`). The source is field feedback from Gagiste (`jnl-tshi/gagiste` `docs/memory-seed-issues.md`, MSI-001 to MSI-012). Discovery ran in three read-only Codex rounds (Codex thread `01a168fb-a9cd-7f93-8e6d-3a1a2a68e65d`).

## Approved Discovery Records (summary)

1. **Session logging and PR integration:** remove clean elapsed-time advisories entirely; block only on evidence debt. Install additive managed `.gitattributes` rules for structural paths, verified by doctor. Raw `gh pr merge` produces a warning naming `memory-seed session open-pr`, not a refusal. Refresh managed hooks by digest with archive-before-replace.

2. **ADR lifecycle:** non-descending proposals remain valid but report `acceptance_ready=false` and the missing descent edge. `adr reviewed` becomes preview-by-default with `--apply`. Review refusals return paste-ready outcomes and warn against using `adr reviewed`. Session headings remain local; ADR events use UTC `Z`; explicit ambiguous timestamps require offsets. ADR commands retain mandatory `:dN` and emit one actionable error.

3. **Install, profiles, and Task Packets:** promote the entire lazy-loaded `agent_collaboration.md` to core. Remove the `collaboration` profile immediately, without an alias. Updates remove `agent_collaboration.md` from `skills.ignored` and cleanly drop legacy `collaboration` profile entries. Hooks execute through the installed `memory-seed` environment. Profiles and topics remain separate; provide an explicit opt-in security-topic command.

4. **Doctor:** inspect Git-authoritative bytes for tracked-file encoding, working bytes for untracked files, and recognize attribute/autocrlf checkout conversion. Preserve all other encoding checks.

5. **Superpowers:** approved matrix—brainstorming style-only; writing-plans excluded as authority; read-only parallel dispatch supported; SDD only after an approved plan with packets; Git/worktree/finish controllers excluded; TDD is worker-local for domain/unit code only, with BDD scenarios retaining acceptance authority.

No approved option conflicts with assessed authority. Final fingerprints are `cda0987d…`, `f349e356…`, `99783067…`, `9ba4f9f8…`, and `20de2bdf…`.

## Plan Gate

```json
{
  "schema": "memory-seed/plan-dispatch",
  "version": 1,
  "defaults": {
    "project_context": {
      "project_type_and_purpose": "Memory Seed is a local-first Markdown-authoritative memory, decision, and repository-control system for file-reading agents.",
      "relevant_subsystem": "Installation profiles, Task Packets, integration routing, hooks, ADR ledgers, doctor checks, external workflow boundaries, and package provenance.",
      "task_fit": "Implement seven JNL-approved tranches derived from reproduced Gagiste failures and assessed against current Memory Seed authority.",
      "downstream_use": "Fresh and upgraded projects receive a closed, discoverable, testable main flow without silent hook, merge, timestamp, reference, or encoding failures.",
      "non_goals": [
        "Do not rewrite historical session entries or ADR events.",
        "Do not publish packages, create releases, push branches, or merge pull requests.",
        "Do not adopt external planning, worktree, integration, or acceptance-test ownership."
      ]
    },
    "execution": {
      "role": "worker",
      "persona": "developer",
      "capability_tier": "frontier",
      "forbidden_files": [
        ".memory-seed/policy.md",
        ".memory-seed/index.md",
        ".memory-seed/sessions/2026-10/2026-10-19.md",
        ".memory-seed/decisions/adr_decision_identity.md",
        ".memory-seed/decisions/adr_collaboration_compositional_ownership.md"
      ],
      "output_contract": [
        "Treat each task's edit_ownership paths as its complete allowed_files set; every other file is forbidden until replanned.",
        "Run the task's focused verification before behavior edits to establish the baseline, then rerun it after edits.",
        "Return DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, or BLOCKED; include files changed, commit range, tests and results, substitutions, residual risks, and unresolved conflicts.",
        "Use an independent frontier reviewer, at most two implementation-review iterations, and escalate rather than expanding scope."
      ]
    },
    "retrieval": {
      "profile": "implementation",
      "profile_version": 1,
      "overrides": {
        "selectors": {
          "pinned": []
        },
        "filters": {
          "paths": [],
          "topics": []
        },
        "limits": {
          "max_entries": 40,
          "max_tokens": 12000
        },
        "output": {
          "include_resolution_trace": true,
          "include_excerpts": false
        }
      }
    },
    "budget": {
      "supplemental_input_tokens": 4000,
      "output_tokens": 6000,
      "over_soft_cap": "fail",
      "over_soft_cap_reason": null
    },
    "constitution_refs": [
      "constitution:v2#append-only",
      "constitution:v2#authority",
      "constitution:v2#edge-kinds",
      "constitution:v2#expose-before-rank",
      "constitution:v2#integration-mode",
      "constitution:v2#ownership",
      "constitution:v2#prove-automation",
      "constitution:v2#single-source",
      "constitution:v2#topic-vocabulary",
      "constitution:v2#trust-first"
    ],
    "packet_version": 2,
    "memory_update_policy": "orchestrator"
  },
  "objectives": {
    "T1": "Promote agent_collaboration.md to core, remove the collaboration profile without an alias, migrate legacy selected/ignored/profile state, and make controlled-reference closure fail visibly. Capability allocation: frontier worker and independent frontier reviewer; high reasoning; escalate on any destructive migration or unowned configuration shape.",
    "T2": "Install additive structural .gitattributes protection and expose the exact PR-mode integration command, while warning rather than refusing raw gh merge usage. Capability allocation: frontier worker and independent frontier reviewer; high reasoning; escalate if safe warning requires interception outside existing Memory Seed guards.",
    "T3": "Run package-dependent hooks through the installed Memory Seed executable, refresh managed hooks by digest with archive-before-replace, remove clean elapsed-time advisories, and prove fast-forward checkpoint behavior. Capability allocation: frontier worker and independent frontier reviewer; high reasoning; escalate on foreign hook ownership or cross-host output incompatibility.",
    "T4": "Repair ADR review guidance, proposal readiness reporting, reviewed-no-change write consent, timezone conversion, and actionable :dN validation without weakening append-only replay. Capability allocation: frontier worker and independent frontier reviewer; maximum reasoning; escalate on any historical rewrite, identity relaxation, or ledger-schema change.",
    "T5": "Make doctor encoding checks use Git-authoritative tracked bytes while retaining working-tree checks for untracked files and all non-newline diagnostics. Capability allocation: frontier worker and independent frontier reviewer; high reasoning; escalate if the design cannot distinguish committed CRLF from checkout conversion.",
    "T6": "Document and test the approved Superpowers compatibility matrix, including the worker-local TDD and BDD acceptance boundary. Capability allocation: frontier worker and independent frontier reviewer; medium reasoning; escalate if external skill behavior exceeds the approved ownership matrix.",
    "T7": "Prepare the non-publishing release/provenance tranche: archive the 2.24 control-plane snapshot, assign a distinct package/control-plane version, update changelog and provenance tests, and verify an isolated upgrade without publishing, pushing, tagging, or creating a release. Capability allocation: frontier worker and independent frontier reviewer; high reasoning; stop before every external release action."
  },
  "implementation_plan": {
    "approval_reference": "mse_fkftgrfefdh715qe:d2",
    "tasks": [
      {
        "id": "T1",
        "acceptance_observables": [
          "agent_collaboration.md is in CORE_SKILL_NAMES and absent from optional skill membership",
          "the collaboration profile no longer exists",
          "update removes legacy collaboration profile entries and agent_collaboration.md from skills.ignored with a clear message",
          "fresh init with Gagiste's original profile set installs agent_collaboration.md",
          "doctor rejects an installed controlled Markdown reference whose target is absent"
        ],
        "edit_ownership": [
          {
            "path": "memory_seed/core.py",
            "line_range": [
              1,
              14000
            ]
          },
          {
            "path": ".memory-seed/agent-rules.md",
            "line_range": [
              1,
              260
            ]
          },
          {
            "path": "memory_seed/seed/.memory-seed/agent-rules.md",
            "line_range": [
              1,
              260
            ]
          },
          {
            "path": ".memory-seed/skills/index.md",
            "line_range": [
              1,
              700
            ]
          },
          {
            "path": "memory_seed/seed/.memory-seed/skills/index.md",
            "line_range": [
              1,
              700
            ]
          },
          {
            "path": "tests/test_project_lifecycle.py",
            "line_range": [
              1,
              1100
            ]
          },
          {
            "path": "tests/test_session_schema.py",
            "line_range": [
              1,
              900
            ]
          },
          {
            "path": "tests/test_cli_help.py",
            "line_range": [
              1,
              1200
            ]
          }
        ],
        "dependencies": [],
        "evidence_references": [
          "mse_fkftgrfefdh715qe:d1",
          "ms-1bcfcc91:d1"
        ],
        "verification": [
          "python -m pytest -q tests/test_project_lifecycle.py tests/test_session_schema.py tests/test_cli_help.py",
          "git diff --check"
        ],
        "replan_conditions": [
          "migration would delete or rewrite unrelated project.yaml values",
          "agent_collaboration.md cannot be made core without splitting its established Task Packet contract",
          "a controlled reference outside the declared files must change"
        ]
      },
      {
        "id": "T2",
        "acceptance_observables": [
          "fresh init creates or additively updates .gitattributes with -merge for Memory Seed structural paths",
          "foreign .gitattributes rules remain byte-for-byte except for the managed addition",
          "doctor reports missing or incorrect managed merge attributes",
          "PR-mode Task Packets and final handoffs name memory-seed session open-pr",
          "raw gh PR merging after session-path changes produces a warning but is not refused",
          "concurrent same-day PR preparation preserves session, link, and topic blocks structurally"
        ],
        "edit_ownership": [
          {
            "path": "memory_seed/core.py",
            "line_range": [
              1,
              14000
            ]
          },
          {
            "path": "memory_seed/cli.py",
            "line_range": [
              1,
              3000
            ]
          },
          {
            "path": "memory_seed/packet_render.py",
            "line_range": [
              1,
              900
            ]
          },
          {
            "path": "memory_seed/seed/.gitattributes",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": ".memory-seed/skills/agent_collaboration.md",
            "line_range": [
              1,
              800
            ]
          },
          {
            "path": "memory_seed/seed/.memory-seed/skills/agent_collaboration.md",
            "line_range": [
              1,
              800
            ]
          },
          {
            "path": ".memory-seed/skills/orientation.md",
            "line_range": [
              1,
              180
            ]
          },
          {
            "path": "memory_seed/seed/.memory-seed/skills/orientation.md",
            "line_range": [
              1,
              180
            ]
          },
          {
            "path": "tests/test_project_lifecycle.py",
            "line_range": [
              1,
              1100
            ]
          },
          {
            "path": "tests/test_session_fuse_and_merge.py",
            "line_range": [
              1,
              3100
            ]
          },
          {
            "path": "tests/test_packet_render.py",
            "line_range": [
              1,
              500
            ]
          },
          {
            "path": "tests/test_cli_help.py",
            "line_range": [
              1,
              1200
            ]
          }
        ],
        "dependencies": [
          "T1"
        ],
        "evidence_references": [
          "mse_t388apx6evvmmd1r:d1",
          "mse_dr5eprnhrctqeeg3:d1",
          "mse_9c151e4gbkkv1w5v:d1"
        ],
        "verification": [
          "python -m pytest -q tests/test_project_lifecycle.py tests/test_session_fuse_and_merge.py tests/test_packet_render.py tests/test_cli_help.py",
          "git diff --check"
        ],
        "replan_conditions": [
          "warning on raw gh usage requires a new external shell interceptor",
          "managed attribute insertion cannot preserve foreign rules",
          "a hosted PR path would still permit silent line-based corruption after the change"
        ]
      },
      {
        "id": "T3",
        "acceptance_observables": [
          "SessionStart and Stop hooks work when ambient python3 cannot import memory_seed",
          "all package-dependent configured hooks execute through the installed memory-seed environment",
          "managed hook content drift refreshes at equal declared version and archives the replaced copy",
          "clean elapsed-time turns emit no advisory or block",
          "real HEAD or worktree debt still blocks",
          "a fast-forward pull containing a new latest session entry clears and rebaselines debt",
          "the historical Gagiste hook hash upgrades to the current managed digest"
        ],
        "edit_ownership": [
          {
            "path": "memory_seed/core.py",
            "line_range": [
              1,
              14000
            ]
          },
          {
            "path": "memory_seed/cli.py",
            "line_range": [
              1,
              3000
            ]
          },
          {
            "path": "memory_seed/session_checkpoint.py",
            "line_range": [
              1,
              520
            ]
          },
          {
            "path": ".memory-seed/hooks/session-log-check.py",
            "line_range": [
              1,
              180
            ]
          },
          {
            "path": "memory_seed/seed/.memory-seed/hooks/session-log-check.py",
            "line_range": [
              1,
              180
            ]
          },
          {
            "path": ".memory-seed/hooks/session-start-context.py",
            "line_range": [
              1,
              220
            ]
          },
          {
            "path": "memory_seed/seed/.memory-seed/hooks/session-start-context.py",
            "line_range": [
              1,
              220
            ]
          },
          {
            "path": ".memory-seed/hooks/file-touch-decisions.py",
            "line_range": [
              1,
              380
            ]
          },
          {
            "path": "memory_seed/seed/.memory-seed/hooks/file-touch-decisions.py",
            "line_range": [
              1,
              380
            ]
          },
          {
            "path": "tests/test_hook_merge.py",
            "line_range": [
              1,
              300
            ]
          },
          {
            "path": "tests/test_session_checkpoint.py",
            "line_range": [
              1,
              560
            ]
          },
          {
            "path": "tests/test_project_lifecycle.py",
            "line_range": [
              1,
              1100
            ]
          }
        ],
        "dependencies": [
          "T2"
        ],
        "evidence_references": [
          "mse_dpa5g3h1fma6dazw:d1",
          "mse_903jqy9v4pr8g388:d2"
        ],
        "verification": [
          "python -m pytest -q tests/test_hook_merge.py tests/test_session_checkpoint.py tests/test_project_lifecycle.py",
          "git diff --check"
        ],
        "replan_conditions": [
          "a supported client cannot invoke the installed memory-seed executable",
          "digest refresh would overwrite a foreign or locally owned hook",
          "removing the advisory weakens real evidence-debt enforcement"
        ]
      },
      {
        "id": "T4",
        "acceptance_observables": [
          "ADR review refusal emits a complete paste-ready decisions[].adrs retry shape",
          "the refusal explicitly says not to use adr reviewed for the pending append",
          "adr reviewed performs no write without --apply",
          "non-descending revise succeeds but reports acceptance_ready=false and the missing descent edge",
          "session and ADR timestamps represent the same aware instant and ADR output ends in Z",
          "ambiguous explicit timestamps are refused without an offset",
          "bare ADR lifecycle refs produce one actionable append-:d1 error"
        ],
        "edit_ownership": [
          {
            "path": "memory_seed/adr.py",
            "line_range": [
              1,
              1600
            ]
          },
          {
            "path": "memory_seed/core.py",
            "line_range": [
              1,
              14000
            ]
          },
          {
            "path": "memory_seed/cli.py",
            "line_range": [
              1,
              3000
            ]
          },
          {
            "path": "memory_seed/mcp_server.py",
            "line_range": [
              1,
              1900
            ]
          },
          {
            "path": ".memory-seed/skills/session_logging.md",
            "line_range": [
              1,
              380
            ]
          },
          {
            "path": "memory_seed/seed/.memory-seed/skills/session_logging.md",
            "line_range": [
              1,
              380
            ]
          },
          {
            "path": "tests/test_adr_sidecar.py",
            "line_range": [
              1,
              1200
            ]
          },
          {
            "path": "tests/test_adr_ledger_v2.py",
            "line_range": [
              1,
              1400
            ]
          },
          {
            "path": "tests/test_adr_contract_extension.py",
            "line_range": [
              1,
              800
            ]
          },
          {
            "path": "tests/test_mcp_session_append.py",
            "line_range": [
              1,
              1500
            ]
          },
          {
            "path": "tests/test_mcp_server.py",
            "line_range": [
              1,
              1600
            ]
          },
          {
            "path": "tests/test_cli_help.py",
            "line_range": [
              1,
              1200
            ]
          }
        ],
        "dependencies": [
          "T3"
        ],
        "evidence_references": [
          "ms-e30b9c47:d1",
          "mse_kdhw53hzp4nh8wwm:d1",
          "mse_0qycwt519qdggrpe:d1",
          "mse_17d0qqh34a07qp5b:d1"
        ],
        "verification": [
          "python -m pytest -q tests/test_adr_sidecar.py tests/test_adr_ledger_v2.py tests/test_adr_contract_extension.py tests/test_mcp_session_append.py tests/test_mcp_server.py tests/test_cli_help.py",
          "git diff --check"
        ],
        "replan_conditions": [
          "a proposed change would rewrite or delete existing ledger events",
          "timestamp correction requires changing historical session-heading grammar",
          "a proposed convenience would weaken explicit ADR decision identity"
        ]
      },
      {
        "id": "T5",
        "acceptance_observables": [
          "tracked LF blobs with autocrlf-created working CRLF produce no CRLF issue",
          "a committed CRLF blob still produces a CRLF issue",
          "an untracked CRLF file still produces a CRLF issue",
          "BOM, invalid UTF-8, normalization, and mojibake diagnostics remain unchanged",
          "repair does not rewrite expected checkout conversion"
        ],
        "edit_ownership": [
          {
            "path": "memory_seed/text_files.py",
            "line_range": [
              1,
              420
            ]
          },
          {
            "path": "memory_seed/core.py",
            "line_range": [
              1,
              14000
            ]
          },
          {
            "path": "tests/test_text_files.py",
            "line_range": [
              1,
              280
            ]
          }
        ],
        "dependencies": [
          "T4"
        ],
        "evidence_references": [
          "mse_74ddxsena9nj2afk:d1",
          "mse_kn36asmf96bf5tk1:d1"
        ],
        "verification": [
          "python -m pytest -q tests/test_text_files.py",
          "git diff --check"
        ],
        "replan_conditions": [
          "Git blob or attribute evidence is unavailable for tracked files",
          "the change would suppress committed or untracked CRLF violations",
          "repair cannot distinguish repository policy from checkout materialization"
        ]
      },
      {
        "id": "T6",
        "acceptance_observables": [
          "every approved Superpowers skill has one explicit supported, constrained, or excluded classification",
          "brainstorming is style-only and writes no authoritative spec",
          "writing-plans owns no Memory Seed plan",
          "SDD requires an approved plan and rendered packets",
          "TDD is limited to worker-local domain and unit code",
          "BDD scenarios alone remain acceptance authority",
          "Git, worktree, finish, branch, and integration ownership remains with Memory Seed"
        ],
        "edit_ownership": [
          {
            "path": ".memory-seed/skills/superpowers_integration.md",
            "line_range": [
              1,
              180
            ]
          },
          {
            "path": "memory_seed/seed/.memory-seed/skills/superpowers_integration.md",
            "line_range": [
              1,
              180
            ]
          },
          {
            "path": "tests/test_superpowers_integration.py",
            "line_range": [
              1,
              180
            ]
          }
        ],
        "dependencies": [
          "T5"
        ],
        "evidence_references": [
          "mse_fkftgrfefdh715qe:d1"
        ],
        "verification": [
          "python -m pytest -q tests/test_superpowers_integration.py",
          "git diff --check"
        ],
        "replan_conditions": [
          "an external skill requires plan, branch, integration, or acceptance ownership",
          "the supported Superpowers major version changes",
          "Task Packet trial evidence contradicts the approved matrix"
        ]
      },
      {
        "id": "T7",
        "acceptance_observables": [
          "the prior 2.24 control-plane snapshot is archived before replacement",
          "package and control-plane files expose one distinct internally consistent next version",
          "CHANGELOG documents the seven approved tranches and migration behavior",
          "an isolated install and Gagiste-shaped update refresh managed hook and skill artifacts while preserving project-owned content",
          "doctor succeeds after the isolated upgrade",
          "no package is published, no tag or release is created, and no branch is pushed or merged"
        ],
        "edit_ownership": [
          {
            "path": "pyproject.toml",
            "line_range": [
              1,
              120
            ]
          },
          {
            "path": "memory_seed/core.py",
            "line_range": [
              1,
              14000
            ]
          },
          {
            "path": "memory_seed/seed/AGENTS.md",
            "line_range": [
              1,
              120
            ]
          },
          {
            "path": "memory_seed/seed/CLAUDE.md",
            "line_range": [
              1,
              80
            ]
          },
          {
            "path": "memory_seed/seed/GEMINI.md",
            "line_range": [
              1,
              80
            ]
          },
          {
            "path": "CHANGELOG.md",
            "line_range": [
              1,
              1400
            ]
          },
          {
            "path": ".memory-seed/archive/2.24/agent-rules.md",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": ".memory-seed/archive/2.24/project-bootstrap.md",
            "line_range": [
              1,
              1
            ]
          },
          {
            "path": "tests/test_project_lifecycle.py",
            "line_range": [
              1,
              1100
            ]
          },
          {
            "path": "tests/test_cli_help.py",
            "line_range": [
              1,
              1200
            ]
          }
        ],
        "dependencies": [
          "T1",
          "T2",
          "T3",
          "T4",
          "T5",
          "T6"
        ],
        "evidence_references": [
          "mse_903jqy9v4pr8g388:d2",
          "mse_fkftgrfefdh715qe:d1"
        ],
        "verification": [
          "python -m pytest -q tests/test_project_lifecycle.py tests/test_cli_help.py",
          "python -m build --no-isolation",
          "git diff --check",
          "git status --short"
        ],
        "replan_conditions": [
          "release preparation requires network access, publication credentials, pushing, tagging, or release creation",
          "version preparation would overwrite project-owned downstream content",
          "isolated upgrade cannot prove replacement of the historical Gagiste hook digest",
          "any earlier tranche remains unverified"
        ]
      }
    ],
    "test_strategy": {
      "tests": [
        "tests/test_project_lifecycle.py",
        "tests/test_session_schema.py",
        "tests/test_session_fuse_and_merge.py",
        "tests/test_packet_render.py",
        "tests/test_hook_merge.py",
        "tests/test_session_checkpoint.py",
        "tests/test_adr_sidecar.py",
        "tests/test_adr_ledger_v2.py",
        "tests/test_adr_contract_extension.py",
        "tests/test_mcp_session_append.py",
        "tests/test_mcp_server.py",
        "tests/test_text_files.py",
        "tests/test_superpowers_integration.py",
        "tests/test_cli_help.py"
      ],
      "alternative_checks": [
        "git diff --check",
        "isolated fresh-init and Gagiste-shaped update fixtures",
        "package build without publication"
      ],
      "exceptions": [],
      "tests_before_behavior_change": true,
      "behavior_changes": true
    }
  }
}
```

Discovery receipts: the `plan-dispatch` schema has no `design_discovery` field (MSI-013), so each task's rendered dispatch carries its cluster's receipt (T1: cluster 3 `99783067`; T2-T3: cluster 1 `cda0987d` and cluster 3; T4: cluster 2 `f349e356`; T5: cluster 4 `9ba4f9f8`; T6: cluster 5 `20de2bdf`). Pack fingerprints: `sha256:cda0987d2b914bf946c7043c77ba37afe76a22797c9044b95abca9e951ba988d`, `sha256:f349e3563dc1f3d807be623855baf88c83902bc2ae539b5a37257906dc11a3fe`, `sha256:99783067d69fc7b2b68731720aba362597473d81b8dcfdf9830bc4a02f4d1b6c`, `sha256:9ba4f9f84296f176f5a695c43d2f9044c130a689c7a7241b5c263d8a134930d8`, `sha256:20de2bdf4197d1686f20f344ae6fa352b5dfdea618d2fad6e6e71ac50e827981`.

