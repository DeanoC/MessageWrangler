import os
import sys
import tempfile

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cpp_generator import UnrealCppGenerator
from message_parser_core import MessageParser
from tests.test_utils import randomize_def_file, cleanup_temp_dir

def test_unreal_cpp_indentation():
    """Test the indentation in the generated Unreal C++ code."""
    # Get the paths to the original .def files
    base_file_path = os.path.join(os.path.dirname(__file__), "sh4c_base.def")
    comms_file_path = os.path.join(os.path.dirname(__file__), "sh4c_comms.def")

    # Create randomized versions of the files
    base_temp_dir, random_base_path, base_name_mapping = randomize_def_file(base_file_path)
    comms_temp_dir, random_comms_path, comms_name_mapping = randomize_def_file(comms_file_path)

    try:
        # Get the directory and filename of the random files
        random_base_dir = os.path.dirname(random_base_path)
        random_base_name = os.path.basename(random_base_path)
        random_comms_dir = os.path.dirname(random_comms_path)
        random_comms_name = os.path.basename(random_comms_path)

        # Copy the randomized base file to the comms directory
        import shutil
        base_in_comms_dir = os.path.join(random_comms_dir, random_base_name)
        shutil.copy(random_base_path, base_in_comms_dir)

        # Update the import statement in the randomized comms file
        with open(random_comms_path, 'r') as f:
            comms_content = f.read()

        # Replace the import statement
        import re
        updated_comms_content = re.sub(
            r'import\s+"./sh4c_base.def"\s+as\s+Base',
            f'import "./{random_base_name}" as Base',
            comms_content
        )

        with open(random_comms_path, 'w') as f:
            f.write(updated_comms_content)

        # Store the original directory
        original_dir = os.getcwd()

        # Change to the directory containing the random comms file
        os.chdir(random_comms_dir)

        # Parse the randomized comms file (which imports the randomized base file)
        parser = MessageParser(random_comms_name)
        model = parser.parse()
        assert model is not None, f"Failed to parse {random_comms_name}"

        # Create a temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate Unreal C++ code
            generator = UnrealCppGenerator(model, temp_dir)
            result = generator.generate()
            assert result, "Failed to generate Unreal C++ code"

            # Find the generated comms file
            output_name = "ue_" + random_comms_name.replace(".def", "")
            comms_file = os.path.join(temp_dir, f"{output_name}_msgs.h")
            assert os.path.exists(comms_file), f"Generated comms file not found: {comms_file}"

            # Read the comms file
            with open(comms_file, 'r') as f:
                content = f.read()
                print(content)

        # Change back to the original directory
        os.chdir(original_dir)
    finally:
        # Clean up the temporary directories
        cleanup_temp_dir(base_temp_dir)
        cleanup_temp_dir(comms_temp_dir)

if __name__ == "__main__":
    test_unreal_cpp_indentation()
