from pathlib import Path
import sys

# Plugin dependencies are vendored under libs/. Add them before importing
# the provider so direct Core imports work even when dependency installation
# is skipped by the plugin dependency cache.
_LIBS = Path(__file__).resolve().parent / 'libs'
if str(_LIBS) not in sys.path:
    sys.path.insert(0, str(_LIBS))

from .plugin import WikidocsReaderMetadataProvider

__all__ = ["WikidocsReaderMetadataProvider"]
