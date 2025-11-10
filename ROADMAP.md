<!-- Roadmap.md -->
# 🧭 Roadmap

## 🧰 CLI Parameters
Planned command-line flags for future releases:

- `--self-update` — update pocket-build itself
- `--no-update-check` — skip automatic update check

## ⚙️ Config File Enhancements

- Add key to disable update checks directly in config
- Provide a JSON Schema for validation and autocomplete

## 🧩 Joiner Scripts (Build System)
Exploring bundling options for generating the single-file release:

- zip file: zipapp / shiv / pyinstaller --onefile

## 🧪 Tests

## 🧑‍💻 Development


deployment
  - Deploy action when I tag a release should create a release and attach it to the tagged release.
  
API
  - put utils into a submodule (as long as our sticher can handle it)
  - can utils/config be made into a single submodule? how does that play with the bundler?
  - do we want a way to dump the schema for documentation purposes?

documentation
  - where do we document the structure of the project? what do we document inside it vs here?
  - where do we do longer usage documentation? README can get a bit big
  - logo? images? icon? readme banner?
  - API docs

## 💡 Ideas & Experiments
Potential quality-of-life features:

- split out and depend on a basic CLI module
- split out and depend on (dev-only) a make_script CLI
- split out and depend on (dev-only) a list-project CLI
- split out and depend on (dev-only) a pytest multi-target plugin
- publish to PyPI, NPM, PACKAGIST, others?
- Add partial “Gitignore-like” behavior for '**' matches in py3.10

## make_script TODO

- have it's own configuration file
- make it more agnostic (and not pocket-build specific)
- don't repeat files
- allow you to specify a file for order, then include the rest of the dir
- document decisions/rejected
- builds without a version should have timestamp

> See [REJECTED.md](REJECTED.md) for experiments and ideas that were explored but intentionally not pursued.

---

> ✨ *AI was used to help draft language, formatting, and code — plus we just love em dashes.*

<p align="center">
  <sub>😐 <a href="https://apathetic-tools.github.io/">Apathetic Tools</a> © <a href="./LICENSE">MIT-aNOAI</a></sub>
</p>
