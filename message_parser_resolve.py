"""
Reference resolution and validation helpers for MessageParser.
"""

from typing import Optional, Any
from message_model import Message, Enum

def _validate_references(self) -> None:
    self.debug_print("DEBUG: Starting reference validation...")
    for message in self.model.messages.values():
        self.debug_print(f"DEBUG: Validating references for message: '{message.name}'")
        if message.parent:
            self.debug_print(f"DEBUG: Validating parent message reference: '{message.parent}' for message '{message.name}'")
            parent_message = _resolve_message_reference(self, message.parent)
            if not parent_message:
                self.errors.append(f"Message '{message.name}': Parent message '{message.parent}' not found.")
                self.debug_print(f"DEBUG: Parent message '{message.parent}' not found for '{message.name}'.")
            else:
                message.parent_message = parent_message
                self.debug_print(f"DEBUG: Resolved parent message '{message.parent}' for '{message.name}'.")
        for field in message.fields:
            if field.field_type.name == "MESSAGE_REFERENCE":
                referenced_message = _resolve_message_reference(self, field.message_reference)
                if not referenced_message:
                    self.errors.append(f"Message '{message.name}', Field '{field.name}': Referenced message '{field.message_reference}' not found.")
                else:
                    field.message = referenced_message
            elif field.field_type.name == "ENUM":
                referenced_enum = _resolve_enum_reference(self, field.enum_reference)
                if not referenced_enum and field.enum_reference:
                    if '.' in field.enum_reference:
                        msg_name, enum_name = field.enum_reference.split('.', 1)
                        msg_name = msg_name.strip()  # <-- Strip whitespace
                        enum_name = enum_name.strip()  # <-- Strip whitespace
                        msg_obj = self.model.get_message(msg_name)
                        if not msg_obj:
                            self.errors.append(f"Message '{msg_name}' referenced by enum reference '{field.enum_reference}' not found.")
                        else:
                            self.errors.append(f"Enum '{enum_name}' not found in message '{msg_name}' referenced by enum reference '{field.enum_reference}'.")
                else:
                    field.enum = referenced_enum
                    if referenced_enum and field.inline_enum:
                        merged_values = []
                        seen_names = set()
                        # Removed local seen_values set

                        # Add referenced enum values first and to the global seen_enum_values
                        for ev in referenced_enum.values:
                            merged_values.append(ev)
                            seen_names.add(ev.name)
                            try:
                                self.seen_enum_values.add(int(ev.value))
                            except ValueError:
                                self.errors.append(f"Invalid value '{ev.value}' in referenced enum '{referenced_enum.name}'. Value must be an integer.")
                                # Continue processing other values
                                pass

                        # Add extension values, checking for duplicates against the global seen_enum_values
                        for ext_ev in field.inline_enum.values:
                            if ext_ev.name in seen_names:
                                self.errors.append(f"Duplicate enum value name '{ext_ev.name}' in extended enum reference '{field.enum_reference}' for field '{field.name}' in message '{message.name}'.")
                                self.errors.append(f"Duplicate enum value in extended enum reference '{field.enum_reference}' for field '{field.name}' in message '{message.name}'.")
                                continue
                            try:
                                int_ext_value = int(ext_ev.value)
                            except ValueError:
                                self.errors.append(f"Invalid value '{ext_ev.value}' in inline enum extension for field '{field.name}' in message '{message.name}'. Value must be an integer.")
                                continue

                            if int_ext_value in self.seen_enum_values:
                                self.errors.append(f"Duplicate enum value '{ext_ev.value}' in extended enum reference '{field.enum_reference}' for field '{field.name}' in message '{message.name}'.")
                                self.errors.append(f"Duplicate enum value in extended enum reference '{field.enum_reference}' for field '{field.name}' in message '{message.name}'.")
                                continue
                            merged_values.append(ext_ev)
                            seen_names.add(ext_ev.name)
                            self.seen_enum_values.add(int_ext_value) # Add to the global seen_enum_values
                            field.enum_values = merged_values
                    elif referenced_enum:
                        field.enum_values = referenced_enum.values
                    elif field.inline_enum:
                        field.enum_values = field.inline_enum.values
            elif field.field_type.name == "OPTIONS":
                options_name = field.options_reference
                referenced_options = self.model.get_options(options_name)
                if not referenced_options and '::' in options_name:
                    referenced_options = self.model.get_options(options_name)
                if not referenced_options:
                    self.errors.append(f"Message '{message.name}', Field '{field.name}': Referenced options '{field.options_reference}' not found.")
                else:
                    field.options_obj = referenced_options
    for enum in self.model.enums.values():
        self.debug_print(f"DEBUG: Validating parent reference for standalone enum: '{enum.name}'")
        if enum.parent:
            self.debug_print(f"DEBUG: Resolving parent enum reference: '{enum.parent}' for standalone enum '{enum.name}'")
            parent_enum = _resolve_enum_reference(self, enum.parent)
            if not parent_enum:
                self.errors.append(f"Standalone Enum '{enum.name}': Parent enum '{enum.parent}' not found.")
                self.debug_print(f"DEBUG: Parent enum '{enum.parent}' not found for standalone enum '{enum.name}'.")
            else:
                enum.parent_enum = parent_enum
                self.debug_print(f"DEBUG: Resolved parent enum '{enum.parent}' for standalone enum '{enum.name}'.")
    # Options inheritance validation can be added here if needed

def _resolve_message_reference(self, reference: str) -> Optional[Message]:
    self.debug_print(f"DEBUG: Resolving message reference: '{reference}'")
    if '::' in reference:
        parts = reference.split('::', 1)
        alias_or_namespace = parts[0]
        message_name = parts[1]
        if alias_or_namespace in self.imported_models:
            imported_model = self.imported_models[alias_or_namespace]
            for msg in imported_model.messages.values():
                if msg.name == message_name:
                    self.debug_print(f"DEBUG: Resolved message reference '{reference}' to imported message '{msg.get_full_name()}'")
                    return msg
            referenced_message = imported_model.get_message(message_name)
            if referenced_message:
                self.debug_print(f"DEBUG: Resolved message reference '{reference}' to imported namespaced message '{referenced_message.get_full_name()}'")
                return referenced_message
        else:
            full_name = reference
            referenced_message = self.model.get_message(full_name)
            if referenced_message:
                self.debug_print(f"DEBUG: Resolved message reference '{reference}' to namespaced message '{referenced_message.get_full_name()}'")
                return referenced_message
    else:
        referenced_message = self.model.get_message(reference)
        if referenced_message:
            self.debug_print(f"DEBUG: Resolved message reference '{reference}' to global message '{referenced_message.get_full_name()}'")
            return referenced_message
    self.debug_print(f"DEBUG: Message reference '{reference}' not resolved.")
    return None

def _resolve_enum_reference(self, reference: str) -> Optional[Enum]:
    self.debug_print(f"DEBUG: Resolving enum reference: '{reference}'")
    if reference is None:
        self.debug_print("DEBUG: Enum reference is None, skipping resolution.")
        return None
    if '::' in reference:
        parts = reference.split('::', 1)
        alias_or_namespace = parts[0]
        rest_of_reference = parts[1]
        if alias_or_namespace in self.imported_models:
            imported_model = self.imported_models[alias_or_namespace]
            self.debug_print(f"DEBUG: Found imported model for alias '{alias_or_namespace}'")
            if '.' in rest_of_reference:
                msg_enum_parts = rest_of_reference.split('.', 1)
                message_name_part = msg_enum_parts[0]
                inline_enum_name = msg_enum_parts[1]
                inline_enum_lookup_name = f"{inline_enum_name}_Enum"
                self.debug_print(f"DEBUG: Resolving inline enum '{inline_enum_name}' within message '{message_name_part}' in imported model")
                referenced_message = None
                for msg in imported_model.messages.values():
                    if msg.name == message_name_part or msg.get_full_name() == message_name_part:
                        referenced_message = msg
                        break
                if referenced_message:
                    self.debug_print(f"DEBUG: Found referenced message '{referenced_message.get_full_name()}' in imported model. Checking inline enums.")
                    if inline_enum_lookup_name in referenced_message.inline_enums:
                        self.debug_print(f"DEBUG: Resolved enum reference '{reference}' to imported inline enum '{referenced_message.inline_enums[inline_enum_lookup_name].get_full_name()}'")
                        return referenced_message.inline_enums[inline_enum_lookup_name]
                    else:
                        self.debug_print(f"DEBUG: Inline enum '{inline_enum_lookup_name}' not found in imported message '{referenced_message.get_full_name()}'.")
                else:
                    self.debug_print(f"DEBUG: Message '{message_name_part}' not found in imported model.")
            else:
                self.debug_print(f"DEBUG: Resolving standalone enum '{rest_of_reference}' in imported model")
                referenced_enum = None
                for enum in imported_model.enums.values():
                    if enum.name == rest_of_reference or enum.get_full_name() == rest_of_reference:
                        referenced_enum = enum
                        break
                if referenced_enum:
                    self.debug_print(f"DEBUG: Resolved enum reference '{reference}' to imported standalone enum '{referenced_enum.get_full_name()}'")
                    return referenced_enum
                else:
                    self.debug_print(f"DEBUG: Standalone enum '{rest_of_reference}' not found in imported model.")
        else:
            full_name = reference
            self.debug_print(f"DEBUG: Resolving enum reference '{reference}' as namespaced standalone enum in current model")
            referenced_enum = self.model.get_enum(full_name)
            self.debug_print(f"DEBUG: Result of self.model.get_enum('{full_name}'): {referenced_enum}")
            if referenced_enum:
                self.debug_print(f"DEBUG: Resolved enum reference '{reference}' to namespaced standalone enum '{referenced_enum.get_full_name()}'")
                return referenced_enum
            else:
                self.debug_print(f"DEBUG: Namespaced standalone enum '{full_name}' not found in current model.")
    elif '.' in reference:
        parts = reference.split('.', 1)
        message_name = parts[0].strip()  # <-- Strip whitespace
        inline_enum_name = parts[1].strip()  # <-- Strip whitespace
        inline_enum_lookup_name = f"{inline_enum_name}_Enum"
        self.debug_print(f"DEBUG: Resolving inline enum '{inline_enum_name}' within message '{message_name}' in current model")
        referenced_message = self.model.get_message(message_name)
        self.debug_print(f"DEBUG: Result of self.model.get_message('{message_name}'): {referenced_message}")
        if referenced_message:
            self.debug_print(f"DEBUG: Found referenced message '{referenced_message.get_full_name()}'. Checking inline enums. Looking for '{inline_enum_lookup_name}'. Available inline enums: {list(referenced_message.inline_enums.keys())}")
            if inline_enum_lookup_name in referenced_message.inline_enums:
                self.debug_print(f"DEBUG: Resolved enum reference '{reference}' to inline enum '{referenced_message.inline_enums[inline_enum_lookup_name].get_full_name()}'")
                return referenced_message.inline_enums[inline_enum_lookup_name]
            else:
                self.debug_print(f"DEBUG: Inline enum '{inline_enum_lookup_name}' not found in message '{referenced_message.get_full_name()}'.")
        else:
            self.debug_print(f"DEBUG: Message '{message_name}' not found in current model.")
    else:
        self.debug_print(f"DEBUG: Resolving standalone enum '{reference}' in current model")
        referenced_enum = self.model.get_enum(reference)
        self.debug_print(f"DEBUG: Result of self.model.get_enum('{reference}'): {referenced_enum}")
        if referenced_enum:
            self.debug_print(f"DEBUG: Resolved enum reference '{reference}' to standalone enum '{referenced_enum.get_full_name()}'")
            return referenced_enum
        else:
            self.debug_print(f"DEBUG: Standalone enum '{reference}' not found in current model.")
    self.debug_print(f"DEBUG: Enum reference '{reference}' not resolved.")
    return None

def _resolve_compound_reference(self, reference: str) -> Optional[Any]:
    message = _resolve_message_reference(self, reference)
    if message:
        return message
    enum = _resolve_enum_reference(self, reference)
    if enum:
        return enum
    return None
