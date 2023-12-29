""" Module to interact with the e621 API and download from database dumps. """
import csv
import gzip
import logging
import os
from base64 import b64encode
from time import sleep
from typing import Any, Callable

from furbox.connectors.cache import Cache
from furbox.connectors.downloader import download_file
from furbox.models.e621 import Pool

from requests import session
from tqdm import tqdm

# Parsing posts database with the default field size can fail
csv.field_size_limit(int(pow(2, 20)))
logger = logging.getLogger(__name__)


class E621Connector:
    """ Search for data through the e621 API.

    Constructed with an e621 username and API key.

    Args:
        username (str): e621 username.
        api_key (str): e621 API key.
    """

    API_DELAY:           float = 1
    PAGE_LIMIT:          int = 320
    MAX_PAGE:            int = 750
    PROGRESS_BAR_FORMAT: str = "{desc}: {n_fmt} [{elapsed}]"

    base_url:            str = "https://e621.net"
    leave_progress_bars: bool = True

    def __init__(self, username: str, api_key: str) -> None:
        self.session = session()
        b64_basic_auth = b64encode(f"{username}:{api_key}".encode("ascii")).decode("ascii")
        self.session.headers.update({
            "User-Agent": "furbox (github:Twalaght/furbox)",
            "Authorization": f"Basic {b64_basic_auth}",
        })

    def get_posts(self, search: str, offset: int | None = None,
                  limit: int | None = None, desc: str = None) -> list[dict[str, Any]]:
        """ Get e621 posts matching a search query.

        Args:
            search (str): HTML quoted search query.
            offset (int | None, optional): Number of posts to skip before starting the search. \
                                           Defaults to None, where no posts will be skipped.
            limit (int | None, optional): Maximum number of posts to return. \
                                          Defaults to None, where all posts will be returned.
            desc (str, optional): Description to use in progress bar. Defaults to None, \
                                  which will use the search query string.

        Returns:
            list[dict[str, Any]]: Post JSON data matching the search query.
        """
        # For substantial offsets, skip straight to the page where results start
        page = 1
        if offset:
            page += offset // self.PAGE_LIMIT
            offset = offset % self.PAGE_LIMIT

            # Page numbers greater than 750 will return an error. In the case where the page is set above
            # this, cap the limit and increase offset accordingly. This results in unnecessary posts being
            # searched, but is required for functionality when using very high offsets
            if page > self.MAX_PAGE:
                offset += (self.PAGE_LIMIT * (page - self.MAX_PAGE))
                page = self.MAX_PAGE

            if limit:
                limit += offset

        progress_bar = tqdm(
            desc=f"Fetching posts - {desc or search}",
            position=0,
            bar_format=self.PROGRESS_BAR_FORMAT,
            leave=self.leave_progress_bars,
        )

        posts = []
        while True:
            # Setting page to "b{post_id}" will show posts before the given ID. This is done for accurate
            # pagination, as posts will move between pages if any are created or deleted between requests
            page = f"b{posts[-1]['id']}" if posts else page

            # Request each page of posts through the API
            search_url = f"{self.base_url}/posts.json?limit={self.PAGE_LIMIT}&tags={search}&page={page}"
            response = self.session.get(search_url)
            response.raise_for_status()

            response_posts = response.json()["posts"]
            posts.extend(response_posts)
            progress_bar.update(len(response_posts))

            # Break if a partial response is received, as it must be the final page
            if len(response_posts) < self.PAGE_LIMIT:
                break

            # Break if a limit was provided and the number of posts exceeds it
            if limit and len(posts) >= limit:
                break

            sleep(self.API_DELAY)

        progress_bar.close()
        return posts[offset:limit]

    def get_pool(self, pool_id: int | str) -> dict[str, Any]:
        """ Get an e621 pool by ID.

        Args:
            pool_id (int | str): Pool ID number.

        Returns:
            dict[str, Any]: Pool JSON data.
        """
        search_url = f"{self.base_url}/pools/{str(pool_id)}.json"
        response = self.session.get(search_url)
        response.raise_for_status()
        return response.json()


class E621DbConnector:
    """ Connector to download and parse information from the e621 database dumps.

    Optionally constructed with a specific cache directory to download database dumps to.

    Args:
        cache_dir (str | os.PathLike, optional): Cache directory to use when reading and writing database dumps. \
                                                 Defaults to None, where a default cache location will be used.
    """

    base_url: str = "https://e621.net"

    def __init__(self, cache_dir: str | os.PathLike = None) -> None:
        self.session = session()
        self.cache = Cache(cache_dir)

    def _get_database(self, database_name: str, data_model: type,
                      filter_condition: Callable[[type], bool] = None) -> list[type]:
        """ Get dataclass objects from a database dump.

        Args:
            database_name (str): Name of the database type to download.
            data_model (type): Dataclass type to parse database entries to.
            filter_condition (Callable[[type], bool], optional): \
                Filter function to apply on dataclasses to determine if they will be returned. \
                Defaults to None, where all dataclass objects will be returned.

        Returns:
            list[type]: List of dataclass objects.
        """
        file_path = self.cache.resolve_path(f"{database_name}.gz")
        if not self.cache.check(file_path):
            response = self.session.get(f"{self.base_url}/db_export/")
            response.raise_for_status()

            all_database_indexes = response.text.splitlines()
            latest_database = next(line for line in reversed(all_database_indexes) if database_name in line)
            latest_database_name = latest_database.split('"')[1]

            download_file(
                url=f"{self.base_url}/db_export/{latest_database_name}",
                file_path=file_path,
                desc=f"Fetching database {latest_database_name}",
                leave_progress_bar=True,
            )

        database_entries = []
        with gzip.open(file_path, "rt") as f:
            for row in csv.DictReader(f):
                entry = data_model().from_database(row)
                if not filter_condition or filter_condition(entry):
                    database_entries.append(entry)

        return database_entries

    def get_pools(self, filter_condition: Callable[[Pool], bool] = None) -> list[Pool]:
        """ Get pool dataclass objects from a database dump.

        Args:
            filter_condition (Callable[[Pool], bool], optional): \
                Filter function to apply on pool dataclasses to determine if it will be returned. \
                Defaults to None, where all pools will be returned.

        Returns:
            list[Pool]: List of pool dataclasses.
        """
        return self._get_database("pools", Pool, filter_condition)
