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

T = t.TypeVar("T")
T_co = t.TypeVar("T_co", covariant=True)


class Registrar(t.Protocol, t.Generic[T_co]):
    """Protocol for extension modules."""

    def register(self) -> t.Type[T_co]:
        """Return the registered extension class."""
        raise NotImplementedError


def load_extension_from_spec(spec: str) -> Registrar[t.Any]:
    """Load an extension from a spec."""
    return _load_from_spec(spec)


def load_extension_from_path(path: Path) -> Registrar[t.Any]:
    """Load an extension from a path."""
    return _load_from_path(path)


def load_mapper_from_path(ext: Path) -> Registrar[t.Any]:
    """Load a stream mapper from a path."""
    return _load_from_path(ext)


def _load_from_spec(module: str) -> Registrar[T]:
    """Load an extension from a spec."""
    spec = importlib.util.find_spec(module)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load extension module {module!r}.")
    ext_namespace = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ext_namespace)
    return t.cast(Registrar[T], ext_namespace)


def _load_from_path(ext: Path) -> Registrar[T]:
    """Load an extension from a path."""
    spec = importlib.util.spec_from_file_location(ext.stem, ext)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load extension from {ext}.")
    ext_namespace = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ext_namespace)
    return t.cast(Registrar[T], ext_namespace)


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


def bounded_table_rows(
    items: t.Sequence[t.Any],
    part_factory: t.Callable[[t.Any], t.List[t.Any]],
    truncate: bool,
) -> t.Tuple[t.List[str], int]:
    output = [["Type", "Size (Mb)", "Last Updated", "Name"]]
    max_width = [len(w) for w in output[0]]
    remainder = 0
    for n, item in enumerate(items):
        parts = part_factory(item)
        output.append(parts)
        for i, part in enumerate(parts):
            max_width[i] = max(max_width[i], len(str(part)))
        if truncate and n > 10:
            output.append(["...", "...", "...", "..."])
            remainder = len(items[n + 1 :])
            break
    return padded_table_rows(output, max_width), remainder


def padded_table_rows(output: t.List[t.List[t.Any]], max_width: t.List[int]) -> t.List[str]:
    return [
        "".join(str(part).ljust(max_width[i] + 2) for i, part in enumerate(row)) for row in output
    ]


def filesystem_info_parts(info: t.Mapping[str, t.Any], name: str) -> t.List[t.Any]:
    size = "" if info["type"][0] == "d" else f"{info['size'] * 1e-6:.02f}"
    return [info["type"][0], size, info.get("updated", ""), name]


def message_type(raw: bytes) -> int:
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
