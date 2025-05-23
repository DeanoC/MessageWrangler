"""
test_early_transform_pipeline.py
Unit tests for the EarlyModel transform pipeline.
"""
import unittest
from early_model import EarlyModel
from early_transform_pipeline import run_early_transform_pipeline, EarlyTransform

class DummyTransform:
    def __init__(self, tag):
        self.tag = tag
    def transform(self, model: EarlyModel) -> EarlyModel:
        # Add a dummy attribute for test purposes
        setattr(model, f"_dummy_{self.tag}", True)
        return model

class TestEarlyTransformPipeline(unittest.TestCase):
    def test_pipeline_applies_all_transforms(self):
        # Minimal EarlyModel for testing
        model = EarlyModel([], [], [], [], [], [], "dummy_file")
        transforms = [DummyTransform("a"), DummyTransform("b")]
        result = run_early_transform_pipeline(model, transforms)
        self.assertTrue(hasattr(result, "_dummy_a"))
        self.assertTrue(hasattr(result, "_dummy_b"))
        self.assertIs(result, model)  # Should be the same object if transforms mutate in place

if __name__ == "__main__":
    unittest.main()
