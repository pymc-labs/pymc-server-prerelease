from pymc_server.connectivity.connect_ray import RemoteStatefulActorWrapper, Actor
server = RemoteStatefulActorWrapper('dev_2', Actor, allow_reconnect=True)

breakpoint()

