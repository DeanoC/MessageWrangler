"""
Test Duplicate Messages

This module contains tests for the duplicate message detection.
"""

import os
import pytest
from message_parser import MessageParser

def test_duplicate_message_detection():
    """Test detection of duplicate message definitions."""
    # Get the path to the test file
    test_file = os.path.join(os.path.dirname(__file__), "test_duplicate_messages.def")

    # Parse the file
    parser = MessageParser(test_file)
    model = parser.parse()

    # Check that there are errors
    assert parser.errors, "Expected parser errors for duplicate message definitions"
    
    # Check that the error message contains the expected text
    error_found = False
    for error in parser.errors:
        if "Duplicate message definition 'ClientCommands::ChangeMode'" in error:
            error_found = True
            break
    
    assert error_found, "Expected error message for duplicate message definition not found"
    
    # The model should be None because parsing failed
    assert model is None, "Expected model to be None when parsing fails"