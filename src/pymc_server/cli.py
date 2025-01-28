import click
import sky
from typing import Any, Dict, List, Optional, Tuple, Union
from pymc_server.utils.yaml import merge_yaml
#from pymc_server.commands.launch_cli import launch as cli_launch,cli_launch_
from pymc_server.commands.down_cli import (down as down_cli, setup_down_factory as setup_down_factory)
from pymc_server.commands.launch_cli import launch as launch_cli
from pymc_server.commands.exec_cli import exec as exec_cli
from pymc_server.commands.status_cli import status as status_cli

from pymc_server.cli_factory import setup_launch_factory, setup_status_factory, setup_exec_factory, setup_start_factory,setup_stop_factory
from sky.usage import usage_lib
from sky.cli import _get_shell_complete_args, _get_click_major_version, _complete_cluster_name, _NaturalOrderGroup, _DocumentedCodeCommand

from sky.cli import (
    status as sky_status,
    launch as sky_launch,
    check as sky_check,
    start as sky_start,
    stop as sky_stop
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
    #ctx.invoke(_status_test, *args, **kwargs)
    #print("*args",*args)
    data = ctx.invoke(status_cli, *args, **kwargs)
    #print("DATA",data)

    #ctx.invoke(sky_status, *args, **kwargs)


@setup_launch_factory
@usage_lib.entrypoint
def exec(*args, **kwargs):
    """ calls the sky status command by passing the click context"""
    ctx = click.get_current_context()
    #sky_check(*args, **kwargs)
    ctx.invoke(exec_cli, *args, **kwargs)
    #sads


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
    ctx.invoke(launch_cli, *args, **kwargs)

@setup_status_factory
@usage_lib.entrypoint
def check(*args, **kwargs):
    """ calls the sky status command by passing the click context"""
    ctx = click.get_current_context()
    #sky_check(*args, **kwargs)
    ctx.invoke(sky_check, *args, **kwargs)




@setup_start_factory
@usage_lib.entrypoint
def start(*args, **kwargs):
    ctx = click.get_current_context()
    #sky_check(*args, **kwargs)
    ctx.invoke(sky_start, *args, **kwargs)
    """Deletes a local cluster."""

@setup_stop_factory
@usage_lib.entrypoint
def stop(*args, **kwargs):
    ctx = click.get_current_context()
    #sky_check(*args, **kwargs)
    ctx.invoke(sky_stop, *args, **kwargs)
    """Deletes a local cluster."""

@setup_down_factory
@usage_lib.entrypoint
def down(*args, **kwargs):
    ctx = click.get_current_context()
    #sky_check(*args, **kwargs)
    ctx.invoke(down_cli, *args, **kwargs)
    """Deletes a local cluster."""


cli.add_command(status)
cli.add_command(launch)
cli.add_command(check)
cli.add_command(start)
cli.add_command(stop)
cli.add_command(down)
cli.add_command(exec)

if __name__ == '__main__':
    cli()

