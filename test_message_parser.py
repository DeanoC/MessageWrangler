"""
Test Message Parser

This module contains tests for the message parser.
"""

import os
import unittest
from tempfile import NamedTemporaryFile

from message_model import FieldType, Message, MessageModel
from message_parser import MessageParser


class TestMessageParser(unittest.TestCase):
    """Test cases for the MessageParser class."""

    def test_parse_empty_file(self):
        """Test parsing an empty file."""
        with NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("")
            temp_file = f.name

        try:
            parser = MessageParser(temp_file)
            model = parser.parse()
            self.assertIsNotNone(model)
            self.assertEqual(len(model.messages), 0)
        finally:
            os.unlink(temp_file)

    def test_parse_simple_message(self):
        """Test parsing a simple message with basic fields."""
        with NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("""
message SimpleMessage {
    field stringField: string
    field intField: int
    field floatField: float
}
            """)
            temp_file = f.name

        try:
            parser = MessageParser(temp_file)
            model = parser.parse()
            self.assertIsNotNone(model)
            self.assertEqual(len(model.messages), 1)
            
            # Check message
            message = model.get_message("SimpleMessage")
            self.assertIsNotNone(message)
            self.assertEqual(message.name, "SimpleMessage")
            self.assertIsNone(message.parent)
            self.assertEqual(len(message.fields), 3)
            
            # Check fields
            self.assertEqual(message.fields[0].name, "stringField")
            self.assertEqual(message.fields[0].field_type, FieldType.STRING)
            
            self.assertEqual(message.fields[1].name, "intField")
            self.assertEqual(message.fields[1].field_type, FieldType.INT)
            
            self.assertEqual(message.fields[2].name, "floatField")
            self.assertEqual(message.fields[2].field_type, FieldType.FLOAT)
        finally:
            os.unlink(temp_file)

    def test_parse_enum_field(self):
        """Test parsing a message with an enum field."""
        with NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("""
message EnumMessage {
    field status: enum { OK, ERROR, PENDING }
}
            """)
            temp_file = f.name

        try:
            parser = MessageParser(temp_file)
            model = parser.parse()
            self.assertIsNotNone(model)
            
            # Check message
            message = model.get_message("EnumMessage")
            self.assertIsNotNone(message)
            self.assertEqual(len(message.fields), 1)
            
            # Check enum field
            field = message.fields[0]
            self.assertEqual(field.name, "status")
            self.assertEqual(field.field_type, FieldType.ENUM)
            self.assertEqual(len(field.enum_values), 3)
            
            # Check enum values
            self.assertEqual(field.enum_values[0].name, "OK")
            self.assertEqual(field.enum_values[0].value, 0)
            
            self.assertEqual(field.enum_values[1].name, "ERROR")
            self.assertEqual(field.enum_values[1].value, 1)
            
            self.assertEqual(field.enum_values[2].name, "PENDING")
            self.assertEqual(field.enum_values[2].value, 2)
        finally:
            os.unlink(temp_file)

    def test_parse_compound_field(self):
        """Test parsing a message with a compound field."""
        with NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("""
message CompoundMessage {
    field position: float { x, y, z }
}
            """)
            temp_file = f.name

        try:
            parser = MessageParser(temp_file)
            model = parser.parse()
            self.assertIsNotNone(model)
            
            # Check message
            message = model.get_message("CompoundMessage")
            self.assertIsNotNone(message)
            self.assertEqual(len(message.fields), 1)
            
            # Check compound field
            field = message.fields[0]
            self.assertEqual(field.name, "position")
            self.assertEqual(field.field_type, FieldType.COMPOUND)
            self.assertEqual(field.compound_base_type, "float")
            self.assertEqual(len(field.compound_components), 3)
            self.assertEqual(field.compound_components, ["x", "y", "z"])
        finally:
            os.unlink(temp_file)

    def test_parse_inheritance(self):
        """Test parsing messages with inheritance."""
        with NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("""
message BaseMessage {
    field baseField: string
}

message DerivedMessage : BaseMessage {
    field derivedField: int
}
            """)
            temp_file = f.name

        try:
            parser = MessageParser(temp_file)
            model = parser.parse()
            self.assertIsNotNone(model)
            self.assertEqual(len(model.messages), 2)
            
            # Check base message
            base_message = model.get_message("BaseMessage")
            self.assertIsNotNone(base_message)
            self.assertIsNone(base_message.parent)
            self.assertEqual(len(base_message.fields), 1)
            self.assertEqual(base_message.fields[0].name, "baseField")
            
            # Check derived message
            derived_message = model.get_message("DerivedMessage")
            self.assertIsNotNone(derived_message)
            self.assertEqual(derived_message.parent, "BaseMessage")
            self.assertEqual(len(derived_message.fields), 1)
            self.assertEqual(derived_message.fields[0].name, "derivedField")
        finally:
            os.unlink(temp_file)


if __name__ == '__main__':
    unittest.main()