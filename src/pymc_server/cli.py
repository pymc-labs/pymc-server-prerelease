import click

@click.group()
def cli():
    pass

    @cli.command()
    def foo():
        click.echo('bar')
