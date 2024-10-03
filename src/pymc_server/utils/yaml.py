import yaml
import hiyapyco
from typing import Any, Dict, List, Optional, Tuple, Union
from sky import dag as dag_lib
from sky import task as task_lib
import os
import os.path
import pymc_server

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
    merged_yaml = hiyapyco.load(pymc_path, user_config_path, method=hiyapyco.METHOD_MERGE)
    return hiyapyco.dump(merged_yaml)

def getUserYaml(path):
    merged_yaml = hiyapyco.load(path, path, method=hiyapyco.METHOD_MERGE)
    return hiyapyco.dump(merged_yaml)

def get_pymc_module_from_yaml():
    try :   return str(userYaml[0]['pymc_module'])
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
                print("DAG afterCheck::::")
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
            is_yaml = False
        print("done")
    except yaml.YAMLError as e:
        is_yaml = False

    return result, is_yaml

def get_pymc_config_yaml(pymc_module, import_from="config", file_name="base.yaml", supported_modules=['pymc-marketing']):
    """
    Get's the base config for the pymc module

    Example:
        ```
        get_pymc_config_yaml('pymc-marketing')
        ```
    """
    #assert pymc_module == 'pymc-marketing', 'Not Implemented: the only supported module is pymc-marketing'
    base_path = os.path.dirname(os.path.abspath(pymc_server.__file__))
    file_exists = os.path.isfile(f'{base_path}/{import_from}/{pymc_module}/{file_name}')
    list = ""

    if file_exists == False:
        list = ', '.join(os.listdir(f'{base_path}/{import_from}'))

    # check that we have the config and support the module
    is_valid_module = file_exists and pymc_module in supported_modules
    assert is_valid_module , f'Not Implemented: the only supported module are {supported_modules} but we may have config for additional modules: {list}'

    return f'{base_path}/{import_from}/{pymc_module}/{file_name}'

def remove_key(d, key):
    r = dict(d)
    del r[key]
    return r

def set_config(config):
    try: return remove_key(config,'pymc_module')
    except: return config


def get_config_from_yaml(entrypoint: Tuple[str, ...],pymc_module:Optional[str]):

    user_file = entrypoint
    pymc_file = None
    userYaml, isValid = _check_and_return_yaml(getUserYaml(entrypoint))


    pymc_file = pymc_module if pymc_module is not None else get_pymc_module_from_yaml()

    #module_config_path = get_pymc_config_yaml(pymc_module)
    module_config_path = get_pymc_config_yaml(pymc_file) if pymc_file is not None else get_pymc_config_yaml('pymc-marketing')
    configs,is_yaml = _check_and_return_yaml(
        merge_yaml(
            user_config_path=user_file,
            pymc_path=module_config_path
        )
    )

    if is_yaml: configs = [set_config(config) for config in configs]
    return configs, is_yaml
