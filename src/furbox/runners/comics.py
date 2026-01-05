""" Runner to update and synchronise collections of comics. """
import argparse
import logging
import sys
from enum import auto, StrEnum

import yaml
from fluffless.utils import cli

from furbox.connectors.e621 import E621Connector, E621DbConnector
from furbox.helpers.e621_comic import e621_comics_update, E621Comic
from furbox.models.config import Config

logger = logging.getLogger(__name__)


class ComicTypes(StrEnum):
    """ String enum of all supported comic types for the synchronisation runner. """

    E621 = auto()

    def all_types() -> str:
        """ Convert string enum to a list of strings, for all valid keys. """
        return [str(comic) for comic in ComicTypes]


PARSER = cli.add_parser(name="comics_update", help="Update local comic files.")
PARSER.add_argument("comic_type", nargs="*", type=ComicTypes, choices=ComicTypes.all_types(),
                    help=(f"Types of comic to update. All types will be downloaded if not specified. "
                          f"Allowed comic types are '{'\', \''.join(ComicTypes.all_types())}'."))
PARSER.add_argument("--use-db", action="store_true", help="Fetch e621 pool data from a database dump.")


@cli.entrypoint(parser=PARSER)
def comics_update(args: argparse.Namespace, config: Config) -> None:
    """ Update comics on disk based on config definitions. """
    if config.comics is None:
        logger.error("Config requires `comics` to be defined to use comic update utility")
        sys.exit(1)

    # If no argument was provided for comic types, enable all of them.
    enabled_categories = args.comic_type or ComicTypes.all_types()

    comic_base_path = config.comics.base_path
    comic_db_yaml_path = comic_base_path / config.comics.database_file

    if not comic_db_yaml_path.exists() or not comic_db_yaml_path.is_file():
        raise FileNotFoundError(f"File '{comic_db_yaml_path}' does not exist or is not a file")

    with comic_db_yaml_path.open() as f:
        comic_data = yaml.safe_load(f)

    if (
        ComicTypes.E621 in enabled_categories and
        (e621_data := comic_data.get("e621"))
    ):
        # Sort parsed data by pool name, and update comics in this order.
        pools = sorted(
            [E621Comic(**data) for data in e621_data],
            key=lambda pool: pool.name or "",
        )

        e621_connector = E621Connector(
            username=config.e621.username,
            api_key=config.e621.api_key,
        )

        e621_comics_update(
            api_connector=e621_connector,
            comics=pools,
            comic_path=config.comics.base_path,
            db_connector=E621DbConnector(config.misc.cache_dir or None) if args.use_db else None,
        )
