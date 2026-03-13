import logging
import sys
from argparse import ArgumentParser, Namespace

from src.browser import create_driver, wait_for_manual_login
from src.cli.common import add_common_args, require_wall_json
from src.config import Config
from src.output import save_json
from src.scrapers.posts import collect_all_posts, download_post_pages

log = logging.getLogger(__name__)


class PostsCommand:
    name = "posts"
    help = "Fetch full comment trees for each post → data/posts.json"

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:
        add_common_args(parser=parser)

        parser.add_argument(
            "--comment-pause",
            type=float,
            default=1.5,
            metavar="SEC",
            help="Seconds to wait when expanding comment threads (default: %(default)s)",
        )

    @staticmethod
    def run(args: Namespace) -> None:
        config = Config(
            output_dir=args.output_dir,
            pages_dir=args.pages_dir,
            comment_pause_sec=args.comment_pause,
            gzip_pages=args.gzip,
        )

        posts = require_wall_json(config).posts
        if not posts:
            log.error("No posts in wall.json.")
            sys.exit(1)

        log.info("Loaded %d posts from wall.json.", len(posts))

        if args.no_scraping:
            save_json(collect_all_posts(None, posts, config), config.posts_json)
            log.info("Done → %s", config.posts_json)
            return

        if args.no_parsing:
            driver = create_driver(config)
            try:
                wait_for_manual_login(driver, config.login_url)
                download_post_pages(driver, posts, config)
            except KeyboardInterrupt:
                log.warning("Interrupted.")
            finally:
                driver.quit()
            log.info("Download done → %s/", config.posts_dir)
            return

        driver = create_driver(config)
        try:
            wait_for_manual_login(driver, config.login_url)
            download_post_pages(driver, posts, config)
            save_json(collect_all_posts(None, posts, config), config.posts_json)
        except KeyboardInterrupt:
            log.warning("Interrupted — partial results saved.")
        finally:
            driver.quit()
        log.info("Done → %s", config.posts_json)
