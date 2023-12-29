""" Runner to update and synchronise collections of comics. """
import argparse
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from furbox.connectors.downloader import download_files, get_numbered_file_names
from furbox.connectors.e621 import E621Connector, E621DbConnector
from furbox.models.config import Config
from furbox.models.e621 import Pool, Post
from furbox.runners import cli

import yaml

logger = logging.getLogger(__name__)

_PARSER = cli.create_subparser("comics_update", has_subparsers=True, help="update local comic files")
_PARSER.add_argument("--use-db", action="store_true", help="fetch e621 pool data from a database dump")


@dataclass
class E621Comic(Pool):
    """ Extension of E621 Pool dataclass with local archive information. """

    # Number of posts which are not expected to be downloaded (Ex. Deliberately excluded pages)
    local_offset:   int = 0
    # Number of posts which have been deleted on server side, and should be skipped over
    server_deleted: int = 0
    # Local directory to download files to, relative to the base comics directory
    dir_name:       str | os.PathLike = None
    # Update the local files if True, only check for new items without downloading if False
    update:         bool = True


def e621_comics_update(api_connector: E621Connector, pools: list[E621Comic],
                       comic_path: str | os.PathLike, db_connector: E621DbConnector = None) -> None:
    """ Check for new posts and download new items for E621 pools.

    Args:
        api_connector (E621Connector): E621 connector object to interact with the API.
        pools (list[E621Comic]): List of pool objects, with information about the local archive.
        comic_path (str | os.PathLike): Base directory for comic archives.
        db_connector (E621DbConnector, optional): E621 database connector, if provided it will be used \
                                                  instead of the API to determine if pools have updates. \
                                                  Defaults to None.
    """
    # If a database connector was provided, fetch pool info using a database dump
    if db_connector:
        db_pools = db_connector.get_pools(lambda pool: pool.pool_id in [pool.pool_id for pool in pools])
        db_pools.sort(key=lambda db_pool: [pool.pool_id for pool in pools].index(db_pool.pool_id))

        # Enrich each pool with the corresponding database information
        for pool, db_pool in zip(pools, db_pools):
            pool.parse_dict(db_pool.to_dict())

    for pool in pools:
        # If a database connector was not provided, fetch pool info using the API
        if not db_connector:
            pool.from_api(api_connector.get_pool(pool.pool_id))

        local_pool_dir = Path(comic_path) / (pool.dir_name or pool.name)
        if not local_pool_dir.exists():
            print(f"Folder '{local_pool_dir}' does not exist, creating it")
            local_pool_dir.mkdir(parents=True, exist_ok=True)

        # Count the number of local files present, and offset it by the provided local file offset
        local_num_posts = len([f for f in local_pool_dir.iterdir() if f.is_file()])
        offset_local_num_posts = local_num_posts + pool.local_offset

        # Calculate the difference between local posts and server posts
        page_num_diff = pool.post_count - pool.server_deleted - offset_local_num_posts
        if page_num_diff > 0:
            print(f"{pool.name} has {page_num_diff} new pages")

            if not pool.update:
                continue

            # Fetch all posts from the pool through the API
            post_data = api_connector.get_posts(
                search=f"pool:{pool.pool_id}",
                offset=None,
                limit=None,
                desc=pool.name,
            )
            posts = [Post().from_api(post) for post in post_data]

            # Enforce the order of posts with respect to the pool info data. This will filter
            # out removed posts, and handle posts where pool order does not match upload time
            posts.sort(key=lambda post: pool.post_ids.index(post.post_id))

            # Remove the URLs which correspond to files already downloaded
            download_urls = [post.file_info.url for post in posts][offset_local_num_posts:]

            download_files(
                url_name_pairs=list(zip(
                    download_urls,
                    get_numbered_file_names(
                        name=pool.name,
                        length=len(download_urls),
                        offset=local_num_posts,
                    ),
                )),
                download_dir=local_pool_dir,
                desc=f"Downloading {pool.name}",
            )

        # Report if the comic is ahead or matching the server count
        elif page_num_diff < 0:
            print(f"\033[34m{pool.name} is ahead of e6 by {-page_num_diff} pages\033[0m")
        else:
            print(f"\033[32m{pool.name} is up to date\033[0m")


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

        e621_comics_update(
            api_connector=e621_connector,
            pools=pools,
            comic_path=config.comics.base_path,
            db_connector=E621DbConnector() if args.use_db else None,
        )
