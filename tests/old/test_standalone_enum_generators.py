import os
import sys
import unittest
import tempfile
import shutil

# Add the parent directory to the path so we can import the message_parser module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from message_parser_core import MessageParser
from cpp_generator import StandardCppGenerator
from python_generator import PythonGenerator
from typescript_generator import TypeScriptGenerator
from tests.test_utils import randomize_def_file, cleanup_temp_dir


class TestStandaloneEnumGenerators(unittest.TestCase):
    def setUp(self):
        # Get the path to the test file
        self.original_test_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_standalone_enum.def")

        # Create a randomized version of the file
        self.temp_dir, self.random_file_path, self.name_mapping = randomize_def_file(self.original_test_file)

        # Get the directory and filename of the random file
        self.random_file_dir = os.path.dirname(self.random_file_path)
        self.random_file_name = os.path.basename(self.random_file_path)

        # Store the original directory
        self.original_dir = os.getcwd()

        # Change to the directory containing the random file
        os.chdir(self.random_file_dir)

        # Parse the randomized file
        parser = MessageParser(self.random_file_name)
        self.model = parser.parse()

        # Ensure the model was created successfully
        self.assertIsNotNone(self.model, "Failed to parse the randomized test file")

        # Debug: Print the model's enums
        print("Model enums:")
        for enum_name, enum in self.model.enums.items():
            print(f"  {enum_name}: {enum.name}, is_open={enum.is_open}, values={[v.name for v in enum.values]}")

    def tearDown(self):
        # Change back to the original directory
        os.chdir(self.original_dir)

        # Clean up the temporary directory
        cleanup_temp_dir(self.temp_dir)

    def test_cpp_generator(self):
        # Create the C++ generator with a unique output name
        random_output_name = "test_" + self.random_file_name.replace(".def", "")
        generator = StandardCppGenerator(self.model, self.temp_dir, random_output_name)

        # Generate the C++ code
        result = generator.generate()

        # Check the output file
        output_file = os.path.join(self.temp_dir, f"c_{random_output_name}_msgs.h")

        # Check that the generation was successful
        self.assertTrue(result, "C++ generation failed")

        # Check that the output file exists
        self.assertTrue(os.path.exists(output_file), "C++ output file not created")

        # Read the generated code
        with open(output_file, "r") as f:
            code = f.read()

        # Get the randomized names from the name mapping
        test_enum = self.name_mapping.get("TestEnum", "TestEnum")
        test_open_enum = self.name_mapping.get("TestOpenEnum", "TestOpenEnum")
        test_enum_with_inheritance = self.name_mapping.get("TestEnumWithInheritance", "TestEnumWithInheritance")
        test_namespace = self.name_mapping.get("TestNamespace", "TestNamespace")
        namespaced_enum = self.name_mapping.get("NamespacedEnum", "NamespacedEnum")

        # Check that the standalone enums are in the code
        self.assertIn(f"enum class {test_enum}", code)
        self.assertIn(f"enum {test_open_enum}", code)
        self.assertIn(f"enum class {test_enum_with_inheritance}", code)
        self.assertIn(f"namespace {test_namespace}", code)
        self.assertIn(f"enum class {namespaced_enum}", code)

        # Get the randomized enum values from the name mapping
        zero = self.name_mapping.get("Zero", "Zero")
        one = self.name_mapping.get("One", "One")
        two = self.name_mapping.get("Two", "Two")
        three = self.name_mapping.get("Three", "Three")
        four = self.name_mapping.get("Four", "Four")

        # Check that the enum values are in the code
        self.assertIn(f"{zero} = 0", code)
        self.assertIn(f"{one} = 1", code)
        self.assertIn(f"{two} = 2", code)
        self.assertIn(f"{three} = 3", code)
        self.assertIn(f"{four} = 4", code)

    def test_python_generator(self):
        # Create the Python generator with a unique output name
        random_output_name = "test_" + self.random_file_name.replace(".def", "")
        generator = PythonGenerator(self.model, self.temp_dir, random_output_name)

        # Generate the Python code
        result = generator.generate()

        # Check the output file
        output_file = os.path.join(self.temp_dir, f"{random_output_name}_msgs.py")

        # Check that the generation was successful
        self.assertTrue(result, "Python generation failed")

        # Check that the output file exists
        self.assertTrue(os.path.exists(output_file), "Python output file not created")

        # Read the generated code
        with open(output_file, "r") as f:
            code = f.read()

        # Get the randomized names from the name mapping
        test_enum = self.name_mapping.get("TestEnum", "TestEnum")
        test_open_enum = self.name_mapping.get("TestOpenEnum", "TestOpenEnum")
        test_enum_with_inheritance = self.name_mapping.get("TestEnumWithInheritance", "TestEnumWithInheritance")
        test_namespace = self.name_mapping.get("TestNamespace", "TestNamespace")
        namespaced_enum = self.name_mapping.get("NamespacedEnum", "NamespacedEnum")

        # Python generator converts names to lowercase for class names
        self.assertIn(f"class {test_enum.lower()}(Enum)", code)
        self.assertIn(f"class {test_open_enum.lower()}(IntEnum)", code)
        self.assertIn(f"class {test_enum_with_inheritance.lower()}(Enum)", code)
        self.assertIn(f"class {test_namespace.lower()}{namespaced_enum}(Enum)", code)

        # Get the randomized enum values from the name mapping
        zero = self.name_mapping.get("Zero", "Zero")
        one = self.name_mapping.get("One", "One")
        two = self.name_mapping.get("Two", "Two")
        three = self.name_mapping.get("Three", "Three")
        four = self.name_mapping.get("Four", "Four")

        # Check that the enum values are in the code
        self.assertIn(f"{zero} = 0", code)
        self.assertIn(f"{one} = 1", code)
        self.assertIn(f"{two} = 2", code)
        self.assertIn(f"{three} = 3", code)
        self.assertIn(f"{four} = 4", code)

    def test_typescript_generator(self):
        # Create the TypeScript generator with a unique output name
        random_output_name = "test_" + self.random_file_name.replace(".def", "")
        generator = TypeScriptGenerator(self.model, self.temp_dir, random_output_name)

        # Generate the TypeScript code
        result = generator.generate()

        # Check the output file
        output_file = os.path.join(self.temp_dir, f"{random_output_name}_msgs.ts")

        # Check that the generation was successful
        self.assertTrue(result, "TypeScript generation failed")

        # Check that the output file exists
        self.assertTrue(os.path.exists(output_file), "TypeScript output file not created")

        # Read the generated code
        with open(output_file, "r") as f:
            code = f.read()

        # Get the randomized names from the name mapping
        test_enum = self.name_mapping.get("TestEnum", "TestEnum")
        test_open_enum = self.name_mapping.get("TestOpenEnum", "TestOpenEnum")
        test_enum_with_inheritance = self.name_mapping.get("TestEnumWithInheritance", "TestEnumWithInheritance")
        test_namespace = self.name_mapping.get("TestNamespace", "TestNamespace")
        namespaced_enum = self.name_mapping.get("NamespacedEnum", "NamespacedEnum")

        # Check that the standalone enums are in the code
        self.assertIn(f"export enum {test_enum}", code)
        self.assertIn(f"export enum {test_open_enum}", code)
        self.assertIn(f"export enum {test_enum_with_inheritance}", code)
        self.assertIn(f"export enum {test_namespace}_{namespaced_enum}", code)

        # Get the randomized enum values from the name mapping
        zero = self.name_mapping.get("Zero", "Zero")
        one = self.name_mapping.get("One", "One")
        two = self.name_mapping.get("Two", "Two")
        three = self.name_mapping.get("Three", "Three")
        four = self.name_mapping.get("Four", "Four")

        # Check that the enum values are in the code
        self.assertIn(f"{zero} = 0", code)
        self.assertIn(f"{one} = 1", code)
        self.assertIn(f"{two} = 2", code)
        self.assertIn(f"{three} = 3", code)
        self.assertIn(f"{four} = 4", code)


if __name__ == "__main__":
    unittest.main()
