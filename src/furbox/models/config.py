""" Module to handle access and parsing of all configuration.

Example usage of Config: ::

    config = Config().load_from_yaml(input_dict)
    api_key = config.e621.api_key
"""
from pathlib import Path

from furbox.models.base_model import BaseModel
from furbox.utils import logging

logger = logging.getLogger(__name__)


class Config(BaseModel):
    """ Unified config object for various dataclass namespaces and top level fields. """

    class Comics(BaseModel):
        """ Comics config definitions. """

        base_path:     Path
        database_file: Path

    class E621(BaseModel):
        """ E621 config definitions. """

        class FavPaths(BaseModel):
            """ E621 favourite path config definitions. """

            safe:         Path
            questionable: Path
            explicit:     Path

        username:  str
        api_key:   str
        fav_paths: FavPaths | None = None

    class Misc(BaseModel):
        """ Comics config definitions. """

        cache_dir: Path | None = None

    e621:   E621 | None = None
    comics: Comics | None = None
    misc:   Misc = Misc()
