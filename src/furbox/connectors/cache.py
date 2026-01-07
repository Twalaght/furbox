""" Module to handle caching data based on file name and modification time.

Example usage of Cache: ::

    cache = Cache()
    file_path = cache.resolve_path("posts_latest.csv")
    if not cache.check("posts_latest.csv"):
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

    If no base directory is specified, `$XDG_CACHE_HOME/furbox` will be used if set, otherwise `$HOME/.cache/furbox`.

    Args:
        cache_dir (str | Path | None, optional): Custom directory to use as the base cache location. \
                                                 Defaults to None.
        expiry_hours (int, optional): Hours a cache file is valid for. Defaults to 24.
        expiry_minutes (int, optional): Minutes a cache file is valid for. Defaults to 0.

    Raises:
        ValueError: Provided cache path was not a directory, or does not exist.
    """

    def __init__(self, cache_dir: str | Path | None = None, expiry_hours: int = 24, expiry_minutes: int = 0) -> None:
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            cache_dir = os.getenv("XDG_CACHE_HOME", Path.home() / ".cache")
            self.cache_dir = Path(cache_dir) / "furbox"

        self.expiry_minutes = expiry_minutes + (expiry_hours * 60)

        if not self.cache_dir.exists():
            logger.info(f"Cache directory '{cache_dir}' does not exist, creating it")
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        if not self.cache_dir.is_dir():
            raise ValueError(f"Cache directory '{cache_dir}' exists but is not a directory")

    def check(self, file_path: str | Path) -> bool:
        """ Return True if the file path has a current valid cache entry, False otherwise. """
        file_path = Path(file_path)
        if not file_path.is_relative_to(self.cache_dir):
            file_path = self.resolve_path(file_path)

        if not file_path.exists():
            return False

        cache_expiry_time = timedelta(minutes=self.expiry_minutes)
        last_modified = datetime.fromtimestamp(file_path.lstat().st_mtime, tz=None)
        return not (datetime.now(tz=None) - last_modified) > cache_expiry_time and self.expiry_minutes >= 0

    def resolve_path(self, file_path: str | Path) -> Path:
        """ Resolve a file path relative to the cache directory. """
        return self.cache_dir / file_path
