"""
JSON Schema generator for MessageModel.
Generates a valid JSON Schema (Draft 7+) for all messages, enums, and options in the model.
"""
import json
from message_model import MessageModel, FieldType

BASIC_TYPE_TO_JSON = {
    FieldType.STRING: "string",
    FieldType.INT: "integer",
    FieldType.FLOAT: "number",
    FieldType.BOOL: "boolean",
    FieldType.BYTE: "integer",  # with range 0-255
}

def generate_json_schema(model: MessageModel, title="Message Definitions", description="JSON schema for message definitions"):
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": title,
        "description": description,
        "definitions": {},
    }
    # Enums
    for enum in model.enums.values():
        enum_def = {
            "type": "integer",
            "description": enum.description or enum.name,
            "enum": [v.value for v in enum.values],
            "enumNames": [v.name for v in enum.values],
        }
        schema["definitions"][enum.name] = enum_def
    # Messages
    for msg in model.messages.values():
        msg_def = {
            "type": "object",
            "description": msg.description or msg.name,
            "properties": {},
            "required": [],
        }
        for field in msg.fields:
            field_schema = field_to_json_schema(field, model)
            msg_def["properties"][field.name] = field_schema
            if "optional" not in field.modifiers:
                msg_def["required"].append(field.name)
        if not msg_def["required"]:
            del msg_def["required"]
        schema["definitions"][msg.name] = msg_def
    return schema

def field_to_json_schema(field, model):
    # Basic types
    if field.field_type in BASIC_TYPE_TO_JSON:
        sch = {"type": BASIC_TYPE_TO_JSON[field.field_type]}
        if field.field_type == FieldType.BYTE:
            sch["minimum"] = 0
            sch["maximum"] = 255
        if field.is_array:
            return {"type": "array", "items": sch}
        if field.is_map:
            return {"type": "object", "additionalProperties": sch}
        return sch
    # Enum
    if field.field_type == FieldType.ENUM:
        enum_type = field.enum_type or field.name
        enum_obj = model.enums.get(enum_type)
        if enum_obj:
            sch = {
                "type": "integer",
                "enum": [v.value for v in enum_obj.values],
                "enumNames": [v.name for v in enum_obj.values],
            }
            if field.is_array:
                return {"type": "array", "items": sch}
            if field.is_map:
                return {"type": "object", "additionalProperties": sch}
            return sch
        return {"type": "integer"}
    # Message reference
    if field.field_type == FieldType.MESSAGE_REFERENCE:
        ref = field.message_reference or field.name
        ref_schema = {"$ref": f"#/definitions/{ref}"}
        if field.is_array:
            return {"type": "array", "items": ref_schema}
        if field.is_map:
            return {"type": "object", "additionalProperties": ref_schema}
        return ref_schema
    # Compound
    if field.field_type == FieldType.COMPOUND:
        sch = {
            "type": "object",
            "properties": {c: {"type": "number"} for c in (field.compound_components or [])},
            "required": list(field.compound_components or []),
        }
        if field.is_array:
            return {"type": "array", "items": sch}
        if field.is_map:
            return {"type": "object", "additionalProperties": sch}
        return sch
    # Map (generic fallback)
    if field.field_type == FieldType.MAP:
        return {"type": "object", "additionalProperties": {"type": "object"}}
    # Unknown
    return {"type": "object"}

def write_json_schema_file(model: MessageModel, out_path):
    schema = generate_json_schema(model)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
