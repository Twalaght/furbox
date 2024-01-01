""" Runner to update and synchronise collections of comics. """
import argparse
import logging
from pathlib import Path

from furbox.connectors.e621 import E621Connector, E621DbConnector
from furbox.helpers.e621_comic import E621Comic, e621_comics_update
from furbox.models.config import Config
from furbox.runners import cli
import yaml

logger = logging.getLogger(__name__)

_PARSER = cli.create_subparser("comics_update", has_subparsers=True, help="update local comic files")
_PARSER.add_argument("--use-db", action="store_true", help="fetch e621 pool data from a database dump")


@cli.entrypoint(parser=_PARSER)
def comics_update(args: argparse.Namespace, config: Config) -> None:
    """ TODO. """
    comic_base_path = Path(config.comics.base_path)
    comic_yaml_path = comic_base_path / (config.comics.database_file or "comics.yaml")

    if not comic_yaml_path.exists() or not comic_yaml_path.is_file():
        raise FileNotFoundError(f"File '{comic_yaml_path}' does not exist or is not a file")

    with open(comic_yaml_path) as f:
        comic_data = yaml.safe_load(f)

    if e621_data := comic_data.get("e621"):
        # Sort pools by name, if a name was provided
        pools = sorted(
            [E621Comic().parse_dict(data, overwrite=True) for data in e621_data],
            key=lambda pool: pool.name or "",
        )

        e621_connector = E621Connector(
            username=config.e621.username,
            api_key=config.e621.api_key,
        )

        e621_db_connector = E621DbConnector(config.misc.cache_dir or None)

        e621_comics_update(
            api_connector=e621_connector,
            pools=pools,
            comic_path=config.comics.base_path,
            db_connector=e621_db_connector if args.use_db else None,
        )
