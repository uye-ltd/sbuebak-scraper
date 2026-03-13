"""Parse VK wall post elements from a page HTML snapshot."""

import logging
import re

from bs4 import BeautifulSoup, Tag

from src.helpers.text import get_int, get_text
from src.models import Attachment, Post

log = logging.getLogger(__name__)

_OWNER_RE = re.compile(r"wall-(\d+)_")


def _parse_attachments(post_el: Tag) -> list[Attachment]:
    attachments: list[Attachment] = []
    content = post_el.find(attrs={"data-testid": "post-content-container"}) or post_el

    # --- Audio: single track ---
    track_title_el = content.find(attrs={"data-testid": "music-track-overlay-badge-title"})
    if track_title_el:
        raw = get_text(track_title_el)
        parts = raw.split(" \u2014 ", 1)  # em dash
        artist = parts[0].strip() if len(parts) == 2 else None
        title = parts[1].strip() if len(parts) == 2 else raw
        audio_link = content.find("a", href=lambda h: h and str(h).startswith("/audio"))
        url = f"https://vk.com{audio_link['href']}" if audio_link else None

        attachment = Attachment(type="audio", artist=artist, title=title, url=url)
        attachments.append(attachment)

    # --- Audio: playlist badge ---
    elif content.find(attrs={"data-testid": "musicbadge"}):
        if info_el := content.find(attrs={"data-testid": "musicplaylistoverlaybadge_infobutton"}):
            lines = [ln.strip() for ln in get_text(info_el).splitlines() if ln.strip()]
            raw = lines[0] if lines else get_text(info_el)
            parts = raw.split(" \u2014 ", 1)
            artist = parts[0].strip() if len(parts) == 2 else None
            title = parts[1].strip() if len(parts) == 2 else raw

            attachment = Attachment(type="audio", artist=artist, title=title)
            attachments.append(attachment)

    # --- Video ---
    for vid_link in content.find_all("a", attrs={"data-video": True}):
        href = vid_link.get("href", "")
        title = vid_link.get("aria-label") or None
        url = f"https://vk.com{href}" if href else None

        attachment = Attachment(type="video", url=url, title=title)
        attachments.append(attachment)

    # --- Photos ---
    seen_photo_urls: set[str] = set()
    for a in content.find_all("a", href=lambda h: h and str(h).startswith("/photo")):
        if (href := str(a.get("href", ""))) not in seen_photo_urls:
            seen_photo_urls.add(href)
    
            attachment = Attachment(type="photo", url=f"https://vk.com{href}")
            attachments.append(attachment)

    # --- External links ---
    for a in content.find_all("a", href=True):
        href = str(a.get("href", ""))
        if href.startswith("http") and "vk.com" not in href:
            title = get_text(a) or None

            attachment = Attachment(type="link", url=href, title=title)
            attachments.append(attachment)

    return attachments


def parse_post(post_el: Tag) -> Post | None:
    try:
        post_id: str = post_el.get("data-post-id", "")  # type: ignore[assignment]

        author_el = post_el.find(attrs={"data-testid": "post-header-title"})
        author = get_text(author_el)
        author_href = author_el.get("href") if author_el else None
        author_url = f"https://vk.com{author_href}" if author_href else None

        date_el = post_el.find(attrs={"data-testid": "post_date_block_preview"})
        date_raw = get_text(date_el)
        date_href = date_el.get("href") if date_el else None
        post_url = f"https://vk.com{date_href}" if date_href else None

        text_el = (
            post_el.find(attrs={"data-testid": "showmoretext-in-expanded"})
            or post_el.find(attrs={"data-testid": "showmoretext-in"})
            or post_el.find(attrs={"data-testid": "post-content-container"})
        )
        text = get_text(text_el)

        likes = get_int(post_el.find(attrs={"data-testid": "post_footer_action_like"}))
        comments = get_int(post_el.find(attrs={"data-testid": "post_footer_action_comment"}))
        reposts = get_int(post_el.find(attrs={"data-testid": "post_footer_action_share"}))
        attachments = _parse_attachments(post_el)

        return Post(
            id=post_id,
            author=author,
            author_url=author_url,
            date_raw=date_raw,
            timestamp=None,
            text=text,
            likes=likes,
            comments=comments,
            reposts=reposts,
            views=None,
            attachments=attachments,
            post_url=post_url,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed on post %s: %s", post_el.get("data-post-id", "?"), exc)
        return None


def parse_page(html: str) -> list[Post]:
    """Return all top-level posts from a full page HTML snapshot."""
    soup = BeautifulSoup(html, "lxml")

    posts: list[Post] = []
    for el in soup.select('div[data-post-id][data-post-nesting-lvl="0"]'):
        post = parse_post(el)
        if post and post.id:
            posts.append(post)

    return posts


def extract_community_id(posts: list[Post]) -> str | None:
    """Extract numeric community ID from post IDs (format: wall-NNNNNN_MM)."""
    for post in posts:
        if m := _OWNER_RE.search(post.id or ""):
            return m.group(1)
    
    return None
