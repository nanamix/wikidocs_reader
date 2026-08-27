from __future__ import annotations
import json
from typing import Any
from bs4 import BeautifulSoup
from curl_cffi import requests

BASE_URL = "https://wikidocs.net"


class WikiDocsError(RuntimeError):
    pass


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
                "content_html": str(content), "url": f"https://wikidocs.net/{page_id}"}
