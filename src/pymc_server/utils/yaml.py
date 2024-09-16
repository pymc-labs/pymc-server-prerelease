import hiyapyco

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