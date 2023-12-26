""" Base class for dataclasses to add standardised functionality. """
import logging
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

from typing_extensions import Self

logger = logging.getLogger(__name__)


@dataclass
class DataclassParser:
    """ Base class for dataclasses to add standardised parser behaviour. """

    def parse_dict(self, data: dict[str, Any], overwrite: bool = False) -> Self:
        """ Populate a dataclass with values from a dictionary.

        Args:
            data (dict[str, Any]): Dictionary of mapped field/value pairs for the dataclass.
            overwrite (bool, optional): Overwrite existing field values. Defaults to False.

        Returns:
            Self: Reference to the dataclass itself.
        """
        dataclass_name = self.__class__.__name__

        # Iterate over each field present within the given dataclass
        for field_name, reference in vars(self).items():
            # For fields which are dataclasses themselves, parse the data recursively
            if is_dataclass(reference):
                if data_subset := data.pop(field_name, None):
                    reference.parse_dict(data_subset, overwrite)

            # For fields which exist in data, set the field value if permissable
            elif (field_name in data) and ((value := data.pop(field_name)) is not None):
                if getattr(self, field_name, None):
                    if overwrite:
                        logger.debug(f"Duplicate definition for '{dataclass_name}', overwriting")
                    else:
                        logger.debug(f"Duplicate definition for '{dataclass_name}', not overwriting")
                        continue

                setattr(self, field_name, value)

        if data:
            logger.warning(f"Received definitions for '{dataclass_name}' which did not match any fields. "
                           f"Dataclass field keys = {list(data.keys())}")

        return self

    def to_dict(self) -> dict[str, Any]:
        """ Return a generic dictionary representation of a dataclass. """
        return asdict(self)
