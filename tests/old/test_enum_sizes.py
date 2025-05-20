import os
import sys
import unittest
import tempfile
import shutil
import re

# Add the parent directory to the path so we can import the message_parser module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from message_parser_core import MessageParser
from cpp_generator import StandardCppGenerator, UnrealCppGenerator
from message_model import Enum
from tests.test_utils import randomize_def_file, cleanup_temp_dir


class TestEnumSizes(unittest.TestCase):
    def setUp(self):
        # Get the path to the original file
        self.original_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_enum_sizes.def")

        # Create a randomized version of the file
        self.temp_dir, self.random_file_path, self.name_mapping = randomize_def_file(self.original_file)

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

        # Change back to the original directory
        os.chdir(self.original_dir)

        # Ensure the model was created successfully
        self.assertIsNotNone(self.model, "Failed to parse the randomized test file")

        # Create a temporary directory for the generated files
        self.output_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Remove the temporary directories
        cleanup_temp_dir(self.temp_dir)
        shutil.rmtree(self.output_dir)

    def test_standard_cpp_generator(self):
        # Get the randomized enum and message names
        enum8bit = self.name_mapping.get("Enum8Bit", "Enum8Bit")
        enum16bit = self.name_mapping.get("Enum16Bit", "Enum16Bit")
        enum32bit = self.name_mapping.get("Enum32Bit", "Enum32Bit")
        enum64bit = self.name_mapping.get("Enum64Bit", "Enum64Bit")
        open_enum8bit = self.name_mapping.get("OpenEnum8Bit", "OpenEnum8Bit")
        open_enum64bit = self.name_mapping.get("OpenEnum64Bit", "OpenEnum64Bit")
        test_enum_sizes = self.name_mapping.get("TestEnumSizes", "TestEnumSizes")
        enum8bit_field = self.name_mapping.get("enum8Bit", "enum8Bit")
        enum16bit_field = self.name_mapping.get("enum16Bit", "enum16Bit")
        enum32bit_field = self.name_mapping.get("enum32Bit", "enum32Bit")
        enum64bit_field = self.name_mapping.get("enum64Bit", "enum64Bit")

        # Create a unique output name based on the random file name
        output_name = "test_" + self.random_file_name.replace(".def", "")

        # Create the C++ generator
        generator = StandardCppGenerator(self.model, self.output_dir, output_name)

        # Generate the C++ code
        result = generator.generate()

        # Check that the generation was successful
        self.assertTrue(result, "C++ generation failed")

        # Check the output file
        output_file = os.path.join(self.output_dir, f"c_{output_name}_msgs.h")
        self.assertTrue(os.path.exists(output_file), "C++ output file not created")

        # Read the generated code
        with open(output_file, "r") as f:
            code = f.read()

        # Check that the enums have the correct sizes
        self.assertRegex(code, rf"enum class {enum8bit} : uint8_t")
        self.assertRegex(code, rf"enum class {enum16bit} : uint16_t")
        self.assertRegex(code, rf"enum class {enum32bit} : uint32_t")
        self.assertRegex(code, rf"enum class {enum64bit} : uint64_t")

        # Open enums should default to 32-bit unless they have values > 32 bits
        self.assertRegex(code, rf"enum {open_enum8bit} : uint32_t")
        self.assertRegex(code, rf"enum {open_enum64bit} : uint64_t")

        # Check inline enum fields
        self.assertRegex(code, rf"enum class {test_enum_sizes}_{enum8bit_field}_Enum : uint8_t")
        self.assertRegex(code, rf"enum class {test_enum_sizes}_{enum16bit_field}_Enum : uint16_t")
        self.assertRegex(code, rf"enum class {test_enum_sizes}_{enum32bit_field}_Enum : uint32_t")
        self.assertRegex(code, rf"enum class {test_enum_sizes}_{enum64bit_field}_Enum : uint64_t")

    def test_unreal_cpp_generator(self):
        # Get the randomized enum and message names
        enum8bit = self.name_mapping.get("Enum8Bit", "Enum8Bit")
        enum16bit = self.name_mapping.get("Enum16Bit", "Enum16Bit")
        enum32bit = self.name_mapping.get("Enum32Bit", "Enum32Bit")
        enum64bit = self.name_mapping.get("Enum64Bit", "Enum64Bit")
        open_enum8bit = self.name_mapping.get("OpenEnum8Bit", "OpenEnum8Bit")
        open_enum64bit = self.name_mapping.get("OpenEnum64Bit", "OpenEnum64Bit")
        test_enum_sizes = self.name_mapping.get("TestEnumSizes", "TestEnumSizes")
        enum8bit_field = self.name_mapping.get("enum8Bit", "enum8Bit")
        enum16bit_field = self.name_mapping.get("enum16Bit", "enum16Bit")
        enum32bit_field = self.name_mapping.get("enum32Bit", "enum32Bit")
        enum64bit_field = self.name_mapping.get("enum64Bit", "enum64Bit")

        # Create a unique output name based on the random file name
        output_name = "test_" + self.random_file_name.replace(".def", "")

        # Create the Unreal C++ generator
        generator = UnrealCppGenerator(self.model, self.output_dir, output_name)

        # Generate the C++ code
        result = generator.generate()

        # Check that the generation was successful
        self.assertTrue(result, "Unreal C++ generation failed")

        # Check the output file
        output_file = os.path.join(self.output_dir, f"ue_{output_name}_msgs.h")
        self.assertTrue(os.path.exists(output_file), "Unreal C++ output file not created")

        # Read the generated code
        with open(output_file, "r") as f:
            code = f.read()

        # Check that the enums have the correct sizes
        self.assertRegex(code, rf"enum class {enum8bit} : uint8")
        self.assertRegex(code, rf"enum class {enum16bit} : uint16")
        self.assertRegex(code, rf"enum class {enum32bit} : uint32")
        self.assertRegex(code, rf"enum class {enum64bit} : uint64")

        # Open enums should default to 32-bit unless they have values > 32 bits
        self.assertRegex(code, rf"enum {open_enum8bit} : uint32")
        self.assertRegex(code, rf"enum {open_enum64bit} : uint64")

        # Check inline enum fields
        self.assertRegex(code, rf"enum class {test_enum_sizes}_{enum8bit_field}_Enum : uint8")
        self.assertRegex(code, rf"enum class {test_enum_sizes}_{enum16bit_field}_Enum : uint16")
        self.assertRegex(code, rf"enum class {test_enum_sizes}_{enum32bit_field}_Enum : uint32")
        self.assertRegex(code, rf"enum class {test_enum_sizes}_{enum64bit_field}_Enum : uint64")


if __name__ == "__main__":
    unittest.main()
