from pathlib import Path
import sys

# Vendored runtime dependencies follow the same root-level plugin layout as
# bookoasis_gamebooks while remaining isolated from Core.
_LIBS = Path(__file__).resolve().parent / 'libs'
if str(_LIBS) not in sys.path:
    sys.path.insert(0, str(_LIBS))

from .wikidocs_reader import WikidocsReaderMetadataProvider

__all__ = ["WikidocsReaderMetadataProvider"]
