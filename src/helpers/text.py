"""DOM text / number extraction utilities shared across parsers."""

import re

from bs4 import Tag


def get_text(tag: Tag | None) -> str:
    if tag is None:
        return ""
    return tag.get_text(separator=" ", strip=True)


def get_int(tag: Tag | None) -> int:
    if tag is None:
        return 0
    raw = tag.get_text(strip=True).replace("\u00a0", "").replace(" ", "").replace(",", "")
    try:
        return int(raw)
    except ValueError:
        return 0


def comment_level(wrapper: Tag) -> int:
    """Extract --comment-layout-level CSS variable value from a wrapper div."""
    style = wrapper.get("style") or ""
    m = re.search(r"--comment-layout-level:\s*(\d+)", str(style))
    return int(m.group(1)) if m else 0
