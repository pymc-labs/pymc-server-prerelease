import click
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


def setup_status_factory(func):
    options = [
        click.command(),
        click.option('--all',
                      '-a',
                      default=False,
                      is_flag=True,
                      required=False,
                      help='Show all information in full.'),
        click.option(
            '--refresh',
            '-r',
            default=False,
            is_flag=True,
            required=False,
            help='Query the latest cluster statuses from the cloud provider(s).'),
        click.option('--ip',
                      default=False,
                      is_flag=True,
                      required=False,
                      help=('Get the IP address of the head node of a cluster. This '
                            'option will override all other options. For Kubernetes '
                            'clusters, the returned IP address is the internal IP '
                            'of the head pod, and may not be accessible from outside '
                            'the cluster.')),
        click.option('--endpoints',
                      default=False,
                      is_flag=True,
                      required=False,
                      help=('Get all exposed endpoints and corresponding URLs for a'
                            'cluster. This option will override all other options.')),
        click.option('--endpoint',
                      required=False,
                      default=None,
                      type=int,
                      help=('Get the endpoint URL for the specified port number on the '
                            'cluster. This option will override all other options.')),
        click.option('--show-managed-jobs/--no-show-managed-jobs',
                      default=True,
                      is_flag=True,
                      required=False,
                      help='Also show recent in-progress managed jobs, if any.'),
        click.option('--show-services/--no-show-services',
                      default=True,
                      is_flag=True,
                      required=False,
                      help='Also show sky serve services, if any.'),
        click.argument('clusters',
                        required=False,
                        type=str,
                        nargs=-1,
                        **_get_shell_complete_args(_complete_cluster_name)),
    ]
    for option in reversed(options):
        func = option(func)
    return func

def setup_launch_factory(func):
    options = [
        click.command(cls=_DocumentedCodeCommand),
        click.argument('entrypoint',
                        required=False,
                        type=str,
                        nargs=-1,
                        **_get_shell_complete_args(_complete_file_name)),
        click.option('--pymc_module',
                      '-m',
                      required=False,
                      type=str,
                      help=('Define the PyMC module / project you need tu use')),
        click.option('--cluster',
                      '-c',
                      default=None,
                      type=str,
                      **_get_shell_complete_args(_complete_cluster_name),
                      help=_CLUSTER_FLAG_HELP),
        click.option('--dryrun',
                      default=False,
                      is_flag=True,
                      help='If True, do not actually run the job.'),
        click.option(
            '--detach-setup',
            '-s',
            default=False,
            is_flag=True,
            help=
            ('If True, run setup in non-interactive mode as part of the job itself. '
             'You can safely ctrl-c to detach from logging, and it will not interrupt '
             'the setup process. To see the logs again after detaching, use `sky logs`.'
             ' To cancel setup, cancel the job via `sky cancel`. Useful for long-'
             'running setup commands.')),
        click.option(
            '--detach-run',
            '-d',
            default=False,
            is_flag=True,
            help=('If True, as soon as a job is submitted, return from this call '
                  'and do not stream execution logs.')),
        click.option('--docker',
                      'backend_name',
                      flag_value=backends.LocalDockerBackend.NAME,
                      default=False,
                      help='If used, runs locally inside a docker container.'),
        _add_click_options(_TASK_OPTIONS_WITH_NAME + _EXTRA_RESOURCES_OPTIONS),
        click.option(
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
                  '. If not set, the cluster will not be autostopped.')),
        click.option(
            '--retry-until-up',
            '-r',
            default=False,
            is_flag=True,
            required=False,
            help=('Whether to retry provisioning infinitely until the cluster is up, '
                  'if we fail to launch the cluster on any possible region/cloud due '
                  'to unavailability errors.'),
        ),
        click.option(
            '--yes',
            '-y',
            is_flag=True,
            default=False,
            required=False,
            # Disabling quote check here, as there seems to be a bug in pylint,
            # which incorrectly recognizes the help string as a docstring.
            # pylint: disable=bad-docstring-quotes
            help='Skip confirmation prompt.'),
        click.option('--no-setup',
                      is_flag=True,
                      default=False,
                      required=False,
                      help='Skip setup phase when (re-)launching cluster.'),
        click.option(
            '--clone-disk-from',
            '--clone',
            default=None,
            type=str,
            **_get_shell_complete_args(_complete_cluster_name),
            help=('[Experimental] Clone disk from an existing cluster to launch '
                  'a new one. This is useful when the new cluster needs to have '
                  'the same data on the boot disk as an existing cluster.'))
    ]

    for option in reversed(options):
        func = option(func)
    return func
