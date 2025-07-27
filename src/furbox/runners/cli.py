""" Runner module to provide entrypoint decorator functions for CLI interface.

Example usage of CLI entrypoints: ::

    _PARSER = cli.create_subparser(command="awoo", has_subparsers=True)

    @entrypoint(_PARSER)
    def awoo() -> None:
        print("Awoo!")

    cli.run(parse_args(), Config())
"""
import argparse
import importlib
import pkgutil
from types import ModuleType
from typing import Any, Callable

from furbox.models.config import Config

__ROOT_PARSER = argparse.ArgumentParser()
__ROOT_SUBPARSERS = __ROOT_PARSER.add_subparsers(required=True)
__ROOT_PARSER.set_defaults(_entry_func=None)


def base_leaf_parser() -> argparse.ArgumentParser:
    """ Bottom level parser base template with standardised behaviour. """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-q", "--quiet", action="count", default=0,
                        help="decrease verbosity of logger output")
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="increase verbosity of logger output")
    return parser


def create_subparser(command: str, has_subparsers: bool, *args, **kwargs) -> argparse.ArgumentParser:
    """ Create and add subparser within the root parser.

    Args:
        command (str): Command to invoke the subparser.
        has_subparsers (bool): True if the subparser will have nested subparsers, False otherwise.
        *args: Additional positional arguments to pass to `add_parser()`.
        **kwargs: Additional keyword arguments to pass to `add_parser()`.

    Returns:
        argparse.ArgumentParser: Subparser created from the arguments.
    """
    # Only lowest level subparsers should inherit from the parser template
    parents = [base_leaf_parser()] if not has_subparsers else []
    return __ROOT_SUBPARSERS.add_parser(command, *args, **kwargs, parents=parents)


def parse_args(*args, **kwargs) -> argparse.Namespace:
    """ Parse the full set of command line arguments through the root parser. """
    return __ROOT_PARSER.parse_args(*args, **kwargs)


def run(args: argparse.Namespace, config: Config) -> None:
    """ Execute the entrypoint function, or print help if it was provided. """
    if args._entry_func:
        args._entry_func(args, config)
    else:
        __ROOT_PARSER.print_help()


def entrypoint(parser: argparse.ArgumentParser) -> Callable[[argparse.Namespace, Config], Any]:
    """ Decorate a function as the default entrypoint for a given parser. """
    entrypoint_func = Callable[[argparse.Namespace, Config], Any]

    def entrypoint_decorator(entry_func: entrypoint_func) -> entrypoint_func:
        """ Set default entry function for the parser. """
        parser.set_defaults(_entry_func=entry_func)
        return entry_func

    return entrypoint_decorator

def import_package_modules(package: ModuleType) -> None:
    """ Import all modules of a package recursively.

    Args:
        package (ModuleType): Base package to import all modules from.
    """
    for _, name, is_pkg in pkgutil.walk_packages(package.__path__):
        # Resolve the full name of the module and import it.
        module = importlib.import_module(f"{package.__name__}.{name}")

        # If the module itself is a package, import recursively.
        if is_pkg:
            import_package_modules(module)
