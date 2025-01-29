import uuid
# import colorama
from sky.utils import common_utils

def generate_service_name(prefix = "pymcs"):
    return f'{prefix}-service-{uuid.uuid4().hex[:4]}'

def generate_cluster_name(cluster:str=None,prefix = "pymcs"):
    cluster = cluster if cluster != None else common_utils.get_cleaned_username()
    return f'{prefix}-{uuid.uuid4().hex[:4]}-{cluster}'
