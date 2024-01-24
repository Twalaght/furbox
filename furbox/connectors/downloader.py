""" Module to download files and helper functions related to download operations. """
import logging
import os
from multiprocessing import Pool, cpu_count
from pathlib import Path
from urllib.request import URLopener

import requests
from tqdm import tqdm

from furbox.helpers.utils import Constants, clean_url

logger = logging.getLogger(__name__)


def get_numbered_file_names(name: str, length: int, offset: int = 0, zero_pad: int = None) -> list[str]:
    """ Generate files names numbered incrementally.

    Args:
        name (str): Base name for all files.
        length (int): Number of file names to generate.
        offset (int, optional): Offset to all file numbers. Defaults to 0.
        zero_pad (int, optional): Use a fixed length zero padding for file names if provided. \
                                  Defaults to None.

    Returns:
        list[str]: List of generated file names.
    """
    # Calculate the standard zero padding, which will be at least 2 unless a custom pad is provided
    page_len = len(str(offset + length + 1))
    zero_len = zero_pad or max(2, page_len)
    return [f"{name} {str(num).zfill(zero_len)}" for num in range(offset + 1, offset + length + 1)]


def download_file(url: str, file_path: str | os.PathLike, desc: str, leave_progress_bar: bool) -> None:
    """ Download a file from a URL with a progress bar.

    Args:
        url (str): URL to download the file from.
        file_path (str | os.PathLike): File path to save the downloaded file to.
        desc (str): Description to use in progress bar.
        leave_progress_bar (bool): Leave the progress bar display after the download has finished.
    """
    # Download the file as a stream, such that progress can be accurately displayed
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(file_path, "wb") as f:
        with tqdm(
            desc=desc,
            position=0,
            total=int(response.headers.get("content-length", 0)),
            unit="b",
            unit_scale=True,
            unit_divisor=1024,
            bar_format=Constants.PROGRESS_BAR_FORMAT,
            leave=leave_progress_bar,
        ) as progress:
            for chunk in response.iter_content(chunk_size=(1024 * 128)):
                progress.update(len(chunk))
                f.write(chunk)


def parallel_download(args: tuple[str, str | os.PathLike]) -> None:
    """ Download multiple files in parallel.

    Args:
        args (tuple[str, str  |  os.PathLike]): Positional arguments to pass to `download()`.
    """
    def download(url: str, file_path: str | os.PathLike) -> None:
        """ Download a single file to disk.

        Args:
            url (str): URL to download the file from.
            file_path (str | os.PathLike): File path to save the downloaded file to.
        """
        URLopener().retrieve(url, file_path)

    download(*args)


def download_files(url_name_pairs: list[tuple[str, str]], download_dir: str | os.PathLike, desc: str) -> None:
    """ Download multiple files from a list of URL name pairs.

    Args:
        url_name_pairs (list[tuple[str, str]]): List of tuples containing the URL to download from, \
                                                and the file name to write to.
        download_dir (str | os.PathLike): Directory to download all files to.
        desc (str): Description to use in progress bar.
    """
    # Strip HTTP query string params from the URL and format file names to include extension
    download_args = []
    for url, name in url_name_pairs:
        cleaned_url = clean_url(url)
        download_args.append((cleaned_url, Path(download_dir) / f"{name}.{cleaned_url.split('.')[-1]}"))

    with tqdm(
        desc=desc,
        position=0,
        total=len(url_name_pairs),
        bar_format=Constants.PROGRESS_BAR_FORMAT,
        leave=True,
    ) as progress_bar:
        # Use a multiprocessing pool to download files in parallel
        for _ in Pool(cpu_count()).imap(parallel_download, download_args, chunksize=1):
            progress_bar.update()
