"""
Field, enum, and options parsing helpers for MessageParser.
"""

from typing import List, Optional, Any
from message_model import FieldType, EnumValue, Field, Message, Enum, Namespace

def _parse_enum_values(self, enum_str: str, line_number: int = 0) -> List[EnumValue]:
    self.debug_print(f"DEBUG: _parse_enum_values input: '{enum_str}' (line {line_number})")
    values = []
    next_implicit_value = 0
    seen_names_local = set() # Use a local set for names within this enum block
    # Add a local set for values within this enum block
    seen_values_local = set()

    enum_value_defs = []
    balance = 0
    current_def = ""
    for char in enum_str:
        if char == ',' and balance == 0:
            enum_value_defs.append(current_def.strip())
            current_def = ""
        else:
            current_def += char
            if char == '(':
                balance += 1
            elif char == ')':
                balance -= 1
    if current_def:
        enum_value_defs.append(current_def.strip())
    for value_def in enum_value_defs:
        self.debug_print(f"DEBUG: _parse_enum_values processing value_def: '{value_def}'")
        if not value_def:
            continue
        name = ""
        value = None
        options = {}
        if '=' in value_def:
            name_part, value_part = value_def.split('=', 1)
            name = name_part.strip()
            value_part = value_part.strip()
            if '(' in value_part and value_part.endswith(')'):
                value_str, options_str = value_part.split('(', 1)
                value_str = value_str.strip()
                options_str = options_str[:-1].strip()
                options = _parse_options(self, options_str)
            else:
                value_str = value_part
            try:
                value = int(value_str)
                next_implicit_value = value + 1
                self.debug_print(f"DEBUG: _parse_enum_values parsed explicit value: {value}, next_implicit_value: {next_implicit_value}")
            except ValueError:
                self.errors.append(f"Line {line_number}: Invalid enum value for '{name}': '{value_str}'. Value must be an integer.")
                continue
        else:
            name = value_def.strip()
            value = next_implicit_value
            next_implicit_value += 1
            self.debug_print(f"DEBUG: _parse_enum_values assigned implicit value: {value}, next_implicit_value: {next_implicit_value}")
            if '(' in name and name.endswith(')'):
                name_part, options_str = name.split('(', 1)
                name = name_part.strip()
                options_str = options_str[:-1].strip()
                options = _parse_options(self, options_str)
        if _is_reserved_keyword(self, name):
            self.errors.append(f"Line {line_number}: Enum value name '{name}' is a reserved keyword and cannot be used.")
            continue

        # Check for duplicate names within this enum block
        if name in seen_names_local:
             self.errors.append(f"Line {line_number}: Duplicate enum value name '{name}' in enum definition.")
             continue
        seen_names_local.add(name)

        # Check for duplicate values within this enum block
        if value in seen_values_local:
             self.errors.append(f"Line {line_number}: Duplicate enum value '{value}' in enum definition.")
             continue
        seen_values_local.add(value)

        # Do NOT check for duplicate values against the global set here.
        # This will be done after all values for an enum are collected.

        values.append(EnumValue(name=name, value=value, options=options))
    return values

def _parse_enum_field(self, name: str, type_def: str, line_number: int = 0) -> Optional[Field]:
    self.debug_print(f"DEBUG: _parse_enum_field received type_def: '{type_def}'")
    enum_def = type_def[len('enum '):].strip()
    self.debug_print(f"DEBUG: _parse_enum_field - enum_def after removing 'enum ': '{enum_def}'")
    enum_reference = None
    inline_enum = None
    if '+' in enum_def:
        parts = enum_def.split('+', 1)
        enum_reference_part = parts[0].strip()
        inline_enum_part = parts[1].strip()
        self.debug_print(f"DEBUG: _parse_enum_field - Combined type detected. enum_reference_part: '{enum_reference_part}', inline_enum_part: '{inline_enum_part}'")
        if enum_reference_part.startswith('enum '):
            enum_reference = enum_reference_part[len('enum '):].strip()
        else:
            enum_reference = enum_reference_part
        # Normalize enum_reference by removing spaces around the dot
        if enum_reference and '.' in enum_reference:
            enum_reference = '.'.join([part.strip() for part in enum_reference.split('.')])
        if inline_enum_part.startswith('enum {') or inline_enum_part.startswith('open_enum {'):
            is_open = inline_enum_part.startswith('open_enum {')
            content_str = inline_enum_part[len('open_enum {'):].strip() if is_open else inline_enum_part[len('enum {'):].strip()
            if content_str.endswith('}'):
                content_str = content_str[:-1].strip()
            values = _parse_enum_values(self, content_str, line_number)
            inline_enum = Enum(name=f"{name}_Enum", values=values, is_open=is_open)
            self.debug_print(f"DEBUG: _parse_enum_field parsed inline enum with {len(values)} values")
        elif inline_enum_part.startswith('{'): # Added this condition
            is_open = False # Inline enums starting with { are not open by default
            content_str = inline_enum_part[len('{'):].strip()
            if content_str.endswith('}'):
                content_str = content_str[:-1].strip()
            values = _parse_enum_values(self, content_str, line_number)
            inline_enum = Enum(name=f"{name}_Enum", values=values, is_open=is_open)
            self.debug_print(f"DEBUG: _parse_enum_field parsed inline enum with {len(values)} values (starts with {{}})")
        else:
            self.errors.append(f"Line {line_number}: Invalid inline enum definition in combined type for field '{name}': '{inline_enum_part}'")
            return None
    elif enum_def.startswith('{'):
        start = enum_def.find('{')
        end = enum_def.rfind('}')
        if start != -1 and end != -1 and end > start:
            enum_values_str = enum_def[start+1:end].strip()
            self.debug_print(f"DEBUG: Extracted inline enum values string: '{enum_values_str}'")
            values = _parse_enum_values(self, enum_values_str, line_number)
            inline_enum = Enum(name=f"{name}_Enum", values=values, is_open=False)
        else:
            enum_values_str = enum_def[1:].strip()
            if enum_values_str.endswith('}'):
                enum_values_str = enum_values_str[:-1].strip()
            self.debug_print(f"DEBUG: Fallback inline enum values string: '{enum_values_str}'")
            values = _parse_enum_values(self, enum_values_str, line_number)
            inline_enum = Enum(name=f"{name}_Enum", values=values, is_open=False)
    elif (',' in enum_def or '=' in enum_def) and not enum_def.startswith('{'):
        enum_values_str = enum_def.strip()
        self.debug_print(f"DEBUG: Detected inline enum without braces: '{enum_values_str}'")
        values = _parse_enum_values(self, enum_values_str, line_number)
        inline_enum = Enum(name=f"{name}_Enum", values=values, is_open=False)
        enum_reference = None
    else:
        enum_reference = enum_def
        # Normalize enum_reference by removing spaces around the dot
        if enum_reference and '.' in enum_reference:
            enum_reference = '.'.join([part.strip() for part in enum_reference.split('.')])
        self.debug_print(f"DEBUG: _parse_enum_field identified enum reference: '{enum_reference}'")
    enum_values = None
    if inline_enum is not None:
        enum_values = inline_enum.values
    field = Field(
        name=name,
        field_type=FieldType.ENUM,
        enum_reference=enum_reference,
        inline_enum=inline_enum,
        enum_values=enum_values,
        source_file=self.input_file,
        line_number=line_number
    )
    self.debug_print(f"DEBUG: _parse_enum_field returning field: name='{field.name}', field_type={field.field_type}, enum_reference='{field.enum_reference}', inline_enum={field.inline_enum}, enum_values={enum_values}, optional={field.optional}")
    return field

def _parse_standalone_enum(self, line: str, is_open: bool, line_number: int = 0, current_namespace: Optional[Namespace] = None, current_comment: str = "") -> Optional[Enum]:
    self.debug_print(f"DEBUG: _parse_standalone_enum input: '{line}' (line {line_number})")
    try:
        enum_def = line[len('open_enum '):].strip() if is_open else line[len('enum '):].strip()
        enum_name = ""
        enum_values_str = ""
        parent_enum = None
        if '{' in enum_def:
            name_part, values_part = enum_def.split('{', 1)
            name_part = name_part.strip()
            if ':' in name_part:
                enum_name, parent_enum = [s.strip() for s in name_part.split(':', 1)]
                self.debug_print(f"DEBUG: _parse_standalone_enum found parent enum: '{parent_enum}'")
            else:
                enum_name = name_part
            enum_values_str = values_part.strip()
            if enum_values_str.endswith('}'):
                enum_values_str = enum_values_str[:-1].strip()
        else:
            name_part = enum_def.strip()
            if ':' in name_part:
                enum_name, parent_enum = [s.strip() for s in name_part.split(':', 1)]
                self.debug_print(f"DEBUG: _parse_standalone_enum found parent enum: '{parent_enum}'")
            else:
                enum_name = name_part
        if _is_reserved_keyword(self, enum_name):
            self.errors.append(f"Line {line_number}: Enum name '{enum_name}' is a reserved keyword and cannot be used.")
            return None
        full_name = f"{current_namespace.name}::{enum_name}" if current_namespace else enum_name
        if self.model.get_enum(full_name):
            self.errors.append(f"Line {line_number}: Duplicate standalone enum definition '{full_name}'. An enum with the same name already exists in this namespace.")
            return None
        values = _parse_enum_values(self, enum_values_str, line_number)

        # Check for duplicate values in the collected values against the global set
        for value_obj in values:
            try:
                int_value = int(value_obj.value)
            except ValueError:
                # Error already logged in _parse_enum_values, skip duplicate check
                continue

            if int_value in self.seen_enum_values:
                self.errors.append(f"Line {line_number}: Duplicate enum value '{value_obj.value}' in standalone enum '{enum_name}'.")
                self.errors.append(f"Line {line_number}: Duplicate enum value in standalone enum '{enum_name}'.")
                self.debug_print(f"DEBUG: Detected duplicate value: '{value_obj.value}' for name '{value_obj.name}' in standalone enum '{enum_name}'")
            else:
                self.seen_enum_values.add(int_value) # Add to the global seen_enum_values

        enum = Enum(
            name=enum_name,
            values=values,
            parent=parent_enum,
            namespace=current_namespace.name if current_namespace else None,
            description=f"{enum_name} enum",
            comment=current_comment,
            source_file=self.input_file,
            is_open=is_open
        )
        return enum
    except Exception as e:
        self.errors.append(f"Line {line_number}: Error parsing enum definition: {e}")
        return None

def _parse_compound_field(self, name: str, type_def: str, line_number: int = 0) -> Optional[Field]:
    if type_def.startswith('message {'):
        compound_type = FieldType.INLINE_MESSAGE
        content_str = type_def[len('message {'):].strip()
    elif type_def.startswith('enum {') or type_def.startswith('open_enum {'):
        compound_type = FieldType.ENUM
        is_open = type_def.startswith('open_enum {')
        type_def_stripped = type_def.strip()
        start = type_def_stripped.find('{')
        if start != -1:
            brace_count = 1
            content_chars = []
            i = start + 1
            while i < len(type_def_stripped):
                c = type_def_stripped[i]
                if c == '{':
                    brace_count += 1
                elif c == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        break
                content_chars.append(c)
                i += 1
            content_str = ''.join(content_chars).strip()
            if brace_count > 0 and hasattr(self, '_current_multiline_field_lines') and self._current_multiline_field_lines:
                multiline = type_def_stripped + '\n' + '\n'.join(self._current_multiline_field_lines)
                start = multiline.find('{')
                brace_count = 1
                content_chars = []
                i = start + 1
                while i < len(multiline):
                    c = multiline[i]
                    if c == '{':
                        brace_count += 1
                    elif c == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            break
                    content_chars.append(c)
                    i += 1
                content_str = ''.join(content_chars).strip()
            if brace_count > 0:
                self.errors.append(f"Line {line_number}: Could not robustly extract inline enum values for field '{name}' (unbalanced braces)")
                return None
        else:
            self.errors.append(f"Line {line_number}: Could not robustly extract inline enum values for field '{name}' (no opening brace)")
            return None
    elif type_def.startswith('options {'):
        compound_type = FieldType.OPTIONS
        content_str = type_def[len('options {'):].strip()
    else:
        self.errors.append(f"Line {line_number}: Invalid inline compound type definition: '{type_def}'")
        return None
    if content_str.endswith('}'):
        content_str = content_str[:-1].strip()
    inline_message = None
    inline_enum = None
    inline_options = None
    enum_values = None
    if hasattr(self, '_current_multiline_field_lines'):
        self._current_multiline_field_lines = []
    if compound_type == FieldType.INLINE_MESSAGE:
        temp_parser = self.__class__(self.input_file)
        temp_parser.model = type(self.model)()
        temp_parser.errors = []
        temp_lines = content_str.splitlines()
        temp_i = 0
        temp_current_message = Message(name="InlineMessage", source_file=self.input_file, line_number=line_number)
        temp_parser.model.add_message(temp_current_message)
        while temp_i < len(temp_lines):
            temp_line = temp_lines[temp_i].strip()
            if temp_line.startswith('field '):
                temp_field_def = temp_line[len('field '):].strip()
                if ':' in temp_field_def:
                    temp_name, temp_type_def = temp_field_def.split(':', 1)
                    temp_name = temp_name.strip()
                    temp_type_def = temp_type_def.strip()
                    _process_field(temp_parser, temp_current_message, temp_name, temp_type_def, "", line_number)
            temp_i += 1
        if not temp_parser.errors:
            inline_message = temp_current_message
        else:
            for error in temp_parser.errors:
                self.errors.append(f"Line {line_number}: Error parsing inline message: {error}")
            return None
    elif compound_type == FieldType.ENUM:
        self.debug_print(f"DEBUG: _parse_compound_field about to parse enum values: '{content_str}'")
        values = _parse_enum_values(self, content_str, line_number)
        inline_enum = Enum(name=f"{name}_Enum", values=values, is_open=is_open)
        enum_values = values

        # Check for duplicate values within the inline enum itself
        seen_values_local_to_field = set()
        for value_obj in values:
            try:
                int_value = int(value_obj.value)
            except ValueError:
                # Error already logged in _parse_enum_values, skip duplicate check
                continue

            if int_value in seen_values_local_to_field:
                self.errors.append(f"Line {line_number}: Duplicate enum value '{value_obj.value}' in inline enum for field '{name}'.")
                self.debug_print(f"DEBUG: Detected duplicate value within inline enum: '{int_value}' for name '{value_obj.name}' in inline enum for field '{name}'")
            seen_values_local_to_field.add(int_value)

        # The global seen_enum_values check should happen in _validate_references for standalone enums and their extensions.
        # For inline enums within fields, the duplicate check is primarily within the inline definition itself.
        # We might still need to consider if an inline enum value duplicates a value in the base enum it extends,
        # but that's a separate check that should likely happen during reference validation.

    elif compound_type == FieldType.OPTIONS:
        inline_options = _parse_options(self, content_str)
        enum_values = []
        bit = 1
        for opt_name in inline_options.keys() if inline_options else []:
            enum_values.append(EnumValue(name=opt_name, value=bit))
            bit <<= 1
    field = Field(
        name=name,
        field_type=compound_type,
        inline_message=inline_message,
        inline_enum=inline_enum,
        inline_options=inline_options,
        enum_values=enum_values,
        source_file=self.input_file,
        line_number=line_number
    )
    return field

def _parse_options_field(self, name: str, type_def: str, line_number: int = 0) -> Optional[Field]:
    options_def = type_def[len('options '):].strip()
    options_reference = None
    inline_options = None
    if options_def.startswith('{'):
        options_str = options_def[1:].strip()
        if options_str.endswith('}'):
            options_str = options_str[:-1].strip()
        inline_options = _parse_options(self, options_str)
    else:
        options_reference = options_def
    field = Field(
        name=name,
        field_type=FieldType.OPTIONS,
        options_reference=options_reference,
        inline_options=inline_options,
        source_file=self.input_file,
        line_number=line_number
    )
    return field

def _parse_options(self, options_str: str) -> dict:
    options = {}
    option_defs = []
    balance = 0
    current_def = ""
    for char in options_str:
        if char == ',' and balance == 0:
            option_defs.append(current_def.strip())
            current_def = ""
        else:
            current_def += char
            if char == '(':
                balance += 1
            elif char == ')':
                balance -= 1
    if current_def:
        option_defs.append(current_def.strip())
    for option_def in option_defs:
        if ':' in option_def:
            key, value = option_def.split(':', 1)
            options[key.strip()] = value.strip()
    return options

def _process_field(self, message: Message, name: str, type_def: str, comment: str, line_number: int) -> None:
    if _is_reserved_keyword(self, name):
        self.errors.append(f"Line {line_number}: Field name '{name}' is a reserved keyword and cannot be used.")
        return
    if any(field.name == name for field in message.fields):
        self.errors.append(f"Line {line_number}: Duplicate field name '{name}' in message '{message.name}'.")
        return
    is_optional = False
    if type_def.startswith('optional '):
        is_optional = True
        type_def = type_def[len('optional '):].strip()
    default_value = None
    if ' = ' in type_def:
        type_def, default_value_str = type_def.split(' = ', 1)
        default_value = default_value_str.strip()
        if default_value.endswith(';'):
            default_value = default_value[:-1].strip()
    options = {}
    if '(' in type_def and type_def.endswith(')'):
        type_name, options_str = type_def.split('(', 1)
        type_name = type_name.strip()
        options_str = options_str[:-1].strip()
        options = _parse_options(self, options_str)
        type_def = type_name
    self.debug_print(f"DEBUG: [PROCESS_FIELD] Processing field '{name}' with type_def: {repr(type_def)}")
    is_array = False
    array_size = None
    if '[' in type_def and type_def.endswith(']'):
        is_array = True
        type_name, array_size_str = type_def.split('[', 1)
        type_name = type_name.strip()
        array_size_str = array_size_str[:-1].strip()
        if array_size_str:
            try:
                array_size = int(array_size_str)
            except ValueError:
                self.errors.append(f"Line {line_number}: Invalid array size for field '{name}': '{array_size_str}'. Array size must be an integer.")
                return
        type_def = type_name
    is_map = False
    map_key_type = None
    if '<' in type_def and '>' in type_def and 'map' in type_def:
        is_map = True
        map_def = type_def[type_def.find('<') + 1:type_def.rfind('>')].strip()
        if ',' in map_def:
            map_key_type, type_name = map_def.split(',', 1)
            map_key_type = map_key_type.strip()
            type_name = type_name.strip()
            type_def = type_name
        else:
            self.errors.append(f"Line {line_number}: Invalid map definition for field '{name}': '{type_def}'. Expected format is 'map<key_type, value_type>'.")
            return
    if type_def.startswith("enum "):
        self.debug_print(f"DEBUG: Handling enum type: '{type_def}'")
        enum_field = _parse_enum_field(self, name, type_def, line_number)
        if enum_field:
            enum_field.field_type = FieldType.ENUM
            if enum_field.inline_enum is not None:
                enum_field.enum_values = enum_field.inline_enum.values
            elif enum_field.enum_reference is not None:
                referenced_enum = self.model.get_enum(enum_field.enum_reference)
                if referenced_enum:
                    if hasattr(referenced_enum, 'get_all_values'):
                        enum_field.enum_values = referenced_enum.get_all_values()
                    else:
                        enum_field.enum_values = referenced_enum.values
            enum_field.comment = comment
            enum_field.optional = is_optional
            enum_field.default_value = default_value
            enum_field.is_array = is_array
            enum_field.array_size = array_size
            enum_field.is_map = is_map
            enum_field.map_key_type = map_key_type
            enum_field.options.update(options)
            message.add_field(enum_field)
            return
    compound_starts = [
        'message {', 'message{',
        'open_enum {', 'open_enum{',
        'options {', 'options{'
    ]
    if any(type_def.startswith(prefix) for prefix in compound_starts):
        self.debug_print(f"DEBUG: _process_field using _parse_compound_field for '{name}' with type_def: '{type_def}'")
        field = _parse_compound_field(self, name, type_def, line_number)
        if field:
            field.comment = comment
            field.optional = is_optional
            field.default_value = default_value
            field.is_array = is_array
            field.array_size = array_size
            field.is_map = is_map
            field.map_key_type = map_key_type
            field.options.update(options)
            if field.inline_enum is not None:
                field.field_type = FieldType.ENUM
                field.enum_values = field.inline_enum.values
                self.debug_print(f"DEBUG: _process_field detected inline_enum with {len(field.enum_values) if field.enum_values else 0} values: {field.enum_values}")
            if field.inline_options is not None and field.field_type == FieldType.OPTIONS:
                pass
            message.add_field(field)
        return
    if '.' in type_def:
        self.debug_print(f"DEBUG: Handling enum type: '{type_def}'")
        enum_field = _parse_enum_field(self, name, type_def, line_number)
        if enum_field:
            enum_field.field_type = FieldType.ENUM
            if enum_field.inline_enum is not None:
                enum_field.enum_values = enum_field.inline_enum.values
            elif enum_field.enum_reference is not None:
                referenced_enum = self.model.get_enum(enum_field.enum_reference)
                if referenced_enum:
                    if hasattr(referenced_enum, 'get_all_values'):
                        enum_field.enum_values = referenced_enum.get_all_values()
                    else:
                        enum_field.enum_values = referenced_enum.values
            enum_field.comment = comment
            enum_field.optional = is_optional
            enum_field.default_value = default_value
            enum_field.is_array = is_array
            enum_field.array_size = array_size
            enum_field.is_map = is_map
            enum_field.map_key_type = map_key_type
            enum_field.options.update(options)
            message.add_field(enum_field)
            return
    referenced_message = self.model.get_message(type_def)
    if not referenced_message and '::' in type_def:
        referenced_message = self.model.get_message(type_def)
    if referenced_message:
        self.debug_print(f"DEBUG: Handling message reference type: '{type_def}'")
        field = Field(
            name=name,
            field_type=FieldType.MESSAGE_REFERENCE,
            message_reference=type_def,
            comment=comment,
            optional=is_optional,
            default_value=default_value,
            is_array=is_array,
            array_size=array_size,
            is_map=is_map,
            map_key_type=map_key_type,
            options=options
        )
        message.add_field(field)
        return
    field_type = _get_field_type(self, type_def)
    if field_type:
        self.debug_print(f"DEBUG: Handling primitive type: '{type_def}'")
        field = Field(
            name=name,
            field_type=field_type,
            comment=comment,
            optional=is_optional,
            default_value=default_value,
            is_array=is_array,
            array_size=array_size,
            is_map=is_map,
            map_key_type=map_key_type,
            options=options
        )
        message.add_field(field)
        return
    self.warnings.append(f"Line {line_number}: Unknown field type or unresolved reference '{type_def}' for field '{name}'. Will attempt to resolve later.")
    self.debug_print(f"DEBUG: Handling unknown or unresolved type: '{type_def}'")
    field = Field(
        name=name,
        field_type=FieldType.UNKNOWN,
        type_name=type_def,
        comment=comment,
        optional=is_optional,
        default_value=default_value,
        is_array=is_array,
        array_size=array_size,
        is_map=is_map,
        map_key_type=map_key_type,
        options=options
    )
    message.add_field(field)
    return

def _get_field_type(self, type_name: str) -> Optional[FieldType]:
    type_map = {
        "string": FieldType.STRING,
        "int": FieldType.INT,
        "float": FieldType.FLOAT,
        "bool": FieldType.BOOL,
        "boolean": FieldType.BOOLEAN,
        "byte": FieldType.BYTE,
    }
    return type_map.get(type_name)

def _is_reserved_keyword(self, name: str) -> bool:
    return name in self.reserved_keywords

def _parse_import_statement(self, line: str, line_number: int) -> Optional[tuple]:
    try:
        import_def = line[len('import '):].strip()
        if not (import_def.startswith('"') and '"' in import_def[1:]):
            self.errors.append(f"Line {line_number}: Invalid import statement format. File path must be enclosed in double quotes.")
            return None
        import re
        file_path_match = re.match(r'"(\.?/?.*?)"', import_def)
        if not file_path_match:
            self.errors.append(f"Line {line_number}: Invalid import statement format. File path not found.")
            return None
        file_path = file_path_match.group(1)
        alias = None
        alias_match = re.search(r'as (\w+)', import_def)
        if alias_match:
            alias = alias_match.group(1)
            if _is_reserved_keyword(self, alias):
                self.errors.append(f"Line {line_number}: Import alias '{alias}' is a reserved keyword and cannot be used.")
                return None
        return file_path, alias
    except Exception as e:
        self.errors.append(f"Line {line_number}: Error parsing import statement: {e}")
        return None

