"""
Configuration des tests
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Répertoire temporaire pour les tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_system_info():
    """Informations système simulées"""
    return {
        "distro": "ubuntu",
        "version": "22.04",
        "arch": "x86_64",
        "cpu_count": 4,
        "ram_gb": 8.0,
        "disk_free_gb": 50.0,
    }
