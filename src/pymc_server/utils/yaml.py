import yaml
import click
import colorama
import hiyapyco
from typing import Any, Dict, List, Optional, Tuple, Union
from sky import dag as dag_lib
from sky import task as task_lib
import os
import os.path
import pymc_server
import sky

from sky import clouds as sky_clouds
from sky.cli import _parse_override_params
from sky.usage import usage_lib

from .names import generate_cluster_name


def merge_yaml(user_config_path, pymc_path):
    """
    Merges a pymc module's base config with the user config

    Args:
        user_config_path: Path to the user portion of the config yaml file
        pymc_path: Path to the base config for the pymc module
    Example:
        ```
        merge_yaml(
            user_config_path='/my_config.yaml'
            pymc_path='pymc_server/config/pymc-marketing/base.yaml'
        )
        ```
    """

    merged_yaml = hiyapyco.load(pymc_path, user_config_path)

    return hiyapyco.dump(merged_yaml)

def getUserYaml(path):
    merged_yaml = hiyapyco.load(path, path, method=hiyapyco.METHOD_MERGE)
    return hiyapyco.dump(merged_yaml)

def get_module_name_from_yaml():
    try :   return str(userYaml[0]['module_name'])
    except: return None

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
            if task_config is None:
                continue
            task = task_lib.Task.from_yaml_config(task_config, env_overrides)
            if current_task is not None:
                current_task >> task  # pylint: disable=pointless-statement
            current_task = task
    dag.name = dag_name
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
            is_yaml = FalseHe
    except yaml.YAMLError as e:
        is_yaml = False

    return result, is_yaml

def get_pymc_config_yaml(module_name, import_from="config", file_name="base.yaml", supported_modules=['pymc-marketing']):
    """
    Get's the base config for the pymc module

    Example:
        ```
        get_pymc_config_yaml('pymc-marketing')
        ```
    """
    #assert module_name == 'pymc-marketing', 'Not Implemented: the only supported module is pymc-marketing'
    base_path = os.path.dirname(os.path.abspath(pymc_server.__file__))
    file_exists = os.path.isfile(f'{base_path}/{import_from}/{module_name}/{file_name}')
    list = ""

    if file_exists == False:
        list = ', '.join(os.listdir(f'{base_path}/{import_from}'))

    # check that we have the config and support the module
    is_valid_module = file_exists and module_name in supported_modules
    assert is_valid_module , f'{colorama.Fore.RED}Not Implemented: {colorama.Style.RESET_ALL}the only supported module are {colorama.Fore.YELLOW}{supported_modules}{colorama.Style.RESET_ALL} but we may have config for additional modules: {colorama.Fore.YELLOW}{list}{colorama.Style.RESET_ALL}'

    return f'{base_path}/{import_from}/{module_name}/{file_name}'

def remove_key(d, key):
    r = dict(d)
    del r[key]
    return r

def set_config(config):
    try: return remove_key(config,'module_name')
    except: return config


def exists(path):
    exists_ =  os.path.exists(path)
    if exists_ is False:
       raise Exception(f'{colorama.Fore.RED}File Not Found: '
                       f'{colorama.Fore.YELLOW}{path}{colorama.Style.RESET_ALL}')

def get_config_from_yaml(entrypoint: Tuple[str, ...],module_name:Optional[str],base_config_path:Optional[str]):

    user_file = entrypoint
    base_file = None
    module_config_path =None
    if entrypoint != ():
        exists(entrypoint[0])
    userYaml, isValid = _check_and_return_yaml(getUserYaml(entrypoint))

    current_module = module_name if module_name is not None else get_module_name_from_yaml()
    if base_config_path is not None:
        if(current_module is None):
            raise Exception(f'{colorama.Fore.RED}Please define a module for: '
                            f'{colorama.Fore.YELLOW}{base_config_path}{colorama.Style.RESET_ALL}')
        base_file =  f'{base_config_path}/{module_name}/base.yaml'
        exists(base_file)
        #customBaseYaml, isValid_ = _check_and_return_yaml(getUserYaml(base_file))
        module_config_path = base_file


    if module_config_path is None:
        base_file = get_pymc_config_yaml(current_module if current_module is not None else "pymc-marketing")
        exists(base_file)
        module_config_path = base_file

    # print(f'module_config_path:: {module_config_path}')
    configs,is_yaml = _check_and_return_yaml(
        merge_yaml(
            user_config_path=user_file,
            pymc_path=module_config_path
        )
    )

    if is_yaml: configs = [set_config(config) for config in configs]
    return configs, is_yaml, module_config_path



def _make_task_or_dag_from_entrypoint_with_overrides(
    entrypoint: Tuple[str, ...],
    module_name:Optional[str],
    base_config_folder:Optional[str],
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

    configs, is_yaml,module_config_path = get_config_from_yaml(entrypoint,module_name,base_config_folder)

    clean_up_config(configs)

    print(f'{colorama.Fore.YELLOW} ERRRRROOOOORRR HERE')

    click.secho(f'{colorama.Fore.GREEN}used base_config_folder:'
                f'{colorama.Style.RESET_ALL}{base_config_folder}')
    click.secho(f'{colorama.Fore.GREEN}used entrypoint:'
                f'{colorama.Style.RESET_ALL}{entrypoint}')

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


def _get_auto_stop_from_yaml(configs):
    try:
            autostop = configs["resources"]['autostop'] if 'autostop' in configs["resources"] else None
            idle_minutes = configs["resources"]['autostop']['idle_minutes'] if 'idle_minutes' in autostop else None
            down = configs["resources"]['autostop']['down'] if 'down' in autostop else None
            return idle_minutes, down
    except: return None, None


def get_auto_stop_from_entrypoint(entrypoint):
    if entrypoint != ():
       exists(entrypoint)
    else: return None, None
    userYaml =  hiyapyco.load(entrypoint, entrypoint, method=hiyapyco.METHOD_MERGE)
    return _get_auto_stop_from_yaml(userYaml)

def get_auto_stop(entrypoint: Tuple[str, ...],module_name:Optional[str],base_config_path:Optional[str]):
    configs, is_yaml,module_config_path = get_config_from_yaml(entrypoint,module_name,base_config_path)
    return _get_auto_stop_from_yaml(configs[0])


def clean_up_config(config):
    try:
        del config[0]["resources"]['autostop']
    except : ()

