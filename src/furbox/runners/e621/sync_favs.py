
import argparse
from furbox.connectors.e621 import E621Connector
from furbox.models.config import Config
from furbox.models.e621 import NewPost, Post
from furbox.runners.e621 import _SUBPARSERS
# from furbox.utils import cli, logging
from fluffless.utils import cli, logging

logger = logging.getLogger(__name__)


PARSER = cli.add_parser("sync-favs", subparsers=_SUBPARSERS, help="sync favourited images")
# _DOWNLOAD_PARSER.add_argument("search_query", help="search query or pool number to download posts from")


@cli.entrypoint(parser=PARSER)
def sync_favs(args: argparse.Namespace, config: Config) -> None:
    """ TODO. """
    

    # e621_connector = E621Connector(
    #     username=config.e621.username,
    #     api_key=config.e621.api_key,
    # )

    # out = e621_connector.get_posts(f"fav:{config.e621.username}", limit=3000)
    # exit()
    
    # with open("test.json") as f:
    #     import json
    #     data = json.load(f)
    #     # f.write(json.dumps(out[0], indent=4))

    # # print(data)

    # post = NewPost.from_api(data)
    # logger.print(post)

    # # print(len(out))

    # exit()

