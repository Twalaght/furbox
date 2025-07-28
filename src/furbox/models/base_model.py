""" Pydantic model base class definitions. """

from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


class BaseModel(PydanticBaseModel):
    """ Base class for Pydantic models, setting standard configuration. """

    model_config = ConfigDict(
        extra="ignore",            # Undefined extra values are ignored without raising an error.
        validate_assignment=True,  # Model is validated and type conversion is performed as items are loaded.
        use_enum_values=True,      # Deserialize StrEnum's to their string representation.
    )

    @classmethod
    def load_from_yaml(cls, yaml_path: Path) -> Self:
        """ Load data from a YAML file into a model.

        Args:
            yaml_path (Path): YAML file path to load data from.

        Raises:
            FileNotFoundError: YAML file does not exist.

        Returns:
            Self: Instantiated instance of the model.
        """
        if not yaml_path.exists():
            raise FileNotFoundError(f"YAML file '{yaml_path}' does not exist")

        with yaml_path.open() as f:
            return cls(**yaml.safe_load(f))


class StrictModel(BaseModel):
    """ Base class for Pydantic models, setting standard configuration. """

    model_config = ConfigDict(
        extra="forbid",  # Undefined extra values raise an error.
    )
