from plugins.metadata.wikidocs_reader.wikidocs_reader import BookService
from plugins.metadata.wikidocs_reader.wikidocs_reader import ReadingService
from plugins.metadata.wikidocs_reader.wikidocs_reader import SearchService
class Books:
 def __init__(self): self.d={}
 def upsert(self,b):
  i=next((x for x,v in self.d.items() if v['wikidocs_book_id']==b['wikidocs_book_id']),len(self.d)+1);self.d[i]={'id':i,**b};return i
 def get(self,i):return self.d.get(i)
class Pages:
 def __init__(self):self.d={}
 def upsert(self,p):
  i=next((x for x,v in self.d.items() if v['wikidocs_page_id']==p['wikidocs_page_id']),len(self.d)+1);self.d[i]={'id':i,**p};return i
 def list_by_book(self,b):return [v for v in self.d.values() if v['book_id']==b]
 def get(self,i):return self.d.get(i)
class Users:
 def __init__(self):self.d=set()
 def add(self,u,b):self.d.add((u,b))
 def contains(self,u,b):return (u,b) in self.d
 def list(self,u):return [dict(id=b) for x,b in self.d if x==u]
class Progress:
 def __init__(self):self.d={}
 def get(self,u,b):return self.d.get((u,b))
 def save(self,u,b,pid,pos,read,total):self.d[(u,b)]={'page_id':pid,'position':pos,'pages_read':read,'total_pages':total,'is_completed':total>0 and read>=total}
 def mark_unread(self,u,b):self.d.pop((u,b),None)
 def recent(self,u,limit):return list(self.d.values())[:limit]
class Gateway:
 def search_public_books(self,q,page=1):return [{'wikidocs_book_id':10,'title':'파이썬','url':'https://wikidocs.net/book/10'}]
 def get_book(self,i):return {'title':'파이썬','page_count':2,'url':'https://wikidocs.net/book/10'}
 def get_toc(self,i):return [{'id':101,'title':'1장'},{'id':102,'title':'2장'}]
 def get_page(self,i):return {'title':'1장','content_html':'본문','url':'https://wikidocs.net/101'}
class Cache:
 def __init__(self):self.d={}
 def get(self,k):return self.d.get(k)
 def set(self,k,v,ttl):self.d[k]=v
 def purge(self):pass
 def purge_to_size(self,n):pass
def test_mvp_user_journey_and_isolation():
 books,pages,users=Books(),Pages(),Users(); progress=Progress(); gateway=Gateway()
 search=SearchService(gateway,Cache()); assert search.search('파이썬')[0]['title']=='파이썬'
 svc=BookService(books,pages,users,gateway); reading=ReadingService(progress,users)
 bid=svc.import_book(10,1); assert svc.get_for_user(1,bid); assert svc.get_for_user(2,bid) is None
 assert len(svc.sync_pages(1,bid))==2
 assert svc.get_page_for_user(1,bid,1)['content_html']=='본문'
 reading.save_position(1,bid,1,.68,1,2); p=reading.get_progress(1,bid); assert p['page_id']==1 and p['position']==.68 and not p['is_completed']
 reading.complete(1,bid,2); assert reading.get_progress(1,bid)['is_completed']
 reading.mark_unread(1,bid); assert reading.get_progress(1,bid) is None
 assert reading.get_progress(2,bid) is None
