"""Parse VK community members page HTML snapshots."""

import logging
import re

from bs4 import BeautifulSoup

from src.helpers.text import get_text
from src.models import Subscriber

log = logging.getLogger(__name__)

_PROFILE_RE = re.compile(r"^/(?:id\d+|[a-zA-Z][a-zA-Z0-9_.]{1,})$")
_BASE_SKIP_PATHS = {
    "/im",
    "/feed",
    "/settings",
    "/login",
    "/notifications",
    "/friends",
    "/groups",
    "/video",
    "/music",
    "/photos",
    "/wall",
}


def parse_subscribers_page(html: str, community_slug: str = "") -> list[Subscriber]:
    """Parse member cards from a VK community members page snapshot."""
    soup = BeautifulSoup(html, "lxml")
    skip = _BASE_SKIP_PATHS | ({f"/{community_slug}"} if community_slug else set())
    subscribers: list[Subscriber] = []
    seen: set[str] = set()

    container = (
        soup.find(attrs={"data-testid": "community_members"})
        or soup.find(attrs={"data-testid": "members_list"})
        or soup.find(id="list_members")
        or soup.body
    )
    if not container:
        return []

    for a in container.find_all("a", href=True):
        href = str(a.get("href", ""))
        if href in skip or not _PROFILE_RE.match(href):
            continue
        name = get_text(a)
        if not name or len(name) < 2:
            continue
        url = f"https://vk.com{href}"
        if url in seen:
            continue
        seen.add(url)
        subscribers.append(Subscriber(name=name, url=url))

    return subscribers
