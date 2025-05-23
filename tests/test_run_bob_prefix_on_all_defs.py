# Moved from run_bob_prefix_on_all_defs.py
# This script runs BobPrefixTransform on all valid .def files in tests/def and prints the results.

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from early_model_transforms.bob_prefix_transform import BobPrefixTransform
from early_transform_pipeline import run_early_transform_pipeline
from def_file_loader import load_def_file
import glob

def main():
    def_dir = os.path.join(os.path.dirname(__file__), 'def')
    if not os.path.exists(def_dir):
        def_dir = os.path.join(os.path.dirname(__file__), '..', 'tests', 'def')
    def_files = glob.glob(os.path.join(def_dir, '*.def'))
    for def_file in def_files:
        model = load_def_file(def_file)
        transformed = run_early_transform_pipeline(model, [BobPrefixTransform()])
        print(f"\nFile: {def_file}")
        print(transformed)

if __name__ == "__main__":
    main()
