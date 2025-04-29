"""
Test script to verify that existing functionality still works.
"""

import os
import pytest
from message_parser import MessageParser


def test_parse_messages_def():
    """Test parsing of test_messages.def file."""
    # Use the file in the tests directory
    file_path = os.path.join(os.path.dirname(__file__), "test_messages.def")
    parser = MessageParser(file_path)
    model = parser.parse()

    assert model is not None, "Failed to parse test_messages.def"
    assert len(model.messages) > 0, "No messages were parsed from test_messages.def"


def test_parse_namespaces_def():
    """Test parsing of test_namespaces.def file."""
    # Use the file in the tests directory
    file_path = os.path.join(os.path.dirname(__file__), "test_namespaces.def")
    parser = MessageParser(file_path)
    model = parser.parse()

    assert model is not None, "Failed to parse test_namespaces.def"
    assert len(model.messages) > 0, "No messages were parsed from test_namespaces.def"
