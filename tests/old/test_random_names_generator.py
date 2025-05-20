import os
import sys
import random
import string
import re
import tempfile
import shutil

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from message_parser_core import MessageParser
from cpp_generator import UnrealCppGenerator

def generate_random_name(length=8):
    """Generate a random name with the specified length."""
    return ''.join(random.choice(string.ascii_letters) for _ in range(length))

def create_name_mapping(content):
    """Create a mapping of original names to random names."""
    # Find all message, enum, and field names
    message_pattern = r'message\s+(\w+)'
    enum_pattern = r'enum\s+(\w+)'
    field_pattern = r'field\s+(\w+)'
    namespace_pattern = r'namespace\s+(\w+)'

    # Patterns for enum values
    # This pattern matches enum values in regular enum definitions
    enum_value_pattern = r'enum\s+\w+(?:\s*:\s*\w+(?:::\w+)*(?:\.\w+)*)?\s*(?:\+\s*enum)?\s*\{[^}]*?\}'
    # This pattern matches enum values in field definitions with enum type
    field_enum_value_pattern = r'field\s+\w+\s*:\s*enum\s*\{[^}]*?\}'
    # This pattern matches options values
    options_value_pattern = r'field\s+\w+\s*:\s*options\s*\{[^}]*?\}'

    names = []

    # Extract message names
    for match in re.finditer(message_pattern, content):
        names.append(match.group(1))

    # Extract enum names
    for match in re.finditer(enum_pattern, content):
        names.append(match.group(1))

    # Extract field names
    for match in re.finditer(field_pattern, content):
        names.append(match.group(1))

    # Extract namespace names
    for match in re.finditer(namespace_pattern, content):
        names.append(match.group(1))

    # Helper function to extract enum values from a block of text
    def extract_enum_values(text):
        # Find all words inside braces
        brace_start = text.find('{')
        brace_end = text.rfind('}')
        if brace_start != -1 and brace_end != -1:
            brace_content = text[brace_start+1:brace_end]
            # Split by commas and extract words
            for item in brace_content.split(','):
                # Extract the word before any equals sign or comment
                item = item.strip()
                if item:
                    # Get the word before any equals sign
                    if '=' in item:
                        item = item.split('=')[0].strip()
                    # Remove any comments
                    if '//' in item:
                        item = item.split('//')[0].strip()
                    # Check if it's a valid identifier
                    if item and item.isidentifier():
                        # Skip keywords
                        if item not in ['enum', 'message', 'field', 'namespace', 'options'] and not item.isdigit():
                            names.append(item)

    # Extract enum values from regular enum definitions
    for match in re.finditer(enum_value_pattern, content):
        extract_enum_values(match.group(0))

    # Extract enum values from field enum definitions
    for match in re.finditer(field_enum_value_pattern, content):
        extract_enum_values(match.group(0))

    # Extract values from options fields
    for match in re.finditer(options_value_pattern, content):
        extract_enum_values(match.group(0))

    # Create mapping
    name_mapping = {}
    for name in names:
        if name not in name_mapping:
            name_mapping[name] = generate_random_name()

    return name_mapping

def replace_names(content, name_mapping, namespace_mapping=None):
    """Replace all occurrences of names with their random equivalents."""
    # First replace namespace references (e.g., Base::Command)
    if namespace_mapping:
        for original_ns, random_ns in namespace_mapping.items():
            pattern = r'\b' + re.escape(original_ns) + r'::'
            content = re.sub(pattern, random_ns + '::', content)

    # Then replace individual names
    for original_name, random_name in name_mapping.items():
        # Use word boundaries to ensure we only replace whole words
        pattern = r'\b' + re.escape(original_name) + r'\b'
        content = re.sub(pattern, random_name, content)

    return content

def generate_random_files():
    """Generate random versions of sh4c_base.def and sh4c_comms.def in a temporary directory."""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()

    # Read the original files
    base_file_path = os.path.join(os.path.dirname(__file__), "sh4c_base.def")
    comms_file_path = os.path.join(os.path.dirname(__file__), "sh4c_comms.def")

    with open(base_file_path, 'r') as f:
        base_content = f.read()

    with open(comms_file_path, 'r') as f:
        comms_content = f.read()

    # Create name mappings
    base_mapping = create_name_mapping(base_content)
    comms_mapping = create_name_mapping(comms_content)

    # Combine mappings to ensure consistency
    combined_mapping = {**base_mapping, **comms_mapping}

    # Generate random names for the files
    random_base_name = f"random_{generate_random_name()}_base.def"
    random_comms_name = f"random_{generate_random_name()}_comms.def"

    # Create a random name for the Base namespace
    random_base_namespace = combined_mapping.get("Base", generate_random_name())
    namespace_mapping = {"Base": random_base_namespace}

    # Replace "Base" with a random name in the import statement
    import_pattern = r'import\s+"./sh4c_base.def"\s+as\s+Base'
    random_import = f'import "./{random_base_name}" as {random_base_namespace}'
    comms_content = re.sub(import_pattern, random_import, comms_content)

    # Replace all other names
    base_content = replace_names(base_content, combined_mapping)
    comms_content = replace_names(comms_content, combined_mapping, namespace_mapping)

    # Write the new files to the temporary directory
    random_base_path = os.path.join(temp_dir, random_base_name)
    random_comms_path = os.path.join(temp_dir, random_comms_name)

    with open(random_base_path, 'w') as f:
        f.write(base_content)

    with open(random_comms_path, 'w') as f:
        f.write(comms_content)

    return temp_dir, random_base_name, random_comms_name

def create_test_script(temp_dir, random_comms_name):
    """Create a test script for the randomly generated files."""
    test_script_name = f"test_{random_comms_name.replace('.def', '')}.py"
    test_script_path = os.path.join(temp_dir, test_script_name)

    test_script_content = f"""import os
import sys

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from message_parser_core import MessageParser
from cpp_generator import UnrealCppGenerator

def test_random_comms():
    # Parse the {random_comms_name} file
    parser = MessageParser("{random_comms_name}", verbose=True)
    model = parser.parse()

    if model:
        # Generate the C++ code
        output_name = "ue_" + "{random_comms_name}".replace(".def", "")
        generator = UnrealCppGenerator(model, os.path.dirname(__file__), output_name)
        generator.generate()
        print(f"Generated C++ code for {random_comms_name}")
        return True
    else:
        print(f"Failed to parse {random_comms_name}")
        return False

if __name__ == "__main__":
    test_random_comms()
"""

    with open(test_script_path, 'w') as f:
        f.write(test_script_content)

    return test_script_name

def main():
    """Generate random files and create a test script."""
    try:
        # Generate random files in a temporary directory
        temp_dir, random_base_name, random_comms_name = generate_random_files()
        test_script_name = create_test_script(temp_dir, random_comms_name)

        print(f"Generated random files in temporary directory: {temp_dir}")
        print(f"Random files: {random_base_name}, {random_comms_name}")
        print(f"Created test script: {test_script_name}")

        # Change to the temporary directory to run the test
        original_dir = os.getcwd()
        os.chdir(temp_dir)

        print(f"Running test script: {test_script_name}")

        # Import and run the test function
        sys.path.append(temp_dir)
        module_name = test_script_name.replace('.py', '')
        test_module = __import__(module_name)
        result = test_module.test_random_comms()

        # Change back to the original directory
        os.chdir(original_dir)

        if result:
            print("Test passed!")
        else:
            print("Test failed!")

        return result
    finally:
        # Clean up the temporary directory
        if 'temp_dir' in locals():
            print(f"Cleaning up temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
