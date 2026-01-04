""" Runner to update and synchronise collections of comics. """
import argparse
import logging
import sys

import yaml
from fluffless.utils import cli

from furbox.connectors.e621 import E621Connector, E621DbConnector
from furbox.helpers.e621_comic import e621_comics_update, E621Comic
from furbox.models.config import Config

logger = logging.getLogger(__name__)


PARSER = cli.add_parser(name="comics_update", help="Update local comic files.")
# TODO - Make strict, currently unused.
PARSER.add_argument("comic_type", nargs="*", default=["all"], help="Types of comic to update.")
PARSER.add_argument("--use-db", action="store_true", help="Fetch e621 pool data from a database dump.")

logger = logging.getLogger(__name__)


@cli.entrypoint(parser=PARSER)
def comics_update(args: argparse.Namespace, config: Config) -> None:
    """ Update comics on disk based on config definitions. """
    if not config.comics:
        logger.error("Config requires `comics` to be defined to use comic update utility")
        sys.exit(1)

    comic_base_path = config.comics.base_path
    comic_yaml_path = comic_base_path / config.comics.database_file

    # TODO - This is a bad system.
    args.comic_type = [comic_type.lower() for comic_type in args.comic_type]

    if not comic_yaml_path.exists() or not comic_yaml_path.is_file():
        raise FileNotFoundError(f"File '{comic_yaml_path}' does not exist or is not a file")

    with comic_yaml_path.open() as f:
        comic_data = yaml.safe_load(f)

    if (e621_data := comic_data.get("e621")):
        # Sort parsed data by pool name, and update comics in this order
        pools = sorted(
            [E621Comic(**data) for data in e621_data],
            key=lambda pool: pool.name or "",
        )

        e621_connector = E621Connector(
            username=config.e621.username,
            api_key=config.e621.api_key,
        )

        e621_db_connector = E621DbConnector(config.misc.cache_dir or None)

        e621_comics_update(
            api_connector=e621_connector,
            comics=pools,
            comic_path=config.comics.base_path,
            db_connector=e621_db_connector if args.use_db else None,
        )
