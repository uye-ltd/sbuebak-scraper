# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python web scraper targeting VK.ru public communities (default: `uyebark`, https://vk.com/uyebark). Extracts all wall posts (text, audio, photos, links), full comment trees (with nested replies), playlists, and subscribers via Selenium + BeautifulSoup4. Exports to JSON and CSV.

## Commands

```bash
# Install / sync dependencies
uv sync

# 1. Scrape community wall → data/wall.json + data/wall.csv
uv run scraper wall
uv run scraper wall --community-slug other_page
uv run scraper wall --gzip            # save snapshots as .html.gz
uv run scraper wall --no-parsing      # download HTML only, skip wall.json
uv run scraper wall --no-scraping     # parse from existing pages/wall/ only

# 2. Fetch comment trees (requires wall.json) → data/posts.json
uv run scraper posts
uv run scraper posts --no-scraping    # parse from existing pages/posts/ only
uv run scraper posts --no-parsing     # download post pages only

# 3. Scrape community playlists (requires wall.json) → data/playlists.json
uv run scraper playlists
uv run scraper playlists --no-scraping
uv run scraper playlists --no-parsing

# 4. Scrape community members (requires wall.json) → data/subscribers.json
uv run scraper subscribers
uv run scraper subscribers --no-scraping
uv run scraper subscribers --no-parsing

# Bulk compress / decompress pages/
uv run scraper compress               # .html → .html.gz, deletes originals
uv run scraper uncompress             # .html.gz → .html, deletes originals

# Help
uv run scraper --help
uv run scraper wall --help
uv run scraper posts --help

# Lint / format
uv run ruff check src/ main.py
uv run ruff format src/ main.py
```

## Structure

```
main.py          # CLI entry point — subcommands: wall, posts, playlists,
                 #   subscribers, gzip, gunzip
src/
├── config.py    # Config dataclass (URLs, paths, timeouts, limits, gzip_pages)
├── browser.py   # Selenium WebDriver factory + manual-login helper
├── models.py    # Post / Attachment / Comment / Subscriber / WallData dataclasses
├── output.py    # save_wall, load_wall, save_json (streaming), save_csv
├── parser.py    # Re-export shim → src.parsers.*
├── scraper.py   # Re-export shim → src.scrapers.*
├── helpers/
│   ├── text.py  # get_text, get_int, comment_level (shared BS4 helpers)
│   └── io.py    # write_page, read_page, page_exists, list_snapshots,
│                #   compress_pages, decompress_pages
├── parsers/
│   ├── wall.py         # parse_page, parse_post, extract_community_id
│   ├── posts.py        # parse_comments
│   ├── playlists.py    # parse_playlists_page(html) → list[dict]
│   └── subscribers.py  # parse_subscribers_page(html) → list[Subscriber]
└── scrapers/
    ├── wall.py         # scroll_wall, parse_wall_snapshots
    ├── posts.py        # download_post_pages, collect_all_posts
    ├── playlists.py    # scroll_playlists, parse_playlists_snapshots
    └── subscribers.py  # scroll_subscribers, parse_subscribers_snapshots
```

`main.py` and all modules within `src/` use absolute imports (`from src.config import Config`).

## Data flow

Every command has two phases, each independently skippable via `--no-scraping` / `--no-parsing`.

### `wall` command

**Scraping** (`scroll_wall`):
1. Navigates to `https://vk.com/{community_slug}`, waits for `div[data-post-id]`
2. Infinite scroll loop: captures `page_source` → `parse_page(html)` → deduplicates in-memory dict → saves snapshot to `pages/wall/scroll_NNNN.html[.gz]`
3. Stops when at page bottom AND no new posts for `max_unchanged_scrolls` consecutive scrolls (or `max_posts` reached)

**Parsing**: parses all snapshots, builds `WallData` with `subscribers_url`, `playlists_url` (derived from community_id extracted from post IDs), and `posts` array. Writes `data/wall.json` + `data/wall.csv`.

`--no-scraping`: calls `parse_wall_snapshots` — reads from existing `pages/wall/` only.

### `posts` command

Requires `data/wall.json`.

**Scraping** (`download_post_pages`): for each post with `comments > 0`, navigates to `post_url`, expands all comment threads, saves full HTML to `pages/posts/<slug>.html[.gz]`.

**Parsing** (`collect_all_posts` generator → `save_json` streaming): reads each cached HTML, calls `parse_comments`, yields Post with `comment_list` populated. Streams to `data/posts.json`.

`--no-scraping`: parses from existing `pages/posts/` only (skips posts without cached HTML).

### `playlists` command

Requires `data/wall.json` (for `playlists_url = https://vk.com/audios-{community_id}`).

**Scraping** (`scroll_playlists`): scrolls audio page, saves snapshots to `pages/playlists/`.
**Parsing** (`parse_playlists_snapshots`): reads snapshots, returns `list[dict]`, writes `data/playlists.json`.

### `subscribers` command

Requires `data/wall.json` (for `subscribers_url = https://vk.com/{slug}?act=members`).

**Scraping** (`scroll_subscribers`): scrolls members modal, saves snapshots to `pages/subscribers/`.
**Parsing** (`parse_subscribers_snapshots`): reads snapshots, deduplicates by URL, writes `data/subscribers.json`.

### `gzip` / `gunzip` commands

`compress_pages` / `decompress_pages` from `helpers/io.py` — `rglob` the pages directory, convert each file, delete the original. Skip files whose counterpart already exists.

## Key implementation details

**Login**: all scraping commands always prompt for manual VK login via `wait_for_manual_login`. Browser opens to `https://vk.com/login`; user presses ENTER after authenticating.

**No cache.json**: post data is not cached mid-run. If wall scraping is interrupted, existing `pages/wall/` snapshots can be parsed via `--no-scraping`.

**wall.json structure**:
```json
{
  "community_slug": "uyebark",
  "subscribers_url": "https://vk.com/uyebark?act=members",
  "playlists_url": "https://vk.com/audios-109302706",
  "posts": [...]
}
```
`playlists_url` is `None` if no post IDs were found (community_id couldn't be extracted).

**community_id extraction**: post `data-post-id` attributes have format `wall-NNNNNN_MM`. Regex `wall-(\d+)_` captures the numeric group ID used to build `audios-NNNNNN`.

**Page I/O (`helpers/io.py`):**
- `write_page(path, html, config)` — writes `.html` or `.html.gz` based on `config.gzip_pages`
- `read_page(path)` — checks for `.gz` sibling first, falls back to plain; transparent to callers
- `page_exists(path)` — returns True for either variant
- `list_snapshots(dir, pattern)` — globs both extensions, compressed takes precedence when both exist

**Performance:**
- `page_load_strategy = "none"` — `driver.get()` returns immediately; waiting done via explicit `WebDriverWait`
- `implicit_wait = 0` — `find_elements` returns immediately when no elements found; avoids 10s blocking per call

**Click safety (with `implicit_wait=0`):**
- `_click_show_more_comments`: fingerprints each button by `outerHTML.substring(0,80)`; stops if same button seen twice. Hard cap: 50 clicks.
- `_click_collapsed_threads`: fingerprints each thread by `thread.text[:60]`; once attempted, never clicked again. Hard cap: 100 clicks.

**Comment parsing (`parse_comments`):**
- Finds all `wall_comments_comment_root` elements recursively (not just direct children)
- Determines nesting level by walking each element's ancestor chain to find the nearest `--comment-layout-level` CSS variable (`0` = top-level, `1` = reply)
- Handles both VK's flat layout (reply wrappers as siblings) and nested layout
- Deduplicates by comment `id`

**Generators / streaming:**
- `collect_all_posts` is a generator (`Iterator[Post]`) — yields every post as processed
- `save_json` accepts `Iterable[Post]` and streams to JSON array one post at a time; `finally` always closes the array even on interrupt

**Playlists parser**: selectors in `parsers/playlists.py` are best-guess — inspect `pages/playlists/` HTML and update `data-testid` values after first scrape.

## Models

```
WallData
├── community_slug, subscribers_url, playlists_url
└── posts: list[Post]

Post
├── id, author, author_url, date_raw, timestamp
├── text, likes, comments (count), reposts, views
├── attachments: list[Attachment]   # photo / audio / video / link
├── post_url, comments_fetched
└── comment_list: list[Comment]     # populated by posts command only

Comment                              # tree — VK has max 2 levels
├── id, author, author_url, date_raw
├── text, likes
└── replies: list[Comment]

Attachment
└── type, url, title, artist, duration

Subscriber
└── name, url
```

All dataclasses implement `to_dict()` and `from_dict()` for JSON serialisation.

## Logging

All output uses Python's `logging` module (configured in `main.py`). Each module has `log = logging.getLogger(__name__)`. All calls use `%s`-style lazy formatting.

## Output directories

| Path | Contents |
|---|---|
| `data/wall.json` | WallData (slug, URLs, posts array) from `wall` command |
| `data/wall.csv` | Flat CSV of posts |
| `data/posts.json` | Posts with full nested `comment_list` from `posts` command |
| `data/playlists.json` | Playlist records from `playlists` command |
| `data/subscribers.json` | Community member names and URLs from `subscribers` command |
| `pages/wall/scroll_NNNN.html[.gz]` | Wall HTML snapshot per scroll step |
| `pages/posts/<slug>.html[.gz]` | Post page HTML, e.g. `wall-109302706_3860.html` |
| `pages/playlists/scroll_NNNN.html[.gz]` | Audio page snapshot per scroll step |
| `pages/subscribers/scroll_NNNN.html[.gz]` | Members page snapshot per scroll step |

## VK DOM selectors (verified 2026-03)

VK uses a React/vkui frontend — use `data-testid` / `data-post-id` attributes, **never** class names (auto-generated hashes).

**Posts**

| Field | Selector |
|---|---|
| Post container | `div[data-post-id][data-post-nesting-lvl="0"]` |
| Post ID | `data-post-id` attribute |
| Author | `a[data-testid="post-header-title"]` |
| Date & post URL | `a[data-testid="post_date_block_preview"]` |
| Text | `showmoretext-in-expanded` → `showmoretext-in` → `post-content-container` |
| Likes / comments / reposts | `post_footer_action_like/comment/share` |
| Audio (track) | `music-track-overlay-badge-title` (text: `"ARTIST — TITLE"`) |
| Audio (playlist) | `musicplaylistoverlaybadge_infobutton` |
| Audio URL | `a[href^="/audio"]` within content |
| Video | `a[data-video]` — `data-video` = VK ID, `aria-label` = title |
| Photo | `a[href^="/photo"]` within content |

**Comments** (parsed from `pages/posts/<slug>.html[.gz]`)

| Field | Selector |
|---|---|
| Comments root | `div[data-testid="wall_comments_layout_root"]` |
| Top-level comment | `div[data-testid="wall_comments_comment_root"]` (has `id="userId_commentId"`) |
| Reply comment | `div[data-testid="wall_comments_comment_in_thread"]` (has `id="userId_commentId"`) |
| Author name | `div[data-testid="comment-owner"]` |
| Author URL | `a[data-testid="comment-avatar"][href]` |
| Date | `a[data-testid="wall_comment_date"]` |
| Text | `showmoretext-in-expanded` → `showmoretext-in` → `comment-text` |
| Likes | `div[data-testid="comment-like"]` |
| Nesting level | CSS var `--comment-layout-level` on nearest styled ancestor (`0` = top, `1` = reply) |
| More comments | `div[data-testid="show_next_comments"]` (click to paginate) |
| Collapsed thread | `div[data-testid="wall_comments_layout_thread"]` (click to expand replies) |
