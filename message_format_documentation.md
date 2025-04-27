# Message Format Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Current Message Format](#current-message-format)
   - [File Format Syntax](#file-format-syntax)
   - [Message Definitions](#message-definitions)
   - [Field Types](#field-types)
   - [Inheritance](#inheritance)
   - [Enum Definitions](#enum-definitions)
   - [Compound Fields](#compound-fields)
   - [Complete Example](#complete-example)
3. [Code Generation Process](#code-generation-process)
   - [C++ Code Generation](#c-code-generation)
   - [TypeScript Code Generation](#typescript-code-generation)
   - [JSON Schema Generation](#json-schema-generation)
   - [Type Mappings](#type-mappings)
4. [Future Extensions](#future-extensions)
   - [Additional Data Types](#additional-data-types)
   - [Versioning Support](#versioning-support)
   - [Validation Rules](#validation-rules)
   - [Default Values](#default-values)
   - [Optional Fields](#optional-fields)
   - [Arrays and Collections](#arrays-and-collections)
   - [Documentation Comments](#documentation-comments)
   - [Namespaces and Modules](#namespaces-and-modules)
   - [Additional Language Support](#additional-language-support)
   - [Schema Validation](#schema-validation)
   - [Binary Format Support](#binary-format-support)
   - [Message Serialization/Deserialization](#message-serialization-deserialization)

## Introduction

This document describes the message format used for communication between an Electron application and Unreal Engine 5 over WebSocket. The system uses a single source file (.def) to define messages that are then converted into C++ (for Unreal Engine), TypeScript (for Electron), and JSON schema formats.

The message format converter is implemented in Python and can be found in `message_wrangler.py`. It processes a .def file and generates the corresponding C++, TypeScript, and JSON schema code.

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

- **Complex Types**:
  - `enum`: Represents an enumeration of predefined values
  - Compound types: Represents a structure with multiple components

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

### Complete Example

Here's a complete example of a message definition file:

```
message ToolToUnrealCmd {
    field command: enum { Ping, Position }
    field verb: string
    field actor: string
}

message UnrealToToolCmdReply {
    field status: enum { OK, FAIL }
}

message UnrealToToolCmdUpdateReply : UnrealToToolCmdReply {
    field position: float { x, y, z }
}
```

This example defines three messages:
1. `ToolToUnrealCmd`: A command sent from the tool to Unreal Engine, with a command enum, a verb string, and an actor string.
2. `UnrealToToolCmdReply`: A reply from Unreal Engine to the tool, with a status enum.
3. `UnrealToToolCmdUpdateReply`: A specialized reply that inherits from `UnrealToToolCmdReply` and adds a position compound field with x, y, and z components.

## Code Generation Process

The message format converter processes the .def file and generates C++ and TypeScript code that can be used by Unreal Engine and the Electron application, respectively.

### C++ Code Generation

For C++, the converter generates a header file (`Messages.h`) with the following structure:

1. **Namespace**: All generated code is enclosed in a `Messages` namespace.
2. **Enum Definitions**: Each enum field is converted to a C++ enum class with the format `MessageName_fieldName_Enum`.
3. **Forward Declarations**: All message structs are forward-declared.
4. **Struct Definitions**: Each message is converted to a C++ struct with the appropriate fields.
5. **Inheritance**: Inheritance relationships are preserved using C++ inheritance with the `public` keyword.
6. **Compound Fields**: Compound fields are implemented as nested anonymous structs.

Example C++ output:
```cpp
// Auto-generated message definitions for C++
#pragma once

#include "CoreMinimal.h"

namespace Messages {

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

} // namespace Messages
```

### TypeScript Code Generation

For TypeScript, the converter generates a file (`messages.ts`) with the following structure:

1. **Namespace**: All generated code is enclosed in an exported `Messages` namespace.
2. **Enum Definitions**: Each enum field is converted to a TypeScript enum with the format `MessageName_fieldName_Enum`.
3. **Interface Definitions**: Each message is converted to a TypeScript interface with the appropriate fields.
4. **Inheritance**: Inheritance relationships are preserved using TypeScript interface extension.
5. **Compound Fields**: Compound fields are implemented as nested object types.

Example TypeScript output:
```typescript
// Auto-generated message definitions for TypeScript

export namespace Messages {

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

} // namespace Messages
```

### JSON Schema Generation

For JSON schema, the converter generates a file (`messages.json`) with the following structure:

1. **Schema Definition**: The file includes standard JSON schema metadata like $schema, title, and description.
2. **Definitions**: Each message is defined as a JSON schema object under the "definitions" property.
3. **Properties**: Each field in a message is defined as a property with appropriate type and description.
4. **Inheritance**: Inheritance relationships are preserved using the "allOf" keyword with a reference to the parent schema.
5. **Enums**: Enum fields include both the numeric values and the corresponding names.
6. **Compound Fields**: Compound fields are implemented as nested object schemas with their own properties.

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

The following table shows how types are mapped between the .def file, C++, and TypeScript:

| .def Type | C++ Type | TypeScript Type | JSON Schema Type |
|-----------|----------|----------------|----------------|
| string    | FString  | string         | string         |
| int       | int32    | number         | integer        |
| float     | float    | number         | number         |
| enum      | enum class | enum         | integer + enum |
| compound  | struct   | object         | object         |

## Future Extensions

The current message format is functional but basic. Below is a prioritized todo list of future extensions, ordered by a combination of implementation complexity and user value:

### Todo List

- [ ] **Additional Data Types**
  - [ ] Boolean: Add support for boolean fields (true/false)
  - [ ] Byte: Add support for byte fields (8-bit unsigned integers)
  - [ ] Double: Add support for double-precision floating-point numbers
  - [ ] Int64: Add support for 64-bit integers
  - [ ] Vector2D/Vector3D/Vector4D: Add dedicated types for 2D, 3D, and 4D vectors
  - [ ] Color: Add support for color values (RGBA)
  - [ ] Quaternion: Add support for quaternions (for rotations)
  - [ ] Matrix: Add support for transformation matrices
  - [ ] UUID: Add support for universally unique identifiers
  - [ ] DateTime: Add support for date and time values

- [ ] **Optional Fields**
  ```
  field description: string optional
  field metadata: Metadata optional
  ```
  This would allow fields to be omitted from messages when not needed.

- [ ] **Default Values**
  ```
  field command: enum { Ping, Position } default(Ping)
  field timeout: int default(30)
  field enabled: bool default(true)
  ```
  This would allow fields to have default values when not explicitly set.

- [ ] **Arrays and Collections**
  ```
  field tags: string[]
  field points: Vector3D[]
  field properties: Map<string, string>
  ```
  This would allow messages to contain collections of values.

- [x] **Documentation Comments**

  The generated output files now include comprehensive self-documenting comments that explain the message format and provide detailed information about each message and field. These comments allow someone (human or AI) to generate a reader for that particular output from just the output file.

  For C++ output:
  ```cpp
  // Auto-generated message definitions for C++
  // This file contains message definitions for communication between systems.
  //
  // DOCUMENTATION FOR MESSAGE FORMAT:
  // ===============================
  // This file defines a set of message structures used for communication.
  // Each message is defined as a C++ struct within the Messages namespace.
  //
  // Message Structure:
  // - Messages are defined as structs with specific fields
  // - Messages can inherit from other messages using standard C++ inheritance
  // - Fields can be of the following types:
  //   * Basic types: int32 (integer), float, FString (string)
  //   * Enum types: defined as enum class with uint8 underlying type
  //   * Compound types: struct with named components

  /**
   * @struct ToolToUnrealCmd
   * @brief ToolToUnrealCmd message
   *
   * @details Fields:
   * - command: Enum (ToolToUnrealCmd_command_Enum) - command enum field
   * - verb: String (FString) - verb field
   * - actor: String (FString) - actor field
   */
  ```

  For TypeScript output:
  ```typescript
  // Auto-generated message definitions for TypeScript
  // This file contains message definitions for communication between systems.
  //
  // DOCUMENTATION FOR MESSAGE FORMAT:
  // ===============================
  // This file defines a set of message interfaces used for communication.
  // Each message is defined as a TypeScript interface within the Messages namespace.

  /**
   * ToolToUnrealCmd message
   *
   * @property {ToolToUnrealCmd_command_Enum} command - command enum field
   * @property {string} verb - verb field
   * @property {string} actor - actor field
   */
  ```

  Note: This implementation differs from the original plan in that it generates self-documenting comments in the output files rather than parsing documentation comments from the input file. This approach ensures that the output files are self-contained and can be understood without access to the original message definitions.

- [x] **User-Supplied Comments**
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
  Users can now add comments in the message definition file to explain the intent and purpose of messages and fields using the `///` syntax. These comments are parsed and included in the generated code (C++, TypeScript, and JSON), providing more context and documentation beyond just the mechanical structure of the messages. This feature is particularly useful for explaining the business logic and use cases for each message and field. The comments are preserved in all generated output formats and appear as documentation comments in the appropriate style for each language.

- [x] **Local Comments**
  ```
  // This is a local comment that will not appear in generated files
  message ToolToUnrealCmd {
      // This comment is only for internal documentation
      field command: enum { Ping, Position }

      // This field is used for verb actions
      field verb: string
  }
  ```
  Users can add local comments in the message definition file using the `//` syntax. These comments are only for the .def file itself and are not propagated to the generated files. This feature allows developers to add notes, explanations, or reminders that are only relevant to those working directly with the message definition file, without cluttering the generated code. Local comments can be placed anywhere in the .def file, including before message definitions, before field definitions, or at the end of blocks.

- [ ] **Namespaces and Modules**
  ```
  namespace Tool {
      message Command {
          // Fields
      }
  }

  namespace Unreal {
      message Response {
          // Fields
      }
  }
  ```
  This would allow messages to be organized into logical groups.

- [ ] **Validation Rules**
  ```
  field age: int min(0) max(120)
  field email: string regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
  field name: string minLength(1) maxLength(100)
  ```
  This would allow the system to validate message fields before sending or after receiving, ensuring data integrity.

- [x] **Message Serialization/Deserialization (Partial)**
  ```
  python message_wrangler.py --input messages.def --output ./generated --json
  ```
  This generates a JSON schema that can be used for JSON serialization and validation. Future work could include generating actual serialization/deserialization code for various formats.

- [ ] **Additional Language Support**
  - [ ] C#: For Unity or .NET applications
  - [ ] Python: For scripting and tools
  - [ ] Java/Kotlin: For Android applications
  - [ ] Swift: For iOS applications
  - [ ] Rust: For high-performance applications

- [x] **Schema Validation**
  ```
  python message_wrangler.py --input messages.def --output ./generated --json
  ```
  This generates a JSON schema file that can be used to validate messages at runtime. The schema includes type information, enum values, and inheritance relationships.

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

---

This document provides a comprehensive overview of the current message format and potential future extensions. The current implementation is a solid foundation that can be extended in various ways to meet evolving requirements.
