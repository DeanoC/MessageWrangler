# This file has moved to early_model_transforms/bob_prefix_transform.py
raise ImportError("This file has moved to early_model_transforms/bob_prefix_transform.py. Please update your imports.")

    def _prefix(self, name: Any) -> Any:
        if isinstance(name, str):
            return f"BOB_{name}"
        return name
