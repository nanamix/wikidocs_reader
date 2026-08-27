"""Pure domain models."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True, slots=True)
class Book:
    wikidocs_book_id: int
    title: str
    author: str | None = None
    description: str | None = None
    cover_url: str | None = None
    url: str | None = None
    page_count: int = 0

@dataclass(frozen=True, slots=True)
class Page:
    wikidocs_page_id: int
    book_id: int
    title: str
    page_order: int = 0
    parent_id: int | None = None
    content_html: str | None = None
    url: str | None = None

@dataclass(frozen=True, slots=True)
class ReadingProgress:
    user_id: int
    book_id: int
    page_id: int | None
    position: float
    pages_read: int
    total_pages: int
    is_completed: bool
    last_read_at: datetime | None = None
    completed_at: datetime | None = None
