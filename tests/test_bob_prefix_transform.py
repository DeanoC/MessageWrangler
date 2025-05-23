"""
test_bob_prefix_transform.py
Test that BobPrefixTransform adds 'BOB_' to all names in EarlyModel.
"""
import unittest
from early_model import EarlyModel, EarlyNamespace, EarlyMessage, EarlyEnum, EarlyEnumValue, EarlyField
from early_model_transforms.bob_prefix_transform import BobPrefixTransform
from early_transform_pipeline import run_early_transform_pipeline

class TestBobPrefixTransform(unittest.TestCase):
    def make_simple_model(self):
        # Create a simple EarlyModel with nested structures
        field = EarlyField(name="field1", type_name="int", file="f", namespace="ns", line=1, raw_type="int")
        msg = EarlyMessage(name="Msg1", fields=[field], file="f", namespace="ns", line=1)
        enum_val = EarlyEnumValue(name="VAL1", value=1, file="f", namespace="ns", line=1)
        enum = EarlyEnum(name="Enum1", values=[enum_val], file="f", namespace="ns", line=1)
        ns = EarlyNamespace(name="NS1", messages=[msg], enums=[enum], file="f", line=1)
        model = EarlyModel(namespaces=[ns], enums=[enum], messages=[msg], standalone_options=[], standalone_compounds=[], imports_raw=[], file="f")
        return model

    def test_bob_prefix_transform(self):
        model = self.make_simple_model()
        transform = BobPrefixTransform()
        out = run_early_transform_pipeline(model, [transform])
        # Check top-level message
        self.assertTrue(out.messages[0].name.startswith("BOB_"))
        # Check top-level enum
        self.assertTrue(out.enums[0].name.startswith("BOB_"))
        # Check field name
        self.assertTrue(out.messages[0].fields[0].name.startswith("BOB_"))
        # Check enum value name
        self.assertTrue(out.enums[0].values[0].name.startswith("BOB_"))
        # Check namespace name
        self.assertTrue(out.namespaces[0].name.startswith("BOB_"))
        # Check nested message in namespace
        self.assertTrue(out.namespaces[0].messages[0].name.startswith("BOB_"))
        # Check nested enum in namespace
        self.assertTrue(out.namespaces[0].enums[0].name.startswith("BOB_"))
        # Check nested enum value in namespace
        self.assertTrue(out.namespaces[0].enums[0].values[0].name.startswith("BOB_"))

if __name__ == "__main__":
    unittest.main()
