"""Console script for crew9bot."""
import logging
import sys
from typing import List, Optional

import click

from . import crew9bot


@click.command()
def main(args: Optional[List[str]] = None) -> int:
    """Console script for crew9bot."""
    # config = load_config()
    # for key in config['crew9bot']:
    #     click.echo(f"{key}: {config['crew9bot'][key]}")

    logging.basicConfig(
        format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s",
        level=logging.INFO,
    )

    bot = crew9bot.Crew9Bot()
    bot.start()
    bot.client.run_until_disconnected()

    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
