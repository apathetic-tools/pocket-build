<!-- DECISIONS.md -->
# DECISIONS.md

A record of major design and implementation choices in **pocket-build** — what was considered, what was chosen, and why.

Each decision:

- Is **atomic** — focused on one clear choice.  
- Is **rationale-driven** — the “why” matters more than the “what.”  
- Should be written as if explaining it to your future self — concise, readable, and honest.  
- Includes **Context**, **Options Considered**, **Decision**, and **Consequences**.  

For formatting guidelines, see the [DECISIONS.md Style Guide](./DECISIONS_STYLE_GUIDE.md).

---

## Choose `Serger` for Single-File Builds
<a id="dec06"></a>*DEC 06 — 2025-10-11*  

### Context

The project needs a **self-contained single-file build** for users who want to run it directly without installation.  
The previous in-house merger script (`dev/make_script.py`) relied on fragile regex parsing and often broke on complex imports.  
We need a **syntax-aware**, low-maintenance bundler that produces **human-readable output**.  

### Options Considered

| Tool | Pros | Cons |
|------|------|------|
| **In-house AST-based**<br>**[`Serger`](https://github.com/apathetic-tools/serger)** | ✅ Full control<br>✅ Easy metadata injection<br>✅ Minimal dependencies | ⚠️ Requires maintenance effort |
| **[`pinliner`](https://pypi.org/project/pinliner/)** | ✅ Preserves internal imports | ⚠️ Unmaintained (~7 yrs)<br>❌ Broken on Python 3.12+ |
| **[`pinliner` “city patch”](https://github.com/The-city-not-present/pinliner)** | ✅ Runs on Python 3.12 | ⚠️ Unmaintained<br>⚠️ One-off patch |
| **[`compyner`](https://pypi.org/project/compyner/)** | ✅ Recursive import handling | ❌ Aimed at MicroPython |
| **[`PyBreeder`](https://github.com/pagekite/PyBreeder)** | ✅ Minimal dependencies | ⚠️ Unmaintained (~5 yrs)<br>❌ Python 2.x target |
| **[`PyBake`](https://pypi.org/project/pybake/)** | ✅ Bundles code and data | ⚠️ Unmaintained (~4 yrs)<br>❌ Early Python 3.x migration |
| **[`pybundler`](https://pypi.org/project/pybundler/)** | ✅ Importable | ⚠️ Unmaintained (~6 yrs)<br>❌ Large bootstrap |

**Executable bundlers** (e.g. `zipapp`, `shiv`, `pex`, `PyInstaller`) are well supported but produce `.pyz` or binaries, not plain `.py` files, and are therefore unsuitable for this build target.

### Decision

Initially, the team chose to adopt **`pinliner`** for single-file builds — aiming to replace fragile regex logic with a syntax-aware merger while avoiding heavy bootstraps or import shims.  
Relying on an existing tool was expected to reduce in-house maintenance.  

### Implications

The build process would simplify to:  
1. Run `pinliner` to bundle the module.  
2. Inject version and license metadata at the top.  

The **PyPI module** would remain the canonical importable form.  

### Follow-up and Evolution (2025-10-13)

Implementation of **[`pinliner`](https://pypi.org/project/pinliner/)** failed: it is incomatible with Python 3.12+ and unmaintained.  
The **[“city patch”](https://github.com/The-city-not-present/pinliner)** hung during tests, and attempts to simplify its output via regex reintroduced the same fragility we were trying to avoid.  
Other surveyed tools were similarly outdated.  

We therefore replaced the regex merger with a custom **AST-based** solution using Python’s built-in `ast` module.  
That prototype evolved into our in-house **[`Serger`](https://github.com/apathetic-tools/serger)** — a dependency-free, syntax-aware combiner now imported as a development-only dependency.


<br/><br/>

---
---

<br/><br/>

## Adopt a Three-Tier Distribution Strategy
<a id="dec05"></a>*DEC 05 — 2025-10-11*  

### Context 

As the early ad-hoc merger script evolved into a tested module, we want to ensure the project remains easy to distribute in forms that best suits different users.  

### Options Considered

| Option | Pros | Cons | Tools
|--------|------|------|------|
| **PyPI module (default)** | ✅ Easy to maintain and install<br>✅ Supports imports and APIs | ❌ Requires installation and internet | [`poetry`](https://python-poetry.org/), [`pip`](https://pypi.org/project/pip/) |
| **Single-file script** | ✅ No install step<br>✅ Human-readable source<br>✅ Ideal for quick CLI use | ❌ Not importable<br>❌ Harder to maintain merger logic | [`serger`](https://github.com/apathetic-tools/serger) |
| **Zipped module (`.pyz`)** | ✅ Bundled, portable archive<br>✅ Maintains import semantics | ⚠️ Requires unzip for source<br>⚠️ Slight startup overhead | [`zipapp`](https://docs.python.org/3/library/zipapp.html), [`shiv`](https://pypi.org/project/shiv/), [`pex`](https://pypi.org/project/pex/) |
| **Executable bundlers** | ✅ Fully portable binaries<br>✅ No Python install required | ❌ Platform-specific<br>❌ Not source-transparent  | [`PyInstaller`](https://pyinstaller.org/en/stable/), [`shiv`](https://pypi.org/project/shiv/), [`pex`](https://pypi.org/project/pex/) |


---

### Decision

Adopt a **three-tier distribution model**:  

1. **PyPI package** — the canonical importable module with semantic versioning guarantees.  
2. **Single-file script** — a CLI build based on `ast` import parsing.  
3. **Zipped module (`.pyz`)** — optional for future releases and easy to produce.  

Each tier serves different users while sharing the same tested, modular codebase.  

This does not rule out an executable bundle in the future.


<br/><br/>

---
---

<br/><br/>


## Target Python Version 3.10
<a id="dec04"></a>*DEC 04 — 2025-10-10*  


### Context

Following the choice of Python *(see [DEC 03](#dec03))*, this project must define a minimum supported version balancing modern features, CI stability, and broad usability.  
The goal is to stay current without excluding common environments.

### Options Considered

The latest Python version is *3.14*.

| Version | Pros | Cons |
|---------|------|------|
| **3.8+** | ✅ Works on older systems | ❌ Lacks modern typing (`\|`, `match`, `typing.Self`) and adds maintenance overhead |
| **3.10+**  | ✅ Matches Ubuntu 22.04 LTS (baseline CI)<br>✅ Includes modern syntax and typing features | ⚠️ Slightly narrower audience but covers all active LTS platforms
| **3.12+** | ✅ Latest stdlib and type system | ❌ Too new; excludes many CI and production environments |

### Platform Baselines
Windows WSL typically runs Ubuntu 22.04 or 24.04 LTS.

| Platform | Default Python | Notes |
|-----------|----------------|-------|
| Ubuntu 22.04 LTS | 3.10 | Minimum baseline |
| Ubuntu 24.04 LTS | 3.12 | Current CI default |
| macOS / Windows | 3.12 | User-installed or Store LTS |
| GitHub Actions `ubuntu-latest` | 3.10 → 3.12 | Transition period coverage |

### Python Versions

| Version | Status | Released | EOL |
|---------|--------|----------|-----|
| 3.14 | bugfix | 2025-10 | 2030-10 |
| 3.13 | bugfix | 2024-10 | 2029-10 |
| 3.12 | security | 2023-10 | 2028-10 |
| 3.11 | security | 2022-10 | 2027-10 |
| **3.10** | security | 2021-10 | 2026-10 |
| 3.9 | security | 2020-10 | 2025-10 |
| 3.8 | end of life | 2019-10-14 | 2024-10-07 |

### Decision

Target **Python 3.10 and newer** as the supported baseline.  
This version provides modern typing and syntax while staying compatible with Ubuntu 22.04 LTS — the lowest common denominator across CI and production systems.


<br/><br/>

---
---

<br/><br/>


## Choose Python as the Implementation Language  
<a id="dec03"></a>*DEC 03 — 2025-10-09*  


### Context

The project aims to be a **lightweight, dependency-free build tool** that runs anywhere — Linux, macOS, Windows, or CI — without setup or compilation.  
Compiled languages (e.g. Go, Rust) would require distributing multiple binaries and would prevent in-place auditing and modification.
Python 3, by contrast, is preinstalled or easily available on all major platforms, balancing universality and maintainability.

---

### Options Considered

| Language | Pros | Cons |
|-----------|------|------|
| **Python** | ✅ Widely available<br>✅ No compile step<br>✅ Readable and introspectable  | ⚠️ Slower execution<br>⚠️ Limited single-file packaging |
| **JavaScript / Node.js** | ✅ Familiar to web developers | ❌ Not standard on all OSes<br>❌ Frequent version churn |
| **Bash** | ✅ Ubiquitous | ❌ Fragile for complex logic

### Decision

Implement the project in **Python 3**, targeting **Python 3.10+** *(see [DEC 04](#dec04))*.  
Python provides **zero-dependency execution**, **cross-platform reach**, and **transparent, editable source code**, aligning with the project’s principle of *clarity over complexity*.  
 It allows users to run the tool immediately and understand it fully — *a build system that fits in your pocket*.

The performance trade-off compared to compiled binaries is acceptable for small workloads.  
Future distributions may include `.pyz` or bundled binary releases as the project evolves.


<br/><br/>

---
---

<br/><br/>


## Choose MIT-NOAI License
<a id="dec02"></a>*DEC 02 — 2025-10-09*  

### Context

This project is meant to be open, modifiable, and educational — a tool for human developers.  
The ethics and legality of AI dataset collection are still evolving, and no reliable system for consent or attribution yet exists.

The project uses AI tools but distinguishes between **using AI** and **being used by AI** without consent.

### Options Considered

- **MIT License (standard)** — simple and permissive, but allows unrestricted AI scraping.
- **MIT + “No-AI Use” rider (MIT-NOAI)** — preserves openness while prohibiting dataset inclusion or model training; untested legally and not OSI-certified.

### Decision

Adopt the **MIT-NOAI license** — the standard MIT license plus an explicit clause banning AI/ML training or dataset inclusion.
This keeps the project open for human collaboration while defining clear ethical boundaries.

While this may deter adopters requiring OSI-certified licenses, it can later be dual-licensed if consent-based frameworks emerge.

### Ethical Consideration

AI helped create this project but does not own it.  
The license asserts consent as a prerequisite for training use — a small boundary while the wider ecosystem matures.


<br/><br/>

---
---

<br/><br/>



## Use AI Assistance for Documentation and Development  
<a id="dec01"></a>*DEC 01 — 2025-10-09*


### Context

This project started as a small internal tool. Expanding it for public release required more documentation, CLI scaffolding, and testing than available time allowed.

AI tools (notably ChatGPT) offered a practical way to draft and refine code and documentation quickly, allowing maintainers to focus on design and correctness instead of boilerplate.

### Options Considered

- **Manual authoring** — complete control but slow and repetitive.
- **Static generators (pdoc, Sphinx)** — good for APIs, poor for narrative docs.
- **AI-assisted drafting** — fast, flexible, and guided by human review.

### Decision

Use **AI-assisted authoring** (e.g. ChatGPT) for documentation and boilerplate generation, with final edits and review by maintainers.  
This balances speed and quality with limited human resources. Effort can shift from writing boilerplate to improving design and clarity.  

AI use is disclosed in headers and footers as appropriate.

### Ethical Note

AI acts as a **paid assistant**, not a data harvester.  
Its role is pragmatic and transparent — used within clear limits while the ecosystem matures.


<br/><br/>

---
---

<br/><br/>

_Written following the [Apathetic Decisions Style v1](https://apathetic-recipes.github.io/decisions-md/v1) and [ADR](https://adr.github.io/), optimized for small, evolving projects._  
_This document records **why** we build things the way we do — not just **what** we built._

> ✨ *AI was used to help draft language, formatting, and code — plus we just love em dashes.*

<p align="center">
  <sub>😐 <a href="https://apathetic-tools.github.io/">Apathetic Tools</a> © <a href="./LICENSE">MIT-NOAI</a></sub>
</p>
