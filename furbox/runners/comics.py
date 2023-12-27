""" TODO. """
import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

from furbox.connectors.downloader import download_files, get_numbered_file_names
from furbox.connectors.e621 import E621Connector
from furbox.models.config import Config
from furbox.models.e621 import Pool, Post
from furbox.runners import cli

import yaml

logger = logging.getLogger(__name__)

_PARSER = cli.create_subparser("comics_update", has_subparsers=True, help="TODO.")


@dataclass
class E621Comic(Pool):
    """ TODO. """

    offset: int = 0
    folder: str = None
    update: bool = True

    @property
    def valid_post_count(self) -> str:
        """ TODO. """
        if self.offset < 0:
            return self.post_count + self.offset

        if self.offset > 0:
            return self.post_count - self.offset

        return self.post_count


def e621_comics_update(e621_connector: E621Connector, pools: list[E621Comic],
                       comic_path: str, use_database: bool = False) -> None:
    """ TODO. """
    for pool in pools:
        pool.from_api(e621_connector.get_pool(pool.pool_id))

        local_folder = Path(comic_path) / (pool.folder or pool.name)

        if not local_folder.exists():
            logger.warning(f"Folder '{local_folder}' does not exist, creating it")
            local_folder.mkdir(parents=True, exist_ok=True)

        # Download the new pages if the server has more than local
        local_num_posts = len([f for f in local_folder.iterdir() if f.is_file()])

        # TODO - Need to use valid posts to cover offsets
        if local_num_posts < pool.valid_post_count:
            print(f"{pool.name} has {pool.valid_post_count - local_num_posts} new pages")

            # If the update flag is set, update the comic
            if pool.update:
                # TODO - kwargs
                post_data = e621_connector.get_posts(f"pool:{pool.pool_id}", None, None, pool.name)
                posts = [Post().from_api(post) for post in post_data]

                # Remove deleted items from the pool
                posts = [post for post in posts if not post.flags.deleted]

                # TODO - Can be improved
                # If the target is a pool, use the pool info to enforce image order
                # Match the images to the correct order stated by the pool
                post_id_keyed = {post.post_id: post for post in posts}
                posts = [post_id_keyed[post_id] for post_id in pool.post_ids if post_id in post_id_keyed]

                # TODO - Set offset? - This can probably be done better
                index = local_num_posts + (pool.offset if pool.offset > 0 else 0)
                urls = [post.file_info.url for post in posts][index:]

                file_names = get_numbered_file_names(pool.name, len(urls), local_num_posts)

                download_files(f"Downloading {pool.name}", urls, file_names, local_folder)

        # Report if the comic is ahead or matching the server
        elif local_num_posts > pool.post_count:
            print(f"\033[34m{pool.name} is ahead of e6 by {local_num_posts - pool.post_count} pages\033[0m")
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
        pools = sorted(
            [E621Comic().parse_dict(data) for data in e621_data],
            key=lambda pool: pool.name or "",
        )

        e621_connector = E621Connector(config.e621.username, config.e621.api_key)
        e621_comics_update(e621_connector, pools, config.comics.base_path)
