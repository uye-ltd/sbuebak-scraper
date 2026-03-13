import logging
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from src.helpers.io import compress_pages, decompress_pages

log = logging.getLogger(__name__)

def _add_compress_args(p: ArgumentParser) -> None:
    p.add_argument(
        "--pages-dir",
        type=Path,
        default=Path("pages"),
        metavar="DIR",
        help="Pages directory (default: %(default)s)",
    )


class CompressCommand:
    name = "compress"
    help = "Compress all .html snapshots in pages/ to .html.gz and delete originals"

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:
        _add_compress_args(parser)

    @staticmethod
    def run(args: Namespace) -> None:
        if not args.pages_dir.exists():
            log.error("Pages directory not found: %s", args.pages_dir)
            sys.exit(1)

        compressed, skipped = compress_pages(args.pages_dir)
        log.info("Compressed %d files, skipped %d (already had .gz sibling).", compressed, skipped)


class UncompressCommand:
    name = "uncompress"
    help = "Uncompress all .html.gz snapshots in pages/ to .html and delete originals"

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:
        _add_compress_args(parser)

    @staticmethod
    def run(args: Namespace) -> None:
        if not args.pages_dir.exists():
            log.error("Pages directory not found: %s", args.pages_dir)
            sys.exit(1)

        decompressed, skipped = decompress_pages(args.pages_dir)
        log.info("Decompressed %d files, skipped %d (plain .html already existed).", decompressed, skipped)
