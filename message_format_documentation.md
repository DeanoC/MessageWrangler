# Message Format Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Current Message Format](#current-message-format)
   - [File Format Syntax](#file-format-syntax)
   - [Message Definitions](#message-definitions)
   - [Field Types](#field-types)
   - [Inheritance](#inheritance)
   - [Enum Definitions](#enum-definitions)
   - [Options Definitions](#options-definitions)
   - [Compound Fields](#compound-fields)
   - [Optional Fields](#optional-fields)
   - [Default Values](#default-values)
   - [Comments](#comments)
   - [Namespaces](#namespaces)
   - [Complete Example](#complete-example)
3. [Code Generation Process](#code-generation-process)
   - [Output Naming](#output-naming)
   - [C++ Code Generation](#c-code-generation)
   - [TypeScript Code Generation](#typescript-code-generation)
   - [Python Code Generation](#python-code-generation)
   - [JSON Schema Generation](#json-schema-generation)
   - [Type Mappings](#type-mappings)
4. [Future Extensions](#future-extensions)
   - [Additional Data Types](#additional-data-types)
   - [Versioning Support](#versioning-support)
   - [Validation Rules](#validation-rules)
   - [Arrays and Collections](#arrays-and-collections)
   - [Additional Language Support](#additional-language-support)
   - [Binary Format Support](#binary-format-support)
   - [Enum References](#enum-references)
   - [Import Commands](#import-commands)

## Introduction

This document describes the message format used for communication between an Electron application and Unreal Engine 5 over WebSocket. The system uses a single source file (.def) to define messages that are then converted into C++ (for Unreal Engine), TypeScript (for Electron), Python, and JSON schema formats.

The message format converter is implemented in Python and can be found in `message_wrangler.py`. It processes a .def file and generates the corresponding C++, TypeScript, Python, and JSON schema code.

## Current Message Format

### File Format Syntax

The message definition file (.def) uses a simple, human-readable syntax:

```
message MessageName {
    field fieldName: fieldType
    field enumField: enum { Value1, Value2, Value3 }
    field compoundField: baseType { component1, component2, component3 }
}

message DerivedMessage : BaseMessage {
    field additionalField: fieldType
}
```

#### Multiple Line Support

The parser supports multi-line definitions for enums, compounds, and fields. This makes the message definition files more readable and easier to maintain, especially for complex structures.

Examples:
```
// Multi-line enum definition
field status: enum { 
    Success, 
    Failure, 
    Pending,
    InProgress,
    Cancelled
};

// Multi-line compound definition
field position: float { 
    x, 
    y, 
    z 
};

// Multi-line field definition
field name: string
;
```

### Message Definitions

Messages are defined using the `message` keyword followed by the message name and a block of field definitions enclosed in curly braces. Each message represents a structure or interface that can be sent between the Electron application and Unreal Engine.

Example:
```
message ToolToUnrealCmd {
    field command: enum { Ping, Position }
    field verb: string
    field actor: string
}
```

### Field Types

The current implementation supports the following field types:

- **Basic Types**:
  - `string`: Represents a text string (maps to FString in C++ and string in TypeScript)
  - `int`: Represents an integer number (maps to int32 in C++ and number in TypeScript)
  - `float`: Represents a floating-point number (maps to float in C++ and number in TypeScript)
  - `bool`: Represents a boolean value (true/false) (maps to bool in C++ and boolean in TypeScript)
  - `byte`: Represents an 8-bit unsigned integer (maps to uint8 in C++ and number in TypeScript)

- **Complex Types**:
  - `enum`: Represents an enumeration of predefined values
  - `options`: Represents a set of bit flags that can be combined (maps to uint32 in C++ and number in TypeScript)
  - Compound types: Represents a structure with multiple components

- **Field Modifiers**:
  - `optional`: Indicates that a field is optional and can be omitted
  - `default(value)`: Specifies a default value for a field

### Inheritance

Messages can inherit from other messages using the colon syntax:

```
message DerivedMessage : BaseMessage {
    // Additional fields
}
```

Inheritance allows a derived message to include all fields from the base message, plus any additional fields defined in the derived message.

Example:
```
message UnrealToToolCmdUpdateReply : UnrealToToolCmdReply {
    field position: float { x, y, z }
}
```

### Enum Definitions

Enumerations are defined inline within field definitions using the `enum` keyword followed by a list of values enclosed in curly braces:

```
field enumField: enum { Value1, Value2, Value3 }
```

Each enum value is automatically assigned a numeric value starting from 0.

Example:
```
field command: enum { Ping, Position }
```

In this example, `Ping` has a value of 0, and `Position` has a value of 1.

### Options Definitions

Options are similar to enums but are designed to be used as bit flags that can be combined. They are defined using the `options` keyword followed by a list of option values enclosed in curly braces:

```
field optionsField: options { Option1, Option2, Option3 }
```

Each option value is automatically assigned a power-of-two bit value (1, 2, 4, 8, etc.), allowing them to be combined using bitwise operations.

Example:
```
field permissions: options { Read, Write, Execute }
```

In this example, `Read` has a value of 1, `Write` has a value of 2, and `Execute` has a value of 4. These values can be combined using the bitwise OR operator (`|`) to represent multiple options:

```
field permissions: options { Read, Write, Execute } default(Read | Execute)
```

This sets the default value to the combination of `Read` and `Execute` (1 | 4 = 5).

### Compound Fields

Compound fields are defined using a base type followed by a list of components enclosed in curly braces:

```
field compoundField: baseType { component1, component2, component3 }
```

Currently, the only supported base type for compound fields is `float`.

Example:
```
field position: float { x, y, z }
```

This defines a compound field named `position` with three float components: `x`, `y`, and `z`.

### Optional Fields

Fields can be marked as optional, indicating that they can be omitted from messages:

```
field description: string optional
field metadata: Metadata optional
```

Optional fields are handled differently in each output format:
- In C++: Documentation indicates the field is optional, and deserialization code doesn't fail if the field is missing
- In TypeScript: Fields are marked with a question mark (e.g., `description?: string;`)
- In JSON Schema: Optional fields are not included in the "required" array

### Default Values

Fields can have default values that are used when the field is not explicitly set:

```
field command: enum { Ping, Position } default(Ping)
field timeout: int default(30)
field enabled: bool default(true)
```

Default values are handled differently in each output format:
- In C++: Fields are initialized with the default value in the struct definition, and the default value is used when deserializing if the field is missing from the JSON
- In TypeScript: Default values are documented in the field comments using the @default JSDoc tag
- In JSON Schema: Default values are included in the schema using the "default" property

Note: If a field is both optional and has a default value, the default value is ignored, as optional fields are never assigned default values.

### Comments

#### User-Supplied Comments

Users can add comments in the message definition file to explain the intent and purpose of messages and fields using the `///` syntax. These comments are parsed and included in the generated code (C++, TypeScript, and JSON), providing more context and documentation beyond just the mechanical structure of the messages.

Example:
```
/// This message is sent from the tool to Unreal Engine to issue a command.
message ToolToUnrealCmd {
    /// The type of command to execute.
    field command: enum { Ping, Position }

    /// The verb describing the action to perform.
    field verb: string

    /// The actor on which to perform the action.
    field actor: string
}
```

These comments are preserved in all generated output formats and appear as documentation comments in the appropriate style for each language.

#### Local Comments

Users can add local comments in the message definition file using the `//` syntax. These comments are only for the .def file itself and are not propagated to the generated files.

Example:
```
// This is a local comment that will not appear in generated files
message ToolToUnrealCmd {
    // This comment is only for internal documentation
    field command: enum { Ping, Position }

    // This field is used for verb actions
    field verb: string
}
```

This feature allows developers to add notes, explanations, or reminders that are only relevant to those working directly with the message definition file, without cluttering the generated code.

### Namespaces

Messages can be organized into logical namespaces to group related messages together and avoid name collisions.

Example:
```
namespace Tool {
    message Command {
        field type: string
        field action: string
    }
}

namespace Unreal {
    message Response {
        field status: enum { Success, Failure }
        field message: string
    }
}
```

In the generated code:
- In C++, namespaces are translated to C++ namespaces within the namespace derived from the def file name
- In TypeScript, namespaces are translated to nested namespaces within the namespace derived from the def file name
- In JSON schema, namespaced messages use fully qualified names (namespace::message)

Messages can reference other messages across namespaces using their fully qualified names. For example, a message in the Tool namespace can inherit from a message in the Unreal namespace.

### Complete Example

Here's a complete example of a message definition file:

```
/// This message is sent from the tool to Unreal Engine to issue a command.
message ToolToUnrealCmd {
    /// The type of command to execute.
    field command: enum { Ping, Position }
    /// The verb describing the action to perform.
    field verb: string
    /// The actor on which to perform the action.
    field actor: string
}

/// This message is sent from Unreal Engine to the tool as a reply to a command.
message UnrealToToolCmdReply {
    /// The status of the command execution.
    field status: enum { OK, FAIL }
}

/// This message is sent from Unreal Engine to the tool as a reply to a command
/// that updates a position.
message UnrealToToolCmdUpdateReply : UnrealToToolCmdReply {
    /// The position in 3D space.
    field position: float { x, y, z }
}
```

This example defines three messages:
1. `ToolToUnrealCmd`: A command sent from the tool to Unreal Engine, with a command enum, a verb string, and an actor string.
2. `UnrealToToolCmdReply`: A reply from Unreal Engine to the tool, with a status enum.
3. `UnrealToToolCmdUpdateReply`: A specialized reply that inherits from `UnrealToToolCmdReply` and adds a position compound field with x, y, and z components.

## Code Generation Process

The message format converter processes the .def file and generates C++ and TypeScript code that can be used by Unreal Engine and the Electron application, respectively.

### Output Naming

The message format converter allows you to specify the name of the output files without extension. The converter will add appropriate extensions and prefixes based on the output format:

- For C++ output:
  - Unreal Engine C++ files are prefixed with `ue_` and have a `_msgs.h` extension
  - Standard C++ files are prefixed with `c_` and have a `_msgs.h` extension
- For TypeScript output:
  - Files have a `_msgs.ts` extension
- For Python output:
  - Files have a `_msgs.py` extension
- For JSON schema output:
  - Files have a `_msgs_schema.json` extension

If no output name is specified, the converter will use the name of the input file (without the `.def` extension) as the base name for the output files.

#### Handling of Imported Definitions

When using import statements, the converter generates separate files for each imported definition file:

1. The main file (the one being processed) generates output files with the specified output name
2. Each imported file generates output files with the base name of the imported file
3. The generated files include appropriate import statements to reference the imported definitions

For example, if `main.def` imports `base.def`, the converter will generate:
- `main_msgs.h` and `base_msgs.h` for C++
- `main_msgs.ts` and `base_msgs.ts` for TypeScript
- `main_msgs.py` and `base_msgs.py` for Python
- A single `main_msgs_schema.json` for JSON schema that includes all definitions

### C++ Code Generation

For C++, the converter generates a header file (e.g., `example_msgs.h`) with the following structure:

1. **Namespace**: All generated code is enclosed in a namespace derived from the def file name. For imported files, each file gets its own namespace based on the file name.
2. **Enum Definitions**: Each enum field is converted to a C++ enum class with the format `MessageName_fieldName_Enum`.
3. **Forward Declarations**: All message structs are forward-declared.
4. **Struct Definitions**: Each message is converted to a C++ struct with the appropriate fields.
5. **Inheritance**: Inheritance relationships are preserved using C++ inheritance with the `public` keyword.
6. **Compound Fields**: Compound fields are implemented as nested anonymous structs.
7. **Includes**: For imported files, appropriate #include statements are added to reference the imported definitions.

Example C++ output:
```cpp
// Auto-generated message definitions for C++
#pragma once

#include "CoreMinimal.h"

namespace ExampleMessages {

    // Enum for ToolToUnrealCmd.command
    enum class ToolToUnrealCmd_command_Enum : uint8
    {
        Ping = 0,
        Position = 1,
    };

    // Enum for UnrealToToolCmdReply.status
    enum class UnrealToToolCmdReply_status_Enum : uint8
    {
        OK = 0,
        FAIL = 1,
    };

    struct ToolToUnrealCmd;
    struct UnrealToToolCmdReply;
    struct UnrealToToolCmdUpdateReply;

    // ToolToUnrealCmd message
    struct ToolToUnrealCmd
    {
        ToolToUnrealCmd_command_Enum command;
        FString verb;
        FString actor;
    };

    // UnrealToToolCmdReply message
    struct UnrealToToolCmdReply
    {
        UnrealToToolCmdReply_status_Enum status;
    };

    // UnrealToToolCmdUpdateReply message
    struct UnrealToToolCmdUpdateReply : public UnrealToToolCmdReply
    {
        struct {
            float x;
            float y;
            float z;
        } position;
    };

} // namespace ExampleMessages
```

### TypeScript Code Generation

For TypeScript, the converter generates a file (e.g., `example_msgs.ts`) with the following structure:

1. **Exports**: All generated code is exported directly using ES2015 module syntax.
2. **Enum Definitions**: Each enum field is converted to a TypeScript enum with the format `MessageName_fieldName_Enum`.
3. **Interface Definitions**: Each message is converted to a TypeScript interface with the appropriate fields.
4. **Inheritance**: Inheritance relationships are preserved using TypeScript interface extension.
5. **Compound Fields**: Compound fields are implemented as nested object types.
6. **Imports**: For imported files, appropriate import statements are added to reference the imported definitions.
7. **Type Guards**: Type guard functions are generated for each message type to enable runtime type checking.

Example TypeScript output:
```typescript
// Auto-generated message definitions for TypeScript

export namespace ExampleMessages {

    // Enum for ToolToUnrealCmd.command
    export enum ToolToUnrealCmd_command_Enum {
        Ping = 0,
        Position = 1,
    }

    // Enum for UnrealToToolCmdReply.status
    export enum UnrealToToolCmdReply_status_Enum {
        OK = 0,
        FAIL = 1,
    }

    // ToolToUnrealCmd message
    export interface ToolToUnrealCmd {
        command: ToolToUnrealCmd_command_Enum;
        verb: string;
        actor: string;
    }

    // UnrealToToolCmdReply message
    export interface UnrealToToolCmdReply {
        status: UnrealToToolCmdReply_status_Enum;
    }

    // UnrealToToolCmdUpdateReply message
    export interface UnrealToToolCmdUpdateReply extends UnrealToToolCmdReply {
        position: {
            x: number;
            y: number;
            z: number;
        };
    }

} // namespace ExampleMessages
```

### Python Code Generation

For Python, the converter generates a file (e.g., `example_msgs.py`) with the following structure:

1. **Imports**: The file includes necessary imports like dataclasses, Enum, and typing.
2. **Enum Definitions**: Each enum field is converted to a Python Enum class with the format `MessageNameFieldNameEnum`.
3. **Compound Field Classes**: Compound fields are implemented as dataclasses with the format `MessageNameFieldNameCompound`.
4. **Message Classes**: Each message is converted to a Python dataclass with the appropriate fields.
5. **Inheritance**: Inheritance relationships are preserved using Python class inheritance.
6. **Serialization Methods**: Each message class includes `to_dict` and `from_dict` methods for serialization and deserialization.
7. **Utility Class**: A `MessageSerialization` class provides utility functions for working with messages.
8. **Imports for Inherited Messages**: For imported files, appropriate import statements are added to reference the imported definitions.
9. **Separate Files for Imported Definitions**: Each imported file generates its own Python file, with classes named according to the message names in that file.

Example Python output:
```python
# Auto-generated message definitions for Python

import json
import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Type, cast

class TooltounrealcmdCommandEnum(Enum):
    """Enum for ToolToUnrealCmd.command"""
    Ping = 0
    Position = 1

class UnrealtotoolcmdreplyStatusEnum(Enum):
    """Enum for UnrealToToolCmdReply.status"""
    OK = 0
    FAIL = 1

@dataclass
class UnrealtotoolcmdupdatereplyPositionCompound:
    """Compound type for UnrealToToolCmdUpdateReply.position"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

@dataclass
class Tooltounrealcmd:
    """ToolToUnrealCmd message"""
    command: TooltounrealcmdCommandEnum = TooltounrealcmdCommandEnum.Ping
    verb: str = ""
    actor: str = ""

    def to_dict(self) -> dict:
        """Convert this message to a dictionary."""
        result = {
            "command": self.command.value,
            "verb": self.verb,
            "actor": self.actor,
        }
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Tooltounrealcmd":
        """Create a message instance from a dictionary."""
        instance = cls()
        if "command" in data:
            instance.command = TooltounrealcmdCommandEnum(data["command"])
        if "verb" in data:
            instance.verb = data["verb"]
        if "actor" in data:
            instance.actor = data["actor"]
        return cast("Tooltounrealcmd", instance)

@dataclass
class Unrealtotoolcmdreply:
    """UnrealToToolCmdReply message"""
    status: UnrealtotoolcmdreplyStatusEnum = UnrealtotoolcmdreplyStatusEnum.OK

    def to_dict(self) -> dict:
        """Convert this message to a dictionary."""
        result = {
            "status": self.status.value,
        }
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Unrealtotoolcmdreply":
        """Create a message instance from a dictionary."""
        instance = cls()
        if "status" in data:
            instance.status = UnrealtotoolcmdreplyStatusEnum(data["status"])
        return cast("Unrealtotoolcmdreply", instance)

@dataclass
class Unrealtotoolcmdupdatereply(Unrealtotoolcmdreply):
    """UnrealToToolCmdUpdateReply message"""
    position: UnrealtotoolcmdupdatereplyPositionCompound = field(default_factory=UnrealtotoolcmdupdatereplyPositionCompound)

    def to_dict(self) -> dict:
        """Convert this message to a dictionary."""
        parent_dict = super().to_dict()
        result = {
            "position": dataclasses.asdict(self.position),
        }
        result.update(parent_dict)
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Unrealtotoolcmdupdatereply":
        """Create a message instance from a dictionary."""
        instance = Unrealtotoolcmdreply.from_dict(data)
        instance.__class__ = cls
        if "position" in data:
            compound_data = data["position"]
            instance.position = UnrealtotoolcmdupdatereplyPositionCompound()
            if "x" in compound_data:
                instance.position.x = compound_data["x"]
            if "y" in compound_data:
                instance.position.y = compound_data["y"]
            if "z" in compound_data:
                instance.position.z = compound_data["z"]
        return cast("Unrealtotoolcmdupdatereply", instance)

# Message serialization utilities
class MessageSerialization:
    """Utility class for message serialization and deserialization."""

    @staticmethod
    def serialize(message_type: str, payload: Any) -> str:
        """Serialize a message to a JSON string with message type."""
        if hasattr(payload, 'to_dict'):
            payload_dict = payload.to_dict()
        else:
            try:
                payload_dict = dataclasses.asdict(payload)
            except TypeError:
                payload_dict = payload

        envelope = {"messageType": message_type, "payload": payload_dict}
        return json.dumps(envelope)
```

### JSON Schema Generation

For JSON schema, the converter generates a file (e.g., `example_msgs_schema.json`) with the following structure:

1. **Schema Definition**: The file includes standard JSON schema metadata like $schema, title, and description.
2. **Definitions**: Each message is defined as a JSON schema object under the "definitions" property.
3. **Properties**: Each field in a message is defined as a property with appropriate type and description.
4. **Inheritance**: Inheritance relationships are preserved using the "allOf" keyword with a reference to the parent schema.
5. **Enums**: Enum fields include both the numeric values and the corresponding names.
6. **Compound Fields**: Compound fields are implemented as nested object schemas with their own properties.
7. **Namespaces**: Messages from imported files are included in the same schema file, with fully qualified names that include their namespace.
8. **Single File**: Unlike the other generators, JSON schema generation produces a single file that includes all definitions, including those from imported files.

Example JSON schema output:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Message Definitions",
  "description": "JSON schema for message definitions",
  "definitions": {
    "ToolToUnrealCmd": {
      "type": "object",
      "description": "ToolToUnrealCmd message",
      "properties": {
        "command": {
          "description": "command enum field",
          "type": "integer",
          "enum": [0, 1],
          "enumNames": ["Ping", "Position"]
        },
        "verb": {
          "description": "verb field",
          "type": "string"
        },
        "actor": {
          "description": "actor field",
          "type": "string"
        }
      },
      "required": ["command", "verb", "actor"]
    },
    "UnrealToToolCmdReply": {
      "type": "object",
      "description": "UnrealToToolCmdReply message",
      "properties": {
        "status": {
          "description": "status enum field",
          "type": "integer",
          "enum": [0, 1],
          "enumNames": ["OK", "FAIL"]
        }
      },
      "required": ["status"]
    },
    "UnrealToToolCmdUpdateReply": {
      "type": "object",
      "description": "UnrealToToolCmdUpdateReply message",
      "properties": {
        "position": {
          "description": "position compound field",
          "type": "object",
          "properties": {
            "x": {
              "type": "number",
              "description": "x component"
            },
            "y": {
              "type": "number",
              "description": "y component"
            },
            "z": {
              "type": "number",
              "description": "z component"
            }
          },
          "required": ["x", "y", "z"]
        }
      },
      "required": ["position"],
      "allOf": [
        {
          "$ref": "#/definitions/UnrealToToolCmdReply"
        }
      ]
    }
  }
}
```

### Type Mappings

The following table shows how types are mapped between the .def file, C++, TypeScript, Python, and JSON Schema:

| .def Type | C++ Type | TypeScript Type | Python Type | JSON Schema Type |
|-----------|----------|----------------|------------|----------------|
| string    | FString  | string         | str        | string         |
| int       | int32    | number         | int        | integer        |
| float     | float    | number         | float      | number         |
| bool      | bool     | boolean        | bool       | boolean        |
| byte      | uint8    | number         | int        | integer (0-255) |
| enum      | enum class | enum         | Enum       | integer + enum |
| options   | uint32   | number         | IntFlag    | integer + options |
| compound  | struct   | object         | dataclass  | object         |

## Current Feature Set

The message format system currently supports a rich set of features that enable the definition of complex message structures for communication between systems. Below is a summary of the current feature set:

### Core Features

- **Message Definitions**: Define structured messages with fields of various types
- **Field Types**: Support for basic types (string, int, float, bool, byte), enums, options, and compound fields
- **Inheritance**: Messages can inherit from other messages to extend their functionality
- **Namespaces**: Messages can be organized into logical namespaces
- **Optional Fields**: Fields can be marked as optional, allowing them to be omitted
- **Default Values**: Fields can have default values that are used when not explicitly set
- **Comments**: Support for user-supplied documentation comments
- **Multi-line Support**: Parser supports multi-line definitions for better readability

### Code Generation

- **Multiple Language Support**: Generate code for TypeScript, C++ (both standard and Unreal Engine), and Python
- **JSON Schema Generation**: Generate JSON schema for message validation
- **Self-documenting Headers**: Generated code includes comprehensive documentation
- **Serialization Utilities**: Generated code includes utilities for serialization and deserialization
- **Type Guards**: TypeScript code includes type guard functions for runtime type checking
- **Default Value Handling**: Generated code properly handles default values
- **Python Dataclasses**: Python code uses dataclasses for clean, type-annotated message definitions

## Future Extensions

While the current message format system is already feature-rich, there are still some potential extensions that could be added in the future. Below is a prioritized todo list of future extensions, ordered by a combination of implementation complexity and user value:

### Todo List

- [ ] **Additional Data Types**
  - [ ] Double: Add support for double-precision floating-point numbers
  - [ ] Int64: Add support for 64-bit integers
  - [ ] Vector2D/Vector3D/Vector4D: Add dedicated types for 2D, 3D, and 4D vectors
  - [ ] Color: Add support for color values (RGBA)
  - [ ] Quaternion: Add support for quaternions (for rotations)
  - [ ] Matrix: Add support for transformation matrices
  - [ ] UUID: Add support for universally unique identifiers
  - [ ] DateTime: Add support for date and time values

- [ ] **Arrays and Collections**
  ```
  field tags: string[]
  field points: Vector3D[]
  field properties: Map<string, string>
  ```
  This would allow messages to contain collections of values.

- [ ] **Validation Rules**
  ```
  field age: int min(0) max(120)
  field email: string regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
  field name: string minLength(1) maxLength(100)
  ```
  This would allow the system to validate message fields before sending or after receiving, ensuring data integrity.

- [ ] **Additional Language Support**
  - [ ] C#: For Unity or .NET applications
  - [ ] Java/Kotlin: For Android applications
  - [ ] Swift: For iOS applications
  - [ ] Rust: For high-performance applications

- [ ] **Versioning Support**
  ```
  message ToolToUnrealCmd version 2 {
      // Fields
  }
  ```
  This would allow the system to handle different versions of the same message, making it easier to evolve the protocol over time.

- [ ] **Binary Format Support**
  ```
  python script.py --input messages.def --output ./generated --binary-format protobuf
  ```
  This would generate code for efficient binary serialization and deserialization.

- [ ] **Enum References**
  ```
  field mode: ChangeMode.Mode
  ```
  This would allow fields to reference enum types defined in other messages, enabling better code organization and reuse of enum definitions. Currently, referencing enums from other messages is not supported and will generate an error.

- [ ] **Message References**
  ```
  field baseMessage: Base::BaseMessage
  ```
  This would allow fields to reference message types defined in other namespaces. Currently, using a message directly as a field type is not supported and will generate an error. Message inheritance should be used instead to achieve similar functionality.

- [x] **Enum numbering**
  ```
  field baseMessage: enum { Zero = 1, Ten = 11, Eleven, Thousand = 1000 }
  ```
  This allows enum to take specific values and auto-increment from the last defined value. Enum values can be explicitly assigned (e.g., `Zero = 1`) or auto-incremented from the last defined value (e.g., `Eleven` after `Ten = 11` would be 12). If no explicit value is assigned to the first enum value, it starts from 0.

- [x] **Import Commands**
  ```
  import "./path.def" as Base
  ```
  or
  ```
  import "./path.def"
  ```
  This allows including external .def files within the current file. When the "as" parameter is provided, the imported definitions are wrapped in the specified namespace. When the "as" parameter is omitted, the imported definitions are included directly in the current file without a namespace, as if they were defined in the current file. This enables:
  - Code reuse across multiple message definition files
  - Creation of message libraries that can be shared between projects
  - Better organization of large message definition sets

  The system generates errors in the following cases:
  - When the specified file cannot be found at the given path
  - When the namespace (provided or derived) is a reserved keyword
  - When circular imports are detected

  The file path can be relative to the current file or absolute, allowing for flexible project structures.

  Example usage with namespace:
  ```
  // In base.def
  message BaseMessage {
      field baseField: string
  }

  // In main.def
  import "./base.def" as Base

  message MainMessage : Base::BaseMessage {
      field mainField: string
  }
  ```

  In this example, the `BaseMessage` from `base.def` is imported into `main.def` with the namespace `Base`. The `MainMessage` then inherits from `Base::BaseMessage`, gaining access to its fields.

  Example usage without namespace:
  ```
  // In base.def
  message BaseMessage {
      field baseField: string
  }

  // In main.def
  import "./base.def"

  message MainMessage : BaseMessage {
      field mainField: string
  }
  ```

  In this example, the `BaseMessage` from `base.def` is imported directly into `main.def` without a namespace. The `MainMessage` can inherit from `BaseMessage` directly, without needing to use a namespace prefix.

This document provides a comprehensive overview of the current message format and potential future extensions. The current implementation is a solid foundation that can be extended in various ways to meet evolving requirements.
