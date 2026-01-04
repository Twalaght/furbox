""" TODO - Module to handle access and parsing of all application configuration.

Example usage of Config: ::

    config = Config().parse_dict(input_dict)
    for config_file in config_files:
        with open(config_file) as f:
            data = yaml.safe_load(f)
            config.parse_dict(data)
"""
from pathlib import Path

from fluffless.models.base_model import BaseModel
from fluffless.utils import logging

logger = logging.getLogger(__name__)


class Config(BaseModel):
    """ Model definition of main config object. """

    class Comics(BaseModel):
        """ Comics config definitions. """

        base_path:     Path
        database_file: str

    class E621(BaseModel):
        """ E621 config definitions. """

        class FavPaths(BaseModel):
            """ E621 favourite path config definitions. """

            safe:         str
            questionable: str
            explicit:     str

        username:  str
        api_key:   str
        fav_paths: FavPaths | None = None

    class Misc(BaseModel):
        """ Miscellaneous config definitions. """

        cache_dir: str | None = None

    comics: Comics | None = None
    e621:   E621 | None = None
    misc:   Misc | None = None
