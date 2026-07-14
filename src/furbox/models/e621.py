""" Model for e621 posts and pools, with parsing functionality. """
import itertools
from copy import deepcopy
from datetime import datetime
from enum import IntEnum, StrEnum
from typing import Any, Self

from fluffless.models.base_model import BaseModel
from fluffless.utils import logging

logger = logging.getLogger(__name__)

# Artist tags which are used only for metadata, and should not be considered as actual artists.
META_ARTISTS = (
    "anonymous_artist",
    "conditional_dnp",
    "sound_warning",
    "third-party_edit",
    "unknown_artist",
)


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


class Post(BaseModel):
    """ Dataclass representation of an e621 post. """

    class Rating(StrEnum):
        """ Permissible content rating associated with a post. """

        SAFE = "s"
        QUESTIONABLE = "q"
        EXPLICIT = "e"

    class FileInfo(BaseModel):
        """ File information associated with a post. """

        width:  int
        height: int
        size:   int
        ext:    str
        md5:    str
        url:    str

    class Flags(BaseModel):
        """ Post status flags. """

        deleted:       bool
        pending:       bool
        flagged:       bool
        rating_locked: bool
        status_locked: bool
        note_locked:   bool

    class Relationships(BaseModel):
        """ Post relationship information. """

        parent_id:           int | None = None
        has_children:        bool | None = None
        has_active_children: bool | None = None
        children:            list[int] = []

    class Score(BaseModel):
        """ Post score values. """

        total: int
        up:    int
        down:  int

    class Tags(BaseModel):
        """ Post tags by category, and a combined full list. """

        general:    list[str] = []
        artist:     list[str] = []
        copyrights: list[str] = []
        character:  list[str] = []
        species:    list[str] = []
        invalid:    list[str] = []
        meta:       list[str] = []
        lore:       list[str] = []

        # Database tags are not split by normal categories, and as such are given their own category.
        database:   list[str] = []

        @property
        def all_tags(self) -> list[str]:
            """ Property combining all tags present in the post into one list. """
            all_tags = [getattr(self, key) for key in list(type(self).model_fields.keys())]
            return sorted(set(itertools.chain(*all_tags)))

        @property
        def artist_names(self) -> list[str]:
            """ Get the names of all artists not considered metadata tags. """
            return [artist for artist in self.artist if artist not in META_ARTISTS]

    post_id:       int
    uploader_id:   int
    approver_id:   int | None = None
    created_at:    datetime
    updated_at:    datetime | None = None
    rating:        Rating
    description:   str
    fav_count:     int
    comment_count: int
    change_seq:    int
    duration:      float | None = None
    is_favorited:  bool | None = None
    sources:       list[str] = []
    pools:         list[int] = []
    file_info:     FileInfo
    flags:         Flags
    relationships: Relationships
    score:         Score
    tags:          Tags

    @classmethod
    def from_api(cls, api_response: dict[str, Any]) -> Self:
        """ Create a post model from an API response. """
        # Copy the API response such that the input data is not mangled during the remap
        data = deepcopy(api_response)

        # Rename response fields to match their corresponding model fields.
        data["tags"]["copyrights"] = data["tags"].pop("copyright")
        data["post_id"] = data.pop("id")

        # Extract info for file metadata and the original file.
        file_info = data.pop("files")
        data["file_info"] = file_info["meta"] | file_info["original"]

        # Extract stats info for score, then combine stats with top level data.
        stats = data.pop("stats")
        data["score"] = stats["score"]
        data |= stats

        # Explicitly drop some API data which is not parsed to a post model.
        for key in ("preview", "sample", "locked_tags", "has_notes"):
            data.pop(key, None)

        return cls(**data)

    @classmethod
    def from_database(cls, database_entry: dict[str, Any]) -> Self:
        """ Create a post from a database CSV row input, from e621's `db_export` endpoint. """
        # Copy the database entry such that the input data is not mangled during the remap.
        data = deepcopy(database_entry)

        file_info = cls.FileInfo(
            width=data["image_width"],
            height=data["image_height"],
            size=data["file_size"],
            ext=data["file_ext"],
            md5=data["md5"],
            url=source_url_from_hash(data["md5"], data["file_ext"]),
        )

        flags = cls.Flags(**{
            name: data[f"is_{name}"] for name in
            ("deleted", "pending", "flagged", "rating_locked", "status_locked", "note_locked")},
        )

        score = cls.Score(
            total=data["score"],
            up=data["up_score"],
            down=data["down_score"],
        )

        all_tags = []
        for tag_type in ["tag_string", "locked_tags"]:
            if tag_string := database_entry[tag_type]:
                all_tags.extend(tag_string.split())

        return cls(
            post_id=data["id"],
            uploader_id=data["uploader_id"],
            approver_id=data["approver_id"] or None,
            created_at=data["created_at"],
            updated_at=data["updated_at"] or None,
            rating=data["rating"],
            description=data["description"],
            fav_count=data["fav_count"],
            comment_count=data["comment_count"],
            change_seq=data["change_seq"],
            duration=data["duration"] or None,
            sources=data["source"].splitlines(),
            file_info=file_info,
            flags=flags,
            relationships=cls.Relationships(parent_id=data["parent_id"] or None),
            score=score,
            tags=cls.Tags(database=all_tags),
        )


class Pool(BaseModel):
    """ Dataclass representation of an e621 pool. """

    pool_id:     int
    name:        str
    created_at:  datetime
    updated_at:  datetime
    description: str
    active:      bool
    category:    str
    post_ids:    list[int]
    post_count:  int

    @classmethod
    def from_api(cls, api_response: dict[str, Any]) -> Self:
        """ Create a pool model from an API response. """
        # Copy the API response such that the input data is not mangled during the remap.
        data = deepcopy(api_response)

        # Rename response fields to match their corresponding model fields.
        data["pool_id"] = data.pop("id")
        data["active"] = data.pop("is_active")

        # Explicitly drop some API data which is not parsed to a pool model.
        for key in ("creator_id", "creator_name"):
            data.pop(key, None)

        return cls(**data)

    @classmethod
    def from_database(cls, database_entry: dict[str, Any]) -> Self:
        """ Create a pool from a database CSV row input, from e621's `db_export` endpoint. """
        # Copy the database entry such that the input data is not mangled during the remap.
        data = deepcopy(database_entry)

        # Extra post ID's from the string provided in the database, and get their length.
        post_ids_str = data["post_ids"][1:-1]
        data["post_ids"] = [int(post_id) for post_id in post_ids_str.split(",")] if post_ids_str else []
        data["post_count"] = len(data["post_ids"])

        # Rename response fields to match their corresponding model fields.
        data["pool_id"] = data.pop("id")
        data["active"] = data.pop("is_active")

        return cls(**data)  # type: ignore[invalid-argument-type]


class Tag(BaseModel):
    """ Dataclass representation of an e621 tag. """

    class Category(IntEnum):
        """ Int enum of categories an e621 tag may be associated with. """

        GENERAL = 0
        ARTIST = 1
        CONTRIBUTOR = 2
        COPYRIGHT = 3
        CHARACTER = 4
        SPECIES = 5
        INVALID = 6
        META = 7
        LORE = 8

    tag_id:                  int
    name:                    str
    post_count:              int
    related_tags:            dict[str, int] = {}
    related_tags_updated_at: datetime
    category:                Category
    is_locked:               bool
    created_at:              datetime
    updated_at:              datetime

    @classmethod
    def from_api(cls, api_response: dict[str, Any]) -> Self:
        """ Create a tag model from an API response. """
        # Copy the API response such that the input data is not mangled during the remap.
        data = deepcopy(api_response)

        # Rename response fields to match their corresponding model fields.
        data["tag_id"] = data.pop("id")

        # Extract the related tags string into a dictionary of tag names to their associated relationship score.
        # It can return a literal string "[]" when empty so this must be checked against.
        if (related_tag_string := data.pop("related_tags")) not in ("[]", None):
            iterator = iter(related_tag_string.split(" "))
            data["related_tags"] = dict(zip(iterator, iterator, strict=True))

        return cls(**data)
