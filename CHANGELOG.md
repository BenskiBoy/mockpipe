## Changelog

### 0.0.6 - 2026-07-31

* fix `pip install mockpipe` crashing on import due to a missing `jsonlines` runtime dependency
* move `black`/`pytest`/`pytest-cov` out of runtime `install_requires` into a `dev` extra (they were also breaking installs on Python 3.8, since the pinned `black` version has no 3.8 wheels)
* CI and `make install-dev` now install from the same pinned `dev` extra instead of duplicating version pins in three places

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