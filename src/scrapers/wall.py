"""Infinite-scroll wall scraper."""

import logging
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.config import Config
from src.helpers.io import list_snapshots, read_page, write_page
from src.models import Post
from src.parsers.wall import extract_community_id, parse_page

log = logging.getLogger(__name__)


def _wait_for_wall(driver: webdriver.Chrome, config: Config) -> None:
    log.info("Waiting for post elements (up to 30 s)…")
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-post-id]"))
        )
        log.info("Wall ready.")
    except Exception:  # noqa: BLE001
        log.warning("No post elements found after 30 s – proceeding anyway.")


def scroll_wall(driver: webdriver.Chrome, config: Config) -> tuple[list[Post], str | None]:
    """Scroll community wall, save snapshots to pages/wall/, return (posts, community_id)."""
    log.info("Navigating to %s", config.target_url)
    try:
        driver.get(config.target_url)
    except Exception:  # noqa: BLE001
        log.warning("Page load timed out – continuing with partial load.")
    _wait_for_wall(driver, config)

    wall_dir = config.wall_dir
    wall_dir.mkdir(parents=True, exist_ok=True)

    seen: dict[str, Post] = {}
    community_id: str | None = None
    scroll_index = 0
    no_new_at_bottom = 0

    log.info("Starting infinite scroll…")

    while True:
        html = driver.page_source
        write_page(wall_dir / f"scroll_{scroll_index:04d}.html", html, config)

        new_posts: list[Post] = []
        for post in parse_page(html):
            if post.id and post.id not in seen:
                seen[post.id] = post
                new_posts.append(post)

        if community_id is None and seen:
            community_id = extract_community_id(list(seen.values()))

        at_bottom: bool = driver.execute_script(
            "return (window.scrollY + window.innerHeight) >= (document.body.scrollHeight - 200);"
        )

        log.info(
            "Scroll %d: +%d new posts (total %d)%s",
            scroll_index,
            len(new_posts),
            len(seen),
            " [bottom]" if at_bottom else "",
        )

        if config.max_posts and len(seen) >= config.max_posts:
            log.info("Reached max_posts=%d. Stopping.", config.max_posts)
            break

        if at_bottom and not new_posts:
            no_new_at_bottom += 1
            log.info(
                "At bottom, no new posts (%d/%d)", no_new_at_bottom, config.max_unchanged_scrolls
            )
            if no_new_at_bottom >= config.max_unchanged_scrolls:
                log.info("Page end detected. Stopping.")
                break
            time.sleep(config.scroll_pause_sec)
        else:
            no_new_at_bottom = 0

        driver.execute_script("window.scrollBy(0, window.innerHeight * 4);")
        time.sleep(config.scroll_pause_sec)
        scroll_index += 1

    log.info("Collected %d unique posts.", len(seen))
    return list(seen.values()), community_id


def parse_wall_snapshots(config: Config) -> tuple[list[Post], str | None]:
    """Parse posts from existing pages/wall/ snapshots (no browser)."""
    snaps = list_snapshots(config.wall_dir)
    if not snaps:
        log.warning("No wall snapshots found in %s", config.wall_dir)
        return [], None

    log.info("Parsing %d wall snapshots from %s", len(snaps), config.wall_dir)
    seen: dict[str, Post] = {}
    for snap in snaps:
        for post in parse_page(read_page(snap)):
            if post.id and post.id not in seen:
                seen[post.id] = post

    community_id = extract_community_id(list(seen.values())) if seen else None
    log.info("Parsed %d unique posts.", len(seen))
    return list(seen.values()), community_id
