"""
Dependency sort utility for EarlyModels based on their imports.
Raises an error if a cycle is detected.
"""
from early_model import EarlyModel
from typing import Dict, List, Set

class DependencyCycleError(Exception):
    pass

def topological_sort_earlymodels(models: Dict[str, EarlyModel]) -> List[EarlyModel]:
    """
    Given a dict of name -> EarlyModel, returns a list of EarlyModels sorted so that dependencies come first.
    Raises DependencyCycleError if a cycle is detected.
    """
    visited = set()
    temp_mark = set()
    result = []

    import os
    def normalize_path(path):
        return os.path.abspath(os.path.normpath(path))

    # Build a mapping from normalized file path to model
    norm_models = {normalize_path(k): v for k, v in models.items()}

    def visit(name: str):
        nname = normalize_path(name)
        if nname in visited:
            return
        if nname in temp_mark:
            raise DependencyCycleError(f"Cycle detected involving {nname}")
        temp_mark.add(nname)
        model = norm_models[nname]
        for dep_name, _ in model.imports_raw:
            dep_file = os.path.join(os.path.dirname(nname), dep_name)
            dep_file = normalize_path(dep_file)
            if dep_file in norm_models:
                visit(dep_file)
        temp_mark.remove(nname)
        visited.add(nname)
        result.append(model)

    for name in norm_models:
        visit(name)
    return result
