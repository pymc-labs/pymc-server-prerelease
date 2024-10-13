#!/usr/bin/env python
import ray
# -*- coding: utf-8 -*-


ray.init(namespace="my_namespace")

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

ray.shutdown()
