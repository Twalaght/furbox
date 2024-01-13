

""" Unit test class for Dataclass parser class defined in furbox/models/dataclass.py. """
import os
from pathlib import Path
from typing import Any

from attrs import define, field
import pytest

from furbox.models.dataclass import DataclassParser


class TestDataclass:
    """ Test functionality provided in the base dataclass. """

    @define
    class Pack(DataclassParser):
        """ Example dataclass of a wolf pack. """

        @define
        class Wolf(DataclassParser):
            """ Example dataclass of a wolf. """

            name:       str | None = None
            age:        int | None = None
            attributes: dict[str, Any] = field(factory=dict)

        leader:     Wolf
        group_name: str | None = None
        members:    list[Wolf] = field(factory=list)

    input_dict = {
        "group_name": "uwu",
        "leader": {
            "name": "Blaidd",
            "age": 25,
            "attributes": {
                "str": 10,
            },
        },
        "members": [
            {
                "name": "Legoshi",
                "age": 19,
                "attributes": {},
            },
            {
                "name": "Death",
                "age": None,
                "attributes": {},
            },
        ],
    }

    def test_missing_required_value(self) -> None:
        """ Create a dataclass with no value provided for a required field. """
        with pytest.raises(TypeError):
            self.Pack()

    def test_dict_parser(self) -> None:
        """ Parse a dataclass from a dictionary input. """
        pack = self.Pack(leader=None).parse_dict(self.input_dict)

        assert isinstance(pack.leader, self.Pack.Wolf)
        for wolf in pack.members:
            assert isinstance(wolf, self.Pack.Wolf)

        assert pack.to_dict() == self.input_dict

    def test_parser_overwrite(self) -> None:
        """ Parse from a dictionary with existing data in the respective fields. """
        pack = self.Pack(leader=None).parse_dict({"leader": {"name": "Blaidd"}})
        assert "cute" not in pack.leader.attributes

        pack.parse_dict({"leader": {"name": "Legoshi", "attributes": {"cute": True}}}, overwrite=False)
        assert pack.leader.name == "Blaidd"
        assert pack.leader.attributes["cute"] is True

        pack.parse_dict({"leader": {"name": "Legoshi"}}, overwrite=True)
        assert pack.leader.name == "Legoshi"
        assert pack.leader.attributes["cute"] is True

    def test_type_conversion(self) -> None:
        """ Parse from a dictionary and assert type conversion was appropriate. """
        @define
        class Config(DataclassParser):
            config_dir: os.PathLike | None = None

        config = Config().parse_dict({"config_dir": "config/dir/path"})
        assert isinstance(config.config_dir, os.PathLike)

        config = Config().parse_dict({"config_dir": Path("config/dir/path")})
        assert isinstance(config.config_dir, os.PathLike)
