import logging
import click
import time
import itertools
import threading
import sys

from .mockpipe import MockPipe
from .config import Config
from ._version import __version__


logger = logging.getLogger()


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
    "--config_create",
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
    "--verbose",
    help="Enable verbose logging",
    is_flag=True,
)
@click.version_option(__version__)
def mockpipe_cli(
    config_create: bool, config: str, steps: int, run_time: int, verbose: bool
):

    options_selected = sum([bool(config_create), bool(steps), bool(run_time)])
    if options_selected > 1:
        raise click.UsageError(
            "Only one of --config_create, --steps, or --run-time can be provided"
        )

    if verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.ERROR)

    if config_create:
        with open("./config.yaml", "w") as f:
            f.write(Config.get_sample_config())
        print("Sample config file created at ./config.yaml")
        return

    click.echo(f"Loading config from {config}")

    mp = MockPipe(config)

    try:
        if not verbose:  # don't display spinner if verbose logging is enabled
            stop_flag, spinner_thread = spinning_wheel("Generating")

        if not steps and not run_time and not config_create:
            mp.start()
            while True:
                time.sleep(1)

        if steps:
            for _ in range(steps):
                mp.step()
                time.sleep(mp.cnf.inter_action_delay)

        if run_time:
            mp.start()
            time.sleep(run_time)

    except KeyboardInterrupt:
        mp.stop()
        if not verbose:
            stop_flag.set()
            spinner_thread.join()
        sys.exit(0)

    finally:
        mp.stop()
        if not verbose:
            stop_flag.set()
            spinner_thread.join()


if __name__ == "__main__":
    mockpipe_cli()
