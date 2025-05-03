import os
import sys
import unittest
import tempfile
import shutil

# Add the parent directory to the path so we can import the message_parser module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from message_parser import MessageParser
from cpp_generator import StandardCppGenerator
from python_generator import PythonGenerator
from typescript_generator import TypeScriptGenerator


class TestStandaloneEnumGenerators(unittest.TestCase):
    def setUp(self):
        # Get the path to the test file
        self.test_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_standalone_enum.def")

        # Parse the test file
        parser = MessageParser(self.test_file)
        self.model = parser.parse()

        # Ensure the model was created successfully
        self.assertIsNotNone(self.model, "Failed to parse the test file")

        # Debug: Print the model's enums
        print("Model enums:")
        for enum_name, enum in self.model.enums.items():
            print(f"  {enum_name}: {enum.name}, is_open={enum.is_open}, values={[v.name for v in enum.values]}")

        # Create a temporary directory for the generated files
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)

    def test_cpp_generator(self):
        # Create the C++ generator with a unique output name
        generator = StandardCppGenerator(self.model, self.temp_dir, "test_standalone_enum_cpp")

        # Generate the C++ code
        result = generator.generate()

        # Check the output file
        output_file = os.path.join(self.temp_dir, f"c_test_standalone_enum_msgs.h")

        # Check that the generation was successful
        self.assertTrue(result, "C++ generation failed")

        # Check that the output file exists
        self.assertTrue(os.path.exists(output_file), "C++ output file not created")

        # Read the generated code
        with open(output_file, "r") as f:
            code = f.read()

        # Check that the standalone enums are in the code
        self.assertIn("enum class TestEnum", code)
        self.assertIn("enum TestOpenEnum", code)
        self.assertIn("enum class TestEnumWithInheritance", code)
        self.assertIn("namespace TestNamespace", code)
        self.assertIn("enum class NamespacedEnum", code)

        # Check that the enum values are in the code
        self.assertIn("Zero = 0", code)
        self.assertIn("One = 1", code)
        self.assertIn("Two = 2", code)
        self.assertIn("Three = 3", code)
        self.assertIn("Four = 4", code)

    def test_python_generator(self):
        # Create the Python generator with a unique output name
        generator = PythonGenerator(self.model, self.temp_dir, "test_standalone_enum_py")

        # Generate the Python code
        result = generator.generate()

        # Check the output file
        output_file = os.path.join(self.temp_dir, f"test_standalone_enum_msgs.py")

        # Check that the generation was successful
        self.assertTrue(result, "Python generation failed")

        # Check that the output file exists
        self.assertTrue(os.path.exists(output_file), "Python output file not created")

        # Read the generated code
        with open(output_file, "r") as f:
            code = f.read()

        # Check that the standalone enums are in the code
        self.assertIn("class Testenum(Enum)", code)
        self.assertIn("class Testopenenum(IntEnum)", code)
        self.assertIn("class Testenumwithinheritance(Enum)", code)
        self.assertIn("class TestnamespaceNamespacedenum(Enum)", code)

        # Check that the enum values are in the code
        self.assertIn("Zero = 0", code)
        self.assertIn("One = 1", code)
        self.assertIn("Two = 2", code)
        self.assertIn("Three = 3", code)
        self.assertIn("Four = 4", code)

    def test_typescript_generator(self):
        # Create the TypeScript generator with a unique output name
        generator = TypeScriptGenerator(self.model, self.temp_dir, "test_standalone_enum_ts")

        # Generate the TypeScript code
        result = generator.generate()

        # Check the output file
        output_file = os.path.join(self.temp_dir, f"test_standalone_enum_msgs.ts")

        # Check that the generation was successful
        self.assertTrue(result, "TypeScript generation failed")

        # Check that the output file exists
        self.assertTrue(os.path.exists(output_file), "TypeScript output file not created")

        # Read the generated code
        with open(output_file, "r") as f:
            code = f.read()

        # Check that the standalone enums are in the code
        self.assertIn("export enum TestEnum", code)
        self.assertIn("export enum TestOpenEnum", code)
        self.assertIn("export enum TestEnumWithInheritance", code)
        self.assertIn("export enum TestNamespace_NamespacedEnum", code)

        # Check that the enum values are in the code
        self.assertIn("Zero = 0", code)
        self.assertIn("One = 1", code)
        self.assertIn("Two = 2", code)
        self.assertIn("Three = 3", code)
        self.assertIn("Four = 4", code)


if __name__ == "__main__":
    unittest.main()
