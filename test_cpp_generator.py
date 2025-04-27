"""
Test C++ Generator

This module contains tests for the C++ generator.
"""

import os
import unittest
from tempfile import TemporaryDirectory

from message_model import FieldType, EnumValue, Field, Message, MessageModel
from cpp_generator import CppGenerator


class TestCppGenerator(unittest.TestCase):
    """Test cases for the CppGenerator class."""

    def setUp(self):
        """Set up a test model."""
        self.model = MessageModel()
        
        # Create a simple message
        simple_message = Message(
            name="SimpleMessage",
            description="A simple message"
        )
        
        # Add fields to the simple message
        simple_message.fields.append(
            Field(
                name="stringField",
                field_type=FieldType.STRING,
                description="A string field"
            )
        )
        
        simple_message.fields.append(
            Field(
                name="intField",
                field_type=FieldType.INT,
                description="An int field"
            )
        )
        
        simple_message.fields.append(
            Field(
                name="floatField",
                field_type=FieldType.FLOAT,
                description="A float field"
            )
        )
        
        # Create an enum field
        enum_field = Field(
            name="status",
            field_type=FieldType.ENUM,
            description="A status enum"
        )
        enum_field.enum_values = [
            EnumValue(name="OK", value=0),
            EnumValue(name="ERROR", value=1),
            EnumValue(name="PENDING", value=2)
        ]
        simple_message.fields.append(enum_field)
        
        # Create a compound field
        compound_field = Field(
            name="position",
            field_type=FieldType.COMPOUND,
            description="A position field"
        )
        compound_field.compound_base_type = "float"
        compound_field.compound_components = ["x", "y", "z"]
        simple_message.fields.append(compound_field)
        
        # Add the simple message to the model
        self.model.add_message(simple_message)
        
        # Create a base message
        base_message = Message(
            name="BaseMessage",
            description="A base message"
        )
        base_message.fields.append(
            Field(
                name="baseField",
                field_type=FieldType.STRING,
                description="A base field"
            )
        )
        self.model.add_message(base_message)
        
        # Create a derived message
        derived_message = Message(
            name="DerivedMessage",
            parent="BaseMessage",
            description="A derived message"
        )
        derived_message.fields.append(
            Field(
                name="derivedField",
                field_type=FieldType.INT,
                description="A derived field"
            )
        )
        self.model.add_message(derived_message)

    def test_generate(self):
        """Test generating C++ code."""
        with TemporaryDirectory() as temp_dir:
            generator = CppGenerator(self.model, temp_dir)
            result = generator.generate()
            self.assertTrue(result)
            
            # Check that the output file exists
            output_file = os.path.join(temp_dir, "Messages.h")
            self.assertTrue(os.path.exists(output_file))
            
            # Read the output file
            with open(output_file, 'r') as f:
                content = f.read()
            
            # Check that the content contains expected elements
            self.assertIn("namespace Messages", content)
            self.assertIn("struct SimpleMessage", content)
            self.assertIn("struct BaseMessage", content)
            self.assertIn("struct DerivedMessage : public BaseMessage", content)
            self.assertIn("FString stringField", content)
            self.assertIn("int32 intField", content)
            self.assertIn("float floatField", content)
            self.assertIn("SimpleMessage_status_Enum status", content)
            self.assertIn("enum class SimpleMessage_status_Enum", content)
            self.assertIn("OK = 0", content)
            self.assertIn("ERROR = 1", content)
            self.assertIn("PENDING = 2", content)
            self.assertIn("struct {", content)
            self.assertIn("float x", content)
            self.assertIn("float y", content)
            self.assertIn("float z", content)
            self.assertIn("} position", content)


if __name__ == '__main__':
    unittest.main()