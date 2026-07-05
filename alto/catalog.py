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
"""Catalog utilities."""

import copy
import fnmatch
import json
import typing as t
from enum import Enum
from pathlib import Path

from alto.models import SingerCatalog, SingerCatalogStreamMetadata

__all__ = [
    "CatalogMutationStrategy",
    "apply_selected",
    "apply_metadata",
]


class CatalogMutationStrategy(str, Enum):
    """The strategy to use when applying the selected streams to the catalog

    - PRUNE: Remove all streams that are not selected
    - DESELECT: Deselect all streams that are not selected"""

    PRUNE = "prune"
    DESELECT = "deselect"


def _remove_breadcrumb_from_schema(
    schema: t.Dict[str, t.Any], entry: SingerCatalogStreamMetadata
) -> None:
    parent: t.List[str] = []
    schema_ptr = copy.copy(schema)
    breadcrumb = list(entry.breadcrumb)
    try:
        while breadcrumb:
            prop = breadcrumb.pop(0)
            if not breadcrumb:
                schema.pop(prop, None)
                _remove_empty_schema_parent(schema, schema_ptr, parent)
                break
            child = schema.get(prop)
            if not isinstance(child, dict):
                break
            schema = child
            parent.append(prop)
    except (KeyError, IndexError):
        return


def _remove_empty_schema_parent(
    schema: t.Dict[str, t.Any], schema_ptr: t.Dict[str, t.Any], parent: t.List[str]
) -> None:
    if schema or len(parent) <= 2:
        return
    inner = schema_ptr
    for path in parent[:-2]:
        inner = inner[path]
    inner.pop(parent[-2], None)


def _select_attribute(attribute: SingerCatalogStreamMetadata) -> bool:
    propagated = True
    entry = attribute.metadata
    selected_by_default = entry.get("selected-by-default", False)
    is_selected = entry.get("selected")
    # Apply the selection and return the propagation state
    if is_selected:
        return propagated
    if is_selected is None and selected_by_default:
        entry["selected"] = True
        return propagated
    if not is_selected and entry.get("inclusion") == "automatic":
        entry["selected"] = True
        return not propagated
    return not propagated


SelectionPattern = t.Tuple[str, str, bool]
CatalogSource = t.Union[Path, str, t.Dict[str, t.Any], SingerCatalog]


def _normalize_selections(selections: t.List[str]) -> t.List[str]:
    selections = selections or ["*.*"]
    if all(selection.startswith(("!", "~")) for selection in selections):
        selections.insert(0, "*.*")
    return selections


def _selection_patterns(selections: t.List[str]) -> t.List[SelectionPattern]:
    patterns = [
        (stream.lstrip("!"), ".".join(breadcrumb), stream.startswith("!"))
        for stream, breadcrumb in (
            (
                selection.split(".", 1)[0],
                selection.split(".", 1)[1:] if selection.count(".") > 0 else ["*"],
            )
            for selection in selections
            if not selection.startswith("~")
        )
    ]
    if all(inverted for _, _, inverted in patterns):
        patterns.insert(0, ("*", "*", False))
    return patterns


def _catalog_from_source(target_catalog: CatalogSource) -> SingerCatalog:
    if isinstance(target_catalog, Path):
        return SingerCatalog.parse_file(target_catalog)
    if isinstance(target_catalog, str):
        return SingerCatalog.parse_str(target_catalog)
    if isinstance(target_catalog, dict):
        return SingerCatalog.parse_json(t.cast(t.Dict[str, t.Any], target_catalog))
    return target_catalog


def _root_metadata_index(stream: t.Any) -> t.Optional[int]:
    return next((i for i, entry in enumerate(stream.metadata) if entry.is_root), None)


def _ensure_root_metadata(stream: t.Any) -> SingerCatalogStreamMetadata:
    root_ix = _root_metadata_index(stream)
    if root_ix is None:
        root = SingerCatalogStreamMetadata(breadcrumb=[], metadata={})
        stream.metadata.append(root)
        return root
    root = stream.metadata[root_ix]
    root.metadata.pop("selected", None)
    return root


def _apply_stream_patterns(stream: t.Any, patterns: t.List[SelectionPattern]) -> None:
    _ensure_root_metadata(stream)
    stream_id = stream.tap_stream_id
    for stream_glob, breadcrumb_glob, invert in patterns:
        if not fnmatch.fnmatch(stream_id, stream_glob):
            continue
        for attribute in stream.metadata:
            if _attribute_matches(attribute, breadcrumb_glob):
                attribute.metadata["selected"] = True ^ invert


def _attribute_matches(attribute: SingerCatalogStreamMetadata, breadcrumb_glob: str) -> bool:
    return fnmatch.fnmatch(
        ".".join(attribute.get("breadcrumb", ["properties"])[1:]),
        breadcrumb_glob,
    )


def _apply_attribute_selection(stream: t.Any, strategy: CatalogMutationStrategy) -> bool:
    if not any(_select_attribute(attr) for attr in stream.metadata):
        return False
    stream.selected = True
    stream.metadata[_root_metadata_index(stream) or 0].metadata["selected"] = True
    _handle_unselected_attributes(stream, strategy)
    return True


def _handle_unselected_attributes(stream: t.Any, strategy: CatalogMutationStrategy) -> None:
    attr_to_remove: t.List[int] = []
    for j, entry in enumerate(stream.metadata):
        if entry.metadata.get("selected") is None:
            entry.metadata["selected"] = True
        elif not entry.metadata["selected"]:
            attr_to_remove.append(j)
    for j in reversed(attr_to_remove):
        _handle_unselected_attribute(stream, j, strategy)


def _handle_unselected_attribute(
    stream: t.Any, index: int, strategy: CatalogMutationStrategy
) -> None:
    if strategy == CatalogMutationStrategy.PRUNE:
        _remove_breadcrumb_from_schema(stream.schema, stream.metadata.pop(index))
    elif strategy == CatalogMutationStrategy.DESELECT:
        stream.metadata[index].metadata["selected"] = False


def _handle_unselected_stream(
    catalog: SingerCatalog, index: int, strategy: CatalogMutationStrategy
) -> None:
    if strategy == CatalogMutationStrategy.PRUNE:
        catalog.streams.pop(index)
    elif strategy == CatalogMutationStrategy.DESELECT:
        catalog.streams[index].selected = False


def apply_selected(
    target_catalog: CatalogSource,
    selections: t.List[str],
    write: bool = True,
    strategy: CatalogMutationStrategy = CatalogMutationStrategy.PRUNE,
) -> SingerCatalog:
    """Applies the selected streams and attributes to the target catalog in two passes:

    - Pass-1 - apply attribute level selections / negations in sequence
    - Pass-2 - apply stream selections / deletions based on attribute selections
    """

    patterns = _selection_patterns(_normalize_selections(selections))
    catalog = _catalog_from_source(target_catalog)

    # Pass-1
    for stream in catalog.streams:
        _apply_stream_patterns(stream, patterns)

    # Pass-2
    streams_to_remove: t.List[int] = []
    for i, stream in enumerate(catalog.streams):
        if not _apply_attribute_selection(stream, strategy):
            streams_to_remove.append(i)

    # Remove streams in reverse order to avoid index shifting
    for i in reversed(streams_to_remove):
        _handle_unselected_stream(catalog, i, strategy)

    if write and isinstance(target_catalog, Path):
        target_catalog.write_text(json.dumps(catalog.to_dict(), indent=2))

    return catalog


def _metadata_catalog_from_source(
    target_catalog: t.Union[Path, str, SingerCatalog],
) -> SingerCatalog:
    if isinstance(target_catalog, Path):
        return SingerCatalog.parse_file(target_catalog)
    if isinstance(target_catalog, str):
        return SingerCatalog.parse_str(target_catalog)
    return target_catalog


def _apply_metadata_payload(stream: t.Any, payload: t.Dict[str, t.Any]) -> None:
    root_metadata = t.cast(
        t.Dict[str, t.Any],
        stream.metadata[_root_metadata_index(stream) or 0].metadata,
    )
    root_metadata.update(payload)
    if "replication-method" in payload:
        stream.replication_method = payload["replication-method"]
    if "replication-key" in payload:
        stream.replication_key = payload["replication-key"]


def apply_metadata(
    target_catalog: t.Union[Path, str, SingerCatalog],
    metadata: t.Dict[str, t.Dict[str, t.Any]],
    write: bool = True,
) -> SingerCatalog:
    """Applies the metadata to the target catalog"""

    if not metadata:
        metadata = {}

    catalog = _metadata_catalog_from_source(target_catalog)

    for criteria, payload in metadata.items():
        # Ensure users cannot mess with selection which is handled by
        # dedicated apply_selected function
        payload.pop("selected", None)

        for stream in catalog.streams:
            # Skip streams that do not match the criteria
            if not fnmatch.fnmatch(stream.tap_stream_id, criteria):
                continue
            _apply_metadata_payload(stream, payload)

    if write and isinstance(target_catalog, Path):
        target_catalog.write_text(json.dumps(catalog.to_dict(), indent=2))

    return catalog
