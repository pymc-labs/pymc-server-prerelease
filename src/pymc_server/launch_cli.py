import os
import yaml
import click
import sky
import pymc_server
from sky import Task
from sky import dag as dag_lib
from sky import task as task_lib
from sky import serve as serve_lib
from sky.usage import usage_lib
from sky.utils import dag_utils,ux_utils
from typing import Any, Dict, List, Optional, Tuple, Union
from pymc_server.utils.yaml import merge_yaml, getUserYaml
from sky.utils import common_utils

def get_config_from_yaml(entrypoint: Tuple[str, ...],pymc_yaml:Optional[str]):
    module_config_path = get_pymc_config_yaml('pymc-marketing')
    user_file = entrypoint
    pymc_file = None
    userYaml, isValid = _check_and_return_yaml(getUserYaml(entrypoint))

    def get_pymc_yaml_from_yaml():
        try :   return str(userYaml[0]['pymc_yaml'])
        except: return module_config_path
    pymc_file = pymc_yaml if pymc_yaml is not None else get_pymc_yaml_from_yaml()

    configs,is_yaml = _check_and_return_yaml(
        merge_yaml(
            user_config_path=user_file,
            pymc_path=pymc_file
        )
    )
    def remove_key(d, key):
        r = dict(d)
        del r[key]
        return r
    def set_config(config):
        try: return remove_key(config,'pymc_yaml')
        except: return config
    if is_yaml: configs = [set_config(config) for config in configs]
    return configs, is_yaml

def load_chain_dag_from_yaml(
    configs: List[Dict[str, Any]],
    env_overrides: Optional[List[Tuple[str, str]]] = None,
) -> dag_lib.Dag:
    """Loads a chain DAG from a YAML file.

    Has special handling for an initial section in YAML that contains only the
    'name' field, which is the DAG name.

    'env_overrides' is a list of (key, value) pairs that will be used to update
    the task's 'envs' section. If it is a chain dag, the envs will be updated
    for all tasks in the chain.

    Returns:
      A chain Dag with 1 or more tasks (an empty entrypoint would create a
      trivial task).
    """
    dag_name = None
    if set(configs[0].keys()) == {'name'}:
        dag_name = configs[0]['name']
        configs = configs[1:]
    elif len(configs) == 1:
        dag_name = configs[0].get('name')

    if len(configs) == 0:
        # YAML has only `name: xxx`. Still instantiate a task.
        configs = [{'name': dag_name}]
    current_task = None

    with dag_lib.Dag() as dag:
        for task_config in configs:
            print("DAG afterCheck::::")
            if task_config is None:
                continue
            print("DAG afterCheck::::")
            task = task_lib.Task.from_yaml_config(task_config, env_overrides)
            print("DAG afterCheck::::"+str(task))
            if current_task is not None:
                print("DAG afterCheck::::")
                current_task >> task  # pylint: disable=pointless-statement
            current_task = task
    dag.name = dag_name
    print("DAG afterCheck::::")

    return dag

def _check_and_return_yaml(yaml_file) :#-> Tuple[bool, Optional[Dict[str, Any]]]:
    """Checks if entrypoint is a readable YAML file.

    Args:
        entrypoint: Path to a YAML file.
    """
    
   # try:
        
    #with open(entrypoint, 'r', encoding='utf-8') as f: # change that - open 
    try:
        is_yaml = True
        config = list(yaml.safe_load_all(yaml_file))
        if config:
            # FIXME(zongheng): in a chain DAG YAML it only returns the
            # first section. OK for downstream but is weird.
            result = config
        else:
            result = {}
        if isinstance(result, str):
            # 'sky exec cluster ./my_script.sh'
            is_yaml = False
        print("done")
    except yaml.YAMLError as e:
        is_yaml = False

    return result, is_yaml

def get_pymc_config_yaml(pymc_module, import_from="config", file_name="base.yaml"):
    """
    Get's the base config for the pymc module

    Example:
        ```
        get_pymc_config_yaml('pymc-marketing')
        ```
    """
    assert pymc_module == 'pymc-marketing', 'Not Implemented: the only supported module is pymc-marketing'
    base_path = os.path.dirname(os.path.abspath(pymc_server.__file__))
    return f'{base_path}/{import_from}/{pymc_module}/{file_name}'



def launch(
    entrypoint: Tuple[str, ...],
    pymc_yaml:Optional[str],
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

    configs, is_yaml = get_config_from_yaml(entrypoint=entrypoint,pymc_yaml=pymc_yaml)

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

    click.secho('Service Spec:', fg='cyan')
    click.echo(task.service)

    click.secho('New replica will use the following resources (estimated):',
                fg='cyan')
    with sky.Dag() as dag:
        dag.add(task)
    sky.optimize(dag)

    service_name ="Name"
    if not yes:
        click.confirm(f'Updating service {service_name!r}. Proceed?',
            default=True,
            abort=True,
            show_default=True)

    serve_lib.update(task, service_name, mode=serve_lib.UpdateMode(mode))
    
    return task


