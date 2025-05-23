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

    def visit(name: str):
        if name in visited:
            return
        if name in temp_mark:
            raise DependencyCycleError(f"Cycle detected involving {name}")
        temp_mark.add(name)
        model = models[name]
        for dep_name, _ in model.imports_raw:
            if dep_name in models:
                visit(dep_name)
        temp_mark.remove(name)
        visited.add(name)
        result.append(model)

    for name in models:
        visit(name)
    return result
