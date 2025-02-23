import click
import pymc_server
import uuid
import colorama
import multiprocessing
from typing import Any, Dict, List, Optional, Tuple, Union
import sky
from sky import core
from sky.cli import _get_managed_jobs, _get_services
from sky.utils import controller_utils, rich_utils, ux_utils

from sky.backends import backend as backend_lib
from sky import backends
from sky.backends import backend_utils
from sky.utils.cli_utils import status_utils
from sky.cli import _get_glob_clusters
from sky import status_lib

prefix = 'pymcs'
_STATUS_PROPERTY_CLUSTER_NUM_ERROR_MESSAGE = (
    '{cluster_num} cluster{plural} {verb}. Please specify {cause} '
    'cluster to show its {property}.\nUsage: `{prefix} status --{flag} <cluster>`')

def status(all: bool, refresh: bool, ip: bool, endpoints: bool,
           endpoint: Optional[int], show_managed_jobs: bool,
           show_services: bool, clusters: List[str]):
    # NOTE(dev): Keep the docstring consistent between the Python API and CLI.
    """Show clusters.

    If CLUSTERS is given, show those clusters. Otherwise, show all clusters.

    If --ip is specified, show the IP address of the head node of the cluster.
    Only available when CLUSTERS contains exactly one cluster, e.g.
    ``pymcs status --ip mycluster``.

    If --endpoints is specified, show all exposed endpoints in the cluster.
    Only available when CLUSTERS contains exactly one cluster, e.g.
    ``pymcs status --endpoints mycluster``. To query a single endpoint, you
    can use ``pymcs status mycluster --endpoint 8888``.

    The following fields for each cluster are recorded: cluster name, time
    since last launch, resources, region, zone, hourly price, status, autostop,
    command.

    Display all fields using ``pymcs status -a``.

    Each cluster can have one of the following statuses:

    - ``INIT``: The cluster may be live or down. It can happen in the following
      cases:

      - Ongoing provisioning or runtime setup. (A ``pymcs launch`` has started
        but has not completed.)

      - Or, the cluster is in an abnormal state, e.g., some cluster nodes are
        down, or the SkyPilot runtime is unhealthy. (To recover the cluster,
        try ``pymcs launch`` again on it.)

    - ``UP``: Provisioning and runtime setup have succeeded and the cluster is
      live.  (The most recent ``pymcs launch`` has completed successfully.)

    - ``STOPPED``: The cluster is stopped and the storage is persisted. Use
      ``pymcs start`` to restart the cluster.

    Autostop column:

    - Indicates after how many minutes of idleness (no in-progress jobs) the
      cluster will be autostopped. '-' means disabled.

    - If the time is followed by '(down)', e.g., '1m (down)', the cluster will
      be autodowned, rather than autostopped.

    Getting up-to-date cluster statuses:

    - In normal cases where clusters are entirely managed by SkyPilot (i.e., no
      manual operations in cloud consoles) and no autostopping is used, the
      table returned by this command will accurately reflect the cluster
      statuses.

    - In cases where clusters are changed outside of SkyPilot (e.g., manual
      operations in cloud consoles; unmanaged spot clusters getting preempted)
      or for autostop-enabled clusters, use ``--refresh`` to query the latest
      cluster statuses from the cloud providers.
    """
    # Using a pool with 2 worker to run the managed job query and pymcs serve
    # service query in parallel to speed up. The pool provides a AsyncResult
    # object that can be used as a future.
    with multiprocessing.Pool(2) as pool:
        # Do not show job queue if user specifies clusters, and if user
        # specifies --ip or --endpoint(s).
        show_managed_jobs = show_managed_jobs and not any(
            [clusters, ip, endpoints])
        show_endpoints = endpoints or endpoint is not None
        show_single_endpoint = endpoint is not None
        if show_managed_jobs:
            # Run managed job query in parallel to speed up the status query.
            managed_jobs_future = pool.apply_async(
                _get_managed_jobs,
                kwds=dict(refresh=False,
                          skip_finished=True,
                          show_all=False,
                          limit_num_jobs_to_show=not all,
                          is_called_by_user=False))

        show_services = show_services and not clusters and not ip
        if show_services:
            # Run the sky serve service query in parallel to speed up the
            # status query.
            services_future = pool.apply_async(_get_services,
                                               kwds=dict(
                                                   service_names=None,
                                                   show_all=False,
                                                   show_endpoint=False,
                                                   is_called_by_user=False))
        if ip or show_endpoints:
            if refresh:
                raise click.UsageError(
                    'Using --ip or --endpoint(s) with --refresh is not'
                    'supported for now. To fix, refresh first, '
                    'then query the IP or endpoint.')

            if ip and show_endpoints:
                with ux_utils.print_exception_no_traceback():
                    raise ValueError(
                        'Cannot specify both --ip and --endpoint(s) '
                        'at the same time.')

            if endpoint is not None and endpoints:
                with ux_utils.print_exception_no_traceback():
                    raise ValueError(
                        'Cannot specify both --endpoint and --endpoints '
                        'at the same time.')

            if len(clusters) != 1:
                with ux_utils.print_exception_no_traceback():
                    plural = 's' if len(clusters) > 1 else ''
                    cluster_num = (str(len(clusters))
                                   if len(clusters) > 0 else 'No')
                    cause = 'a single' if len(clusters) > 1 else 'an existing'
                    raise ValueError(
                        _STATUS_PROPERTY_CLUSTER_NUM_ERROR_MESSAGE.format(
                            prefix=prefix,
                            cluster_num=cluster_num,
                            plural=plural,
                            verb='specified',
                            cause=cause,
                            property='IP address' if ip else 'endpoint(s)',
                            flag='ip' if ip else
                            ('endpoint port'
                             if show_single_endpoint else 'endpoints')))
        else:
            click.echo(f'{colorama.Fore.CYAN}{colorama.Style.BRIGHT}Clusters'
                       f'{colorama.Style.RESET_ALL}')
        query_clusters: Optional[List[str]] = None
        if clusters:
            query_clusters = _get_glob_clusters(clusters, silent=ip)
        cluster_records = core.status(cluster_names=query_clusters,
                                      refresh=refresh)
        if ip or show_endpoints:
            if len(cluster_records) != 1:
                with ux_utils.print_exception_no_traceback():
                    plural = 's' if len(cluster_records) > 1 else ''
                    cluster_num = (str(len(cluster_records))
                                   if len(cluster_records) > 0 else
                                   f'{clusters[0]!r}')
                    verb = 'found' if len(cluster_records) > 0 else 'not found'
                    cause = 'a single' if len(clusters) > 1 else 'an existing'
                    raise ValueError(
                        _STATUS_PROPERTY_CLUSTER_NUM_ERROR_MESSAGE.format(
                            cluster_num=cluster_num,
                            plural=plural,
                            verb=verb,
                            cause=cause,
                            property='IP address' if ip else 'endpoint(s)',
                            flag='ip' if ip else
                            ('endpoint port'
                             if show_single_endpoint else 'endpoints')))

            cluster_record = cluster_records[0]
            if cluster_record['status'] != status_lib.ClusterStatus.UP:
                with ux_utils.print_exception_no_traceback():
                    raise RuntimeError(f'Cluster {cluster_record["name"]!r} '
                                       'is not in UP status.')
            handle = cluster_record['handle']
            if not isinstance(handle, backends.CloudVmRayResourceHandle):
                with ux_utils.print_exception_no_traceback():
                    raise ValueError('Querying IP address is not supported '
                                     'for local clusters.')

            head_ip = handle.external_ips()[0]
            if show_endpoints:
                if endpoint:
                    cluster_endpoint = core.endpoints(cluster_record['name'],
                                                      endpoint).get(
                                                          endpoint, None)
                    if not cluster_endpoint:
                        raise click.Abort(
                            f'Endpoint {endpoint} not found for cluster '
                            f'{cluster_record["name"]!r}.')
                    click.echo(cluster_endpoint)
                else:
                    cluster_endpoints = core.endpoints(cluster_record['name'])
                    assert isinstance(cluster_endpoints, dict)
                    if not cluster_endpoints:
                        raise click.Abort(f'No endpoint found for cluster '
                                          f'{cluster_record["name"]!r}.')
                    for port, port_endpoint in cluster_endpoints.items():
                        click.echo(
                            f'{colorama.Fore.BLUE}{colorama.Style.BRIGHT}{port}'
                            f'{colorama.Style.RESET_ALL}: '
                            f'{colorama.Fore.CYAN}{colorama.Style.BRIGHT}'
                            f'{port_endpoint}{colorama.Style.RESET_ALL}')
                return
            click.echo(head_ip)
            return
        hints = []
        normal_clusters = []
        controllers = []
        for cluster_record in cluster_records:
            cluster_name = cluster_record['name']
            controller = controller_utils.Controllers.from_name(cluster_name)
            if controller is not None:
                controllers.append(cluster_record)
            else:
                normal_clusters.append(cluster_record)

        num_pending_autostop = 0
        num_pending_autostop += status_utils.show_status_table(
            normal_clusters + controllers, all)

        def _try_get_future_result(future) -> Tuple[bool, Any]:
            result = None
            interrupted = False
            try:
                result = future.get()
            except KeyboardInterrupt:
                pool.terminate()
                interrupted = True
            return interrupted, result

        managed_jobs_query_interrupted = False
        if show_managed_jobs:
            click.echo(f'\n{colorama.Fore.CYAN}{colorama.Style.BRIGHT}'
                       f'Managed jobs{colorama.Style.RESET_ALL}')
            with rich_utils.safe_status('[cyan]Checking managed jobs[/]'):
                managed_jobs_query_interrupted, result = _try_get_future_result(
                    managed_jobs_future)
                if managed_jobs_query_interrupted:
                    # Set to -1, so that the controller is not considered
                    # down, and the hint for showing sky jobs queue
                    # will still be shown.
                    num_in_progress_jobs = -1
                    msg = 'KeyboardInterrupt'
                else:
                    num_in_progress_jobs, msg = result

            click.echo(msg)
            if num_in_progress_jobs is not None:
                # jobs controller is UP.
                job_info = ''
                if num_in_progress_jobs > 0:
                    plural_and_verb = ' is'
                    if num_in_progress_jobs > 1:
                        plural_and_verb = 's are'
                    job_info = (
                        f'{num_in_progress_jobs} managed job{plural_and_verb} '
                        'in progress')
                    if (num_in_progress_jobs >
                            _NUM_MANAGED_JOBS_TO_SHOW_IN_STATUS):
                        job_info += (
                            f' ({_NUM_MANAGED_JOBS_TO_SHOW_IN_STATUS} latest '
                            'ones shown)')
                    job_info += '. '
                hints.append(
                    controller_utils.Controllers.JOBS_CONTROLLER.value.
                    in_progress_hint.format(job_info=job_info))

        if show_services:
            click.echo(f'\n{colorama.Fore.CYAN}{colorama.Style.BRIGHT}'
                       f'Services{colorama.Style.RESET_ALL}')
            num_services = None
            if managed_jobs_query_interrupted:
                # The pool is terminated, so we cannot run the service query.
                msg = 'KeyboardInterrupt'
            else:
                with rich_utils.safe_status('[cyan]Checking services[/]'):
                    interrupted, result = _try_get_future_result(
                        services_future)
                    if interrupted:
                        num_services = -1
                        msg = 'KeyboardInterrupt'
                    else:
                        num_services, msg = result
            click.echo(msg)
            if num_services is not None:
                hints.append(controller_utils.Controllers.SKY_SERVE_CONTROLLER.
                             value.in_progress_hint)

        if show_managed_jobs or show_services:
            try:
                pool.close()
                pool.join()
            except SystemExit as e:
                # This is to avoid a "Exception ignored" problem caused by
                # ray worker setting the sigterm handler to sys.exit(15)
                # (see ray/_private/worker.py).
                # TODO (zhwu): Remove any importing of ray in SkyPilot.
                if e.code != 15:
                    raise

        if num_pending_autostop > 0 and not refresh:
            # Don't print this hint if there's no pending autostop or user has
            # already passed --refresh.
            plural_and_verb = ' has'
            if num_pending_autostop > 1:
                plural_and_verb = 's have'
            hints.append(f'* {num_pending_autostop} cluster{plural_and_verb} '
                         'auto{stop,down} scheduled. Refresh statuses with: '
                         f'{colorama.Style.BRIGHT}sky status --refresh'
                         f'{colorama.Style.RESET_ALL}')
        if hints:
            click.echo('\n' + '\n'.join(hints))

