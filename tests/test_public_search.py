from wikidocs_reader import PublicBookSearch


class FakeClient:
    def search_public_books(self, query, page=1):
        assert query == "파이썬"
        assert page == 1
        return '''<div class="book-item"><a href="/book/1" class="book-subject">점프 투 파이썬</a></div>
        <div class="book-item"><a href="/book/922" class="book-subject">초보자를 위한 파이썬 300제</a></div>'''


def test_public_book_search_parses_html():
    results = PublicBookSearch(FakeClient()).search("파이썬")
    assert results == [
        {"wikidocs_book_id": 1, "title": "점프 투 파이썬", "author": None, "published_at": None, "url": "https://wikidocs.net/book/1"},
        {"wikidocs_book_id": 922, "title": "초보자를 위한 파이썬 300제", "author": None, "published_at": None, "url": "https://wikidocs.net/book/922"},
    ]
