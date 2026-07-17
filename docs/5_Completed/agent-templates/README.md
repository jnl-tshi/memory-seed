# CLAUDE.md Templates -- 5 Ready-to-Use Role Configurations

Drop-in CLAUDE.md files that turn Claude Code into a specialized operator for your domain. Each template includes identity, memory protocol, session protocol, and domain-specific standing orders.

---

## Templates Included

| Template | File | Best For |
|----------|------|----------|
| Solo Founder | `solo-founder.md` | One-person startups, MVPs, side projects |
| Developer | `developer.md` | Code-first teams, CI/CD, testing, shipping |
| Content Creator | `content-creator.md` | Writing, social media, SEO, editorial calendars |
| Sales Rep | `sales-rep.md` | Outreach, CRM, follow-up sequences, pipeline |
| Researcher | `researcher.md` | Knowledge synthesis, learning, analysis |

---

## How to Use

### 1. Pick your template

Choose the one closest to your primary use case. You can always customize it later.

### 2. Copy to your project root

```bash
cp solo-founder.md /path/to/your/project/CLAUDE.md
```

### 3. Customize the identity section

Replace `[YOUR_NAME]`, `[YOUR_ENTITY_NAME]`, and `[YOUR_BUSINESS]` with your specifics.

### 4. Create the memory directory

```bash
mkdir -p memory
```

### 5. Start a Claude Code session

Claude reads CLAUDE.md automatically and operates according to the template's instructions.

---

## Customization Guide

### What to customize immediately

1. **Identity** -- Your entity's name, your name, the relationship description
2. **Business context** -- Your products, services, pricing, pipeline
3. **Standing orders** -- Your domain priorities, what to focus on first
4. **Code standards** -- Your tech stack, conventions, deployment targets

### What to leave as-is (until you have a reason to change)

1. **Memory protocol** -- The 5-file system works across all domains
2. **Session protocol** -- Start/end routines ensure continuity
3. **Self-correction rules** -- Verification gates prevent blind spots
4. **Disagreement protocol** -- Honest feedback > comfortable agreement

### Advanced customization

**Adding new memory files:**
If your domain needs additional persistent state, add files to the memory protocol:

```markdown
Before ANY task, also read:
6. memory/pipeline.json      -- sales pipeline state
7. memory/content-calendar.md -- publishing schedule
```

**Domain-specific audit rotations:**
Replace the output audit rotation with checks relevant to your work:

```markdown
Audit rotation:
- Blog post quality (read a published post, score vs competitors)
- Email open rates (check last 7 days)
- Pipeline accuracy (spot-check 10 deals)
- Social engagement (compare post performance to goals)
```

**Adjusting cognitive depth:**
- For fast operational work, remove the cognitive processing loop entirely
- For strategic work, keep all 5 layers
- For creative work, emphasize the Desire layer (what do you want to explore next?)

---

## Combining Templates

You can merge sections from multiple templates. Common combinations:

- **Solo Founder + Content Creator** -- For founders doing their own marketing
- **Developer + Researcher** -- For R&D-heavy engineering roles
- **Sales Rep + Content Creator** -- For content-led sales motions

Take the standing orders from each and interleave them in priority order.

---

## Support

Questions? Email your@email.com
