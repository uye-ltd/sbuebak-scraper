"""Per-post HTML download and comment collection."""

import logging
import time
from collections.abc import Iterator
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.config import Config
from src.helpers.io import page_exists, read_page, write_page
from src.models import Comment, Post
from src.parsers.posts import parse_comments

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Browser wait helpers
# ---------------------------------------------------------------------------


def _wait_for_comments(driver: webdriver.Chrome, timeout: float = 8) -> bool:
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-testid="wall_comments_comment_root"]')
            )
        )
        return True
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Comment expansion helpers
# ---------------------------------------------------------------------------


def _click_show_more_comments(driver: webdriver.Chrome, pause: float) -> int:
    """Repeatedly click 'show next comments' until none remain. Returns clicks made."""
    clicked = 0
    seen: set[str] = set()

    while clicked < 50:
        if not (btns := driver.find_elements(By.CSS_SELECTOR, '[data-testid="show_next_comments"]')):
            break
        
        btn_id = driver.execute_script("return arguments[0].outerHTML.substring(0, 80)", btns[0])
        if btn_id in seen:
            break
        
        seen.add(btn_id)
    
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", btns[0])
            btns[0].click()
            time.sleep(pause)
            clicked += 1
        except Exception:  # noqa: BLE001
            break

    return clicked


def _click_collapsed_threads(driver: webdriver.Chrome, pause: float) -> int:
    """Click collapsed reply-thread indicators so inline replies are rendered."""
    clicked = 0
    attempted: set[str] = set()

    while clicked < 100:
        threads = driver.find_elements(
            By.CSS_SELECTOR, '[data-testid="wall_comments_layout_thread"]'
        )
        expanded_one = False
        for thread in threads:
            if (fingerprint := thread.text[:60]) in attempted:
                continue
            
            inner = thread.find_elements(
                By.CSS_SELECTOR, '[data-testid="wall_comments_comment_root"]'
            )
            if inner:
                attempted.add(fingerprint)
                continue

            attempted.add(fingerprint)
        
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", thread)
                thread.click()
                time.sleep(pause)
                clicked += 1
                expanded_one = True
                break
            except Exception:  # noqa: BLE001
                continue

        if not expanded_one:
            break

    return clicked


# ---------------------------------------------------------------------------
# Per-post HTML download
# ---------------------------------------------------------------------------


def _post_html_path(post: Post, config: Config) -> Path:
    slug = (post.post_url or "unknown").rsplit("/", 1)[-1]

    return config.posts_dir / f"{slug}.html"


def _download_one(driver: webdriver.Chrome, post: Post, config: Config) -> bool:
    """Navigate to post_url, expand all comments, save full HTML. Returns True on success."""
    path = _post_html_path(post, config)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        driver.get(post.post_url)
    except Exception:  # noqa: BLE001
        log.warning("Page load timed out for %s – continuing.", post.post_url)

    has_comments = _wait_for_comments(driver, timeout=12)

    if has_comments:
        try:
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-testid="wall_comments_layout_thread"]')
                )
            )
        except Exception:  # noqa: BLE001
            pass

        more = _click_show_more_comments(driver, config.comment_pause_sec)
        threads = _click_collapsed_threads(driver, config.comment_pause_sec)
        if more or threads:
            log.debug("Expanded: %d pages, %d threads", more, threads)
    else:
        log.debug("No comment section on %s — saving page as-is.", post.post_url)

    write_page(path, driver.page_source, config)

    return True


def download_post_pages(driver: webdriver.Chrome, posts: list[Post], config: Config) -> None:
    """Download and save HTML for every post, skipping cached files."""
    eligible = [p for p in posts if p.post_url]
    to_download = [p for p in eligible if not page_exists(_post_html_path(p, config))]

    log.info(
        "Downloading HTML for %d posts (%d already cached, %d to fetch)…",
        len(eligible),
        len(eligible) - len(to_download),
        len(to_download),
    )

    fetch_i = 0
    for post in eligible:
        if not page_exists(_post_html_path(post, config)):
            fetch_i += 1
            log.info("[%d/%d][%d/%d] %s", fetch_i, len(eligible), fetch_i, len(to_download), post.post_url)
            _download_one(driver, post, config)
    
    log.info("Done → %s/", config.posts_dir)


def _fetch_comments(driver: webdriver.Chrome | None, post: Post, config: Config) -> list[Comment]:
    """Parse comments for a post; uses cached HTML when available."""
    if not post.post_url:
        return []

    path = _post_html_path(post, config)

    if page_exists(path):
        soup = BeautifulSoup(read_page(path), "lxml")
        return parse_comments(soup)

    if driver is None:
        log.warning("No cached page for %s and no browser — skipping.", post.post_url)
        return []

    if not _download_one(driver, post, config):
        return []

    soup = BeautifulSoup(read_page(path), "lxml")

    return parse_comments(soup)


# ---------------------------------------------------------------------------
# Comment collection phase (generator)
# ---------------------------------------------------------------------------


def collect_all_posts(
    driver: webdriver.Chrome | None, 
    posts: list[Post], 
    config: Config,
) -> Iterator[Post]:
    """
    Generator — yields every post with comment_list populated.

    Posts with 0 comments are yielded immediately.  For others: uses existing
    pages/posts/<slug>.html when present; downloads via browser otherwise
    (or skips with a warning if driver is None).
    """
    skipped = 0
    for p in posts:
        if p.comments == 0:
            p.comments_fetched = True
            skipped += 1
    if skipped:
        log.info("Skipping comment parsing for %d posts with 0 comments.", skipped)

    to_fetch = [p for p in posts if not p.comments_fetched]
    log.info("Fetching comments for %d posts…", len(to_fetch))

    fetch_count = 0
    for post in posts:
        if post.comments_fetched:
            yield post
            continue

        fetch_count += 1
        log.info(
            "[%d/%d] %s (expected %d comments)",
            fetch_count,
            len(to_fetch),
            post.post_url,
            post.comments,
        )
        comment_list = _fetch_comments(driver, post, config)
        total_c = sum(1 + len(c.replies) for c in comment_list)
        log.info(
            "  got %d comments (%d top-level, %d replies)",
            total_c,
            len(comment_list),
            total_c - len(comment_list),
        )

        post.comment_list = comment_list
        post.comments_fetched = True
    
        yield post

    log.info("Comments done.")
