"""Parse comment trees from a VK post page HTML snapshot."""

import logging

from bs4 import BeautifulSoup, Tag

from src.helpers.text import comment_level, get_int, get_text
from src.models import Comment

log = logging.getLogger(__name__)


def _nesting_level(comment_el: Tag, root: Tag) -> int:
    """
    Walk up from a comment element to root to find the nearest ancestor carrying
    a --comment-layout-level CSS variable.  Returns 0 if none found.
    """
    for ancestor in comment_el.parents:
        if ancestor is root:
            break

        lvl = comment_level(ancestor)
        if lvl > 0:
            return lvl
    
    return 0


def _parse_single_comment(comment_el: Tag) -> Comment | None:
    try:
        comment_id: str = comment_el.get("id", "")  # type: ignore[assignment]

        avatar_el = comment_el.find(attrs={"data-testid": "comment-avatar"})
        author_href = avatar_el.get("href") if avatar_el else None
        author_url = f"https://vk.com{author_href}" if author_href else None

        owner_el = comment_el.find(attrs={"data-testid": "comment-owner"})
        author = get_text(owner_el)

        date_el = comment_el.find(attrs={"data-testid": "wall_comment_date"})
        date_raw = get_text(date_el)

        text_el = (
            comment_el.find(attrs={"data-testid": "showmoretext-in-expanded"})
            or comment_el.find(attrs={"data-testid": "showmoretext-in"})
            or comment_el.find(attrs={"data-testid": "comment-text"})
        )
        text = get_text(text_el)

        like_el = comment_el.find(attrs={"data-testid": "comment-like"})
        likes = get_int(like_el)

        return Comment(
            id=comment_id,
            author=author,
            author_url=author_url,
            date_raw=date_raw,
            text=text,
            likes=likes,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed on comment %s: %s", comment_el.get("id", "?"), exc)
        return None


def parse_comments(container: Tag | BeautifulSoup) -> list[Comment]:
    """
    Parse a full comment tree from a post page or post element.

    Finds ALL wall_comments_comment_root (top-level) and
    wall_comments_comment_in_thread (reply) elements, determines each one's
    nesting level, and builds the parent→replies tree.  Deduplicates by id.
    """
    if not (root := container.find(attrs={"data-testid": "wall_comments_layout_root"})):
        return []

    top_level: list[Comment] = []
    last_top: Comment | None = None
    seen_ids: set[str] = set()

    _COMMENT_TESTIDS = {"wall_comments_comment_root", "wall_comments_comment_in_thread"}
    for comment_el in root.find_all(lambda t: t.get("data-testid") in _COMMENT_TESTIDS):
        cid: str = comment_el.get("id", "")  # type: ignore[assignment]
        if cid and (cid in seen_ids):
            continue
        if cid:
            seen_ids.add(cid)

        if (comment := _parse_single_comment(comment_el)) is None:
            continue

        level = _nesting_level(comment_el, root)
        if level == 0:
            top_level.append(comment)
            last_top = comment
        elif last_top is not None:
            last_top.replies.append(comment)

    return top_level
