""" TODO. """
import argparse
import logging

from fluffless.utils import cli

from furbox.models.config import Config
from furbox.runners.e621 import _SUBPARSERS

logger = logging.getLogger(__name__)


PARSER = cli.add_parser("download", subparsers=_SUBPARSERS, help="TODO.")
PARSER.add_argument("search_query", help="search query or pool number to download posts from")


@cli.entrypoint(PARSER)
def download(args: argparse.Namespace, config: Config) -> None:
    """ TODO. """
    del args, config
    raise NotImplementedError
