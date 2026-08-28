from pathlib import Path
import ast
import subprocess

ROOT=Path(__file__).parents[1]/'plugins'/'metadata'/'wikidocs_reader'
MODULE=ROOT/'wikidocs_reader.py'


def _provider_class():
    tree=ast.parse(MODULE.read_text())
    return next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='WikidocsReaderMetadataProvider')


def test_reference_repo_root_layout():
    assert MODULE.exists()
    assert (ROOT/'__init__.py').exists()
    for name in ('index.html','script.js','style.css','requirements.txt','VERSION'):
        assert (ROOT/name).exists()
    assert not (ROOT/'application').exists()
    assert not (ROOT/'domain').exists()
    assert not (ROOT/'infrastructure').exists()
    assert not (ROOT/'presentation').exists()
    assert not (ROOT/'wikidocs').exists()
    assert not (ROOT/'plugin.py').exists()
    assert (ROOT/'README.md').exists()


def test_plugin_uses_core_contract_and_matching_names():
    text=MODULE.read_text()
    cls=_provider_class()
    assert 'from plugins.metadata.base import BaseMetadataProvider' in text
    assert 'class WikidocsReaderMetadataProvider(BaseMetadataProvider)' in text
    assert "id = 'wikidocs_reader'" in text or "id='wikidocs_reader'" in text
    assert 'self.get_db_gateway' in text
    assert 'update_manifest' in text
    assert 'import database' not in text
    assert 'sqlite3' not in text
    assert 'security_event' in text
    assert any(isinstance(b,ast.FunctionDef) and b.name=='search' for b in cls.body)
    assert any(isinstance(b,ast.FunctionDef) and b.name=='apply' for b in cls.body)


def test_update_manifest_declares_flat_runtime_files():
    cls=_provider_class()
    assigns={n.targets[0].id:n.value for n in cls.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
    manifest=ast.literal_eval(assigns['update_manifest'])
    assert manifest['enabled'] is True
    assert manifest['provider']=='github-raw'
    assert manifest['version_key']=='plugin version'
    assert manifest['files']==['wikidocs_reader.py','__init__.py','script.js','index.html','style.css','requirements.txt','VERSION']
    assert (ROOT/'VERSION').read_text().strip().startswith('{')


def test_no_committed_runtime_artifacts():
    tracked=subprocess.check_output(['git','ls-files',str(ROOT)],text=True).splitlines()
    assert not any('__pycache__' in p or p.endswith(('.pyc','.sqlite3','.sqlite3-wal','.sqlite3-shm')) or p.endswith('/security.log') for p in tracked)
