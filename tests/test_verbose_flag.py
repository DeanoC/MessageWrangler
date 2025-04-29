"""
Test Verbose Flag

This script tests that the verbose flag correctly controls debug output.
"""

import os
import sys
import io
from contextlib import redirect_stdout

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from message_parser import MessageParser

def main():
    """Test that the verbose flag correctly controls debug output."""
    # Create a temporary file with a simple message
    with open("tests/temp_verbose_test.def", "w") as f:
        f.write("""
message SimpleMessage {
    field stringField: string
    field intField: int
    field enumField: enum { Value1, Value2, Value3 }
}
        """)

    # Parse the file without verbose flag
    print("\nParsing without verbose flag:")
    f = io.StringIO()
    with redirect_stdout(f):
        parser = MessageParser("tests/temp_verbose_test.def", verbose=False)
        model = parser.parse()
    output = f.getvalue()
    print(f"Output length: {len(output)}")
    print(f"Contains DEBUG: {'DEBUG:' in output}")

    # Parse the file with verbose flag
    print("\nParsing with verbose flag:")
    f = io.StringIO()
    with redirect_stdout(f):
        parser = MessageParser("tests/temp_verbose_test.def", verbose=True)
        model = parser.parse()
    output = f.getvalue()
    print(f"Output length: {len(output)}")
    print(f"Contains DEBUG: {'DEBUG:' in output}")

    # Clean up
    os.remove("tests/temp_verbose_test.def")

if __name__ == "__main__":
    main()