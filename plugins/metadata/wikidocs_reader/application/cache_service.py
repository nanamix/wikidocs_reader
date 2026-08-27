import json
from .cache_policy import SEARCH_TTL,MAX_CACHE_BYTES
from ..infrastructure.cache import CacheRepository,cache_key
class CacheService:
 def __init__(self,repo): self.repo=repo
 def search(self,query,page,loader):
  key=cache_key('search',query,page)
  hit=self.repo.get(key)
  if hit is not None:return json.loads(hit)
  value=loader(); self.repo.set(key,json.dumps(value,ensure_ascii=False,separators=(',',':')),SEARCH_TTL); self.repo.purge(); self.repo.purge_to_size(MAX_CACHE_BYTES); return value
