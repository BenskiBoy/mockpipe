import os
from pathlib import Path

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
        result = runner.invoke(mockpipe_cli, ["--config-create"])

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


def test_dry_run_validates_config_without_running():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("config.yaml", "w") as f:
            f.write(SAMPLE_CONFIG)

        result = runner.invoke(mockpipe_cli, ["--config", "config.yaml", "--dry-run"])

        assert result.exit_code == 0
        assert "is valid" in result.output
        # dry-run must not create the db file or run any actions
        assert not os.path.isfile("test.db")


def test_dry_run_reports_invalid_config():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("config.yaml", "w") as f:
            f.write("db_path: test.db\n")  # missing required 'tables' key

        result = runner.invoke(mockpipe_cli, ["--config", "config.yaml", "--dry-run"])

        assert result.exit_code != 0


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


def test_steps_shows_progress_counter():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("config.yaml", "w") as f:
            f.write(SAMPLE_CONFIG)

        result = runner.invoke(
            mockpipe_cli, ["--config", "config.yaml", "--steps", "3"]
        )

        assert result.exit_code == 0
        assert "Step 3/3" in result.output


def test_output_format_and_path_overrides():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("config.yaml", "w") as f:
            f.write(SAMPLE_CONFIG)  # config says output.format: json, path: extract

        result = runner.invoke(
            mockpipe_cli,
            [
                "--config",
                "config.yaml",
                "--steps",
                "2",
                "--output-format",
                "csv",
                "--output-path",
                "custom_extract",
                "--verbose",
            ],
        )

        assert result.exit_code == 0
        assert not os.path.isdir("extract")
        csv_files = list((Path("custom_extract") / "foo").glob("*.csv"))
        assert len(csv_files) == 2
