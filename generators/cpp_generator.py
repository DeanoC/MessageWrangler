# cpp_generator.py
"""
Base/shared logic for C++ code generation for MessageWrangler message definitions.
This class is intended to be subclassed by specific C++ standard variants (e.g., C++23).
"""

from typing import List, Dict, Any

CPP_RESERVED_KEYWORDS = {
    # Standard C++ keywords
    "alignas", "alignof", "and", "and_eq", "asm", "atomic_cancel", "atomic_commit",
    "atomic_noexcept", "auto", "bitand", "bitor", "bool", "break", "case", "catch",
    "char", "char8_t", "char16_t", "char32_t", "class", "compl", "concept", "const",
    "consteval", "constexpr", "constinit", "const_cast", "continue", "co_await",
    "co_return", "co_yield", "decltype", "default", "delete", "do", "double",
    "dynamic_cast", "else", "enum", "explicit", "export", "extern", "false", "float",
    "for", "friend", "goto", "if", "inline", "int", "long", "mutable", "namespace",
    "new", "noexcept", "not", "not_eq", "nullptr", "operator", "or", "or_eq",
    "private", "protected", "public", "reflexpr", "register", "reinterpret_cast",
    "requires", "return", "short", "signed", "sizeof", "static", "static_assert",
    "static_cast", "struct", "switch", "synchronized", "template", "this",
    "thread_local", "throw", "true", "try", "typedef", "typeid", "typename", "union",
    "unsigned", "using", "virtual", "void", "volatile", "wchar_t", "while", "xor",
    "xor_eq",
    # Common library names that might be problematic if used as identifiers directly
    # "std", "string", "vector", "map", "optional", "variant", "chrono", "thread", "mutex"
    # Adding common ones that might appear in DSLs as type names
    "main", "override", "final", "module" # module is C++20, import/export too
}

class CppGeneratorBase:
    def __init__(self, namespaces: List[Any], options: Dict[str, Any] = None):
        self.namespaces = namespaces
        self.options = options or {}
    def generate_header(self) -> Dict[str, str]:
        """
        Generate C++ header files for all namespaces.
        Returns a dict mapping filename to file content.
        """
        raise NotImplementedError("Subclasses must implement generate_header()")

    def generate_source(self) -> Dict[str, str]:
        """
        Generate C++ source files for all namespaces.
        Returns a dict mapping filename to file content.
        """
        raise NotImplementedError("Subclasses must implement generate_source()")

    # Shared utility methods for all C++ generators can be added here
    def _sanitize_identifier(self, name: str, for_namespace: bool = False) -> str:
        """
        Sanitizes a name to be a valid C++ identifier.
        Replaces problematic characters and prefixes reserved keywords.
        """
        import re
        sanitized = str(name)

        # Replace common problematic characters. For namespaces, '::' is preserved by splitting and rejoining.
        # For other identifiers, '::' is typically flattened.
        if not for_namespace:
            sanitized = sanitized.replace('::', '_')
        sanitized = sanitized.replace('-', '_').replace('.', '_')

        if sanitized in CPP_RESERVED_KEYWORDS:
            sanitized = f"mw_{sanitized}" # "mw_" for "MessageWrangler" prefix

        # Ensure it starts with a letter or underscore, and contains only valid characters.
        # This is a basic check; more complex validation might be needed for edge cases.
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", sanitized.split('::')[-1]): # Check last part for qualified names
            sanitized = f"mw_{sanitized}"
            # Re-clean after prefixing, in case the prefix itself created an issue (unlikely with "mw_")
            if not for_namespace:
                sanitized = sanitized.replace('::', '_')
            sanitized = sanitized.replace('-', '_').replace('.', '_')
        return sanitized

    def _cpp_type_mapping(self, type_name: str) -> dict[str, str]:
        return {
            'int': 'int32_t',
            'uint': 'uint32_t',
            'int8': 'int8_t',
            'uint8': 'uint8_t',
            'int16': 'int16_t',
            'uint16': 'uint16_t',
            'int32': 'int32_t',
            'uint32': 'uint32_t',
            'int64': 'int64_t',
            'uint64': 'uint64_t',
            'float': 'float',
            'double': 'double',
            'bool': 'bool',
            'string': 'std::string',
        }.get(type_name, 'unknown_type')

    def _cpp_type(self, field) -> str:
        # Shared C++14+ type mapping for basic types; override for advanced/variant types
        # This assumes field has a 'type' attribute (str) and 'is_array' (bool)
        base_type = getattr(field, 'type', 'unknown_type')
        cpp_type = self._cpp_type_mapping(base_type)
        if getattr(field, 'is_array', False):
            return f'{cpp_type}'
        return cpp_type

    def _namespace_prefix(self, ns) -> str:
        # Returns the C++ namespace prefix for a given namespace object
        return ns.name + '::' if hasattr(ns, 'name') else ''

    def _default_value(self, field) -> str:
        # Shared logic for C++ default value expressions (C++14+)
        if hasattr(field, 'default'):
            if isinstance(field.default, str):
                return f'"{field.default}"' if getattr(field, 'type', 'unknown_type') == 'string' else str(field.default)
            return str(field.default)
        return ''

    # ... more shared helpers as needed
