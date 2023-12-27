""" Main entrypoint to perform setup and transfer control to a runner's entry function. """

import logging
from pathlib import Path

from furbox.models.config import Config
from furbox.runners import cli
from furbox.runners.comics import comics_update

import yaml

logger = logging.getLogger(__name__)


def main() -> None:
    """ TODO. """
    args = cli.parse_args()

    # TODO - Placeholder for config location
    project_root = Path(__file__).parents[1]
    config_path = project_root / "furbox_config.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    config = Config().parse_dict(data)

    cli.run(args, config)


if __name__ == "__main__":
    main()
