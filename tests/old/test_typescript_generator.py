"""
Test TypeScript Generator

This module contains tests for the TypeScript generator.
"""

import os
import pytest

from typescript_generator import TypeScriptGenerator


import os
import pytest
from typescript_generator import TypeScriptGenerator

def test_generate(test_model, temp_dir):
    """Test generating TypeScript code."""
    generator = TypeScriptGenerator(test_model, temp_dir)
    result = generator.generate()
    assert result

    # Check that the output file exists
    output_file = os.path.join(temp_dir, f"{generator.output_name}_msgs.ts")
    assert os.path.exists(output_file)

    # Read the output file
    with open(output_file, 'r') as f:
        content = f.read()

    # Check that the content contains expected elements
    assert "export interface SimpleMessage" in content
    assert "export interface BaseMessage" in content
    assert "export interface DerivedMessage extends BaseMessage" in content
    assert "stringField: string" in content
    assert "intField: number" in content
    assert "floatField: number" in content
    assert "status: SimpleMessage_status_Enum" in content
    assert "export enum SimpleMessage_status_Enum" in content
    assert "OK = 0" in content
    assert "ERROR = 1" in content
    assert "PENDING = 2" in content
    assert "position: {" in content
    assert "x: number" in content
    assert "y: number" in content
    assert "z: number" in content
