<!-- Roadmap.md -->
# 🧭 Roadmap

## 🧰 CLI Parameters
Planned command-line flags for future releases:

- `--self-update` — update pocket-build itself
- `--no-update-check` — skip automatic update check

## ⚙️ Config File Enhancements

- Add key to disable update checks directly in config
- Provide a JSON Schema for validation and autocomplete
- How is IncludePath dest configured in the config file and handled?

## 🧩 Joiner Scripts (Build System)
Exploring bundling options for generating the single-file release:

- zip file: zipapp / shiv / pyinstaller --onefile

## 🧪 Tests
- verify every function has test coverage
- check for redundant tests
- test coverage report

## 🧑‍💻 Development


deployment
  - Deploy action when I tag a release should create a release and attach it to the tagged release.

review
  - main is just high level orchestration and making sure the right command is run
  
API
  - put utils into a submodule (as long as our sticher can handle it)
  - can utils/config be made into a single submodule? how does that play with the bundler?
  - do we want a way to dump the schema for documentation purposes?
  - 

load_and_validate_config
  - _validate_typed_dict likely needs to check if required fields are present

documentation
  - where do we document the structure of the project? what do we document inside it vs here?
  - where do we do longer usage documentation? README can get a bit big
  - logo? images? icon? readme banner?
  - API docs

program flow
  - how do include path dest parameters get transfered in? from the CLI? from the config? do they work?
  - how does the "include dest" affect exclude paths?
  - review the run_build flow and private functions to make sure they are not full of while-debugging logic.
  - review/add/remove all debug/trace messages with an eye for issue reports

CLI
  - add runtime cache to store last python version run (or maybe in their config if available?)
      Path.home() / ".pocket_build" / "runtime.json"


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
  <sub>😐 <a href="https://apathetic-tools.github.io/">Apathetic Tools</a> © <a href="./LICENSE">MIT-NOAI</a></sub>
</p>
