import os
import sys
import tempfile
import re

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cpp_generator import UnrealCppGenerator
from message_parser import MessageParser

def fix_indentation():
    """Generate C++ code and fix indentation issues."""
    # Get the paths to the .def files
    base_file_path = os.path.join(os.path.dirname(__file__), "sh4c_base.def")
    comms_file_path = os.path.join(os.path.dirname(__file__), "sh4c_comms.def")

    # Parse the comms file (which imports the base file)
    parser = MessageParser(comms_file_path)
    model = parser.parse()
    assert model is not None, "Failed to parse sh4c_comms.def"

    # Create a temporary directory for output
    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate Unreal C++ code
        generator = UnrealCppGenerator(model, temp_dir)
        result = generator.generate()
        assert result, "Failed to generate Unreal C++ code"

        # Find the generated comms file
        comms_file = os.path.join(temp_dir, "ue_sh4c_comms_msgs.h")
        assert os.path.exists(comms_file), f"Generated comms file not found: {comms_file}"

        # Read the comms file
        with open(comms_file, 'r') as f:
            content = f.read()

        # Fix indentation issues
        # 1. Find all enums that are directly inside the namespace (not inside a nested namespace)
        # These are the enums that have 8 spaces of indentation but should have 4
        fixed_content = content
        
        # Find the start of the namespace
        namespace_match = re.search(r'namespace ue_sh4c_comms {', content)
        if namespace_match:
            namespace_start = namespace_match.end()
            
            # Find all enum definitions that are directly inside the namespace
            enum_pattern = re.compile(r'(\s{8})(// Enum for .+?\n\s{8}enum class .+?{.+?};)', re.DOTALL)
            fixed_content = enum_pattern.sub(r'    \2', content[namespace_start:])
            
            # Restore the content before the namespace
            fixed_content = content[:namespace_start] + fixed_content
        
        # Print the fixed content
        print(fixed_content)

if __name__ == "__main__":
    fix_indentation()