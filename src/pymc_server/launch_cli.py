import os
import yaml
import click
import sky
import pymc_server
import uuid
from typing import  Dict, List, Optional, Tuple, Union

from sky import Task
from sky import backends
from sky import serve as serve_lib
from sky import jobs as managed_jobs
from sky.cli import _parse_override_params,_merge_env_vars
from sky.utils import dag_utils,ux_utils
from sky.utils import common_utils
from sky.utils import controller_utils
from sky.usage import usage_lib
from sky.cli import _launch_with_confirm

from pymc_server.utils.names import generate_cluster_name
from pymc_server.utils.yaml import get_config_from_yaml,load_chain_dag_from_yaml


def launch(
    entrypoint: Tuple[str, ...],
    pymc_module:Optional[str],
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
):

    configs, is_yaml = get_config_from_yaml(entrypoint,pymc_module)

    entrypoint_name = 'Task',
    if is_yaml:
        # Treat entrypoint as a yaml.
        click.secho(f'{entrypoint_name} from YAML spec: ',
                    fg='yellow',
                    nl=False)
        click.secho(configs, bold=True)
    
    env: List[Tuple[str, str]] = []

    if is_yaml:
        assert configs is not None

        #remove_key(configs[0],'pymc_yaml')
        usage_lib.messages.usage.update_user_task_yaml(configs[0])
        dag = load_chain_dag_from_yaml(configs = configs)
        task = dag.tasks[0]

        if len(dag.tasks) > 1:
            # When the dag has more than 1 task. It is unclear how to
            # override the params for the dag. So we just ignore the
            # override params.
            if override_params:
                click.secho(
                    f'WARNING: override params {override_params} are ignored, '
                    'since the yaml file contains multiple tasks.',
                    fg='yellow')
            return dag

        assert len(dag.tasks) == 1, (
            f'If you see this, please file an issue; tasks: {dag.tasks}')
       
       
    else:

        task = sky.Task(name='sky-cmd', run=configs)
        task.set_resources({sky.Resources()})
        # env update has been done for DAG in load_chain_dag_from_yaml for YAML.
        task.update_envs(env)
    # Override.
    #workdir = None
    #job_recovery = None
    #num_nodes = None
    #name = None
    if workdir is not None:
        task.workdir = workdir

    # job launch specific.
    #if job_recovery is not None:
    #    override_params['job_recovery'] = job_recovery



    if num_nodes is not None:
        task.num_nodes = num_nodes
    if name is not None:
        task.name = name


    if isinstance(task, sky.Dag):
        raise click.UsageError(
            _DAG_NOT_SUPPORTED_MESSAGE.format(command=not_supported_cmd))
    #if task.service is None:
    #    with ux_utils.print_exception_no_traceback():
    #        raise ValueError('Service section not found in the YAML file. '
    #                         'To fix, add a valid `service` field.')
    #print(task)
    service_port: Optional[int] = None
    for requested_resources in list(task.resources):
        """
        if requested_resources.ports is None or len(
                requested_resources.ports) != 1:
            with ux_utils.print_exception_no_traceback():
                raise ValueError(
                    'Must only specify one port in resources. Each replica '
                    'will use the port specified as application ingress port.')
        service_port_str = requested_resources.ports[0]
        if not service_port_str.isdigit():
            # For the case when the user specified a port range like 10000-10010
            with ux_utils.print_exception_no_traceback():
                raise ValueError(f'Port {service_port_str!r} is not a valid '
                                 'port number. Please specify a single port '
                                 f'instead. Got: {service_port_str!r}')
        # We request all the replicas using the same port for now, but it
        # should be fine to allow different replicas to use different ports
        # in the future.
        resource_port = int(service_port_str)
        if service_port is None:
            service_port = resource_port
        if service_port != resource_port:
            with ux_utils.print_exception_no_traceback():
                raise ValueError(f'Got multiple ports: {service_port} and '
                                 f'{resource_port} in different resources. '
                                 'Please specify single port instead.')

        """
    click.secho('Service Spec:', fg='cyan')
    click.echo(task.service)

    click.secho('New replica will use the following resources (estimated):',
                fg='cyan')

    with sky.Dag() as dag:
        dag.add(task)
    sky.optimize(dag)


    click.secho(f"service_name, {"service_name"}:", fg='cyan')

    if service_name is None:
            service_name = serve_lib.generate_service_name()


    if not yes:
        click.confirm(f'Updating service {service_name!r}. Proceed?',
            default=True,
            abort=True,
            show_default=True)
    print("manage jobs now!")
    managed_jobs.launch(dag,
                            name,
                            detach_run=detach_run,
                            retry_until_up=retry_until_up)

    #serve_lib.update(task, service_name, mode=serve_lib.UpdateMode(mode))
    
    return task


def cli_launch_(
    entrypoint: Tuple[str, ...],
    pymc_module:Optional[str],
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
):
    """Launch a managed job from a YAML or a command.

    If ENTRYPOINT points to a valid YAML file, it is read in as the task
    specification. Otherwise, it is interpreted as a bash command.

    Examples:

    .. code-block:: bash

      # You can use normal task YAMLs.
      sky jobs launch task.yaml

      sky jobs launch 'echo hello!'
    """
    if cluster is not None:
        if name is not None and name != cluster:
            raise click.UsageError('Cannot specify both --name and --cluster. '
                                   'Use one of the flags as they are alias.')
        name = cluster
    env = _merge_env_vars(env_file, env)
    task_or_dag = _make_task_or_dag_from_entrypoint_with_overrides(
        entrypoint,
        pymc_module=pymc_module,
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
        job_recovery=job_recovery,
    )

    # Deprecation. We set the default behavior to be retry until up, and the
    # flag `--retry-until-up` is deprecated. We can remove the flag in 0.8.0.
    if retry_until_up is not None:
        flag_str = '--retry-until-up'
        if not retry_until_up:
            flag_str = '--no-retry-until-up'
        click.secho(
            f'Flag {flag_str} is deprecated and will be removed in a '
            'future release (managed jobs will always be retried). '
            'Please file an issue if this does not work for you.',
            fg='yellow')
    else:
        retry_until_up = True



    if not isinstance(task_or_dag, sky.Dag):
        assert isinstance(task_or_dag, sky.Task), task_or_dag
        with sky.Dag() as dag:
            dag.add(task_or_dag)
            dag.name = task_or_dag.name
    else:
        dag = task_or_dag
    if name is not None:
        dag.name = name
    if dag.name is None :
        dag.name = generate_cluster_name()

    dag.name = generate_cluster_name()
    click.secho(f'Managed job {dag.name!r} will be launched on (estimated):',
                    fg='yellow')
    dag_utils.maybe_infer_and_fill_dag_and_task_names(dag)
    dag_utils.fill_default_config_in_dag_for_job_launch(dag)


    click.secho(f'Managed job {dag.name!r} will be launched on (estimated):',
                fg='yellow')
    dag = sky.optimize(dag)

    if not yes:
        prompt = f'Launching a managed job {dag.name!r}. Proceed?'
        if prompt is not None:
            click.confirm(prompt, default=True, abort=True, show_default=True)

    common_utils.check_cluster_name_is_valid(name)

    managed_jobs.launch(dag,
                        name,
                        detach_run=detach_run,
                        retry_until_up=retry_until_up)

def launch_2(
    entrypoint: Tuple[str, ...],
    pymc_module:Optional[str],
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
        pymc_module=pymc_module,
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
    if isinstance(task_or_dag, sky.Dag):
        raise click.UsageError(
            _DAG_NOT_SUPPORTED_MESSAGE.format(command='sky launch'))
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
            f'`sky launch`. {colorama.Style.RESET_ALL}\n{colorama.Fore.YELLOW}'
            'To spin up a service, use SkyServe CLI: '
            f'{colorama.Style.RESET_ALL}{colorama.Style.BRIGHT}sky serve up'
            f'{colorama.Style.RESET_ALL}')

    _launch_with_confirm(task,
                         backend,
                         cluster=generate_cluster_name(),
                         dryrun=dryrun,
                         detach_setup=detach_setup,
                         detach_run=detach_run,
                         no_confirm=yes,
                         idle_minutes_to_autostop=idle_minutes_to_autostop,
                         down=down,
                         retry_until_up=retry_until_up,
                         no_setup=no_setup,
                         clone_disk_from=clone_disk_from)



def _make_task_or_dag_from_entrypoint_with_overrides(
    entrypoint: Tuple[str, ...],
    pymc_module:Optional[str],
    *,
    entrypoint_name: str = 'Task',
    name: Optional[str] = None,
    workdir: Optional[str] = None,
    cloud: Optional[str] = None,
    region: Optional[str] = None,
    zone: Optional[str] = None,
    gpus: Optional[str] = None,
    cpus: Optional[str] = None,
    memory: Optional[str] = None,
    instance_type: Optional[str] = None,
    num_nodes: Optional[int] = None,
    use_spot: Optional[bool] = None,
    image_id: Optional[str] = None,
    disk_size: Optional[int] = None,
    disk_tier: Optional[str] = None,
    ports: Optional[Tuple[str]] = None,
    env: Optional[List[Tuple[str, str]]] = None,
    field_to_ignore: Optional[List[str]] = None,
    # job launch specific
    job_recovery: Optional[str] = None,
) -> Union[sky.Task, sky.Dag]:
    """Creates a task or a dag from an entrypoint with overrides.

    Returns:
        A dag iff the entrypoint is YAML and contains more than 1 task.
        Otherwise, a task.
    """
    #entrypoint = ' '.join(entrypoint)
    configs, is_yaml = get_config_from_yaml(entrypoint,pymc_module)
    #is_yaml, _ = _check_yaml(entrypoint)
    entrypoint: Optional[str]
    if is_yaml:
        # Treat entrypoint as a yaml.
        click.secho(f'{entrypoint_name} from YAML spec: ',
                    fg='yellow',
                    nl=False)
        click.secho(entrypoint, bold=True)
    else:
        if not entrypoint:
            entrypoint = None
        else:
            # Treat entrypoint as a bash command.
            click.secho(f'{entrypoint_name} from command: ',
                        fg='yellow',
                        nl=False)
            click.secho(entrypoint, bold=True)

    override_params = _parse_override_params(cloud=cloud,
                                             region=region,
                                             zone=zone,
                                             gpus=gpus,
                                             cpus=cpus,
                                             memory=memory,
                                             instance_type=instance_type,
                                             use_spot=use_spot,
                                             image_id=image_id,
                                             disk_size=disk_size,
                                             disk_tier=disk_tier,
                                             ports=ports)
    if field_to_ignore is not None:
        _pop_and_ignore_fields_in_override_params(override_params,
                                                  field_to_ignore)

    if is_yaml:
        assert entrypoint is not None
        usage_lib.messages.usage.update_user_task_yaml(configs[0])
        dag = load_chain_dag_from_yaml(configs = configs)
        #task = dag.tasks[0]
        #usage_lib.messages.usage.update_user_task_yaml(entrypoint)

        if len(dag.tasks) > 1:
            # When the dag has more than 1 task. It is unclear how to
            # override the params for the dag. So we just ignore the
            # override params.
            if override_params:
                click.secho(
                    f'WARNING: override params {override_params} are ignored, '
                    'since the yaml file contains multiple tasks.',
                    fg='yellow')
            return dag
        assert len(dag.tasks) == 1, (
            f'If you see this, please file an issue; tasks: {dag.tasks}')
        task = dag.tasks[0]
    else:
        task = sky.Task(name='pymc-cmd', run=entrypoint)
        task.set_resources({sky.Resources()})
        # env update has been done for DAG in load_chain_dag_from_yaml for YAML.
        task.update_envs(env)

    # Override.
    if workdir is not None:
        task.workdir = workdir

    # job launch specific.
    if job_recovery is not None:
        override_params['job_recovery'] = job_recovery

    task.set_resources_override(override_params)

    if num_nodes is not None:
        task.num_nodes = num_nodes
    if name is not None:
        task.name = name

    return task

