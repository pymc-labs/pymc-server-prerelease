from pymc_server.connectivity.connect_ray import RemoteStatefulActorWrapper, Actor
pymcs_namespace = 'dev_2'

server = RemoteStatefulActorWrapper(
    pymcs_namespace,
    Actor,
    allow_local_fallback=True,
)

breakpoint()

