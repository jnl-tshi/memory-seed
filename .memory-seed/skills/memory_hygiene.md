---
memory-system-version: 2.12
tags:
  - memory-seed
  - skill
  - memory-hygiene
---

# Memory Hygiene Skill

Use this skill when memory content may expose secrets, private facts, local-only identities, client data, reusable seed templates, or public-release risk.

## Public Memory Hygiene

Treat `.memory-seed` files as potentially publishable unless the user explicitly says the repository will always remain private.

Do not write secrets, credentials, tokens, private keys, sensitive account details, client confidential information, or unnecessary personal data into `index.md`, `policy.md`, skills, archive notes, or session logs.

## Private And Public Risk Distinctions

- Runtime project memory may mention local project paths and decisions when they are necessary for future work.
- Public docs and reusable seed files should avoid private paths, identities, accounts, customer facts, and environment-specific assumptions.
- Session entries should focus on durable technical decisions, tradeoffs, validation, and follow-up risk.
- When a sensitive value is relevant, describe the category of risk rather than recording the value.

## Reusable Template Hygiene

Reusable seed files must stay generic and portable. Do not write project-specific private paths, identities, account details, customer facts, private repository names, or domain-specific secrets into `memory_seed/seed/` templates.

When extracting a project-specific lesson into a reusable template:

1. Remove names, absolute paths, account identifiers, tokens, and private operational details.
2. Preserve the general rule, trigger, or procedure.
3. Keep examples generic.
4. Verify the seed twin and live runtime file still match when parity is required.

## Redaction Pattern

If sensitive information was accidentally recorded:

1. Stop copying the value into further outputs.
2. Ask the user before rewriting historical memory unless the repository's policy already authorizes that repair.
3. Replace the value with a category label, such as `[token redacted]`, only when repair is approved.
4. Record the repair without repeating the secret.

