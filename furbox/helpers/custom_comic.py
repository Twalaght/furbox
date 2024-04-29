""" Module to provide functionality for comic updates on custom web comics. """
import logging
import os
from pathlib import Path

from attrs import define, field
from bs4 import BeautifulSoup
from bs4.element import Tag
import requests
from tqdm import tqdm

from furbox.connectors.downloader import download_files, get_numbered_file_names
from furbox.helpers.utils import Constants, clean_url, md5_from_file, md5_from_url
from furbox.models.dataclass import DataclassParser

logger = logging.getLogger(__name__)


@define
class CustomComic(DataclassParser):
    """ Dataclass representation of a custom web comic. """

    @define
    class Instruction(DataclassParser):
        """ Single instruction to apply on a BeautifulSoup to extract data. """

        html_type: str | None = None
        text:      str | None = None
        attrs:     dict[str, str] = field(factory=dict)
        index:     int | None = 0

    name: str | None = None
    url:  str | None = None

    # Local directory to download files to, relative to the base comics directory
    dir_name: str | os.PathLike | None = None
    # Update the local files if True, only check for new items without downloading if False
    update:   bool = True

    # List of instructions to extract a link to the latest page,
    # images on a page, and the previous page respectively
    latest:   list[Instruction] = field(factory=list)
    images:   list[Instruction] = field(factory=list)
    backlink: list[Instruction] = field(factory=list)


def custom_comic_update(custom_comic: CustomComic, comic_path: str | os.PathLike) -> None:
    """ Check for new pages and download new items for a web comic.

    Args:
        custom_comic (CustomComic): Dataclass with local archive information and parsing instructions.
        comic_path (str | os.PathLike): Base directory for comic archives.
    """
    def extract_from_soup(soup: BeautifulSoup, instructions: list[CustomComic.Instruction]) -> Tag | list[Tag]:
        """ Extract a single tag, or a set of tags from a BeautifulSoup object.

        Args:
            soup (BeautifulSoup): BeautifulSoup object to find tags from.
            instructions (list[CustomComic.Instruction]): \
                List of instructions to perform on the input soup to extract tags.

        Returns:
            Tag | list[Tag]: Tag or list of tags extracted from the input soup.
        """
        tags = soup
        for instruction in instructions:
            tags = tags.find_all(instruction.html_type, attrs=instruction.attrs)

            # If text was provided, search for the text in the tag list
            if text := instruction.text:
                tags = [tag for tag in tags if text in tag.text]

            # If an index was provided, return the tag matching it
            if instruction.index is not None:
                tags = tags[instruction.index]

        return tags

    # Set up a session object with a standard browser user agent, and fetch the initial page
    session = requests.session()
    session.headers = {"User-Agent": Constants.USER_AGENT}
    page = custom_comic.url

    # If custom instructions to get to the latest page were provided, extract using them
    if custom_comic.latest:
        response = session.get(custom_comic.url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        page = extract_from_soup(soup, custom_comic.latest)["href"]

    local_comic_dir = Path(comic_path) / (custom_comic.dir_name or custom_comic.name)
    if not local_comic_dir.exists():
        print(f"Folder '{local_comic_dir}' does not exist, creating it")
        local_comic_dir.mkdir(parents=True, exist_ok=True)

    # Find the alphabetical last file in the directory if it exists
    # Use this files hash as the stopping point when searching backwards through pages,
    # and use it's associated number as a file naming offset when writing pages to disk
    target_hash = None
    file_name_offset = 0
    if local_files := [f for f in local_comic_dir.iterdir() if f.is_file()]:
        last_file = local_files[-1]
        target_hash = md5_from_file(last_file)
        try:
            file_name_offset = int(last_file.stem.split(" ")[-1])
        except Exception:
            logger.error(f"File '{last_file}' must follow the format 'series_name page_number.ext'")

    images = []
    with tqdm(
        desc=f"Searching pages - {custom_comic.name}",
        position=0,
        bar_format=Constants.UNKNOWN_LEN_PROGRESS_BAR_FORMAT,
        leave=True,
    ) as progress:
        while True:
            response = session.get(page)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            image_urls = [tag["src"] for tag in extract_from_soup(soup, custom_comic.images)]
            image_urls = [clean_url(url) for url in image_urls]

            # If any of the image hashes match the local file, all new pages have been found
            if target_hash in [md5_from_url(url, session) for url in image_urls]:
                break

            images = image_urls + images
            progress.update(len(image_urls))

            # Find the backlink to the previous page if it exists
            try:
                page = extract_from_soup(soup, custom_comic.backlink)["href"]
            except Exception:
                break

    if not images:
        print(f"\033[32m{custom_comic.name} is up to date\033[0m")
        return

    print(f"{custom_comic.name} has {len(images)} new pages")
    download_files(
        url_name_pairs=list(zip(
            images,
            get_numbered_file_names(
                name=custom_comic.name,
                length=len(images),
                offset=file_name_offset,
                zero_pad=4,
            ),
        )),
        download_dir=local_comic_dir,
        description=f"Downloading {custom_comic.name}",
    )
