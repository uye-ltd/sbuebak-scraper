import logging
import sys
from argparse import ArgumentParser, Namespace

from src.browser import create_driver, wait_for_manual_login
from src.cli.common import add_common_args
from src.config import Config
from src.helpers.io import list_snapshots
from src.models import WallData
from src.output import save_wall
from src.scrapers.wall import parse_wall_snapshots, scroll_wall

log = logging.getLogger(__name__)


class WallCommand:
    name = "wall"
    help = "Scroll community wall → data/wall.json + data/wall.csv"

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:
        add_common_args(parser=parser)

        parser.add_argument(
            "--community-slug",
            default="uyebark",
            metavar="SLUG",
            help="VK community slug to scrape (default: %(default)s)",
        )
        parser.add_argument(
            "--max-posts",
            type=int,
            default=None,
            metavar="N",
            help="Stop after collecting N posts (default: no limit)",
        )
        parser.add_argument(
            "--scroll-pause",
            type=float,
            default=3.0,
            metavar="SEC",
            help="Seconds to wait after each scroll (default: %(default)s)",
        )
        parser.add_argument(
            "--max-unchanged",
            type=int,
            default=6,
            metavar="N",
            help="Stop after N consecutive scrolls with no new content (default: %(default)s)",
        )

    @staticmethod
    def run(args: Namespace) -> None:
        config = Config(
            community_slug=args.community_slug,
            output_dir=args.output_dir,
            pages_dir=args.pages_dir,
            max_posts=args.max_posts,
            scroll_pause_sec=args.scroll_pause,
            max_unchanged_scrolls=args.max_unchanged,
            gzip_pages=args.gzip,
        )

        if args.no_scraping:
            posts, community_id = parse_wall_snapshots(config)
        else:
            driver = create_driver(config)
            posts, community_id = [], None
            try:
                wait_for_manual_login(driver, config.login_url)
                posts, community_id = scroll_wall(driver, config)
            except KeyboardInterrupt:
                log.warning("Interrupted — parsing collected snapshots…")
                posts, community_id = parse_wall_snapshots(config)
            finally:
                driver.quit()

        if not posts:
            log.error("No posts collected.")
            sys.exit(1)

        if args.no_parsing:
            snaps = list_snapshots(config.wall_dir)
            log.info("Scraping done. %d snapshots in %s/", len(snaps), config.wall_dir)
            return

        wall = WallData(
            community_slug=args.community_slug,
            subscribers_url=f"https://vk.com/{args.community_slug}?act=members",
            playlists_url=f"https://vk.com/audios-{community_id}" if community_id else None,
            posts=posts,
        )

        save_wall(wall, config.wall_json, config.wall_csv)
        log.info("Done. %d posts → %s/", len(posts), config.output_dir)
