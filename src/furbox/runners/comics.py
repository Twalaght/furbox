""" Runner to update and synchronise collections of comics. """
import argparse
import logging
from enum import auto, StrEnum

from fluffless.utils import cli

from furbox.helpers.comic.e621 import update_e621_comics
from furbox.models.comic import Comics
from furbox.models.config import Config

logger = logging.getLogger(__name__)


class ComicTypes(StrEnum):
    """ String enum of all supported comic types for the synchronisation runner. """

    E621 = auto()

    @classmethod
    def all_types(cls) -> list[str]:
        """ Convert string enum to a list of strings, for all valid keys. """
        return [str(comic.value) for comic in cls]


PARSER = cli.add_parser(name="comics_update", help="Update local comic files.")
PARSER.add_argument("comic_type", nargs="*", type=ComicTypes, choices=ComicTypes.all_types(),
                    help=(f"Types of comic to update. All types will be downloaded if not specified. "
                          f"Allowed comic types are '{'\', \''.join(ComicTypes.all_types())}'."))
PARSER.add_argument("--use-db", action="store_true", help="Fetch e621 pool data from a database dump.")


@cli.entrypoint(parser=PARSER)
def comics_update(args: argparse.Namespace, config: Config) -> int | None:
    """ Update comics on disk based on config definitions. """
    if config.comics is None:
        logger.error("Config requires `comics` to be defined to use comic update utility")
        return 1

    # If no argument was provided for comic types, enable all of them.
    enabled_categories = args.comic_type or ComicTypes.all_types()

    comic_base_path = config.comics.base_path
    comic_db_yaml_path = comic_base_path / config.comics.database_file

    if not comic_db_yaml_path.exists() or not comic_db_yaml_path.is_file():
        raise FileNotFoundError(f"File '{comic_db_yaml_path}' does not exist or is not a file")

    comics = Comics.load_from_yaml(comic_db_yaml_path)

    if comics.e621 and ComicTypes.E621 in enabled_categories:
        update_e621_comics(
            config=config,
            e621_comics=comics.e621,
            use_db=args.use_db,
        )

    return None
