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
    class E621(DataclassParser):
        """ E621 config definitions. """

        @dataclass
        class FavPaths(DataclassParser):
            """ E621 favourite path config definitions. """

            safe:         str = ""
            questionable: str = ""
            explicit:     str = ""

        username:  str = ""
        api_key:   str = ""
        fav_paths: FavPaths = field(default_factory=FavPaths)

    e621: E621 = field(default_factory=E621)
