"""Parse VK community audio page HTML snapshots.

NOTE: VK's audio page is heavily React-rendered. Selectors below are best-guess
and may need adjustment after inspecting actual page HTML.
"""

import logging

from bs4 import BeautifulSoup

log = logging.getLogger(__name__)


def parse_playlists_page(html: str) -> list[dict]:
    """Parse playlist cards from a VK community audio page snapshot."""
    soup = BeautifulSoup(html, "lxml")
    playlists: list[dict] = []
    seen_urls: set[str] = set()

    # VK audio page playlist cards — selectors need verification against live HTML
    for card in soup.find_all(attrs={"data-testid": "music_playlist"}):
        title_el = card.find(attrs={"data-testid": "music_playlist_title"})
        count_el = card.find(attrs={"data-testid": "music_playlist_count"})
        link_el = card.find("a", href=lambda h: h and "/playlist/" in str(h))

        url = f"https://vk.com{link_el['href']}" if link_el else None
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)

        playlists.append(
            {
                "title": title_el.get_text(strip=True) if title_el else None,
                "count": count_el.get_text(strip=True) if count_el else None,
                "url": url,
            }
        )

    if not playlists:
        log.warning(
            "No playlist cards found — VK may have changed its DOM. "
            "Inspect pages/playlists/ HTML and update selectors in parsers/playlists.py."
        )

    return playlists
