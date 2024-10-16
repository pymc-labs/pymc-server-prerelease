#!/usr/bin/env python
import ray
# -*- coding: utf-8 -*-


ray.init(namespace="my_namespace")
# Get the actor from the namespace "my_namespace"
actor = ray.get_actor("stateful_actor")
remote_val = actor.foobar.remote()
print(ray.get(remote_val))

#assert  remote_val == 'bar'

"""
# Use the abstracted way to set and get values dynamically
actor.key1 = 'value1'  # Abstracted assignment
print(ray.get(actor.key1))  # Outputs: value1

actor.key2 = 'value2'
print(ray.get(actor.key2))  # Outputs: value2
"""

ray.shutdown()
