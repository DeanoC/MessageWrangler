import os
import sys

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from message_parser_core import MessageParser
from cpp_generator import UnrealCppGenerator
from tests.test_utils import randomize_def_file, cleanup_temp_dir

def main():
    # Get the path to the original file
    original_file = os.path.join(os.path.dirname(__file__), "sh4c_comms.def")

    # Create a randomized version of the file
    temp_dir, random_file_path, name_mapping = randomize_def_file(original_file)

    try:
        # Get the directory and filename of the random file
        random_file_dir = os.path.dirname(random_file_path)
        random_file_name = os.path.basename(random_file_path)

        # Change to the directory containing the random file
        original_dir = os.getcwd()
        os.chdir(random_file_dir)

        # Parse the randomized file
        parser = MessageParser(random_file_name, verbose=True)
        model = parser.parse()

        if model:
            # Generate the C++ code with a random output name
            output_name = "ue_" + random_file_name.replace(".def", "")
            generator = UnrealCppGenerator(model, ".", output_name)
            generator.generate()
            print(f"Generated C++ code for {random_file_name}")
        else:
            print(f"Failed to parse {random_file_name}")

        # Change back to the original directory
        os.chdir(original_dir)
    finally:
        # Clean up the temporary directory
        cleanup_temp_dir(temp_dir)

if __name__ == "__main__":
    main()
