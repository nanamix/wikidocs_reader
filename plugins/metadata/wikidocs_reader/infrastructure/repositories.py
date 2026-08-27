"""Repositories: the only layer allowed to issue SQL."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from .database import Database

def now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")
class BookRepository:
    def __init__(self, db: Database): self.db = db
    def upsert(self, book: dict[str, Any]) -> int:
        t=now()
        with self.db.connect() as c:
            c.execute('''INSERT INTO wikidocs_books(wikidocs_book_id,title,author,description,cover_url,url,page_count,synced_at,updated_at)
                         VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(wikidocs_book_id) DO UPDATE SET title=excluded.title,author=excluded.author,description=excluded.description,cover_url=excluded.cover_url,url=excluded.url,page_count=excluded.page_count,synced_at=excluded.synced_at,updated_at=excluded.updated_at''',
                      (int(book['wikidocs_book_id']),book.get('title',''),book.get('author'),book.get('description'),book.get('cover_url'),book.get('url'),int(book.get('page_count') or 0),t,t))
            return int(c.execute('SELECT id FROM wikidocs_books WHERE wikidocs_book_id=?',(int(book['wikidocs_book_id']),)).fetchone()['id'])
    def get(self, book_id: int):
        with self.db.connect() as c:
            r=c.execute('SELECT * FROM wikidocs_books WHERE id=?',(int(book_id),)).fetchone()
        return dict(r) if r else None
    def get_by_remote_id(self, remote_id: int):
        with self.db.connect() as c:
            r=c.execute('SELECT * FROM wikidocs_books WHERE wikidocs_book_id=?',(int(remote_id),)).fetchone()
        return dict(r) if r else None
class PageRepository:
    def __init__(self, db: Database): self.db=db
    def upsert(self, page: dict[str, Any]) -> int:
        t=now()
        with self.db.connect() as c:
            c.execute('''INSERT INTO wikidocs_pages(wikidocs_page_id,book_id,parent_id,title,page_order,content_html,url,synced_at,updated_at)
                         VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(wikidocs_page_id) DO UPDATE SET book_id=excluded.book_id,parent_id=excluded.parent_id,title=excluded.title,page_order=excluded.page_order,content_html=COALESCE(excluded.content_html,wikidocs_pages.content_html),url=excluded.url,synced_at=excluded.synced_at,updated_at=excluded.updated_at''',
                      (int(page['wikidocs_page_id']),int(page['book_id']),page.get('parent_id'),page.get('title',''),int(page.get('page_order') or 0),page.get('content_html'),page.get('url'),t,t))
            return int(c.execute('SELECT id FROM wikidocs_pages WHERE wikidocs_page_id=?',(int(page['wikidocs_page_id']),)).fetchone()['id'])
    def list_by_book(self,book_id:int)->list[dict[str,Any]]:
        with self.db.connect() as c:r=c.execute('SELECT * FROM wikidocs_pages WHERE book_id=? ORDER BY page_order,id',(int(book_id),)).fetchall()
        return [dict(x) for x in r]
    def get(self,page_id:int):
        with self.db.connect() as c:r=c.execute('SELECT * FROM wikidocs_pages WHERE id=?',(int(page_id),)).fetchone()
        return dict(r) if r else None
class UserBookRepository:
    def __init__(self, db: Database): self.db=db
    def contains(self,user_id:int,book_id:int)->bool:
        with self.db.connect() as c:r=c.execute('SELECT 1 FROM wikidocs_user_books WHERE user_id=? AND book_id=?',(int(user_id),int(book_id))).fetchone()
        return r is not None
    def list(self,user_id:int)->list[dict[str,Any]]:
        with self.db.connect() as c:r=c.execute('''SELECT b.*,u.added_at,u.updated_at FROM wikidocs_user_books u JOIN wikidocs_books b ON b.id=u.book_id WHERE u.user_id=? ORDER BY u.updated_at DESC''',(int(user_id),)).fetchall()
        return [dict(x) for x in r]
    def add(self,user_id:int,book_id:int)->None:
        with self.db.connect() as c:c.execute('INSERT INTO wikidocs_user_books(user_id,book_id) VALUES(?,?) ON CONFLICT(user_id,book_id) DO UPDATE SET updated_at=CURRENT_TIMESTAMP',(int(user_id),int(book_id)))
class ReadingProgressRepository:
    def __init__(self, db: Database): self.db=db
    def get(self,user_id:int,book_id:int):
        with self.db.connect() as c:r=c.execute('SELECT * FROM wikidocs_reading_progress WHERE user_id=? AND book_id=?',(int(user_id),int(book_id))).fetchone()
        return dict(r) if r else None
    def save(self,user_id:int,book_id:int,page_id:int|None,position:float,pages_read:int,total_pages:int)->None:
        position=max(0.0,min(float(position),1.0)); completed=int(total_pages>0 and pages_read>=total_pages); t=now()
        with self.db.connect() as c:c.execute('''INSERT INTO wikidocs_reading_progress(user_id,book_id,page_id,position,pages_read,total_pages,is_completed,last_read_at,completed_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(user_id,book_id) DO UPDATE SET page_id=excluded.page_id,position=excluded.position,pages_read=excluded.pages_read,total_pages=excluded.total_pages,is_completed=excluded.is_completed,last_read_at=excluded.last_read_at,completed_at=CASE WHEN excluded.is_completed=1 AND wikidocs_reading_progress.completed_at IS NULL THEN excluded.completed_at WHEN excluded.is_completed=0 THEN NULL ELSE wikidocs_reading_progress.completed_at END,updated_at=excluded.updated_at''',(int(user_id),int(book_id),page_id,position,int(pages_read),int(total_pages),completed,t,t if completed else None,t))
    def recent(self,user_id:int,limit:int=20)->list[dict[str,Any]]:
        with self.db.connect() as c:r=c.execute('''SELECT b.*,p.page_id,p.position,p.pages_read,p.total_pages,p.is_completed,p.last_read_at,p.completed_at FROM wikidocs_reading_progress p JOIN wikidocs_books b ON b.id=p.book_id WHERE p.user_id=? AND p.last_read_at IS NOT NULL ORDER BY p.last_read_at DESC LIMIT ?''',(int(user_id),max(1,min(int(limit),100)))).fetchall()
        return [dict(x) for x in r]
    def mark_unread(self,user_id:int,book_id:int)->None:
        with self.db.connect() as c:c.execute('DELETE FROM wikidocs_reading_progress WHERE user_id=? AND book_id=?',(int(user_id),int(book_id)))
