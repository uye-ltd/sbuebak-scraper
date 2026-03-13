"""Serialise collected data to JSON and CSV."""

import json
import logging
from collections.abc import Iterable
from pathlib import Path

from src.models import Post, WallData, write_csv

log = logging.getLogger(__name__)


def save_wall(wall: WallData, json_path: Path, csv_path: Path) -> None:
    """Write wall.json and wall.csv."""
    json_path.parent.mkdir(parents=True, exist_ok=True)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(wall.to_dict(), f, ensure_ascii=False, indent=2)
    log.info("JSON saved → %s (%d posts)", json_path, len(wall.posts))

    write_csv(wall.posts, csv_path)
    log.info("CSV saved  → %s (%d posts)", csv_path, len(wall.posts))


def load_wall(json_path: Path) -> WallData:
    """Load wall.json into a WallData object."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    return WallData.from_dict(data)


def save_json(posts: Iterable[Post], path: Path) -> None:
    """Stream posts to a JSON array one by one — no full list held in memory.
    The array is always properly closed even if iteration is interrupted."""
    path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with open(path, "w", encoding="utf-8") as f:
        f.write("[\n")
        first = True
        try:
            for post in posts:
                if not first:
                    f.write(",\n")
                json.dump(post.to_dict(), f, ensure_ascii=False, indent=2)
                first = False
                count += 1
        finally:
            f.write("\n]")

    log.info("JSON saved → %s (%d posts)", path, count)
