""" Synchronise upstream e621 favourites with local files. """
import argparse
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import cast, NamedTuple

from fluffless.utils import cli, logging

from furbox.connectors.downloader import download_files, UrlFileTarget
from furbox.connectors.e621 import E621Connector
from furbox.helpers.utils import execute_futures, hash_file
from furbox.models.config import Config
from furbox.models.e621 import Post, Tag
from furbox.runners.e621 import _SUBPARSERS
from furbox.utils.progress_bar import ProgressBar

logger = logging.getLogger(__name__)

PARSER = cli.add_parser("fav-sync", subparsers=_SUBPARSERS,
                        help=" Synchronise upstream e621 favourites with local files.")
PARSER.add_argument("--dry-run", action="store_true", help="Preview updates without modifying files.")


@cli.entrypoint(PARSER)
def fav_sync(args: argparse.Namespace, config: Config) -> int | None:
    """ Sync e621 favourites with local files. """
    if config.e621 is None:
        logger.error("Config requires `e621` to be defined to use fav sync utility")
        return 1

    if config.e621.fav_paths is None:
        logger.error("Config requires `e621.fav_paths` to be defined to use fav sync utility")
        return 1

    dry_run = args.dry_run

    e621_connector = E621Connector(
        username=config.e621.username,
        api_key=config.e621.api_key,
    )

    # Fetch all favourites for the user defined in config.
    favourites = [Post.from_api(post) for post in e621_connector.get_posts(f"fav:{config.e621.username}")]

    # Process each directory and aggregate rename and download tasks.
    tasks: list[RenameFileTarget | UrlFileTarget] = []
    for rating in Post.Rating:
        logger.print(f"Processing directory for posts rated '{rating.name.lower()}'")
        directory = cast(Path, getattr(config.e621.fav_paths, rating.name.lower()))
        tasks += process_directory(
            e621_connector=e621_connector,
            directory=directory,
            rating=rating,
            favourites=favourites,
        )

    # Split rename and download tasks into their own lists, to be actioned separately.
    rename_tasks = [x for x in tasks if isinstance(x, RenameFileTarget)]
    download_tasks = [x for x in tasks if isinstance(x, UrlFileTarget)]

    if dry_run:
        logger.print(f"Had {len(rename_tasks)} files to rename and {len(download_tasks)} files to download")
        for task in rename_tasks:
            parent = task.original_file.parent.name
            logger.print(f"Would rename '{parent}/{task.original_file.name}' -> '{parent}/{task.updated_name}'")
        for task in download_tasks:
            logger.print(f"Would download '{task.download_directory.name}/{task.file_name}'")

        return None

    with ProgressBar("Renaming files", length=len(rename_tasks), persist=True) as progress:
        for task in rename_tasks:
            parent = task.original_file.parent.name
            logger.info(f"Renaming '{parent}/{task.original_file.name}' -> '{parent}/{task.updated_name}'")

            shutil.move(task.original_file, task.original_file.with_name(task.updated_name))

            progress.advance()

    download_files(download_tasks, description="Downloading files")

    return None


class RenameFileTarget(NamedTuple):
    """ Named tuple pair of a target download URL and the associated destination file name. """

    original_file: Path
    updated_name:  str


def determine_artist(e621_connector: E621Connector, post: Post) -> str:
    """ Determine the primary artist of a given post.

    Chosen by the artist with the most posts if multiple are present.
    """
    artists = post.tags.artist_names

    if len(artists) == 1:
        return next(iter(artists))
    if counts := {
        artist: Tag.from_api(tag_info).post_count
        for artist in artists
        if (tag_info := e621_connector.get_tag(artist, Tag.Category.ARTIST))
    }:
        return max(counts, key=lambda x: counts[x], default="unknown_artist")

    return "unknown_artist"


def process_directory(
    e621_connector: E621Connector, directory: Path, rating: Post.Rating, favourites: list[Post],
) -> list[UrlFileTarget | RenameFileTarget]:
    """ Generate jobs to perform to synchronise a given directory with E621 favourites.

    Args:
        e621_connector (E621Connector): E621 connector to use when determining artist information.
        directory (Path): Local directory to consider for synchronisation.
        rating (Post.Rating): Rating to consider for the given directory.
        favourites (list[Post]): Full list of E621 favourites to sync.

    Returns:
        list[UrlFileTarget | RenameFileTarget]: List of rename and download tasks to perform for the directory.
    """
    files = [f for f in directory.iterdir() if f.is_file()]

    # Get the MD5 hash of all local files to compare to the upstream.
    with (
        ProgressBar(f"Hashing local '{rating.name.lower()}' files", length=len(files), persist=False) as progress,
        ThreadPoolExecutor(max_workers=8) as executor,
    ):
        futures = [
            executor.submit(
                hash_file,
                file_path=target,
                hash_algorithm="md5",
            ) for target in files
        ]

        file_hashes = dict(zip(files, execute_futures(futures, progress), strict=True))

    # Consider only favourites matching the rating category associated with the current folder.
    filtered_favourites = {fav.post_id: fav for fav in favourites if fav.rating == rating}
    outputs: list[UrlFileTarget | RenameFileTarget] = []

    for local_file in files:
        if local_file.stem.startswith("_"):
            continue

        post_id = local_file.stem.split("_")[0]
        if not post_id.isnumeric():
            logger.info(f"Could not determine post ID for '{directory.stem}/{local_file.stem}'")
            continue

        post_id = int(post_id)
        has_artist = len(local_file.stem.split("_")) > 1

        if not (upstream := filtered_favourites.pop(post_id, None)):
            logger.info(f"Post {post_id} either no longer favourited, or deleted from e621")
            continue

        if file_hashes[local_file] == upstream.file_info.md5:
            if not has_artist:
                logger.print(f"Post {post_id} matches upstream, but has no artist name locally")
                artist = determine_artist(e621_connector, upstream)
                outputs.append(RenameFileTarget(
                    original_file=local_file,
                    updated_name=f"{post_id}_{artist}{local_file.suffix}",
                ))
                continue
        else:
            if local_file.stat().st_size > upstream.file_info.size:
                logger.info(f"Post {post_id} mismatch with upstream, but better quality locally")
                continue

            logger.print(f"Post {post_id} exists in better quality upstream")
            artist = determine_artist(e621_connector, upstream)
            outputs.append(RenameFileTarget(
                original_file=local_file,
                updated_name=f"_lq-{local_file.name}",
            ))
            outputs.append(UrlFileTarget.create(
                url=upstream.file_info.url,
                file_name=f"{upstream.post_id}_{artist}",
                download_directory=directory,
            ))

    for favourite in filtered_favourites.values():
        logger.info(f"Post {favourite.post_id} not found locally")
        artist = determine_artist(e621_connector, favourite)
        outputs.append(UrlFileTarget.create(
            url=favourite.file_info.url,
            file_name=f"{favourite.post_id}_{artist}",
            download_directory=directory,
        ))

    return outputs
