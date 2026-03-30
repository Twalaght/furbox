""" Model definitions for comics. """
from fluffless.models.base_model import BaseModel


class E621Comic(BaseModel):
    """ Local comic database model for an e621 pool. """

    # Pool ID for the comic.
    pool_id:        int
    # Name of the folder to download to, will default to the name of the pool in E621 if unset.
    name:           str | None = None
    # Number of posts which are not expected to be downloaded (Ex. Deliberately excluded pages).
    local_offset:   int = 0
    # Number of posts which have been deleted on server side, and should be skipped over.
    server_deleted: int = 0
    # Local directory to download files to, relative to the base comics directory.
    dir_name:       str | None = None
    # Update the local files if True, only check for new items without downloading if False.
    update:         bool = True


class Comics(BaseModel):
    """ Top level config object for the comics database file. """

    e621: list[E621Comic] = []
