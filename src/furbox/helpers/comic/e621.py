
""" Module to provide functionality for comic updates on e621 pools.

Example usage of e621 comic downloading: ::

    e621_comics = [
        E621Comic(
            pool_id=23079,
            name="Duncan & Eddie",
        )
    ]

    e621_comics_update(config=config, e621_comics=pools)
"""
from typing import cast

from fluffless.utils import logging

from furbox.connectors.downloader import download_files, get_numbered_file_names
from furbox.connectors.e621 import E621Connector, E621DbConnector
from furbox.models.comic import E621Comic
from furbox.models.config import Config
from furbox.models.e621 import Pool, Post
from furbox.utils.progress_bar import ProgressBar

logger = logging.getLogger(__name__)


def update_e621_comics(config: Config, e621_comics: list[E621Comic], use_db: bool = False) -> None:
    """ Update e621 comics defined by comic definition file. """
    if config.e621 is None:
        logger.info("Config was not provided for e621, not updating")
        return

    config.comics = cast(Config.Comics, config.comics)

    # Sort parsed data by pool name, and update comics in this order.
    local_comics = sorted(e621_comics, key=lambda comic: comic.name or "")

    e621_connector = E621Connector(
        username=config.e621.username,
        api_key=config.e621.api_key,
    )

    # If a database connector was provided, fetch pool info using a database dump.
    if use_db:
        db_connector = E621DbConnector(config.misc.cache_dir or None)
        db_pools = {
            pool.pool_id: pool for pool in
            db_connector.get_pools(
                filter_condition=lambda pool: pool.pool_id in [local_comic.pool_id for local_comic in local_comics],
            )
        }

    # Start a progress bar, and iterate through each pool
    with ProgressBar("Updating e621 pools", length=len(e621_comics)) as progress:
        for comic in e621_comics:
            pool = db_pools.get(comic.pool_id, Pool.from_api(e621_connector.get_pool(comic.pool_id)))
            comic_name = comic.name or pool.name

            local_pool_dir = config.comics.base_path / (comic.dir_name or comic_name)
            if not local_pool_dir.exists():
                logger.print(f"Folder '{local_pool_dir}' does not exist, creating it")
                local_pool_dir.mkdir(parents=True, exist_ok=True)

            # Count the number of local files present, and offset it by the provided local file offset.
            local_num_posts = len([f for f in local_pool_dir.iterdir() if f.is_file()])
            offset_local_num_posts = local_num_posts + comic.local_offset

            # Calculate the difference between local posts and server posts.
            page_num_diff = pool.post_count - comic.server_deleted - offset_local_num_posts

            # Report if the comic is ahead or matching the server count.
            if page_num_diff < 0:
                logger.print(f"[blue]{comic.name} is ahead of e621 by {-page_num_diff} pages[/]")
                progress.advance()
                continue
            if page_num_diff == 0:
                logger.print(f"[green]{comic.name} is up to date[/]")
                progress.advance()
                continue

            logger.print(f"{comic.name} has {page_num_diff} new pages")
            if not comic.update:
                progress.advance()
                continue

            # Fetch all posts from the pool through the API
            post_data = e621_connector.get_posts(
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

            url_name_pairs = list(zip(
                download_urls,
                get_numbered_file_names(
                    name=comic_name,
                    length=len(download_urls),
                    offset=local_num_posts,
                ),
                strict=True,
            ))

            download_files(
                url_name_pairs=url_name_pairs,
                download_dir=local_pool_dir,
                description=f"Downloading {comic_name}",
            )

            progress.advance()
