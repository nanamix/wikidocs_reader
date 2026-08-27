"""Connection and schema lifecycle for the plugin-owned database."""
from __future__ import annotations
import sqlite3
from pathlib import Path
SCHEMA_VERSION = 2
class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn
    def migrate(self) -> None:
        with self.connect() as conn:
            conn.executescript('''
            CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS wikidocs_cache (cache_key TEXT PRIMARY KEY, value TEXT NOT NULL, expires_at REAL NOT NULL, created_at REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_cache_expires ON wikidocs_cache(expires_at);
            CREATE TABLE IF NOT EXISTS wikidocs_books (
                id INTEGER PRIMARY KEY AUTOINCREMENT, wikidocs_book_id INTEGER NOT NULL UNIQUE,
                title TEXT NOT NULL, author TEXT, description TEXT, cover_url TEXT, url TEXT,
                page_count INTEGER NOT NULL DEFAULT 0, synced_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS wikidocs_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, wikidocs_page_id INTEGER NOT NULL UNIQUE,
                book_id INTEGER NOT NULL, parent_id INTEGER, title TEXT NOT NULL,
                page_order INTEGER NOT NULL DEFAULT 0, content_html TEXT, url TEXT, synced_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(book_id) REFERENCES wikidocs_books(id) ON DELETE CASCADE);
            CREATE INDEX IF NOT EXISTS idx_pages_book_order ON wikidocs_pages(book_id, page_order);
            CREATE TABLE IF NOT EXISTS wikidocs_user_books (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, book_id INTEGER NOT NULL,
                added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, book_id), FOREIGN KEY(book_id) REFERENCES wikidocs_books(id) ON DELETE CASCADE);
            CREATE INDEX IF NOT EXISTS idx_user_books_user ON wikidocs_user_books(user_id, updated_at DESC);
            CREATE TABLE IF NOT EXISTS wikidocs_reading_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, book_id INTEGER NOT NULL,
                page_id INTEGER, position REAL NOT NULL DEFAULT 0, pages_read INTEGER NOT NULL DEFAULT 0,
                total_pages INTEGER NOT NULL DEFAULT 0, is_completed INTEGER NOT NULL DEFAULT 0,
                last_read_at TEXT, completed_at TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, book_id), FOREIGN KEY(book_id) REFERENCES wikidocs_books(id) ON DELETE CASCADE,
                FOREIGN KEY(page_id) REFERENCES wikidocs_pages(id) ON DELETE SET NULL);
            CREATE INDEX IF NOT EXISTS idx_progress_user_last_read ON wikidocs_reading_progress(user_id, last_read_at DESC);
            ''')
            row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            if row is None: conn.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
            elif row['version'] == 1: conn.execute('UPDATE schema_version SET version=?', (SCHEMA_VERSION,))
            elif row['version'] != SCHEMA_VERSION: raise RuntimeError(f"Unsupported schema version: {row['version']}")
