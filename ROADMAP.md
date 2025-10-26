<!-- Roadmap.md -->
# 🧭 Roadmap

## 🧰 CLI Parameters
Planned command-line flags for future releases:

- `--self-update` — update pocket-build itself
- `--no-update-check` — skip automatic update check

## ⚙️ Config File Enhancements

- [ ] Add key to disable update checks directly in config
- [ ] Provide a JSON Schema for validation and autocomplete
- [ ] How does IncludePath dest configured and handled?

## 🧩 Joiner Scripts (Build System)
Exploring bundling options for generating the single-file release:

- [ ] zip file: zipapp / shiv / pyinstaller --onefile

## 🧪 Tests

- [ ] update tests to new form
- [ ] for all runtime changes consider using mp.setitem
- [ ] make sure with monkeypatch.context is warranted
- [ ] make sure importing inside each test function is warranted
- [ ] tests should only output when they fail so we can trace them
- [ ] how to get pytest to show each file with dots for progress instead of all together?

## 🧑‍💻 Development
- [ ] Deploy action when I tag a release should create a release and attach it to the tagged release.
- [ ] put utils into a submodule
- [ ] position args 1 for input s2 for outputs
- [ ] load_config should log nice messages
- [ ] exceptions need to be dealt with before they hit main
- [ ] main is just high level orchestration and making sure the right command is run
- [ ] a helper for API folks that adds stdout, stderr, and stdout+stderr to return values and exceptions
- [ ] validation of single-warn modules should collect then output single at end (dry-run, etc)
- [ ] coerse build into builds: even if the wrong value, but warn
- [ ] what are common mispellings? second letter mispellings? may not be worth doing
- [ ] can utils/config be made into a single submodule? how does that play with the bundler?
- [ ] where do we document the structure of the project? what do we document inside it vs here?
- [ ] where do we do longer usage documentation? README can get a bit big
- [ ] log(): I didn't know about Python.logging or logging.Logger.
- [ ] log(): should it respect the env outside of runtime? atm CLI trumps env but it could set it too.
- [ ] log(): why does LOG_LEVEL=silent not work in tests?
- [ ] functions that bail out early like log() might want to validate arguments first to make sure code is okay when they won't bail out.
- [ ] _warn_keys_once: collect tags that warned then output a single message for all builds with the same error.
- [ ] maybe abstract _normalize_base_and_path in config_resolve for _include, _exclude, and _out for if statement clarity
- [ ] how do include path dest parameters get transfered in? from the CLI? from the config? do they work?
- [ ] how does the "include dest" affect exclude paths?
- [ ] add [trace] Runtime: Python 3.12.3 (CPython)
      platform.python_version(), platform.python_implementation(), sys.version
- [ ] add runtime cache to store last python version run (or maybe in their config if available?)
      Path.home() / ".pocket_build" / "runtime.json"
- [ ] clean up "base" to "root" and "_normalize_base_and_path()" to "_normalize_path_with_root()"
- [ ] validate_config should use a log() wrapper that prints a "Syntax errors in your config <filename>:" before starting error output.
- [ ] review the run_build flow and private functions to make sure they are not full of while-debugging logic.
- [ ] converge on single term for package/module vs singlefile vs pyz

## 💡 Ideas & Experiments
Potential quality-of-life features:

- [ ] split out and depend on a basic CLI module
- [ ] split out and depend on (dev-only) a make_script CLI
- [ ] split out and depend on (dev-only) a list-project CLI
- [ ] split out and depend on (dev-only) a pytest multi-target plugin
- [ ] publish to PyPI, NPM, PACKAGIST, others?
- [ ] Add partial “Gitignore-like” behavior for '**' matches in py3.10

## make_script TODO

- [ ] have it's own configuration file
- [ ] make it more agnostic (and not pocket-build specific)
- [ ] don't repeat files
- [ ] allow you to specify a file for order, then include the rest of the dir
- [ ] document decisions/rejected
- [ ] builds without a version should have timestamp

> See [REJECTED.md](REJECTED.md) for experiments and ideas that were explored but intentionally not pursued.

---

> ✨ *AI was used to help draft language, formatting, and code — plus we just love em dashes.*

<p align="center">
  <sub>😐 <a href="https://apathetic-tools.github.io/">Apathetic Tools</a> © <a href="./LICENSE">MIT-NOAI</a></sub>
</p>
