import logging
import click

from src.mockpipe import mockpipe

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
def mockpipe(config: str):
    click.echo(f"Loading config from {config}")
    mockpipe(config).execute()


if __name__ == "__main__":
    mockpipe()
