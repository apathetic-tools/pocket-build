# DECISIONS.md

A record of major design and implementation decisions in **pocket-build** — what was considered, what was chosen, and why.

Each entry should be:

- **Atomic:** one key decision per entry.
- **Dated:** include the date you made the call.
- **Rationale-focused:** emphasize _why_ something was done (or not done), not just _what_.

---

# Template

## [YYYY-MM-DD] Title of Decision

### Context

What was happening — what problem or limitation you encountered, or what idea you were evaluating.

### Options Considered

- Option A — pros/cons
- Option B — pros/cons
- (Optional) Related discussions, experiments, or PRs

### Decision

The chosen path (or decision _not_ to act), with a short explanation.

### Consequences

Implications, trade-offs, or follow-ups to keep in mind.

---

# Example

## [2025-10-07] Example: Don't Auto-Update Headers on File Rename

### Context

Auto-updating header paths sounded useful but caused confusion when the header diverged from intentional naming (e.g. generated or aliased files).

### Options Considered

- ✅ Disable automatic updates by default
- 🔄 Enable by default with an opt-out
- ⚙️ Make it configurable

### Decision

Set `autoUpdate = false` by default.

### Consequences

- Simplifies mental model — users must explicitly choose to auto-update.
- Slightly less convenient for file renames, but avoids silent edits.
