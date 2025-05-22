def test_cpp_generator_std23_header_filenames_integration():
    """
    Integration: Ensure all generated header files have the correct filename (not messages_std23.h except for messages.def)
    """
    import glob
    import os
    from message_model_builder import build_model_from_file_recursive
    from generators.cpp_generator_std23 import CppGeneratorStd23
    all_defs = glob.glob(os.path.join("tests", "def", "*.def"))
    invalid = {
        "test_invalid.def",
        "test_duplicate_fields.def",
        "test_arrays_and_references_corner_cases.def",
        "test_unresolved.def",
    }
    def_files = [f for f in all_defs if os.path.basename(f) not in invalid]
    for def_path in def_files:
        model = build_model_from_file_recursive(def_path)
        model.main_file_path = def_path
        gen = CppGeneratorStd23([model], model=model)
        header_map = gen.generate_header()
        base_filename = os.path.splitext(os.path.basename(def_path))[0]
        sanitized_ns = gen._sanitize_identifier(base_filename, for_namespace=True)
        expected_header = f"{sanitized_ns}_std23.h"
        for header_name in header_map.keys():
            if header_name == "messages_std23.h":
                assert base_filename == "messages", f"Header {header_name} generated for {def_path}, but file is not messages.def"
            else:
                assert header_name.endswith("_std23.h"), f"Header {header_name} does not end with _std23.h"
                if base_filename != "messages":
                    assert expected_header in header_map, f"Expected header {expected_header} not found in generated headers for {def_path}: {list(header_map.keys())}"


import subprocess

import os
import glob
import tempfile
import pytest
from lark_parser import parse_message_dsl
from message_model_builder import build_model_from_lark_tree
from generators.cpp_generator_std23 import CppGeneratorStd23

def get_def_files():
    all_defs = glob.glob(os.path.join("tests", "def", "*.def"))
    invalid = {
        "test_invalid.def",
        "test_duplicate_fields.def",
        "test_arrays_and_references_corner_cases.def",
        "test_unresolved.def",
    }
    return [f for f in all_defs if os.path.basename(f) not in invalid]

@pytest.mark.parametrize("def_path", get_def_files())
def test_cpp_generator_std23_source(def_path):
    # Parse and build model, instantiate generator
    with open(def_path, "r", encoding="utf-8") as f:
        dsl = f.read()
    from message_model_builder import build_model_from_file_recursive
    import re
    model = build_model_from_file_recursive(def_path)
    if hasattr(model, 'namespaces'):
        namespaces = list(model.namespaces.values())
    else:
        namespaces = [model]
    gen = CppGeneratorStd23(namespaces, model=model)
    # Integration: check generated C++ compiles (syntax only)
    # This test expects modular header output: each .def file (including imports) generates its own header.
    # The dummy main.cpp includes all generated headers to ensure all types are visible for compilation.
    code_map = gen.generate_source()
    header_map = gen.generate_header()
    output_dir = os.path.join("generated", "cpp_std23")
    os.makedirs(output_dir, exist_ok=True)

    # Recursively generate and write all modular headers, including imports
    written_headers = set()
    def write_headers_for_file(def_file, already_done):
        if def_file in already_done:
            return
        print(f"[DEBUG] Processing def file: {def_file}")
        already_done.add(def_file)
        if not os.path.exists(def_file):
            print(f"[ERROR] Imported .def file does not exist: {def_file}")
            return
        m = build_model_from_file_recursive(def_file)
        if hasattr(m, 'namespaces'):
            ns_list = list(m.namespaces.values())
        else:
            ns_list = [m]
        # Determine if this file is being imported with an alias (as NAMESPACE)
        root_namespace = None
        # If this is not the main file, check if it was imported with an alias
        if def_file != def_path:
            # Find the import statement in the parent file that led to this import
            # (We pass the alias down recursively)
            for parent_file in already_done:
                with open(parent_file, "r", encoding="utf-8") as pf:
                    parent_text = pf.read()
                import_pattern = re.compile(r'^\s*import\s+"([^"]+)"\s+as\s+([A-Za-z_][A-Za-z0-9_]*)', re.MULTILINE)
                base_dir = os.path.dirname(os.path.abspath(parent_file))
                for match in import_pattern.finditer(parent_text):
                    import_path, import_ns = match.groups()
                    import_file = os.path.normpath(os.path.join(base_dir, import_path))
                    if import_file == def_file:
                        root_namespace = import_ns
                        break
                if root_namespace:
                    break
        g = CppGeneratorStd23(ns_list, model=m)
        hmap = g.generate_header() if not root_namespace else g.generate_header(root_namespace=root_namespace)
        # Write all headers produced by the generator for this file
        for header_name, header_content in hmap.items():
            out_path = os.path.join(output_dir, header_name)
            print(f"[DEBUG] Writing header: {header_name} for {def_file} (namespace: {root_namespace if root_namespace else 'default'}) to {out_path}")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(header_content)
            print(f"[DEBUG] Wrote header file: {out_path} (size: {os.path.getsize(out_path)} bytes)")
            written_headers.add(header_name)
        # Find imports in this file and recurse
        with open(def_file, "r", encoding="utf-8") as f:
            text = f.read()
        import_pattern = re.compile(r'^\s*import\s+"([^"]+)"\s+as\s+([A-Za-z_][A-Za-z0-9_]*)', re.MULTILINE)
        base_dir = os.path.dirname(os.path.abspath(def_file))
        for match in import_pattern.finditer(text):
            import_path, _ = match.groups()
            import_file = os.path.normpath(os.path.join(base_dir, import_path))
            print(f"[DEBUG] Recursing into import: {import_file}")
            write_headers_for_file(import_file, already_done)

    # Write all headers for the main file and all its imports
    write_headers_for_file(def_path, set())
    print(f"[DEBUG] written_headers after header writing: {sorted(written_headers)}")
    # Write all generated sources (if any)
    for fname, code in code_map.items():
        out_path = os.path.join(output_dir, fname)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"[DEBUG] Wrote source file: {out_path} (size: {os.path.getsize(out_path)} bytes)")
    # If no .cpp files were generated, create a dummy main.cpp that includes all headers
    if not code_map:
        def_base = os.path.splitext(os.path.basename(def_path))[0]
        main_cpp = os.path.join(output_dir, f"test_include_main_{def_base}.cpp")
        # Use all headers actually written (sorted for determinism)
        includes = [f'#include "{fname}"' for fname in sorted(written_headers)]
        print(f"[DEBUG] Creating dummy main.cpp with includes: {includes}")
        main_code = '\n'.join(includes) + '\nint main() { return 0; }\n'
        with open(main_cpp, "w", encoding="utf-8") as f:
            f.write(main_code)
        print(f"[DEBUG] Wrote dummy main.cpp: {main_cpp} (size: {os.path.getsize(main_cpp)} bytes)")
        code_map = {f"test_include_main_{def_base}.cpp": main_code}
    print(f"[INFO] Generated C++ files written to: {output_dir}")
    # --- Find C++ compiler only once per test session ---
    import shutil
    import threading
    compiler_cache = getattr(test_cpp_generator_std23_source, '_compiler_cache', None)
    if compiler_cache is None:
        compilers = [
            ["g++", "-std=c++23", "-fsyntax-only"],
            ["clang++", "-std=c++23", "-fsyntax-only"]
        ]
        cl_path = shutil.which("cl.exe")
        print(f"[DEBUG] cl.exe in PATH: {cl_path}")
        cl_env = None
        if not cl_path:
            import os as _os
            vswhere = r"C:\\Program Files (x86)\\Microsoft Visual Studio\\Installer\\vswhere.exe"
            if _os.path.exists(vswhere):
                import subprocess as _subprocess
                try:
                    print(f"[DEBUG] Running vswhere to find cl.exe...")
                    cl_paths_raw = _subprocess.check_output([
                        vswhere, "-products", "*", "-latest", "-prerelease", "-find", "**\\Hostx64\\x64\\cl.exe", "-format", "value"
                    ], encoding="utf-8")
                    print(f"[DEBUG] vswhere output:\n{cl_paths_raw}")
                    cl_paths = cl_paths_raw.strip().splitlines()
                    if cl_paths:
                        cl_path = cl_paths[0]
                        print(f"[DEBUG] Found cl.exe via vswhere: {cl_path}")
                    else:
                        print("[DEBUG] No cl.exe found via vswhere.")
                except Exception as e:
                    print(f"[DEBUG] Exception running vswhere: {e}")
        if cl_path:
            # Try to find vcvarsall.bat and set up the MSVC environment automatically
            vs_root = None
            vcvarsall = None
            import os as _os
            import subprocess as _subprocess
            try:
                vswhere = r"C:\\Program Files (x86)\\Microsoft Visual Studio\\Installer\\vswhere.exe"
                if _os.path.exists(vswhere):
                    vs_root = _subprocess.check_output([
                        vswhere, "-products", "*", "-latest", "-prerelease", "-property", "installationPath"
                    ], encoding="utf-8").strip()
                    vcvarsall_candidate = _os.path.join(vs_root, "VC", "Auxiliary", "Build", "vcvarsall.bat")
                    if _os.path.exists(vcvarsall_candidate):
                        vcvarsall = vcvarsall_candidate
            except Exception as e:
                print(f"[DEBUG] Could not find vcvarsall.bat: {e}")
            if vcvarsall:
                # Prepare a command to run vcvarsall and then output the environment
                arch = "x64"
                cmd = f'"{vcvarsall}" {arch} && set'
                print(f"[DEBUG] Running: {cmd}")
                proc = _subprocess.Popen(cmd, stdout=_subprocess.PIPE, shell=True)
                out, _ = proc.communicate()
                env = dict(line.split('=', 1) for line in out.decode(errors='ignore').splitlines() if '=' in line)
                cl_env = os.environ.copy()
                cl_env.update(env)
                print(f"[DEBUG] MSVC environment loaded from vcvarsall.bat")
            # Use /std:c++latest for MSVC, and only pass basenames (since cwd=output_dir)
            cl_cmd = [cl_path, "/std:c++latest", "/c"]
            compilers.append((cl_cmd, cl_env))
        compiler_cache = (compilers, cl_env)
        setattr(test_cpp_generator_std23_source, '_compiler_cache', compiler_cache)
    else:
        compilers, cl_env = compiler_cache
    cpp_files_full = [os.path.join(output_dir, f) for f in code_map.keys()]

    last_result = None
    compiler_attempted = False
    for compiler_entry in compilers:
        # Support (cmd, env) tuple for cl.exe, or just cmd for others
        if isinstance(compiler_entry, tuple):
            compiler, env = compiler_entry
        else:
            compiler, env = compiler_entry, None
        # For cl.exe, use only basenames; for others, use full paths
        if compiler[0].lower().endswith("cl.exe"):
            files = [os.path.basename(f) for f in cpp_files_full]
        else:
            files = cpp_files_full
        try:
            cmd = compiler + files
            print(f"[DEBUG] Running compiler: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=output_dir, env=env)
            print(f"[DEBUG] Compiler return code: {result.returncode}")
            print(f"[DEBUG] Compiler STDOUT:\n{result.stdout}")
            print(f"[DEBUG] Compiler STDERR:\n{result.stderr}")
            compiler_attempted = True
            last_result = result
            if result.returncode == 0:
                break # Success, no need to try other compilers
        except FileNotFoundError as e:
            print(f"[DEBUG] FileNotFoundError: {e}")
            continue # Compiler not found, try next one

    if not compiler_attempted:
        print("[DEBUG] No suitable C++23 compiler found or all invocations failed with FileNotFoundError.")
        pytest.skip("No suitable C++23 compiler (g++, clang++, or cl.exe) found in PATH or typical install locations.")
    else:
        # If compiler was attempted, assert the last result
        assert last_result.returncode == 0, f"C++ compiler error for {files}:\nSTDOUT:\n{last_result.stdout}\nSTDERR:\n{last_result.stderr}"
