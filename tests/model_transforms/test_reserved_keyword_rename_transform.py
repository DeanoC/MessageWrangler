import pytest
from model import Model, ModelNamespace, ModelMessage, ModelEnum, ModelField, FieldType
from model_transforms.reserved_keyword_rename_transform import ReservedKeywordRenameTransform

def make_simple_model():
    # Create a model with reserved keywords as names
    ns = ModelNamespace(
        name="TestNS",
        messages=[
            ModelMessage(
                name="class",
                fields=[
                    ModelField(
                        name="def",
                        field_types=[FieldType.STRING],
                        type_refs=[None],
                        type_names=["string"]
                    ),
                    ModelField(
                        name="normal",
                        field_types=[FieldType.INT],
                        type_refs=[None],
                        type_names=["int"]
                    )
                ]
            ),
            ModelMessage(
                name="normal",
                fields=[]
            )
        ],
        enums=[
            ModelEnum(
                name="return",
                values=[]
            ),
            ModelEnum(
                name="normal",
                values=[]
            )
        ],
        namespaces=[]
    )
    return Model(
        file="test.def",
        namespaces=[ns],
        options=[],
        compounds=[],
        alias_map={},
        imports={}
    )

def test_reserved_keyword_rename_transform():
    reserved = {"class", "def", "return"}
    prefix = "py_"
    model = make_simple_model()
    transform = ReservedKeywordRenameTransform(reserved, prefix)
    model = transform.transform(model)
    ns = model.namespaces[0]
    # Message names
    assert ns.messages[0].name == "py_class"
    assert ns.messages[1].name == "normal"
    # Field names
    assert ns.messages[0].fields[0].name == "py_def"
    assert ns.messages[0].fields[1].name == "normal"
    # Enum names
    assert ns.enums[0].name == "py_return"
    assert ns.enums[1].name == "normal"
