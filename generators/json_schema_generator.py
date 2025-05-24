"""
JSON Schema generator for MessageModel.
Generates a valid JSON Schema (Draft 7+) for all messages, enums, and options in the model.
"""
import json

from model import Model, FieldType
from typing import List, Callable
from model_transforms.flatten_imports_transform  import FlattenImportsTransform

BASIC_TYPE_TO_JSON = {
    FieldType.STRING: "string",
    FieldType.INT: "integer",
    FieldType.FLOAT: "number",
    FieldType.BOOL: "boolean",
}


def generate_json_schema(model: Model, title="Message Definitions", description="JSON schema for message definitions", transforms: List[Callable] = None):
    # Apply model transforms if any
    transforms = transforms or []
    transforms.insert(0, FlattenImportsTransform())
    for transform in transforms:
        model = transform(model)

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": title,
        "description": description,
        "definitions": {},
    }
    # Traverse all namespaces, messages, enums
    for ns in model.namespaces:
        # Enums
        for enum in getattr(ns, 'enums', []):
            enum_def = {
                "type": "integer",
                "description": getattr(enum, 'doc', None) or getattr(enum, 'comment', None) or enum.name,
                "enum": [v.value for v in getattr(enum, 'values', [])],
                "enumNames": [v.name for v in getattr(enum, 'values', [])],
            }
            schema["definitions"][enum.name] = enum_def
        # Messages
        for msg in getattr(ns, 'messages', []):
            msg_def = {
                "type": "object",
                "description": getattr(msg, 'doc', None) or getattr(msg, 'comment', None) or msg.name,
                "properties": {},
                "required": [],
            }
            for field in getattr(msg, 'fields', []):
                field_schema = field_to_json_schema(field, model)
                msg_def["properties"][field.name] = field_schema
                if not hasattr(field, 'modifiers') or "optional" not in [str(m).lower() for m in getattr(field, 'modifiers', [])]:
                    msg_def["required"].append(field.name)
            if not msg_def["required"]:
                del msg_def["required"]
            schema["definitions"][msg.name] = msg_def
    return schema

def field_to_json_schema(field, model):
    # Use the first field type as the primary type
    ftype = field.field_types[0] if hasattr(field, 'field_types') and field.field_types else None
    # Array
    if ftype == FieldType.ARRAY and len(field.field_types) > 1:
        element_type = field.field_types[1]
        fake_field = type('FakeField', (), dict(
            field_types=[element_type],
            type_names=field.type_names[1:] if hasattr(field, 'type_names') else [],
            name=getattr(field, 'name', None),
            inline_values=getattr(field, 'inline_values', []),
            compound_components=getattr(field, 'compound_components', [])
        ))
        return {"type": "array", "items": field_to_json_schema(fake_field, model)}
    # Map
    if ftype == FieldType.MAP and len(field.field_types) > 2:
        value_type = field.field_types[2]
        fake_field = type('FakeField', (), dict(
            field_types=[value_type],
            type_names=field.type_names[2:] if hasattr(field, 'type_names') else [],
            name=getattr(field, 'name', None),
            inline_values=getattr(field, 'inline_values', []),
            compound_components=getattr(field, 'compound_components', [])
        ))
        return {"type": "object", "additionalProperties": field_to_json_schema(fake_field, model)}
    # Basic types
    if ftype in BASIC_TYPE_TO_JSON:
        sch = {"type": BASIC_TYPE_TO_JSON[ftype]}
        return sch
    # Enum
    if ftype == FieldType.ENUM:
        enum_names = [v.name for v in getattr(field, 'inline_values', [])]
        enum_values = [v.value for v in getattr(field, 'inline_values', [])]
        sch = {
            "type": "integer",
            "enum": enum_values,
            "enumNames": enum_names,
        }
        return sch
    # Message reference
    if ftype == FieldType.MESSAGE:
        ref = field.type_names[0] if hasattr(field, 'type_names') and field.type_names else field.name
        ref_schema = {"$ref": f"#/definitions/{ref}"}
        return ref_schema
    # Compound
    if ftype == FieldType.COMPOUND:
        sch = {
            "type": "object",
            "properties": {c: {"type": "number"} for c in (field.compound_components or [])},
            "required": list(field.compound_components or []),
        }
        return sch
    # Unknown
    return {"type": "object"}

def write_json_schema_file(model: Model, out_path):
    schema = generate_json_schema(model)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
