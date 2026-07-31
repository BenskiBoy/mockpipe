import logging
import click
import time
import itertools
import threading
import sys
from typing import Union

from .mockpipe import MockPipe
from .config import Config
from ._version import __version__


def spinning_wheel(self, message: str = "Generating"):
    """Displays a spinning wheel animation until stopped."""

    spinner = itertools.cycle(["|", "/", "-", "\\"])  # Characters for the spinner
    stop_flag = threading.Event()  # Threading event to signal stopping

    def spin():
        while not stop_flag.is_set():
            sys.stdout.write(f"\r{message}... {next(spinner)}")
            sys.stdout.flush()
            time.sleep(0.1)  # Control the speed of the spinner
        sys.stdout.write(f"\r{message}... Done!    \n")  # Clear spinner

    spinner_thread = threading.Thread(target=spin)
    spinner_thread.start()
    return stop_flag, spinner_thread


@click.command()
@click.option(
    "--config-create",
    help="generate a sample config file",
    is_flag=True,
)
@click.option(
    "--config",
    help="path to yaml config file",
    type=click.Path(),
    default="config.yaml",
)
@click.option(
    "--steps",
    help="Number of steps to execute initially",
    type=int,
)
@click.option(
    "--run-time",
    help="Time to run the mockpipe process in seconds",
    type=int,
)
@click.option(
    "--dry-run",
    help="Validate the config file and exit without running anything",
    is_flag=True,
)
@click.option(
    "--output-format",
    help="Override the config file's output.format (e.g. json, csv, parquet)",
    default=None,
)
@click.option(
    "--output-path",
    help="Override the config file's output.path",
    default=None,
)
@click.option(
    "--output-url",
    help="Override the config file's output.url (used by the webhook format)",
    default=None,
)
@click.option(
    "--verbose",
    help="Enable verbose logging",
    is_flag=True,
)
@click.version_option(__version__)
def mockpipe_cli(
    config_create: bool,
    config: str,
    steps: int,
    run_time: int,
    dry_run: bool,
    output_format: str,
    output_path: str,
    output_url: str,
    verbose: bool,
):

    options_selected = sum(
        [bool(config_create), steps is not None, run_time is not None, dry_run]
    )
    if options_selected > 1:
        raise click.UsageError(
            "Only one of --config-create, --steps, --run-time, or --dry-run can be provided"
        )

    logging.basicConfig(
        level=logging.INFO if verbose else logging.ERROR,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if config_create:
        with open("./config.yaml", "w") as f:
            f.write(Config.get_sample_config())
        print("Sample config file created at ./config.yaml")
        return

    effective_config: Union[str, dict] = config
    if output_format or output_path or output_url:
        cnf_probe = Config(config)
        output_cfg = cnf_probe.config.setdefault("output", {})
        if output_format:
            output_cfg["format"] = output_format
        if output_path:
            output_cfg["path"] = output_path
        if output_url:
            output_cfg["url"] = output_url
        effective_config = cnf_probe.config

    if dry_run:
        cnf = Config(effective_config)
        cnf.load_datasets()
        click.echo("Config is valid")
        return

    click.echo(f"Loading config from {config}")

    mp = MockPipe(effective_config)

    # The spinner has no natural end point for --steps, since we know the
    # total up front - show a step counter there instead.
    show_spinner = not verbose and steps is None

    try:
        if show_spinner:
            stop_flag, spinner_thread = spinning_wheel("Generating")

        if steps is None and run_time is None and not config_create:
            mp.start()
            while True:
                time.sleep(1)

        if steps is not None:
            for i in range(steps):
                mp.step()
                if not verbose:
                    sys.stdout.write(f"\rStep {i + 1}/{steps}")
                    sys.stdout.flush()
                time.sleep(mp.cnf.inter_action_delay)
            if not verbose:
                sys.stdout.write("\n")

        if run_time is not None:
            mp.start()
            time.sleep(run_time)

    except KeyboardInterrupt:
        mp.stop()
        if show_spinner:
            stop_flag.set()
            spinner_thread.join()
        sys.exit(0)

    finally:
        mp.stop()
        if show_spinner:
            stop_flag.set()
            spinner_thread.join()


if __name__ == "__main__":
    mockpipe_cli()
