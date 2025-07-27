""" Main entrypoint to perform setup and transfer control to a runner's entry function. """

import logging
import os
from pathlib import Path

import yaml

from furbox import runners
from furbox.models.config import Config
from furbox.runners import cli

cli.import_package_modules(runners)

logger = logging.getLogger(__name__)


def get_config_path() -> os.PathLike:
    """ Search for a config path in multiple locations, following a preset order.

    Config will be sourced from `furbox_config.yaml` in the first valid location from:
        - local package directory (for a development environment install)
        - $XDG_CONFIG_HOME/furbox
        - $HOME/.config/furbox

    Raises:
        NotImplementedError: TODO. Default case where config does not exist is not handled.

    Returns:
        os.PathLike: Path of config file.
    """
    if "site-packages" not in __file__:
        project_root = Path(__file__).parents[1]
        config_path = project_root / "furbox_config.yaml"
        if config_path.exists():
            return config_path

    if config_root := os.getenv("XDG_CONFIG_HOME"):
        config_path = config_root / "furbox" / "furbox_config.yaml"
        if config_path.exists():
            return config_path

    config_root = Path.home() / ".config" / "furbox" / "furbox_config.yaml"
    if config_path.exists():
        return config_path

    # TODO - Handle case where no config exists
    raise NotImplementedError


def main() -> None:
    """ TODO. """
    args = cli.parse_args()

    with open(get_config_path()) as f:
        data = yaml.safe_load(f)

    config = Config().parse_dict(data)

    cli.run(args, config)


if __name__ == "__main__":
    main()
