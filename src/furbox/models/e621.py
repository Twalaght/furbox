""" Module implementing a model representation of e621 posts and pools, with parsing functionality.

Example usage for a post: ::

    # From API response
    api_response = e621_connector.get_posts("vulpine")
    api_posts = [Post().from_api(post) for post in api_response]

    # From database dump
    with open("posts.csv") as f:
        database_posts = [
            Post().from_database(row)
            for row in csv.DictReader(f)
        ]
"""
import itertools
import logging
from copy import deepcopy
from datetime import datetime
from typing import Any, Self

from attrs import define, field

from furbox.models.dataclass import DataclassParser

logger = logging.getLogger(__name__)


class E621Model(DataclassParser):
    """ Standardised parsing behaviour for E621 models. """

    @staticmethod
    def char_to_bool(char: str) -> bool:
        """ Convert a single character input to the corresponding boolean. """
        return bool(char == "t")

    @staticmethod
    def parse_datetime(iso_datetime: str) -> datetime | None:
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

    @staticmethod
    def source_url_from_hash(md5_hash: str, extension: str) -> str:
        """ Get a post source url from an MD5 hash.

        Args:
            md5_hash (str): MD5 hash of the post.
            extension (str): File extension of the post.

        Returns:
            str: Full quality source url corresponding to the input hash.
        """
        # As e621 is a superset of e926, e621 can be used as the base url for sources in all instances
        base_url = "https://static1.e621.net/data"
        return f"{base_url}/{md5_hash[:2]}/{md5_hash[2:4]}/{md5_hash}.{extension}"


@define
class Post(E621Model):
    """ Dataclass representation of an e621 post. """

    @define
    class FileInfo(DataclassParser):
        """ File information associated with a post. """

        width:  int | None = None
        height: int | None = None
        size:   int | None = None
        ext:    str | None = None
        md5:    str | None = None
        url:    str | None = None

    @define
    class Flags(DataclassParser):
        """ Post status flags. """

        deleted:       bool | None = None
        pending:       bool | None = None
        flagged:       bool | None = None
        rating_locked: bool | None = None
        status_locked: bool | None = None
        note_locked:   bool | None = None

    @define
    class Relationships(DataclassParser):
        """ Post relationship information. """

        parent_id:           int | None = None
        has_children:        bool | None = None
        has_active_children: bool | None = None
        children:            list[int] = field(factory=list)

    @define
    class Score(DataclassParser):
        """ Post score values. """

        total: int | None = None
        up:    int | None = None
        down:  int | None = None

    @define
    class Tags(DataclassParser):
        """ Post tags by category, and a combined full list. """

        general:    list[str] = field(factory=list)
        artist:     list[str] = field(factory=list)
        copyrights: list[str] = field(factory=list)
        character:  list[str] = field(factory=list)
        species:    list[str] = field(factory=list)
        invalid:    list[str] = field(factory=list)
        meta:       list[str] = field(factory=list)
        lore:       list[str] = field(factory=list)
        all_tags:   list[str] = field(factory=list)

    post_id:       int | None = None
    uploader_id:   int | None = None
    approver_id:   int | None = None
    created_at:    datetime | None = None
    updated_at:    datetime | None = None
    rating:        str | None = None
    description:   str | None = None
    fav_count:     int | None = None
    comment_count: int | None = None
    change_seq:    int | None = None
    duration:      float | None = None
    is_favorited:  bool | None = None
    sources:       list[str] = field(factory=list)
    pools:         list[int] = field(factory=list)
    file_info:     FileInfo = field(factory=FileInfo)
    flags:         Flags = field(factory=Flags)
    relationships: Relationships = field(factory=Relationships)
    score:         Score = field(factory=Score)
    tags:          Tags = field(factory=Tags)

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
        data["tags"]["all_tags"] = list(set(itertools.chain.from_iterable(data["tags"].values())))

        # Convert ISO datetime strings to datetime objects
        data["created_at"] = self.parse_datetime(data["created_at"])
        data["updated_at"] = self.parse_datetime(data["updated_at"])

        # Explicitly drop some API data which is not parsed to a post dataclass
        data.pop("preview", None)
        data.pop("sample", None)
        data.pop("locked_tags", None)
        data.pop("has_notes", None)

        return self.parse_dict(data)

    def from_database(self, database_entry: dict[str, str]) -> Self:
        """ Create a post from a database CSV row input.

        Args:
            database_entry (dict[str, str]): Database CSV entry for a single post.

        Returns:
            Self: Reference to the dataclass itself.
        """
        file_info = {
            "width":  int(database_entry["image_width"]),
            "height": int(database_entry["image_height"]),
            "size":   int(database_entry["file_size"]),
            "ext":    database_entry["file_ext"],
            "md5":    database_entry["md5"],
            "url":    self.source_url_from_hash(database_entry["md5"], database_entry["file_ext"]),
        }

        flags = {
            "deleted":       self.char_to_bool(database_entry["is_deleted"]),
            "pending":       self.char_to_bool(database_entry["is_pending"]),
            "flagged":       self.char_to_bool(database_entry["is_flagged"]),
            "rating_locked": self.char_to_bool(database_entry["is_rating_locked"]),
            "status_locked": self.char_to_bool(database_entry["is_status_locked"]),
            "note_locked":   self.char_to_bool(database_entry["is_note_locked"]),
        }

        relationships = {
            "parent_id": int(parent_id) if (parent_id := database_entry["parent_id"]) else None,
        }

        score = {
            "total": int(database_entry["score"]),
            "up":    int(database_entry["up_score"]),
            "down":  int(database_entry["down_score"]),
        }

        all_tags = []
        for tag_type in ["tag_string", "locked_tags"]:
            if tag_string := database_entry[tag_type]:
                all_tags.extend(tag_string.split())

        return self.parse_dict({
            "post_id":       int(database_entry["id"]),
            "uploader_id":   int(database_entry["uploader_id"]),
            "approver_id":   int(approver_id) if (approver_id := database_entry.get("approver_id")) else None,
            "created_at":    self.parse_datetime(database_entry["created_at"]),
            "updated_at":    self.parse_datetime(database_entry["updated_at"]),
            "rating":        database_entry["rating"],
            "description":   database_entry["description"],
            "fav_count":     int(database_entry["fav_count"]),
            "comment_count": int(database_entry["comment_count"]),
            "change_seq":    int(database_entry["change_seq"]),
            "duration":      float(duration) if (duration := database_entry.get("duration")) else None,
            "is_favorited":  None,
            "sources":       database_entry["source"].splitlines(),
            "pools":         None,
            "file_info":     file_info,
            "flags":         flags,
            "relationships": relationships,
            "score":         score,
            "tags":          {"all_tags": all_tags},
        })


@define
class Pool(E621Model):
    """ Dataclass representation of an e621 pool. """

    pool_id:     int | None = None
    name:        str | None = None
    created_at:  datetime | None = None
    updated_at:  datetime | None = None
    description: str | None = None
    active:      bool | None = None
    category:    str | None = None
    post_ids:    list[int] = field(factory=list)
    post_count:  int | None = None

    def from_api(self, api_response: dict[str, Any]) -> Self:
        """ Create a pool from an API response input.

        Args:
            api_response (dict[str, Any]): API JSON response data for a single pool.

        Returns:
            Self: Reference to the dataclass itself.
        """
        # Copy the API response such that the input data is not mangled during the remap
        data = deepcopy(api_response)

        # Rename response fields to match their corresponding dataclass fields
        data["pool_id"] = data.pop("id")
        data["active"] = data.pop("is_active")

        # Perform type conversions where required
        data["created_at"] = self.parse_datetime(data["created_at"])
        data["updated_at"] = self.parse_datetime(data["updated_at"])
        data["active"] = self.char_to_bool(data["active"])

        # Explicitly drop some API data which is not parsed to a post dataclass
        data.pop("creator_id", None)
        data.pop("creator_name", None)

        return self.parse_dict(data)

    def from_database(self, database_entry: dict[str, str]) -> Self:
        """ Create a pool from a database CSV row input.

        Args:
            database_entry (dict[str, str]): Database CSV entry for a single pool.

        Returns:
            Self: Reference to the dataclass itself.
        """
        post_ids_str = database_entry["post_ids"][1:-1]
        post_ids = [int(post_id) for post_id in post_ids_str.split(",")] if post_ids_str else []

        return self.parse_dict({
            "pool_id":     int(database_entry["id"]),
            "name":        database_entry["name"],
            "created_at":  self.parse_datetime(database_entry["created_at"]),
            "updated_at":  self.parse_datetime(database_entry["updated_at"]),
            "description": database_entry["description"],
            "active":      self.char_to_bool(database_entry["is_active"]),
            "category":    database_entry["category"],
            "post_ids":    post_ids,
            "post_count":  len(post_ids),
        })
