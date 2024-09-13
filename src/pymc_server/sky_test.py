import sky 

task = sky.Task(run='echo hello SkyPilot')
task.set_resources(sky.Resources(cloud=sky.AWS(), accelerators='V100:4'))
sky.launch(task, cluster_name='my-cluster')
sky.status(cluster_names=None, refresh=False)
sky.down( cluster_name='my-cluster',purge=True)