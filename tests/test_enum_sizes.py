import os
import sys
import unittest
import tempfile
import shutil
import re

# Add the parent directory to the path so we can import the message_parser module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from message_parser import MessageParser
from cpp_generator import StandardCppGenerator, UnrealCppGenerator
from message_model import Enum


class TestEnumSizes(unittest.TestCase):
    def setUp(self):
        # Get the path to the test file
        self.test_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_enum_sizes.def")

        # Parse the test file
        parser = MessageParser(self.test_file)
        self.model = parser.parse()

        # Ensure the model was created successfully
        self.assertIsNotNone(self.model, "Failed to parse the test file")

        # Create a temporary directory for the generated files
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)

    def test_standard_cpp_generator(self):
        # Create the C++ generator
        generator = StandardCppGenerator(self.model, self.temp_dir, "test_enum_sizes")

        # Generate the C++ code
        result = generator.generate()

        # Check that the generation was successful
        self.assertTrue(result, "C++ generation failed")

        # Check the output file
        output_file = os.path.join(self.temp_dir, "c_test_enum_sizes_msgs.h")
        self.assertTrue(os.path.exists(output_file), "C++ output file not created")

        # Read the generated code
        with open(output_file, "r") as f:
            code = f.read()

        # Check that the enums have the correct sizes
        self.assertRegex(code, r"enum class Enum8Bit : uint8_t")
        self.assertRegex(code, r"enum class Enum16Bit : uint16_t")
        self.assertRegex(code, r"enum class Enum32Bit : uint32_t")
        self.assertRegex(code, r"enum class Enum64Bit : uint64_t")
        
        # Open enums should default to 32-bit unless they have values > 32 bits
        self.assertRegex(code, r"enum OpenEnum8Bit : uint32_t")
        self.assertRegex(code, r"enum OpenEnum64Bit : uint64_t")
        
        # Check inline enum fields
        self.assertRegex(code, r"enum class TestEnumSizes_enum8Bit_Enum : uint8_t")
        self.assertRegex(code, r"enum class TestEnumSizes_enum16Bit_Enum : uint16_t")
        self.assertRegex(code, r"enum class TestEnumSizes_enum32Bit_Enum : uint32_t")
        self.assertRegex(code, r"enum class TestEnumSizes_enum64Bit_Enum : uint64_t")

    def test_unreal_cpp_generator(self):
        # Create the Unreal C++ generator
        generator = UnrealCppGenerator(self.model, self.temp_dir, "test_enum_sizes")

        # Generate the C++ code
        result = generator.generate()

        # Check that the generation was successful
        self.assertTrue(result, "Unreal C++ generation failed")

        # Check the output file
        output_file = os.path.join(self.temp_dir, "ue_test_enum_sizes_msgs.h")
        self.assertTrue(os.path.exists(output_file), "Unreal C++ output file not created")

        # Read the generated code
        with open(output_file, "r") as f:
            code = f.read()

        # Check that the enums have the correct sizes
        self.assertRegex(code, r"enum class Enum8Bit : uint8")
        self.assertRegex(code, r"enum class Enum16Bit : uint16")
        self.assertRegex(code, r"enum class Enum32Bit : uint32")
        self.assertRegex(code, r"enum class Enum64Bit : uint64")
        
        # Open enums should default to 32-bit unless they have values > 32 bits
        self.assertRegex(code, r"enum OpenEnum8Bit : uint32")
        self.assertRegex(code, r"enum OpenEnum64Bit : uint64")
        
        # Check inline enum fields
        self.assertRegex(code, r"enum class TestEnumSizes_enum8Bit_Enum : uint8")
        self.assertRegex(code, r"enum class TestEnumSizes_enum16Bit_Enum : uint16")
        self.assertRegex(code, r"enum class TestEnumSizes_enum32Bit_Enum : uint32")
        self.assertRegex(code, r"enum class TestEnumSizes_enum64Bit_Enum : uint64")


if __name__ == "__main__":
    unittest.main()