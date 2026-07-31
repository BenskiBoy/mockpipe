## Changelog

### 0.0.7 - 2026-07-31

* add upfront pydantic-based structural validation for config files (missing/wrong-type keys now get clear, unified errors before the deeper semantic validation runs)
* add a Parquet exporter (`output.format: parquet`), alongside the existing JSON/CSV options
* update README: refresh the "Future Enhancements" list to drop already-completed items, document the `parquet` output format

### 0.0.6 - 2026-07-31

* fix `pip install mockpipe` crashing on import due to a missing `jsonlines` runtime dependency
* fix `pip install mockpipe` crashing on first real use due to a missing `pandas` runtime dependency (`db_connector.py`'s `.to_df()` calls need it)
* move `black`/`pytest`/`pytest-cov` out of runtime `install_requires` into a `dev` extra (they were also breaking installs on Python 3.8, since the pinned `black` version has no 3.8 wheels)
* CI and `make install-dev` now install from the same pinned `dev` extra instead of duplicating version pins in three places
* **fix action `frequency` being completely ignored** - actions were selected with uniform random chance regardless of their configured frequency; selection is now correctly weighted
* fix crash when `effect_count` is written as a bare YAML integer (e.g. `effect_count: 1`) instead of a quoted string
* fix static values with embedded parentheses (e.g. `static("Smith & Sons (Ltd)")`) failing to parse
* fix `\"` inside a quoted `static(...)` value not actually being unescaped
* add a lock around shared pipeline state so `execute_action()` can safely be called directly while the background `start()` thread is also running
* fix mutable default arguments across `Action`, `Field`, `Imposter`, and `Table.evaluate_imposter`
* wire up `flake8` and `mypy` in CI (previously defined as `Makefile` targets but never actually run)
* add test coverage for `MockPipe`, `DBConnector`, and the CLI - none of these had any tests before
* add `full_load`: every `full_load.frequency` recorded changes, export a full snapshot of every table's current rows alongside the normal incremental change stream
* add a metadata table tracking iteration count across runs against the same `db_path`, so `full_load`'s schedule resumes instead of restarting at zero
* add `--dry-run` CLI flag to validate a config file and exit without running anything

### 0.0.5 - 2026-07-31

* improve config validation error messages (empty/non-mapping YAML)
* fix --verbose so it actually produces log output
* fix --steps 0 / --run-time 0 silently running forever instead of doing nothing
* fix several misleading type hints (see PR #8)

### 0.0.4 - 2026-07-31

* fix several crash-on-first-use bugs in config validation and action execution (see PR #7)

### 0.0.3 - 2025-06-09

* fix crashes with string values containing `'` or `"`
* add more examples
* abstract out exporter to allow for custom exporter types

### 0.0.2 - 2025-01-02

* README overhall
* Enforce action result limit
* couple small bug fixes relating to faker functionality
* cli command for creating a sample config file
* Add spinner to cli utility as well as better exit handling

### 0.0.1 - 2024-12-31

* First release