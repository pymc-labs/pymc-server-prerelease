#!/usr/bin/env python
import ray
# -*- coding: utf-8 -*-


ray.init(namespace="my_namespace")

#ray.init()

class ActorWrapper:
    def __init__(self, actor_name, namespace):
        self.actor = ray.get_actor(actor_name, namespace=namespace)

    def __getattr__(self, attr_name):
        # Get the attribute from the actor
        #attr = getattr(self.actor, attr_name)
        attr= ray.get(self.actor.get_attribute.remote(attr_name))

        # If the attribute is a method, return a function that calls the method remotely
        if callable(attr):
            def func(*args, **kwargs):
                method = getattr(self.actor, attr_name)
                breakpoint()
                return ray.get(method.remote(*args, **kwargs))
            return func

        # If the attribute is not a method, get its latest value from the actor
        else:
            return ray.get(self.actor.get_attribute.remote(attr_name))

    def __setattr__(self, attr_name, value):
        if attr_name == "actor":
            self.__dict__[attr_name] = value
        else:
            self.actor.set_attribute.remote(attr_name, value)

wrapper = ActorWrapper("stateful_actor", "my_namespace")
foo = wrapper.foo
print(foo)
wrapper._foobar()
ic = wrapper.invocation_count
breakpoint()
# Get the actor from the namespace "my_namespace"
"""
actor = ray.get_actor("stateful_actor")
remote_val = actor.foobar.remote()
print(ray.get(remote_val))

remote_val = actor.foobar.remote()
print(ray.get(remote_val))

#assert  remote_val == 'bar'

# Use the abstracted way to set and get values dynamically
actor.key1 = 'value1'  # Abstracted assignment
print(ray.get(actor.key1))  # Outputs: value1

actor.key2 = 'value2'
print(ray.get(actor.key2))  # Outputs: value2
"""

ray.shutdown()
