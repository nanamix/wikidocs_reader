from unittest.mock import Mock

import pytest
import wikidocs_reader as plugin


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(plugin.FlaskUserContext, 'current_user_id', lambda self: 7)
    result = object.__new__(plugin.WikidocsReaderMetadataProvider)
    result.books = Mock()
    result.reading = Mock()
    result.search_service = Mock()
    return result


@pytest.mark.parametrize('user_id,owned', [(7, True), (8, False), (None, False)])
def test_public_books_uses_current_users_membership(provider, monkeypatch, user_id, owned):
    monkeypatch.setattr(plugin.FlaskUserContext, 'current_user_id', lambda self: user_id)
    cached = {'wikidocs_book_id': 10, 'title': 'Book'}
    provider.search_service.list_public.return_value = [cached]
    provider.books.get_by_remote_id.return_value = {'id': 10}
    provider.books.contains.side_effect = lambda u, b: u == 7 and b == 10
    result = provider.run_context_menu_action('general', 'wikidocs_rpc', {'op': 'public_books'})
    assert result['success']
    assert result['items'][0]['in_my_books'] is owned
    assert 'in_my_books' not in cached
    if user_id is None:
        provider.books.contains.assert_not_called()


@pytest.mark.parametrize('page', [None, {'book_id': 20}])
def test_progress_rejects_missing_or_foreign_page(provider, page):
    provider.books.pages.get.return_value = page
    result = provider.run_context_menu_action('general', 'wikidocs_rpc', {
        'op': 'progress', 'book_id': 10, 'page_id': 99,
    })
    assert not result['success']
    provider.reading.save_position.assert_not_called()


def test_progress_accepts_page_of_current_book(provider):
    provider.books.pages.get.return_value = {'book_id': 10}
    result = provider.run_context_menu_action('general', 'wikidocs_rpc', {
        'op': 'progress', 'book_id': 10, 'page_id': '99',
    })
    assert result['success']
    provider.reading.save_position.assert_called_once_with(7, 10, 99, 0, 0, 0)


def test_security_log_skips_non_object_records(tmp_path, monkeypatch):
    path = tmp_path / 'security.log'
    monkeypatch.setattr(plugin, 'LOG_PATH', path)
    path.write_text('[]\nnull\n42\n"bad"\n')
    plugin.security_event('recovered')
    import json
    assert [json.loads(line)['event'] for line in path.read_text().splitlines()] == ['recovered']
