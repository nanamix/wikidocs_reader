"""Pytest bootstrap for the repository-root plugin module.

The production plugin intentionally has a root-level ``wikidocs_reader.py`` and
``__init__.py`` because Stable loads the provider from the plugin directory.
When pytest is launched from this repository, Python may prefer the repository
package named ``wikidocs_reader`` over the module file. Load the provider module
explicitly so tests exercise the same source file Stable loads.
"""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "wikidocs_reader.py"

spec = spec_from_file_location("wikidocs_reader", MODULE_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Unable to load plugin module: {MODULE_PATH}")
module = module_from_spec(spec)
sys.modules["wikidocs_reader"] = module
spec.loader.exec_module(module)
