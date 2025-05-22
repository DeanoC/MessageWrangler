# MessageWrangler Namespace Resolution Hierarchy

This document describes how MessageWrangler resolves message and enum names (especially unqualified names) across namespaces and imported files, for C++ code generation.

## 1. File-level Namespace

- Each `.def` file defines a C++ namespace matching the sanitized filename (e.g., `foo.def` → `namespace foo { ... }`).
- Messages/enums defined at the top level (not inside any `namespace` block) go directly into this file-level namespace.

## 2. Nested Namespaces

- `namespace Bar { ... }` in `foo.def` becomes `namespace foo { namespace Bar { ... } }` in the header.
- Messages/enums inside `namespace Bar` go into `foo::Bar`.
- If a namespace matches the file-level namespace, it is still nested: e.g., `y.def` with `namespace Y { ... }` emits `namespace Y { namespace Y { ... } }`.

## 3. Imports and Aliases

- `import "X"` brings in the file-level namespace `X` from `X.def`.
- `import "X" as L` brings in the file-level namespace as `L`.
- Aliased imports are only accessible via the alias (e.g., `L::AA`).
- Non-aliased imports allow unqualified references to their file-level namespace (see below).

## 4. Name Resolution Order (for inheritance/references)

When resolving an unqualified (unadorned) name (e.g., `AA`):

1. **Current Namespace:** Search the current namespace.
2. **Parent Namespaces:** Recursively search parent namespaces, up to the file-level namespace.
3. **File-level Namespace:** If not found, search the file-level namespace of the current `.def` file.
4. **Non-aliased Imports:** If still not found, search the file-level namespace of any non-aliased imports (not their sub-namespaces).
5. **Aliased Imports:** Only accessible via their alias (never by unadorned name).

## 5. Examples

### Example 1: Simple

x.def:
message AA {}
namespace B {
  message BB {}
}

- `AA` is in `X`.
- `BB` is in `X::B`.

### Example 2: Import and Reference

y.def:
import "X"
message CC {}
namespace D {
  message DD : AA {}      // AA resolves to X::AA
  message EE : CC {}      // CC resolves to Y::CC
}

### Example 3: Nested and Shadowing

y.def:
import "X"
namespace Y {
  namespace Z {
    message AA {}
    message EE : AA {}    // AA resolves to Y::Y::Z::AA
    message FF : BB {}    // BB resolves to Y::BB (if present at file-level)
  }
}

### Example 4: Aliased Import

z.def:
import "X" as L
message ZZ : L:AA {}      // L::AA

## 6. Summary Table

| Where is name defined?         | How to reference?         |
|-------------------------------|---------------------------|
| Current namespace             | Unqualified name          |
| Parent namespace(s)           | Unqualified name          |
| File-level namespace          | Unqualified name          |
| Non-aliased import file-level | Unqualified name          |
| Aliased import                | Must use alias            |
| Sub-namespace of import       | Must use qualified name   |

---

This logic ensures that C++ code generation matches user expectations and avoids ambiguity in cross-file and cross-namespace references.
