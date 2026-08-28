from pathlib import Path
ROOT=Path(__file__).parents[1]/'plugins'/'metadata'/'wikidocs_reader'

def test_plugin_uses_core_contract():
 text=(ROOT/'plugin.py').read_text()
 assert 'from plugins.metadata.base import BaseMetadataProvider' in text
 assert 'self.get_db_gateway' in text
 assert 'update_manifest' in text
 assert 'class BaseMetadataProvider' not in text
 assert 'from .infrastructure.database import Database' not in text

def test_plugin_has_no_direct_database_dependency():
 for p in ROOT.rglob('*.py'):
  text=p.read_text()
  assert 'import database' not in text
  assert 'sqlite3' not in text

def test_update_manifest_declares_version_and_runtime_files():
 import ast
 tree=ast.parse((ROOT/'plugin.py').read_text())
 cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='WikidocsReaderMetadataProvider')
 assigns={n.targets[0].id:n.value for n in cls.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
 manifest=ast.literal_eval(assigns['update_manifest'])
 assert manifest['enabled'] is True
 assert manifest['provider']=='github-raw'
 assert manifest['version_key']=='plugin version'
 assert 'VERSION' in manifest['files']
 assert (ROOT/'VERSION').read_text().strip().startswith('{')

def test_no_committed_pycache_or_runtime_data():
 import subprocess
 tracked=subprocess.check_output(['git','ls-files',str(ROOT)],text=True).splitlines()
 deleted=set(subprocess.check_output(['git','ls-files','-d',str(ROOT)],text=True).splitlines())
 tracked=[p for p in tracked if p not in deleted]
 assert not any('__pycache__' in p or p.endswith(('.pyc','.sqlite3','.sqlite3-wal','.sqlite3-shm')) or p.endswith('/security.log') for p in tracked)

def test_book_service_uses_remote_wikidocs_gateway():
 import ast
 tree=ast.parse((ROOT/'plugin.py').read_text())
 cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='WikidocsReaderMetadataProvider')
 init=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
 src=ast.get_source_segment((ROOT/'plugin.py').read_text(), init)
 assert 'BookService(books,pages,users,client)' in src
 assert 'SearchService(PublicBookSearch(client)' in src
