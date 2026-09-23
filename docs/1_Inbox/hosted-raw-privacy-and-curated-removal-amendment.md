---
priority: P0
next_action: "Open points resolved 2026-09-23; JNL ratifies Constitution v2.2 as drafted, adjusts it, or rejects it. Nothing is applied until ratification."
---

# Hosted raw privacy and curated-record removal amendment

Status: **DRAFT PROPOSAL — awaiting JNL ratification.** Drafted 2026-09-23 from the hosted design discovery
recorded in session entry `mse_ad2jp0msr78je6zw` (D4). No Constitution, contract or programme text changes
until JNL ratifies it.

## Why an amendment is needed

The 2026-09-23 discovery settled two hosted policies that the ratified text does not yet state, and one of them
conflicts with a live invariant:

1. **Raw is visible only to its owner.** A member's raw conversations and tool evidence are visible to that
   member alone, including against the project lead. Invariant #1 grants hosted users only "governed access".
   The edition contract says nothing on raw visibility, and the programme's earlier wording ("a lead does not
   *automatically* receive access") left room for granted access. Because this limits what any governance
   role may ever be granted, it belongs in the ownership invariant, not only in a plan.
2. **Removing a curated record is a last resort.** The selected policy corrects decisions through `evolves` and
   `replaces`, and removes a curated record only for a leaked secret or personal data, misattribution, or a
   curator fabrication, leaving a tombstone. Invariant #2 says "never rewrite or delete", with only named
   exceptions. §11 says a lower layer cannot win by shipping first, so this removal would violate the invariant
   unless the invariant grants the exception.

Both changes are additive. The first narrows who may access data. The second adds a bounded exception
in the same shape as the 1.2 metadata-curation exception. Under §11 precedent, both are a minor bump:
**v2.1 → v2.2**.

## Proposed Constitution text

### Invariant #1 — append after "…deliberate deletion and complete human-readable Markdown export."

> In the hosted edition, a member's raw captured evidence (conversations, tool calls and tool results) is
> readable only by that member. No project lead, delegate, other member or product operator role can be
> granted access to it. The curator may process it as a machine within its bounded evidence window. What
> the team shares is curated records and their permitted excerpts, never another member's raw evidence.

### Invariant #2 — new exception after the 2.1 paragraph

> <!-- constitution-ref: constitution:v1#hosted-curated-removal -->
> **Narrow exception — hosted curated-record removal (2.2):** in the hosted edition, a curated record's
> content may be removed from active storage only when lifecycle correction cannot remedy it. That is the
> case when the record exposes a secret or personal data, attributes words or decisions to the wrong member,
> or states something its evidence does not support (a curator fabrication). A record that is merely wrong
> or outdated is corrected by `evolves` or `replaces` and stays in history. Its author may remove it by giving
> one of those reasons, and the project lead is notified. Removing another member's record requires a
> lead-granted permission. A member to whom a record wrongly attributes words or decisions may report the
> misattribution directly. The report marks the record as disputed and notifies its author and the lead, but
> it does not remove the record itself. Every removal
> leaves a permanent tombstone recording the record id, who removed it, when, the reason category and the
> affected dependents, but not the removed title or content. Records that relied on it, including ADRs and
> approved replacements, remain and mark their evidence as source withdrawn. Removal never applies to the
> local edition, to tombstones, to audit events or to lifecycle edges, and it is never automatic or batched.
> How long removed content may persist in backups is set by hosted retention policy, not by this exception.

### §11 version log row

> | 2.2 | 2026-09-2X | **Amendment: hosted raw-evidence privacy and last-resort curated-record removal.**
> Invariant #1 makes a member's hosted raw evidence readable only by that member; no governance role can be
> granted it, and the curator is the only machine reader. Invariant #2 adds a narrow hosted-only exception:
> a curated record may be removed only for a secret or personal data, misattribution, or fabrication. The
> author removes their own record and the lead is notified; another member's needs a lead-granted
> permission; a misattributed member may report the record as disputed. Each removal leaves a tombstone
> without content, and wrong or outdated decisions are corrected through `evolves`/`replaces`. |
> JNL |

The header's **Version** line and "amended" list gain the matching 2.2 entry.

## Consequential changes on ratification

- `docs/3_Spec/edition-authority-contract.md`: in the identity and authority boundary, add that raw evidence
  is readable only by its owner and that no delegation can grant it. Add acceptance fixtures:
  - a lead, delegate and other member are each denied another member's raw evidence, including through raw
    fallback in retrieval;
  - a removal leaves a content-free tombstone, and its dependents show source withdrawn;
  - a wrong-but-honest record cannot be removed and must be replaced;
  - an author's removal notifies the lead;
  - a misattributed member can mark a record disputed, which notifies its author and the lead but does not
    remove it.
- `docs/2_Todo/hosted-memory-mvp-programme.md`: cite the Invariant #1 and #2 clauses from the Privacy
  section instead of restating them as plan policy.
- The hosted release gate "Privacy/security" gains the fixtures above.

## Alternatives considered

- **Keep both rules in the programme only.** Rejected. Raw privacy would stay revocable by a plan edit, and
  the removal rule would contradict Invariant #2 as written.
- **Change Invariant #2 into "append-only except hosted deletion" (2.x → 3.0).** Rejected as broader than
  needed. The general hosted "deliberate deletion" right already sits in Invariant #1. This exception only
  permits removing curated content under a tombstone.
- **Require the lead's permission for every removal.** JNL's first proposal. Rejected in discovery so an
  author can retract their own sensitive content without waiting.

## Resolved ratification points (JNL, 2026-09-23)

1. **Lead notification:** an author's removal of their own record also notifies the project lead.
2. **Backup purge:** the invariant sets no bound. The maximum time removed content may persist in backups is
   left to the P1.7 retention decisions.
3. **Misattribution reports:** a member to whom a record wrongly attributes words or decisions may report
   it directly, without going through the lead. The report marks the record as disputed and notifies its
   author and the lead. Removal still follows the author or lead-granted path.

## Non-authorizations

This draft changes no ratified text and authorizes no implementation, data collection or hosted deployment.
