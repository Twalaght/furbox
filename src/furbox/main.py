""" Main entrypoint to perform setup and initialise a selected runners entry function. """
import os
import sys
from pathlib import Path

import yaml
from rich.prompt import Confirm

from furbox import runners
from furbox.models.config import Config
from furbox.utils import cli, logging

cli.import_package_modules(runners)

logger = logging.getLogger(__name__)


def get_config_path() -> Path:
    """ Source a config path from a list of locations, following a preset order.

    Config will be sourced from the first valid location from:
    - $XDG_CONFIG_HOME/furbox/config.yaml
    - $HOME/.config/furbox/config.yaml

    If no config is present, user will be prompted to create a default config.

    Returns:
        Path: Path of config file.
    """
    config_root = os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")
    if (config_path := Path(config_root) / "furbox" / "config.yaml").exists():
        return config_path

    if Confirm(f"No config detected at '{config_path}', create with dummy values?"):
        default_config = Config(
            e621=Config.E621(
                username="e621_username",
                api_key="e621_api_key",
            ),
            comics=Config.Comics(
                base_path="base_path_to_comics",
                database_file="comics_database_yaml_file",
            ),
        )

        with config_path.open("w") as f:
            f.write(yaml.dump(default_config.model_dump()))

        logger.print(f"Default config created at '{config_path}'")

        return config_path

    # Exit with an error if no config was provided, and default is not created.
    sys.exit(1)


def main() -> None:
    """ Parse arguments, perform initial setup, and execute the selected runner. """
    args = cli.parse_args()
    logging.setup_logger(args.verbose)
    config = Config.load_from_yaml(get_config_path())

    cli.run(args, config)


if __name__ == "__main__":
    main()
