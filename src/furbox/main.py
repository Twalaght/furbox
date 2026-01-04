""" Runner entrypoint for Furbox. """
import os
from pathlib import Path

from fluffless.utils import cli, logging

from furbox import runners
from furbox.models.config import Config

logger = logging.getLogger(__name__)


def get_config_path() -> Path:
    """ Search for a config path in multiple locations, following a preset order.

    Config will be sourced from `config.yaml` in the first valid location from:
        - local package directory (for a development environment install)
        - $XDG_CONFIG_HOME/furbox
        - $HOME/.config/furbox

    Raises:
        FileNotFoundError: Default case where config does not exist is not handled.

    Returns:
        Path: Path of config file.
    """
    config_file_name = "config.yaml"

    if (
        "site-packages" not in __file__ and
        (config_path := Path(__file__).parents[2] / config_file_name).exists()
    ):
        return config_path

    config_root = os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")
    if (config_path := config_root / "furbox" / config_file_name).exists():
        return config_path

    # TODO - Handle case where no config exists.
    raise FileNotFoundError("No valid config file found")


def main() -> None:
    """ Entrypoint runner. """
    cli.import_package_modules(runners)
    args = cli.parse_args()

    logging.setup_logger(
        verbosity=args.verbose,
        modules=["furbox"],
    )

    # TODO
    # Load config from the provided config file.
    config = Config.load_from_yaml(get_config_path())
    cli.run(args, config)


if __name__ == "__main__":
    main()
