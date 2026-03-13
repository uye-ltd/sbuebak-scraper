import json
import logging
from argparse import ArgumentParser, Namespace

from src.browser import create_driver, wait_for_manual_login
from src.cli.common import add_common_args, require_wall_json
from src.config import Config
from src.helpers.io import list_snapshots
from src.scrapers.subscribers import parse_subscribers_snapshots, scroll_subscribers

log = logging.getLogger(__name__)


class SubscribersCommand:
    name = "subscribers"
    help = "Scrape community members → data/subscribers.json"

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

        wall = require_wall_json(config)
        subscribers_url = wall.subscribers_url
        community_slug = wall.community_slug

        if not args.no_scraping:
            driver = create_driver(config)
            try:
                wait_for_manual_login(driver, config.login_url)
                scroll_subscribers(driver, subscribers_url, config)
            except KeyboardInterrupt:
                log.warning("Interrupted — parsing collected snapshots.")
            finally:
                driver.quit()

        if args.no_parsing:
            snaps = list_snapshots(config.subscribers_dir)
            log.info("Scraping done. %d snapshots in %s/", len(snaps), config.subscribers_dir)
            return

        subscribers = parse_subscribers_snapshots(config, community_slug)
        out = config.subscribers_json
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump([s.to_dict() for s in subscribers], f, ensure_ascii=False, indent=2)
        log.info("Done. %d subscribers → %s", len(subscribers), out)
