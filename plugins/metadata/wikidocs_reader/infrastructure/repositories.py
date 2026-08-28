"""Repositories backed by the BookOasis plugin DB gateway."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

def now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")

class BookRepository:
    def __init__(self, db): self.db = db
    def upsert(self, book: dict[str, Any]) -> int:
        t=now(); rid=int(book['wikidocs_book_id'])
        self.db.execute('UPDATE wikidocs_books SET title=?,author=?,description=?,cover_url=?,url=?,page_count=?,synced_at=?,updated_at=? WHERE wikidocs_book_id=?',(book.get('title',''),book.get('author'),book.get('description'),book.get('cover_url'),book.get('url'),int(book.get('page_count') or 0),t,t,rid))
        if not self.db.fetch_one('SELECT id FROM wikidocs_books WHERE wikidocs_book_id=?',(rid,)):
            self.db.execute('INSERT INTO wikidocs_books(id,wikidocs_book_id,title,author,description,cover_url,url,page_count,synced_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(rid,rid,book.get('title',''),book.get('author'),book.get('description'),book.get('cover_url'),book.get('url'),int(book.get('page_count') or 0),t,t))
        return rid
    def get(self, book_id: int):
        r=self.db.fetch_one('SELECT * FROM wikidocs_books WHERE id=?',(int(book_id),)); return dict(r) if r else None
    def get_by_remote_id(self, remote_id: int):
        r=self.db.fetch_one('SELECT * FROM wikidocs_books WHERE wikidocs_book_id=?',(int(remote_id),)); return dict(r) if r else None

class PageRepository:
    def __init__(self, db): self.db=db
    def upsert(self, page: dict[str, Any]) -> int:
        t=now(); rid=int(page['wikidocs_page_id'])
        self.db.execute('UPDATE wikidocs_pages SET book_id=?,parent_id=?,title=?,page_order=?,content_html=COALESCE(?,content_html),url=?,synced_at=?,updated_at=? WHERE wikidocs_page_id=?',(int(page['book_id']),page.get('parent_id'),page.get('title',''),int(page.get('page_order') or 0),page.get('content_html'),page.get('url'),t,t,rid))
        if not self.db.fetch_one('SELECT id FROM wikidocs_pages WHERE wikidocs_page_id=?',(rid,)):
            self.db.execute('INSERT INTO wikidocs_pages(id,wikidocs_page_id,book_id,parent_id,title,page_order,content_html,url,synced_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(rid,rid,int(page['book_id']),page.get('parent_id'),page.get('title',''),int(page.get('page_order') or 0),page.get('content_html'),page.get('url'),t,t))
        return rid
    def list_by_book(self,book_id:int): return [dict(x) for x in self.db.fetch_all('SELECT * FROM wikidocs_pages WHERE book_id=? ORDER BY page_order,id',(int(book_id),))]
    def get(self,page_id:int):
        r=self.db.fetch_one('SELECT * FROM wikidocs_pages WHERE id=?',(int(page_id),)); return dict(r) if r else None

class UserBookRepository:
    def __init__(self, db): self.db=db
    def contains(self,user_id:int,book_id:int)->bool: return self.db.fetch_one('SELECT 1 FROM wikidocs_user_books WHERE user_id=? AND book_id=?',(int(user_id),int(book_id))) is not None
    def list(self,user_id:int): return [dict(x) for x in self.db.fetch_all('''SELECT b.*,u.added_at,u.updated_at FROM wikidocs_user_books u JOIN wikidocs_books b ON b.id=u.book_id WHERE u.user_id=? ORDER BY u.updated_at DESC''',(int(user_id),))]
    def add(self,user_id:int,book_id:int)->None:
        if self.db.fetch_one('SELECT 1 FROM wikidocs_user_books WHERE user_id=? AND book_id=?',(int(user_id),int(book_id))): self.db.execute('UPDATE wikidocs_user_books SET updated_at=CURRENT_TIMESTAMP WHERE user_id=? AND book_id=?',(int(user_id),int(book_id)))
        else: self.db.execute('INSERT INTO wikidocs_user_books(user_id,book_id) VALUES(?,?)',(int(user_id),int(book_id)))

class ReadingProgressRepository:
    def __init__(self, db): self.db=db
    def get(self,user_id:int,book_id:int):
        r=self.db.fetch_one('SELECT * FROM wikidocs_reading_progress WHERE user_id=? AND book_id=?',(int(user_id),int(book_id))); return dict(r) if r else None
    def save(self,user_id:int,book_id:int,page_id:int|None,position:float,pages_read:int,total_pages:int)->None:
        position=max(0.0,min(float(position),1.0)); completed=int(total_pages>0 and pages_read>=total_pages); t=now()
        params=(page_id,position,int(pages_read),int(total_pages),completed,t,t if completed else None,t,int(user_id),int(book_id))
        if self.db.fetch_one('SELECT 1 FROM wikidocs_reading_progress WHERE user_id=? AND book_id=?',(int(user_id),int(book_id))):
            self.db.execute('''UPDATE wikidocs_reading_progress SET page_id=?,position=?,pages_read=?,total_pages=?,is_completed=?,last_read_at=?,completed_at=CASE WHEN ?=1 AND completed_at IS NULL THEN ? WHEN ?=0 THEN NULL ELSE completed_at END,updated_at=? WHERE user_id=? AND book_id=?''',(page_id,position,int(pages_read),int(total_pages),completed,t,completed,t if completed else None,completed,t,int(user_id),int(book_id)))
        else:
            self.db.execute('INSERT INTO wikidocs_reading_progress(user_id,book_id,page_id,position,pages_read,total_pages,is_completed,last_read_at,completed_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(int(user_id),int(book_id),page_id,position,int(pages_read),int(total_pages),completed,t,t if completed else None,t))
    def recent(self,user_id:int,limit:int=20): return [dict(x) for x in self.db.fetch_all('''SELECT b.*,p.page_id,p.position,p.pages_read,p.total_pages,p.is_completed,p.last_read_at,p.completed_at FROM wikidocs_reading_progress p JOIN wikidocs_books b ON b.id=p.book_id WHERE p.user_id=? AND p.last_read_at IS NOT NULL ORDER BY p.last_read_at DESC LIMIT ?''',(int(user_id),max(1,min(int(limit),100))))]
    def mark_unread(self,user_id:int,book_id:int)->None: self.db.execute('DELETE FROM wikidocs_reading_progress WHERE user_id=? AND book_id=?',(int(user_id),int(book_id)))
