""" Base class for attrs dataclasses to add standardised functionality. """
import datetime
import logging
import os
from pathlib import Path
from typing import Any

import attrs
import cattr
from typing_extensions import Self

logger = logging.getLogger(__name__)

# TODO
cattr.register_structure_hook(os.PathLike, lambda path, _: Path(path))
cattr.register_structure_hook(datetime.datetime, lambda datetime, _: datetime)


class DataclassParser:
    """ Base class for dataclasses to add standardised parser behaviour. """

    NONE_TYPES = (None, {}, [])

    def parse_dataclass(self, dataclass: Self, overwrite: bool = False) -> Self:
        """ Parse a dataclass of the same type into self, merging the two dataclasses.

        Args:
            dataclass (Self): Input dataclass of the same type to parse from.
            overwrite (bool, optional): Overwrite existing field values. Defaults to False.

        Returns:
            Self: Reference to the existing dataclass, with values added from the input.
        """
        # Iterate over the top level field names for the class
        for field_name in [field.name for field in attrs.fields(type(self))]:
            # Skip the field if the input dataclass has no data for it
            if (new_field_data := getattr(dataclass, field_name)) in self.NONE_TYPES:
                continue

            field_data = getattr(self, field_name)

            # If the field is a subclass, parse from dataclass recursively
            if attrs.has(field_data):
                field_data.parse_dataclass(new_field_data, overwrite)
                continue

            if field_data not in self.NONE_TYPES:
                log_message = f"Duplicate definition provided for {self.__class__.__name__}.{field_name}"

                if not overwrite:
                    logger.info(f"{log_message}, NOT overwriting")
                    continue

                logger.info(f"{log_message}, overwriting")

            setattr(self, field_name, new_field_data)

        return self

    def parse_dict(self, data: dict[str, Any], overwrite: bool = False) -> Self:
        """ Populate a dataclass with values from a dictionary.

        Args:
            data (dict[str, Any]): Dictionary of mapped field/value pairs for the dataclass.
            overwrite (bool, optional): Overwrite existing field values. Defaults to False.

        Returns:
            Self: Reference to the existing dataclass, with values added from the input.
        """
        dataclass = cattr.structure(data, type(self))
        return self.parse_dataclass(dataclass, overwrite)

    def to_dict(self) -> dict[str, Any]:
        """ Return a generic dictionary representation of a dataclass. """
        return attrs.asdict(self)
