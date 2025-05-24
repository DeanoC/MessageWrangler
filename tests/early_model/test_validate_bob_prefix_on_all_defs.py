# Moved from validate_bob_prefix_on_all_defs.py
# This script validates that all names are correctly prefixed with 'BOB_' after transformation.

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from early_model_transforms.bob_prefix_transform import BobPrefixTransform
from early_transform_pipeline import run_early_transform_pipeline
from def_file_loader import load_def_file
import glob

def assert_bob_prefix(name):
    assert name.startswith('BOB_'), f"Name '{name}' is not prefixed with 'BOB_'"

def validate_model(model):
    # Validate namespaces
    for ns in model.namespaces:
        assert_bob_prefix(ns.name)
        # Validate messages
        for msg in ns.messages:
            assert_bob_prefix(msg.name)
            for field in msg.fields:
                assert_bob_prefix(field.name)
        # Validate enums
        for enum in ns.enums:
            assert_bob_prefix(enum.name)
            for value in enum.values:
                assert_bob_prefix(value.name)

def main():
    def_dir = os.path.join(os.path.dirname(__file__), 'def')
    if not os.path.exists(def_dir):
        def_dir = os.path.join(os.path.dirname(__file__), '..', 'tests', 'def')
    def_files = glob.glob(os.path.join(def_dir, '*.def'))
    for def_file in def_files:
        model = load_def_file(def_file)
        transformed = run_early_transform_pipeline(model, [BobPrefixTransform()])
        try:
            validate_model(transformed)
            print(f"PASS: {def_file}")
        except AssertionError as e:
            print(f"FAIL: {def_file} - {e}")
            raise

if __name__ == "__main__":
    main()
