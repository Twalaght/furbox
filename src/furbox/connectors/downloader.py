""" Module to download files and helper functions related to download operations. """
import logging
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple, Self

import backoff
import requests

from furbox.helpers.utils import clean_url
from furbox.utils.progress_bar import ProgressBar, ProgressBarStyle

logger = logging.getLogger(__name__)


class UrlFileTarget(NamedTuple):
    """ Named tuple pair of a target download URL and the associated destination file name. """

    url:                str
    file_name:          str
    download_directory: Path
    extension:          str | None

    @property
    def output_path(self) -> Path:
        """ Sanitise file name, extension, and download directory into a path. """
        file_name_with_extension = self.file_name + (f".{self.extension}" if self.extension else "")
        return self.download_directory / file_name_with_extension

    @classmethod
    def create(cls, url: str, file_name: str, download_directory: Path, extension: str | None = None) -> Self:
        """ Parse a URL and file name into a clean URL and file path named tuple.

        Args:
            url (str): URL of file to download.
            file_name (str): Name of file to download.
            download_directory (Path): Directory to download file targets to.
            extension (str | None, optional): \
                Specify the extension to download the file as. Defaults to None, \
                where extension is inferred by file preferentially, then URL.

        Returns:
            Self: Created UrlFileTarget instance.
        """
        # Strip query parameters from the input URL.
        url = clean_url(url)

        # Determine the extension to download to, sourced preferentially from:
        # 1. The supplied extension argument.
        # 2. Extension inferred from the file name.
        # 3. Extension inferred from the stripped URL.
        # If nothing is found, file is downloaded without any extension.
        extensions = (
            extension,
            file_name.rsplit(".", maxsplit=1)[-1] if "." in file_name else None,
            url.split(".")[-1] if "." in url else None,
        )

        return cls(
            url=url,
            file_name=file_name,
            download_directory=Path(download_directory),
            extension=next((ext for ext in extensions if ext), None),
        )


def get_numbered_file_names(
    download_urls: list[str], download_directory: Path, name: str, offset: int = 0, zero_pad: int | None = None,
) -> list[UrlFileTarget]:
    """ Generate download file targets names numbered incrementally.

    Args:
        download_urls (list[str]): List of URLs to generate file targets with numbered names for.
        download_directory (Path): Directory to download file targets to.
        name (str): Base name for all files.
        offset (int, optional): Offset to all file numbers. Defaults to 0.
        zero_pad (int | None, optional): Use a fixed length zero padding for file names if provided. \
                                         Defaults to None.

    Returns:
        list[UrlFileTarget]: List of generated download targets.
    """
    # Calculate the amount of zero padding to apply, which will be at least 2 unless a custom pad is provided.
    num_urls = len(download_urls)
    page_len = len(str(offset + num_urls + 1))
    zero_len = zero_pad or max(2, page_len)
    file_names = [f"{name} {str(num).zfill(zero_len)}" for num in range(offset + 1, offset + num_urls + 1)]

    return [
        UrlFileTarget.create(url=url, file_name=file_name, download_directory=download_directory)
        for url, file_name in zip(download_urls, file_names, strict=True)
    ]


def download_file(url: str, file_path: Path, description: str, leave_progress_bar: bool) -> None:
    """ Download a file from a URL with a progress bar.

    Args:
        url (str): URL to download the file from.
        file_path (Path): File path to save the downloaded file to.
        description (str): Description to use in progress bar.
        leave_progress_bar (bool): Leave the progress bar display after the download has finished.
    """
    # Download the file as a stream, such that progress can be accurately displayed.
    response = requests.get(url, stream=True, timeout=5)
    response.raise_for_status()

    # Create the parent directory if required.
    parent_path = file_path.resolve().parent
    parent_path.mkdir(parents=True, exist_ok=True)

    # Download the file to a temporary file path.
    tmp_file_path = parent_path / f"_{file_path.name}"
    with (
        Path(tmp_file_path).open("wb") as f,
        ProgressBar(
            description=description,
            length=int(response.headers.get("content-length", 0)),
            style=ProgressBarStyle.FILE,
            persist=leave_progress_bar,
        ) as progress,
    ):
        for chunk in response.iter_content(chunk_size=(1024 * 128)):
            progress.advance(len(chunk))
            f.write(chunk)

    # Once downloaded, move the temporarily file to the desired file path.
    shutil.move(
        src=tmp_file_path,
        dst=file_path,
    )


def parallel_download(args: tuple[str, Path]) -> None:
    """ Download multiple files in parallel.

    Args:
        args (tuple[str, Path]): Positional arguments to pass to `download()`.
    """
    @backoff.on_exception(backoff.expo, exception=requests.HTTPError, max_tries=3)
    def download(url: str, file_path: Path, progress_bar: ProgressBar | None = None) -> None:
        """ Download a single file to disk.

        Args:
            url (str): URL to download the file from.
            file_path (Path): File path to save the downloaded file to.
            progress_bar (ProgressBar | None): Progress bar to increment on successful download, if provided.
        """
        # Create the parent directory if required.
        parent_path = file_path.resolve().parent
        parent_path.mkdir(parents=True, exist_ok=True)

        if file_path.exists() and file_path.is_file():
            while True:
                backup_path = parent_path / f"_backup_{uuid.uuid4()}{file_path.name}"
                if not backup_path.exists():
                    logger.warning(f"File '{file_path}' already exists, moving it to '{backup_path}'")
                    file_path.rename(backup_path)

        # Download the file to a temporary file path.
        tmp_file_path = file_path.resolve().parent / f"_{file_path.name}"
        with Path(tmp_file_path).open("wb") as f:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            f.write(response.content)

        # Once downloaded, move the temporarily file to the desired file path.
        tmp_file_path.rename(file_path)

        if progress_bar:
            progress_bar.advance()

    # Call the inner function with supplied tuple of arguments.
    download(*args)


def download_files(file_targets: list[UrlFileTarget], description: str, threads: int = 8) -> None:
    """ Download a list of file targets.

    Args:
        file_targets (list[UrlFileTarget]): List of download targets, pairing download URLs with file names.
        description (str): Description to use in progress bar.
        threads (int): Number of threads to use when downloading. Defaults to 8.
    """
    with (
        ProgressBar(description, length=len(file_targets)) as progress,
        ThreadPoolExecutor(max_workers=threads) as executor,
    ):
        download_args = [(target.url, target.output_path, progress) for target in file_targets]
        executor.map(parallel_download, download_args)
