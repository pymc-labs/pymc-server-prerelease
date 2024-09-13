
import click
#import colorama
#import dotenv
import sky
from file_merger import mergeYaml
from launch_cli import launch as cli_launch
@click.group()
def cli():
    pass

@click.command()
#@click.option('--count', default=1, help='Number of greetings.')
#@click.option('--name', prompt='Your name',
#              help='The person to greet.')
def status():
    task = sky.Task(run='echo hello SkyPilot')
    task.set_resources(sky.Resources(cloud=sky.AWS(), accelerators='V100:4'))
    sky.launch(task, cluster_name='my-cluster')
    click.echo(sky.status(cluster_names=None, refresh=False))
    """Simple program that greets NAME for a total of COUNT times."""
    #for x in range(count):
    #    click.echo(f"Hello {name}!")

cli.add_command(status)

@click.command()
#@click.option('--count', default=1, help='Number of greetings.')
#@click.option('--name', prompt='Your name',
#              help='The person to greet.')
def launch():
    print('Launch Mode ::')
    '''
    task = sky.Task(run='echo hello SkyPilot')
    task.set_resources(sky.Resources(cloud=sky.AWS(), accelerators='V100:4'))
    sky.launch(task, cluster_name='my-cluster')
    click.echo(sky.status(cluster_names=None, refresh=False))
    '''
    
   # print(mergeYaml(devPath='dev.yaml',pymcPath='pymc.yaml'))
    cli_launch()

    """Simple program that greets NAME for a total of COUNT times."""
    #for x in range(count):
    #    click.echo(f"Hello {name}!")

cli.add_command(launch)
if __name__ == '__main__':
    cli()
