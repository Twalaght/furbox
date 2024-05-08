""" Module to interact with the e621 API and download from database dumps. """
import csv
import gzip
import logging
import os
from base64 import b64encode
from enum import Enum
from time import sleep
from typing import Any, Callable

import requests

from furbox.connectors.cache import Cache
from furbox.connectors.downloader import download_file
from furbox.helpers.utils import Constants
from furbox.models.e621 import Pool
from furbox.utils.progress_bar import progress

logger = logging.getLogger(__name__)


class E621Connector:
    """ Connector class to interact with the e621 API.

    Constructed with an e621 username and API key, and optionally a custom backend URL. Request
    authentication is provided with basic auth. As such, the username and API key are related and
    cannot be modified independently.

    Optionally, a `backend_url` argument may be provided to access a different backend, such as e926.
    A username and API key pair generated for e621 will be valid when accessing e926, and vice versa.
    All mentions of e621 are interchangeable with e926 when using it as the backend URL.

    Args:
        username (str): e621 username.
        api_key (str): e621 API key generated for the given value of `username`.
        backend_url (BackendUrl, optional): Base URL to use for all requests. \
                                            Valid options defined in `E621Connector.BackendUrl`. \
                                            Defaults to `E621Connector.BackendUrl.E621`.
    """

    API_DELAY:           float = 1
    PAGE_LIMIT:          int = 320
    MAX_PAGE:            int = 750

    leave_progress_bars: bool = True

    class BackendUrl(Enum):
        """ Valid base URL definitions for the connector. """

        E621 = "https://e621.net"
        E926 = "https://e926.net"

    def __init__(self, username: str, api_key: str, backend_url: BackendUrl = BackendUrl.E621) -> None:
        self.session = requests.session()
        b64_basic_auth = b64encode(f"{username}:{api_key}".encode("ascii")).decode("ascii")
        self.session.headers.update({
            "User-Agent": Constants.USER_AGENT,
            "Authorization": f"Basic {b64_basic_auth}",
        })

        self.base_url = backend_url.value

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
                                  where the search query string will be used.

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

        posts_progress_bar = progress.add_task(
            description=f"Fetching posts - {desc or search}",
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
            progress.advance(posts_progress_bar, len(response_posts))

            # Break if a partial response is received, as it must be the final page
            if len(response_posts) < self.PAGE_LIMIT:
                break

            # Break if a limit was provided and the number of posts exceeds it
            if limit and len(posts) >= limit:
                break

            sleep(self.API_DELAY)

        progress.finish(posts_progress_bar)
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

        sleep(self.API_DELAY)

        return response.json()


class E621DbConnector:
    """ Connector to download and parse information from the e621 database dumps.

    Optionally constructed with a specific cache directory to download database dumps to.
    Note that database dumps must be fetched from e621, as e926 does not provide equivalent data.

    Args:
        cache_dir (str | os.PathLike, optional): \
            Cache directory to use when reading and writing database dumps. \
            Defaults to None, where a default cache location will be used.
    """

    BASE_URL: str = "https://e621.net"

    class DatabaseType(Enum):
        """ List of valid database types available from the e621 exports.

        TODO - Not an exhaustive list, other types not yet implemented.
        """

        post = "posts"
        pool = "pools"

    def __init__(self, cache_dir: str | os.PathLike = None) -> None:
        self.session = requests.session()
        self.cache = Cache(cache_dir)

    def _get_database(self, database_name: str) -> os.PathLike:
        """ Download a database dump if no valid cached file exists.

        Args:
            database_name (str): Name of database to download. \
                                 Valid options defined in `E621DbConnector.DatabaseType`.

        Returns:
            os.PathLike: Path to the database file on disk.
        """
        file_path = self.cache.resolve_path(f"{database_name}.gz")
        if not self.cache.check(file_path):
            response = self.session.get(f"{self.BASE_URL}/db_export/")
            response.raise_for_status()

            all_database_indexes = response.text.splitlines()
            latest_database = next(line for line in reversed(all_database_indexes) if database_name in line)
            latest_database_name = latest_database.split('"')[1]

            download_file(
                url=f"{self.BASE_URL}/db_export/{latest_database_name}",
                file_path=file_path,
                description=f"Fetching database {latest_database_name}",
                leave_progress_bar=True,
            )

        return file_path

    def _parse_database(self, file_path: os.PathLike, data_model: type,
                        filter_condition: Callable[[type], bool] = None) -> list[type]:
        """ Parse a database file into dataclass objects, optionally subject to a filter condition.

        Args:
            file_path (os.PathLike): Path to the database file on disk.
            data_model (type): Dataclass type to parse database rows into.
            filter_condition (Callable[[type], bool], optional): \
                Filter function to apply on dataclasses to determine if they will be returned. \
                Defaults to None, where all dataclass objects will be returned.

        Returns:
            list[type]: List of dataclass objects parsed from the database.
        """
        database_entries = []
        with gzip.open(file_path, "rt") as f:
            # Specifically when parsing the "posts" database, using the default CSV field size will throw
            # an error. The default size is 2^17, and increasing this to 2^20 allows the CSV to be parsed
            csv.field_size_limit(int(pow(2, 20)))

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
        file_path = self._get_database(self.DatabaseType.pool.value)
        return self._parse_database(file_path, Pool, filter_condition)
