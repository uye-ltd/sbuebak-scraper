# sbuebak-scraper

Scrapes wall posts (text, audio, photos, links), full comment trees, playlists, and subscribers from VK public communities (default: [uyebark](https://vk.com/uyebark)). Exports to JSON and CSV.

## Requirements

- Python ≥ 3.13
- [uv](https://docs.astral.sh/uv/)
- Google Chrome (Selenium manages the driver automatically)

## Setup

```bash
git clone <repo>
cd sbuebak-scraper
uv sync
```

## Usage

```
uv run scraper <command> [flags]
```

Commands must be run in order: `wall` first, then `posts` / `playlists` / `subscribers` (all three read `data/wall.json`).

Every command shares three phase-control flags:

| Flag | Description |
|---|---|
| `--no-scraping` | Skip browser; parse from existing `pages/` snapshots only |
| `--no-parsing` | Download HTML to `pages/` only; skip writing output JSON/CSV |
| `--gzip` | Save page snapshots as `.html.gz` (reads both formats automatically) |

---

### wall

Infinite-scrolls the community wall. Saves every post to `data/wall.json` and `data/wall.csv`. Also records the community's `subscribers_url` and `playlists_url` in `wall.json` for use by the other commands.

```bash
uv run scraper wall
uv run scraper wall --community-slug other_page
uv run scraper wall --gzip
uv run scraper wall --no-parsing     # download snapshots only
uv run scraper wall --no-scraping    # parse from existing pages/wall/ snapshots
```

A Chrome window opens — log in to VK manually, then press **Enter**.

| Flag | Default | Description |
|---|---|---|
| `--community-slug SLUG` | `uyebark` | VK community slug to scrape |
| `--output-dir DIR` | `data/` | Directory for JSON and CSV output |
| `--pages-dir DIR` | `pages/` | Directory for HTML snapshots |
| `--max-posts N` | no limit | Stop after N posts |
| `--scroll-pause SEC` | `3.0` | Seconds to wait after each scroll |
| `--max-unchanged N` | `6` | Consecutive at-bottom scrolls with no new posts before stopping |
| `--gzip` | — | Save snapshots as `.html.gz` |
| `--no-scraping` | — | Parse from existing `pages/wall/` only |
| `--no-parsing` | — | Download snapshots only, skip writing `wall.json` |

---

### posts

Fetches the full comment tree for every post with `comments > 0`. Uses cached HTML from `pages/posts/` when available — only opens the browser for posts not yet downloaded. Writes `data/posts.json`.

Requires `data/wall.json` (run `wall` first).

```bash
uv run scraper posts
uv run scraper posts --no-scraping   # parse from existing pages/posts/ only
uv run scraper posts --no-parsing    # download post pages only
uv run scraper posts --gzip
```

| Flag | Default | Description |
|---|---|---|
| `--comment-pause SEC` | `1.5` | Wait when expanding comment threads |
| `--output-dir DIR` | `data/` | — |
| `--pages-dir DIR` | `pages/` | — |
| `--gzip` | — | Save newly downloaded pages as `.html.gz` |
| `--no-scraping` | — | Parse comments from cached `pages/posts/` only (skip missing) |
| `--no-parsing` | — | Download post pages only, skip writing `posts.json` |

---

### playlists

Scrolls the community audio page (`https://vk.com/audios-{id}`) and parses playlist cards. Writes `data/playlists.json`.

Requires `data/wall.json` (for `playlists_url`).

```bash
uv run scraper playlists
uv run scraper playlists --no-scraping   # parse from existing pages/playlists/ only
uv run scraper playlists --no-parsing    # download snapshots only
```

> **Note:** The playlist parser (`src/parsers/playlists.py`) uses best-guess `data-testid` selectors. If `playlists.json` comes back empty, inspect `pages/playlists/scroll_0000.html` and update the selectors.

| Flag | Default | Description |
|---|---|---|
| `--output-dir DIR` | `data/` | — |
| `--pages-dir DIR` | `pages/` | — |
| `--gzip` | — | Save snapshots as `.html.gz` |
| `--no-scraping` | — | Parse from existing `pages/playlists/` only |
| `--no-parsing` | — | Download snapshots only, skip writing `playlists.json` |

---

### subscribers

Scrolls the community members page and saves member names and profile links. Writes `data/subscribers.json`.

Requires `data/wall.json` (for `subscribers_url`).

```bash
uv run scraper subscribers
uv run scraper subscribers --no-scraping   # parse from existing pages/subscribers/ only
uv run scraper subscribers --no-parsing    # download snapshots only
```

Output: list of `{ name, url }` objects.

| Flag | Default | Description |
|---|---|---|
| `--output-dir DIR` | `data/` | — |
| `--pages-dir DIR` | `pages/` | — |
| `--gzip` | — | Save snapshots as `.html.gz` |
| `--no-scraping` | — | Parse from existing `pages/subscribers/` only |
| `--no-parsing` | — | Download snapshots only, skip writing `subscribers.json` |

---

### gzip / gunzip

Bulk-compress or decompress all page snapshots under `pages/`.

```bash
uv run scraper gzip    # .html  → .html.gz  (deletes originals)
uv run scraper gunzip  # .html.gz → .html   (deletes originals)
```

Both commands recurse into all subdirectories and skip files whose counterpart already exists.

| Flag | Default | Description |
|---|---|---|
| `--pages-dir DIR` | `pages/` | Root directory to process |

---

## Output

| Path | Contents |
|---|---|
| `data/wall.json` | WallData: `community_slug`, `subscribers_url`, `playlists_url`, `posts` array |
| `data/wall.csv` | Flat CSV of posts |
| `data/posts.json` | Posts with full nested `comment_list` trees |
| `data/playlists.json` | Playlist records from the community audio page |
| `data/subscribers.json` | Community member names and profile URLs |
| `pages/wall/scroll_NNNN.html[.gz]` | Wall HTML snapshot per scroll step |
| `pages/posts/<slug>.html[.gz]` | Post page HTML used by `posts` command |
| `pages/playlists/scroll_NNNN.html[.gz]` | Audio page snapshot per scroll step |
| `pages/subscribers/scroll_NNNN.html[.gz]` | Members page snapshot per scroll step |

### wall.json structure

```json
{
  "community_slug": "uyebark",
  "subscribers_url": "https://vk.com/uyebark?act=members",
  "playlists_url": "https://vk.com/audios-109302706",
  "posts": [
    {
      "id": "wall-109302706_3860",
      "author": "...",
      "post_url": "https://vk.com/wall-109302706_3860",
      "comments": 12,
      "attachments": [...],
      ...
    }
  ]
}
```

### Comment fields (nested tree, max 2 levels)

```json
{
  "id": "12626382_3899",
  "author": "Юра Габуев",
  "author_url": "https://vk.com/ygabuev",
  "date_raw": "18 авг 2020",
  "text": "упс",
  "likes": 1,
  "replies": [...]
}
```

## Resuming interrupted runs

- **wall** — if interrupted, run `wall --no-scraping` to parse whatever snapshots were saved to `pages/wall/`
- **posts** — already-downloaded `pages/posts/*.html[.gz]` files are reused automatically; run with `--no-scraping` to skip any posts without cached HTML
- **subscribers / playlists** — run with `--no-scraping` to parse from existing snapshots

## Development

```bash
uv run ruff check src/ main.py   # lint
uv run ruff format src/ main.py  # format
```
