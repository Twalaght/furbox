""" TODO. """
import argparse
import logging

from furbox.models.config import Config
from furbox.runners import cli

logger = logging.getLogger(__name__)

_PARSER = cli.create_subparser("e621", has_subparsers=True, help="TODO.")
_SUBPARSERS = _PARSER.add_subparsers(required=True)

_DOWNLOAD_PARSER = _SUBPARSERS.add_parser("download", parents=[cli.base_leaf_parser()], help="TODO.")
_DOWNLOAD_PARSER.add_argument("search_query", help="search query or pool number to download posts from")


@cli.entrypoint(parser=_DOWNLOAD_PARSER)
def download(args: argparse.Namespace, config: Config) -> None:
    """ TODO. """
    return
