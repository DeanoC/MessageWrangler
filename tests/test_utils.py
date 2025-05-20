import os
import random
import string
import re
import tempfile
import shutil
import sys

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

def randomize_def_file(file_path):
    """
    Create a randomized version of a .def file, handling imports recursively.

    Args:
        file_path: Path to the original .def file

    Returns:
        tuple: (temp_dir, random_file_path, name_mapping)
            - temp_dir: Temporary directory where the random file and its imported files are created
            - random_file_path: Path to the randomized main file
            - name_mapping: Dictionary mapping original names to random names from the main file and all imported files
    """
    # Create a temporary directory to store the randomized file and any imported files
    temp_dir = tempfile.mkdtemp()
    print(f"DEBUG: Created temporary directory: {temp_dir}")

    # Read the original file
    with open(file_path, 'r') as f:
        content = f.read()
    print(f"DEBUG: Original file content: \n{content}")

    # Find all import statements - Modified to handle paths with ./ prefix
    import_pattern = r'import\s+"(\.?/?(\w+\.def))"'
    imports_match = re.findall(import_pattern, content)
    imports = [match[1] for match in imports_match]  # Extract just the filename
    print(f"DEBUG: Found imports: {imports}")
    print(f"DEBUG: Full import matches: {imports_match}")

    # Initialize combined name mapping with main file's mapping
    combined_name_mapping = create_name_mapping(content)

    # Process imported files recursively
    for i, original_import in enumerate(imports):
        print(f"DEBUG: Processing import: {original_import}")
        imported_file_path = os.path.join(os.path.dirname(file_path), original_import)
        print(f"DEBUG: Imported file path: {imported_file_path}")
        
        # Recursively randomize the imported file
        imported_temp_dir, random_imported_file_path, imported_name_mapping = randomize_def_file(imported_file_path)
        print(f"DEBUG: Randomized imported file path: {random_imported_file_path}")

        # Copy the randomized imported file to the main temporary directory
        shutil.copy(random_imported_file_path, temp_dir)
        print(f"DEBUG: Copied {random_imported_file_path} to {temp_dir}")
        
        # List files in temp_dir after copying
        print(f"DEBUG: Files in {temp_dir} after copying: {os.listdir(temp_dir)}")

        # Clean up the temporary directory created for the imported file
        cleanup_temp_dir(imported_temp_dir)
        print(f"DEBUG: Cleaned up temporary directory: {imported_temp_dir}")

        # Update the import path in the main file content to use the randomized filename
        original_imported_filename = original_import
        full_import_path = imports_match[i][0]  # Get the full import path including ./ if present
        random_imported_filename = os.path.basename(random_imported_file_path)
        print(f"DEBUG: Original imported filename: {original_imported_filename}")
        print(f"DEBUG: Full import path: {full_import_path}")
        print(f"DEBUG: Randomized imported filename: {random_imported_filename}")
        
        # Print the content before replacement
        print(f"DEBUG: Content before replacement: \n{content}")
        
        # Check if the original import statement exists in the content
        import_statement = f'import "{full_import_path}"'
        if import_statement in content:
            print(f"DEBUG: Found import statement: {import_statement}")
        else:
            print(f"DEBUG: Import statement not found: {import_statement}")
            # Print all occurrences of 'import' in the content
            import_lines = [line for line in content.split('\n') if 'import' in line]
            print(f"DEBUG: All import lines: {import_lines}")
        
        # Use regex to find and replace the import statement
        import_regex = r'import\s+"' + re.escape(full_import_path) + r'"'
        new_import = f'import "./{random_imported_filename}"'
        content = re.sub(import_regex, new_import, content)
        
        # Print the content after replacement
        print(f"DEBUG: Content after replacement: \n{content}")
        
        # Check if the replacement was successful
        if new_import in content:
            print(f"DEBUG: Replacement successful, found: {new_import}")
        else:
            print(f"DEBUG: Replacement failed, not found: {new_import}")

        # Merge the imported file's name mapping into the combined mapping
        combined_name_mapping.update(imported_name_mapping)
        print(f"DEBUG: Merged name mapping. Combined mapping size: {len(combined_name_mapping)}")

    # Generate a random name for the main file
    original_filename = os.path.basename(file_path)
    random_filename = f"random_{generate_random_name()}_{original_filename}"
    print(f"DEBUG: Randomized main filename: {random_filename}")

    # Replace all names in the main file using the combined mapping
    randomized_content = replace_names(content, combined_name_mapping)
    print(f"DEBUG: Randomized content: \n{randomized_content}")

    # Write the randomized content to the new file in the main temporary directory
    random_file_path = os.path.join(temp_dir, random_filename)
    with open(random_file_path, 'w') as f:
        f.write(randomized_content)
    print(f"DEBUG: Wrote randomized content to: {random_file_path}")
    
    # List files in temp_dir after writing
    print(f"DEBUG: Files in {temp_dir} after writing: {os.listdir(temp_dir)}")

    return temp_dir, random_file_path, combined_name_mapping

def cleanup_temp_dir(temp_dir):
    """Clean up the temporary directory."""
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)