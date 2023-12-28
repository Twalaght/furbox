""" Module to download files and helper functions related to download operations. """
import logging
import os
from multiprocessing import Pool, cpu_count
from pathlib import Path
from urllib.request import URLopener
from tqdm import tqdm

logger = logging.getLogger(__name__)


def get_numbered_file_names(name: str, length: int, offset: int = 0) -> None:
    """ TODO. """
    zero_len = len(str(offset + length + 1))
    return [f"{name} {str(num).zfill(zero_len)}" for num in range(offset + 1, offset + length + 1)]


# Download files from a download argument tuple
def parallel_download(args: tuple[str, str | os.PathLike]) -> None:
    """ TODO. """
    def download(url: str, path: str | os.PathLike) -> None:
        """ TODO. """
        URLopener().retrieve(url, path)

    download(*args)


def download_files(desc: str, file_urls: list[str], file_names: list[str], download_dir: str | os.PathLike) -> None:
    """ TODO. """
    if len(file_urls) != len(file_names):
        # TODO - This shouldn't be able to happen normally
        raise RuntimeError

    download_args = []
    for url, name in zip(file_urls, file_names):
        ext = url.split(".")[-1]
        download_args.append(
            (url, Path(download_dir) / f"{name}.{ext}"),
        )

    # TODO - Custom bar format
    progress_bar = tqdm(
        desc=desc,
        position=0,
        leave=True,
        total=len(file_urls),
    )

    # Download files in parallel
    for _ in Pool(cpu_count()).imap(parallel_download, download_args, chunksize=1):
        progress_bar.update()
