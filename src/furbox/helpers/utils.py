""" Miscellaneous utility helper functions and constant definitions. """
import hashlib
from concurrent.futures import Future
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

from furbox.utils.progress_bar import ProgressBar


class Constants:
    """ Definitions of constant values. """

    USER_AGENT:         str = "furbox (github:Twalaght/furbox)"
    GENERIC_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:152.0) Gecko/20100101 Firefox/152.0"


def execute_futures[T](futures: list[Future[T]], progress_bar: ProgressBar | None = None) -> list[T]:
    """ Execute and return a list of futures, incrementing a progress bar if one was provided. """
    def result_and_advance(future: Future[T], progress_bar: ProgressBar) -> T:
        """ Wrap a future to get the result and increment a progress bar. """
        result = future.result()
        progress_bar.advance()
        return result

    return [
        result_and_advance(future, progress_bar) if progress_bar else future.result()
        for future in futures
    ]


def clean_url(url: str) -> str:
    """ Remove all query parameters from a URL. """
    return urljoin(url, urlparse(url).path)


def md5_from_url(url: str, session: requests.Session) -> str:
    """ Calculate the MD5 hash for a file from a URL. """
    md5 = hashlib.md5()  # noqa: S324
    response = session.get(url, stream=True, timeout=5)
    for chunk in response.iter_content(chunk_size=(1024 * 1024)):
        md5.update(chunk)

    return md5.hexdigest()


def hash_file(file_path: Path, hash_algorithm: str = "md5") -> str:
    """ Calculate the hash digest for a file on disk.

    Args:
        file_path (Path): File to calculate hash for.
        hash_algorithm (str, optional): Hashing algorithm to use. Defaults to "md5".

    Returns:
        str: Hash digest of the input file.
    """
    with file_path.open("rb") as f:
        return hashlib.file_digest(f, hash_algorithm).hexdigest()
