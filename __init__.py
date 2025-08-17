"""
TrustNoCorpo compatibility shim
===============================

This root package now forwards to the maintained implementation under `tnc`.
It exists only to preserve backward compatibility for imports such as:

  from TrustNoCorpo.core import trustnocorpo
  from TrustNoCorpo.keys import KeyManager

New code should import from `tnc` directly.
"""

from importlib import import_module
import sys as _sys

__version__ = "1.0.1"
__author__ = "TrustNoCorpo Security Team"
__license__ = "MIT"

# Re-export primary symbols from tnc
from tnc.core import trustnocorpo  # type: ignore
from tnc.keys import KeyManager  # type: ignore
from tnc.protector import PDFProtector  # type: ignore
from tnc.logger import BuildLogger  # type: ignore

__all__ = [
    "trustnocorpo",
    "KeyManager",
    "PDFProtector",
    "BuildLogger",
]

# Provide submodule compatibility: TrustNoCorpo.core, TrustNoCorpo.keys, ...
for _name in ("core", "keys", "protector", "logger", "cli"):
    try:
        _mod = import_module(f"tnc.{_name}")
        _sys.modules[f"TrustNoCorpo.{_name}"] = _mod
    except Exception:
        # If a module doesn't exist, ignore to avoid import-time failures.
        pass

