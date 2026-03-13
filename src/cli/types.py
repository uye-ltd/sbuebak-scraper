from argparse import ArgumentParser, Namespace
from typing import Literal, Protocol

CommandName = Literal[
    "wall",
    "posts",
    "playlists",
    "subscribers",
    "compress",
    "uncompress",
]

class Command(Protocol):
    name: CommandName
    help: str

    @staticmethod
    def add_args(parser: ArgumentParser) -> None: ...

    @staticmethod
    def run(args: Namespace) -> None: ...
