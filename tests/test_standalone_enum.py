import os
import sys
import unittest

# Add the parent directory to the path so we can import the message_parser module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from message_parser import MessageParser
from message_model import FieldType


class TestStandaloneEnum(unittest.TestCase):
    def setUp(self):
        # Get the path to the test file
        self.test_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_standalone_enum.def")

        # Parse the test file
        parser = MessageParser(self.test_file)
        self.model = parser.parse()

        # Ensure the model was created successfully
        self.assertIsNotNone(self.model, "Failed to parse the test file")

    def test_standalone_enum(self):
        # Test that the standalone enum was parsed correctly
        enum = self.model.get_enum("TestEnum")
        self.assertIsNotNone(enum, "TestEnum not found")
        self.assertEqual(enum.name, "TestEnum")
        self.assertFalse(enum.is_open, "TestEnum should not be an open enum")
        self.assertEqual(len(enum.values), 3, "TestEnum should have 3 values")
        self.assertEqual(enum.values[0].name, "Zero")
        self.assertEqual(enum.values[0].value, 0)
        self.assertEqual(enum.values[1].name, "One")
        self.assertEqual(enum.values[1].value, 1)
        self.assertEqual(enum.values[2].name, "Two")
        self.assertEqual(enum.values[2].value, 2)

    def test_open_enum(self):
        # Test that the open enum was parsed correctly
        enum = self.model.get_enum("TestOpenEnum")
        self.assertIsNotNone(enum, "TestOpenEnum not found")
        self.assertEqual(enum.name, "TestOpenEnum")
        self.assertTrue(enum.is_open, "TestOpenEnum should be an open enum")
        self.assertEqual(len(enum.values), 3, "TestOpenEnum should have 3 values")
        self.assertEqual(enum.values[0].name, "Zero")
        self.assertEqual(enum.values[0].value, 0)
        self.assertEqual(enum.values[1].name, "One")
        self.assertEqual(enum.values[1].value, 1)
        self.assertEqual(enum.values[2].name, "Two")
        self.assertEqual(enum.values[2].value, 2)

    def test_enum_with_inheritance(self):
        # Test that the enum with inheritance was parsed correctly
        enum = self.model.get_enum("TestEnumWithInheritance")
        self.assertIsNotNone(enum, "TestEnumWithInheritance not found")
        self.assertEqual(enum.name, "TestEnumWithInheritance")
        self.assertEqual(enum.parent, "TestEnum")
        self.assertEqual(len(enum.values), 2, "TestEnumWithInheritance should have 2 values")
        self.assertEqual(enum.values[0].name, "Three")
        self.assertEqual(enum.values[0].value, 3)
        self.assertEqual(enum.values[1].name, "Four")
        self.assertEqual(enum.values[1].value, 4)

    def test_namespaced_enum(self):
        # Test that the namespaced enum was parsed correctly
        enum = self.model.get_enum("TestNamespace::NamespacedEnum")
        self.assertIsNotNone(enum, "TestNamespace::NamespacedEnum not found")
        self.assertEqual(enum.name, "NamespacedEnum")
        self.assertEqual(enum.namespace, "TestNamespace")
        self.assertEqual(len(enum.values), 3, "NamespacedEnum should have 3 values")
        self.assertEqual(enum.values[0].name, "Zero")
        self.assertEqual(enum.values[0].value, 0)
        self.assertEqual(enum.values[1].name, "One")
        self.assertEqual(enum.values[1].value, 1)
        self.assertEqual(enum.values[2].name, "Two")
        self.assertEqual(enum.values[2].value, 2)

    def test_message_enum_field(self):
        # Test that the message with an enum field was parsed correctly
        message = self.model.get_message("TestMessage")
        self.assertIsNotNone(message, "TestMessage not found")
        self.assertEqual(len(message.fields), 1, "TestMessage should have 1 field")
        field = message.fields[0]
        self.assertEqual(field.name, "enumField")
        self.assertEqual(field.field_type, FieldType.ENUM)
        self.assertEqual(len(field.enum_values), 3, "enumField should have 3 values")
        self.assertEqual(field.enum_values[0].name, "Zero")
        self.assertEqual(field.enum_values[0].value, 0)
        self.assertEqual(field.enum_values[1].name, "One")
        self.assertEqual(field.enum_values[1].value, 1)
        self.assertEqual(field.enum_values[2].name, "Two")
        self.assertEqual(field.enum_values[2].value, 2)


if __name__ == "__main__":
    unittest.main()
