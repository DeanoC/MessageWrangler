import os
import tempfile
import shutil
import re
from message_parser_core import MessageParser
from cpp_generator import StandardCppGenerator
from tests.test_utils import randomize_def_file

def main():
    # Get the path to the original file
    original_file = os.path.join('tests', 'test_enum_inheritance.def')
    
    # Create a randomized version of the file
    temp_dir, random_file_path, name_mapping = randomize_def_file(original_file)
    
    try:
        # Get the directory and filename of the random file
        random_file_dir = os.path.dirname(random_file_path)
        random_file_name = os.path.basename(random_file_path)
        
        # Store the original directory
        original_dir = os.getcwd()
        
        # Change to the directory containing the random file
        os.chdir(random_file_dir)
        
        # Parse the randomized file, passing the temporary directory as the base directory
        parser = MessageParser(random_file_name, verbose=True, base_dir=temp_dir)
        model = parser.parse()
        
        # Change back to the original directory
        os.chdir(original_dir)
        
        # Create a temporary directory for output
        with tempfile.TemporaryDirectory() as output_dir:
            # Generate standard C++ code
            generator = StandardCppGenerator(model, output_dir)
            result = generator.generate()
            
            # Find the generated C++ files
            cpp_files = [f for f in os.listdir(output_dir) if f.endswith('_msgs.h')]
            
            # Print the content of each file
            for file_name in cpp_files:
                with open(os.path.join(output_dir, file_name), 'r') as f:
                    content = f.read()
                print(f'\n\n===== {file_name} =====\n{content}')
                
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

if __name__ == '__main__':
    main()