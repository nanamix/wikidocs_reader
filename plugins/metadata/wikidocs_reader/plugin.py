from plugins.metadata.base import BaseMetadataProvider
from .infrastructure.repositories import BookRepository,PageRepository,UserBookRepository,ReadingProgressRepository
from .infrastructure.cache import CacheRepository
from .infrastructure.schema import ensure_schema
from .wikidocs.client import WikiDocsClient,WikiDocsError
from .wikidocs.search import PublicBookSearch
from .application.book_service import BookService
from .application.reading_service import ReadingService
from .application.search_service import SearchService
class WikidocsReaderMetadataProvider(BaseMetadataProvider):
 id='wikidocs_reader';name='WikiDocs';is_searchable=True;enabled=True
 category_tab={'title':'WikiDocs','icon':'fa-solid fa-book-open','order':80,'sessions':['general']}
 dashboard_widget={'title':'WikiDocs','subtitle':'최근 읽은 WikiDocs 책','provider':'WikiDocs','icon':'fa-solid fa-book-open','limit':20,'supported_types':['general']}
 config_schema=[]
 update_manifest={'enabled':True,'provider':'github-raw','raw_base_url':'https://raw.githubusercontent.com/C-Rhapsody/bookoasis-wikidocs/main/plugins/metadata/wikidocs_reader','files':['plugin.py','__init__.py','script.js','index.html','style.css','settings.html','requirements.txt','VERSION','application/book_service.py','application/cache_policy.py','application/cache_service.py','application/reading_service.py','application/search_service.py','domain/models.py','domain/ports.py','infrastructure/cache.py','infrastructure/repositories.py','infrastructure/schema.py','presentation/context.py','wikidocs/client.py','wikidocs/search.py'],'version_file':'VERSION','version_key':'plugin version','show_sample_update_button':True}
 def __init__(self,db=None,gateway=None):
  gateway = gateway or self.get_db_gateway(db or 'general'); ensure_schema(gateway); client=WikiDocsClient(); books=BookRepository(gateway);pages=PageRepository(gateway);users=UserBookRepository(gateway);progress=ReadingProgressRepository(gateway)
  self.books=BookService(books,pages,users,client);self.reading=ReadingService(progress,users);self.search_service=SearchService(PublicBookSearch(client),CacheRepository(gateway))
 def search(self,db_type,query):
  try:return self.search_service.search(query)
  except WikiDocsError as exc:
   from .infrastructure.security_log import security_event
   security_event('search_error', error_type=type(exc).__name__)
   return []
 def apply(self,db_type,book_id,item_data):
  try:
   from .presentation.context import FlaskUserContext
   u=FlaskUserContext().current_user_id()
   if u is None:return False,'로그인이 필요합니다.'
   self.books.import_book(int(item_data['wikidocs_book_id']),u);return True,'WikiDocs 책을 저장했습니다.'
  except (KeyError,ValueError,WikiDocsError,PermissionError) as e:return False,str(e)
 def get_context_menu_items(self,db_type,context):
  return [{
   'id':'wikidocs_rpc',
   'label':'WikiDocs',
   'icon':'fa-solid fa-book-open',
  }]

 def run_context_menu_action(self,db_type,action_id,context):
  if action_id != 'wikidocs_rpc':
   return {'success':False,'error':'지원하지 않는 WikiDocs 액션입니다.'}
  op=str((context or {}).get('op') or '').strip()
  user_id=None
  if not op:
   return {'success':False,'error':'WikiDocs 작업이 지정되지 않았습니다.'}
  try:
   if op == 'browser_debug':
    events=context.get('events') or []
    if not isinstance(events,list): return {'success':False,'error':'브라우저 로그 형식이 올바르지 않습니다.'}
    events=events[-50:]
    from .infrastructure.security_log import security_event
    security_event('browser_debug', event_count=len(events))
    for event in events:
     if isinstance(event,dict):
      safe={k:event.get(k) for k in ('type','timestamp','fullscreen','topbarExists','hidden','display','visibility','width','height','zIndex','message','bookId') if k in event}
      security_event('browser_event', **safe)
    return {'success':True,'count':len(events)}
   if op == 'search':
    return {'success':True,'items':self.search_service.search(str(context.get('query') or '').strip())}
   if op == 'public_books':
    page=max(1,int(context.get('page',1))); sort_type=str(context.get('sort_type') or 'recent'); items=self.search_service.list_public(page, sort_type)
    enriched=[]
    for item in items:
     local=self.books.get_by_remote_id(int(item['wikidocs_book_id']))
     item=dict(item); item['book_id']=local['id'] if local else None; item['in_my_books']=bool(local and user_id is not None and self.books.contains(user_id,local['id']))
     enriched.append(item)
    return {'success':True,'items':enriched,'page':page,'has_next':len(items)==20,'has_prev':page>1}
   if user_id is None:
    from .presentation.context import FlaskUserContext
    user_id=FlaskUserContext().current_user_id()
   if user_id is None:
    return {'success':False,'error':'로그인이 필요합니다.'}
   if op == 'books':
    items=[]
    for book in self.books.my_books(user_id):
     book=dict(book); book['progress']=self.reading.get_progress(user_id,int(book['id']))
     items.append(book)
    return {'success':True,'items':items}
   if op == 'add':
    remote_id=int(context['remote_id'])
    return {'success':True,'book_id':self.books.import_book(remote_id,user_id)}
   if op == 'detail':
    book_id=int(context['book_id'])
    book=self.books.get_for_user(user_id,book_id)
    if not book:return {'success':False,'error':'책을 찾을 수 없습니다.'}
    return {'success':True,'book':book,'progress':self.reading.get_progress(user_id,book_id),'pages':self.books.sync_pages(user_id,book_id)}
   if op == 'page':
    book_id=int(context['book_id']);page_id=int(context['page_id'])
    page=self.books.get_page_for_user(user_id,book_id,page_id)
    return {'success':True,'page':page} if page else {'success':False,'error':'페이지를 찾을 수 없습니다.'}
   if op == 'progress':
    book_id=int(context['book_id'])
    if not self.books.get_for_user(user_id,book_id):return {'success':False,'error':'책을 찾을 수 없습니다.'}
    self.reading.save_position(user_id,book_id,context.get('page_id'),context.get('position',0),context.get('pages_read',0),context.get('total_pages',0))
    return {'success':True,'progress':self.reading.get_progress(user_id,book_id)}
   if op == 'complete':
    book_id=int(context['book_id'])
    if not self.books.get_for_user(user_id,book_id):return {'success':False,'error':'책을 찾을 수 없습니다.'}
    self.reading.complete(user_id,book_id,int(context.get('total_pages',0)))
    return {'success':True,'progress':self.reading.get_progress(user_id,book_id)}
   if op == 'reset':
    book_id=int(context['book_id'])
    if not self.books.get_for_user(user_id,book_id):return {'success':False,'error':'책을 찾을 수 없습니다.'}
    self.reading.mark_unread(user_id,book_id)
    return {'success':True}
   return {'success':False,'error':'지원하지 않는 WikiDocs 작업입니다.'}
  except (KeyError,TypeError,ValueError,WikiDocsError,PermissionError) as e:
   return {'success':False,'error':str(e) or f'{type(e).__name__}'}

 def get_dashboard_data(self,db_type,limit=20):
  try:
   from .presentation.context import FlaskUserContext
   u=FlaskUserContext().current_user_id()
   return {'success':True,'items':self.reading.recent(u,limit)} if u is not None else {'success':False,'error':'로그인이 필요합니다.'}
  except Exception as exc:
   from .infrastructure.security_log import security_event
   security_event('dashboard_error', error_type=type(exc).__name__)
   return {'success':False,'items':[]}
