import click
import sky
from typing import Any, Dict, List, Optional, Tuple, Union
from pymc_server.utils.yaml import merge_yaml
from pymc_server.launch_cli import launch as cli_launch
from sky.cli import (
    _DocumentedCodeCommand,
    _get_shell_complete_args,
    _complete_file_name,
    _complete_cluster_name,
    _CLUSTER_FLAG_HELP,
    _TASK_OPTIONS_WITH_NAME,
    _EXTRA_RESOURCES_OPTIONS,
    usage_lib,
    backends,
    _add_click_options
   
)

# TODO: remove, check pyproject.py for a reference to this function
@click.group()
def cli():
    pass

@click.command()
#@click.option('--count', default=1, help='Number of greetings.')
#@click.option('--name', prompt='Your name',
#              help='The person to greet.')
def status():
    click.echo(sky.status())
    #  click.echo(core_status())
    """Simple program that greets NAME for a total of COUNT times."""
    #for x in range(count):
    #    click.echo(f"Hello {name}!")

cli.add_command(status)

@cli.command(cls=_DocumentedCodeCommand)
@click.argument('entrypoint',
                required=False,
                type=str,
                nargs=-1,
                **_get_shell_complete_args(_complete_file_name))
@click.option('--cluster',
              '-c',
              default=None,
              type=str,
              **_get_shell_complete_args(_complete_cluster_name),
              help=_CLUSTER_FLAG_HELP)
@click.option('--dryrun',
              default=False,
              is_flag=True,
              help='If True, do not actually run the job.')
@click.option(
    '--detach-setup',
    '-s',
    default=False,
    is_flag=True,
    help=
    ('If True, run setup in non-interactive mode as part of the job itself. '
     'You can safely ctrl-c to detach from logging, and it will not interrupt '
     'the setup process. To see the logs again after detaching, use `sky logs`.'
     ' To cancel setup, cancel the job via `sky cancel`. Useful for long-'
     'running setup commands.'))
@click.option(
    '--detach-run',
    '-d',
    default=False,
    is_flag=True,
    help=('If True, as soon as a job is submitted, return from this call '
          'and do not stream execution logs.'))
@click.option('--docker',
              'backend_name',
              flag_value=backends.LocalDockerBackend.NAME,
              default=False,
              help='If used, runs locally inside a docker container.')
@_add_click_options(_TASK_OPTIONS_WITH_NAME + _EXTRA_RESOURCES_OPTIONS)
@click.option(
    '--idle-minutes-to-autostop',
    '-i',
    default=None,
    type=int,
    required=False,
    help=('Automatically stop the cluster after this many minutes '
          'of idleness, i.e., no running or pending jobs in the cluster\'s job '
          'queue. Idleness gets reset whenever setting-up/running/pending jobs '
          'are found in the job queue. '
          'Setting this flag is equivalent to '
          'running ``sky launch -d ...`` and then ``sky autostop -i <minutes>``'
          '. If not set, the cluster will not be autostopped.'))
@click.option(
    '--down',
    default=False,
    is_flag=True,
    required=False,
    help=
    ('Autodown the cluster: tear down the cluster after all jobs finish '
     '(successfully or abnormally). If --idle-minutes-to-autostop is also set, '
     'the cluster will be torn down after the specified idle time. '
     'Note that if errors occur during provisioning/data syncing/setting up, '
     'the cluster will not be torn down for debugging purposes.'),
)
@click.option(
    '--retry-until-up',
    '-r',
    default=False,
    is_flag=True,
    required=False,
    help=('Whether to retry provisioning infinitely until the cluster is up, '
          'if we fail to launch the cluster on any possible region/cloud due '
          'to unavailability errors.'),
)
@click.option(
    '--yes',
    '-y',
    is_flag=True,
    default=False,
    required=False,
    # Disabling quote check here, as there seems to be a bug in pylint,
    # which incorrectly recognizes the help string as a docstring.
    # pylint: disable=bad-docstring-quotes
    help='Skip confirmation prompt.')
@click.option('--no-setup',
              is_flag=True,
              default=False,
              required=False,
              help='Skip setup phase when (re-)launching cluster.')
@click.option(
    '--clone-disk-from',
    '--clone',
    default=None,
    type=str,
    **_get_shell_complete_args(_complete_cluster_name),
    help=('[Experimental] Clone disk from an existing cluster to launch '
          'a new one. This is useful when the new cluster needs to have '
          'the same data on the boot disk as an existing cluster.'))
@usage_lib.entrypoint
def launch(
    entrypoint: Tuple[str, ...],
    cluster: Optional[str],
    dryrun: bool,
    detach_setup: bool,
    detach_run: bool,
    backend_name: Optional[str],
    name: Optional[str],
    workdir: Optional[str],
    cloud: Optional[str],
    region: Optional[str],
    zone: Optional[str],
    gpus: Optional[str],
    cpus: Optional[str],
    memory: Optional[str],
    instance_type: Optional[str],
    num_nodes: Optional[int],
    use_spot: Optional[bool],
    image_id: Optional[str],
    env_file: Optional[Dict[str, str]],
    env: List[Tuple[str, str]],
    disk_size: Optional[int],
    disk_tier: Optional[str],
    ports: Tuple[str],
    idle_minutes_to_autostop: Optional[int],
    down: bool,  # pylint: disable=redefined-outer-name
    retry_until_up: bool,
    yes: bool,
    no_setup: bool,
    clone_disk_from: Optional[str],
):
    """Launch a cluster or task.

    If ENTRYPOINT points to a valid YAML file, it is read in as the task
    specification. Otherwise, it is interpreted as a bash command.

    In both cases, the commands are run under the task's workdir (if specified)
    and they undergo job queue scheduling.
    """
    cli_launch(entrypoint)

    """Simple program that greets NAME for a total of COUNT times."""
    #for x in range(count):
    #    click.echo(f"Hello {name}!")

cli.add_command(launch)
if __name__ == '__main__':
    cli()
