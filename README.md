# WikiDocs

BookOasis WikiDocs metadata/dashboard plugin.

The plugin follows the same root-level layout as `bookoasis_gamebooks`:

- `wikidocs_reader.py` — provider and all plugin implementation code
- `__init__.py` — provider export and vendored dependency bootstrap
- `index.html`, `script.js`, `style.css` — plugin UI
- `requirements.txt` — plugin-local dependencies
- `VERSION` — automatic-update version contract

Runtime data is stored through the BookOasis Core DB gateway; no plugin-owned
SQLite database is required.
