from __future__ import annotations
from dataclasses import dataclass
from bs4 import BeautifulSoup
from .client import WikiDocsClient

@dataclass(frozen=True, slots=True)
class PublicBookSearchResult:
    wikidocs_book_id: int
    title: str
    url: str

class PublicBookSearch:
    def __init__(self, client: WikiDocsClient | None = None):
        self.client = client or WikiDocsClient()

    def list_public(self, page: int = 1) -> list[dict[str, object]]:
        return self._parse(self.client.list_public_books(page=page, sort_type="recent"))

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
