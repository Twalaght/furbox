""" Module implementing a model representation of an e621 post, and parsing functionality.

Example usage ::

    api_response = e621_connector.get_posts("vulpine")
    api_posts = [Post().from_api(post) for post in api_response]

    # TODO - Database example
"""
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from furbox.models.dataclass import DataclassParser

from typing_extensions import Self

logger = logging.getLogger(__name__)


@dataclass
class Post(DataclassParser):
    """ Dataclass representation of an e621 post. """

    @dataclass
    class FileInfo(DataclassParser):
        """ File information associated with a post. """

        width:  int = None
        height: int = None
        size:   int = None
        ext:    str = None
        md5:    str = None
        url:    str = None

    @dataclass
    class Flags(DataclassParser):
        """ Post status flags. """

        deleted:       bool = None
        pending:       bool = None
        flagged:       bool = None
        rating_locked: bool = None
        status_locked: bool = None
        note_locked:   bool = None

    @dataclass
    class Relationships(DataclassParser):
        """ Post relationship information. """

        parent_id:           int = None
        has_children:        bool = None
        has_active_children: bool = None
        children:            list[int] = field(default_factory=list)

    @dataclass
    class Score(DataclassParser):
        """ Post score values. """

        total: int = None
        up:    int = None
        down:  int = None

    @dataclass
    class Tags(DataclassParser):
        """ Post tags by category, and a combined full list. """

        general:    list[str] = field(default_factory=list)
        artist:     list[str] = field(default_factory=list)
        copyrights: list[str] = field(default_factory=list)
        character:  list[str] = field(default_factory=list)
        species:    list[str] = field(default_factory=list)
        invalid:    list[str] = field(default_factory=list)
        meta:       list[str] = field(default_factory=list)
        lore:       list[str] = field(default_factory=list)
        all_tags:   list[str] = field(default_factory=list)

    post_id:       int = None
    uploader_id:   int = None
    approver_id:   int = None
    created_at:    datetime = None
    updated_at:    datetime = None
    rating:        str = None
    description:   str = None
    fav_count:     int = None
    comment_count: int = None
    change_seq:    int = None
    duration:      float = None
    is_favorited:  bool = None
    sources:       list[str] = field(default_factory=list)
    pools:         list[int] = field(default_factory=list)
    file_info:     FileInfo = field(default_factory=FileInfo)
    flags:         Flags = field(default_factory=Flags)
    relationships: Relationships = field(default_factory=Relationships)
    score:         Score = field(default_factory=Score)
    tags:          Tags = field(default_factory=Tags)

    def from_api(self, api_response: dict[str, Any]) -> Self:
        """ Create a post from an API response input.

        Args:
            api_response (dict[str, Any]): API JSON response data for a single post.

        Returns:
            Self: Reference to the dataclass itself.
        """
        # Copy the API response such that the input data is not mangled during the remap
        data = deepcopy(api_response)

        # Rename response fields to match their corresponding dataclass fields
        data["tags"]["copyrights"] = data["tags"].pop("copyright")
        data["post_id"] = data.pop("id")
        data["file_info"] = data.pop("file")

        # Combine all unique existing tags into the "all_tags" category
        data["tags"]["all_tags"] = list(set(sum(data["tags"].values(), [])))

        # Convert ISO datetime strings to datetime objects
        data["created_at"] = self._parse_datetime(data["created_at"])
        data["updated_at"] = self._parse_datetime(data["updated_at"])

        # Explicitly drop some API data which is not parsed to a post dataclass
        data.pop("preview", None)
        data.pop("sample", None)
        data.pop("locked_tags", None)
        data.pop("has_notes", None)

        return self.parse_dict(data)

    def from_database(self, database_entry: dict[str, Any]) -> Self:
        """ TODO. """
        raise NotImplementedError

    @staticmethod
    def _parse_datetime(iso_datetime: str) -> datetime | None:
        """ Parse varied formats of ISO datetime strings to a standardised datetime object.

        Args:
            iso_datetime (str): ISO time string.

        Returns:
            datetime | None: Converted datetime object from the ISO string, \
                             or None if the input was not valid.
        """
        if not iso_datetime or len(iso_datetime) < 19:
            return None

        # Retain only the "%Y-%m-%d" and "%H:%M:%S" components of the ISO string
        clipped_iso_datetime = iso_datetime[:10] + " " + iso_datetime[11:19]
        return datetime.strptime(clipped_iso_datetime, "%Y-%m-%d %H:%M:%S")
