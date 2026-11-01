import sqlite3
from types import SimpleNamespace

import pytest

from wikidocs_reader import ensure_schema


def test_sqlite_schema_initialization_is_repeatable_and_preserves_data():
    with sqlite3.connect(':memory:') as db:
        gateway = SimpleNamespace(execute=db.execute)
        ensure_schema(gateway)
        db.execute("INSERT INTO wikidocs_books(id,wikidocs_book_id,title) VALUES(1,1,'book')")
        ensure_schema(gateway)
        assert db.execute('SELECT title FROM wikidocs_books').fetchone() == ('book',)
        for name, columns in [
            ('idx_wikidocs_user_books_user', ['user_id', 'updated_at']),
            ('idx_wikidocs_progress_user_last_read', ['user_id', 'last_read_at']),
        ]:
            rows = db.execute(f'PRAGMA index_info({name})').fetchall()
            assert [row[2] for row in rows] == columns


@pytest.mark.parametrize('engine', ['mysql', 'mariadb'])
def test_mysql_schema_retains_text_index_prefixes(engine):
    statements = []
    ensure_schema(SimpleNamespace(_engine=engine, execute=statements.append))
    indexes = '\n'.join(sql for sql in statements if sql.startswith('CREATE INDEX'))
    assert 'updated_at(255)' in indexes
    assert 'last_read_at(255)' in indexes
