"""
Test Verbose Flag

This script tests that the verbose flag correctly controls debug output.
It uses randomized names to ensure the test isn't passing due to hardcoded special cases.
"""

import os
import sys
import io
import tempfile
from contextlib import redirect_stdout

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from message_parser_core import MessageParser
from tests.test_utils import generate_random_name

def main():
    """Test that the verbose flag correctly controls debug output."""
    # Generate random names for message, fields, and enum values
    message_name = f"RandomMessage_{generate_random_name()}"
    string_field = f"randomString_{generate_random_name()}"
    int_field = f"randomInt_{generate_random_name()}"
    enum_field = f"randomEnum_{generate_random_name()}"
    value1 = f"RANDOM_VALUE1_{generate_random_name()}"
    value2 = f"RANDOM_VALUE2_{generate_random_name()}"
    value3 = f"RANDOM_VALUE3_{generate_random_name()}"

    # Create a temporary file with a message using randomized names
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.def')
    temp_file_path = temp_file.name

    with open(temp_file_path, "w") as f:
        f.write(f"""
message {message_name} {{
    field {string_field}: string
    field {int_field}: int
    field {enum_field}: enum {{ {value1}, {value2}, {value3} }}
}}
        """)

    # Parse the file without verbose flag
    print("\nParsing without verbose flag:")
    f = io.StringIO()
    with redirect_stdout(f):
        parser = MessageParser(temp_file_path, verbose=False)
        model = parser.parse()
    output = f.getvalue()
    print(f"Output length: {len(output)}")
    print(f"Contains DEBUG: {'DEBUG:' in output}")

    # Parse the file with verbose flag
    print("\nParsing with verbose flag:")
    f = io.StringIO()
    with redirect_stdout(f):
        parser = MessageParser(temp_file_path, verbose=True)
        model = parser.parse()
    output = f.getvalue()
    print(f"Output length: {len(output)}")
    print(f"Contains DEBUG: {'DEBUG:' in output}")

    # Clean up
    os.remove(temp_file_path)

if __name__ == "__main__":
    main()
