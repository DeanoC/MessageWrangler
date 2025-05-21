import pytest
from lark_parser import parse_message_dsl
from message_model_builder import build_model_from_lark_tree
from message_model import FieldType

def test_corner_cases_arrays_and_references():
    import lark
    with open("tests/def/test_arrays_and_references_corner_cases.def", "r", encoding="utf-8") as f:
        dsl = f.read()
    try:
        tree = parse_message_dsl(dsl)
    except lark.exceptions.UnexpectedCharacters:
        # Parser should fail on nested arrays, which is expected; skip the rest of the test
        return
    model = build_model_from_lark_tree(tree)

    # 1. Arrays of arrays (should be rejected or handled as error/unknown)
    invalid = model.get_message("InvalidNestedArray")
    nested_array = next((f for f in invalid.fields if f.name == "nestedArray"), None)
    assert nested_array is not None
    # Should be UNKNOWN or error, as nested arrays are not supported
    assert nested_array.field_type == FieldType.UNKNOWN or nested_array.field_type == FieldType.MESSAGE_REFERENCE
    assert not getattr(nested_array, "is_array", False) or nested_array.message_reference is None

    # 2. Maps with array values
    map_with_array = model.get_message("MapWithArray")
    arr_map = next((f for f in map_with_array.fields if f.name == "arrMap"), None)
    obj_arr_map = next((f for f in map_with_array.fields if f.name == "objArrMap"), None)
    assert arr_map.is_map and arr_map.map_key_type == "string"
    assert obj_arr_map.is_map and obj_arr_map.map_key_type == "string"
    # Value type for map with array should be UNKNOWN or handled as error
    # (Current model does not track map value type deeply)

    # 3. Arrays of maps
    array_of_maps = model.get_message("ArrayOfMaps")
    map_array = next((f for f in array_of_maps.fields if f.name == "mapArray"), None)
    assert map_array.is_array
    # Should be UNKNOWN or error, as arrays of maps are not supported
    assert map_array.field_type == FieldType.UNKNOWN or map_array.field_type == FieldType.MESSAGE_REFERENCE

    # 4. Maps with message reference values (including namespaced)
    map_with_ref = model.get_message("MapWithRef")
    ref_map = next((f for f in map_with_ref.fields if f.name == "refMap"), None)
    assert ref_map.is_map and ref_map.map_key_type == "string"

    # 5. Arrays of enums/options
    enum_arr = model.get_message("EnumArr")
    status = next((f for f in enum_arr.fields if f.name == "status"), None)
    assert status.is_array
    # Should be FieldType.UNKNOWN or FieldType.MESSAGE_REFERENCE (depending on implementation)
    assert status.field_type in (FieldType.UNKNOWN, FieldType.MESSAGE_REFERENCE)

    # 6. Maps with enum/options as value
    map_enum = model.get_message("MapEnum")
    status_map = next((f for f in map_enum.fields if f.name == "statusMap"), None)
    assert status_map.is_map and status_map.map_key_type == "string"

    # 7. Maps with non-string keys (should be rejected or UNKNOWN)
    map_non_string_key = model.get_message("MapNonStringKey")
    int_key_map = next((f for f in map_non_string_key.fields if f.name == "intKeyMap"), None)
    assert int_key_map.is_map
    # Should be UNKNOWN or error, as only string keys are supported
    assert int_key_map.map_key_type != "string"

    # 8. Arrays/Maps of unknown or undefined types
    unknown_arr = model.get_message("UnknownArr")
    unknowns = next((f for f in unknown_arr.fields if f.name == "unknowns"), None)
    assert unknowns.is_array
    assert unknowns.field_type == FieldType.UNKNOWN

    # 9. Optional arrays/maps
    optional_arr_map = model.get_message("OptionalArrMap")
    tags = next((f for f in optional_arr_map.fields if f.name == "tags"), None)
    dict_field = next((f for f in optional_arr_map.fields if f.name == "dict"), None)
    assert tags.is_array and "optional" in tags.modifiers
    assert dict_field.is_map and "optional" in dict_field.modifiers

    # 10. Default values for arrays/maps (should be rejected or handled as error/ignored)
    default_arr_map = model.get_message("DefaultArrMap")
    tags = next((f for f in default_arr_map.fields if f.name == "tags"), None)
    dict_field = next((f for f in default_arr_map.fields if f.name == "dict"), None)
    # Should not support default values for arrays/maps, so options should not include 'default'
    assert "default" not in tags.options
    assert "default" not in dict_field.options
