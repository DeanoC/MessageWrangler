def test_message_inheritance_from_non_message_type_fails_model_building():
    """
    Tests that attempting to inherit a message from a non-existent message
    (e.g., a C++ type name like 'int16' used in the DSL inheritance syntax)
    causes model building to fail, as 'int16' is not a valid message reference.
    """
    dsl_content = """
    namespace TestInvalidParent {
        message MyMessage : int16 { // 'int16' is not a defined message in the DSL
            value: int;
        }
    }
    """
    # Create a temporary .def file
    with tempfile.TemporaryDirectory() as tmpdir:
        def_path = os.path.join(tmpdir, "invalid_message_parent.def")
        with open(def_path, "w", encoding="utf-8") as f:
            f.write(dsl_content)

        # Expect a RuntimeError (or a more specific error if defined by the model builder)
        # when it tries to resolve 'int16' as a parent message.
        expected_error_pattern = (
            r"Cannot resolve parent message 'int16' for message '([\w:]+::)?MyMessage'|"
            r"Unresolved parent message 'int16' for '([\w:]+::)?MyMessage'"
        )
        with pytest.raises(RuntimeError, match=expected_error_pattern):
            build_model_from_file_recursive(def_path)
def test_cpp_generator_std23_emits_field_enum():
    """
    Ensure that if a message field uses an enum type (inline or referenced),
    the generated C++ header emits the corresponding enum declaration.
    """
    import tempfile
    from def_file_loader import build_model_from_file_recursive
    from generators.cpp_generator_std23 import CppGeneratorStd23
    # Create a .def file with a message and an inline enum field
    dsl = '''
namespace TestNS {
    enum CommandType {
        FOO = 0;
        BAR = 1;
    }
    message Command {
        type: CommandType;
    }
}
'''
    with tempfile.TemporaryDirectory() as tmpdir:
        def_path = os.path.join(tmpdir, "test_enum.def")
        with open(def_path, "w", encoding="utf-8") as f:
            f.write(dsl)
        model = build_model_from_file_recursive(def_path)
        model.main_file_path = def_path
        gen = CppGeneratorStd23([model], model=model)
        header_map = gen.generate_header()
        # There should be only one header
        assert len(header_map) == 1
        header_content = list(header_map.values())[0]
        # The header should contain the enum declaration for CommandType
        import re
        enum_decl = re.search(r'enum class (CommandType|CommandType_Enum)\b', header_content)
        assert enum_decl, (
            "Generated header does not contain the expected enum declaration for CommandType.\n" +
            header_content
        )
        # The struct should use the correct enum type for the field
        assert re.search(r'CommandType(_Enum)?\s+type;', header_content), (
            "Struct Command does not use the expected enum type for field 'type'.\n" +
            header_content
        )
def test_cpp_generator_std23_namespace_struct_name_collision():
    """
    Ensure that if a namespace and a struct/message have the same name (e.g., 'Base'),
    the generated C++ code does not emit both a namespace and a struct/class with the same name,
    which would cause a C++ compiler error (C2757).
    """
    import tempfile
    from def_file_loader import build_model_from_file_recursive
    from generators.cpp_generator_std23 import CppGeneratorStd23
    # Create a .def file with a namespace and a message both named 'Base'
    dsl = '''
namespace Base {
    message Base {
        id: int;
    }
}
'''
    with tempfile.TemporaryDirectory() as tmpdir:
        def_path = os.path.join(tmpdir, "base.def")
        with open(def_path, "w", encoding="utf-8") as f:
            f.write(dsl)
        model = build_model_from_file_recursive(def_path)
        model.main_file_path = def_path
        gen = CppGeneratorStd23([model], model=model)
        header_map = gen.generate_header()
        # There should be only one header
        assert len(header_map) == 1
        header_content = list(header_map.values())[0]
        # The header should not contain both 'namespace Base {' and 'struct Base' at the same scope
        # (which would cause a C++ name collision)
        # Instead, the struct should be disambiguated (e.g., prefixed or renamed)
        # Check for the problematic pattern:
        import re
        ns_match = re.search(r'namespace\s+Base\s*{', header_content)
        struct_match = re.search(r'struct\s+Base\b', header_content)
        assert not (ns_match and struct_match), (
            "Generated header contains both 'namespace Base' and 'struct Base', which will cause a C++ name collision.\n" +
            header_content
        )
        # Optionally, check that the struct is renamed or prefixed (e.g., 'mw_Base' or similar)
        # Accept either no struct, or a struct with a different name
        if ns_match:
            # If namespace Base exists, struct Base should not exist
            assert not struct_match, (
                "Struct 'Base' should not be emitted inside namespace 'Base' due to name collision.\n" +
                header_content
            )
        # If struct Base exists, namespace Base should not exist (should be renamed)
        if struct_match:
            assert not ns_match, (
                "Namespace 'Base' should not be emitted if struct 'Base' exists at the same scope.\n" +
                header_content
            )
import glob
import os
import pytest
def get_def_files():
    all_defs = glob.glob(os.path.join("tests", "def", "*.def"))
    invalid = {
        "test_invalid.def",
        "test_duplicate_fields.def",
        "test_arrays_and_references_corner_cases.def",
        "test_unresolved.def",
    }
    return [f for f in all_defs if os.path.basename(f) not in invalid]

# Test: All generated header files have the correct filename (not messages_std23.h except for messages.def)
@pytest.mark.parametrize("def_path", get_def_files())
def test_cpp_generator_std23_header_filenames(def_path):
    from def_file_loader import build_model_from_file_recursive
    from generators.cpp_generator_std23 import CppGeneratorStd23
    model = build_model_from_file_recursive(def_path)
    model.main_file_path = def_path
    gen = CppGeneratorStd23([model], model=model)
    header_map = gen.generate_header()
    base_filename = os.path.splitext(os.path.basename(def_path))[0]
    # Use the generator's sanitization logic
    sanitized_ns = gen._sanitize_identifier(base_filename, for_namespace=True)
    expected_header = f"{sanitized_ns}_std23.h"
    # All headers generated for this file (including imports) should have correct names
    for header_name in header_map.keys():
        # Allow 'messages_std23.h' only if the .def file is actually messages.def
        if header_name == "messages_std23.h":
            assert base_filename == "messages", f"Header {header_name} generated for {def_path}, but file is not messages.def"
        else:
            assert header_name.endswith("_std23.h"), f"Header {header_name} does not end with _std23.h"
            # The main header for this file should match expected_header
            if base_filename != "messages":
                assert expected_header in header_map, f"Expected header {expected_header} not found in generated headers for {def_path}: {list(header_map.keys())}"
def test_cpp_generator_std23_no_fake_std_includes():
    """
    Ensure that the generator does NOT emit #include directives for non-existent or built-in namespaces like 'std_std23.h'.
    This test will fail if any generated header includes a header for a namespace/file that is not actually imported or defined.
    """
    import tempfile
    import os
    from def_file_loader import build_model_from_file_recursive
    from generators.cpp_generator_std23 import CppGeneratorStd23
    # Create a .def file with a message using only built-in types
    dsl = '''
namespace Tool {
    message Command {
        id: int;
        name: string;
    }
}
'''
    with tempfile.TemporaryDirectory() as tmpdir:
        def_path = os.path.join(tmpdir, "tool.def")
        with open(def_path, "w", encoding="utf-8") as f:
            f.write(dsl)
        model = build_model_from_file_recursive(def_path)
        model.main_file_path = def_path
        gen = CppGeneratorStd23([model], model=model)
        header_map = gen.generate_header()
        for header_name, content in header_map.items():
            # Should not include any #include "std_std23.h" or similar
            assert 'include "std_std23.h"' not in content, f"Header {header_name} incorrectly includes std_std23.h!\n---\n{content}\n---"
            # Should not include any #include for non-imported namespaces
            # (We only expect includes for actu`al imports, but this file has none)
            for line in content.splitlines():
                if line.strip().startswith('#include "') and line.strip().endswith('_std23.h"'):
                    inc = line.strip().split('"')[1]
                    assert inc == f"tool_std23.h", f"Header {header_name} includes unexpected header: {inc}\n---\n{content}\n---"
def test_cpp_generator_std23_cross_namespace_include():
    """
    Test that a header includes the correct #include for a referenced namespace even if not explicitly imported.
    """
    import tempfile
    # Create two .def files: base.def and main.def
    base_def = '''
namespace Base {
    message BaseMessage {
        baseField: string;
    }
}
'''
    main_def = '''
import "base.def" as Base

namespace Main {
    message MainMessage : Base::BaseMessage {
        mainField: string;
    }
}
'''
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = os.path.join(tmpdir, "base.def")
        main_path = os.path.join(tmpdir, "main.def")
        with open(base_path, "w", encoding="utf-8") as f:
            f.write(base_def)
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(main_def)
        # Build models
        from def_file_loader import build_model_from_file_recursive
        from generators.cpp_generator_std23 import CppGeneratorStd23
        base_model = build_model_from_file_recursive(base_path)
        base_model.main_file_path = base_path
        main_model = build_model_from_file_recursive(main_path)
        main_model.main_file_path = main_path
        # Generate header for main.def
        gen = CppGeneratorStd23([main_model], model=main_model)
        header_map = gen.generate_header()
        print(f"Generated headers: {list(header_map.keys())}")
        # Use the only header that is not the base header
        for k in header_map:
            if k != "base_std23.h":
                main_header = header_map[k]
                break
        else:
            raise AssertionError(f"No main header found in generated headers: {list(header_map.keys())}")
        print("\n==== main header content ====")
        print(main_header)
        print("===========================\n")
        # The header should include base_std23.h because MainMessage inherits from Base::BaseMessage
        assert '#include "base_std23.h"' in main_header, f"Expected #include for base namespace in main header:\n{main_header}"
        # The struct should inherit from Base::BaseMessage
        assert 'struct MainMessage : public Base::BaseMessage' in main_header, f"Expected MainMessage struct with base class in header:\n{main_header}"
import os
import glob
import tempfile
import pytest
import re

from lark_parser import parse_message_dsl
from def_file_loader import build_model_from_file_recursive
from generators.cpp_generator_std23 import CppGeneratorStd23, CppGeneratorBase


def get_def_files():
    all_defs = glob.glob(os.path.join("tests", "def", "*.def"))
    invalid = {
        "test_invalid.def",
        "test_duplicate_fields.def",
        "test_arrays_and_references_corner_cases.def",
        "test_unresolved.def",
    }
    return [f for f in all_defs if os.path.basename(f) not in invalid]

def _sanitize_cpp_identifier(name: str) -> str:
    """Sanitizes a name to be a valid C++ identifier, prefixing if it's a reserved keyword."""
    # This helper is for test expectations; the generator uses its own _sanitize_identifier.
    sanitized = str(name)
    if sanitized in CppGeneratorBase.CPP_RESERVED_KEYWORDS: # Accessing from the generator base
        sanitized = f"mw_{sanitized}" # Match generator's prefixing for reserved keywords
    return sanitized.replace("-", "_").replace(".", "_") # Basic char replacement


@pytest.mark.parametrize("def_path", get_def_files())
def test_cpp_generator_std23_namespace_coverage(def_path):


    model = build_model_from_file_recursive(def_path)
    model.main_file_path = def_path
    namespaces = [model] if not hasattr(model, 'namespaces') else list(model.namespaces.values())
    gen = CppGeneratorStd23(namespaces, model=model)
    header_map = gen.generate_header()

    print(f"[DEBUG] Generated headers: {list(header_map.keys())}")
    # For each header, check that it contains a namespace and at least one struct/enum if applicable
    for header_name, content in header_map.items():
        print(f"\n[GENERATED HEADER: {header_name}]\n{content}\n[END HEADER]\n")
        # Check that the header contains a namespace declaration
        ns_match = None
        import re
        m = re.search(r'namespace\s+([a-zA-Z0-9_]+)\s*{', content)
        if m:
            ns_match = m.group(1)
        assert ns_match, f"No namespace found in header {header_name}\n---\n{content}\n---"
        # Check that at least one struct or enum is present (unless header is intentionally empty)
        has_struct = 'struct ' in content
        has_enum = 'enum ' in content
        assert has_struct or has_enum, f"No struct or enum found in header {header_name}\n---\n{content}\n---"

    # Special check for main.def: ensure the main header contains MainMessage and DerivedMessage (no FQN required)
    if os.path.basename(def_path) == "main.def":
        base_filename = os.path.splitext(os.path.basename(def_path))[0]
        sanitized_ns = CppGeneratorBase(namespaces=namespaces)._sanitize_identifier(base_filename, for_namespace=True)
        main_header_name = f"{sanitized_ns}_std23.h"
        assert main_header_name in header_map, f"Expected main header '{main_header_name}' not found in generated headers: {list(header_map.keys())}"
        content = header_map[main_header_name]
        assert "struct MainMessage" in content, f"MainMessage struct not found in generated {main_header_name}:\n---\n{content}\n---"
        assert "struct DerivedMessage" in content, f"DerivedMessage struct not found in generated {main_header_name}:\n---\n{content}\n---"
        assert f"namespace {sanitized_ns}" in content, f"Expected namespace '{sanitized_ns}' not found in generated {main_header_name}:\n---\n{content}\n---"
        # The header should not be empty inside the namespace
        inner = content.split(f"namespace {sanitized_ns}", 1)[1].split("}", 1)[0]
        assert inner.strip(), f"Generated {sanitized_ns} namespace is empty in {main_header_name}:\n---\n{content}\n---"

def test_cpp_generator_std23_cross_file_includes_and_references():
    """
    Fast test: Ensure that when a .def file imports/includes another, the generated header contains the correct #include and references.
    Uses sh4c_comms.def (which imports sh4c_base.def) as a concrete example.
    """
    import re
    from def_file_loader import build_model_from_file_recursive
    def_path = os.path.join("tests", "def", "sh4c_comms.def")
    model = build_model_from_file_recursive(def_path)
    model.main_file_path = def_path  # Ensure correct header naming
    if hasattr(model, 'namespaces'):
        namespaces = list(model.namespaces.values())
    else:
        namespaces = [model]
    gen = CppGeneratorStd23(namespaces, model=model)
    header_map = gen.generate_header()
    # The header should be named after the .def base name (sh4c_comms_std23.h)
    def_base = os.path.splitext(os.path.basename(def_path))[0]
    expected_header_name = f"{CppGeneratorBase(namespaces=namespaces)._sanitize_identifier(def_base, for_namespace=True)}_std23.h"
    assert expected_header_name in header_map, f"No {expected_header_name} header generated. Got: {list(header_map.keys())}"
    content = header_map[expected_header_name]
    # Check that it includes the Base header (from sh4c_base.def)
    assert re.search(r'#include\s+"sh4c_base_std23.h"', content), f"Expected #include for sh4c_base_std23.h in {expected_header_name}\n---\n{content}\n---"
    # Check that types from Base (e.g., Base::Command, Base::Reply) are referenced in the generated code
    assert re.search(r'struct\s+CommCommand\s*:\s*public\s+Base::Command', content), f"CommCommand should inherit from Base::Command in {expected_header_name}\n---\n{content}\n---"
    assert re.search(r'struct\s+ChangeModeReply\s*:\s*public\s+Base::Reply', content), f"ChangeModeReply should inherit from Base::Reply in {expected_header_name}\n---\n{content}\n---"
    # Enum inheritance is not supported in C++: the generator should flatten enums, not inherit.
    # So we do NOT expect 'enum class Command : Base::Command::type' or similar in the output.
    # Instead, just check that the Command enum is present and well-formed.
    assert re.search(r'enum class Command(_Enum)?\s*:\s*uint(8|16|32|64)_t', content), (
        f"Enum Command or Command_Enum should be present and use a fixed underlying type in {expected_header_name}\n---\n{content}\n---"
    )


@pytest.mark.parametrize("def_path", get_def_files())
def test_cpp_generator_std23_header(def_path):

    # Parse DSL and build model
    model = build_model_from_file_recursive(def_path)
    model.main_file_path = def_path
    namespaces = [model]

    # Always expect a single header named after the .def file
    base_filename = os.path.splitext(os.path.basename(def_path))[0]
    sanitized_ns = CppGeneratorBase(namespaces=namespaces)._sanitize_identifier(base_filename, for_namespace=True)
    gen = CppGeneratorStd23(namespaces, model=model)
    header_map = gen.generate_header()
    print(f"Generated headers: {list([header_map.keys(), header_map.values()])}")

    # Helper to get the header name for a namespace/model
    def get_header_name_for_ns(ns):
        # For pseudo-namespaces (imported), always use the base name of main_file_path, not the alias
        if hasattr(ns, "main_file_path") and ns.main_file_path:
            ns_base = os.path.splitext(os.path.basename(ns.main_file_path))[0]
        else:
            ns_base = getattr(ns, "name", None) or ""
        sanitized = CppGeneratorBase(namespaces=[ns])._sanitize_identifier(ns_base, for_namespace=True)
        return f"{sanitized}_std23.h"

    # Build header_expected for each header, not just the main one
    header_expected = {}

    def collect_for_ns(ns, root_model):
        header = get_header_name_for_ns(ns)
        print(f"[DEBUG] collect_for_ns: header={header} in header_map={header in header_map}")
        if header not in header_map:
            return
        if header not in header_expected:
            header_expected[header] = {"messages": set(), "enums": set(), "docs": set()}
        ns_name = getattr(ns, 'name', None)
        for msg in getattr(ns, 'messages', {}).values():
            # Only add messages that are defined in this namespace (not just imported for reference)
            if (getattr(msg, 'namespace', None) == ns_name) or (ns_name is None and not getattr(msg, 'namespace', None)):
                header_expected[header]["messages"].add(msg.name)
                if getattr(msg, 'description', None):
                    header_expected[header]["docs"].add(msg.description.strip())
                for field in getattr(msg, 'fields', []):
                    if getattr(field, 'description', None):
                        header_expected[header]["docs"].add(field.description.strip())
        for enum in getattr(ns, 'enums', {}).values():
            # Only add enums that are defined in this namespace (not just imported for reference)
            if (getattr(enum, 'namespace', None) == ns_name) or (ns_name is None and not getattr(enum, 'namespace', None)):
                header_expected[header]["enums"].add(enum.name)
                if getattr(enum, 'description', None):
                    header_expected[header]["docs"].add(enum.description.strip())
        # Recursively collect for sub-namespaces
        for subns in getattr(ns, 'namespaces', {}).values():
            collect_for_ns(subns, root_model)
        # Recursively collect for imports: load the full model for each import, matching the generator's logic
        if hasattr(ns, 'imports') and getattr(ns, 'imports'):
            from def_file_loader import build_model_from_file_recursive
            for imported_ns, imported_path in ns.imports.items():
                try:
                    imported_model = build_model_from_file_recursive(imported_path)
                    imported_model.main_file_path = imported_path  # Ensure correct header naming in test
                    collect_for_ns(imported_model, imported_model)
                except Exception as e:
                    print(f"[TEST WARNING] Could not load imported model for {imported_path}: {e}")
    collect_for_ns(model, model)
    import pprint
    print("header_expected (detailed):")
    pprint.pprint(header_expected)
    # --- Check each header contains its expected messages/enums/docs, and not those from other headers ---
    for header_name, content in header_map.items():
        expected = header_expected.get(header_name, {"messages": set(), "enums": set(), "docs": set()})
        # Only check for messages/enums/docs that are defined in this header's namespace/model
        # Do not require imported messages to appear in the main header
        for msg_name in expected["messages"]:
            assert f"struct {msg_name}" in content, f"Message struct '{msg_name}' missing from header {header_name}\n---\n{content}\n---"
        for other_header, other_expected in header_expected.items():
            if other_header == header_name:
                continue
            for msg_name in other_expected["messages"]:
                # Only assert absence if this message is not expected in this header
                if msg_name not in expected["messages"]:
                    assert f"struct {msg_name}" not in content, f"Message struct '{msg_name}' should NOT be in header {header_name} (belongs in {other_header})\n---\n{content}\n---"
        # Enums: only check for enums defined in this header
        for enum_name in expected["enums"]:
            flat_enum_name = enum_name.replace('::', '_')
            has_flat_enum = flat_enum_name in content
            has_flat_enum_with_suffix = f"{flat_enum_name}_Enum" in content
            has_enum_class = f"enum class {flat_enum_name}_Enum" in content
            assert has_flat_enum or has_flat_enum_with_suffix or has_enum_class, \
                f"Enum '{enum_name}' (flattened: '{flat_enum_name}_Enum') not found in header {header_name}\n---\n{content}\n---"
        for other_header, other_expected in header_expected.items():
            if other_header == header_name:
                continue
            for enum_name in other_expected["enums"]:
                flat_enum_name = enum_name.replace('::', '_')
                assert flat_enum_name not in content and f"{flat_enum_name}_Enum" not in content, \
                    f"Enum '{enum_name}' should NOT be in header {header_name} (belongs in {other_header})\n---\n{content}\n---"
        # Docs: only check for docs defined in this header
        for doc in expected["docs"]:
            if doc and doc.startswith("///"):
                assert doc in content, f"Doc comment '{doc}' not found in header {header_name}\n---\n{content}\n---"
        for other_header, other_expected in header_expected.items():
            if other_header == header_name:
                continue
            for doc in other_expected["docs"]:
                if doc and doc.startswith("///"):
                    assert doc not in content, f"Doc comment '{doc}' should NOT be in header {header_name} (belongs in {other_header})\n---\n{content}\n---"

    # --- Check includes as before, only for the main header ---
    with open(def_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    expected_imports = []
    for line in lines:
        m = re.match(r'\s*import\s+"([^"]+)"\s+as\s+([A-Za-z_][A-ZaZ0-9_]*)', line)
        if m:
            imported_path, _ = m.groups() # Alias not needed for include check here
            imported_base = os.path.splitext(os.path.basename(imported_path))[0]
            expected_imports.append(f"#include \"{imported_base}_std23.h\"")

    main_header_name = f"{sanitized_ns}_std23.h"
    main_content = header_map[main_header_name]
    for inc in expected_imports:
        assert inc in main_content, f"Expected {inc} in {main_header_name} for import in {def_path}\n---\n{main_content}\n---"
    # Allow includes for referenced namespaces, not just explicit imports

    # --- Additional check: Ensure base classes are defined before derived classes in each header ---
    for header_name, content in header_map.items():
        struct_defs = [(m.group(1), m.start()) for m in re.finditer(r'struct\s+(\w+)', content)]
        struct_order = {name: idx for idx, (name, _) in enumerate(struct_defs)}
        # Find the ns/model for this header
        ns = None
        for candidate_ns in [model] + list(getattr(model, 'namespaces', {}).values()):
            if get_header_name_for_ns(candidate_ns) == header_name:
                ns = candidate_ns
                break
        if ns is None:
            continue
        for msg in getattr(ns, 'messages', {}).values():
            parent = getattr(msg, 'parent', None)
            if parent and msg.name in struct_order and parent in struct_order:
                assert struct_order[parent] < struct_order[msg.name], (
                    f"Base class '{parent}' for message '{msg.name}' is not defined before the derived class in {header_name}\n---\n{content}\n---"
                )

@pytest.mark.parametrize("def_path", get_def_files())
def test_cpp_generator_std23_source(def_path):
    model = build_model_from_file_recursive(def_path)
    if hasattr(model, 'namespaces'):
        namespaces = list(model.namespaces.values())
    else:
        namespaces = [model]
    gen = CppGeneratorStd23(namespaces, model=model)
    code_map = gen.generate_source()
    # For the current set of .def files (assumed to be POD/enum-only or simple enough for header-only generation),
    # no .cpp files are expected. If the generator's capabilities expand or new complex .def files are added,
    # this test (or new tests) would need to verify .cpp file content.
    assert not code_map, f"Expected no .cpp files for '{def_path}' (assuming it's POD/enum-only or header-only), but got: {list(code_map.keys())}"

def collect_all_messages(model, seen=None):
    if seen is None:
        seen = set()
    expected_msgs = {}
    if id(model) in seen:
        return expected_msgs
    seen.add(id(model))
    # Collect messages from this model
    for msg in getattr(model, 'messages', {}).values():
        msg_name = msg.name
        field_names = [f.name for f in getattr(msg, 'fields', [])]
        expected_msgs[msg_name] = set(field_names)
    # Recursively collect from namespaces
    for ns in getattr(model, 'namespaces', {}).values():
        expected_msgs.update(collect_all_messages(ns, seen))
    # Recursively collect from imports (if your model supports this)
    for imported in getattr(model, 'imports', []):
        expected_msgs.update(collect_all_messages(imported, seen))
    return expected_msgs


def test_generate_header_with_local_enums_and_messages_pytest():
    """
    Tests that enums defined in a .def file are generated correctly in the C++ header
    and are available before messages in the same file try to use them.
    (Pytest style)
    """
    dsl_content = """
    namespace TestEnumGenPytest {
        enum MyStatus : int16 {
            OK = 0;
            ERROR = 1;
        }

        message StatusMessage {
            current_status: MyStatus;
            description: string;
        }
    }
    """
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".def", encoding="utf-8", dir="./generated/cpp_std23") as tmp_def_file:
        tmp_def_file.write(dsl_content)
        tmp_def_file_path = tmp_def_file.name
    
    generated_header_content = None
    # Derive expected header name based on your generator's convention
    # e.g., os.path.splitext(os.path.basename(tmp_def_file_path))[0] + "_std23.h"
    # For simplicity, let's assume a fixed part of the name if the temp name is tricky
    # or better, derive it like in the integration test.
    def_base_name = os.path.splitext(os.path.basename(tmp_def_file_path))[0]
    expected_header_filename = f"{def_base_name}_std23.h" 

    try:
        model = build_model_from_file_recursive(tmp_def_file_path)
        
        assert hasattr(model, 'namespaces'), "Model should have namespaces attribute"
        assert "TestEnumGenPytest" in model.namespaces, "TestEnumGenPytest namespace not found"
        
        namespaces_to_generate = [model.namespaces["TestEnumGenPytest"]]
        gen = CppGeneratorStd23(namespaces_to_generate, model=model)
        header_map = gen.generate_header()
        
        assert expected_header_filename in header_map, \
            f"Expected header file '{expected_header_filename}' not found. Found: {list(header_map.keys())}"
        generated_header_content = header_map[expected_header_filename]

        # Assertions for enum and struct definitions
        assert re.search(r"enum\s+class\s+MyStatus_Enum\s*:\s*uint8_t", generated_header_content), \
            "MyStatus_Enum definition missing or incorrect type."
        assert "OK = 0" in generated_header_content
        assert "ERROR = 1" in generated_header_content
        
        assert "struct StatusMessage" in generated_header_content
        assert "MyStatus_Enum current_status;" in generated_header_content
        assert "std::string description;" in generated_header_content

        # Verify namespace wrapping
        assert "namespace TestEnumGenPytest {" in generated_header_content
        assert generated_header_content.strip().endswith("} // namespace TestEnumGenPytest"), \
            "Namespace not closed correctly."

        # Check order: enum definition before struct usage
        my_status_enum_def_index = generated_header_content.find("enum class MyStatus_Enum")
        status_message_struct_def_index = generated_header_content.find("struct StatusMessage")

        assert my_status_enum_def_index != -1, "MyStatus_Enum definition not found for order checking."
        assert status_message_struct_def_index != -1, "StatusMessage definition not found for order checking."
        assert my_status_enum_def_index < status_message_struct_def_index, \
            "MyStatus_Enum must be defined before StatusMessage struct."

    finally:
        os.remove(tmp_def_file_path)

def test_enum_inheritance_from_non_enum_type_fails_model_building():
    """
    Tests that attempting to inherit an enum from a non-existent enum
    (e.g., a C++ type name like 'int16' used in the DSL inheritance syntax)
    causes model building to fail, as 'int16' is not a valid enum reference.
    """
    dsl_content = """
    namespace TestInvalidParent {
        enum MyStatus : int16 { // 'int16' is not a defined enum in the DSL
            OK = 0;
            ERROR = 1;
        }
    }
    """
    # Create a temporary .def file
    with tempfile.TemporaryDirectory() as tmpdir:
        def_path = os.path.join(tmpdir, "invalid_enum_parent.def")
        with open(def_path, "w", encoding="utf-8") as f:
            f.write(dsl_content)

        # Expect a RuntimeError (or a more specific error if defined by the model builder)
        # when it tries to resolve 'int16' as a parent enum.
        # The regex for the error message is made somewhat flexible.
        expected_error_pattern = (
            r"Cannot resolve parent enum 'int16' for enum '([\w:]+::)?MyStatus'|"
            r"Unresolved parent enum 'int16' for '([\w:]+::)?MyStatus'"
        )
        with pytest.raises(RuntimeError, match=expected_error_pattern):
            build_model_from_file_recursive(def_path)
