#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ray

@ray.remote
class Actor:
    def __init__(self, foo, bar):
        self.foo = foo
        self.bar = bar
        self.invocation_count = 0
        self.baz = 1

    def reset(self):
        self.invocation_count = 0

    def _foobar(self):
        print(super())
        self.invocation_count += 1
        self.baz=42
        #self.set_attribute('invocation_count', 100)
        return 'foobar'

    def get_attribute(self, attr_name):
        print("getattr", attr_name)
        return getattr(self, attr_name)

    def set_attribute(self, attr_name, value):
        setattr(self, attr_name, value)

class ActorWrapper:
    def __init__(self, foo, bar):
        self.actor = Actor.options(name="stateful_actor", lifetime="detached", namespace="my_namespace").remote(foo, bar)


    def __getattr__(self, attr_name):
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



# Initialize Ray
ray.init(
runtime_env={
        "env_vars": {"RAY_DEBUG": "1"},
    }
)

wrapper = ActorWrapper('foo', 'bar')
foo = wrapper.foo
wrapper.foo = 'new_foo_value'

ray.shutdown()
print("make sure to kill the actor with the `examples/stateful_kill_actor.py` script")

