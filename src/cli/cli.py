import logging
from argparse import ArgumentParser
from typing import Final

from src.cli import commands
from src.cli.types import Command

log = logging.getLogger(__name__)


_COMMANDS: Final[tuple[Command, ...]] = (
    commands.WallCommand,
    commands.PostsCommand,
    commands.PlaylistsCommand,
    commands.SubscribersCommand,
    commands.CompressCommand,
    commands.UncompressCommand,
)

def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="scraper",
        description="Scrape VK community wall, posts, playlists, and subscribers.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    for command in _COMMANDS:
        subparser = sub.add_parser(name=command.name, help=command.help)

        command.add_args(parser=subparser)

        subparser.set_defaults(func=command.run)

    return parser
