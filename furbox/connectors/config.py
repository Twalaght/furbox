""" Centralised module to handle all application configuration.

Example usage of Config: ::

    # TODO
"""
import logging
from dataclasses import dataclass, field, is_dataclass
from typing import Any, Type

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """ Unified config object for various dataclass namespaces and top level fields. """

    @dataclass
    class E621():
        """ E621 config definitions. """

        @dataclass
        class FavPaths():
            """ E621 favourite path config definitions. """

            safe:         str = ""
            questionable: str = ""
            explicit:     str = ""

        username:  str = ""
        api_key:   str = ""
        fav_paths: FavPaths = field(default_factory=FavPaths)

    e621: E621 = field(default_factory=E621)

    @staticmethod
    def parse_dict_to_dataclass(dataclass: Type, data: dict[str, Any], overwrite: bool = False) -> None:
        """ Populate a dataclass with values from a dictionary.

        Args:
            dataclass (Type): Dataclass to set field values for.
            data (dict[str, Any]): Dictionary of mapped field/value pairs for the dataclass.
            overwrite (bool, optional): Overwrite existing field values. Defaults to False.
        """
        dataclass_name = dataclass.__class__.__name__

        # Iterate over each field present within the given dataclass
        for field_name, reference in vars(dataclass).items():
            # For fields which are dataclasses themselves, parse the data recursively
            if is_dataclass(reference):
                if data_subset := data.pop(field_name, None):
                    Config.parse_dict_to_dataclass(reference, data_subset, overwrite)

            # For fields which exist in data, set the field value if permissable
            elif (field_name in data) and (value := data.pop(field_name)):
                # if existing_value := getattr(dataclass, field_name, None):
                if getattr(dataclass, field_name, None):
                    if overwrite:
                        logger.debug(f"Duplicate definition for '{dataclass_name}', overwriting")
                    else:
                        logger.debug(f"Duplicate definition for '{dataclass_name}', not overwriting")
                        continue

                setattr(dataclass, field_name, value)

        if data:
            logger.warning(f"Received definitions for '{dataclass_name}' which did not match any fields. "
                           f"Dataclass field keys = {list(data.keys())}")
