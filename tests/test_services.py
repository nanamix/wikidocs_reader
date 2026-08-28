from plugins.metadata.wikidocs_reader.wikidocs_reader import BookService
from plugins.metadata.wikidocs_reader.wikidocs_reader import ReadingService
class Books:
 def __init__(self): self.data={1:{'id':1,'wikidocs_book_id':10,'title':'x'}}
 def get(self,i):return self.data.get(i)
 def upsert(self,b):self.data[1]={'id':1,**b};return 1
class Pages:
 def __init__(self):self.data={}
 def upsert(self,p):self.data[p['wikidocs_page_id']]=p;return p['wikidocs_page_id']
 def list_by_book(self,b):return [p for p in self.data.values() if p['book_id']==b]
 def get(self,i):return self.data.get(i)
class Users:
 def __init__(self):self.data=set()
 def add(self,u,b):self.data.add((u,b))
 def contains(self,u,b):return (u,b) in self.data
 def list(self,u):return [{'id':b} for x,b in self.data if x==u]
class Progress:
 def __init__(self):self.data={}
 def get(self,u,b):return self.data.get((u,b))
 def save(self,u,b,*x):self.data[(u,b)]=x
 def mark_unread(self,u,b):self.data.pop((u,b),None)
 def recent(self,u,limit):return []
class Gateway:
 def get_book(self,i):return {'title':'x','page_count':2}
 def get_toc(self,i):return [{'id':11,'title':'one'}]
 def get_page(self,i):return {'content_html':'body'}
 def search_public_books(self,q,page=1):return []
def test_user_book_isolation():
 b,u,p=Books(),Users(),Pages(); s=BookService(b,p,u,Gateway());s.import_book(10,1);assert s.get_for_user(1,1);assert s.get_for_user(2,1) is None
def test_reading_requires_ownership():
 u=Users();p=Progress();s=ReadingService(p,u)
 try:s.save_position(1,1,1,.5,1,2);assert False
 except PermissionError:pass
