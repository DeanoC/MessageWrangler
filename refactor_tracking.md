# Refactor Tracking for MessageWrangler Model Builder Split

## Outstanding Tasks

1. **Remove `build_model_from_file_recursive` from `def_file_loader.py`**
   - Ensure all references in the codebase import it from `def_file_loader.py` instead.
   - Clean up any related helper code or comments.

2. **Update Tests**
   - Update any test files or test utilities that import or call `build_model_from_file_recursive` to use the new module path (`def_file_loader.py`).
   - Run all tests to confirm correct import and behavior.

3. **Namespace/FQN Resolution Split**
   - Moved `resolve_reference_hierarchically` to `namespace_resolver.py` as a top-level function.
   - Updated `def_file_loader.py` to import and use it from `namespace_resolver.py`.
   - Check for any other usages in the codebase and update imports if found.

4. **Model Flattening and Debugging**
   - Model flattening logic has been moved to `model_flatten.py` as `flatten_model_for_generation`.
   - `def_file_loader.py` now calls this at the end of model building.
   - Next: Add a pretty-print/debug dump step in a new module (e.g., `model_debug.py`).
   - Ensure these are called from the main builder as needed.

5. **Documentation**
   - Update or add documentation to reflect the new module structure and usage.

---
Add to this file as new refactor steps or reminders arise.
