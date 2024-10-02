import uuid
from sky.utils import common_utils
def generate_service_name(prefix = "pymc"):
    return f'{prefix}-service-{uuid.uuid4().hex[:4]}'

def generate_cluster_name(prefix = "pymc"):
    return f'{prefix}-{uuid.uuid4().hex[:4]}-{common_utils.get_cleaned_username()}'