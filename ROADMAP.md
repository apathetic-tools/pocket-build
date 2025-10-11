# 🧭 Roadmap

## 🧰 CLI Parameters
Planned command-line flags for future releases:

- `--self-update` — update pocket-build itself  
- `--no-update-check` — skip automatic update check  
- `--no-colors` — disable ANSI color output  
- `--include` / `--exclude` — override config include/exclude patterns

## ⚙️ Config File Enhancements

- [ ] Allow config to be a **`.py`** file, not just JSON  
- [ ] Add key to disable update checks directly in config
- [ ] Add key to disable colors directly in config
- [ ] Add key to run quiet directly in config
- [ ] Add key to run verbose directly in config
- [ ] Provide a JSON Schema for validation and autocomplete  

## 🧩 Joiner Scripts (Build System)
Exploring bundling options for generating the single-file release:

- [ ] **tiny-python-bundler**  
- [ ] **pycat**  
- [ ] **unimport**
- [ ] Home grown script

## 🧪 Tests
- [ ] Flesh out tests for additional functionality after it has been added
- [ ] `--selftest` that runs a few minimal checks internally using Python’s `unittest`—so the user can verify that the install works without needing pytest.

## 🧑‍💻 Development 
- [ ] Deploy action when I tag a release should create a release and attach it to the tagged release.

## 💡 Ideas & Experiments
Potential quality-of-life features:

- [ ] Inject version into final bundled script  
- [ ] Add SHA-256 hashing to skip unchanged files  
- [ ] Implement `--watch` mode for live rebuilds  
- [ ] publish to PyPI, NPM, PACKAGIST, others?
