
import pytest
import os
import sys
from tempfile import TemporaryDirectory

# Add the parent directory to sys.path to allow importing from parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with TemporaryDirectory() as dir_path:
        yield dir_path