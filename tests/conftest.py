
import sys
import os
from tempfile import TemporaryDirectory
import pytest
# Ensure the project root is on sys.path for all tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with TemporaryDirectory() as dir_path:
        yield dir_path