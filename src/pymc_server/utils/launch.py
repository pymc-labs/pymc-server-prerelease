from sky import Task
import sky
import click
import colorama
from sky.backends import backend as backend_lib
from sky.backends import backend_utils
from sky.utils import controller_utils

from sky import backends
from sky.utils import timeline
from sky.usage import usage_lib
from sky import optimizer
from typing import  Dict, List, Optional, Tuple, Union
from sky import exceptions
from sky import check as sky_check
from sky.execution import _execute





def launch_with_confirm(
    task: Task,
    backend: backends.Backend,
    cluster: Optional[str],
    *,
    dryrun: bool,
    detach_run: bool,
    detach_setup: bool = False,
    no_confirm: bool = False,
    idle_minutes_to_autostop: Optional[int] = None,
    down: bool = False,  # pylint: disable=redefined-outer-name
    retry_until_up: bool = False,
    no_setup: bool = False,
    clone_disk_from: Optional[str] = None,
):
    """Launch a cluster with a Task."""
    if cluster is None:
        cluster = backend_utils.generate_cluster_name()

    clone_source_str = ''
    if clone_disk_from is not None:
        clone_source_str = f' from the disk of {clone_disk_from!r}'
        task, _ = backend_utils.check_can_clone_disk_and_override_task(
            clone_disk_from, cluster, task)

    with sky.Dag() as dag:
        dag.add(task)

    maybe_status, handle = backend_utils.refresh_cluster_status_handle(cluster)
    if maybe_status is None:
        # Show the optimize log before the prompt if the cluster does not exist.
        try:
            sky_check.get_cached_enabled_clouds_or_refresh(
                raise_if_no_cloud_access=True)
        except exceptions.NoCloudAccessError as e:
            # Catch the exception where the public cloud is not enabled, and
            # make it yellow for better visibility.
            with ux_utils.print_exception_no_traceback():
                raise RuntimeError(f'{colorama.Fore.YELLOW}{e}'
                                   f'{colorama.Style.RESET_ALL}') from e
        dag = sky.optimize(dag)
    task = dag.tasks[0]

    if handle is not None:
        backend.check_resources_fit_cluster(handle, task)

    confirm_shown = False
    if not no_confirm:
        # Prompt if (1) --cluster is None, or (2) cluster doesn't exist, or (3)
        # it exists but is STOPPED.
        prompt = None
        if maybe_status is None:
            cluster_str = '' if cluster is None else f' {cluster!r}'
            prompt = (
                f'Launching a new cluster{cluster_str}{clone_source_str}. '
                'Proceed?')
        elif maybe_status == status_lib.ClusterStatus.STOPPED:
            prompt = f'Restarting the stopped cluster {cluster!r}. Proceed?'
        if prompt is not None:
            confirm_shown = True
            click.confirm(prompt, default=True, abort=True, show_default=True)

    if not confirm_shown:
        click.secho(f'Running task on cluster {cluster}...', fg='yellow')

    launch(
        dag,
        dryrun=dryrun,
        stream_logs=True,
        cluster_name=cluster,
        detach_setup=detach_setup,
        detach_run=detach_run,
        backend=backend,
        idle_minutes_to_autostop=idle_minutes_to_autostop,
        down=down,
        retry_until_up=retry_until_up,
        no_setup=no_setup,
        clone_disk_from=clone_disk_from,
    )

@timeline.event
@usage_lib.entrypoint
def launch(
    task: Union['pymcs.Task', 'pymcs.Dag'],
    cluster_name: Optional[str] = None,
    retry_until_up: bool = False,
    idle_minutes_to_autostop: Optional[int] = None,
    dryrun: bool = False,
    down: bool = False,
    stream_logs: bool = True,
    backend: Optional[backends.Backend] = None,
    optimize_target: optimizer.OptimizeTarget = optimizer.OptimizeTarget.COST,
    detach_setup: bool = False,
    detach_run: bool = False,
    no_setup: bool = False,
    clone_disk_from: Optional[str] = None,
    # Internal only:
    # pylint: disable=invalid-name
    _is_launched_by_jobs_controller: bool = False,
    _is_launched_by_sky_serve_controller: bool = False,
    _disable_controller_check: bool = False,
) -> Tuple[Optional[int], Optional[backends.ResourceHandle]]:
    # NOTE(dev): Keep the docstring consistent between the Python API and CLI.
    """Launch a cluster or task.

    The task's setup and run commands are executed under the task's workdir
    (when specified, it is synced to remote cluster).  The task undergoes job
    queue scheduling on the cluster.

    Currently, the first argument must be a sky.Task, or (EXPERIMENTAL advanced
    usage) a sky.Dag. In the latter case, currently it must contain a single
    task; support for pipelines/general DAGs are in experimental branches.

    Args:
        task: sky.Task, or sky.Dag (experimental; 1-task only) to launch.
        cluster_name: name of the cluster to create/reuse.  If None,
            auto-generate a name.
        retry_until_up: whether to retry launching the cluster until it is
            up.
        idle_minutes_to_autostop: automatically stop the cluster after this
            many minute of idleness, i.e., no running or pending jobs in the
            cluster's job queue. Idleness gets reset whenever setting-up/
            running/pending jobs are found in the job queue. Setting this
            flag is equivalent to running
            ``sky.launch(..., detach_run=True, ...)`` and then
            ``sky.autostop(idle_minutes=<minutes>)``. If not set, the cluster
            will not be autostopped.
        down: Tear down the cluster after all jobs finish (successfully or
            abnormally). If --idle-minutes-to-autostop is also set, the
            cluster will be torn down after the specified idle time.
            Note that if errors occur during provisioning/data syncing/setting
            up, the cluster will not be torn down for debugging purposes.
        dryrun: if True, do not actually launch the cluster.
        stream_logs: if True, show the logs in the terminal.
        backend: backend to use.  If None, use the default backend
            (CloudVMRayBackend).
        optimize_target: target to optimize for. Choices: OptimizeTarget.COST,
            OptimizeTarget.TIME.
        detach_setup: If True, run setup in non-interactive mode as part of the
            job itself. You can safely ctrl-c to detach from logging, and it
            will not interrupt the setup process. To see the logs again after
            detaching, use `sky logs`. To cancel setup, cancel the job via
            `sky cancel`. Useful for long-running setup
            commands.
        detach_run: If True, as soon as a job is submitted, return from this
            function and do not stream execution logs.
        no_setup: if True, do not re-run setup commands.
        clone_disk_from: [Experimental] if set, clone the disk from the
            specified cluster. This is useful to migrate the cluster to a
            different availability zone or region.

    Example:
        .. code-block:: python

            import sky
            task = sky.Task(run='echo hello SkyPilot')
            task.set_resources(
                sky.Resources(cloud=sky.AWS(), accelerators='V100:4'))
            sky.launch(task, cluster_name='my-cluster')

    Raises:
        exceptions.ClusterOwnerIdentityMismatchError: if the cluster is
            owned by another user.
        exceptions.InvalidClusterNameError: if the cluster name is invalid.
        exceptions.ResourcesMismatchError: if the requested resources
            do not match the existing cluster.
        exceptions.NotSupportedError: if required features are not supported
            by the backend/cloud/cluster.
        exceptions.ResourcesUnavailableError: if the requested resources
            cannot be satisfied. The failover_history of the exception
            will be set as:
                1. Empty: iff the first-ever sky.optimize() fails to
                find a feasible resource; no pre-check or actual launch is
                attempted.
                2. Non-empty: iff at least 1 exception from either
                our pre-checks (e.g., cluster name invalid) or a region/zone
                throwing resource unavailability.
        exceptions.CommandError: any ssh command error.
        exceptions.NoCloudAccessError: if all clouds are disabled.
    Other exceptions may be raised depending on the backend.

    Returns:
      job_id: Optional[int]; the job ID of the submitted job. None if the
        backend is not CloudVmRayBackend, or no job is submitted to
        the cluster.
      handle: Optional[backends.ResourceHandle]; the handle to the cluster. None
        if dryrun.
    """
    entrypoint = task
    if not _disable_controller_check:
        controller_utils.check_cluster_name_not_controller(
            cluster_name, operation_str='pymcs.launch')

    return _execute(
        entrypoint=entrypoint,
        dryrun=dryrun,
        down=down,
        stream_logs=stream_logs,
        handle=None,
        backend=backend,
        retry_until_up=retry_until_up,
        optimize_target=optimize_target,
        cluster_name=cluster_name,
        detach_setup=detach_setup,
        detach_run=detach_run,
        idle_minutes_to_autostop=idle_minutes_to_autostop,
        no_setup=no_setup,
        clone_disk_from=clone_disk_from,
        _is_launched_by_jobs_controller=_is_launched_by_jobs_controller,
        _is_launched_by_sky_serve_controller=
        _is_launched_by_sky_serve_controller,
    )