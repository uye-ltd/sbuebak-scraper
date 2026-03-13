import logging
import sys
from argparse import ArgumentParser
from pathlib import Path

from src.config import Config
from src.models import WallData
from src.output import load_wall

log = logging.getLogger(__name__)


def add_common_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        metavar="DIR",
        help="Directory for JSON and CSV output (default: %(default)s)",
    )
    parser.add_argument(
        "--pages-dir",
        type=Path,
        default=Path("pages"),
        metavar="DIR",
        help="Directory for HTML snapshots (default: %(default)s)",
    )
    parser.add_argument(
        "--gzip",
        action="store_true",
        help="Save page snapshots as .html.gz (reads both plain and gzipped files)",
    )
    parser.add_argument(
        "--no-scraping",
        action="store_true",
        help="Skip browser scraping phase; parse from existing pages/ snapshots only",
    )
    parser.add_argument(
        "--no-parsing",
        action="store_true",
        help="Skip parsing phase; only download HTML to pages/",
    )


def require_wall_json(config: Config) -> WallData:
    if not config.wall_json.exists():
        log.error("wall.json not found at %s — run 'wall' command first.", config.wall_json)
        sys.exit(1)
    
    return load_wall(config.wall_json)
