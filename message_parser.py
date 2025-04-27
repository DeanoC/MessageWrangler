"""
Message Parser

This module provides functionality for parsing message definition files
and converting them to the intermediate representation defined in message_model.py.
"""

import os
from typing import List, Optional, Tuple

from message_model import (
    FieldType,
    EnumValue,
    Field,
    Message,
    MessageModel
)


class MessageParser:
    """
    Parser for message definition files.
    Converts the input file format to the intermediate representation.
    """
    
    def __init__(self, input_file: str):
        """
        Initialize the parser with the input file path.
        
        Args:
            input_file: Path to the input file containing message definitions
        """
        self.input_file = input_file
        self.model = MessageModel()
    
    def parse(self) -> Optional[MessageModel]:
        """
        Parse the input file and return the resulting message model.
        
        Returns:
            The parsed message model, or None if parsing failed
        """
        try:
            print(f"Parsing input file: {self.input_file}")
            
            # Check if the file exists
            if not os.path.exists(self.input_file):
                print(f"Error: Input file '{self.input_file}' does not exist.")
                return None
            
            # Read the file content
            with open(self.input_file, 'r') as f:
                content = f.read()
            
            # Parse the content
            current_message = None
            
            # Split content into lines and process each line
            lines = content.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Skip empty lines
                if not line:
                    i += 1
                    continue
                
                # Parse message definition
                if line.startswith('message '):
                    # Extract message name and parent if exists
                    message_def = line[len('message '):].strip()
                    if '{' in message_def:
                        message_def = message_def[:message_def.find('{')].strip()
                    
                    # Check for inheritance
                    parent_message = None
                    if ':' in message_def:
                        parts = message_def.split(':')
                        message_name = parts[0].strip()
                        parent_message = parts[1].strip()
                    else:
                        message_name = message_def
                    
                    # Create new message
                    current_message = Message(
                        name=message_name,
                        parent=parent_message,
                        description=f"{message_name} message"
                    )
                    self.model.add_message(current_message)
                
                # Parse field definition
                elif line.startswith('field ') and current_message is not None:
                    # Extract field name and type
                    field_def = line[len('field '):].strip()
                    if ':' in field_def:
                        name, type_def = field_def.split(':', 1)
                        name = name.strip()
                        type_def = type_def.strip()
                        
                        # Remove trailing semicolon if present
                        if type_def.endswith(';'):
                            type_def = type_def[:-1].strip()
                        
                        # Handle enum type
                        if type_def.startswith('enum'):
                            field = self._parse_enum_field(name, type_def)
                            if field:
                                current_message.fields.append(field)
                        
                        # Handle compound type (like float { x, y, z })
                        elif '{' in type_def and '}' in type_def:
                            field = self._parse_compound_field(name, type_def)
                            if field:
                                current_message.fields.append(field)
                        
                        # Handle simple type
                        else:
                            field_type = self._get_field_type(type_def)
                            if field_type:
                                field = Field(
                                    name=name,
                                    field_type=field_type,
                                    description=f"{name} field"
                                )
                                current_message.fields.append(field)
                
                # Check for closing brace of message definition
                elif line == '}':
                    current_message = None
                
                i += 1
            
            print(f"Successfully parsed {len(self.model.messages)} message definitions.")
            return self.model
        
        except Exception as e:
            print(f"Error parsing input file: {str(e)}")
            return None
    
    def _parse_enum_field(self, name: str, type_def: str) -> Optional[Field]:
        """
        Parse an enum field definition.
        
        Args:
            name: The name of the field
            type_def: The type definition string (e.g., "enum { Value1, Value2 }")
            
        Returns:
            The parsed field, or None if parsing failed
        """
        try:
            field = Field(
                name=name,
                field_type=FieldType.ENUM,
                description=f"{name} enum field"
            )
            
            # Extract enum values
            if '{' in type_def and '}' in type_def:
                enum_str = type_def[type_def.find('{')+1:type_def.find('}')].strip()
                enum_values = [v.strip() for v in enum_str.split(',')]
                
                # Create EnumValue objects
                for i, value_name in enumerate(enum_values):
                    if value_name:  # Skip empty values
                        enum_value = EnumValue(name=value_name, value=i)
                        field.enum_values.append(enum_value)
            
            return field
        
        except Exception as e:
            print(f"Error parsing enum field '{name}': {str(e)}")
            return None
    
    def _parse_compound_field(self, name: str, type_def: str) -> Optional[Field]:
        """
        Parse a compound field definition.
        
        Args:
            name: The name of the field
            type_def: The type definition string (e.g., "float { x, y, z }")
            
        Returns:
            The parsed field, or None if parsing failed
        """
        try:
            field = Field(
                name=name,
                field_type=FieldType.COMPOUND,
                description=f"{name} compound field"
            )
            
            # Extract base type and components
            base_type = type_def[:type_def.find('{')].strip()
            components_str = type_def[type_def.find('{')+1:type_def.find('}')].strip()
            components = [c.strip() for c in components_str.split(',')]
            
            field.compound_base_type = base_type
            field.compound_components = [c for c in components if c]  # Skip empty components
            
            return field
        
        except Exception as e:
            print(f"Error parsing compound field '{name}': {str(e)}")
            return None
    
    def _get_field_type(self, type_name: str) -> Optional[FieldType]:
        """
        Convert a type name string to a FieldType enum value.
        
        Args:
            type_name: The type name string (e.g., "string", "int", "float")
            
        Returns:
            The corresponding FieldType enum value, or None if not recognized
        """
        type_map = {
            "string": FieldType.STRING,
            "int": FieldType.INT,
            "float": FieldType.FLOAT
        }
        
        return type_map.get(type_name.lower())