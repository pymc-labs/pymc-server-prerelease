import ray
from ray import remote

@remote
class Actor:
    def __init__(self, foo='foo', bar='bar'):
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
        return getattr(self, attr_name)

    def set_attribute(self, attr_name, value):
        setattr(self, attr_name, value)

class RemoteStatefulActorWrapper:
    """
    A ray backed remote actor that is stateful and can be reconnected to.

    """
    def __init__(
            self,
            namespace,
            implementation,
            allow_reconnect,
            *args, 
            **kwargs
    ):
        if allow_reconnect:
            self.actor = ray.get_actor('remote_stateful_actor', namespace=namespace)
        else:
            self.actor = implementation.options(
                name="remote_stateful_actor",
                lifetime="detached", # this should never chagne
                namespace=namespace
            ).remote(*args, **kwargs)


    def __kill__(self):
        ray.kill(self.actor)

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
        print(attr_name)
        if attr_name == "actor":
            self.__dict__[attr_name] = value
        else:
            self.actor.set_attribute.remote(attr_name, value)


