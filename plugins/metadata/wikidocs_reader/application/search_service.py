import json
from .cache_policy import SEARCH_TTL, PUBLIC_BOOK_LIST_TTL, MAX_CACHE_BYTES
from ..infrastructure.cache import cache_key

class SearchService:
    def __init__(self, gateway, cache):
        self.gateway = gateway
        self.cache = cache

    def list_public(self, page=1):
        page = max(1, int(page))
        key = cache_key('public-books', page)
        hit = self.cache.get(key)
        if hit:
            return json.loads(hit)
        value = self.gateway.list_public(page=page)
        self.cache.set(key, json.dumps(value, ensure_ascii=False), PUBLIC_BOOK_LIST_TTL)
        self.cache.purge()
        self.cache.purge_to_size(MAX_CACHE_BYTES)
        return value

    def search(self, q, page=1):
        q = str(q or '').strip()
        page = max(1, int(page))
        if not q:
            return []
        key = cache_key('search', q, page)
        hit = self.cache.get(key)
        if hit:
            return json.loads(hit)
        # PublicBookSearch is the application-facing adapter; WikiDocsClient is
        # deliberately hidden behind it.
        search_fn = getattr(self.gateway, 'search', None) or getattr(self.gateway, 'search_public_books')
        value = search_fn(q, page=page)
        self.cache.set(key, json.dumps(value, ensure_ascii=False), SEARCH_TTL)
        self.cache.purge()
        self.cache.purge_to_size(MAX_CACHE_BYTES)
        return value
