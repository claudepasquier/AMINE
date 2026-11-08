"""Shared pytest configuration for the AMINE test-suite.

The package lives under ``src/`` (src-layout). We add it to ``sys.path`` so the
tests can import ``amine`` without requiring an editable install.
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for path in (str(SRC), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)
