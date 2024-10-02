import click
import sky
from typing import Any, Dict, List, Optional, Tuple, Union
from pymc_server.utils.yaml import merge_yaml
from pymc_server.launch_cli import launch as cli_launch,cli_launch_
from pymc_server.cli_factory import setup_launch_factory, setup_status_factory
from sky.usage import usage_lib
from pymc_server.utils.cli_ex import launch as ex_launch


from sky.cli import (
    status as sky_status,
    launch as sky_launch,
    check as sky_check
)
   

# TODO: remove, check pyproject.py for a reference to this function
@click.group()
def cli():
    pass

@setup_status_factory
@usage_lib.entrypoint
def status(*args, **kwargs):
    """ calls the sky status command by passing the click context"""
    ctx = click.get_current_context()
    ctx.invoke(sky_status, *args, **kwargs)


@setup_launch_factory
@usage_lib.entrypoint
def launch(*args, **kwargs):
    """Launch a cluster or task.

    If ENTRYPOINT points to a valid YAML file, it is read in as the task
    specification. Otherwise, it is interpreted as a bash command.

    In both cases, the commands are run under the task's workdir (if specified)
    and they undergo job queue scheduling.
    """
    #  cli_launch(*args, **kwargs)
    ctx = click.get_current_context()
    ctx.invoke(cli_launch_, *args, **kwargs)

    #ctx.invoke(sky_launch, *args, **kwargs)

@setup_status_factory
@usage_lib.entrypoint
def check(*args, **kwargs):
    """ calls the sky status command by passing the click context"""
    ctx = click.get_current_context()
    #sky_check(*args, **kwargs)
    ctx.invoke(sky_check, *args, **kwargs)


cli.add_command(status)
cli.add_command(launch)
cli.add_command(check)

if __name__ == '__main__':
    cli()

