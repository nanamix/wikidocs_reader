"""Plugin schema declarations executed exclusively through the Core DB gateway."""
SCHEMA = [
'''CREATE TABLE IF NOT EXISTS wikidocs_cache (cache_key VARCHAR(255) PRIMARY KEY, value TEXT NOT NULL, expires_at DOUBLE PRECISION NOT NULL, created_at DOUBLE PRECISION NOT NULL)''',
'''CREATE INDEX IF NOT EXISTS idx_wikidocs_cache_expires ON wikidocs_cache(expires_at)''',
'''CREATE TABLE IF NOT EXISTS wikidocs_books (id BIGINT PRIMARY KEY, wikidocs_book_id BIGINT NOT NULL UNIQUE, title TEXT NOT NULL, author TEXT, description TEXT, cover_url TEXT, url TEXT, page_count INTEGER NOT NULL DEFAULT 0, synced_at TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''',
'''CREATE TABLE IF NOT EXISTS wikidocs_pages (id BIGINT PRIMARY KEY, wikidocs_page_id BIGINT NOT NULL UNIQUE, book_id BIGINT NOT NULL, parent_id BIGINT, title TEXT NOT NULL, page_order INTEGER NOT NULL DEFAULT 0, content_html TEXT, url TEXT, synced_at TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(book_id) REFERENCES wikidocs_books(id) ON DELETE CASCADE)''',
'''CREATE INDEX IF NOT EXISTS idx_wikidocs_pages_book_order ON wikidocs_pages(book_id,page_order,id)''',
'''CREATE TABLE IF NOT EXISTS wikidocs_user_books (user_id BIGINT NOT NULL, book_id BIGINT NOT NULL, added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id,book_id), FOREIGN KEY(book_id) REFERENCES wikidocs_books(id) ON DELETE CASCADE)''',
'''CREATE INDEX IF NOT EXISTS idx_wikidocs_user_books_user ON wikidocs_user_books(user_id,updated_at)''',
'''CREATE TABLE IF NOT EXISTS wikidocs_reading_progress (user_id BIGINT NOT NULL, book_id BIGINT NOT NULL, page_id BIGINT, position DOUBLE PRECISION NOT NULL DEFAULT 0, pages_read INTEGER NOT NULL DEFAULT 0, total_pages INTEGER NOT NULL DEFAULT 0, is_completed INTEGER NOT NULL DEFAULT 0, last_read_at TEXT, completed_at TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id,book_id), FOREIGN KEY(book_id) REFERENCES wikidocs_books(id) ON DELETE CASCADE, FOREIGN KEY(page_id) REFERENCES wikidocs_pages(id) ON DELETE SET NULL)''',
'''CREATE INDEX IF NOT EXISTS idx_wikidocs_progress_user_last_read ON wikidocs_reading_progress(user_id,last_read_at)''',
]
def ensure_schema(gateway):
 for sql in SCHEMA: gateway.execute(sql)
