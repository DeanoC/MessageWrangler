import os
import sys
import unittest
import tempfile
import shutil

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from message_parser_core import MessageParser
from message_model import FieldType
from tests.test_utils import randomize_def_file, cleanup_temp_dir


class TestStandaloneEnum(unittest.TestCase):
    def setUp(self):
        # Get the path to the original file
        self.original_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_standalone_enum.def")

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
        self.parser_errors = parser.errors

        # Change back to the original directory
        os.chdir(self.original_dir)

        # Ensure the model was created successfully
        if self.model is None:
            print("\nParser errors:")
            for err in self.parser_errors:
                print(err)
        self.assertIsNotNone(self.model, f"Failed to parse the randomized test file. Errors: {self.parser_errors}")

    def tearDown(self):
        # Clean up the temporary directory
        cleanup_temp_dir(self.temp_dir)

    def test_standalone_enum(self):
        # Get the randomized enum and value names
        test_enum = self.name_mapping.get("TestEnum", "TestEnum")
        zero = self.name_mapping.get("Zero", "Zero")
        one = self.name_mapping.get("One", "One")
        two = self.name_mapping.get("Two", "Two")

        # Test that the standalone enum was parsed correctly
        enum = self.model.get_enum(test_enum)
        self.assertIsNotNone(enum, f"{test_enum} not found")
        self.assertEqual(enum.name, test_enum)
        self.assertFalse(enum.is_open, f"{test_enum} should not be an open enum")
        self.assertEqual(len(enum.values), 3, f"{test_enum} should have 3 values")
        self.assertEqual(enum.values[0].name, zero)
        self.assertEqual(enum.values[0].value, 0)
        self.assertEqual(enum.values[1].name, one)
        self.assertEqual(enum.values[1].value, 1)
        self.assertEqual(enum.values[2].name, two)
        self.assertEqual(enum.values[2].value, 2)

    def test_open_enum(self):
        # Get the randomized enum and value names
        test_open_enum = self.name_mapping.get("TestOpenEnum", "TestOpenEnum")
        zero = self.name_mapping.get("Zero", "Zero")
        one = self.name_mapping.get("One", "One")
        two = self.name_mapping.get("Two", "Two")

        # Test that the open enum was parsed correctly
        enum = self.model.get_enum(test_open_enum)
        self.assertIsNotNone(enum, f"{test_open_enum} not found")
        self.assertEqual(enum.name, test_open_enum)
        self.assertTrue(enum.is_open, f"{test_open_enum} should be an open enum")
        self.assertEqual(len(enum.values), 3, f"{test_open_enum} should have 3 values")
        self.assertEqual(enum.values[0].name, zero)
        self.assertEqual(enum.values[0].value, 0)
        self.assertEqual(enum.values[1].name, one)
        self.assertEqual(enum.values[1].value, 1)
        self.assertEqual(enum.values[2].name, two)
        self.assertEqual(enum.values[2].value, 2)

    def test_enum_with_inheritance(self):
        # Get the randomized enum and value names
        test_enum_with_inheritance = self.name_mapping.get("TestEnumWithInheritance", "TestEnumWithInheritance")
        test_enum = self.name_mapping.get("TestEnum", "TestEnum")
        three = self.name_mapping.get("Three", "Three")
        four = self.name_mapping.get("Four", "Four")

        # Test that the enum with inheritance was parsed correctly
        enum = self.model.get_enum(test_enum_with_inheritance)
        self.assertIsNotNone(enum, f"{test_enum_with_inheritance} not found")
        self.assertEqual(enum.name, test_enum_with_inheritance)
        self.assertEqual(enum.parent, test_enum)
        self.assertEqual(len(enum.values), 2, f"{test_enum_with_inheritance} should have 2 values")
        self.assertEqual(enum.values[0].name, three)
        self.assertEqual(enum.values[0].value, 3)
        self.assertEqual(enum.values[1].name, four)
        self.assertEqual(enum.values[1].value, 4)

    def test_namespaced_enum(self):
        # Get the randomized enum and value names
        test_namespace = self.name_mapping.get("TestNamespace", "TestNamespace")
        namespaced_enum = self.name_mapping.get("NamespacedEnum", "NamespacedEnum")
        zero = self.name_mapping.get("Zero", "Zero")
        one = self.name_mapping.get("One", "One")
        two = self.name_mapping.get("Two", "Two")

        # Test that the namespaced enum was parsed correctly
        enum = self.model.get_enum(f"{test_namespace}::{namespaced_enum}")
        self.assertIsNotNone(enum, f"{test_namespace}::{namespaced_enum} not found")
        self.assertEqual(enum.name, namespaced_enum)
        self.assertEqual(enum.namespace, test_namespace)
        self.assertEqual(len(enum.values), 3, f"{namespaced_enum} should have 3 values")
        self.assertEqual(enum.values[0].name, zero)
        self.assertEqual(enum.values[0].value, 0)
        self.assertEqual(enum.values[1].name, one)
        self.assertEqual(enum.values[1].value, 1)
        self.assertEqual(enum.values[2].name, two)
        self.assertEqual(enum.values[2].value, 2)

    def test_message_enum_field(self):
        # Get the randomized message, field, and value names
        test_message = self.name_mapping.get("TestMessage", "TestMessage")
        enum_field = self.name_mapping.get("enumField", "enumField")
        zero = self.name_mapping.get("Zero", "Zero")
        one = self.name_mapping.get("One", "One")
        two = self.name_mapping.get("Two", "Two")

        # Test that the message with an enum field was parsed correctly
        message = self.model.get_message(test_message)
        self.assertIsNotNone(message, f"{test_message} not found")
        self.assertEqual(len(message.fields), 1, f"{test_message} should have 1 field")
        field = message.fields[0]
        self.assertEqual(field.name, enum_field)
        self.assertEqual(field.field_type, FieldType.ENUM)
        self.assertEqual(len(field.enum_values), 3, f"{enum_field} should have 3 values")
        self.assertEqual(field.enum_values[0].name, zero)
        self.assertEqual(field.enum_values[0].value, 0)
        self.assertEqual(field.enum_values[1].name, one)
        self.assertEqual(field.enum_values[1].value, 1)
        self.assertEqual(field.enum_values[2].name, two)
        self.assertEqual(field.enum_values[2].value, 2)


if __name__ == "__main__":
    unittest.main()
