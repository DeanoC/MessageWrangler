# Message Format LLM Specification

This document provides a concise, machine-readable specification of the message definition format used in this project. It is intended for use by large language models (LLMs) and other automated tools to understand, parse, and generate valid message definitions.

---

## Top-Level Structure

- The format consists of one or more message, enum, options, or namespace definitions.
- Comments may be included using `//`, `/* ... */`, or `///` (doc comment).

---

## Message Definition

```
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
- **Options:** `options { ... }` (inline)
- **Compound:** `float { x, y, z }` (currently only float supported)
- **Message reference:** `OtherMessage` or `Namespace::OtherMessage`
- **Array:** `Type[]` (e.g., `string[]`, `Vec3[]`)
- **Map:** `Map<string, Type>` (key must be string)

---

## Enum Definition

```
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

```
options OptionsName {
    Option1 [= number],
    Option2 [= number],
    ...
}
```

- Like enums, but values are powers of two (bit flags).

---

## Namespace Definition

```
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

```
import "./other.def" [as Namespace]
```

- Imports definitions from another file, optionally into a namespace.

---

## Examples

### Message with basic fields

```
message Example {
    name: string
    id: int
    active: bool optional
}
```

### Message with array, map, and reference

```
message Complex {
    tags: string[]
    points: Vec3[]
    properties: Map<string, string>
    ref: OtherMessage
}
```

### Enum and options

```
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

```
namespace Tool {
    message Command {
        type: string
    }
}
import "./base.def" as Base
```

---

## Not Supported

- Nested arrays (e.g., `string[][]`) are not allowed.
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
| Array          | tags: string[]                        | No nested arrays                      |
| Map            | dict: Map<string, int>                | Key must be string                    |
| Enum           | enum Status { OK = 0, ERR = 1 }       | Inline or top-level                   |
| Enum Ref       | field: OtherMsg.Status                |                                       |
| Options        | options Perms { Read = 1, ... }       | Bit flags                             |
| Compound       | float { x, y, z }                     | Only float supported                  |
| Namespace      | namespace NS { ... }                  |                                       |
| Import         | import "./foo.def" as Bar             |                                       |
| Comments       | /// doc, // local, /*...*/          | /// included in output                |

---

This document is intended for LLM and tool consumption. For human-oriented documentation, see `message_format_documentation.md`.
