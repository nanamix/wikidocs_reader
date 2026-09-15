from plugins.metadata.base import BaseMetadataProvider
# ===== domain/models.py =====
"""Pure domain models."""
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True, slots=True)
class Book:
    wikidocs_book_id: int
    title: str
    author: str | None = None
    description: str | None = None
    cover_url: str | None = None
    url: str | None = None
    page_count: int = 0

@dataclass(frozen=True, slots=True)
class Page:
    wikidocs_page_id: int
    book_id: int
    title: str
    page_order: int = 0
    parent_id: int | None = None
    content_html: str | None = None
    url: str | None = None

@dataclass(frozen=True, slots=True)
class ReadingProgress:
    user_id: int
    book_id: int
    page_id: int | None
    position: float
    pages_read: int
    total_pages: int
    is_completed: bool
    last_read_at: datetime | None = None
    completed_at: datetime | None = None

# ===== domain/ports.py =====
from typing import Any, Protocol
class BookStore(Protocol):
 def upsert(self,b:dict[str,Any])->int: ...
 def get(self,i:int)->dict[str,Any]|None: ...
class PageStore(Protocol):
 def upsert(self,p:dict[str,Any])->int: ...
 def list_by_book(self,b:int)->list[dict[str,Any]]: ...
 def get(self,i:int)->dict[str,Any]|None: ...
class UserBookStore(Protocol):
 def add(self,u:int,b:int)->None: ...
 def contains(self,u:int,b:int)->bool: ...
 def list(self,u:int)->list[dict[str,Any]]: ...
class ProgressStore(Protocol):
 def get(self,u:int,b:int)->dict[str,Any]|None: ...
 def save(self,u:int,b:int,p:int|None,pos:float,read:int,total:int)->None: ...
 def mark_unread(self,u:int,b:int)->None: ...
 def recent(self,u:int,limit:int)->list[dict[str,Any]]: ...
class WikiDocsGateway(Protocol):
 def get_book(self,i:int)->dict[str,Any]: ...
 def get_toc(self,i:int)->list[dict[str,Any]]: ...
 def get_page(self,i:int)->dict[str,Any]: ...
 def search_public_books(self,q:str,page:int=1)->list[dict[str,Any]]: ...
class CacheStore(Protocol):
 def get(self,k:str)->str|None: ...
 def set(self,k:str,v:str,ttl:int)->None: ...
 def purge(self)->None: ...
 def purge_to_size(self,n:int)->None: ...

# ===== application/cache_policy.py =====
SEARCH_TTL=600
PUBLIC_BOOK_LIST_TTL=600
BOOK_TTL=1800
TOC_TTL=1800
PAGE_TTL=1800
MAX_CACHE_BYTES=100*1024*1024

# ===== wikidocs/client.py =====
import json
from typing import Any
from bs4 import BeautifulSoup
from curl_cffi import requests

BASE_URL = "https://wikidocs.net"


class WikiDocsError(RuntimeError):
    pass


ALLOWED_HTML_TAGS = {
    "p", "br", "hr", "div", "span", "section", "article",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "b", "em", "i", "u", "s", "del", "ins",
    "ul", "ol", "li", "dl", "dt", "dd",
    "blockquote", "pre", "code",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td",
    "a", "img",
    "figure", "figcaption", "sup", "sub", "kbd", "samp", "var",
    "mark", "details", "summary",
}
DANGEROUS_HTML_TAGS = {
    "script", "style", "iframe", "object", "embed", "form", "input",
    "button", "svg",
}
ALLOWED_ATTRS = {
    "a": {"href", "title", "target", "rel"},
    "img": {"src", "alt", "title", "width", "height"},
    "th": {"colspan", "rowspan"},
    "td": {"colspan", "rowspan"},
}

def sanitize_content_html(html: str) -> str:
    """Sanitize remote WikiDocs HTML before it can reach the browser.

    The reader intentionally supports rich text, tables, code blocks and images,
    but does not trust remote markup. Scripts, executable embeds, event handlers,
    inline styles and unsafe URLs are removed.
    """
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup.find_all(DANGEROUS_HTML_TAGS):
        tag.decompose()
    for tag in list(soup.find_all(True)):
        if not isinstance(tag.name, str):
            continue
        name = tag.name.lower()
        if name not in ALLOWED_HTML_TAGS:
            tag.unwrap()
            continue
        allowed = ALLOWED_ATTRS.get(name, set())
        for attr in list(tag.attrs):
            if not isinstance(attr, str):
                continue
            attr_name = attr.lower()
            if attr_name.startswith("on") or attr_name == "style" or attr_name not in allowed:
                del tag.attrs[attr]
        if name == "a":
            href = tag.get("href", "")
            if href and not (href.startswith("/") or href.startswith("#") or href.startswith("https://") or href.startswith("http://")):
                tag.attrs.pop("href", None)
            if tag.get("target") == "_blank":
                tag["rel"] = "noopener noreferrer"
        elif name == "img":
            src = tag.get("src", "")
            if not (src.startswith("/") or src.startswith("https://") or src.startswith("http://")):
                tag.decompose()
    return str(soup)


class WikiDocsClient:
    def __init__(self, base_url: str = BASE_URL, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/139.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        })

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        try:
            response = self._session.request(
                method, f"{self.base_url}/{path.lstrip('/')}",
                impersonate="chrome", timeout=self.timeout, **kwargs,
            )
            response.raise_for_status()
            return response
        except Exception as exc:
            raise WikiDocsError(f"WikiDocs request failed: {exc}") from exc

    def _json(self, path: str) -> Any:
        response = self._request("GET", path, headers={"Accept": "application/json"})
        try:
            return response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise WikiDocsError("Unexpected WikiDocs JSON response") from exc

    def list_public_books(self, page: int = 1, sort_type: str = "recent") -> str:
        response = self._request(
            "POST", "/tab/all",
            data={"page": max(1, int(page)), "sort_type": sort_type, "kw": ""},
            headers={"Referer": f"{self.base_url}/", "X-Requested-With": "XMLHttpRequest"},
        )
        return response.text

    def search_public_books(self, query: str, page: int = 1, sort_type: str = "recommend") -> str:
        query = query.strip()
        if not query:
            return ""
        response = self._request(
            "POST", "/tab/all",
            data={"page": max(1, int(page)), "sort_type": sort_type, "kw": query},
            headers={"Referer": f"{self.base_url}/", "X-Requested-With": "XMLHttpRequest"},
        )
        return response.text

    def _public_html(self, path: str) -> BeautifulSoup:
        response = self._request("GET", path, headers={"Accept": "text/html"})
        return BeautifulSoup(response.text, "html.parser")

    def get_book(self, book_id: int) -> dict[str, Any]:
        # WikiDocs' public NAPI currently returns 401 without its authenticated
        # browser session. Public book pages themselves are available, so use
        # the same public representation as the browser for public books.
        book_id = int(book_id)
        soup = self._public_html(f"/book/{book_id}")
        title = (soup.select_one('meta[property="og:title"]') or {}).get("content") if soup.select_one('meta[property="og:title"]') else None
        if not title:
            node = soup.select_one("a.book-title strong") or soup.select_one("title")
            title = " ".join(node.stripped_strings).replace(" - WikiDocs", "").strip() if node else "제목 없음"
        description = None
        desc = soup.select_one('meta[name="description"]')
        if desc: description = desc.get("content")
        author = None
        # The public book page exposes the author/profile link near the book info.
        profile = soup.select_one('a[href*="/profile/info/book/"]')
        if profile: author = " ".join(profile.stripped_strings).strip() or None
        pages = soup.select("a.toc-item[data-id]")
        return {"id": book_id, "title": title, "author": author,
                "description": description, "cover_url": None,
                "url": f"https://wikidocs.net/book/{book_id}",
                "page_count": len(pages)}

    def get_toc(self, book_id: int) -> Any:
        soup = self._public_html(f"/book/{int(book_id)}")
        result = []
        for i, node in enumerate(soup.select("a.toc-item[data-id]")):
            try: page_id = int(node.get("data-id"))
            except (TypeError, ValueError): continue
            title = (node.get("title") or " ".join(node.stripped_strings)).strip()
            parent = node.get("data-parent-id")
            result.append({"id": page_id, "parent_id": int(parent) if parent else None,
                           "title": title, "url": f"https://wikidocs.net/{page_id}", "page_order": i})
        return result

    def get_page(self, page_id: int) -> dict[str, Any]:
        page_id = int(page_id)
        soup = self._public_html(f"/{page_id}")
        content = soup.select_one(".page-content")
        title = soup.select_one(".page-subject-text") or soup.select_one("h1.page-subject")
        if not content:
            raise WikiDocsError(f"WikiDocs public page {page_id} has no content")
        return {"id": page_id, "title": " ".join(title.stripped_strings).strip() if title else "",
                "content_html": sanitize_content_html(str(content)), "url": f"https://wikidocs.net/{page_id}"}

# ===== wikidocs/search.py =====
from dataclasses import dataclass
from bs4 import BeautifulSoup

@dataclass(frozen=True, slots=True)
class PublicBookSearchResult:
    wikidocs_book_id: int
    title: str
    author: str | None
    published_at: str | None
    url: str

class PublicBookSearch:
    def __init__(self, client: WikiDocsClient | None = None):
        self.client = client or WikiDocsClient()

    def list_public(self, page: int = 1, sort_type: str = "recent") -> list[dict[str, object]]:
        if sort_type not in {"recent", "recommend", "popular"}:
            sort_type = "recent"
        return self._parse(self.client.list_public_books(page=page, sort_type=sort_type))

    def search(self, query: str, page: int = 1) -> list[dict[str, object]]:
        return self._parse(self.client.search_public_books(query, page=page))

    @staticmethod
    def _parse(html: str) -> list[dict[str, object]]:
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        results = []
        seen: set[int] = set()
        for link in soup.select('a.book-subject[href*="/book/"]'):
            href = link.get("href", "")
            try:
                remote_id = int(href.rstrip("/").split("/book/")[-1])
            except ValueError:
                continue
            if remote_id in seen:
                continue
            title = " ".join(link.stripped_strings).strip()
            if not title:
                continue
            card = link.find_parent(class_="media-body") or link.parent
            author = None
            date = None
            if card:
                detail = card.select_one(".book-detail")
                if detail:
                    parts = [" ".join(x.stripped_strings) for x in detail.find_all("div", recursive=False)]
                    if parts:
                        author = parts[0].lstrip("- ").strip() or None
                    if len(parts) > 1:
                        date = parts[1].lstrip("- ").strip() or None
            seen.add(remote_id)
            results.append({"wikidocs_book_id": remote_id, "title": title, "author": author, "published_at": date, "url": f"https://wikidocs.net/book/{remote_id}"})
        return results

# ===== infrastructure/cache.py =====
import hashlib, time
class CacheRepository:
 def __init__(self,db): self.db=db
 def get(self,key):
  r=self.db.fetch_one('SELECT value FROM wikidocs_cache WHERE cache_key=? AND expires_at>?',(key,time.time())); return r['value'] if r else None
 def set(self,key,value,ttl):
  now=time.time(); expires=now+ttl
  if getattr(self.db,'_engine','sqlite') in ('mariadb','mysql'):
   self.db.execute('INSERT INTO wikidocs_cache(cache_key,value,expires_at,created_at) VALUES(?,?,?,?) ON DUPLICATE KEY UPDATE value=VALUES(value),expires_at=VALUES(expires_at),created_at=VALUES(created_at)',(key,value,expires,now))
  else:
   self.db.execute('INSERT INTO wikidocs_cache(cache_key,value,expires_at,created_at) VALUES(?,?,?,?) ON CONFLICT(cache_key) DO UPDATE SET value=excluded.value,expires_at=excluded.expires_at,created_at=excluded.created_at',(key,value,expires,now))
 def purge(self): self.db.execute('DELETE FROM wikidocs_cache WHERE expires_at<=?',(time.time(),))
 def purge_to_size(self,max_bytes):
  while True:
   r=self.db.fetch_one('SELECT COALESCE(SUM(length(value)),0) n FROM wikidocs_cache')
   if not r or (r['n'] or 0)<=max_bytes: break
   self.db.execute('DELETE FROM wikidocs_cache WHERE cache_key=(SELECT cache_key FROM wikidocs_cache ORDER BY expires_at ASC LIMIT 1)')
def cache_key(kind,*parts): return hashlib.sha256((kind+'|'+'|'.join(map(str,parts))).encode()).hexdigest()

# ===== infrastructure/repositories.py =====
"""Repositories backed by the BookOasis plugin DB gateway."""
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

# ===== infrastructure/schema.py =====
"""Plugin schema declarations executed exclusively through the Core DB gateway."""
SCHEMA = [
'''CREATE TABLE IF NOT EXISTS wikidocs_cache (cache_key VARCHAR(255) PRIMARY KEY, value TEXT NOT NULL, expires_at DOUBLE PRECISION NOT NULL, created_at DOUBLE PRECISION NOT NULL)''',
'''CREATE INDEX IF NOT EXISTS idx_wikidocs_cache_expires ON wikidocs_cache(expires_at)''',
'''CREATE TABLE IF NOT EXISTS wikidocs_books (id BIGINT PRIMARY KEY, wikidocs_book_id BIGINT NOT NULL UNIQUE, title TEXT NOT NULL, author TEXT, description TEXT, cover_url TEXT, url TEXT, page_count INTEGER NOT NULL DEFAULT 0, synced_at TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''',
'''CREATE TABLE IF NOT EXISTS wikidocs_pages (id BIGINT PRIMARY KEY, wikidocs_page_id BIGINT NOT NULL UNIQUE, book_id BIGINT NOT NULL, parent_id BIGINT, title TEXT NOT NULL, page_order INTEGER NOT NULL DEFAULT 0, content_html TEXT, url TEXT, synced_at TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(book_id) REFERENCES wikidocs_books(id) ON DELETE CASCADE)''',
'''CREATE INDEX IF NOT EXISTS idx_wikidocs_pages_book_order ON wikidocs_pages(book_id,page_order,id)''',
'''CREATE TABLE IF NOT EXISTS wikidocs_user_books (user_id BIGINT NOT NULL, book_id BIGINT NOT NULL, added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id,book_id), FOREIGN KEY(book_id) REFERENCES wikidocs_books(id) ON DELETE CASCADE)''',
'''CREATE INDEX IF NOT EXISTS idx_wikidocs_user_books_user ON wikidocs_user_books(user_id,updated_at(255))''',
'''CREATE TABLE IF NOT EXISTS wikidocs_reading_progress (user_id BIGINT NOT NULL, book_id BIGINT NOT NULL, page_id BIGINT, position DOUBLE PRECISION NOT NULL DEFAULT 0, pages_read INTEGER NOT NULL DEFAULT 0, total_pages INTEGER NOT NULL DEFAULT 0, is_completed INTEGER NOT NULL DEFAULT 0, last_read_at TEXT, completed_at TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id,book_id), FOREIGN KEY(book_id) REFERENCES wikidocs_books(id) ON DELETE CASCADE, FOREIGN KEY(page_id) REFERENCES wikidocs_pages(id) ON DELETE SET NULL)''',
'''CREATE INDEX IF NOT EXISTS idx_wikidocs_progress_user_last_read ON wikidocs_reading_progress(user_id,last_read_at(255))''',
]
def ensure_schema(gateway):
 for sql in SCHEMA: gateway.execute(sql)

# ===== infrastructure/security_log.py =====
"""Server-side security event logging with a hard 24-hour retention window."""

import json
import os
import time
from pathlib import Path
from threading import Lock

LOG_PATH = Path(__file__).resolve().parent / "data" / "security.log"
RETENTION_SECONDS = 24 * 60 * 60
_LOCK = Lock()


def _prune(now: float) -> None:
    if not LOG_PATH.exists():
        return
    cutoff = now - RETENTION_SECONDS
    try:
        lines = []
        with LOG_PATH.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    record = json.loads(line)
                    if float(record.get("ts", 0)) >= cutoff:
                        lines.append(line.rstrip("\n"))
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
        tmp = LOG_PATH.with_suffix(".tmp")
        tmp.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        os.replace(tmp, LOG_PATH)
    except OSError:
        return


def security_event(event: str, **details: object) -> None:
    """Write a minimal server-only event; never expose logging failures to users."""
    now = time.time()
    record = {"ts": now, "event": event, **details}
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            _prune(now)
            with LOG_PATH.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    except OSError:
        pass

# ===== application/book_service.py =====
class BookService:
 def __init__(self,books:BookStore,pages:PageStore,users:UserBookStore,gateway:WikiDocsGateway):self.books,self.pages,self.users,self.gateway=books,pages,users,gateway
 def import_book(self,remote_id,user_id):
  r=self.gateway.get_book(remote_id)
  if not isinstance(r,dict):
   raise WikiDocsError(f'WikiDocs 도서 정보를 가져오지 못했습니다. (book_id={remote_id})')
  b=self.books.upsert({'wikidocs_book_id':remote_id,'title':r.get('title') or '제목 없음','author':r.get('author'),'description':r.get('description'),'cover_url':r.get('cover_url'),'url':r.get('url') or f'https://wikidocs.net/book/{remote_id}','page_count':r.get('page_count',0)})
  self.users.add(user_id,b);return b
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

# ===== application/reading_service.py =====
class ReadingService:
 def __init__(self,progress:ProgressStore,users:UserBookStore):self.progress,self.users=progress,users
 def _owned(self,u,b):return self.users.contains(u,b)
 def get_progress(self,u,b):return self.progress.get(u,b) if self._owned(u,b) else None
 def save_position(self,u,b,pid,pos,read,total):
  if not self._owned(u,b):raise PermissionError('책을 찾을 수 없습니다.')
  self.progress.save(u,b,pid,pos,read,total)
 def complete(self,u,b,total):self.save_position(u,b,None,1.0,total,total)
 def mark_unread(self,u,b):
  if not self._owned(u,b):raise PermissionError('책을 찾을 수 없습니다.')
  self.progress.mark_unread(u,b)
 def recent(self,u,limit=20):return self.progress.recent(u,limit)

# ===== application/search_service.py =====
class SearchService:
    def __init__(self, gateway, cache):
        self.gateway = gateway
        self.cache = cache

    def list_public(self, page=1, sort_type='recent'):
        page = max(1, int(page))
        sort_type = sort_type if sort_type in {'recent', 'recommend', 'popular'} else 'recent'
        key = cache_key('public-books', page, sort_type)
        hit = self.cache.get(key)
        if hit:
            return json.loads(hit)
        value = self.gateway.list_public(page=page, sort_type=sort_type)
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

# ===== application/cache_service.py =====
class CacheService:
 def __init__(self,repo): self.repo=repo
 def search(self,query,page,loader):
  key=cache_key('search',query,page)
  hit=self.repo.get(key)
  if hit is not None:return json.loads(hit)
  value=loader(); self.repo.set(key,json.dumps(value,ensure_ascii=False,separators=(',',':')),SEARCH_TTL); self.repo.purge(); self.repo.purge_to_size(MAX_CACHE_BYTES); return value

# ===== presentation/context.py =====
class UserContext:
 def current_user_id(self):raise NotImplementedError
class FlaskUserContext(UserContext):
 def current_user_id(self):
  from flask import session
  v=session.get('user_id')
  if v is None:
   x=session.get('user');v=x.get('id') if isinstance(x,dict) else None
  try:return int(v) if v is not None else None
  except (TypeError,ValueError):return None


# ===== wikidocs_reader.py provider =====
class WikidocsReaderMetadataProvider(BaseMetadataProvider):
 id='wikidocs_reader';name='WikiDocs';is_searchable=True;enabled=True
 category_tab={'title':'WikiDocs','icon':'fa-solid fa-book-open','order':80,'sessions':['general']}
 dashboard_widget={'title':'WikiDocs','subtitle':'최근 읽은 WikiDocs 책','provider':'WikiDocs','icon':'fa-solid fa-book-open','limit':20,'supported_types':['general']}
 config_schema=[]
 update_manifest={'enabled':True,'provider':'github-raw','raw_base_url':'https://raw.githubusercontent.com/C-Rhapsody/wikidocs_reader/main','files':['wikidocs_reader.py','__init__.py','script.js','index.html','style.css','requirements.txt','VERSION'],'version_file':'VERSION','version_key':'plugin version','show_sample_update_button':True}
 def __init__(self,db=None,gateway=None):
  gateway = gateway or self.get_db_gateway(db or 'general'); ensure_schema(gateway); client=WikiDocsClient(); books=BookRepository(gateway);pages=PageRepository(gateway);users=UserBookRepository(gateway);progress=ReadingProgressRepository(gateway)
  self.books=BookService(books,pages,users,client);self.reading=ReadingService(progress,users);self.search_service=SearchService(PublicBookSearch(client),CacheRepository(gateway))
 def search(self,db_type,query):
  try:return self.search_service.search(query)
  except WikiDocsError as exc:
   security_event('search_error', error_type=type(exc).__name__)
   return []
 def apply(self,db_type,book_id,item_data):
  try:
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
   u=FlaskUserContext().current_user_id()
   return {'success':True,'items':self.reading.recent(u,limit)} if u is not None else {'success':False,'error':'로그인이 필요합니다.'}
  except Exception as exc:
   security_event('dashboard_error', error_type=type(exc).__name__)
   return {'success':False,'items':[]}
