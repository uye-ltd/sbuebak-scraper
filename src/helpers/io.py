"""Page I/O helpers: write/read HTML files with optional gzip compression."""

import gzip
from pathlib import Path

from src.config import Config

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _gz(path: Path) -> Path:
    """Return the .gz sibling of a plain .html path."""
    return path.parent / (path.name + ".gz")


def _snapshot_key(p: Path) -> str:
    """Normalise a snapshot path to a sort key, stripping .html and .html.gz."""
    name = p.name

    if name.endswith(".html.gz"):
        return name[:-8]
    if name.endswith(".html"):
        return name[:-5]
    
    return name


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_page(path: Path, html: str, config: Config) -> None:
    """Write an HTML page to disk; uses gzip if config.gzip_pages is True."""
    if config.gzip_pages:
        dest = _gz(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(dest, "wt", encoding="utf-8") as f:
            f.write(html)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")


def read_page(path: Path) -> str:
    """Read an HTML page; checks for a .gz sibling first, then falls back to plain."""
    gz = _gz(path)
    if gz.exists():
        with gzip.open(gz, "rt", encoding="utf-8") as f:
            return f.read()
    
    return path.read_text(encoding="utf-8")


def page_exists(path: Path) -> bool:
    """True if the page exists as plain HTML or as a gzipped file."""
    return path.exists() or _gz(path).exists()


def list_snapshots(directory: Path, pattern: str = "scroll_*") -> list[Path]:
    """
    Return snapshot paths sorted by name.

    Scans for both <pattern>.html and <pattern>.html.gz; when both exist for
    the same snapshot, the compressed file takes precedence.
    """
    seen: dict[str, Path] = {}
    for p in directory.glob(pattern + ".html"):
        seen[_snapshot_key(p)] = p
    for p in directory.glob(pattern + ".html.gz"):
        seen[_snapshot_key(p)] = p  # gz overwrites plain
    
    return [seen[k] for k in sorted(seen)]


def compress_pages(directory: Path) -> tuple[int, int]:
    """
    Recursively gzip every .html file under *directory*.

    Skips files that already have a .html.gz sibling.
    Deletes the original .html after successful compression.
    Returns (compressed, skipped).
    """
    compressed, skipped = 0, 0
    for html_path in sorted(directory.rglob("*.html")):
        gz_path = _gz(html_path)
        if gz_path.exists():
            skipped += 1
            continue
        with open(html_path, "rb") as src, gzip.open(gz_path, "wb") as dst:
            dst.write(src.read())
        html_path.unlink()
        compressed += 1
    
    return compressed, skipped


def decompress_pages(directory: Path) -> tuple[int, int]:
    """
    Recursively gunzip every .html.gz file under *directory*.

    Skips files whose plain .html sibling already exists.
    Deletes the .html.gz after successful decompression.
    Returns (decompressed, skipped).
    """
    decompressed = skipped = 0
    for gz_path in sorted(directory.rglob("*.html.gz")):
        html_path = gz_path.parent / gz_path.name[:-3]  # strip .gz
        if html_path.exists():
            skipped += 1
            continue
        with gzip.open(gz_path, "rb") as src, open(html_path, "wb") as dst:
            dst.write(src.read())
        gz_path.unlink()
        decompressed += 1
    
    return decompressed, skipped
