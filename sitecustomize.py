"""Test/runtime helper to ensure project packages are importable.

Some environments (notably certain pytest runners) may not add the repository root
to sys.path early enough. Python automatically imports `sitecustomize` (if found)
when the interpreter starts, so we use it to force the root on sys.path.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
root_str = str(ROOT)

if root_str not in sys.path:
    sys.path.insert(0, root_str)

