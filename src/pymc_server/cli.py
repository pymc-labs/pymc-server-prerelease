import click
import sky
from typing import Any, Dict, List, Optional, Tuple, Union
from pymc_server.utils.yaml import merge_yaml
from pymc_server.launch_cli import launch as cli_launch
from pymc_server.cli_factory import setup_launch_factory
from sky.cli import usage_lib
   

# TODO: remove, check pyproject.py for a reference to this function
@click.group()
def cli():
    pass

@click.command
def status():
    click.echo(sky.status())

cli.add_command(status)

@setup_launch_factory
@usage_lib.entrypoint
def launch(*args, **kwargs):
    """Launch a cluster or task.

    If ENTRYPOINT points to a valid YAML file, it is read in as the task
    specification. Otherwise, it is interpreted as a bash command.

    In both cases, the commands are run under the task's workdir (if specified)
    and they undergo job queue scheduling.
    """
    cli_launch(*args, **kwargs)

    """Simple program that greets NAME for a total of COUNT times."""
    #for x in range(count):
    #    click.echo(f"Hello {name}!")

cli.add_command(launch)
if __name__ == '__main__':
    cli()
