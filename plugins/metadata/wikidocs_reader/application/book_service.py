from ..domain.ports import BookStore,PageStore,UserBookStore,WikiDocsGateway
class BookService:
 def __init__(self,books:BookStore,pages:PageStore,users:UserBookStore,gateway:WikiDocsGateway):self.books,self.pages,self.users,self.gateway=books,pages,users,gateway
 def import_book(self,remote_id,user_id):
  r=self.gateway.get_book(remote_id); b=self.books.upsert({'wikidocs_book_id':remote_id,'title':r.get('title') or '제목 없음','author':r.get('author'),'description':r.get('description'),'cover_url':r.get('cover_url'),'url':r.get('url') or f'https://wikidocs.net/book/{remote_id}','page_count':r.get('page_count',0)});self.users.add(user_id,b);return b
 def get_for_user(self,u,b):return self.books.get(b) if self.users.contains(u,b) else None
 def my_books(self,u):return self.users.list(u)
 def get_by_remote_id(self,remote_id):return self.books.get_by_remote_id(remote_id)
 def contains(self,u,b):return self.users.contains(u,b)
 def sync_pages(self,u,b):
  book=self.get_for_user(u,b)
  if not book:return []
  for i,p in enumerate(self.gateway.get_toc(book['wikidocs_book_id'])):self.pages.upsert({'wikidocs_page_id':p['id'],'book_id':b,'parent_id':p.get('parent_id'),'title':p.get('title',''),'page_order':i,'url':p.get('url')})
  return self.pages.list_by_book(b)
 def get_page_for_user(self,u,b,pid):
  if not self.get_for_user(u,b):return None
  p=self.pages.get(pid)
  if not p or p['book_id']!=b:return None
  if not p.get('content_html'):
   r=self.gateway.get_page(p['wikidocs_page_id']);p.update(content_html=r.get('content_html'),title=r.get('title') or p['title'],url=r.get('url') or p['url']);self.pages.upsert(p)
  return p
