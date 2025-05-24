# Copilot Instructions for the Project
We use a strict test-first design development process. This means that you should always write tests before writing the code that implements the functionality.
The tests should be written in the same file as the code, and they should be clearly marked as tests. The tests should be written in a way that they can be run automatically, and they should cover all the functionality of the code.

The processing pipelines consists of the following steps:
1. lark_parser - input is .def files
2. load_early_model_with_imports - loads .def files into the EarlyModel
3. early_model to model conversion - converts the EarlyModel to the final Model
4. generators - generates output from the Model

** Example of correct loading and processing of main.def:
```python
    early_main, all_early_models = load_early_model_with_imports(main_path)
    model_main = EarlyModelToModelTransform().transform(early_main)

```

Once a Model is created, it the input to the generators.

# Generators
1. (TODO) json_schema_generator - generates JSON schema from the Model (this is used for validation)
2. (TODO) python_generator - generates Python code from the Model
3. (TODO) typescript_generator - generates TypeScript code from the Model
4. (TODO) C++ generator - generates C++ code from the Model has several variants:
   - (TODO) C++ std20 - generates C++ source files using C++20 features
   - (TODO) C++ unreal5 - generates C++ source files for Unreal Engine 5


When debugging, always challenge your assumptions. Verify that the input where the error happens is valid. Use prior test and debug print to validate you are getting what you think you shoulld.