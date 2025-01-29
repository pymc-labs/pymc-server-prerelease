import click
import sky
import pymc_server
import colorama
from typing import  Dict, List, Optional, Tuple, Union
from sky import global_user_state
from sky.cli import _get_glob_clusters
from sky.backends import backend_utils
from sky import status_lib
from sky.utils import controller_utils
from sky import exceptions
from sky import core

from pymc_server.utils.yaml import (
   get_auto_stop_from_entrypoint
)

def start(
        clusters: List[str],
        entrypoint: Tuple[str, ...],
        all: bool,
        yes: bool,
        idle_minutes_to_autostop: Optional[int],
        down: bool,  # pylint: disable=redefined-outer-name
        retry_until_up: bool,
        force: bool):

    if entrypoint != None:
        auto_idle_minutes_to_autostop, auto_down = get_auto_stop_from_entrypoint(entrypoint)
        idle_minutes_to_autostop = idle_minutes_to_autostop if idle_minutes_to_autostop != None else auto_idle_minutes_to_autostop
        down = down if down != None else auto_down
    down = False if down == None else down

    # NOTE(dev): Keep the docstring consistent between the Python API and CLI.
    """Restart cluster(s).

    If a cluster is previously stopped (status is STOPPED) or failed in
    provisioning/runtime installation (status is INIT), this command will
    attempt to start the cluster.  In the latter case, provisioning and runtime
    installation will be retried.

    Auto-failover provisioning is not used when restarting a stopped
    cluster. It will be started on the same cloud, region, and zone that were
    chosen before.

    If a cluster is already in the UP status, this command has no effect.

    Examples:

    .. code-block:: bash

      # Restart a specific cluster.
      sky start cluster_name
      \b
      # Restart multiple clusters.
      sky start cluster1 cluster2
      \b
      # Restart all clusters.
      sky start -a

    """
    if down and idle_minutes_to_autostop is None:
        raise click.UsageError(
            '--idle-minutes-to-autostop must be set if --down is set.')
    to_start = []

    if not clusters and not all:
        # UX: frequently users may have only 1 cluster. In this case, be smart
        # and default to that unique choice.
        all_cluster_names = global_user_state.get_cluster_names_start_with('')
        if len(all_cluster_names) <= 1:
            clusters = all_cluster_names
        else:
            raise click.UsageError(
                '`sky start` requires either a cluster name or glob '
                '(see `sky status`), or the -a/--all flag.')

    if all:
        if len(clusters) > 0:
            click.echo('Both --all and cluster(s) specified for sky start. '
                       'Letting --all take effect.')

        # Get all clusters that are not controllers.
        clusters = [
            cluster['name']
            for cluster in global_user_state.get_clusters()
            if controller_utils.Controllers.from_name(cluster['name']) is None
        ]

    if not clusters:
        click.echo('Cluster(s) not found (tip: see `sky status`). Do you '
                   'mean to use `sky launch` to provision a new cluster?')
        return
    else:
        # Get GLOB cluster names
        clusters = _get_glob_clusters(clusters)

        for name in clusters:
            cluster_status, _ = backend_utils.refresh_cluster_status_handle(
                name)
            # A cluster may have one of the following states:
            #
            #  STOPPED - ok to restart
            #    (currently, only AWS/GCP non-spot clusters can be in this
            #    state)
            #
            #  UP - skipped, see below
            #
            #  INIT - ok to restart:
            #    1. It can be a failed-to-provision cluster, so it isn't up
            #      (Ex: launch --gpus=A100:8).  Running `sky start` enables
            #      retrying the provisioning - without setup steps being
            #      completed. (Arguably the original command that failed should
            #      be used instead; but using start isn't harmful - after it
            #      gets provisioned successfully the user can use the original
            #      command).
            #
            #    2. It can be an up cluster that failed one of the setup steps.
            #      This way 'sky start' can change its status to UP, enabling
            #      'sky ssh' to debug things (otherwise `sky ssh` will fail an
            #      INIT state cluster due to head_ip not being cached).
            #
            #      This can be replicated by adding `exit 1` to Task.setup.
            if (not force and cluster_status == status_lib.ClusterStatus.UP):
                # An UP cluster; skipping 'sky start' because:
                #  1. For a really up cluster, this has no effects (ray up -y
                #    --no-restart) anyway.
                #  2. A cluster may show as UP but is manually stopped in the
                #    UI.  If Azure/GCP: ray autoscaler doesn't support reusing,
                #    so 'sky start existing' will actually launch a new
                #    cluster with this name, leaving the original cluster
                #    zombied (remains as stopped in the cloud's UI).
                #
                #    This is dangerous and unwanted behavior!
                click.echo(f'Cluster {name} already has status UP.')
                continue

            assert force or cluster_status in (
                status_lib.ClusterStatus.INIT,
                status_lib.ClusterStatus.STOPPED), cluster_status
            to_start.append(name)
    if not to_start:
        return

    # Checks for controller clusters (jobs controller / sky serve controller).
    controllers, normal_clusters = [], []
    for name in to_start:
        if controller_utils.Controllers.from_name(name) is not None:
            controllers.append(name)
        else:
            normal_clusters.append(name)
    if controllers and normal_clusters:
        # Keep this behavior the same as _down_or_stop_clusters().
        raise click.UsageError('Starting controllers with other cluster(s) '
                               'is currently not supported.\n'
                               'Please start the former independently.')
    if controllers:
        bold = backend_utils.BOLD
        reset_bold = backend_utils.RESET_BOLD
        if len(controllers) != 1:
            raise click.UsageError(
                'Starting multiple controllers is currently not supported.\n'
                'Please start them independently.')
        if idle_minutes_to_autostop is not None:
            raise click.UsageError(
                'Autostop options are currently not allowed when starting the '
                'controllers. Use the default autostop settings by directly '
                f'calling: {bold}sky start {" ".join(controllers)}{reset_bold}')

    if not yes:
        cluster_str = 'clusters' if len(to_start) > 1 else 'cluster'
        cluster_list = ', '.join(to_start)
        click.confirm(
            f'Restarting {len(to_start)} {cluster_str}: '
            f'{cluster_list}. Proceed?',
            default=True,
            abort=True,
            show_default=True)

    for name in to_start:
        try:
            core.start(name,
                       idle_minutes_to_autostop,
                       retry_until_up,
                       down=down,
                       force=force)
        except (exceptions.NotSupportedError,
                exceptions.ClusterOwnerIdentityMismatchError) as e:
            click.echo(str(e))
        else:
            click.secho(f'Cluster {name} started.', fg='green')