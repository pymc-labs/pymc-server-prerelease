import os
import yaml
import click
import sky
import pymc_server
import uuid
import colorama
from typing import  Dict, List, Optional, Tuple, Union

from sky import Task
from sky import backends
from sky import serve as serve_lib
from sky import jobs as managed_jobs
from sky.cli import _parse_override_params, _merge_env_vars
from sky.utils import dag_utils,ux_utils
from sky.utils import common_utils
from sky.utils import controller_utils
from sky.usage import usage_lib
#from sky import core
from pymc_server.utils.names import generate_cluster_name
from pymc_server.utils.launch import launch_with_confirm as _launch_with_confirm
from pymc_server.utils.yaml import (
    get_config_from_yaml, load_chain_dag_from_yaml,
    _make_task_or_dag_from_entrypoint_with_overrides,
    get_auto_stop

)
from sky.cli import (
    status as sky_status,
    launch as sky_launch,
    check as sky_check
)

def launch(
    entrypoint: Tuple[str, ...],
    module_name:Optional[str],
    base_config_folder:Optional[str],
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
    retry_until_up: bool,
    yes: bool,
    no_setup: bool,
    clone_disk_from: Optional[str],
    # job launch specific
    job_recovery: Optional[str] = None,
    down: bool = False
):



    # NOTE(dev): Keep the docstring consistent between the Python API and CLI.
    env = _merge_env_vars(env_file, env)
    controller_utils.check_cluster_name_not_controller(
        cluster, operation_str='Launching tasks on it')
    if backend_name is None:
        backend_name = backends.CloudVmRayBackend.NAME

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
        num_nodes=num_nodes,
        use_spot=use_spot,
        image_id=image_id,
        env=env,
        disk_size=disk_size,
        disk_tier=disk_tier,
        ports=ports,
    )
    """ set auto stop/down from config """
    auto_idle_minutes,auto_down = get_auto_stop(entrypoint,module_name,base_config_folder)
    idle_minutes_to_autostop = idle_minutes_to_autostop if idle_minutes_to_autostop != None else auto_idle_minutes
    down = down if down != None else auto_down
    down = False if down == None else down
    if isinstance(task_or_dag, sky.Dag):
        raise click.UsageError(
            _DAG_NOT_SUPPORTED_MESSAGE.format(command='pymcs launch'))
    task = task_or_dag

    backend: backends.Backend
    if backend_name == backends.LocalDockerBackend.NAME:
        backend = backends.LocalDockerBackend()
    elif backend_name == backends.CloudVmRayBackend.NAME:
        backend = backends.CloudVmRayBackend()
    else:
        with ux_utils.print_exception_no_traceback():
            raise ValueError(f'{backend_name} backend is not supported.')

    if task.service is not None:
        logger.info(
            f'{colorama.Fore.YELLOW}Service section will be ignored when using '
            f'`pymcs launch`. {colorama.Style.RESET_ALL}\n{colorama.Fore.YELLOW}'
            'To spin up a service, use SkyServe CLI: '
            f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}pymcs serve up'
            f'{colorama.Style.RESET_ALL}')

    cluster_name = generate_cluster_name(cluster)
    print(f'{colorama.Fore.YELLOW}new clustername: {cluster_name}')

    _launch_with_confirm(
        task,
        backend,
        cluster=cluster_name,
        dryrun=dryrun,
        detach_setup=detach_setup,
        detach_run=detach_run,
        no_confirm=yes,
        idle_minutes_to_autostop=idle_minutes_to_autostop,
        down=down,
        retry_until_up=retry_until_up,
        no_setup=no_setup,
        clone_disk_from=clone_disk_from
    )

    click.secho(f'{colorama.Fore.YELLOW}new cluster: '
                f'{colorama.Style.RESET_ALL}{cluster_name}')
    #cluster_records = core.status(cluster_names='cluster_name',refresh=False)
    #handle = cluster_records[0]['handle']
    #head_ip = handle.external_ips()[0]

    return cluster_name




