import ray
# Reconnect to Ray with the same namespace
ray.init()
# Get the actor from the namespace "my_namespace"
try:
    actor = ray.get_actor("stateful_actor", namespace="pymc-stateful-actor-dev")
    ray.kill(actor)
except:
    pass
try:
    actor = ray.get_actor("stateful_actor", namespace="my_namespace")
    ray.kill(actor)
except:
    pass
