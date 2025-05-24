# Design Document: JSON-RPC Serializer/Deserializer for MessageWrangler

**Version:** 1.0
**Date:** 2025-05-15
**Author:** Gemini Code Assist

## 1. Introduction

This document outlines the design for a JSON-RPC based serialization/deserialization (serdes) mechanism for messages defined using the MessageWrangler format (as specified in `message_format_llm_spec.md`). The primary goal is to enable robust and standardized network communication of these messages.

### 1.1. Goals

* **Network Communication:** Enable MessageWrangler messages to be transmitted over a network.
* **Standardization:** Leverage the JSON-RPC 2.0 specification for message structure and RPC semantics.
* **Integration:** Seamlessly integrate the serdes logic into the existing MessageWrangler code generation pipeline (Python, C++, TypeScript).
* **Clarity & Efficiency:** Provide a clear, efficient, and human-readable (via JSON) representation of MessageWrangler messages.
* **Type Safety:** Ensure that serialization and deserialization processes respect the type definitions in the MessageWrangler schema.

### 1.2. Scope

This document covers:

* The mapping of MessageWrangler message structures and types to JSON.
* The structure of JSON-RPC requests, responses, and notifications carrying these messages.
* Modifications required in the code generators to produce serdes logic.
* Error handling within the JSON-RPC context.

This document does *not* cover specific network transport implementations (e.g., HTTP/WebSocket server/client implementations) or the definition of RPC service contracts beyond how messages are embedded.

### 1.3. References

* MessageWrangler Message Format LLM Specification (`message_format_llm_spec.md`)
* JSON-RPC 2.0 Specification

## 2. Background

MessageWrangler utilizes a custom definition language (see `message_format_llm_spec.md`) to define messages, enums, and other data structures, from which code is generated in multiple languages. To facilitate interoperability and network communication, a standardized serialization format is needed.

JSON-RPC 2.0 is a stateless, light-weight remote procedure call (RPC) protocol. Its use of JSON makes it broadly compatible and easy to debug.

## 3. Proposed Design

We will implement serdes logic that converts MessageWrangler message objects into JSON payloads suitable for JSON-RPC, and vice-versa.

### 3.1. JSON-RPC Message Structure

The serdes will produce/consume JSON objects that fit into the `params` (for requests/notifications) or `result` (for responses) fields of standard JSON-RPC 2.0 structures.

* **Request Object:**

    ```json
    {
        "jsonrpc": "2.0",
        "method": "YourServiceName.YourMethodName", // Defined by the application
        "params": { /* Serialized MessageWrangler message object */ },
        "id": "request_id" // Non-null for requests expecting a response
    }
    ```

* **Notification Object:**

    ```json
    {
        "jsonrpc": "2.0",
        "method": "YourServiceName.YourNotificationName", // Defined by the application
        "params": { /* Serialized MessageWrangler message object */ }
        // No "id" field
    }
    ```

* **Success Response Object:**

    ```json
    {
        "jsonrpc": "2.0",
        "result": { /* Serialized MessageWrangler message object, or other JSON value */ },
        "id": "request_id"
    }
    ```

* **Error Response Object:**

    ```json
    {
        "jsonrpc": "2.0",
        "error": {
            "code": -32602, // Example: Invalid params
            "message": "Detailed error message",
            "data": { /* Optional: additional error info */ }
        },
        "id": "request_id" // Or null if error detected before parsing id
    }
    ```

### 3.2. MessageWrangler Message to JSON Mapping

* Each MessageWrangler message instance will be serialized into a JSON object.
* Field names from the `.def` file will be used as keys in the JSON object.
  * For Python, names suffixed with `_` (e.g., `type_`) due to reserved words will be serialized using their original name (e.g., `"type"`). The (de)serializer for Python will handle this mapping.
* `optional` fields that are not set in the message object will be omitted from the JSON output.
* Message inheritance: Fields from parent messages will be included in the JSON object of the child message as if they were direct fields of the child (flattened structure).

### 3.3. Type Mapping

The following table details the mapping from MessageWrangler types to JSON types:

| MessageWrangler Type        | JSON Type                                  | Serialization Notes                                                                                                                                                              | Deserialization Notes                                                                                                                                                           |
|-----------------------------|--------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `string`                    | `string`                                   | Direct mapping.                                                                                                                                                                  | Direct mapping.                                                                                                                                                                 |
| `int`                       | `number` (integer)                         | Direct mapping.                                                                                                                                                                  | Validate that it's an integer.                                                                                                                                                  |
| `float`                     | `number` (floating-point)                  | Direct mapping.                                                                                                                                                                  | Validate that it's a number.                                                                                                                                                    |
| `bool`                      | `boolean`                                  | Direct mapping (`true` or `false`).                                                                                                                                              | Direct mapping.                                                                                                                                                                 |
| `byte`                      | `number` (integer 0-255)                   | Direct mapping.                                                                                                                                                                  | Validate range 0-255.                                                                                                                                                           |
| `Enum`                      | `string` (enum value name)                 | Default. E.g., `Status.OK` becomes `"OK"`.                                                                                                                                       | Map string name back to enum value. Case-sensitive. Invalid string results in deserialization error.                                                                            |
| `Enum`                      | `number` (enum value, optional)            | Alternative, if configured. E.g., `Status.OK` (value 0) becomes `0`.                                                                                                             | Map number back to enum value. Invalid number results in deserialization error.                                                                                                 |
| `Options`                   | `number` (integer)                         | Bitwise OR of set option values. E.g., `Read \| Write` (1 \| 2) becomes `3`.                                                                                                | Direct mapping.                                                                                                                                                                 |
| `Compound` (e.g., `float {x,y,z}`) | `object`                                   | E.g., `{"x": 1.0, "y": 2.0, "z": 3.0}`. Field names are component names. Generated as `MessageName_fieldName_Compound` class.                                               | Map to corresponding compound class instance.                                                                                                                                   |
| Message Reference           | `object` (nested JSON object)              | Recursively serialize the referenced message.                                                                                                                                    | Recursively deserialize to the referenced message type.                                                                                                                         |
| `Type[]` (Array)            | `array` (JSON array of mapped types)       | Elements serialized according to their type. `byte[]` is a special case.                                                                                                         | Elements deserialized according to their type.                                                                                                                                  |
| `byte[]`                    | `string` (Base64 encoded)                  | Standard Base64 encoding.                                                                                                                                                        | Decode from Base64 string. Invalid Base64 results in deserialization error.                                                                                                     |
| `Map<string, Type>`         | `object` (JSON object)                     | Map keys become JSON object keys. Values are serialized according to `Type`.                                                                                                       | JSON object keys become map keys. Values are deserialized according to `Type`.                                                                                                  |

**Note on `optional` fields:**

* **Serialization:** If an optional field is not set (e.g., `None` in Python, not present in a C++ `std::optional`, or a designated "unset" state), it MUST be omitted from the JSON output. It should NOT be represented as `null` unless explicitly required by a future specification update for specific cases.
* **Deserialization:** If an optional field is missing from the JSON input, the corresponding field in the deserialized message object MUST be left in its "not set" state. If `null` is encountered for an optional field that is not a message reference, it may be treated as "not set" or raise an error depending on strictness (recommend treating as "not set" for flexibility, if the type itself isn't nullable). For optional message references, `null` should be treated as "not set".

### 3.4. Serialization Process

For each generated message class, a method (e.g., `to_json_dict()` in Python, `toJsonObject()` in C++/TypeScript) will be added.

1. Initialize an empty JSON object representation (e.g., Python `dict`, C++ `nlohmann::json`, TS `object`).
2. Iterate over all fields of the message (including inherited fields).
3. For each field:
    a.  If the field is `optional` and not set, skip it.
    b.  Retrieve the field's value.
    c.  Convert the value to its JSON representation according to the Type Mapping table (Section 3.3).
        *For `byte[]`, encode to Base64 string.
        *   For `Enum`, convert to string name (or integer if configured).
        *For `Compound` types, serialize to a nested JSON object.
        *   For referenced messages, recursively call their serialization method.
        *For arrays, create a JSON array, serializing each element.
        *   For maps, create a JSON object, serializing each value.
    d.  Add the original field name (from `.def` file) and its JSON representation to the JSON object.
4. Return the populated JSON object representation.

### 3.5. Deserialization Process

For each generated message class, a static factory method (e.g., `from_json_dict(data)` in Python, `fromJsonObject(jsonData)` in C++/TypeScript) will be added.

1. Input: A JSON object representation (e.g., Python `dict`, C++ `nlohmann::json`, TS `object`).
2. Create a new instance of the message class.
3. Iterate over all fields defined for the message (including inherited fields).
4. For each field:
    a.  Get the original field name (from `.def` file).
    b.  Check if the field name exists as a key in the input JSON object.
    c.  If the key exists:
        i.  Retrieve the JSON value.
        ii. Convert the JSON value to the expected MessageWrangler type according to the Type Mapping table (Section 3.3). This includes:
            *Type checking (e.g., ensure a number is provided for an `int` field).
            *   For `byte[]`, decode from Base64 string.
            *For `Enum`, convert string name (or integer) to the enum value.
            *   For `Compound` types, deserialize from the nested JSON object into an instance of the compound class.
            *For referenced messages, recursively call their deserialization method.
            *   For arrays, create a native array/list, deserializing each JSON array element.
            *   For maps, create a native map/dictionary, deserializing each JSON object value.
        iii.Set the field in the message instance.
    d.  If the key does not exist:
        i.  If the field is `optional`, leave it in its "not set" state.
        ii. If the field is `required` (once this modifier becomes meaningful and enforced), report a deserialization error.
5. Return the populated message instance.
6. Deserialization errors (type mismatches, invalid enum values, invalid Base64, etc.) should lead to appropriate exceptions or error statuses that can be translated into JSON-RPC error responses (e.g., `code: -32602, "Invalid params"`).

### 3.6. Handling of Specific MessageWrangler Features

* **Cross-file/namespace references:** The generated code already resolves these. Serialization uses the concrete types. JSON itself is namespace-agnostic for payloads; namespaces might appear in JSON-RPC `method` names if desired by the application.
* **Compound types:** (e.g., `SomeMessage_someField_Compound`) will be (de)serialized as nested JSON objects, as per Section 3.3.
* **Parent class references:** Handled by iterating fields from the entire inheritance hierarchy during (de)serialization, resulting in a flat JSON structure for all fields.
* **Basic types:** Never treated as message references; directly (de)serialized.
* **Reserved words (Python):** The (de)serializer for Python will map between the internal `_`-suffixed name and the original name for JSON keys. E.g., Python `field.type_` <-> JSON `{"type": ...}`.
* **Inline enums and compounds:** These are emitted as classes and will be (de)serialized like their top-level counterparts.

## 4. Code Generation Impact

The existing code generators for Python, C++, and TypeScript will be modified:

1. **Message Classes:**
    * Add a public method for serialization (e.g., `serialize_json()`, `toJsonString()`) that internally calls the logic from Section 3.4 and then converts the language-native JSON object (dict, `nlohmann::json`, etc.) to a JSON string.
    * Add a public method that returns the language-native JSON object (e.g., `to_json_dict()`, `toJsonObject()`).
    * Add a static factory method for deserialization from a JSON string (e.g., `deserialize_json(json_string)`, `fromJsonString(jsonString)`). This method will first parse the string into a language-native JSON object and then call the logic from Section 3.5.
    * Add a static factory method for deserialization from a language-native JSON object (e.g., `from_json_dict(data)`, `fromJsonObject(jsonData)`).

2. **Enum Types:**
    * Generate functions/methods to convert enum values to/from their string names.
    * (Optional) Generate functions/methods to convert enum values to/from their integer representations if this serialization mode is supported.

3. **Compound Types Classes:**
    * Similar serialization/deserialization methods as message classes will be added.

4. **Utility Code:**
    * Base64 encoding/decoding utilities might be needed, either by relying on standard libraries per language or by providing/generating helpers.
    * A common runtime library (per language) for serdes helpers could be beneficial.

## 5. JSON-RPC Client/Server Helpers (Future Enhancement)

While the core task is the serdes logic for individual messages, future work could involve extending generators to produce:

* **Client Stubs:** For a defined "service" (a collection of RPC methods using MessageWrangler messages), generate client-side code that simplifies making JSON-RPC calls. This would encapsulate request serialization, network call, and response deserialization.
* **Server Skeletons/Dispatchers:** Generate server-side code to parse incoming JSON-RPC requests, dispatch to appropriate handler functions (with pre-deserialized MessageWrangler message objects as input), and serialize handler return values into JSON-RPC responses.

## 6. Error Handling

* **Serialization Errors:** Errors during serialization (e.g., an invalid state of a message object that prevents serialization) should typically raise exceptions in the local context.
* **Deserialization Errors:** Errors during deserialization (e.g., malformed JSON, type mismatch, missing required field, invalid enum string, invalid Base64) must be caught. These should translate into JSON-RPC error responses, typically using `code: -32602` ("Invalid params") or `code: -32700` ("Parse error" if JSON itself is invalid). The `message` field of the error object should provide a human-readable description of the issue. The optional `data` field can carry more structured error details.

## 7. Example

Given MessageWrangler definitions:

```text
// in common.def
namespace Common;
enum Status {
    PENDING = 0,
    ACTIVE = 1,
    DELETED = 2
}

message Item {
    id: string
    value: float
    status: Status optional
}

// in service.def
namespace MyService;
import "./common.def" as Common;

message UpdateItemRequest {
    itemToUpdate: Common::Item
    timestamp: int // Unix timestamp
}

message UpdateItemResponse {
    itemId: string
    newStatus: Common::Status
    confirmationCode: string optional
}
```

**JSON-RPC Request:**

```json
{
    "jsonrpc": "2.0",
    "method": "MyService.UpdateItem",
    "params": { // Serialized UpdateItemRequest
        "itemToUpdate": { // Serialized Common.Item
            "id": "item-123",
            "value": 42.75,
            "status": "ACTIVE" // Enum as string
        },
        "timestamp": 1678886400
    },
    "id": "req-001"
}
```

If `itemToUpdate.status` was not set, the `"status": "ACTIVE"` line would be omitted.

**JSON-RPC Success Response:**

```json
{
    "jsonrpc": "2.0",
    "result": { // Serialized UpdateItemResponse
        "itemId": "item-123",
        "newStatus": "ACTIVE",
        "confirmationCode": "CONF-XYZ789"
    },
    "id": "req-001"
}
```

If `confirmationCode` was not set in the response object, it would be omitted.

**JSON-RPC Error Response (e.g., invalid status string in request):**

```json
{
    "jsonrpc": "2.0",
    "error": {
        "code": -32602,
        "message": "Invalid params: Field 'itemToUpdate.status' has invalid enum value 'ACTIVATED'. Valid values are PENDING, ACTIVE, DELETED.",
        "data": {
            "field": "itemToUpdate.status",
            "value": "ACTIVATED"
        }
    },
    "id": "req-001"
}
```

## 8. Alternatives Considered

* **Protocol Buffers (Protobuf) / gRPC:** Offers binary efficiency and a strong RPC framework. However, JSON-RPC was specifically requested, offering human readability and broader, simpler integration in many web-centric ecosystems.
* **Raw JSON (no RPC structure):** While simpler for pure data exchange, JSON-RPC provides essential RPC semantics (method dispatch, request/response correlation, error reporting) beneficial for networked services.

## 9. Open Questions / Future Considerations

* **Enum Serialization Configuration:** Should the choice between string name and integer value for enums be configurable (e.g., via an `options` block or a generator flag)? Default to string names for readability.
* **`required` Modifier:** Define precise behavior for `required` fields once this modifier becomes fully active in `message_format_llm_spec.md`. Deserialization must fail if a required field is missing.
* **Message/API Versioning:** How will versions of messages and RPC methods be handled? (Out of scope for this initial serdes design, but important for API evolution).
* **`oneof` / `union` Support:** If MessageWrangler adds algebraic data types like `oneof` or `union`, their JSON representation and (de)serialization logic will need to be defined. (Common patterns include a type discriminator field).
* **JSON Library Dependencies:** Specify or recommend standard JSON libraries for each target language (e.g., Python's `json` module, C++'s `nlohmann/json`, TypeScript's built-in `JSON` object).
* **Strictness of Deserialization:** Define behavior for unknown fields in the JSON input (ignore by default, or error if strict mode is enabled). For now, unknown fields should be ignored to allow for forward compatibility.

This design provides a foundation for robust JSON-RPC communication using MessageWrangler definitions.
