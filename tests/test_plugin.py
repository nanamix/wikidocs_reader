from plugins.metadata.wikidocs_reader.application.search_service import SearchService
class Gateway:
 def __init__(self):self.calls=0
 def search_public_books(self,q,page=1):self.calls+=1;return [{'title':q}]
class Cache:
 def __init__(self):self.d={}
 def get(self,k):return self.d.get(k)
 def set(self,k,v,ttl):self.d[k]=v
 def purge(self):pass
 def purge_to_size(self,n):pass
def test_search_service_caches():
 g=Gateway();s=SearchService(g,Cache());assert s.search('파이썬')==[{'title':'파이썬'}];assert s.search('파이썬')==[{'title':'파이썬'}];assert g.calls==1
