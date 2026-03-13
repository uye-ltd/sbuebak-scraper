"""Scroll VK community members page and save HTML snapshots."""

import logging
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.config import Config
from src.helpers.io import list_snapshots, read_page, write_page
from src.models import Subscriber
from src.parsers.subscribers import parse_subscribers_page

log = logging.getLogger(__name__)


def scroll_subscribers(driver: webdriver.Chrome, subscribers_url: str, config: Config) -> None:
    """Navigate to community members page, scroll it, save snapshots to pages/subscribers/."""
    log.info("Navigating to %s", subscribers_url)
    try:
        driver.get(subscribers_url)
    except Exception:  # noqa: BLE001
        log.warning("Page load timed out – continuing.")

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='/id']"))
        )
    except Exception:  # noqa: BLE001
        log.warning("No member elements found after 20 s – proceeding anyway.")

    subscribers_dir = config.subscribers_dir
    subscribers_dir.mkdir(parents=True, exist_ok=True)

    scroll_index = 0
    no_new_at_bottom = 0

    log.info("Starting subscriber scroll…")

    while True:
        html = driver.page_source
        write_page(subscribers_dir / f"scroll_{scroll_index:04d}.html", html, config)

        at_bottom: bool = driver.execute_script(
            "return (window.scrollY + window.innerHeight) >= (document.body.scrollHeight - 200);"
        )

        log.info("Scroll %d%s", scroll_index, " [bottom]" if at_bottom else "")

        if at_bottom:
            no_new_at_bottom += 1
            if no_new_at_bottom >= config.max_unchanged_scrolls:
                log.info("Page end detected. Stopping.")
                break
            time.sleep(config.scroll_pause_sec)
        else:
            no_new_at_bottom = 0

        driver.execute_script("window.scrollBy(0, window.innerHeight * 3);")
        time.sleep(config.scroll_pause_sec)
        scroll_index += 1

    log.info("Done scrolling subscribers. %d snapshots saved.", scroll_index + 1)


def parse_subscribers_snapshots(config: Config, community_slug: str = "") -> list[Subscriber]:
    """Parse subscribers from existing pages/subscribers/ snapshots (no browser)."""
    snaps = list_snapshots(config.subscribers_dir)
    if not snaps:
        log.warning("No subscriber snapshots found in %s", config.subscribers_dir)
        return []

    log.info("Parsing %d subscriber snapshots from %s", len(snaps), config.subscribers_dir)
    seen: set[str] = set()
    result: list[Subscriber] = []
    for snap in snaps:
        for sub in parse_subscribers_page(read_page(snap), community_slug):
            if sub.url and sub.url not in seen:
                seen.add(sub.url)
                result.append(sub)

    log.info("Parsed %d unique subscribers.", len(result))
    return result
