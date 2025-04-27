# Message Serialization Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Wire Format](#wire-format)
   - [JSON Message Envelope](#json-message-envelope)
   - [Message Type Identification](#message-type-identification)
   - [Error Handling](#error-handling)
3. [Serialization & Deserialization](#serialization--deserialization)
   - [TypeScript Implementation](#typescript-implementation)
   - [C++ Implementation](#c-implementation)
4. [Data Protection](#data-protection)
   - [Schema Validation](#schema-validation)
   - [Type Safety](#type-safety)
   - [Checksums & Integrity](#checksums--integrity)
   - [Error Recovery](#error-recovery)
5. [Implementation Guidelines](#implementation-guidelines)
   - [TypeScript Code Generator Extensions](#typescript-code-generator-extensions)
   - [C++ Code Generator Extensions](#c-code-generator-extensions)
6. [Performance Considerations](#performance-considerations)
   - [JSON Optimization](#json-optimization)
   - [Binary Format Options](#binary-format-options)
7. [Versioning Strategy](#versioning-strategy)
8. [Debugging Tips](#debugging-tips)

## Introduction

This document describes the message serialization system for communication between a client application (TypeScript) and Unreal Engine (C++) over WebSockets. The system uses JSON as the wire format for message exchange, with schema validation to ensure message integrity.

The serialization format described here complements the message definition system (.def files) and the code generation process that produces C++, TypeScript, and JSON schema outputs.

## Wire Format

### JSON Message Envelope

All messages are transmitted as JSON objects with a standard envelope structure that wraps the actual message payload:

```json
{
  "messageType": "MessageName",
  "payload": {
    // Message-specific fields
  }
}
```

The envelope consists of:
- `messageType`: A string identifying the type of message (corresponds to the message name in the .def file)
- `payload`: The actual message content, structured according to the message definition

This envelope pattern allows the receiving system to determine the message type before attempting to parse the payload, enabling proper routing and deserialization.

### Message Type Identification

Message types are identified by the `messageType` field in the message envelope. This field contains a string that matches the name of a message defined in the .def file. For example:

```json
{
  "messageType": "ToolToUnrealCmd",
  "payload": {
    "command": 0,
    "verb": "update",
    "actor": "Player"
  }
}
```

The message type identification system:
1. Enables the receiver to select the appropriate deserialization logic
2. Facilitates message routing to the appropriate handlers
3. Supports inheritance by allowing derived message types to be processed by handlers for base types

### Error Handling

When errors occur during message serialization or deserialization, the system provides structured error responses:

```json
{
  "messageType": "ErrorResponse",
  "payload": {
    "errorCode": 400,
    "errorMessage": "Invalid message format",
    "originalMessageType": "ToolToUnrealCmd",
    "details": "Required field 'command' is missing"
  }
}
```

Common error scenarios include:
- Schema validation failures (missing required fields, invalid types)
- Unknown message types
- Parsing errors (malformed JSON)
- Type conversion errors

Error responses include sufficient context to help diagnose and resolve the issue, including the original message type that caused the error.

## Serialization & Deserialization

### TypeScript Implementation

The TypeScript implementation provides utilities for serializing and deserializing messages:

```typescript
// Serialization
function serializeMessage<T>(messageType: string, payload: T): string {
  const envelope = {
    messageType,
    payload
  };
  return JSON.stringify(envelope);
}

// Deserialization
function deserializeMessage(jsonString: string): { messageType: string, payload: any } {
  const envelope = JSON.parse(jsonString);
  if (!envelope.messageType || !envelope.payload) {
    throw new Error("Invalid message format: missing messageType or payload");
  }
  return envelope;
}
```

The TypeScript implementation leverages the generated interfaces to provide type safety:

```typescript
import { Messages } from './generated/messages';

// Type-safe serialization
const command: Messages.ToolToUnrealCmd = {
  command: Messages.ToolToUnrealCmd_command_Enum.Ping,
  verb: "check",
  actor: "System"
};
const serialized = serializeMessage("ToolToUnrealCmd", command);

// Type-safe deserialization
const envelope = deserializeMessage(receivedJson);
if (envelope.messageType === "ToolToUnrealCmd") {
  const cmd = envelope.payload as Messages.ToolToUnrealCmd;
  // Process command
}
```

### C++ Implementation

The C++ implementation provides similar functionality for Unreal Engine:

```cpp
// Serialization
template<typename T>
FString SerializeMessage(const FString& MessageType, const T& Payload)
{
  TSharedPtr<FJsonObject> EnvelopeObj = MakeShared<FJsonObject>();
  EnvelopeObj->SetStringField("messageType", MessageType);

  TSharedPtr<FJsonObject> PayloadObj = MakeShared<FJsonObject>();
  // Convert Payload to JSON object
  // ...

  EnvelopeObj->SetObjectField("payload", PayloadObj);

  FString OutputString;
  TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutputString);
  FJsonSerializer::Serialize(EnvelopeObj.ToSharedRef(), Writer);

  return OutputString;
}

// Deserialization
bool DeserializeMessage(const FString& JsonString, FString& OutMessageType, TSharedPtr<FJsonObject>& OutPayload)
{
  TSharedPtr<FJsonObject> EnvelopeObj;
  TSharedRef<TJsonReaderFactory<>> Reader = TJsonReaderFactory<>::Create(JsonString);
  if (!FJsonSerializer::Deserialize(Reader, EnvelopeObj) || !EnvelopeObj.IsValid())
  {
    return false;
  }

  if (!EnvelopeObj->TryGetStringField(StringCast<TCHAR>("messageType").Get(), OutMessageType))
  {
    return false;
  }

  const TSharedPtr<FJsonObject>* PayloadObjPtr;
  if (!EnvelopeObj->TryGetObjectField(StringCast<TCHAR>("payload").Get(), PayloadObjPtr))
  {
    return false;
  }

  OutPayload = *PayloadObjPtr;
  return true;
}
```

The C++ implementation includes helper functions for converting between C++ structs and JSON objects, leveraging Unreal Engine's JSON utilities.

## Data Protection

### Schema Validation

Schema validation ensures that messages conform to their defined structure before processing:

1. **Client-side validation**: Before sending a message, the client validates it against the JSON schema to catch errors early
2. **Server-side validation**: Upon receiving a message, the server validates it against the schema before processing
3. **Generated schemas**: The JSON schemas are automatically generated from the .def files, ensuring they stay in sync with the message definitions

Example validation code (TypeScript):

```typescript
import Ajv from 'ajv';
import schema from './generated/messages.json';

const ajv = new Ajv();
const validate = ajv.compile(schema.definitions.ToolToUnrealCmd);

function validateMessage(message) {
  if (!validate(message)) {
    throw new Error(`Validation failed: ${JSON.stringify(validate.errors)}`);
  }
  return true;
}
```

### Type Safety

The system provides type safety through:

1. **Strongly-typed interfaces**: Generated TypeScript interfaces and C++ structs ensure type safety at compile time
2. **Enum validation**: Enum values are validated against their defined ranges
3. **Type conversion**: Automatic conversion between JSON types and native language types

Example of type safety in TypeScript:

```typescript
// Compile-time type checking
function processCommand(cmd: Messages.ToolToUnrealCmd) {
  switch (cmd.command) {
    case Messages.ToolToUnrealCmd_command_Enum.Ping:
      // Handle ping
      break;
    case Messages.ToolToUnrealCmd_command_Enum.Position:
      // Handle position
      break;
    default:
      // Exhaustive check ensures all enum values are handled
      const _exhaustiveCheck: never = cmd.command;
  }
}
```

### Checksums & Integrity

To ensure message integrity during transmission:

1. **WebSocket protocol**: The underlying WebSocket protocol provides basic integrity checking
2. **Optional message checksums**: For critical messages, an optional checksum field can be added:

```json
{
  "messageType": "CriticalCommand",
  "payload": {
    // Message fields
  },
  "checksum": "a1b2c3d4e5f6"
}
```

The checksum is calculated based on the serialized payload and can be verified by the receiver.

### Error Recovery

The system implements several strategies for error recovery:

1. **Automatic retries**: For transient errors, the system can automatically retry sending messages
2. **Fallback values**: When deserializing, missing or invalid fields can be replaced with default values
3. **Partial processing**: When possible, valid parts of a message are processed even if other parts contain errors
4. **State synchronization**: Periodic state synchronization messages ensure that client and server states remain consistent

## Implementation Guidelines

### TypeScript Code Generator Extensions

To extend the TypeScript code generator for serialization support:

1. **Add serialization methods**: Extend the generated code to include serialization/deserialization methods:

```typescript
// In typescript_generator.py
def generate_serialization_methods(self, output_file):
    output_file.write("""
export namespace MessageSerialization {
    export function serialize<T>(messageType: string, payload: T): string {
        return JSON.stringify({
            messageType,
            payload
        });
    }

    export function deserialize(jsonString: string): { messageType: string, payload: any } {
        const envelope = JSON.parse(jsonString);
        if (!envelope.messageType || !envelope.payload) {
            throw new Error("Invalid message format");
        }
        return envelope;
    }
}
""")
```

2. **Add type guards**: Generate type guard functions to safely check message types:

```typescript
// Generated code
export function isToolToUnrealCmd(obj: any): obj is ToolToUnrealCmd {
    return obj && 
           typeof obj.command === 'number' &&
           typeof obj.verb === 'string' &&
           typeof obj.actor === 'string';
}
```

3. **Add validation**: Generate validation functions using the JSON schema:

```typescript
// Generated code
export function validateToolToUnrealCmd(obj: any): boolean {
    // Validation logic
    return true;
}
```

### C++ Code Generator Extensions

To extend the C++ code generator for serialization support:

1. **Add serialization methods**: Generate ToJson and FromJson methods for each message struct:

```cpp
// In cpp_generator.py
def generate_serialization_methods(self, message, output_file):
    output_file.write(f"""
    // Serialization methods for {message.name}
    inline TSharedPtr<FJsonObject> ToJson(const {message.name}& Message)
    {{
        TSharedPtr<FJsonObject> JsonObj = MakeShared<FJsonObject>();
        // Field serialization code
        return JsonObj;
    }}

    inline bool FromJson(const TSharedPtr<FJsonObject>& JsonObj, {message.name}& OutMessage)
    {{
        // Field deserialization code
        return true;
    }}
""")
```

2. **Add message factory**: Generate a message factory that creates message instances based on type:

```cpp
// Generated code
TSharedPtr<FJsonObject> CreateMessage(const FString& MessageType)
{
    if (MessageType == "ToolToUnrealCmd")
    {
        return MakeShared<Messages::ToolToUnrealCmd>();
    }
    // Other message types
    return nullptr;
}
```

## Performance Considerations

### JSON Optimization

To optimize JSON serialization and deserialization:

1. **Minimize message size**: Keep message fields concise and use appropriate data types
2. **Field naming**: Use short but descriptive field names to reduce payload size
3. **Batch processing**: Combine multiple small messages into batches when appropriate
4. **Compression**: For large messages, consider using compression:

```json
{
  "messageType": "CompressedMessage",
  "compressed": true,
  "payload": "gzip-base64-encoded-data"
}
```

5. **Partial updates**: Send only changed fields rather than complete objects when possible

### Binary Format Options

While JSON is the default format, binary formats can be considered for performance-critical applications:

1. **MessagePack**: A binary format that's more compact than JSON and faster to parse
2. **Protocol Buffers**: Google's binary serialization format, offering strong typing and compact representation
3. **FlatBuffers**: Zero-copy binary serialization format, ideal for performance-critical applications

Implementation considerations for binary formats:

```typescript
// TypeScript example with MessagePack
import * as msgpack from 'msgpack-lite';

function serializeBinary(messageType: string, payload: any): Buffer {
  return msgpack.encode({
    messageType,
    payload
  });
}

function deserializeBinary(buffer: Buffer): { messageType: string, payload: any } {
  return msgpack.decode(buffer);
}
```

## Versioning Strategy

To handle evolving message formats:

1. **Version field**: Include a version field in the message envelope:

```json
{
  "messageType": "ToolToUnrealCmd",
  "version": 2,
  "payload": {
    // Message fields
  }
}
```

2. **Backward compatibility**: Ensure new message versions can be processed by older receivers:
   - Make new fields optional
   - Provide default values for new fields
   - Maintain the same field types for existing fields

3. **Forward compatibility**: Allow older message versions to be processed by newer receivers:
   - Check for missing fields and provide defaults
   - Validate field types before processing
   - Include version-specific handling logic

4. **Version negotiation**: Implement a handshake protocol to negotiate supported message versions:

```json
{
  "messageType": "VersionNegotiation",
  "payload": {
    "supportedVersions": [1, 2, 3],
    "preferredVersion": 3
  }
}
```

## Debugging Tips

To facilitate debugging of message serialization issues:

1. **Message logging**: Log all sent and received messages in development environments:

```typescript
function logMessage(direction: 'SEND' | 'RECEIVE', message: any) {
  console.log(`[${direction}] ${JSON.stringify(message, null, 2)}`);
}
```

2. **Schema validation errors**: Provide detailed error messages for schema validation failures:

```typescript
function validateWithDetails(message: any, schema: any): { valid: boolean, errors: any[] } {
  const validate = ajv.compile(schema);
  const valid = validate(message);
  return {
    valid,
    errors: validate.errors || []
  };
}
```

3. **Message replay**: Implement a system to replay problematic messages for debugging:

```typescript
// Store problematic messages
const messageLog: { timestamp: Date, message: string }[] = [];

// Replay functionality
function replayMessage(index: number) {
  const entry = messageLog[index];
  if (entry) {
    processMessage(entry.message);
  }
}
```

4. **Visualization tools**: Create tools to visualize message structure and content:
   - Message structure diagrams
   - Diff views for comparing expected vs. actual messages
   - Timeline views for message sequences

5. **Test fixtures**: Create test fixtures for common message types to use in debugging:

```typescript
const testMessages = {
  ping: {
    messageType: "ToolToUnrealCmd",
    payload: {
      command: 0, // Ping
      verb: "check",
      actor: "System"
    }
  },
  // Other test messages
};
```
