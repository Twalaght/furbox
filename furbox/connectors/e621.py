""" Module to interact and download through the e621 API. """
import logging
from base64 import b64encode
from time import sleep
from typing import Any

from requests import session
from tqdm import tqdm

logger = logging.getLogger(__name__)


class E621Connector:
    """ Construct an E621Connector object with a username and API key.

    Args:
        username (str): E621 username.
        api_key (str): E621 API key.
    """

    API_DELAY:  float = 1
    PAGE_LIMIT: int = 320
    MAX_PAGE:   int = 750

    base_url:            str = "https://e621.net"
    leave_progress_bars: bool = True
    progress_bar_format: str = "{desc}: {n_fmt} [{elapsed}]"

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

        progress_bar = tqdm(desc=f"Fetching posts - {desc or search}",
                            position=0,
                            bar_format=self.progress_bar_format,
                            leave=self.leave_progress_bars)

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
    """ TODO. """

    def __init__(self) -> None:
        raise NotImplementedError
