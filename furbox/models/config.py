""" Module to handle access and parsing of all application configuration.

Example usage of Config: ::

    config = Config().parse_dict(input_dict)
    for config_file in config_files:
        with open(config_file) as f:
            data = yaml.safe_load(f)
            config.parse_dict(data)
"""
import logging

from attrs import define, field
from furbox.models.dataclass import DataclassParser

logger = logging.getLogger(__name__)


@define
class Config(DataclassParser):
    """ Unified config object for various dataclass namespaces and top level fields. """

    @define
    class Comics(DataclassParser):
        """ Comics config definitions. """

        base_path:     str | None = None
        database_file: str | None = None

    @define
    class E621(DataclassParser):
        """ E621 config definitions. """

        @define
        class FavPaths(DataclassParser):
            """ E621 favourite path config definitions. """

            safe:         str | None = None
            questionable: str | None = None
            explicit:     str | None = None

        username:  str | None = None
        api_key:   str | None = None
        fav_paths: FavPaths = field(factory=FavPaths)

    @define
    class Misc(DataclassParser):
        """ Comics config definitions. """

        cache_dir: str | None = None

    comics: Comics = field(factory=Comics)
    e621:   E621 = field(factory=E621)
    misc:   Misc = field(factory=Misc)
