import click
import sky
import pymc_server
import colorama
from typing import  Dict, List, Optional, Tuple, Union
from pymc_server.utils.yaml import (
    get_config_from_yaml, load_chain_dag_from_yaml,
    _make_task_or_dag_from_entrypoint_with_overrides,
    get_auto_stop

)
from sky.utils import controller_utils
from sky.backends import backend_utils
from sky.cli import _parse_override_params, _merge_env_vars, _pop_and_ignore_fields_in_override_params
from sky import global_user_state

def exec(
    cluster: Optional[str],
    cluster_option: Optional[str],
    entrypoint: Tuple[str, ...],
    module_name:Optional[str],
    base_config_folder:Optional[str],
    detach_run: bool,
    name: Optional[str],
    cloud: Optional[str],
    region: Optional[str],
    zone: Optional[str],
    workdir: Optional[str],
    gpus: Optional[str],
    ports: Tuple[str],
    instance_type: Optional[str],
    num_nodes: Optional[int],
    use_spot: Optional[bool],
    image_id: Optional[str],
    env_file: Optional[Dict[str, str]],
    env: List[Tuple[str, str]],
    cpus: Optional[str],
    memory: Optional[str],
    disk_size: Optional[int],
    disk_tier: Optional[str],
):
    # NOTE(dev): Keep the docstring consistent between the Python API and CLI.
    """Execute a task or command on an existing cluster.

    If ENTRYPOINT points to a valid YAML file, it is read in as the task
    specification. Otherwise, it is interpreted as a bash command.

    Actions performed by ``sky exec``:

    1. Workdir syncing, if:

       - ENTRYPOINT is a YAML with the ``workdir`` field specified; or

       - Flag ``--workdir=<local_dir>`` is set.

    2. Executing the specified task's ``run`` commands / the bash command.

    ``sky exec`` is thus typically faster than ``sky launch``, provided a
    cluster already exists.

    All setup steps (provisioning, setup commands, file mounts syncing) are
    skipped.  If any of those specifications changed, this command will not
    reflect those changes.  To ensure a cluster's setup is up to date, use ``sky
    launch`` instead.

    Execution and scheduling behavior:

    - The task/command will undergo job queue scheduling, respecting any
      specified resource requirement. It can be executed on any node of the
      cluster with enough resources.

    - The task/command is run under the workdir (if specified).

    - The task/command is run non-interactively (without a pseudo-terminal or
      pty), so interactive commands such as ``htop`` do not work. Use ``ssh
      my_cluster`` instead.

    Typical workflow:

    .. code-block:: bash

      # First command: set up the cluster once.
      sky launch -c mycluster app.yaml
      \b
      # For iterative development, simply execute the task on the launched
      # cluster.
      sky exec mycluster app.yaml
      \b
      # Do "sky launch" again if anything other than Task.run is modified:
      sky launch -c mycluster app.yaml
      \b
      # Pass in commands for execution.
      sky exec mycluster python train_cpu.py
      sky exec mycluster --gpus=V100:1 python train_gpu.py
      \b
      # Pass environment variables to the task.
      sky exec mycluster --env WANDB_API_KEY python train_gpu.py

    """
    if cluster_option is None and cluster is None:
        raise click.UsageError('Missing argument \'[CLUSTER]\' and '
                               '\'[ENTRYPOINT]...\'')
    if cluster_option is not None:
        if cluster is not None:
            entrypoint = (cluster,) + entrypoint
        cluster = cluster_option
    if not entrypoint:
        raise click.UsageError('Missing argument \'[ENTRYPOINT]...\'')
    assert cluster is not None, (cluster, cluster_option, entrypoint)

    env = _merge_env_vars(env_file, env)
    controller_utils.check_cluster_name_not_controller(
        cluster, operation_str='Executing task on it')
    handle = global_user_state.get_handle_from_cluster_name(cluster)
    if handle is None:
        raise click.BadParameter(f'Cluster {cluster!r} not found. '
                                 'Use `sky launch` to provision first.')
    backend = backend_utils.get_backend_from_handle(handle)

    task_or_dag = _make_task_or_dag_from_entrypoint_with_overrides(
        entrypoint=entrypoint,
        module_name=module_name,
        base_config_folder=base_config_folder,
        name=name,
        workdir=workdir,
        cloud=cloud,
        region=region,
        zone=zone,
        gpus=gpus,
        cpus=cpus,
        memory=memory,
        instance_type=instance_type,
        use_spot=use_spot,
        image_id=image_id,
        num_nodes=num_nodes,
        env=env,
        disk_size=disk_size,
        disk_tier=disk_tier,
        ports=ports,
        field_to_ignore=['cpus', 'memory', 'disk_size', 'disk_tier', 'ports'],
    )

    if isinstance(task_or_dag, sky.Dag):
        raise click.UsageError('YAML specifies a DAG, while `sky exec` '
                               'supports a single task only.')
    task = task_or_dag

    click.secho(f'Executing task on cluster {cluster}...', fg='yellow')
    sky.exec(task, backend=backend, cluster_name=cluster, detach_run=detach_run)
