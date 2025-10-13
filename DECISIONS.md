# DECISIONS.md

A record of major design and implementation decisions in **pocket-build** — what was considered, what was chosen, and why.

Each entry should be:

- **Atomic:** one key decision per entry.
- **Dated:** include the date you made the call.
- **Rationale-focused:** emphasize _why_ something was done (or not done), not just _what_.

---

## Choose [`pinliner`](https://pypi.org/project/pinliner/) for Single-File Builds<small> —  2025-10-11

### Context

`pocket-build` needs a **self-contained single-file** form for users who want to download and run it directly, without installation.  

The previous approach — a hand-built concatenator (`dev/make_script.py`) — broke often due to regex-based import parsing and syntax quirks.  

We wanted a **syntax-aware**, low-maintenance bundler that kept the output **human-readable**.

### Options Considered

All these tools unless marked will merge several `.py` files (sometimes even a complete module) into a single `.py` file of valid python that behaves in the same way.

| Tool | Pros | Cons | Note |
|------|------|------|------|
| **Custom script (current regex based)** | ✅ Full control<br>✅ Easy to inject metadata<br>✅ Minimal deps | ❌ Fragile with multiline imports<br/>❌ Regex-based parsing is unreliable<br>❌ Hard to maintain |
| **Custom script (AST Based)**<br/>`ast.parse()` or `libcst` | ✅ Full control<br>✅ Easy to inject metadata<br>✅ Minimal deps | ❌ Complex tool to develop and maintain<br>❌Distracts resources from main project
| ~~**[`pinliner`](https://pypi.org/project/pinliner/)**~~| ✅ Preserves internal imports<br>✅ Keeps code readable<br>✅ Syntax-aware |❌ No longer maintained (~7 years)<br>❌Does not work on Python 3.12+<br>❌ Adds a small runtime import shim<br>❌ Slightly more complex than plain concatenation | Attempted won't run on 3.12+ |
| ~~**[`pinliner city fork`](https://github.com/The-city-not-present/pinliner)**~~ | ✅ Works on Python 3.12<br>✅ Same as pinliner | ❌ Not actively maintained (~9 months)<br>❌ Fixed just enough to work<br>❌ Same as Pinliner | Attempted, hangs tests,<br> back to regex duct tape |
| **[`compyner`](https://pypi.org/project/compyner/)** | ✅ Lightweight<br>✅ Flat, readable output<br>✅ Works recursively through imports | ❌ Targeted at MicroPython<br>❌ Limited testing<br>❌ Loses *import* semantics |
| **[`PyBreeder`](https://github.com/pagekite/PyBreeder)** | ✅ Simple concatenator<br>✅ Minimal dependencies | ❌ No longer maintained (~5 years)<br>❌ Targets Python 2.x<br>❌ Not syntax-aware<br>❌ Breaks easily on complex imports or formatting<br>❌ No license |
| **[`PyBake`](https://pypi.org/project/pybake/)** | ✅ Can bundle code *and* data with embedded filesystem | ❌ No longer maintained (~4 years)<br>❌ Early stage Python 3.x migration<br>❌ Heavier than needed for pure code<br>❌ Not meant for source-level readability |
| **[`pybundler`](https://pypi.org/project/pybundler/)** | ✅ Preserves importable package structure<br>✅ Great for dual CLI/library tools | ❌ No longer maintained (~6 years)<br>❌ Adds ~100 lines bootstrap<br>❌ May be overkill for CLI |
| **Executable bundlers**<br> ([`zipapp`](https://docs.python.org/3/library/zipapp.html), [`shiv`](https://pypi.org/project/shiv/), [`pex`](https://pypi.org/project/pex/), [`PyInstaller`](https://pyinstaller.org/en/stable/)) | ✅ Ideal for binary-like releases or hermetic CI packaging<br>✅ Well-supported and production-grade | ❌ Produce `.pyz` or binaries (not plain Python)<br>❌ Not human-readable<br>❌ Can have larger artifact size |

### Code sample with `libcst`

```python
import libcst as cst
import os

modules = ["types.py", "utils.py", "config.py", "build.py", "cli.py"]
imports, bodies = [], []

for mod in modules:
    tree = cst.parse_module(open(os.path.join("src/pocket_build", mod)).read())
    for stmt in tree.body:
        if isinstance(stmt, (cst.Import, cst.ImportFrom)):
            if "pocket_build" not in stmt.code:
                imports.append(stmt.code)
        else:
            bodies.append(stmt.code)

with open("bin/pocket-build.py", "w") as f:
    f.write("#!/usr/bin/env python3\n")
    f.write("\n".join(sorted(set(imports))) + "\n\n")
    for body in bodies:
        f.write(body + "\n")
```

### Decision

Attempt to adopt **`pinliner`** as the bundler for producing the single-file `pocket-build.py`.  
It generates a deterministic, clean, human-readable script with none of the parsing fragility of the hand-rolled merger, and without the runtime import machinery of `pybundler`.

### Consequences

- The single-file build becomes **maintainable and robust**.  
- The `dev/make_script.py` logic will be simplified to:  
  1. Call `pinliner` to bundle the module.  
  2. Inject version/license metadata at the top.  
- The **PyPI module** remains the canonical importable form.  
- `.pyz` and similar formats can be layered on later with minimal change.
- Developers can still open, diff, and audit the bundled file easily.  

<br/><br/>

---
---

<br/><br/>

## Adopt a Three-Tier Distribution Strategy<small> — 2025-10-11</small>

### Context 

We want to reach as many people as possible and meet them where they are. 

We started with a simple stand-alone script, then as it grew more complex we made it a module to make maintenance and testing easier, but retained a stand-alone script via a hand-rolled merger script.

This decision formalizes how *pocket-build* will be distributed and supported going forward.

---

### Options Considered

| Option | Pros | Cons | Tools
|--------|------|------|------|
| **PyPI module (default)** | ✅ Easy to maintain<br>✅ Easy for Python projects to install<br>✅ Supports imports and APIs | ❌ Requires installation and internet<br>❌ Not easily portable | [`poetry`](https://python-poetry.org/), [`pip`](https://pypi.org/project/pip/) |
| **Single-file script** | ✅ Easy to distribute<br>✅ No install step<br>✅ Human-readable code<br>✅ Ideal for local and ad-hoc usage | ❌ Not meant for import<br>❌ Intended for CLI use only<br>❌ Merger can be hard to use and maintain<br>❌ Hard to read long source code | [`pinliner`](https://pypi.org/project/pinliner/) |
| **Zipped module (`.pyz`)** | ✅ Bundles everything into a single executable archive<br>✅ Maintains import semantics<br>✅ Excellent for CI/CD or air-gapped usage | ❌ Binary-like (unzip for source)<br>❌ Slight startup overhead | [`zipapp`](https://docs.python.org/3/library/zipapp.html), [`shiv`](https://pypi.org/project/shiv/), [`pex`](https://pypi.org/project/pex/) |
| **Native-like Executable bundlers** | ✅ Portable binary-like form<br>✅ Excellent for deployment<br>✅ No Python environment required<br>✅Unaffected by Python environment changes | ❌ Binaries themselves are not cross-platform<br>❌ Slight startup overhead<br>❌ Not source-level transparent<br>❌ May be overkill for CLI  | [`PyInstaller`](https://pyinstaller.org/en/stable/), [`shiv`](https://pypi.org/project/shiv/), [`pex`](https://pypi.org/project/pex/) |

---

### Decision

Adopt a **three-tier distribution model**:

1. **PyPI package** — the canonical importable module with semver guarantees.  
2. **Zipped module (`.pyz`)** — optional in future releases for CI/CD use. Easy to produce.
3. **Single-file script** — a `bin/pocket-build.py` CLI built using [`pinliner`](https://pypi.org/project/pinliner/).  

Each tier serves a distinct user persona while sharing the same tested, modular codebase.

---

### Consequences

- The **source package (`src/pocket_build`)** remains the authoritative code.  
- The **single-file build** gives end-users a portable, human-readable executable form.  
- A **future `.pyz` target** can provide hermetic portability for CI/CD without extra dependencies.  
- **PyInstaller**, **Shiv**, and **Pex** remain viable for downstream consumers who need binary-like distribution, but won’t be part of the core project.  
- This approach maintains transparency, reproducibility, and the “fits-in-your-pocket” philosophy while scaling to professional workflows.


<br/><br/>

---
---

<br/><br/>


# Target Python Version 3.10 — 2025-10-13

## Context

Pocket-build is a lightweight build system designed to remain compatible with common developer environments and continuous integration (CI) runners.  
We needed to decide which Python versions to officially support to balance modern features, runtime stability, and wide usability.

## Options Considered

- **Support 3.8+**  
  - ✅ Works on very old systems and some embedded CI containers.  
  - ❌ Lacks modern typing (`|` unions, `match`, `typing.Self`) used throughout the codebase.  
  - ❌ Adds maintenance overhead for obsolete Python releases.

- **Support 3.10+**  
  - ✅ Matches Ubuntu 22.04 LTS (the baseline CI OS).  
  - ✅ Includes structural pattern matching, modern typing syntax, and context manager improvements.  
  - ⚠️ Slightly narrower audience, but still covers all current LTS platforms.

- **Support 3.12+**  
  - ✅ Always the latest standard library and type system.  
  - ❌ Too restrictive; would exclude many production and CI environments.

## Platforms

| Platform | Default Python | Notes |
|-----------|----------------|-------|
| Ubuntu 22.04 LTS | 3.10 | Minimum supported baseline. |
| Ubuntu 24.04 LTS | 3.12 | Current CI default. |
| macOS (Homebrew / Python.org) | 3.12 | Must be user-installed. |
| Windows (Microsoft Store) | 3.12 | Microsoft’s LTS release. |
| GitHub Actions `ubuntu-latest` | 3.10 → 3.12 | Both available during transition. |

## Decision

Pocket-build targets **Python 3.10 and newer**.  
This ensures the codebase can use modern language features while staying compatible with Ubuntu 22.04 LTS (the lowest common denominator for CI).

## Consequences

- The project can confidently rely on post–3.10 typing features and standard library APIs.  
- No need for compatibility shims for 3.8/3.9.  
- CI runs on Python 3.10–3.12 to ensure forward compatibility.  
- Users running legacy interpreters must upgrade to Python 3.10+.


<br/><br/>

---
---

<br/><br/>


# Template

## Title of Decision<small> — YYYY-MM-DD</small>

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

## Example: Don't Auto-Update Headers on File Rename<small> — 2025-10-07</small>

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

---

> ✨ *ChatGPT was used to help draft language, formatting, and code — plus we just love em dashes.*

<p align="center">
  <sub>😐 <a href="https://apathetic-tools.github.io/">Apathetic Tools</a> © <a href="./LICENSE">MIT-NOAI</a></sub>
</p>
