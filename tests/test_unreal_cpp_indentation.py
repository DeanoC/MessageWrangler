import os
import sys
import tempfile

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cpp_generator import UnrealCppGenerator
from message_parser import MessageParser

def test_unreal_cpp_indentation():
    """Test the indentation in the generated Unreal C++ code."""
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
            print(content)

if __name__ == "__main__":
    test_unreal_cpp_indentation()
