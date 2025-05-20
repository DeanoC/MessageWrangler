"""
Base generator for C++ code from the intermediate representation.
"""

import os
from typing import TextIO, Dict, List, Optional, Any
from io import StringIO

from message_model import (
    MessageModel,
    Message,
    Field,
    FieldType,
    EnumValue,
    Enum
)


class BaseCppGenerator:
    """
    Base generator for C++ code from the intermediate representation.
    """

    def __init__(self, model: MessageModel, output_dir: str, output_name: str = None):
        """
        Initialize the generator with the message model and output directory.

        Args:
            model: The message model to generate code from
            output_dir: Directory where output files will be generated
            output_name: Base name for output files without extension (default: "Messages")
        """
        self.model = model
        self.output_dir = output_dir
        self.output_name = output_name if output_name else "Messages"

    def _write_namespace_start(self, f: TextIO) -> None:
        """
        Write the start of the namespace.

        Args:
            f: The file to write to
        """
        f.write(f"namespace {self.output_name} {{\n\n")

        # We don't write nested namespaces here anymore
        # They will be written as needed when writing structs and enums


    def _write_namespace_end(self, f: TextIO) -> None:
        """
        Write the end of the namespace.

        Args:
            f: The file to write to
        """
        # We don't close nested namespaces here anymore
        # They will be closed as needed when writing structs and enums

        f.write(f"}} // namespace {self.output_name}\n")


    def _write_forward_declarations(self, f: TextIO, model: MessageModel = None) -> None:
        """
        Write forward declarations for all structs.

        Args:
            f: The file to write to
            model: Optional message model to use (defaults to self.model)
        """
        if model is None:
            model = self.model

        # Group messages by namespace
        global_messages = []
        namespaced_messages = {}

        for message_name, message in model.messages.items():
            if message.namespace:
                if message.namespace not in namespaced_messages:
                    namespaced_messages[message.namespace] = []
                namespaced_messages[message.namespace].append(message.name)
            else:
                global_messages.append(message.name)

        # Write forward declarations for global messages
        for message_name in global_messages:
            f.write(f"    struct {message_name};\n")

        # Write forward declarations for namespaced messages
        for namespace_name, messages in namespaced_messages.items():
            f.write(f"    namespace {namespace_name} {{\n")
            for message_name in messages:
                f.write(f"        struct {message_name};\n")
            f.write(f"    }} // namespace {namespace_name}\n")

        f.write("\n")