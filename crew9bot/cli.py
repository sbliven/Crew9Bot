"""Console script for crew9bot."""
import sys
import click


@click.command()
def main(args=None):
    """Console script for crew9bot."""
    click.echo("Replace this message by putting your code into "
               "crew9bot.cli.main")
    click.echo("See click documentation at https://click.palletsprojects.com/")
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
