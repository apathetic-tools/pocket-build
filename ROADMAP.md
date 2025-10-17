<!-- Roadmap.md -->
# 🧭 Roadmap

## 🧰 CLI Parameters
Planned command-line flags for future releases:

- `--self-update` — update pocket-build itself
- `--no-update-check` — skip automatic update check

## ⚙️ Config File Enhancements

- [ ] Add key to disable update checks directly in config
- [ ] Provide a JSON Schema for validation and autocomplete

## 🧩 Joiner Scripts (Build System)
Exploring bundling options for generating the single-file release:

- [ ] zip file: zipapp / shiv / pyinstaller --onefile

## 🧪 Tests


## 🧑‍💻 Development
- [ ] Deploy action when I tag a release should create a release and attach it to the tagged release.

- [ ] Given we think of the find/load/resolve_build_Config parse_build as all related to resolving configs, should they all live in config.py?

## 💡 Ideas & Experiments
Potential quality-of-life features:

- [ ] submodule shims in .py for import parity and no testing runtime fixture (though it may still be useful for IDE)
- [ ] publish to PyPI, NPM, PACKAGIST, others?

> See [REJECTED.md](REJECTED.md) for experiments and ideas that were explored but intentionally not pursued.

---

> ✨ *AI was used to help draft language, formatting, and code — plus we just love em dashes.*

<p align="center">
  <sub>😐 <a href="https://apathetic-tools.github.io/">Apathetic Tools</a> © <a href="./LICENSE">MIT-NOAI</a></sub>
</p>
