# Message Format LLM Specification

This document provides a concise, machine-readable specification of the message definition format used in this project. It is intended for use by large language models (LLMs) and other automated tools to understand, parse, and generate valid message definitions.

## Recent Updates (2025-05)

- **Cross-file and cross-namespace references**: All references to messages, enums, and compound types across files and namespaces are now correctly imported and available in generated code (Python, C++, TypeScript).
- **Compound types**: For every referenced compound type (e.g., `SomeMessage_someField_Compound`), a class is generated and imported if not defined locally.
- **Parent class references**: Parent classes in inheritance (e.g., `Base::Command`) are now always available in generated code via correct imports and class name resolution.
- **Basic types**: Basic types (`string`, `int`, `float`, `bool`, `byte`) are never treated as message references.
- **Reserved words and built-in names**: Field/component names that match Python reserved words or built-in types are suffixed with `_` in generated Python code to avoid conflicts.
- **Parser strictness**: Nested arrays (e.g., `string[][]`) are explicitly rejected by the parser and will cause a parse error.
- **Inline enums and compounds**: Inline enums and compound types are always emitted as classes in generated code if referenced.

---

## Top-Level Structure

- The format consists of one or more message, enum, options, or namespace definitions.
- Comments may be included using `//`, `/* ... */`, or `///` (doc comment).

---

## Message Definition

```text
message MessageName [ : ParentMessage ] {
    fieldName: FieldType [field modifiers] [= defaultValue]
    ...
}
```

- `MessageName`: Identifier for the message.
- `ParentMessage`: (optional) Inheritance from another message (may be namespaced).
- Fields are defined as `fieldName: FieldType`.
- Field modifiers: `optional`, `repeated`, `required` (optional, only `optional` is currently meaningful).
- Default values: `= value` (optional, only for basic types and enums).

---

## Field Types

- **Basic types:** `string`, `int`, `float`, `bool`, `byte`
- **Enum:** `enum { ... }` (inline) or reference to another enum (see below)
- **Options:** `options { ... }` (inline) or reference to another options type.
- **Compound:** `float { x, y, z }` (currently only float supported). These are defined inline. In generated code, they result in a class, typically named `MessageName_fieldName_Compound` if part of `MessageName`.
- **Message reference:** `MessageName` (if in current scope/namespace or imported directly without an alias) or `NamespaceIdentifier::MessageName`.
- **Array:** `Type[]` (e.g., `string[]`, `Vec3[]`)
- **Map:** `Map<string, Type>` (key must be string)

---

## Enum Definition

```text
enum EnumName [ : ParentEnum ] {
    Value1 [= number],
    Value2 [= number],
    ...
}
```

- Can be top-level or inline in a message field.
- Values auto-increment unless specified.
- Can reference/extend another enum (optionally namespaced).

---

## Options Definition

```text
options OptionsName {
    Option1 [= number],
    Option2 [= number],
    ...
}
```

- Like enums, but values are powers of two (bit flags).

---

## Namespace Definition

```text
namespace NamespaceName {
    ...definitions...
}
```

- Used to group messages, enums, and options.
- Namespaces can be nested.

---

## Field Modifiers

- `optional`: Field may be omitted.
- `repeated`/`required`: Reserved for future use.

---

## Comments

- `//` or `/* ... */`: Local comments, ignored by code generators.
- `///`: Doc comments, included in generated code as documentation.

---

## Import

```text
import "./other.def" [as Namespace]
```

- Imports definitions from another file, optionally into a namespace.

---

## Examples

### Message with basic fields

```text
message Example {
    name: string
    id: int
    active: bool optional
}
```

### Message with array, map, and reference

```text
message Complex {
    tags: string[]
    points: Vec3[]
    properties: Map<string, string>
    ref: OtherMessage
}
```

### Enum and options

```text
enum Status {
    OK = 0,
    ERROR = 1
}
options Permissions {
    Read = 1,
    Write = 2,
    Execute = 4
}
```

### Namespaces and imports

```text
namespace Tool {
    message Command {
        type: string
    }
}
import "./base.def" as Base
```

---

## Not Supported / Strictly Rejected

- Nested arrays (e.g., `string[][]`) are not allowed and will cause a parse error.
- Maps must have `string` keys.
- Default values for arrays/maps are not supported.
- Only `float` is supported for compound types.
- Only `optional` field modifier is meaningful.

---

## Summary Table

| Feature         | Syntax Example                        | Notes                                 |
|----------------|---------------------------------------|---------------------------------------|
| Message        | message Foo { ... }                   |                                       |
| Inheritance    | message Bar : Foo { ... }             |                                       |
| Field          | name: string                          |                                       |
| Array          | tags: string[]                        | No nested arrays; nested arrays rejected |
| Map            | dict: Map<string, int>                | Key must be string                    |
| Enum           | enum Status { OK=0, ERR=1 }           | Inline or top-level. Referenced as `EnumName` or `Namespace::EnumName`. |
| Enum Ref       | field: MyNamespace::MyEnum            | Cross-file/namespace refs imported    |
| Options        | options Perms { Read = 1, ... }       | Bit flags                             |
| Compound       | float { x, y, z }                     | Only float supported; always emitted as class |
| Namespace      | namespace NS { ... }                  |                                       |
| Import         | import "./foo.def" as Bar             | Cross-file/namespace refs imported    |
| Comments       | /// doc, // local, /*...*/            | /// included in output                |
| Reserved Name Handling (Python Gen) | `name` -> `name_` | Python generator suffixes names conflicting with reserved words/built-ins. |


This document is intended for LLM and tool consumption. For human-oriented documentation, see `message_format_documentation.md`.
