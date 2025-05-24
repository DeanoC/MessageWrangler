from model import ModelReference, Model, ModelNamespace, ModelMessage

def test_model_reference_resolution():
    # Create a simple model with two messages, one inheriting from the other
    base_msg = ModelMessage(name="Base", fields=[], parent=None)
    child_ref = ModelReference(qfn="TestNS::Base", kind="message")
    child_msg = ModelMessage(name="Child", fields=[], parent=child_ref)
    ns = ModelNamespace(name="TestNS", messages=[base_msg, child_msg], enums=[])
    model = Model(file="test.def", namespaces=[ns])
    # Should resolve child_msg.parent to base_msg
    resolved = model.resolve_reference(child_msg.parent)
    assert resolved is base_msg, f"Expected to resolve to base_msg, got {resolved}"
    # Should return None for non-existent reference
    bad_ref = ModelReference(qfn="TestNS::DoesNotExist", kind="message")
    assert model.resolve_reference(bad_ref) is None
