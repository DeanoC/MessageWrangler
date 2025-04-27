"""
TypeScript Generator

This module provides functionality for generating TypeScript code from the
intermediate representation defined in message_model.py.
"""

import os
from typing import List, Set, TextIO

from message_model import (
    FieldType,
    Field,
    Message,
    MessageModel
)


class TypeScriptGenerator:
    """
    Generator for TypeScript code from the intermediate representation.
    """
    
    def __init__(self, model: MessageModel, output_dir: str):
        """
        Initialize the generator with the message model and output directory.
        
        Args:
            model: The message model to generate code from
            output_dir: Directory where output files will be generated
        """
        self.model = model
        self.output_dir = output_dir
    
    def generate(self) -> bool:
        """
        Generate TypeScript code from the message model.
        
        Returns:
            bool: True if generation was successful, False otherwise
        """
        try:
            print(f"Generating TypeScript output in: {self.output_dir}")
            
            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Generate TypeScript file
            ts_file = os.path.join(self.output_dir, "messages.ts")
            with open(ts_file, 'w') as f:
                self._write_header(f)
                self._write_namespace_start(f)
                self._write_enums(f)
                self._write_interfaces(f)
                self._write_namespace_end(f)
            
            print(f"Generated TypeScript file: {ts_file}")
            return True
        
        except Exception as e:
            print(f"Error generating TypeScript output: {str(e)}")
            return False
    
    def _write_header(self, f: TextIO) -> None:
        """
        Write the header section of the TypeScript file.
        
        Args:
            f: The file to write to
        """
        f.write("// Auto-generated message definitions for TypeScript\n\n")
    
    def _write_namespace_start(self, f: TextIO) -> None:
        """
        Write the start of the namespace.
        
        Args:
            f: The file to write to
        """
        f.write("export namespace Messages {\n\n")
    
    def _write_namespace_end(self, f: TextIO) -> None:
        """
        Write the end of the namespace.
        
        Args:
            f: The file to write to
        """
        f.write("} // namespace Messages\n")
    
    def _write_enums(self, f: TextIO) -> None:
        """
        Write enum definitions.
        
        Args:
            f: The file to write to
        """
        enums_generated = set()
        
        for message_name, message in self.model.messages.items():
            for field in message.fields:
                if field.field_type == FieldType.ENUM:
                    enum_name = f"{message_name}_{field.name}_Enum"
                    if enum_name not in enums_generated:
                        f.write(f"    // Enum for {message_name}.{field.name}\n")
                        f.write(f"    export enum {enum_name} {{\n")
                        for enum_value in field.enum_values:
                            f.write(f"        {enum_value.name} = {enum_value.value},\n")
                        f.write("    }\n\n")
                        enums_generated.add(enum_name)
    
    def _write_interfaces(self, f: TextIO) -> None:
        """
        Write interface definitions.
        
        Args:
            f: The file to write to
        """
        for message_name, message in self.model.messages.items():
            f.write(f"    // {message.description}\n")
            
            # Handle inheritance
            if message.parent:
                f.write(f"    export interface {message_name} extends {message.parent} {{\n")
            else:
                f.write(f"    export interface {message_name} {{\n")
            
            # Generate fields
            for field in message.fields:
                self._write_field(f, message_name, field)
            
            f.write("    }\n\n")
    
    def _write_field(self, f: TextIO, message_name: str, field: Field) -> None:
        """
        Write a field definition.
        
        Args:
            f: The file to write to
            message_name: The name of the message containing the field
            field: The field to write
        """
        if field.field_type == FieldType.ENUM:
            enum_name = f"{message_name}_{field.name}_Enum"
            f.write(f"        {field.name}: {enum_name};\n")
        
        elif field.field_type == FieldType.COMPOUND:
            # For compound fields like position with x, y, z
            if field.compound_base_type == "float":
                f.write(f"        {field.name}: {{\n")
                for component in field.compound_components:
                    f.write(f"            {component}: number;\n")
                f.write("        };\n")
            else:
                # Handle other compound types if needed
                f.write(f"        // Unsupported compound type: {field.compound_base_type}\n")
        
        elif field.field_type == FieldType.STRING:
            f.write(f"        {field.name}: string;\n")
        
        elif field.field_type == FieldType.INT or field.field_type == FieldType.FLOAT:
            f.write(f"        {field.name}: number;\n")
        
        else:
            f.write(f"        // Unsupported type: {field.field_type}\n")