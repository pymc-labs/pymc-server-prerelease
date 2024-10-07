import os
from typing import Any, Dict, List, Optional, Tuple, Union
import click
import colorama

from sky import global_user_state, exceptions, core
from sky.usage import usage_lib
from sky.utils import controller_utils,subprocess_utils
from rich import progress as rich_progress


from sky.cli import _get_glob_clusters

prefix = "pymcs"
def local_down():
    """Deletes a local cluster."""
    cluster_removed = False

    path_to_package = os.path.dirname(os.path.dirname(__file__))
    down_script_path = os.path.join(path_to_package, 'sky/utils/kubernetes',
                                    'delete_cluster.sh')

    cwd = os.path.dirname(os.path.abspath(down_script_path))
    run_command = shlex.split(down_script_path)

    # Setup logging paths
    run_timestamp = backend_utils.get_run_timestamp()
    log_path = os.path.join(constants.SKY_LOGS_DIRECTORY, run_timestamp,
                            'local_down.log')
    tail_cmd = 'tail -n100 -f ' + log_path

    with rich_utils.safe_status('[bold cyan]Removing local cluster...'):
        style = colorama.Style
        click.echo('To view detailed progress: '
                   f'{style.BRIGHT}{tail_cmd}{style.RESET_ALL}')
        returncode, stdout, stderr = log_lib.run_with_log(cmd=run_command,
                                                          log_path=log_path,
                                                          require_outputs=True,
                                                          stream_logs=False,
                                                          cwd=cwd)
        stderr = stderr.replace('No kind clusters found.\n', '')

        if returncode == 0:
            cluster_removed = True
        elif returncode == 100:
            click.echo('\nLocal cluster does not exist.')
        else:
            with ux_utils.print_exception_no_traceback():
                raise RuntimeError(
                    'Failed to create local cluster. '
                    f'Stdout: {stdout}'
                    f'\nError: {style.BRIGHT}{stderr}{style.RESET_ALL}')
    if cluster_removed:
        # Run sky check
        with rich_utils.safe_status('[bold cyan]Running sky check...'):
            sky_check.check(clouds=['kubernetes'], quiet=True)
        click.echo(
            f'{colorama.Fore.GREEN}Local cluster removed.{style.RESET_ALL}')

def down(
    clusters: List[str],
    all: Optional[bool],  # pylint: disable=redefined-builtin
    yes: bool,
    purge: bool,
):
    # NOTE(dev): Keep the docstring consistent between the Python API and CLI.
    """Tear down cluster(s).

    CLUSTER is the name of the cluster (or glob pattern) to tear down.  If both
    CLUSTER and ``--all`` are supplied, the latter takes precedence.

    Tearing down a cluster will delete all associated resources (all billing
    stops), and any data on the attached disks will be lost.  Accelerators
    (e.g., TPUs) that are part of the cluster will be deleted too.


    Examples:

    .. code-block:: bash

      # Tear down a specific cluster.
      sky down cluster_name
      \b
      # Tear down multiple clusters.
      sky down cluster1 cluster2
      \b
      # Tear down all clusters matching glob pattern 'cluster*'.
      sky down "cluster*"
      \b
      # Tear down all existing clusters.
      sky down -a

    """
    _down_or_stop_clusters(clusters,
                           apply_to_all=all,
                           down=True,
                           no_confirm=yes,
                           purge=purge)


def _down_or_stop_clusters(
        names: List[str],
        apply_to_all: Optional[bool],
        down: bool,  # pylint: disable=redefined-outer-name
        no_confirm: bool,
        purge: bool = False,
        idle_minutes_to_autostop: Optional[int] = None) -> None:
    """Tears down or (auto-)stops a cluster (or all clusters).

    Controllers (jobs controller and sky serve controller) can only be
    terminated if the cluster name is explicitly and uniquely specified (not
    via glob).
    """
    if down:
        command = 'down'
    elif idle_minutes_to_autostop is not None:
        command = 'autostop'
    else:
        command = 'stop'
    if not names and apply_to_all is None:
        # UX: frequently users may have only 1 cluster. In this case, 'sky
        # stop/down' without args should be smart and default to that unique
        # choice.
        all_cluster_names = global_user_state.get_cluster_names_start_with('')
        if len(all_cluster_names) <= 1:
            names = all_cluster_names
        else:
            raise click.UsageError(
                f'` {command}` requires either a cluster name or glob '
                f'(see `{prefix} status`), or the -a/--all flag.')

    operation = 'Terminating' if down else 'Stopping'
    if idle_minutes_to_autostop is not None:
        is_cancel = idle_minutes_to_autostop < 0
        verb = 'Cancelling' if is_cancel else 'Scheduling'
        option_str = 'down' if down else 'stop'
        if is_cancel:
            option_str = '{stop,down}'
        operation = f'{verb} auto{option_str} on'

    if len(names) > 0:
        controllers = [
            name for name in names
            if controller_utils.Controllers.from_name(name) is not None
        ]
        controllers_str = ', '.join(map(repr, controllers))
        names = [
            name for name in _get_glob_clusters(names)
            if controller_utils.Controllers.from_name(name) is None
        ]

        # Make sure the controllers are explicitly specified without other
        # normal clusters.
        if controllers:
            if len(names) != 0:
                names_str = ', '.join(map(repr, names))
                raise click.UsageError(
                    f'{operation} controller(s) '
                    f'{controllers_str} with other cluster(s) '
                    f'{names_str} is currently not supported.\n'
                    f'Please omit the controller(s) {controllers}.')
            if len(controllers) > 1:
                raise click.UsageError(
                    f'{operation} multiple controllers '
                    f'{controllers_str} is currently not supported.\n'
                    f'Please specify only one controller.')
            controller_name = controllers[0]
            if not down:
                raise click.UsageError(
                    f'{operation} controller(s) '
                    f'{controllers_str} is currently not supported.')
            else:
                controller = controller_utils.Controllers.from_name(
                    controller_name)
                assert controller is not None
                hint_or_raise = _CONTROLLER_TO_HINT_OR_RAISE[controller]
                try:
                    # TODO(zhwu): This hint or raise is not transactional, which
                    # means even if it passed the check with no in-progress spot
                    # or service and prompt the confirmation for termination,
                    # a user could still do a `sky jobs launch` or a
                    # `sky serve up` before typing the delete, causing a leaked
                    # managed job or service. We should make this check atomic
                    # with the termination.
                    hint_or_raise(controller_name)
                except (exceptions.ClusterOwnerIdentityMismatchError,
                        RuntimeError) as e:
                    if purge:
                        click.echo(common_utils.format_exception(e))
                    else:
                        raise
                confirm_str = 'delete'
                input_prefix = ('Since --purge is set, errors will be ignored '
                                'and controller will be removed from '
                                'local state.\n') if purge else ''
                user_input = click.prompt(
                    f'{input_prefix}'
                    f'To proceed, please type {colorama.Style.BRIGHT}'
                    f'{confirm_str!r}{colorama.Style.RESET_ALL}',
                    type=str)
                if user_input != confirm_str:
                    raise click.Abort()
                no_confirm = True
        names += controllers

    if apply_to_all:
        all_clusters = global_user_state.get_clusters()
        if len(names) > 0:
            click.echo(
                f'Both --all and cluster(s) specified for `{prefix} {command}`. '
                'Letting --all take effect.')
        # We should not remove controllers when --all is specified.
        # Otherwise, it would be very easy to accidentally delete a controller.
        names = [
            record['name']
            for record in all_clusters
            if controller_utils.Controllers.from_name(record['name']) is None
        ]

    clusters = []
    for name in names:
        handle = global_user_state.get_handle_from_cluster_name(name)
        if handle is None:
            # This codepath is used for 'sky down -p <controller>' when the
            # controller is not in 'sky status'.  Cluster-not-found message
            # should've been printed by _get_glob_clusters() above.
            continue
        clusters.append(name)
    usage_lib.record_cluster_name_for_current_operation(clusters)

    if not clusters:
        click.echo(f'Cluster(s) not found (tip: see `{prefix} status`).')
        return

    if not no_confirm and len(clusters) > 0:
        cluster_str = 'clusters' if len(clusters) > 1 else 'cluster'
        cluster_list = ', '.join(clusters)
        click.confirm(
            f'{operation} {len(clusters)} {cluster_str}: '
            f'{cluster_list}. Proceed?',
            default=True,
            abort=True,
            show_default=True)

    plural = 's' if len(clusters) > 1 else ''
    progress = rich_progress.Progress(transient=True,
                                      redirect_stdout=False,
                                      redirect_stderr=False)
    task = progress.add_task(
        f'[bold cyan]{operation} {len(clusters)} cluster{plural}[/]',
        total=len(clusters))

    def _down_or_stop(name: str):
        success_progress = False
        if idle_minutes_to_autostop is not None:
            try:
                core.autostop(name, idle_minutes_to_autostop, down)
            except (exceptions.NotSupportedError,
                    exceptions.ClusterNotUpError) as e:
                message = str(e)
            else:  # no exception raised
                success_progress = True
                message = (f'{colorama.Fore.GREEN}{operation} '
                           f'cluster {name!r}...done{colorama.Style.RESET_ALL}')
                if idle_minutes_to_autostop >= 0:
                    option_str = 'down' if down else 'stop'
                    passive_str = 'downed' if down else 'stopped'
                    plural = 's' if idle_minutes_to_autostop != 1 else ''
                    message += (
                        f'\n  The cluster will be auto{passive_str} after '
                        f'{idle_minutes_to_autostop} minute{plural} of '
                        'idleness.'
                        f'\n  To cancel the auto{option_str}, run: '
                        f'{colorama.Style.BRIGHT}'
                        f'{prefix} autostop {name} --cancel'
                        f'{colorama.Style.RESET_ALL}')
        else:
            try:
                if down:
                    core.down(name, purge=purge)
                else:
                    core.stop(name, purge=purge)
            except RuntimeError as e:
                message = (
                    f'{colorama.Fore.RED}{operation} cluster {name}...failed. '
                    f'{colorama.Style.RESET_ALL}'
                    f'\nReason: {common_utils.format_exception(e)}.')
            except (exceptions.NotSupportedError,
                    exceptions.ClusterOwnerIdentityMismatchError) as e:
                message = str(e)
            else:  # no exception raised
                message = (
                    f'{colorama.Fore.GREEN}{operation} cluster {name}...done.'
                    f'{colorama.Style.RESET_ALL}')
                if not down:
                    message += ('\n  To restart the cluster, run: '
                                f'{colorama.Style.BRIGHT}{prefix} start {name}'
                                f'{colorama.Style.RESET_ALL}')
                success_progress = True

        progress.stop()
        click.echo(message)
        if success_progress:
            progress.update(task, advance=1)
        progress.start()

    with progress:
        subprocess_utils.run_in_parallel(_down_or_stop, clusters)
        progress.live.transient = False
        # Make sure the progress bar not mess up the terminal.
        progress.refresh()