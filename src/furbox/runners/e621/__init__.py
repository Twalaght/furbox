from fluffless.utils import cli

__PARSER = cli.add_parser("e621", is_leaf=False, help="Collection of e621 related runners.")
_SUBPARSERS = __PARSER.add_subparsers(required=True)
