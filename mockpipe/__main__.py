import logging
import click

from .mockpipe import MockPipe

import time


logger = logging.getLogger()
logger.setLevel(logging.INFO)


@click.command()
@click.option(
    "--config",
    prompt="path to config",
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
def mockpipe_cli(config: str, steps: int, run_time: int):
    click.echo(f"Loading config from {config}")
    sw = MockPipe(config)

    if not steps and not run_time:
        sw.start()

    if steps and run_time:
        raise ValueError("Only one of steps or run_time can be provided")

    if steps:
        for _ in range(steps):
            sw.step()

    if run_time:
        sw.start()
        time.sleep(run_time)
        sw.stop()

    # sw.execute_action(sw.tables["foo"], sw.tables["foo"].actions["create"])


if __name__ == "__main__":
    sw = mockpipe_cli()
