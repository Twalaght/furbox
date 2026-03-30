""" Miscellaneous utility helper functions and constant definitions. """
import hashlib
from pathlib import Path

import requests


class Constants:
    """ Definitions of constant values. """

    USER_AGENT:                      str = "furbox (github:Twalaght/furbox)"
    GENERIC_USER_AGENT:              str = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
                                            "Gecko/20100101 Firefox/121.0")


def clean_url(url: str) -> str:
    """ Remove query parameters from a URL. """
    return url.split("?", maxsplit=1)[0]


def md5_from_url(url: str, session: requests.Session) -> str:
    """ Calculate the MD5 hash for a file from a URL. """
    md5 = hashlib.md5()  # noqa: S324
    response = session.get(url, stream=True, timeout=5)
    for chunk in response.iter_content(chunk_size=(1024 * 1024)):
        md5.update(chunk)

    return md5.hexdigest()


def md5_from_file(file_path: Path) -> str:
    """ Calculate the MD5 hash for a file on disk. """
    md5 = hashlib.md5()  # noqa: S324
    with file_path.open("rb") as f:
        while chunk := f.read(1024 * 128):
            md5.update(chunk)

    return md5.hexdigest()
