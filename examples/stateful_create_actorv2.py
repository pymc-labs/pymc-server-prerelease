#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ray

"""
@ray.remote
class StatefulActor:
    def __init__(self):
        super().__setattr__("state", {})  # Initialize state

    def __setattr__(self, key, value):
        print('key: '+ key + ', value:', value)
        if key.startswith('_') or key == 'state':
            super().__setattr__(key, value)
        else:
            # Set the value using remote call
            ray.get(self.set_value.remote(key, value))

    def __getattr__(self, key):
        print(key)
        # Dynamically fetch the value from the actor's state
        if key.startswith('_') or key == 'state':
            raise AttributeError(f"Attribute '{key}' not found")  # Avoid infinite loop

        return ray.get(self.get_value.remote(key))

    def foobar(self):
        self.invocation_count +=1  
        print("_______FOOOBAR________")
        print(self.invocation_count)
        #self.set_value('invocation_count', self.invocation_count + 1)
        return "foobar"

    def set_value(self, key, value):
        self.state[key] = value

    def get_value(self, key):
        return self.state.get(key, None)

"""
import ray

@ray.remote
class StatefulActor:
    def __init__(self):
        # Initialize internal state attributes
        self._state = {}  # Use a private variable for dynamic attributes
        self.invocation_count = 0  # Internal state attribute

    """
    def __setattr__(self, key, value):
        print('set', key, value)
        # Allow normal assignment for internal attributes
        if '_' in key:
            # Directly set internal state attributes
            super().__setattr__(key, value)
        else:
            # Store dynamic attributes in the _state dictionary
            self._state[key] = value

    def __getattr__(self, key):
        print('get', key)
        # Allow normal retrieval for internal attributes
        if '_' in key:
            return super().__getattribute__(key)
        # Return from dynamic state
        return self._state.get(key, None)
    """

    def get_attribute(self, attr_name):
        return getattr(self, attr_name)

    def foobar(self):
        # Increment invocation_count normally
        print('will halt')
        breakpoint()
        self.invocation_count += 1
        return self.invocation_count

    def get_invocation_count(self):
        return self.invocation_count

    def get_dynamic_value(self, key):
        return self._state.get(key, None)

@ray.remote
class Actor:
    def __init__(self, foo, bar):
        self.foo = foo
        self.bar = bar

    def get_attribute(self, attr_name):
        return getattr(self, attr_name)

    def set_attribute(self, attr_name, value):
        setattr(self, attr_name, value)

class ActorWrapper:
    def __init__(self, foo, bar):
        self.actor = Actor.options(name="stateful_actor", lifetime="detached", namespace="my_namespace").remote(foo, bar)

    def __getattr__(self, attr_name):
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

"""
breakpoint()
# Create a detached actor under the namespace "my_namespace"
actor = StatefulActor.options(
    name="stateful_actor", 
    lifetime="detached", 
    namespace="my_namespace"
).remote()

#  breakpoint()
# Use the abstracted way to set and get values dynamically
actor.key1 = 'value1'  # Abstracted assignment
print(ray.get(actor.key1))  # Outputs: value1

actor.key2 = 'value2'
print(ray.get(actor.key2))  # Outputs: value2

"""
ray.shutdown()

