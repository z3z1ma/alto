# MIT License
# Copyright (c) 2023 Alex Butler
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
"""Useful utilities for alto."""
import importlib.util
import typing as t
from pathlib import Path

if t.TYPE_CHECKING:
    from alto.engine import AltoExtension


class ExtensionModule(t.Protocol):
    """Protocol for extension modules."""

    def register() -> t.Type["AltoExtension"]:
        """Register the extension."""


def load_extension_from_spec(module: str) -> ExtensionModule:
    """Load an extension from a spec."""
    spec = importlib.util.find_spec(module)
    ext_namespace = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ext_namespace)
    return t.cast(ExtensionModule, ext_namespace)


def load_extension_from_path(ext: Path) -> ExtensionModule:
    """Load an extension from a path."""
    spec = importlib.util.spec_from_file_location(ext.stem, ext)
    ext_namespace = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ext_namespace)
    return t.cast(ExtensionModule, ext_namespace)


def merge(source: dict, destination: dict) -> dict:
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
