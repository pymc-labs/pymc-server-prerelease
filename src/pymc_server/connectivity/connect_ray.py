import os
import ray
import traceback
from ray import remote
from pymc_server.config.config_connectivity import (
    DEFAULTS_CONNECTIVITY_YOU_ARE_NOT_CONNECTED_MSG,
    DEFAULTS_CONNECTIVITY_ALREADY_CONNECTED_MSG,
    DEFAULTS_STATEFUL_ACTOR_NAME,
    DEFEAULTS_RAY_DEBUG_ENV_VAR_NAME,
)

class NotConnectedError(Exception):
    pass

class AlreadyConnected(Exception):
    pass

class Pong:
    """ Used to send back to the wrapper to check the connection to the remote Actor"""
    pass

@remote
class Actor:
    """An example actor that can be used as the RemoteStatefulActorWrapper implementation attribute"""
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

    def _ping(self):
        return Pong()

    def get_attribute(self, attr_name):
        return getattr(self, attr_name)

    def set_attribute(self, attr_name, value):
        setattr(self, attr_name, value)

class RemoteStatefulActorWrapper:
    """
    A ray backed remote actor that is stateful and can be reconnected to.

    Arguments:
        namespace (str): A namespace where your actor will be ran. Can be a random string, but should be unique when the pymcs server is shared with other jobs or users.
        implementation (class): A class that represents the remote code to be executed. Needs to follow the Actor constructor.
        allow_local_fallback (bool): This parameter controls if a fallback (local) instance should be started if the connection to the server fails for whatever reason.

    Example:
        ```python

        server = RemoteStatefulActorWrapper(
            'my_namespace',
            implementation=Actor,
            allow_local_fallback=True, # set to False if you want to crash the program when no connection can be made
        )
        server._ping() # should return a Pong instance or fail if not connected
        ```

    There are different connection strategies available depending on your usecase. 
    The server will first try to find a session with your namespace and if not present, start one.
    If a connection cannot be made for any reason, setting the parameter `alllow_local_fallback` to `True` does allow to startup your job correctly, 
    but with a local instance.

    """
    def __init__(
            self,
            namespace: str ,
            implementation: Actor,
            allow_local_fallback : bool,
            *args, 
            **kwargs
    ) -> None:
        # List of local attributes that are resolved NOT remotely, we have overwritten __setattr__ and __getattr__ so we can't just do self.foo
        self.__dict__['local_attrs'] = set([
            'actor',
            '_kill',
            'local_attrs',
            'allow_local_fallback',
            'namespace',
            'is_connected',
            'implementation',
            '_reconnect_actor',
            '_connect_actor',
            '_graceful_reconnect_actor_strategy',
            'debug',
        ]) 
        self.debug = kwargs.pop('debug', False)  # Default to False if 'debug' is not provided
        # we can only do this with attributes named above
        self.is_connected = False
        self.allow_local_fallback = allow_local_fallback
        self.namespace = namespace
        self.implementation = implementation
        self.actor = None
        self._init_connection(*args, **kwargs)

    def _reconnect_actor(self, namespace=None):
        """ Reconnect to ray backed remote actor implementation"""
        return ray.get_actor(
            'remote_stateful_actor',
            namespace=namspace if namespace else self.namespace
        )
    def _connect_actor(self, namespace=None, implementation=None, *args, **kwargs):
        """ Init a new connection to ray with our implementation actor"""
        remote_code = implementation if implementation else self.implementation
        return remote_code.options(
            name="remote_stateful_actor",
            lifetime="detached", # this should never chagne
            namespace=self.namespace
        ).remote(*args, **kwargs)

    def _graceful_reconnect_actor_strategy(self, namespace=None, *args, **kwargs):
        """
        Will try to reconnect or build a new connection if no actor is found .
        Deployment Strategy:
        
        a) good connection
        We'll connect to the remote instance

        b) bad connection - allow_local_fallback = True
        Will complain but connect to a locally started instance

        c) bad connection - allow_local_fallback = False
        Complain and crash the program
        """
        print('Initializing connect/ reconnect.')
        maybe_actor = None
        # controls if we want to error out
        have_grace = True
        env_vars = {}
        if self.debug:
            env_vars.update({DEFEAULTS_RAY_DEBUG_ENV_VAR_NAME: "1"})

        should_fail_when_no_active_ray = not(self.allow_local_fallback)
        try:
            ray.init(
                address='auto',# if should_fail_when_no_active_ray else None,
                namespace=self.namespace,
                runtime_env={
                    "env_vars": env_vars,
                }
            )
        except Exception as e:
            have_grace = False
            print(traceback.format_exc())
            pass

        try:
            # skip the next step if we have a good connection
            self._raise_already_connected_on_good_connection()
            # try to initiate a new connection
            maybe_actor = self._connect_actor(*args, **kwargs) if have_grace else None
            # we're getting sure there's no good connection

        # we might have still a good chance for a good connection, check it next
        except Exception as e:
            print(e)
            pass
        # try a reconnect to our actor first, 
        # if this fails ini a new connection
        try:
            maybe_actor = self._reconnect_actor()

        # we might have still a good chance for a good connection, check it next
        except Exception as e:
            print(e)
            pass


        # If the connection is good, return the actor.
        # if we're not connected here, we're either seeing a completely new instance or going to fallback mode. 
        if maybe_actor:
            return maybe_actor

        # if fallback mode is not allowed, error the program
        if not(self.allow_local_fallback) and not(have_grace): raise NotConnectedError(DEFAULTS_CONNECTIVITY_YOU_ARE_NOT_CONNECTED_MSG)
        # try to initiate a new connection, this will connect to ta local ray instance or a remote instance if we have never seen it
        try:
            maybe_actor = self._connect_actor(*args, **kwargs)

        except Exception as e:
            print(e)
            pass # the connection will be checked again

        # show a waring to the user since we are in fallback mode
        if(self.allow_local_fallback): self._raise_not_connected(warn_only=True)

        return maybe_actor


    def _init_connection(self, *args, **kwargs):
        # make remote debugger listeners
        # first connection attempt, return if good
        self.actor = self._graceful_reconnect_actor_strategy(*args, **kwargs)

        maybe_connected = self._check_is_connected()
        self.is_connected = maybe_connected
        if self.is_connected:
            return True
        return False
        # we're not allowed to continue, fail the program.
        if not(self.allow_local_fallback):
            self._raise_not_connected()

        try:
            # we are only able to connect to a local ray instance, warn the user
            self._raise_not_connected(warn_only=True)
            self.actor = self._connect_actor(*args, **kwargs)

        except Exception as e:
            print(traceback.format_exc())
            pass # we'll raise next if the connection failed

        # final check 
        self.is_connected = self._check_is_connected_or_raise()


    def _raise_already_connected_on_good_connection(self, custom_message=None, warn_only=False):
        """
        Raise (or warn) when  connected. 
        This is useful for breaking a reconnect flow.
        """
        is_connected = self._check_is_connected()

        msg = custom_message if custom_message else DEFAULTS_CONNECTIVITY_ALREADY_CONNECTED_MSG 
        if not(warn_only) and is_connected: raise AlreadyConnected(msg)

    def _raise_not_connected(self, custom_message=None, warn_only=False):
        """
        Raise (or warn) when not connected. 
        This is only showing the messages/exception but not checking the connection
        """
        msg = custom_message if custom_message else DEFAULTS_CONNECTIVITY_YOU_ARE_NOT_CONNECTED_MSG 
        if not(warn_only): raise NotConnectedError(msg)
        print(msg)


    def _check_is_connected(self):
        """ Check if we do receive a pong when sending a ping to the server """
        try:
            maybe_pong = self._ping() # calls the remote actor
            return isinstance(maybe_pong, Pong)
        except Exception as e:
            return False

        return True

    def _check_is_connected_or_raise(self, warn_only=False):
        """ checks if we are connected (static parameter) and raises an error if not"""
        try:
            maybe_pong = self._ping() # calls the remote actor
            if not(isinstance(maybe_pong, Pong)) and not(warn_only) :
                raise NotConnectedError(DEFAULTS_CONNECTIVITY_YOU_ARE_NOT_CONNECTED_MSG)
        except Exception:
            if warn_only: 
                print(DEFAULTS_CONNECTIVITY_YOU_ARE_NOT_CONNECTED_MSG)
                return False
            raise NotConnectedError(DEFAULTS_CONNECTIVITY_YOU_ARE_NOT_CONNECTED_MSG)


        return True

    def __getattr__(self, attr_name):
        local_attrs = super().__getattribute__('local_attrs')
        """
        if  super().__getattribute__('debug'):
            print('CALLING GET', attr_name)
        """

        if self._is_debug_level(1): print('CALLING GET', attr_name)
        if attr_name in local_attrs:
            return self.__dict__[attr_name] 

        attr = ray.get(self.actor.get_attribute.remote(attr_name))

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
        if self._is_debug_level(): print('CALLING SET', attr_name, value)
        if attr_name in self.__dict__['local_attrs']:
            # If the attribute is a local attribute, set it locally
            self.__dict__[attr_name] = value
        else:
            # If the attribute is not a local attribute, set it on the actor
            #self.check_is_connected_or_raise()
            self.actor.set_attribute.remote(attr_name, value)

    def _is_debug_level(self, level=1): return int(os.getenv('DEBUG', 0)) >= level
    def _kill(self): ray.kill(self.actor)


