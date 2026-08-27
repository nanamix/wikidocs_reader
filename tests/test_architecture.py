from pathlib import Path
ROOT=Path(__file__).parents[1]/'plugins'/'metadata'/'wikidocs_reader'
def test_core_db_gateway_is_not_referenced():
 for p in ROOT.rglob('*.py'):
  text=p.read_text();assert 'get_db_gateway' not in text;assert 'PluginDatabaseGateway' not in text

def test_application_has_no_sql_or_flask():
 for p in (ROOT/'application').rglob('*.py'):
  text=p.read_text();assert 'sqlite3' not in text;assert 'from flask' not in text;assert 'import flask' not in text

def test_domain_has_no_framework_or_infrastructure_imports():
 for p in (ROOT/'domain').rglob('*.py'):
  text=p.read_text();assert 'flask' not in text.lower();assert 'sqlite' not in text.lower();assert 'infrastructure' not in text.lower()
