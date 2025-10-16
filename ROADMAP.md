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

- [ ] Tweak get_metadata() so it returns a small @dataclass instead of tupple.
- [ ] Tweak run_selftest() so it has a built-in quiet mode and returns a bool
- [ ] Given we think of the find/load/resolve_build_Config parse_build as all related to resolving configs, should they all live in config.py?

- [ ] Watch mode: Ignore output folder: skip files in out_base so you don’t trigger on your own output.
- [ ] Watch mode: Dynamic discovery: optionally re-expand include patterns after each rebuild, so new files are noticed.
- [ ] Watch mode: Interval tuning: 0.5–2 seconds is a good range — pick your preferred tradeoff between responsiveness and CPU cost.
- [ ] Watch mode: If your include patterns use recursion (**), you can make _collect_included_files() re-run every few rebuilds to catch newly created files — or do it every rebuild as currently.

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
