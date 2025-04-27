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

This document describes the message format used for communication between an Electron application and Unreal Engine 5 over WebSocket. The system uses a single source file (.def) to define messages that are then converted into both C++ (for Unreal Engine) and TypeScript (for Electron) code.

The message format converter is implemented in Python and can be found in `script.py`. It processes a .def file and generates the corresponding C++ and TypeScript code.

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

### Type Mappings

The following table shows how types are mapped between the .def file, C++, and TypeScript:

| .def Type | C++ Type | TypeScript Type |
|-----------|----------|----------------|
| string    | FString  | string         |
| int       | int32    | number         |
| float     | float    | number         |
| enum      | enum class | enum         |
| compound  | struct   | object         |

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

- [ ] **Documentation Comments**
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
  These comments could be included in the generated code as documentation.

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

- [ ] **Message Serialization/Deserialization**
  ```
  python script.py --input messages.def --output ./generated --serialization json
  ```
  This would generate code to convert messages to and from JSON, binary, or other formats.

- [ ] **Additional Language Support**
  - [ ] C#: For Unity or .NET applications
  - [ ] Python: For scripting and tools
  - [ ] Java/Kotlin: For Android applications
  - [ ] Swift: For iOS applications
  - [ ] Rust: For high-performance applications

- [ ] **Schema Validation**
  ```
  python script.py --input messages.def --output ./generated --schema
  ```
  This would generate a schema file that could be used to validate messages at runtime.

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
