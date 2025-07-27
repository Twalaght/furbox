""" Module to handle caching data based on file name and modification time.

Example usage of Cache: ::

    cache = Cache()
    file_path = self.cache.resolve_path("posts_latest.csv")

    if not self.cache.check(file_path):
        download_file("db_export/posts.csv", file_path)

    with open(file_path, "r") as f:
        post_data = f.read()
"""
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class Cache:
    """ Construct a cache, optionally in a specific directory and with a custom expiry length.

    If no base directory is specified, `$XDG_CACHE_HOME` will be used if set, otherwise `$HOME/.cache`.
    Values provided for `expiry_hours` and `expiry_minutes` are additive, and will not override each other.

    Args:
        cache_dir (str | os.PathLike, optional): Custom directory to use as the base cache location. \
                                                 Defaults to None.
        expiry_hours (int, optional): Hours a cache file is valid for. Defaults to 24.
        expiry_minutes (int, optional): Minutes a cache file is valid for. Defaults to 0.

    Raises:
        ValueError: Provided cache path was not a directory, or does not exist.
    """

    def __init__(self, cache_dir: str | os.PathLike = None, expiry_hours: int = 24, expiry_minutes: int = 0) -> None:
        if not cache_dir and not (cache_dir := os.getenv("XDG_CACHE_HOME")):
            cache_dir = Path.home() / ".cache"

        self.cache_dir = Path(cache_dir) / "furbox"
        self.expiry_minutes = expiry_minutes + (expiry_hours * 60)

        if not self.cache_dir.exists():
            logger.info(f"Cache directory '{cache_dir}' does not exist, creating it")
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        if not self.cache_dir.is_dir():
            raise ValueError(f"Cache directory '{cache_dir}' exists but is not a directory")

    def check(self, file_path: str | os.PathLike) -> bool:
        """ Return True if the file path has a current valid cache entry, False otherwise. """
        if not file_path.exists():
            return False

        cache_expiry_time = timedelta(minutes=self.expiry_minutes)
        last_modified = datetime.fromtimestamp(file_path.lstat().st_mtime)
        return not (datetime.now() - last_modified) > cache_expiry_time and self.expiry_minutes >= 0

    def resolve_path(self, file_path: str | os.PathLike) -> os.PathLike:
        """ Resolve a file path relative to the cache directory. """
        return self.cache_dir / file_path
