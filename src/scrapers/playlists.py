"""Scroll VK community audio page and save HTML snapshots."""

import logging
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.config import Config
from src.helpers.io import list_snapshots, read_page, write_page
from src.parsers.playlists import parse_playlists_page

log = logging.getLogger(__name__)


def scroll_playlists(driver: webdriver.Chrome, playlists_url: str, config: Config) -> None:
    """Navigate to VK audio page, scroll it, save snapshots to pages/playlists/."""
    log.info("Navigating to %s", playlists_url)
    try:
        driver.get(playlists_url)
    except Exception:  # noqa: BLE001
        log.warning("Page load timed out – continuing.")

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid], audio, [data-audio]"))
        )
    except Exception:  # noqa: BLE001
        log.warning("No audio elements found after 20 s – proceeding anyway.")

    playlists_dir = config.playlists_dir
    playlists_dir.mkdir(parents=True, exist_ok=True)

    scroll_index = 0
    no_new_at_bottom = 0

    log.info("Starting playlists scroll…")

    while True:
        html = driver.page_source
        write_page(playlists_dir / f"scroll_{scroll_index:04d}.html", html, config)

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

    log.info("Done scrolling playlists. %d snapshots saved.", scroll_index + 1)


def parse_playlists_snapshots(config: Config) -> list[dict]:
    """Parse playlists from existing pages/playlists/ snapshots (no browser)."""
    if not (snaps := list_snapshots(config.playlists_dir)):
        log.warning("No playlists snapshots found in %s", config.playlists_dir)
        return []

    log.info("Parsing %d playlists snapshots from %s", len(snaps), config.playlists_dir)

    seen_urls: set[str] = set()
    result: list[dict] = []
    for snap in snaps:
        for item in parse_playlists_page(read_page(snap)):
            url = item.get("url")
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            result.append(item)

    log.info("Parsed %d playlist items.", len(result))

    return result
