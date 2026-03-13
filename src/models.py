import csv
from dataclasses import dataclass, field


@dataclass
class Attachment:
    type: str  # "photo" | "video" | "audio" | "link" | "doc"
    url: str | None = None
    title: str | None = None
    artist: str | None = None  # audio
    duration: str | None = None  # audio

    def to_dict(self) -> dict:
        return {k: v for k, v in vars(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict) -> "Attachment":
        return cls(
            **{k: v for k, v in d.items() if k in ("type", "url", "title", "artist", "duration")}
        )


@dataclass
class Comment:
    id: str  # "userId_commentId" from VK DOM
    author: str
    author_url: str | None
    date_raw: str
    text: str
    likes: int
    replies: list["Comment"] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "author": self.author,
            "author_url": self.author_url,
            "date_raw": self.date_raw,
            "text": self.text,
            "likes": self.likes,
            "replies": [r.to_dict() for r in self.replies],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Comment":
        return cls(
            id=d.get("id", ""),
            author=d.get("author", ""),
            author_url=d.get("author_url"),
            date_raw=d.get("date_raw", ""),
            text=d.get("text", ""),
            likes=d.get("likes", 0),
            replies=[Comment.from_dict(r) for r in d.get("replies", [])],
        )


@dataclass
class Post:
    id: str  # full id e.g. "wall-12345_67890"
    author: str
    author_url: str | None
    date_raw: str
    timestamp: int | None
    text: str
    likes: int
    comments: int  # count from footer
    reposts: int
    views: int | None
    attachments: list[Attachment] = field(default_factory=list)
    post_url: str | None = None
    comment_list: list[Comment] = field(default_factory=list)
    comments_fetched: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "author": self.author,
            "author_url": self.author_url,
            "date_raw": self.date_raw,
            "timestamp": self.timestamp,
            "text": self.text,
            "likes": self.likes,
            "comments": self.comments,
            "reposts": self.reposts,
            "views": self.views,
            "attachments": [a.to_dict() for a in self.attachments],
            "post_url": self.post_url,
            "comments_fetched": self.comments_fetched,
            "comment_list": [c.to_dict() for c in self.comment_list],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Post":
        return cls(
            id=d.get("id", ""),
            author=d.get("author", ""),
            author_url=d.get("author_url"),
            date_raw=d.get("date_raw", ""),
            timestamp=d.get("timestamp"),
            text=d.get("text", ""),
            likes=d.get("likes", 0),
            comments=d.get("comments", 0),
            reposts=d.get("reposts", 0),
            views=d.get("views"),
            attachments=[Attachment.from_dict(a) for a in d.get("attachments", [])],
            post_url=d.get("post_url"),
            comment_list=[Comment.from_dict(c) for c in d.get("comment_list", [])],
            comments_fetched=d.get("comments_fetched", False),
        )

    def to_csv_row(self) -> dict:
        attachments_str = "; ".join(
            f"{a.type}:{a.artist} - {a.title}" if a.artist else f"{a.type}:{a.title or a.url}"
            for a in self.attachments
        )

        def flatten(comments: list[Comment], depth: int = 0) -> list[str]:
            rows = []
            for c in comments:
                prefix = "  " * depth
                rows.append(f"{prefix}{c.author}: {c.text}")
                rows.extend(flatten(c.replies, depth + 1))
            return rows

        return {
            "id": self.id,
            "author": self.author,
            "author_url": self.author_url or "",
            "date_raw": self.date_raw,
            "timestamp": self.timestamp or "",
            "text": self.text,
            "likes": self.likes,
            "comments": self.comments,
            "reposts": self.reposts,
            "views": self.views or "",
            "attachments": attachments_str,
            "post_url": self.post_url or "",
            "comment_list": " | ".join(flatten(self.comment_list)),
        }


@dataclass
class Subscriber:
    name: str
    url: str | None

    def to_dict(self) -> dict:
        return {"name": self.name, "url": self.url}


@dataclass
class WallData:
    community_slug: str
    subscribers_url: str
    playlists_url: str | None
    posts: list[Post] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "community_slug": self.community_slug,
            "subscribers_url": self.subscribers_url,
            "playlists_url": self.playlists_url,
            "posts": [p.to_dict() for p in self.posts],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WallData":
        return cls(
            community_slug=d.get("community_slug", ""),
            subscribers_url=d.get("subscribers_url", ""),
            playlists_url=d.get("playlists_url"),
            posts=[Post.from_dict(p) for p in d.get("posts", [])],
        )


CSV_FIELDS = [
    "id",
    "author",
    "author_url",
    "date_raw",
    "timestamp",
    "text",
    "likes",
    "comments",
    "reposts",
    "views",
    "attachments",
    "post_url",
    "comment_list",
]


def write_csv(posts: list[Post], path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(p.to_csv_row() for p in posts)
