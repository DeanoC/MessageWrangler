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
    MessageModel,
    Namespace
)


class MessageParser:
    """
    Parser for message definition files.
    Converts the input file format to the intermediate representation.
    """

    def __init__(self, input_file: str, verbose: bool = False):
        """
        Initialize the parser with the input file path.

        Args:
            input_file: Path to the input file containing message definitions
            verbose: Whether to print debug information (default: False)
        """
        self.input_file = input_file
        self.model = MessageModel()
        self.errors = []
        self.warnings = []
        self.verbose = verbose

        # Reserved keywords that shouldn't be used as names
        self.reserved_keywords = [
            "message", "field", "enum", "namespace", "options",
            "string", "int", "float", "bool", "byte", "optional", "default",
            "import", "as"
        ]

    def debug_print(self, message: str) -> None:
        """
        Print a debug message if verbose mode is enabled.

        Args:
            message: The message to print
        """
        if self.verbose:
            print(message)

    def parse(self) -> Optional[MessageModel]:
        """
        Parse the input file and return the resulting message model.

        Returns:
            The parsed message model, or None if parsing failed
        """
        try:
            # Reset errors and warnings
            self.errors = []
            self.warnings = []

            # Check if the file exists
            if not os.path.exists(self.input_file):
                self.errors.append(f"Error: Input file '{self.input_file}' does not exist.")
                return None

            # Read the file content
            with open(self.input_file, 'r') as f:
                content = f.read()

            # Parse the content
            current_message = None
            current_namespace = None
            current_comment = ""

            # Keep track of imported files to avoid circular imports
            imported_files = set()

            # Split content into lines and process each line
            lines = content.splitlines()
            i = 0

            # Variables to track multi-line field parsing
            in_field_def = False
            field_name = ""
            field_type_def = ""
            field_start_line = 0

            while i < len(lines):
                line = lines[i].strip()

                # Skip empty lines
                if not line:
                    i += 1
                    continue

                # Parse comments
                if line.startswith('///'):
                    # Extract comment text (remove the '///' prefix)
                    comment_text = line[3:].strip()
                    if current_comment:
                        current_comment += "\n" + comment_text
                    else:
                        current_comment = comment_text
                    i += 1
                    continue

                # Skip local comments (// but not ///)
                elif line.startswith('//'):
                    # These comments are local to the .def file and not propagated to generated files
                    i += 1
                    continue

                # Parse import statements
                elif line.startswith('import '):
                    # Parse the import statement
                    import_result = self._parse_import_statement(line, i+1)
                    if import_result:
                        file_path, namespace = import_result

                        # Resolve the file path (relative to the current file)
                        if not os.path.isabs(file_path):
                            base_dir = os.path.dirname(os.path.abspath(self.input_file))
                            file_path = os.path.normpath(os.path.join(base_dir, file_path))

                        # Check if the file exists
                        if not os.path.exists(file_path):
                            self.errors.append(f"Line {i+1}: Imported file '{file_path}' does not exist.")
                        else:
                            # Check for circular imports
                            if file_path in imported_files:
                                self.errors.append(f"Line {i+1}: Circular import detected for file '{file_path}'.")
                            else:
                                # Add to imported files set
                                imported_files.add(file_path)

                                # Create a new parser for the imported file
                                import_parser = MessageParser(file_path)

                                # Parse the imported file
                                import_model = import_parser.parse()

                                # If parsing was successful, add the imported messages to the current model
                                if import_model:
                                    # If namespace is provided, create it if it doesn't exist
                                    if namespace is not None and namespace not in self.model.namespaces:
                                        self.model.add_namespace(Namespace(namespace))

                                    # Add all messages from the imported model to the current model
                                    for msg_name, message in import_model.messages.items():
                                        # Handle parent references
                                        parent = None
                                        if message.parent:
                                            if namespace is not None:
                                                # If the parent has a namespace, we need to check if it's from the same file
                                                if '::' in message.parent:
                                                    parent_namespace, parent_name = message.parent.split('::', 1)
                                                    # If the parent is from the same file, update its namespace
                                                    parent = f"{namespace}::{parent_name}"
                                                else:
                                                    # If the parent has no namespace, it's from the same file
                                                    # so we need to add the import namespace
                                                    parent = f"{namespace}::{message.parent}"
                                            else:
                                                # No namespace, keep the parent reference as is
                                                parent = message.parent

                                        # Create a copy of the message
                                        imported_message = Message(
                                            name=message.name,
                                            parent=parent,
                                            namespace=namespace,  # Use the import namespace or None if no 'as' was used
                                            description=message.description,
                                            comment=message.comment,
                                            source_file=file_path  # Set the source file to the imported file path
                                        )

                                        # Copy all fields
                                        imported_message.fields = message.fields.copy()

                                        # Add the message to the model
                                        self.model.add_message(imported_message)
                                else:
                                    # Add errors from the import parser
                                    for error in import_parser.errors:
                                        self.errors.append(f"Import error: {error}")

                    # Reset comment for next use
                    current_comment = ""
                    i += 1
                    continue

                # If we're in the middle of parsing a field definition
                if in_field_def:
                    field_type_def += " " + line

                    # Check if this line completes the field definition
                    # A field definition is complete if it has a semicolon or a closing brace with no opening brace after it
                    if line.endswith(';'):
                        # Field definition is complete with semicolon
                        field_type_def = field_type_def.rstrip(';').strip()
                        self._process_field(current_message, field_name, field_type_def, current_comment, field_start_line)
                        current_comment = ""
                        in_field_def = False
                    elif '}' in line and '{' not in line:
                        # Check if this is the final closing brace of an enum or compound
                        open_braces = field_type_def.count('{')
                        close_braces = field_type_def.count('}')
                        if open_braces == close_braces:
                            # Field definition is complete with balanced braces
                            if line.endswith(';'):
                                field_type_def = field_type_def.rstrip(';').strip()
                            self._process_field(current_message, field_name, field_type_def, current_comment, field_start_line)
                            current_comment = ""
                            in_field_def = False
                    # Check if this is a complete enum or compound definition without a semicolon
                    elif '{' in field_type_def and '}' in field_type_def:
                        open_braces = field_type_def.count('{')
                        close_braces = field_type_def.count('}')
                        if open_braces == close_braces:
                            # Field definition is complete with balanced braces
                            self.debug_print(f"DEBUG: Field definition has balanced braces without semicolon: '{field_type_def}'")
                            self._process_field(current_message, field_name, field_type_def, current_comment, field_start_line)
                            current_comment = ""
                            in_field_def = False

                    i += 1
                    continue

                # Parse namespace definition
                elif line.startswith('namespace '):
                    # Extract namespace name
                    namespace_def = line[len('namespace '):].strip()
                    if '{' in namespace_def:
                        namespace_def = namespace_def[:namespace_def.find('{')].strip()

                    namespace_name = namespace_def

                    # Check if namespace name is a reserved keyword
                    if self._is_reserved_keyword(namespace_name):
                        self.errors.append(f"Line {i+1}: Namespace name '{namespace_name}' is a reserved keyword and cannot be used.")
                    else:
                        # Check if namespace already exists
                        existing_namespace = self.model.get_namespace(namespace_name)
                        if existing_namespace:
                            # Use existing namespace
                            current_namespace = existing_namespace
                            # Update comment if available
                            if current_comment:
                                current_namespace.comment = current_comment
                        else:
                            # Create new namespace with comment if available
                            current_namespace = Namespace(
                                name=namespace_name,
                                description=f"{namespace_name} namespace",
                                comment=current_comment
                            )
                            self.model.add_namespace(current_namespace)

                    # Reset comment for next use
                    current_comment = ""

                # Parse message definition
                elif line.startswith('message '):
                    # Extract message name and parent if exists
                    message_def = line[len('message '):].strip()

                    # Handle the case where the message definition is on a single line
                    if message_def.endswith('{}'):
                        message_def = message_def[:-2].strip()
                    elif '{' in message_def:
                        message_def = message_def[:message_def.find('{')].strip()

                    # Check for inheritance
                    parent_message = None
                    if ':' in message_def:
                        # Split at the first colon that's not part of a namespace separator (::)
                        # This ensures we don't split "Tool::Command" incorrectly
                        colon_pos = message_def.find(':')
                        # Check if this is a namespace separator (::)
                        if colon_pos + 1 < len(message_def) and message_def[colon_pos + 1] == ':':
                            # Find the next colon that's not part of a namespace separator
                            colon_pos = message_def.find(':', colon_pos + 2)
                            if colon_pos == -1:
                                # No inheritance colon found, treat the whole thing as the message name
                                message_name = message_def.strip()
                            else:
                                message_name = message_def[:colon_pos].strip()
                                parent_message = message_def[colon_pos + 1:].strip()
                        else:
                            # Regular inheritance colon
                            message_name = message_def[:colon_pos].strip()
                            parent_message = message_def[colon_pos + 1:].strip()
                        # If the parent name contains ::, it's a namespace reference
                        if parent_message and "::" in parent_message:
                            # The parent name is already fully qualified, so we don't need to do anything
                            # But we should check if it's a valid reference
                            if not self.model.get_message(parent_message):
                                # If the parent message doesn't exist yet, we'll assume it's valid
                                # and it will be resolved later when all messages are parsed
                                # Add a warning about the unresolved parent
                                self.warnings.append(f"Line {i+1}: Parent message '{parent_message}' for '{message_name}' not found yet. Will be resolved later.")
                        # If the message is in a namespace, the parent might be in the same namespace
                        elif parent_message and current_namespace:
                            # Check if the parent is in the global scope
                            global_parent = self.model.get_message(parent_message)
                            if not global_parent:
                                # The parent is not in the global scope, so it might be in the same namespace
                                namespaced_parent = f"{current_namespace.name}::{parent_message}"
                                # Check if the parent is in the same namespace
                                if self.model.get_message(namespaced_parent):
                                    # The parent is in the same namespace, so use the fully qualified name
                                    parent_message = namespaced_parent
                    else:
                        message_name = message_def

                    # Check if message name is a reserved keyword
                    if self._is_reserved_keyword(message_name):
                        self.errors.append(f"Line {i+1}: Message name '{message_name}' is a reserved keyword and cannot be used.")
                    else:
                        # Check if a message with the same name already exists in the same namespace
                        full_name = f"{current_namespace.name}::{message_name}" if current_namespace else message_name
                        if self.model.get_message(full_name):
                            self.errors.append(f"Line {i+1}: Duplicate message definition '{full_name}'. A message with the same name already exists in this namespace.")
                        else:
                            # Create new message with comment if available
                            current_message = Message(
                                name=message_name,
                                parent=parent_message,
                                namespace=current_namespace.name if current_namespace else None,
                                description=f"{message_name} message",
                                comment=current_comment,
                                source_file=self.input_file
                            )
                            self.model.add_message(current_message)

                    # Reset comment for next use
                    current_comment = ""

                # Parse field definition
                elif line.startswith('field '):
                    # Check if we're inside a message
                    if current_message is None:
                        self.errors.append(f"Line {i+1}: Field definition outside of a message context: '{line}'")
                        i += 1
                        continue

                    self.debug_print(f"DEBUG: Found field definition: '{line}' in message '{current_message.name}'")

                    # Extract field name and type
                    field_def = line[len('field '):].strip()
                    if ':' in field_def:
                        name, type_def = field_def.split(':', 1)
                        name = name.strip()
                        type_def = type_def.strip()
                        self.debug_print(f"DEBUG: Extracted field name: '{name}', type: '{type_def}'")

                        # Check if this is a complete field definition or spans multiple lines
                        if type_def.endswith(';'):
                            # Complete field definition with semicolon
                            self.debug_print(f"DEBUG: Field definition ends with semicolon: '{type_def}'")
                            type_def = type_def[:-1].strip()
                            self._process_field(current_message, name, type_def, current_comment, i)
                            current_comment = ""
                        elif '}' in type_def and '{' in type_def:
                            # Check if this is a complete enum or compound definition
                            self.debug_print(f"DEBUG: Field definition contains braces: '{type_def}'")
                            open_braces = type_def.count('{')
                            close_braces = type_def.count('}')
                            if open_braces == close_braces:
                                # Complete field definition with balanced braces
                                self.debug_print(f"DEBUG: Field definition has balanced braces: '{type_def}'")
                                if type_def.endswith(';'):
                                    type_def = type_def[:-1].strip()
                                self._process_field(current_message, name, type_def, current_comment, i)
                                current_comment = ""
                            else:
                                # Multi-line field definition
                                self.debug_print(f"DEBUG: Field definition has unbalanced braces: '{type_def}'")
                                in_field_def = True
                                field_name = name
                                field_type_def = type_def
                                field_start_line = i
                        elif '\n' not in type_def and not ((type_def.startswith('enum {') or type_def.startswith('options {')) and '}' not in type_def):
                            # Single-line field definition without semicolon - treat as complete field
                            self.debug_print(f"DEBUG: Field definition is a single line without semicolon: '{type_def}'")
                            self._process_field(current_message, name, type_def, current_comment, i)
                            current_comment = ""
                        else:
                            # Multi-line field definition
                            self.debug_print(f"DEBUG: Field definition is multi-line: '{type_def}'")
                            in_field_def = True
                            field_name = name
                            field_type_def = type_def
                            field_start_line = i

                # Check for closing brace of message or namespace definition
                elif line == '}':
                    if current_message:
                        current_message = None
                    elif current_namespace:
                        current_namespace = None
                    # If there's a comment that wasn't used, discard it
                    current_comment = ""

                # Any other line that's not empty or a comment is an error
                else:
                    # Check if the line contains any non-whitespace characters
                    if line.strip():
                        self.errors.append(f"Line {i+1}: Invalid syntax: '{line}'. Expected 'message', 'namespace', 'field', or a closing brace.")
                    current_comment = ""

                i += 1

            # Validate all references after parsing is complete
            self._validate_references()

            # Report warnings
            if self.warnings:
                print("\nWarnings:")
                for warning in self.warnings:
                    print(f"  {warning}")

            # Report errors and halt if there are any
            if self.errors:
                print("\nErrors:")
                for error in self.errors:
                    print(f"  {error}")
                print("\nParsing failed due to errors. Please fix the errors and try again.")
                return None

            print(f"Successfully parsed {len(self.model.messages)} message definitions.")
            return self.model

        except Exception as e:
            error_msg = f"Error parsing input file: {str(e)}"
            self.errors.append(error_msg)
            print(error_msg)
            return None

    def _parse_enum_field(self, name: str, type_def: str, line_number: int = 0) -> Optional[Field]:
        """
        Parse an enum field definition.

        Args:
            name: The name of the field
            type_def: The type definition string (e.g., "enum { Value1, Value2 }")
            line_number: The line number where the field is defined (default: 0)

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
                # Get everything between the first { and the last }
                enum_str = type_def[type_def.find('{')+1:type_def.rfind('}')].strip()

                # Process each line to remove comments
                processed_lines = []
                for line in enum_str.split('\n'):
                    # Remove comments (anything after //)
                    if '//' in line:
                        line = line[:line.find('//')]
                    processed_lines.append(line.strip())

                # Join the processed lines
                enum_str = ' '.join(processed_lines)

                # If there are commas, split by commas
                if ',' in enum_str:
                    enum_values = []
                    for v in enum_str.split(','):
                        v = v.strip()
                        if v:  # Skip empty values
                            enum_values.append(v)
                # If there are no commas, treat the entire string as a single value
                else:
                    enum_values = [enum_str.strip()]

                # Debug print
                self.debug_print(f"DEBUG: Enum values: {enum_values}")

                # Create EnumValue objects
                for i, value_name in enumerate(enum_values):
                    if value_name:  # Skip empty values
                        # Check if enum value name is a reserved keyword
                        if self._is_reserved_keyword(value_name):
                            self.errors.append(f"Line {line_number}: Enum value '{value_name}' is a reserved keyword and cannot be used.")
                        else:
                            enum_value = EnumValue(name=value_name, value=i)
                            field.enum_values.append(enum_value)

            return field

        except Exception as e:
            error_msg = f"Line {line_number}: Error parsing enum field '{name}': {str(e)}"
            self.errors.append(error_msg)
            return None

    def _parse_compound_field(self, name: str, type_def: str, line_number: int = 0) -> Optional[Field]:
        """
        Parse a compound field definition.

        Args:
            name: The name of the field
            type_def: The type definition string (e.g., "float { x, y, z }")
            line_number: The line number where the field is defined (default: 0)

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

            # Get everything between the first { and the last }
            components_str = type_def[type_def.find('{')+1:type_def.rfind('}')].strip()

            # Process each line to remove comments
            processed_lines = []
            for line in components_str.split('\n'):
                # Remove comments (anything after //)
                if '//' in line:
                    line = line[:line.find('//')]
                processed_lines.append(line.strip())

            # Join the processed lines and split by commas
            components_str = ' '.join(processed_lines)
            components = []
            for c in components_str.split(','):
                c = c.strip()
                if c:  # Skip empty components
                    components.append(c)

            field.compound_base_type = base_type

            # Check if compound component names are reserved keywords
            valid_components = []
            for component in components:
                if component:
                    if self._is_reserved_keyword(component):
                        self.errors.append(f"Line {line_number}: Compound component '{component}' is a reserved keyword and cannot be used.")
                    else:
                        valid_components.append(component)

            field.compound_components = valid_components  # Use only valid components

            return field

        except Exception as e:
            error_msg = f"Line {line_number}: Error parsing compound field '{name}': {str(e)}"
            self.errors.append(error_msg)
            return None

    def _parse_options_field(self, name: str, type_def: str, line_number: int = 0) -> Optional[Field]:
        """
        Parse an options field definition.

        Args:
            name: The name of the field
            type_def: The type definition string (e.g., "options { OptionA, OptionB }")
            line_number: The line number where the field is defined (default: 0)

        Returns:
            The parsed field, or None if parsing failed
        """
        try:
            field = Field(
                name=name,
                field_type=FieldType.OPTIONS,
                description=f"{name} options field"
            )

            # Extract options values
            if '{' in type_def and '}' in type_def:
                # Get everything between the first { and the last }
                options_str = type_def[type_def.find('{')+1:type_def.rfind('}')].strip()

                # Process each line to remove comments
                processed_lines = []
                for line in options_str.split('\n'):
                    # Remove comments (anything after //)
                    if '//' in line:
                        line = line[:line.find('//')]
                    processed_lines.append(line.strip())

                # Join the processed lines
                options_str = ' '.join(processed_lines)

                # Split by commas or pipe symbols
                options_values = []

                # First, check if there are pipe symbols
                if '|' in options_str:
                    # Split by pipe symbols
                    for v in options_str.split('|'):
                        v = v.strip()
                        if v:  # Skip empty values
                            options_values.append(v)
                else:
                    # Split by commas
                    for v in options_str.split(','):
                        v = v.strip()
                        if v:  # Skip empty values
                            options_values.append(v)

                # Create EnumValue objects (options are stored as enum values)
                for i, value_name in enumerate(options_values):
                    if value_name:  # Skip empty values
                        # Check if option value name is a reserved keyword
                        if self._is_reserved_keyword(value_name):
                            self.errors.append(f"Line {line_number}: Option value '{value_name}' is a reserved keyword and cannot be used.")
                        else:
                            enum_value = EnumValue(name=value_name, value=1 << i)  # Use bit flags (1, 2, 4, 8, etc.)
                            field.enum_values.append(enum_value)

            return field

        except Exception as e:
            error_msg = f"Line {line_number}: Error parsing options field '{name}': {str(e)}"
            self.errors.append(error_msg)
            return None

    def _process_field(self, message: Message, name: str, type_def: str, comment: str, line_number: int) -> None:
        """
        Process a field definition and add it to the message.

        Args:
            message: The message to add the field to
            name: The name of the field
            type_def: The type definition string
            comment: The comment for the field
            line_number: The line number where the field is defined
        """
        self.debug_print(f"DEBUG: Processing field '{name}' with type '{type_def}' in message '{message.name}'")
        self.debug_print(f"DEBUG: Message '{message.name}' has {len(message.fields)} fields before processing")
        # Check if field name is a reserved keyword
        if self._is_reserved_keyword(name):
            self.errors.append(f"Line {line_number}: Field name '{name}' is a reserved keyword and cannot be used.")
            return

        # Check for duplicate field names within the message
        for field in message.fields:
            if field.name == name:
                self.errors.append(f"Line {line_number}: Duplicate field name '{name}' in message '{message.name}'.")
                return

        # Check for field name conflicts with parent messages
        if message.parent:
            parent_message = self.model.get_message(message.parent)
            if parent_message:
                # Check all fields in the parent message hierarchy
                current = parent_message
                while current:
                    for field in current.fields:
                        if field.name == name:
                            self.errors.append(f"Line {line_number}: Field name '{name}' in message '{message.name}' conflicts with field in parent message '{current.name}'.")
                            return
                    # Move up to the next parent
                    if current.parent:
                        current = self.model.get_message(current.parent)
                    else:
                        current = None

        # Check if field is optional
        optional = False
        if "optional" in type_def.split():
            optional = True
            # Remove the optional keyword from the type definition
            type_def = type_def.replace("optional", "").strip()

        # Check for default value
        default_value = None
        if "default(" in type_def and ")" in type_def:
            # Extract default value
            start_idx = type_def.find("default(") + len("default(")
            end_idx = type_def.find(")", start_idx)
            if start_idx < end_idx:
                default_value_str = type_def[start_idx:end_idx].strip()
                # Remove the default value specification from the type definition
                type_def = type_def.replace(f"default({default_value_str})", "").strip()

                # Convert the default value to the appropriate type
                if default_value_str.lower() == "true":
                    default_value = True
                elif default_value_str.lower() == "false":
                    default_value = False
                elif default_value_str.isdigit():
                    default_value = int(default_value_str)
                elif default_value_str.replace(".", "", 1).isdigit():
                    default_value = float(default_value_str)
                else:
                    # For enum values or strings, keep as string
                    default_value = default_value_str
                    # If it's a string literal (enclosed in quotes), remove the quotes
                    if (default_value.startswith('"') and default_value.endswith('"')) or \
                       (default_value.startswith("'") and default_value.endswith("'")):
                        default_value = default_value[1:-1]

                # Check if field is both optional and has a default value
                if optional and default_value is not None:
                    warning_msg = f"Line {line_number}: Field '{name}' is both optional and has a default value. Default values for optional fields are never used. The default value will be ignored."
                    self.warnings.append(warning_msg)
                    default_value = None

        # Check for enum references from other messages (e.g., ChangeMode.Mode)
        if '.' in type_def and not type_def.startswith(('enum', 'options')):
            # Extract just the field type (in case there's more content after it)
            field_type = type_def.split()[0] if ' ' in type_def else type_def
            self.errors.append(f"Line {line_number}: Field type '{field_type}' references an enum from another message. This is not currently supported.")
            return

        # Check for message references (e.g., Base::BaseMessage or BaseMessage)
        if not type_def.startswith(('enum', 'options')):
            # Extract just the field type (in case there's more content after it)
            field_type = type_def.split()[0] if ' ' in type_def else type_def

            # Check if the field type is a message reference with a namespace prefix
            if '::' in field_type:
                # Check if the referenced message exists
                referenced_message = self.model.get_message(field_type)
                if not referenced_message:
                    self.warnings.append(f"Line {line_number}: Message '{field_type}' referenced by field '{name}' not found yet. Will be resolved later.")

                # Add an error for using a message as a field type
                self.errors.append(f"Line {line_number}: Using a message '{field_type}' directly as a field type is not supported. Use message inheritance instead.")
                return

            # Check if the field type is a message reference without a namespace prefix
            else:
                # Check if the field type is a simple type
                simple_type = self._get_field_type(field_type)
                if not simple_type:
                    # Check if the field type is a message reference
                    referenced_message = self.model.get_message(field_type)
                    if referenced_message:
                        # Add an error for using a message as a field type
                        error_msg = f"Line {line_number}: Using a message '{field_type}' directly as a field type is not supported. Use message inheritance instead."
                        self.errors.append(error_msg)
                        self.debug_print(f"DEBUG: Generated error: {error_msg}")
                        return

        # Handle enum type
        if type_def.startswith('enum'):
            # Regular enum field
            field = self._parse_enum_field(name, type_def, line_number)
            if field:
                # Add comment if available
                if comment:
                    field.comment = comment
                field.optional = optional
                field.default_value = default_value
                message.fields.append(field)

        # Handle options type
        elif type_def.startswith('options'):
            field = self._parse_options_field(name, type_def, line_number)
            if field:
                # Add comment if available
                if comment:
                    field.comment = comment
                field.optional = optional

                # Special handling for options default values with bitwise AND
                if default_value is not None and isinstance(default_value, str) and '&' in default_value:
                    # Split the default value string by '&' and evaluate each option
                    option_names = [opt.strip() for opt in default_value.split('&')]
                    combined_value = 0

                    # Find the corresponding enum values and combine them with bitwise OR
                    for option_name in option_names:
                        found = False
                        for enum_value in field.enum_values:
                            if enum_value.name == option_name:
                                combined_value |= enum_value.value
                                found = True
                                break
                        if not found:
                            warning_msg = f"Line {line_number}: Option '{option_name}' not found in options field '{name}'"
                            self.warnings.append(warning_msg)

                    # Store the original string representation for readability
                    field.default_value_str = default_value

                    # Set the combined value as the default value
                    field.default_value = combined_value
                else:
                    field.default_value = default_value
                    if isinstance(default_value, str) and not default_value.isdigit():
                        # For single option values, store the original string
                        field.default_value_str = default_value

                message.fields.append(field)

        # Handle compound type (like float { x, y, z })
        elif '{' in type_def and '}' in type_def:
            field = self._parse_compound_field(name, type_def, line_number)
            if field:
                # Add comment if available
                if comment:
                    field.comment = comment
                field.optional = optional
                field.default_value = default_value
                message.fields.append(field)

        # Handle simple type
        else:
            field_type = self._get_field_type(type_def)
            if field_type:
                field = Field(
                    name=name,
                    field_type=field_type,
                    description=f"{name} field",
                    comment=comment,
                    optional=optional,
                    default_value=default_value
                )
                message.fields.append(field)

    def _get_field_type(self, type_name: str) -> Optional[FieldType]:
        """
        Convert a type name string to a FieldType enum value.

        Args:
            type_name: The type name string (e.g., "string", "int", "float", "bool", "byte")

        Returns:
            The corresponding FieldType enum value, or None if not recognized
        """
        type_map = {
            "string": FieldType.STRING,
            "int": FieldType.INT,
            "float": FieldType.FLOAT,
            "bool": FieldType.BOOLEAN,
            "byte": FieldType.BYTE
        }

        return type_map.get(type_name.lower())

    def _is_reserved_keyword(self, name: str) -> bool:
        """
        Check if a name is a reserved keyword.

        Args:
            name: The name to check

        Returns:
            True if the name is a reserved keyword, False otherwise
        """
        return name.lower() in self.reserved_keywords

    def _parse_import_statement(self, line: str, line_number: int) -> Optional[Tuple[str, Optional[str]]]:
        """
        Parse an import statement and extract the file path and namespace.

        Args:
            line: The line containing the import statement
            line_number: The line number in the source file

        Returns:
            A tuple containing the file path and namespace (or None if no namespace), or None if parsing failed
        """
        try:
            # Extract the import statement (remove 'import' keyword)
            import_statement = line[len('import'):].strip()

            # Check if the statement has the 'as' keyword
            if ' as ' in import_statement:
                # Split the statement into file path and namespace
                file_path_part, namespace = import_statement.split(' as ', 1)

                # Clean up the namespace
                namespace = namespace.strip()

                # Validate the namespace
                if not namespace:
                    self.errors.append(f"Line {line_number}: Import statement must specify a non-empty namespace after 'as'.")
                    return None

                if self._is_reserved_keyword(namespace):
                    self.errors.append(f"Line {line_number}: Namespace '{namespace}' is a reserved keyword and cannot be used.")
                    return None
            else:
                # No 'as' keyword, no namespace
                file_path_part = import_statement
                namespace = None  # No namespace when 'as' is omitted

            # Clean up the file path (remove quotes)
            file_path = file_path_part.strip()
            if (file_path.startswith('"') and file_path.endswith('"')) or \
               (file_path.startswith("'") and file_path.endswith("'")):
                file_path = file_path[1:-1]

            # Validate the file path
            if not file_path:
                self.errors.append(f"Line {line_number}: Import statement must specify a non-empty file path.")
                return None

            return file_path, namespace

        except Exception as e:
            error_msg = f"Line {line_number}: Error parsing import statement: {str(e)}"
            self.errors.append(error_msg)
            return None

    def _validate_references(self) -> None:
        """
        Validate all message and namespace references in the model.

        This method checks that all parent messages referenced by messages in the model
        actually exist. If any references are not found, errors are added to the errors list.
        """
        # Check all messages for unresolved parent references
        for message_name, message in list(self.model.messages.items()):  # Use list() to avoid modification during iteration
            if message.parent:
                parent = self.model.get_message(message.parent)
                if not parent:
                    # Check if this is a reference to an imported message
                    if "::" in message.parent:
                        # This is a reference to a message in a namespace
                        # Keep the warning but don't convert it to an error
                        self.warnings.append(f"Warning: Parent message '{message.parent}' referenced by '{message_name}' not found. This might cause issues in generated code.")
                    else:
                        # This is a reference to a message in the global scope
                        self.errors.append(f"Error: Parent message '{message.parent}' referenced by '{message_name}' not found.")

        # Don't convert warnings about unresolved parents to errors
        # This allows messages with parent references to imported messages to be included in the model
        # even if the parent message is not found yet
