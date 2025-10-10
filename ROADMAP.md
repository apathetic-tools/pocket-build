# 🧭 Roadmap

## 🧰 CLI Parameters
Planned command-line flags for future releases:

- `--quiet` — suppress non-error output  
- `--verbose` — show detailed logs  
- `--help` — display usage info  
- `--out` — override output directory  
- `--config` — specify custom config path  
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
- [ ] Write initial test suite  
- [ ] Add CI for basic sanity checks (copy, exclude, include)

## 🧑‍💻 Development 
- [ ] Bring in common Python development niceties (e.g. **black**, **isort**, **ruff**)  
- [ ] Add a simple Makefile or task runner for common dev commands  

## 💡 Ideas & Experiments
Potential quality-of-life features:

- [ ] Inject version into final bundled script  
- [ ] Add SHA-256 hashing to skip unchanged files  
- [ ] Implement `--watch` mode for live rebuilds  