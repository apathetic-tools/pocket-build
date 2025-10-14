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

This project needs a **self-contained single-file** form for users who want to download and run it directly, without installation.  

The previous approach — a hand-built concatenator (`dev/make_script.py`) — broke often due to regex-based import parsing and syntax quirks.  

We wanted a **syntax-aware**, low-maintenance bundler that kept the output **human-readable**.

### Options Considered

All these tools unless marked will merge several `.py` files (sometimes even a complete module) into a single `.py` file of valid python that behaves in the same way.

| Tool | Pros | Cons |
|------|------|------|
| **Custom script (current regex based)** | ✅ Full control<br>✅ Easy to inject metadata<br>✅ Minimal deps | ❌ Fragile with multiline imports<br/>❌ Regex-based parsing is unreliable<br>❌ Hard to maintain |
| **Custom script (AST Based)** — [`Serger`](https://github.com/apathetic-tools/serger) <br/>`ast.parse()` or `libcst` | ✅ Full control<br>✅ Easy to inject metadata<br>✅ Minimal deps | ❌ Complex tool to develop and maintain<br>❌Distracts resources from main project
| **[`pinliner`](https://pypi.org/project/pinliner/)**| ✅ Preserves internal imports<br>✅ Keeps code readable<br>✅ Syntax-aware |❌ No longer maintained (~7 years)<br>❌Does not work on Python 3.12+<br>❌ Adds a small runtime import shim<br>❌ Slightly more complex than plain concatenation |
| **[`pinliner city fork`](https://github.com/The-city-not-present/pinliner)** | ✅ Works on Python 3.12<br>✅ Same as pinliner | ❌ Not actively maintained (~9 months)<br>❌ Fixed just enough to work<br>❌ Same as Pinliner |
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
    tree = cst.parse_module(open(os.path.join("src/project-script", mod)).read())
    for stmt in tree.body:
        if isinstance(stmt, (cst.Import, cst.ImportFrom)):
            if "pocket_build" not in stmt.code:
                imports.append(stmt.code)
        else:
            bodies.append(stmt.code)

with open("bin/project-script.py", "w") as f:
    f.write("#!/usr/bin/env python3\n")
    f.write("\n".join(sorted(set(imports))) + "\n\n")
    for body in bodies:
        f.write(body + "\n")
```

### Decision

The initial decision is to attempt to adopt **`pinliner`** as the bundler for producing the single-file script.  
It generates a deterministic, clean, human-readable script with none of the parsing fragility of the hand-rolled merger, and without the runtime import machinery of `pybundler`.

### Consequences

- The single-file build becomes **maintainable and robust**.  
- The `dev/make_script.py` logic will be simplified to:  
  1. Call `pinliner` to bundle the module.  
  2. Inject version/license metadata at the top.  
- The **PyPI module** remains the canonical importable form.  
- `.pyz` and similar formats can be layered on later with minimal change.
- Developers can still open, diff, and audit the bundled file easily.  

### Follow-up and Evolution (2025-10-13)

Attempts to implement **[`pinliner`](https://pypi.org/project/pinliner/)** failed:

- Not runnable on Python 3.12+
- Unmaintained for ~7 years  

The **[`pinliner city fork`](https://github.com/The-city-not-present/pinliner)** also failed:

- Hung during tests
- A one-off patch rather than an active fork  
- Architecture too complex for our needs  
- Simplifying its output with regex brought us back to square one  

Other tools surveyed were similarly outdated (4 years + unmaintained).  

As a result, we **pivoted to a custom AST-based merger** using Python’s built-in `ast` module — dependency-free, maintainable, and purpose-built for this project.  We opted not to adopt `libcst` as it would add a unwanted dependency to a basic script. 

That prototype matured into **[`Serger`](https://github.com/apathetic-tools/serger)**, a syntax-aware combiner now maintained as a development-only dependency.


<br/><br/>

---
---

<br/><br/>

## Adopt a Three-Tier Distribution Strategy
<a id="dec05"></a>*DEC 05 — 2025-10-11*  

### Context 

We want to reach as many people as possible and meet them where they are. 

We started with a basic stand-alone script, then as it grew more complex we made it a module to make maintenance and testing easier, but retained a stand-alone script via a hand-rolled merger script.

This decision formalizes how this project will be distributed and supported going forward.

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
3. **Single-file script** — a script CLI based on `ast` import parsing.  

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


## Target Python Version 3.10 — 2025-10-13
<a id="dec04"></a>*DEC 04 — 2025-10-13*  


### Context

We have chosen Python as our authoring languague *(see [DEC 03](#dec03)).

This project is a lightweight build system designed to remain compatible with common developer environments and continuous integration (CI) runners.  
We needed to decide which Python versions to officially support to balance modern features, runtime stability, and wide usability.

### Options Considered

The latest Python version is *3.14*.

| Version | Pros | Cons |
|---------|------|------|
| **3.8+** | ✅ Works on very old systems and some embedded CI containers | ❌ Lacks modern typing (`|` unions, `match`, `typing.Self`) used throughout the codebase.<br>❌ Adds maintenance overhead for obsolete Python releases |
| **3.10+**  | ✅ Matches Ubuntu 22.04 LTS (the baseline CI OS)<br>✅ Includes structural pattern matching, modern typing syntax, and context manager improvements | ⚠️ Slightly narrower audience, but still covers all current LTS platforms
| **3.12+** | ✅ Always the latest standard library and type system | ❌ Too restrictive; would exclude many production and CI environments |

### Platforms

| Platform | Default Python | Notes |
|-----------|----------------|-------|
| Ubuntu 22.04 LTS | 3.10 | Minimum supported baseline |
| Ubuntu 24.04 LTS | 3.12 | Current CI default |
| macOS (Homebrew / Python.org) | 3.12 | Must be user-installed |
| Windows (Microsoft Store) | 3.12 | Microsoft’s LTS release |
| Windows (Microsoft Store)<br>with WSL Ubuntu 24.04 LTS | 3.12 | Matches Ubuntu releases |
| GitHub Actions `ubuntu-latest` | 3.10 → 3.12 | Both available during transition |

### Versions

| Version | Status | Released | EOL |
|---------|--------|----------|-----|
| 3.14 | bugfix | 2025-10 | 2030-10 |
| 3.13 | bugfix | 2024-10 | 2029-10 |
| 3.12 | security | 2023-10 | 2028-10 |
| 3.11 | security | 2022-10 | 2027-10 |
| 3.10 | security | 2021-10 | 2026-10 |
| 3.9 | security | 2020-10 | 2025-10 |
| 3.8 | end of life | 2019-10-14 | 2024-10-07 |

### Decision

This project targets **Python 3.10 and newer**.  
This ensures the codebase can use modern language features while staying compatible with Ubuntu 22.04 LTS (the lowest common denominator for CI).

### Consequences

- The project can confidently rely on post–3.10 typing features and standard library APIs.  
- No need for compatibility shims for 3.8/3.9.  
- CI runs on Python 3.10–3.12 to ensure forward compatibility.  
- Users running legacy interpreters must upgrade to Python 3.10+.


<br/><br/>

---
---

<br/><br/>


## Choose Python as the Implementation Language  
<a id="dec03"></a>*DEC 03 — 2025-10-13*  


### Context

This project aims to provide a **lightweight, dependency-free build tool** that runs out of the box across Linux, macOS, and Windows — including CI environments.  
The guiding principle was that users should be able to **run it immediately and also check it into version control**, without installing toolchains, compiling binaries, or managing package dependencies.

Compiled languages such as Go or Rust would require distributing multiple binaries (x64, ARM, etc.) and rebuilding for each platform.  
By contrast, Python 3 is either preinstalled or one command away on every major platform, offering an ideal middle ground between universality and maintainability.

---

### Options Considered

| Language | Pros | Cons |
|-----------|------|------|
| **Python** | ✅ Preinstalled on most Linux distros and Windows WSL<br>✅ Simple install via Microsoft Store (Windows) or Homebrew (macOS)<br>✅ No compile step; fully introspectable source<br>✅ Mature standard library  | ⚠️ Slower startup compared to compiled binaries<br>⚠️ Weak single-file distribution tooling |
| **Go** | ✅ Cross-compiled static binaries<br>✅ Single-file executables<br>✅ Fast performance<br>✅ Fast onboarding | ❌ Must distribute a binary per architecture<br>❌ Not editable post-build |
| **Rust** | ✅ High performance<br>✅ Excellent safety | ❌ Steep learning curve<br>❌ Slower iteration cycles |
| **JavaScript / Node.js** | ✅ Familiar syntax<br>✅ Rich ecosystem | ❌ Not standard on all OSes<br>❌ Frequent package churn and version issues |
| **PHP / Ruby** | ✅ Interpreted and portable | ❌ Not standard on all OSes |
| **Bash** | ✅ Preinstalled on linux, macOS, and Windows WSL | ❌ Platform differences cause fragility<br>❌ Hard to maintain for complex logic<br>❌ Poor developer tooling

### Decision

Implement the project in **Python 3**, targeting **Python 3.10+** *(see [DEC 04](#dec04))* for baseline compatibility across Ubuntu 22.04 LTS (minimum), Ubuntu 24.04 LTS (CI), macOS, and Windows environments.  
  
Python provides a uniquely accessible combination of:

- **Zero-dependency execution**  
- **Human-readable introspection**  
- **Cross-platform availability**  
- **Ease of installation**  

This choice supports Linux (native and WSL), GitHub Actions runners, macOS, and Windows with minimal friction — matching the project’s goal of being *“a build system that fits in your pocket.”*  

The decision also aligns with the project’s principle of **transparency over performance**:  
a build tool should be something users can understand, tweak, and trust — not a black box.  
Developer accessibility and clarity outweigh raw execution speed for small, human-centric utilities.

---

### Consequences

- ✅ Runs on most systems out-of-the-box  
- ✅ Allows direct inspection and modification of the source without rebuilding  
- ⚠️ Requires a single-file bundler to be maintained  
- ⚠️ Slower execution than compiled binaries — acceptable for small workloads  
- ⚠️ Maintainers must enforce a minimum supported Python version  
- 🔄 Future `.pyz` or PyInstaller packaging options remain possible as distribution evolves  

---

> *Python wasn’t chosen for novelty — it was chosen for inclusivity and clarity.  
> A tool that builds projects should also help build understanding.*


<br/><br/>

---
---

<br/><br/>


## Choose MIT-NOAI License
<a id="dec02"></a>*DEC 02 — 2025-10-13*  


### Context

This project is designed to be freely usable, modifiable, and educational — a tool for human developers.  
However, the current landscape of AI dataset collection remains ethically and legally unsettled.  
There are no clear systems for consent, compensation, or attribution when open-source code is used in AI or ML training.  

The project makes **use of AI as a paid tool**, but distinguishes between *using AI interactively* and *being used by AI systems without consent*.

### Options Considered

- **MIT License (standard)**  
  - ✅ Maximally permissive, well-understood, and widely compatible  
  - ❌ Allows unrestricted AI scraping and reuse without credit or consent  

- **Custom MIT + “No-AI Use Rider” (MIT-NOAI)**  
  - ✅ Retains MIT’s openness while defining explicit AI/ML restrictions  
  - ✅ Aligns with human-centered reuse and consent-based ethics  
  - ⚠️ Custom clause means it’s not OSI-certified “open source”  
  - ⚠️ Enforcement and precedent remain largely untested  

### Decision

License this project under the **MIT License with an Additional “No-AI Use Rider” (MIT-NOAI)**.  
This rider explicitly prohibits using the repository’s contents for AI or ML training or dataset inclusion.  

The goal is to remain permissive and educational for **human developers**, while drawing a clear boundary against non-consensual data harvesting.

### Consequences

- Maintains openness for human collaboration and reuse  
- Protects the project from unconsented AI training use  
- May limit adoption by organizations requiring OSI-certified licenses
- Can be revised or dual-licensed once consent-based frameworks for dataset participation exist 

### Ethical Consideration

This project takes a pragmatic stance: AI assistance was essential to its creation, and avoiding its use alone will not change the broader ecosystem.  
By setting explicit licensing boundaries, this project defines **consent within a maturing system** — participating responsibly without endorsing its flaws.

---

> *AI was used in the creation of this project as a collaborative tool — not as training material.  
> This license marks that distinction clearly and transparently.*


<br/><br/>

---
---

<br/><br/>



## Use AI Assistance for Documentation and Development  
<a id="dec01"></a>*DEC 01 — 2025-10-13*


### Context

This project began as a small internal utility, not a primary product.  
The goal was to share it more broadly, but resources were limited — both in time and technical scope.  

While the main ecosystem project is written in JavaScript, this tool was better suited to Python.  
That choice expanded its potential audience but introduced additional overhead: documentation, CLI flag boilerplate, and testing all had to be rebuilt from scratch in a less familiar language.  

AI tooling (notably ChatGPT) offered a practical way to **draft, refine, and format** this material quickly, enabling the team to produce consistent, well-structured content that would have been infeasible otherwise.

### Options Considered

- **Manual authoring only**  
  - ✅ Full control and authorship transparency  
  - ❌ Significant boilerplate work  
  - ❌ Slower iteration, higher maintenance cost  

- **Automated generators (e.g. pdoc, Sphinx)**  
  - ✅ Good for API references  
  - ❌ Poor fit for narrative documentation, design rationale, or scaffolding code  

- **AI-assisted drafting and scaffolding**  
  - ✅ Accelerates code scaffolding and documentation writing  
  - ✅ Helps translate design intent into structured functions  
  - ✅ Bridges language differences between JavaScript and Python  
  - ⚠️ Requires careful oversight for accuracy and consistency  

### Decision

Adopt **AI-assisted authoring** (e.g. ChatGPT) for documentation, boilerplate, and code drafting — always guided, reviewed, and finalized by maintainers.  
This enables a small team to deliver a polished, well-documented tool rather than a one-off script tied to a single project.

### Consequences

- Enables faster iteration while keeping human authorship and intent explicit  
- Produces consistent documentation and boilerplate code with minimal overhead  
- Frees developers to focus on architecture and testing rather than boilerplate  
- The practice is disclosed transparently in documentation footers:  

  > ✨ *AI was used to help draft language, formatting, and code — plus we just love em dashes.*

- Recognizes AI as a **supporting tool**, not a substitute for understanding  

### Ethical Note

AI participation in this project is **transparent, limited, and disclosed**.  
Its use represents a pragmatic balance — taking advantage of available tools while recognizing that the broader AI ecosystem still lacks clear norms around consent and compensation.  
Until those standards exist, AI here is treated as a **paid assistant**, not a data consumer.

<br/><br/>

---
---

<br/><br/>

_Written following the [DECISIONS.md Style Guide](./DECISIONS_STYLE_GUIDE.md)._  
_This document records **why** we build things the way we do — not just **what** we built._

> ✨ *AI was used to help draft language, formatting, and code — plus we just love em dashes.*

<p align="center">
  <sub>😐 <a href="https://apathetic-tools.github.io/">Apathetic Tools</a> © <a href="./LICENSE">MIT-NOAI</a></sub>
</p>
