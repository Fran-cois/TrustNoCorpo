import os
import sys
import shutil
import tempfile
from pathlib import Path

import pytest

# Ensure `import TrustNoCorpo` works: add parent of repo root to sys.path
_repo_root = Path(__file__).resolve().parents[1]
_repo_parent = _repo_root.parent
if str(_repo_parent) not in sys.path:
    sys.path.insert(0, str(_repo_parent))


@pytest.fixture()
def temp_home(monkeypatch, tmp_path):
    # Isolate user home for KeyManager (~/.trustnocorpo)
    monkeypatch.setenv("HOME", str(tmp_path))
    # Some systems also use USERPROFILE
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return tmp_path


@pytest.fixture()
def temp_project(tmp_path):
    # Create a temporary project directory
    proj = tmp_path / "proj"
    proj.mkdir()
    return proj
