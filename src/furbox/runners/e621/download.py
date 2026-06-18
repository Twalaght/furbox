""" Download a search query or pool from e621. """
import argparse
import itertools
import logging
from collections import Counter
from pathlib import Path
from typing import cast

from fluffless.utils import cli
from rich.prompt import Confirm, Prompt

from furbox.connectors.downloader import download_files, get_numbered_file_names, UrlFileTarget
from furbox.connectors.e621 import E621Connector
from furbox.models.config import Config
from furbox.models.e621 import META_ARTISTS, Pool, Post
from furbox.runners.e621 import _SUBPARSERS

logger = logging.getLogger(__name__)


PARSER = cli.add_parser("download", subparsers=_SUBPARSERS, help="TODO.")
PARSER.add_argument("search_query", help="Search query to download posts from.")
PARSER.add_argument(
    "--pool",
    action="store_true",
    help="Download posts based on a pool, search query must be an integer if using pool mode.",
)


@cli.entrypoint(PARSER)
def download(args: argparse.Namespace, config: Config) -> int | None:
    """ Download from e621 based on search parameters. """
    if config.e621 is None:
        logger.error("Config requires `e621` to be defined to use the download utility")
        return 1

    search_query = cast(str, args.search_query)
    pool_mode = args.pool

    e621_connector = E621Connector(
        username=config.e621.username,
        api_key=config.e621.api_key,
    )

    # For a purely numeric search term, confirm if the user did not supply the pool flag.
    if search_query.isnumeric() and not pool_mode:
        pool_mode = Confirm("Search term is numeric but pool flag not provided, download as a pool?")

    if pool_mode:
        # Fetch pool information from the pools endpoint, and posts information using the general search.
        pool = Pool.from_api(e621_connector.get_pool(search_query))
        posts = [Post.from_api(post) for post in e621_connector.get_posts(f"pool:{search_query}")]
        posts = sorted(posts, key=lambda x: pool.post_ids.index(x.post_id))

        # Prompt the user for the title of the pool, defaulting to the name defined by the pool.
        title = Prompt.ask("Pool title", default=pool.name.replace("_", " "))

        # Set the artist of the pool by finding the most common artist tag applied to the posts.
        artist_tags = list(itertools.chain(*[post.tags.artist for post in posts]))
        artist_tags = [artist for artist in artist_tags if artist not in META_ARTISTS]
        artist = Counter(artist_tags).most_common(1)[0][0].capitalize()
        artist = Prompt.ask("Artist", default=artist)

        # Generate download URLs and associated file name pairs.
        file_targets = get_numbered_file_names(
            download_urls=[post.file_info.url for post in posts],
            download_directory=Path.cwd() / f"{artist} - {title}",
            name=title,
        )

        download_files(file_targets=file_targets, description=f"Downloading {title}")
    else:
        download_dir = Prompt.ask(
            prompt="Download directory",
            default="".join([c if c.isalpha() else "_" for c in search_query]),
        )

        # Fetch pool information from the pools endpoint, and posts information using the general search.
        posts = [Post.from_api(post) for post in e621_connector.get_posts(search_query)]

        # Generate download URLs and associated file name pairs.
        file_targets = [UrlFileTarget(
            url=post.file_info.url,
            file_name=str(post.post_id),
            download_directory=Path.cwd() / download_dir,
            extension=post.file_info.ext,
        ) for post in posts]

        download_files(file_targets=file_targets, description=f"Downloading '{search_query[:60]}'")

    return None
