---
title: Merged local branch tip snapshot
date: 2026-09-22
status: reference
---

# Merged local branch tip snapshot

At `main` commit `26c529ba637d7e7ea7879394cd0330253285a552`, Git reported these 78 local branch tips as ancestors of `main`. The name-to-tip mapping preserves a route to each history after a branch label is removed: use `git log --oneline <tip>` or `git show <tip>`. This records commit ancestry, not content equivalence or permission to remove a worktree.

The four attached branches were excluded from branch deletion. The other 74 were eligible after session-ID comparison found no entries absent from `main`; the final deletion result is recorded in the dated session log. This snapshot does not claim that all eligible refs were deleted.

| Local branch | Tip commit | Snapshot disposition |
|---|---|---|
| `claude/memory-seed-swarms-db4e3a` | `0d98f383c5e69b7aa6c7109ce20307e319be7740` | Eligible; review deletion result |
| `claude/superpowers-seed-integration-19f286` | `b00a9cbb41562910d2c37d95cb09d7e284f7e073` | Eligible; review deletion result |
| `codex/audit-proposal-lifecycle-2026-09-09` | `3f9ab61584c92e1a087257c165d0b27c316fb459` | Eligible; review deletion result |
| `codex/backup-task-packet-foundation-pre-fusion` | `f275600f50a797b7ca6f5aecb184b4f863d20b27` | Eligible; review deletion result |
| `codex/chore/experiment-audit-cleanup` | `fde49b1e1b312158af3070f0085bfe7ac5da2f43` | Eligible; review deletion result |
| `codex/chore/remove-contained-worktrees` | `583dd50a6bc3019d04031d9de951f3d6f438d406` | Eligible; review deletion result |
| `codex/chore/rescue-context-worktree-docs` | `af91d7b25c5f467898668547587b5729daeeebd1` | Eligible; review deletion result |
| `codex/chore/resolve-stale-worktrees-and-origins-v2` | `4080ab05469785d9eedbf0090ddae7e7b8fecfd2` | Eligible; review deletion result |
| `codex/docs/brainstorm-decision-harvest` | `2487de5c31fd9825ee8da9e806b5a31956738a3e` | Eligible; review deletion result |
| `codex/docs/capture-feasibility-discovery` | `61499cf083724a587c3d52e385d3fc13281f546e` | Eligible; review deletion result |
| `codex/docs/decision-proposals-comparison` | `a5d28f9f8ab87722d75a195144587c2d4c19854f` | Eligible; review deletion result |
| `codex/docs/high-signal-task-packets` | `25c6075f3b8e8a34f8117295b56dcce76442c6c2` | Eligible; review deletion result |
| `codex/docs/model-tier-packet-budgets` | `e5870549dbcfb88983a83d1f38459132dbc5082f` | Eligible; review deletion result |
| `codex/docs/parameter-tuning-plan` | `9da48e786b1cb56f5eac4da9b2eb19d925ed439e` | Eligible; review deletion result |
| `codex/docs/preferred-keyword-guidance` | `d994b38e5d29bf60d6487bbdb8f018ae696359cc` | Eligible; review deletion result |
| `codex/docs/push-receipt` | `19486260eacaee3ce904b2376c80cc159f9b27ae` | Eligible; review deletion result |
| `codex/docs/reflection-compaction-amendment` | `f035ae97ae97bd40dd7e35577f749ff4e197a312` | Eligible; review deletion result |
| `codex/docs/reflection-ledger-expiry` | `237097c5a46f73c64d0ffdbcf157a79a56de5364` | Eligible; review deletion result |
| `codex/docs/reflection-ledger-prework` | `9ebdaa976472fc7af0ac92b1fe60eaeca2b62844` | Eligible; review deletion result |
| `codex/docs/reflection-ledger-workstream-evolution` | `367ddcfebf5a9fcf5c178b121be2f166fe80c3e9` | Eligible; review deletion result |
| `codex/docs/reflection-next-steps-audit` | `21419d1b66b2a4c59ed0571a697664f9adb1fd38` | Eligible; review deletion result |
| `codex/docs/reflection-retirement-plan` | `9db1c2f4c74eb1fbb1afc8c50b6780f841e7a62c` | Eligible; review deletion result |
| `codex/docs/reflection-true-v1-plan` | `d3a321a9273615abbb106e9c9357f23ebb54ceea` | Eligible; review deletion result |
| `codex/docs/reflection-v1-retirement-plan` | `290f33f4ff95f293298c1429b412794ada192144` | Eligible; review deletion result |
| `codex/docs/seed-pod-p0-plan-update` | `d4f9a5b385dfa9a78d192a0133e5e6bbc913f750` | Eligible; review deletion result |
| `codex/docs/seed-pod-reconciliation-plan` | `6f0849712681e87e001a9f8518373f6a1fecc751` | Eligible; review deletion result |
| `codex/docs/simple-technical-precision` | `f421427a3bf6676806bbdc1616d6ed459961a777` | Eligible; review deletion result |
| `codex/docs/superpowers-delivery-uplift` | `5d73c50b446bba97c7e130cc3254c504cced7bac` | Retained: attached worktree |
| `codex/docs/worktree-reconciliation-skill` | `006f80dcd4f58bd030743aa609a2272d4c380fa9` | Eligible; review deletion result |
| `codex/eval/reflection-board-v1-launch` | `17e984415c0e0260ae241e2f3e667523ff19cd7a` | Eligible; review deletion result |
| `codex/experiment/task-packet-hardening-evaluation` | `0ebbbcf7589b02c255564523fecea8c17b0681e6` | Eligible; review deletion result |
| `codex/feature/branch-session-inventory` | `2bfc88a7f480ee7630fff912b1f544805418f547` | Eligible; review deletion result |
| `codex/feature/canonical-adr-ledger-v2` | `5361bc0672723dafe822408aafd7ab3f342e7326` | Eligible; review deletion result |
| `codex/feature/canonical-adr-ledger-v2-format` | `bc0d54146eb8c5475ecf4e02c108024d1000f7dd` | Eligible; review deletion result |
| `codex/feature/canonical-adr-ledger-v2-fuse-compat` | `2e8cd6e0f0d9ec7b04926ff6455d21fec69b78b3` | Eligible; review deletion result |
| `codex/feature/drafts-record-kinds` | `0b1e79e9a07b4e7edc065c03a2948c6a8b8d1156` | Retained: attached worktree |
| `codex/feature/drafts-source-search` | `19a71c3c71a434ada2ba538e4e2f1d4f9a312d53` | Eligible; review deletion result |
| `codex/feature/evidence-pack-typed-ids` | `45763fa908c252883a3d3ebdcc9c86b5e57ce2f8` | Eligible; review deletion result |
| `codex/feature/progressive-provenance-contracts` | `73a4e3afce370068bbb89b55602332535ef6ca38` | Eligible; review deletion result |
| `codex/feature/project-process-health` | `bfbc83fc7e83a20a58cb98c8ba4e06c9f017933e` | Eligible; review deletion result |
| `codex/feature/provenance-commit-workflow` | `f3789a858b1f9fe112613fb8fda610addb0f1790` | Eligible; review deletion result |
| `codex/feature/provenance-engine` | `77afe35065ec8766178109d2fc065c6f21c57f8b` | Eligible; review deletion result |
| `codex/feature/provenance-surfaces-boundaries-v2` | `ff6c467650720602f0546638fc7c6a9e1edc80c1` | Eligible; review deletion result |
| `codex/feature/provenance-surfaces-corrected` | `549d9c0a0942b73b1adbff17129bea290fe121ec` | Eligible; review deletion result |
| `codex/feature/provenance-surfaces-final` | `09a2b63bd7d2964ecdb13246b0d33042979c3ddb` | Eligible; review deletion result |
| `codex/feature/reconstructable-task-packet-compiler` | `7eac81ad78b5824f2d7dfe97e096e0ba32f77c1d` | Eligible; review deletion result |
| `codex/feature/reflection-board-dormant` | `d51582a86ef35691ddfa732f30d1bfa2990f9d71` | Eligible; review deletion result |
| `codex/feature/reflection-board-v1-admission` | `cae59f61accf3d91e0999400320c7de81ab07824` | Eligible; review deletion result |
| `codex/feature/reflection-board-v1-core` | `f34a3acdf4e717536cea37b1f592996969f0a2d2` | Eligible; review deletion result |
| `codex/feature/reflection-board-v1-launch` | `cd4fb84423f3b7cae8e48f09b0cbe0626ca7003d` | Eligible; review deletion result |
| `codex/feature/reflection-board-v1-launch-main-91a5` | `c2b360f40b78c0d4473899fb1c8f18090df8eb14` | Eligible; review deletion result |
| `codex/feature/reflection-board-v1-launch-main-ee76` | `1c376483c84497cd0c033f8e2388d1877ebd35e1` | Eligible; review deletion result |
| `codex/feature/reflection-board-v1-surfaces` | `b245f6dbb099d75f0542ceed1f00aaa718e1bc45` | Eligible; review deletion result |
| `codex/feature/reflection-board-v1-transactions` | `c74328b9841fc48591bd4c978c7a387a7a2853b1` | Eligible; review deletion result |
| `codex/feature/reflection-ledger` | `fca3c1f64987c78dcbc11676d2e6853e410b656a` | Eligible; review deletion result |
| `codex/feature/reflection-ledger-v2-core` | `07c85685eb58d3422de9d15f8a9fd4f0262dcf23` | Eligible; review deletion result |
| `codex/feature/session-cleanup-lifecycle` | `ac922745b7175296217e0340c62a6e1288547fa0` | Eligible; review deletion result |
| `codex/feature/superpowers-workflow-implementation` | `c9899b645c530624712093354b997a2f0fc8cf08` | Eligible; review deletion result |
| `codex/feature/task-packet-calibration-harness` | `a5e00c24acda8194cf06929ef925c93f6fcf41b6` | Eligible; review deletion result |
| `codex/feature/task-packet-hardening` | `53a35e4e6df6610ca2fb829b6d4eeea66df62c7f` | Eligible; review deletion result |
| `codex/feature/transitive-session-fusion` | `1d9a91510f7fe93c6323f9badb77f2e20edbfdbe` | Eligible; review deletion result |
| `codex/fix/capture-index-reconcile` | `cec2ad188b5b754d4fb865fcd4175198b1192d6d` | Eligible; review deletion result |
| `codex/fix/context-mode-routing-mainline` | `a64a29aa402740b3e897ac7151e5720c8e4b4f1d` | Eligible; review deletion result |
| `codex/fix/decision-origin-base-code` | `5cbd60313e775cdc593c94b7ce5335a7b27fdba9` | Eligible; review deletion result |
| `codex/fix/reflection-identical-sibling` | `736eb084eacb92caad2fd731d4351e3051c66ab5` | Eligible; review deletion result |
| `codex/fix/reflection-inherited-integration` | `89e0d2b24fef0363184ef18a56b40a4c6c0fd1c5` | Eligible; review deletion result |
| `codex/fix/task-packet-agent-rules-baseline` | `8492750ea1fce285290993b086dbf601a5722b6c` | Eligible; review deletion result |
| `codex/integration/graphify-dependency-map` | `146d1b8d6f508cf73cb379bce64446d3a29ea146` | Retained: attached worktree |
| `codex/integration/merge-reconciliation` | `b00a9cbb41562910d2c37d95cb09d7e284f7e073` | Retained: attached worktree |
| `codex/integration/reconstructable-task-packet-compiler` | `015aae242d5a591bb2aa72f35da1c295d89e134c` | Eligible; review deletion result |
| `codex/integration/task-packet-foundation` | `f275600f50a797b7ca6f5aecb184b4f863d20b27` | Eligible; review deletion result |
| `codex/perf/merge-verification-cache` | `126df86f14915cfcadfc9e0c6df8c7704fa6402b` | Eligible; review deletion result |
| `codex/recovery/main-local-20260913` | `19b237530ed3d214c20461be4c099fbaca56629e` | Eligible; review deletion result |
| `codex/recovery/origin-main-20260913` | `86cdf8c328798b5d4e8b417e52fcb37e861b26be` | Eligible; review deletion result |
| `codex/refactor/retire-reflection` | `8125a9b3aa020a269623dbfa054a4d1dcf58bbe4` | Eligible; review deletion result |
| `codex/refactor/retire-reflection-runtime` | `0189ab2876dc9d1dc1dfaf92983922393e593d05` | Eligible; review deletion result |
| `codex/repair-preview-superpowers` | `5d73c50b446bba97c7e130cc3254c504cced7bac` | Eligible; review deletion result |
| `codex/test/remove-reflection-tests` | `f1191ff9b8f91ac611af94d4c188966bc5918af6` | Eligible; review deletion result |
