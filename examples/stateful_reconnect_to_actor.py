# reconnect_actor.py
import ray

# Reconnect to Ray with the same namespace
ray.init(namespace="pymc-stateful-actor-dev")

# Get the actor from the namespace "my_namespace"
actor = ray.get_actor("stateful_actor")
# Get the previous state
print(ray.get(actor.get_value.remote("key1")))  # Outputs: initial_value
print(ray.get(actor.get_value.remote("key2")))  # Outputs: initial_value

print("-----")
# Set new state
actor.set_value.remote("key2", "new_value")

# Get the new state
print(ray.get(actor.get_value.remote("key2")))  # Outputs: new_value
print("-----")


### foobar
r = actor.foobar.remote()
print(ray.get(r))

r = actor.foobar.remote()
print(ray.get(r))


invocation_count = ray.get(actor.get_value.remote('invocation_count'))
print(invocation_count)  # Outputs: new_value

