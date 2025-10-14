# DECISIONS.md Style Guide
*A lightweight convention for documenting engineering choices*

This style is project-agnostic — you can copy this file verbatim into any repository to establish a consistent decision-recording convention.


---

## Purpose

Every project grows through choices — frameworks, formats, trade-offs, or philosophy.  
A **DECISIONS.md** file records those choices and their reasoning so future contributors can understand *why* things are the way they are.

This guide defines a reusable, human-friendly style for writing those decision records.

---

## Guiding Principles

- **Readable first.** Decisions are for humans, not auditors.  
- **Atomic.** One decision per section.  
- **Dated.** Each record marks the start of a period when that decision applies.  
- **Rationale-focused.** The “why” matters more than the “what.”  
- **Revisable.** You can update outcomes without rewriting history.  
- **Lightweight.** No huge templates, no bureaucracy — just clarity.

---

## File Structure

A `DECISIONS.md` lives at the root of your project and lists all decisions in **reverse chronological order** — most recent at the top.

Each decision is formatted like this:

```markdown
## Use AI Assistance for Documentation and Development
*DEC 01 — 2025-10-13*
<a id="dec01"></a>

**Supersedes:** [DEC 00](#dec00)  (omit if blank)
**Refined by:** [DEC 02](#dec02)  (omit if blank)

### Context
Explain the situation or limitation that led to the decision.

### Options Considered
Summarize the major options (pros/cons if useful).

### Decision
State what was chosen and briefly why.

### Consequences
Describe implications, trade-offs, and follow-ups.

### Follow-up and Evolution (optional)
Used later to note how the decision worked in practice.
```

Projects may include `_Written following the [DECISIONS.md Style Guide](./DECISIONS_STYLE_GUIDE.md)._` at the bottom of their DECISIONS.md to indicate adherence.

---

## Formatting Rules

### Headings
Use a **clear, descriptive title** as the section header (what was decided).  
The DEC number and date appear **below** the title in italics for legibility.

Example:
```markdown
## Switch to TypeScript Build Pipeline
*DEC 03 — 2025-07-12*
<a id="dec03"></a>
```

This ensures:
- GitHub’s TOC lists readable titles (“Switch to TypeScript…”).  
- Readers can still `Ctrl+F` for “DEC 03”.  
- Each decision has a stable link target (`#dec03`).

### Numbering
Prefix decisions sequentially: `DEC 01`, `DEC 02`, `DEC 03`, …  
Two digits are enough for most projects.  
If you expect hundreds, use three (`DEC 001`).

### Anchors
Include an explicit anchor `<a id="dec01"></a>` directly below the metadata.  
This keeps links stable even if the title changes.

### Reverse Order
List newest first — readers see the current worldview immediately.

### Superseding or Refining
When a decision replaces or expands on an earlier one, link both ways:

```markdown
**Supersedes:** [DEC 04](#dec04)
**Refined by:** [DEC 06](#dec06)
```

This creates a readable decision graph without repetition.

### Follow-up and Evolution
Optional section for when a decision led to new insight or a revised implementation. Use it to later record what changed, not to rewrite the past.

If you later revisit a decision, add a short dated follow-up note:

```markdown
### Follow-up and Evolution (2025-11-02)
After testing, the tool failed under Python 3.12. Replaced by Compyner.
```

Do not rewrite (except the title) or delete the original decision.  
Only add outcomes when experience or results provide hindsight.

A decision is not final until a release is made. That means you can log a decision, attempt to implement it, and keep revising the decision as you implement it. Once shipped, treat that decision as frozen until revisited. It's okay to go back and add Outcomes.

---

## When to Create a New Decision

Create a new DEC when:

- The project’s **direction** or **policy** changes (not just code).  
- A previous decision is **formally reversed or superseded** after a release.  
- You introduce a **new architectural pattern** or dependency philosophy.

Do **not** create new entries for day-to-day tweaks or experiments.  
Those belong in commits or pull requests.

---

## TOC and Navigation

GitHub and most renderers automatically generate a **Table of Contents**.  
Do not maintain one manually.

Readers can:
- Use the sidebar/dropdown TOC for titles.  
- Search `DEC 03` for quick jumps.  
- Follow `[DEC 03](#dec03)` links between sections.

---

## Voice and Tone

Write decisions **like a conversation with your future self.**

- Plain language beats corporate jargon.  
- Explain reasoning, not just results.  
- Document uncertainty — it helps the next person.  
- Humor is allowed if it clarifies intent.

Example:
> We tried to hand-roll a bundler. It worked until it didn’t.  
> `pinliner` is smarter, smaller, and less likely to cry under Python 3.12.

---

## Example Minimal Entry

```markdown
## Adopt Ruff for Linting
*DEC 02 — 2025-10-12*
<a id="dec02"></a>

### Context
We needed a fast, unified tool for formatting and linting.

### Options Considered
- **Flake8 + Black** — mature, stable, but two configs.
- **Ruff** — one tool, faster, supports both.

### Decision
Adopt `ruff` as both linter and formatter.

### Consequences
Simpler setup; less flexibility for custom plugins.

### Outcome (2026-01-10)
Ruff replaced `isort` too — fewer moving parts.
```

---

## Summary Philosophy

> **Decisions are part of the codebase.**  
> They deserve version control, clarity, and empathy.

Your `DECISIONS.md` is not a bureaucratic artifact — it’s the memory of how your team learned.  
Keep it tidy, readable, and honest.

---

*Format inspired by [ADR](https://adr.github.io/), but optimized for small, evolving projects.*

> ✨ *ChatGPT was used to help draft language, formatting, and code — plus we just love em dashes.*

<p align="center">
  <sub>😐 <a href="https://apathetic-tools.github.io/">Apathetic Tools</a> © <a href="./LICENSE">MIT-NOAI</a></sub>
</p>
