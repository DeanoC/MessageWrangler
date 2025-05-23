"""
model_flatten.py
Flattens the MessageModel so all references are FQN and lookups are direct, for generator use.
"""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from message_model import MessageModel

def flatten_model_for_generation(model: 'MessageModel') -> 'MessageModel':
    """
    Post-process the model so all messages, enums, and options are keyed by FQN and all references are resolved.
    This makes the model generator-friendly: all lookups are direct, and no further namespace resolution is needed.
    """
    # Ensure all messages are keyed by FQN
    fqn_messages = {}
    for msg in model.messages.values():
        fqn = msg.get_full_name() if hasattr(msg, 'get_full_name') else msg.name
        fqn_messages[fqn] = msg
    model.messages = fqn_messages
    # Ensure all enums are keyed by FQN
    fqn_enums = {}
    for enum in model.enums.values():
        fqn = enum.get_full_name() if hasattr(enum, 'get_full_name') else enum.name
        fqn_enums[fqn] = enum
    model.enums = fqn_enums
    # Ensure all options are keyed by FQN if they have a get_full_name
    if hasattr(model, 'options') and isinstance(model.options, dict):
        fqn_options = {}
        for k, v in model.options.items():
            if hasattr(v, 'get_full_name'):
                fqn = v.get_full_name()
                fqn_options[fqn] = v
            else:
                fqn_options[k] = v
        model.options = fqn_options
    # Optionally, resolve all parent references to FQN (if not already)
    for msg in model.messages.values():
        if msg.parent and '::' not in msg.parent:
            ns = getattr(msg, 'namespace', None)
            if ns:
                msg.parent = f"{ns}::{msg.parent}"
    for enum in model.enums.values():
        if enum.parent and '::' not in enum.parent:
            ns = getattr(enum, 'namespace', None)
            if ns:
                enum.parent = f"{ns}::{enum.parent}"
    return model
