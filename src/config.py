from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    # Community
    community_slug: str = "uyebark"

    # Directories
    output_dir: Path = field(default_factory=lambda: Path("data"))
    pages_dir: Path = field(default_factory=lambda: Path("pages"))

    # Scroll behaviour (wall + subscribers + playlists)
    scroll_pause_sec: float = 3.0
    max_unchanged_scrolls: int = 6

    # Comment fetching (posts)
    comment_pause_sec: float = 0.8

    # Limits
    max_posts: int | None = None

    # Storage
    gzip_pages: bool = False

    # Browser
    headless: bool = False
    window_size: tuple[int, int] = (1440, 900)
    implicit_wait_sec: int = 0

    def __post_init__(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pages_dir.mkdir(parents=True, exist_ok=True)

    # URLs
    @property
    def target_url(self) -> str:
        return f"https://vk.com/{self.community_slug}"

    @property
    def login_url(self) -> str:
        return "https://vk.com/login"

    # Pages directories
    @property
    def wall_dir(self) -> Path:
        return self.pages_dir / "wall"

    @property
    def posts_dir(self) -> Path:
        return self.pages_dir / "posts"

    @property
    def playlists_dir(self) -> Path:
        return self.pages_dir / "playlists"

    @property
    def subscribers_dir(self) -> Path:
        return self.pages_dir / "subscribers"

    # Output files
    @property
    def wall_json(self) -> Path:
        return self.output_dir / "wall.json"

    @property
    def wall_csv(self) -> Path:
        return self.output_dir / "wall.csv"

    @property
    def posts_json(self) -> Path:
        return self.output_dir / "posts.json"

    @property
    def playlists_json(self) -> Path:
        return self.output_dir / "playlists.json"

    @property
    def subscribers_json(self) -> Path:
        return self.output_dir / "subscribers.json"
