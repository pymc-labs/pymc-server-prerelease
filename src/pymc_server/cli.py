import click
import sky
from typing import Any, Dict, List, Optional, Tuple, Union
from pymc_server.utils.yaml import merge_yaml
from pymc_server.launch_cli import launch as cli_launch,cli_launch_
from pymc_server.launch_cli import launch_2
from pymc_server.down_cli import down as down_cli
from pymc_server.cli_factory import setup_launch_factory, setup_status_factory
from sky.usage import usage_lib
from sky.cli import _get_shell_complete_args, _get_click_major_version, _complete_cluster_name, _NaturalOrderGroup, _DocumentedCodeCommand
from pymc_server.utils.cli_ex import jobs_launch as ex_launch


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
    #ctx.invoke(_status_test, *args, **kwargs)
    print("*args",*args)


    data = ctx.invoke(sky_status, *args, **kwargs)
    print("DATA",data)

    #ctx.invoke(sky_status, *args, **kwargs)


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
    ctx.invoke(launch_2, *args, **kwargs)
    #ctx.invoke(sky_launch, *args, **kwargs)

@setup_status_factory
@usage_lib.entrypoint
def check(*args, **kwargs):
    """ calls the sky status command by passing the click context"""
    ctx = click.get_current_context()
    #sky_check(*args, **kwargs)
    ctx.invoke(sky_check, *args, **kwargs)


@cli.command(cls=_DocumentedCodeCommand)
@click.argument('clusters',
                nargs=-1,
                required=False,
                **_get_shell_complete_args(_complete_cluster_name))
@click.option('--all',
              '-a',
              default=None,
              is_flag=True,
              help='Tear down all existing clusters.')
@click.option('--yes',
              '-y',
              is_flag=True,
              default=False,
              required=False,
              help='Skip confirmation prompt.')
@click.option(
    '--purge',
    '-p',
    is_flag=True,
    default=False,
    required=False,
    help=('(Advanced) Forcefully remove the cluster(s) from '
          'SkyPilot\'s cluster table, even if the actual cluster termination '
          'failed on the cloud. WARNING: This flag should only be set sparingly'
          ' in certain manual troubleshooting scenarios; with it set, it is the'
          ' user\'s responsibility to ensure there are no leaked instances and '
          'related resources.'))
@usage_lib.entrypoint
def down(*args, **kwargs):
    ctx = click.get_current_context()
    #sky_check(*args, **kwargs)
    ctx.invoke(down_cli, *args, **kwargs)
    """Deletes a local cluster."""


cli.add_command(status)
cli.add_command(launch)
cli.add_command(check)

if __name__ == '__main__':
    cli()

