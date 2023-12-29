""" Module to handle access and parsing of all application configuration.

Example usage of Config: ::

    config = Config().parse_dict(input_dict)
    for config_file in config_files:
        with open(config_file) as f:
            data = yaml.safe_load(f)
            config.parse_dict(data)
"""
import logging
from dataclasses import dataclass, field

from furbox.models.dataclass import DataclassParser

logger = logging.getLogger(__name__)


@dataclass
class Config(DataclassParser):
    """ Unified config object for various dataclass namespaces and top level fields. """

    @dataclass
    class Comics(DataclassParser):
        """ Comics config definitions. """

        base_path:     str = None
        database_file: str = None

    @dataclass
    class E621(DataclassParser):
        """ E621 config definitions. """

        @dataclass
        class FavPaths(DataclassParser):
            """ E621 favourite path config definitions. """

            safe:         str = None
            questionable: str = None
            explicit:     str = None

        username:  str = None
        api_key:   str = None
        fav_paths: FavPaths = field(default_factory=FavPaths)

    @dataclass
    class Misc(DataclassParser):
        """ Comics config definitions. """

        cache_dir: str = None

    comics: Comics = field(default_factory=Comics)
    e621: E621 = field(default_factory=E621)
    misc: Misc = field(default_factory=Misc)
