"""
Core logic for MessageParser: initialization and main parse loop.
"""

import os
import re
from typing import List, Optional, Tuple, Any
import copy

from message_model import (
    FieldType,
    EnumValue,
    Field,
    Message,
    MessageModel,
    Namespace,
    Enum
)

from message_parser_fields import (
    _parse_enum_values,
    _parse_enum_field,
    _parse_standalone_enum,
    _parse_compound_field,
    _parse_options_field,
    _parse_options,
    _process_field,
    _get_field_type,
    _is_reserved_keyword,
    _parse_import_statement
)
from message_parser_resolve import (
    _validate_references,
    _resolve_message_reference,
    _resolve_enum_reference,
    _resolve_compound_reference
)

class MessageParser:
    """
    Parser for message definition files.
    Converts the input file format to the intermediate representation.
    """

    def __init__(self, input_file: str, verbose: bool = False, base_dir: Optional[str] = None): # Added optional base_dir parameter
        """
        Initialize the parser with the input file path.

        Args:
            input_file: Path to the input file containing message definitions
            verbose: Whether to print debug information (default: False)
            base_dir: Optional base directory for resolving relative import paths
        """
        self.input_file = input_file
        self.model = MessageModel()
        self.errors = []
        self.warnings = []
        self.verbose = verbose
        self.base_dir = base_dir # Store the base directory

        # Store imported models keyed by their alias
        self.imported_models = {}

        # Store seen enum values globally for duplicate checking
        self.seen_enum_values = set()

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
            print(f"[DEBUG] {message}")

    def log_error(self, error: str) -> None:
        """
        Log an error message and add it to the errors list.

        Args:
            error: The error message to log
        """
        self.errors.append(error)
        if self.verbose:
            print(f"[ERROR] {error}")

    def log_warning(self, warning: str) -> None:
        """
        Log a warning message and add it to the warnings list.
        Args:
            warning: The warning message to log
        """
        self.warnings.append(warning)
        if self.verbose:
            print(f"[WARNING] {warning}")

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

            # Set the main file path in the model
            self.model.main_file_path = os.path.abspath(self.input_file)

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

            # Variables to track multi-line enum parsing
            in_enum_def = False
            current_enum = None
            enum_values_str = ""
            enum_start_line = 0

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
                    self.debug_print(f"DEBUG: Found import statement: '{line}' at line {i+1}")
                    # Parse the import statement
                    import_result = _parse_import_statement(line, i+1, self)
                    if import_result:
                        file_path, alias = import_result
                        self.debug_print(f"DEBUG: Parsed import: file_path='{file_path}', alias='{alias}'")

                        # Resolve the file path (relative to the current file)
                        if not os.path.isabs(file_path):
                            # Use the provided base_dir if available, otherwise use the current working directory
                            base_dir = self.base_dir if self.base_dir else os.getcwd() # Use base_dir for resolution
                            self.debug_print(f"DEBUG: Resolving relative import. base_dir='{base_dir}', file_path='{file_path}'")
                            file_path = os.path.normpath(os.path.join(base_dir, file_path))
                            self.debug_print(f"DEBUG: Resolved absolute file_path: '{file_path}'")

                        # Check if the file exists
                        file_exists = os.path.exists(file_path)
                        self.debug_print(f"DEBUG: Checking if file exists: '{file_path}'. Result: {file_exists}")
                        if not file_exists:
                            self.errors.append(f"Line {i+1}: Imported file '{file_path}' does not exist.")
                        else:
                            # Check for circular imports
                            if file_path in imported_files:
                                self.errors.append(f"Line {i+1}: Circular import detected for file '{file_path}'.")
                            else:
                                # Add to imported files set
                                imported_files.add(file_path)

                                # Store the import alias and resolved file path
                                if alias:
                                    if alias in self.model.imports:
                                        self.log_warning(f"Line {i+1}: Import alias '{alias}' is already used. Overwriting.")
                                    self.model.imports[alias] = file_path

                                # Create a new parser for the imported file, passing the base_dir
                                import_parser = MessageParser(file_path, verbose=self.verbose, base_dir=self.base_dir) # Pass base_dir
                                
                                # Parse the imported file
                                import_model = import_parser.parse()

                                # If parsing was successful, add the imported messages and enums to the current model
                                if import_model:
                                    # Store the imported model
                                    if alias:
                                        self.imported_models[alias] = import_model

                                    # Add all messages from the imported model to the current model
                                    for msg_name, message in import_model.messages.items():
                                        # Create a copy of the message to avoid modifying the imported model
                                        imported_message = Message(
                                            name=message.name,
                                            parent=message.parent, # Keep original parent reference
                                            namespace=message.namespace,  # Keep original namespace
                                            description=message.description,
                                            comment=message.comment,
                                            source_file=file_path  # Set the source file to the imported file path
                                        )
                                        # Use deepcopy to ensure all field attributes are copied correctly
                                        imported_message.fields = copy.deepcopy(message.fields)
                                        self.model.add_message(imported_message)

                                    # Add all standalone enums from the imported model
                                    for enum_name, enum in import_model.enums.items():
                                         # Create a copy of the enum
                                        imported_enum = Enum(
                                            name=enum.name,
                                            values=enum.values.copy(), # Copy values
                                            parent=enum.parent, # Keep original parent
                                            namespace=enum.namespace, # Keep original namespace
                                            description=enum.description,
                                            comment=enum.comment,
                                            source_file=file_path, # Set source file
                                            is_open=enum.is_open
                                        )
                                        self.model.add_enum(imported_enum)

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
                    field_type_def += "\n" + line  # Use newline to preserve formatting

                    # Check if this line completes the field definition
                    # A field definition is complete if it has a semicolon or if braces are balanced
                    open_braces = field_type_def.count('{')
                    close_braces = field_type_def.count('}')
                    if (open_braces == close_braces and open_braces > 0) or (not in_field_def and ('{' not in field_type_def and '}' not in field_type_def)):
                        # Field definition is complete
                        # Remove trailing semicolon if present
                        if field_type_def.endswith(';'):
                            field_type_def = field_type_def.rstrip(';').strip()
                        self.debug_print(f"DEBUG: [FIELD ACCUM] Completed field definition for '{field_name}': {repr(field_type_def)}")
                        # Extra debug: print message name and all fields after processing
                        _process_field(self, current_message, field_name, field_type_def, current_comment, field_start_line)
                        self.debug_print(f"DEBUG: [POST_PROCESS] Message '{current_message.name}' now has fields: {[f.name for f in current_message.fields]}")
                        if hasattr(current_message, 'fields'):
                            for f in current_message.fields:
                                self.debug_print(f"DEBUG: [FIELD DETAILS] Field: name={f.name}, type={f.field_type}, enum_values={getattr(f, 'enum_values', None)}, inline_enum={getattr(f, 'inline_enum', None)}")
                        current_comment = ""
                        in_field_def = False
                    # else: keep accumulating
                    i += 1
                    continue

                # If we're in the middle of parsing an enum definition
                elif in_enum_def:
                    enum_values_str += " " + line

                    # Check if this line completes the enum definition
                    if '}' in line:
                        # Get everything up to the closing brace
                        enum_values_str = enum_values_str[:enum_values_str.rfind('}')].strip()

                        # Parse enum values
                        if enum_values_str:
                            current_enum.values = _parse_enum_values(self, enum_values_str, enum_start_line)

                        # Add the enum to the model
                        self.model.add_enum(current_enum)

                        # Reset enum parsing state
                        in_enum_def = False
                        current_enum = None
                        enum_values_str = ""

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
                    if _is_reserved_keyword(self,namespace_name):
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
                    if _is_reserved_keyword(self, message_name):
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
                    self.debug_print(f"DEBUG: [FIELD BLOCK] Entered field parsing for line: {repr(line)}")
                    # Check if we're inside a message
                    if current_message is None:
                        self.errors.append(f"Line {i+1}: Field definition outside of a message context: '{line}'")
                        i += 1
                        continue

                    self.debug_print(f"DEBUG: Found field definition: '{line}' in message '{current_message.name}'")

                    # Accumulate the full field definition, including multi-line, using brace counting
                    field_lines = [line[len('field '):].strip()]
                    open_braces = field_lines[0].count('{')
                    close_braces = field_lines[0].count('}')
                    j = i + 1
                    while (open_braces > close_braces) and j < len(lines):
                        next_line = lines[j].strip()
                        field_lines.append(next_line)
                        open_braces += next_line.count('{')
                        close_braces += next_line.count('}')
                        j += 1
                    # Join all lines for the field definition
                    full_field_def = ' '.join(field_lines)
                    # Tokenize the field definition
                    try:
                        from tokenizer import Tokenizer
                        tokenizer = Tokenizer(full_field_def)
                        tokens = tokenizer.tokens.copy()
                        print(f"[TOKENIZER DEBUG] full_field_def: {full_field_def}")
                        print(f"[TOKENIZER DEBUG] tokens: {tokens}")
                        # Find the colon (field_name : type ...)
                        name = None
                        type_tokens = []
                        for idx, (tok_type, tok_val) in enumerate(tokens):
                            if tok_type == 'COLON':
                                # Use the IDENT immediately before the colon as the field name
                                for rev_idx in range(idx-1, -1, -1):
                                    if tokens[rev_idx][0] == 'IDENT':
                                        name = tokens[rev_idx][1]
                                        break
                                type_tokens = tokens[idx+1:]
                                break
                        # Fallback: if no IDENT before colon, use first IDENT in tokens
                        if name is None:
                            for ttype, val in tokens:
                                if ttype == 'IDENT':
                                    name = val
                                    break
                        if name is None:
                            print(f"[TOKENIZER DEBUG] Could not extract field name from tokens: {tokens}")
                            self.errors.append(f"Line {i+1}: Could not parse field name in definition: '{full_field_def}' (tokens: {tokens})")
                            i = j
                            continue
                        # Reconstruct type_def from tokens, preserving spaces and punctuation for correct parsing
                        punct = {'LBRACE', 'RBRACE', 'LPAREN', 'RPAREN', 'COLON', 'SEMICOLON', 'COMMA', 'EQUALS', 'PIPE', 'LT', 'GT'}
                        type_def = ''
                        n = len(type_tokens)
                        for idx, (ttype, val) in enumerate(type_tokens):
                            if ttype == 'SKIP':
                                continue
                            # Insert a space between IDENT (enum/open_enum) and LBRACE
                            if idx > 0 and type_tokens[idx-1][0] == 'IDENT' and ttype == 'LBRACE':
                                type_def += ' '
                            type_def += val
                            # Add a space if next token is not punctuation and not end
                            if idx + 1 < n:
                                next_type = type_tokens[idx + 1][0]
                                if ttype not in punct and next_type not in punct:
                                    type_def += ' '
                                # Add a space after punctuation if next is not punctuation
                                elif ttype in punct and next_type not in punct:
                                    type_def += ' '
                        # Remove trailing semicolon if present
                        if type_def.endswith(';'):
                            type_def = type_def[:-1].strip()
                        print(f"[TOKENIZER DEBUG] Extracted field name: '{name}', type: '{type_def}' from tokens: {tokens}")
                        _process_field(self, current_message, name, type_def, current_comment, i)
                        current_comment = ""
                        i = j
                        continue
                    except Exception as e:
                        self.errors.append(f"Line {i+1}: Exception during tokenized field parsing: {e}")
                        i = j
                        continue
                # Check for closing brace of message or namespace definition
                elif line == '}':
                    if current_message:
                        current_message = None
                    elif current_namespace:
                        current_namespace = None
                    # If there's a comment that wasn't used, discard it
                    current_comment = ""

                # Parse standalone enum definition
                elif line.startswith('enum ') or line.startswith('open_enum '):
                    is_open = line.startswith('open_enum ')
                    try:
                        # Parse the enum definition
                        enum = _parse_standalone_enum(self, line, is_open, i+1, current_namespace, current_comment)
                        if enum:
                            # Check if this is a complete enum definition or spans multiple lines
                            if '{' in line:
                                # This is a multi-line enum definition
                                # We need to parse the enum values
                                if '{' in line and '}' in line:
                                    # Get everything between the first { and the last }
                                    enum_values_str = line[line.find('{')+1:line.rfind('}')].strip()
                                    if enum_values_str:
                                        # Parse enum values
                                        enum.values = _parse_enum_values(self, enum_values_str, i+1)
                                    # Add the enum to the model
                                    self.model.add_enum(enum)
                                else:
                                    # Start multi-line enum parsing
                                    in_enum_def = True
                                    current_enum = enum
                                    enum_values_str = line[line.find('{')+1:].strip()
                                    enum_start_line = i+1
                            else:
                                # This is a single-line enum definition with no values
                                self.model.add_enum(enum)
                    except Exception as e:
                        self.errors.append(f"Line {i+1}: Exception while parsing enum definition: {e}")
                    # Reset comment for next use
                    current_comment = ""

                # Parse options definition
                elif line.startswith('options '):
                    # Check if we're inside a message or namespace
                    if current_message is None and current_namespace is None:
                        self.errors.append(f"Line {i+1}: Options definition outside of a message or namespace context: '{line}'")
                        i += 1
                        continue

                    # Extract options string
                    options_def = line[len('options '):].strip()
                    if '{' in options_def:
                        options_def = options_def[options_def.find('{')+1:].strip()
                        if options_def.endswith('}'):
                            options_def = options_def[:-1].strip()

                    # Parse options
                    options = _parse_options(options_def)

                    # Add options to the current message or namespace
                    if current_message:
                        current_message.options.update(options)
                    elif current_namespace:
                        current_namespace.options.update(options)

                    # Reset comment for next use
                    current_comment = ""

                # Handle unknown lines
                else:
                    self.errors.append(f"Line {i+1}: Unknown syntax: '{line}'")

                i += 1


            # Fallback: if file ends while in_field_def is True, process the accumulated field
            if in_field_def and field_name and field_type_def:
                self.debug_print(f"DEBUG: [EOF FALLBACK] Processing pending field '{field_name}' at EOF: {repr(field_type_def)}")
                _process_field(self, current_message, field_name, field_type_def, current_comment, field_start_line)
                in_field_def = False

            # Check for errors after initial parsing
            if self.errors:
                self.debug_print("DEBUG: Errors found during initial parsing, returning None.")
                return None

            # After parsing all lines, resolve references
            _validate_references(self)

            # Check for errors after reference validation
            if self.errors:
                self.debug_print("DEBUG: Errors found during reference validation, returning None.")
                return None

            return self.model

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.errors.append(f"An unexpected error occurred during parsing: {e}\n{tb}")
            if self.verbose:
                print(f"[EXCEPTION] {e}\n{tb}")
            return None