import os

from click.testing import CliRunner

from mockpipe.__main__ import mockpipe_cli
from mockpipe._version import __version__


SAMPLE_CONFIG = """
db_path: test.db
delete_behaviour: soft
inter_action_delay: 0.01

output:
  format: json
  path: extract

tables:
  - name: foo
    fields:
      - name: id
        type: int
        value: increment
        is_pk: true
    actions:
      - name: create
        action: create
        frequency: 1.0
"""


def test_config_create_writes_sample_config():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(mockpipe_cli, ["--config_create"])

        assert result.exit_code == 0
        assert os.path.isfile("./config.yaml")
        assert "Sample config file created" in result.output


def test_version_option():
    runner = CliRunner()
    result = runner.invoke(mockpipe_cli, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.output


def test_mutually_exclusive_options_rejected():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("config.yaml", "w") as f:
            f.write(SAMPLE_CONFIG)

        result = runner.invoke(
            mockpipe_cli, ["--config", "config.yaml", "--steps", "1", "--run-time", "1"]
        )

        assert result.exit_code != 0
        assert "Only one of" in result.output


def test_steps_zero_does_nothing_and_exits():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("config.yaml", "w") as f:
            f.write(SAMPLE_CONFIG)

        result = runner.invoke(
            mockpipe_cli, ["--config", "config.yaml", "--steps", "0", "--verbose"]
        )

        assert result.exit_code == 0


def test_steps_runs_requested_number_of_steps():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("config.yaml", "w") as f:
            f.write(SAMPLE_CONFIG)

        result = runner.invoke(
            mockpipe_cli, ["--config", "config.yaml", "--steps", "3", "--verbose"]
        )

        assert result.exit_code == 0

        import duckdb

        conn = duckdb.connect("test.db")
        count = conn.sql("select count(*) as cnt from foo").fetchone()[0]
        assert count == 3
