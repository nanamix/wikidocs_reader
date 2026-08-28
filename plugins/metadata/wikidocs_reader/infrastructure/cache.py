from __future__ import annotations
import hashlib, time
class CacheRepository:
 def __init__(self,db): self.db=db
 def get(self,key):
  r=self.db.fetch_one('SELECT value FROM wikidocs_cache WHERE cache_key=? AND expires_at>?',(key,time.time())); return r['value'] if r else None
 def set(self,key,value,ttl): self.db.execute('INSERT INTO wikidocs_cache(cache_key,value,expires_at,created_at) VALUES(?,?,?,?) ON CONFLICT(cache_key) DO UPDATE SET value=excluded.value,expires_at=excluded.expires_at,created_at=excluded.created_at',(key,value,time.time()+ttl,time.time()))
 def purge(self): self.db.execute('DELETE FROM wikidocs_cache WHERE expires_at<=?',(time.time(),))
 def purge_to_size(self,max_bytes):
  while True:
   r=self.db.fetch_one('SELECT COALESCE(SUM(length(value)),0) n FROM wikidocs_cache')
   if not r or (r['n'] or 0)<=max_bytes: break
   self.db.execute('DELETE FROM wikidocs_cache WHERE cache_key=(SELECT cache_key FROM wikidocs_cache ORDER BY expires_at ASC LIMIT 1)')
def cache_key(kind,*parts): return hashlib.sha256((kind+'|'+'|'.join(map(str,parts))).encode()).hexdigest()
