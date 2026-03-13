import json
import logging
import sys
from argparse import ArgumentParser, Namespace

from src.browser import create_driver, wait_for_manual_login
from src.cli.common import add_common_args, require_wall_json
from src.config import Config
from src.helpers.io import list_snapshots
from src.scrapers.playlists import parse_playlists_snapshots, scroll_playlists

log = logging.getLogger(__name__)


class PlaylistsCommand:
    name = "playlists"
    help = "Scrape community audio page → data/playlists.json"

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:
        add_common_args(parser=parser)

    @staticmethod
    def run(args: Namespace) -> None:
        config = Config(
            output_dir=args.output_dir,
            pages_dir=args.pages_dir,
            gzip_pages=args.gzip,
        )

        if not (playlists_url := require_wall_json(config).playlists_url):
            log.error("playlists_url is missing from wall.json — re-run 'wall' command.")
            sys.exit(1)

        if not args.no_scraping:
            driver = create_driver(config)
            try:
                wait_for_manual_login(driver, config.login_url)
                scroll_playlists(driver, playlists_url, config)
            except KeyboardInterrupt:
                log.warning("Interrupted — parsing collected snapshots.")
            finally:
                driver.quit()

        if args.no_parsing:
            snaps = list_snapshots(config.playlists_dir)
            log.info("Scraping done. %d snapshots in %s/", len(snaps), config.playlists_dir)
            return

        records = parse_playlists_snapshots(config)

        out = config.playlists_json
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        log.info("Done. %d items → %s", len(records), out)
