import importlib.util
from pathlib import Path
from types import ModuleType


def load_extension_from_path(ext: Path) -> ModuleType:
    """Load an extension from a path."""
    spec = importlib.util.spec_from_file_location(ext.stem, ext)
    ext_namespace = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ext_namespace)
    return ext_namespace


def load_extensions_from_path(ext_path: Path) -> list[ModuleType]:
    """Load all extensions from a path."""
    exts = []
    for ext in ext_path.glob("*.py"):
        exts.append(load_extension_from_path(ext))
    return exts


def merge(source: dict, destination: dict):
    """Merge source into destination recursively mutating destination in place."""
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            if isinstance(node, dict):
                merge(value, node)
            else:
                destination[key] = value
        else:
            destination[key] = value
    return destination


def message_type(raw: bytes) -> bool:
    """Get the message type.

    Newline delimited JSON messages can be parsed without unmarshalling into Python objects
    by looking at the first few bytes. This works in most cases because messages are typically
    dumped with the first key being "type".

    Returns:
       -1: Unknown, not JSON
        0: Unknown
        1: RECORD
        2: SCHEMA
        3: STATE
        99: unexpected sort, callee should parse
    """
    if raw[0] != 123:  # JSON
        return -1
    if raw[2:6] != b"type":
        return 99
    if raw[8] == 32:  # Loose
        if raw[10] == 82:  # R
            return 1
        elif raw[10:12] == b"SC":  # SC
            return 2
        elif raw[10:12] == b"ST":  # ST
            return 3
        else:
            return 0
    else:  # Compact
        if raw[9] == 82:  # R
            return 1
        elif raw[9:11] == b"SC":  # SC
            return 2
        elif raw[9:11] == b"ST":  # ST
            return 3
        else:
            return 0
