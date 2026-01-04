
""" Module to provide functionality for comic updates on e621 pools.

Example usage of e621 comic: ::

    pools = [
        E621Comic(
            pool_id: 23079
            name: Duncan & Eddie
        )
    ]

    e621_connector = E621Connector(
        username=config.e621.username,
        api_key=config.e621.api_key,
    )

    e621_comics_update(
        api_connector=e621_connector,
        pools=pools,
        comic_path=config.comics.base_path,
    )
"""
from pathlib import Path

from fluffless.models.base_model import BaseModel
from fluffless.utils import logging

from furbox.connectors.downloader import download_files, get_numbered_file_names
from furbox.connectors.e621 import E621Connector, E621DbConnector
from furbox.models.e621 import Pool, Post
from furbox.utils.progress_bar import ProgressBar

logger = logging.getLogger(__name__)


class E621Comic(BaseModel):
    """ TODO - Extension of E621 Pool dataclass with local archive information. """

    # Name and pool ID associated with an E621 comic.
    pool_id:        int
    name:           str | None = None

    # Number of posts which are not expected to be downloaded (Ex. Deliberately excluded pages)
    local_offset:   int = 0
    # Number of posts which have been deleted on server side, and should be skipped over
    server_deleted: int = 0
    # Local directory to download files to, relative to the base comics directory
    dir_name:       str | None = None
    # Update the local files if True, only check for new items without downloading if False
    update:         bool = True


def e621_comics_update(api_connector: E621Connector, comics: list[E621Comic],
                       comic_path: Path, db_connector: E621DbConnector | None = None) -> None:
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
        db_pools = db_connector.get_pools(lambda pool: pool.pool_id in [pool.pool_id for pool in comics])
        db_pools.sort(key=lambda db_pool: [pool.pool_id for pool in comics].index(db_pool.pool_id))

        # Enrich each pool with the corresponding database information
        for comic, db_pool in zip(comics, db_pools, strict=True):
            comic.parse_dict(db_pool.to_dict())

    # Start a progress bar, and iterate through each pool
    progress = ProgressBar("Updating e621 pools", length=len(comics))
    for comic in comics:
        # If a database connector was not provided, fetch pool info using the API
        if not db_connector:
            pool = Pool.from_api(api_connector.get_pool(comic.pool_id))

        local_pool_dir = comic_path / (comic.dir_name or comic.name)
        if not local_pool_dir.exists():
            print(f"Folder '{local_pool_dir}' does not exist, creating it")
            local_pool_dir.mkdir(parents=True, exist_ok=True)

        # Count the number of local files present, and offset it by the provided local file offset
        local_num_posts = len([f for f in local_pool_dir.iterdir() if f.is_file()])
        offset_local_num_posts = local_num_posts + comic.local_offset

        # Calculate the difference between local posts and server posts
        page_num_diff = pool.post_count - comic.server_deleted - offset_local_num_posts
        if page_num_diff > 0:
            print(f"{comic.name} has {page_num_diff} new pages")

            if not comic.update:
                progress.advance()
                continue

            # Fetch all posts from the pool through the API
            post_data = api_connector.get_posts(
                search=f"pool:{comic.pool_id}",
                offset=None,
                limit=None,
                desc=comic.name,
            )
            posts = [Post.from_api(post) for post in post_data]

            # Enforce the order of posts with respect to the pool info data. This will filter
            # out removed posts, and handle posts where pool order does not match upload time
            posts.sort(key=lambda post: pool.post_ids.index(post.post_id))

            # Remove the URLs which correspond to files already downloaded
            download_urls = [post.file_info.url for post in posts][offset_local_num_posts:]

            download_files(
                url_name_pairs=list(zip(
                    download_urls,
                    get_numbered_file_names(
                        name=comic.name,
                        length=len(download_urls),
                        offset=local_num_posts,
                    ), strict=True,
                )),
                download_dir=local_pool_dir,
                description=f"Downloading {pool.name}",
            )

        # Report if the comic is ahead or matching the server count
        elif page_num_diff < 0:
            print(f"\033[34m{comic.name} is ahead of e6 by {-page_num_diff} pages\033[0m")
        else:
            print(f"\033[32m{comic.name} is up to date\033[0m")

        progress.advance()

    progress.close()
