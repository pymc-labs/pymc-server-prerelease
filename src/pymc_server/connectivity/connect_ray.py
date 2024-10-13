import ray
from ray import remote
from pymc_server.config.config_connectivity import (
    DEFAULTS_CONNECTIVITY_YOU_ARE_NOT_CONNECTED_MSG,
    DEFAULTS_STATEFUL_ACTOR_NAME,
)

class NotConnectedError(Exception):
    pass

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
        # List of local attributes that are resolved NOT remotely, we have overwritten __setattr__ and __getattr__ so we can't just do self.foo
        self.__dict__['local_attrs'] = set([
            'foo',
            'bar',
            'local_attrs',
            'allow_reconnect',
            'is_connected',
            'actor',
        ]) 
        # we can only do this with attributes named above
        self.is_connected = False
        self.allow_reconnect = allow_reconnect
        if self.allow_reconnect:
            try: 
                print('trying to reconnect')
                self.actor = ray.get_actor(
                    'remote_stateful_actor',
                    namespace=namespace
                )
                self.is_connected = True
            except ValueError as e:
                print(e)
                self._raise_not_connected()

        if not(self.is_connected):
            try: 
                self.actor = implementation.options(
                    name="remote_stateful_actor",
                    lifetime="detached", # this should never chagne
                    namespace=namespace
                ).remote(*args, **kwargs)

            except ValueError as e:
                print(e)
                self._raise_not_connected()

    def _raise_not_connected(self, custom_message=None):
        msg = custom_message if custom_message else DEFAULTS_CONNECTIVITY_YOU_ARE_NOT_CONNECTED_MSG 
        raise NotConnectedError(msg)
    def __kill__(self):
        ray.kill(self.actor)

    def __getattr__(self, attr_name):
        local_attrs = super().__getattribute__('local_attrs')
        if attr_name in local_attrs:
            return self.__dict__[attr_name] 

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
        if attr_name in self.__dict__['local_attrs']:
            # If the attribute is a local attribute, set it locally
            self.__dict__[attr_name] = value
        else:
            # If the attribute is not a local attribute, set it on the actor
            self.actor.set_attribute.remote(attr_name, value)


