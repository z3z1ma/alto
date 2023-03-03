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
    parent = []
    schema_ptr = copy.copy(schema)
    try:
        while len(entry.breadcrumb) > 0:
            prop = entry.breadcrumb.pop(0)
            if len(entry.breadcrumb) == 0:
                schema.pop(prop, None)
                if not schema and len(parent) > 2:
                    inner = schema_ptr
                    for path in parent[:-2]:
                        inner = inner[path]
                    inner.pop(parent[-2], None)
                break
            else:
                schema = schema.get(prop)
                if not schema:
                    break
            parent.append(prop)
    except (KeyError, IndexError):
        pass


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


def apply_selected(
    target_catalog: t.Union[Path, str, SingerCatalog],
    selections: t.List[str],
    write: bool = True,
    strategy: CatalogMutationStrategy = CatalogMutationStrategy.PRUNE,
) -> SingerCatalog:
    """Applies the selected streams and attributes to the target catalog in two passes:

    - Pass-1 - apply attribute level selections / negations in sequence
    - Pass-2 - apply stream selections / deletions based on attribute selections
    """

    # If no selections are provided, select all streams
    if not selections:
        selections = ["*.*"]

    # All inverted selections take the stance all streams are selected by default
    # and then negated by the selection patterns
    if all(selection.startswith("!") for selection in selections):
        selections.insert(0, "*.*")

    patterns = [
        (stream.lstrip("!"), ".".join(breadcrumb), stream.startswith("!"))
        for stream, breadcrumb in (
            (
                selection.split(".", 1)[0],
                selection.split(".", 1)[1:] if selection.count(".") > 0 else ["*"],
            )
            for selection in selections
        )
    ]

    # Parse the catalog
    if isinstance(target_catalog, Path):
        catalog = SingerCatalog.parse_file(target_catalog)
    elif isinstance(target_catalog, str):
        catalog = SingerCatalog.parse_str(target_catalog)
    elif isinstance(target_catalog, t.dict):
        catalog = SingerCatalog.parse_json(target_catalog)
    else:
        catalog: SingerCatalog = target_catalog

    # All inverted selections take the stance all streams are selected by default
    # and then negated by the selection patterns
    if all(inverted for _, _, inverted in patterns):
        patterns.insert(0, ("*", "*", False))

    # Pass-1
    for stream in catalog.streams:
        stream_id = stream.tap_stream_id
        root_ix = next((i for i, entry in enumerate(stream.metadata) if entry.is_root), None)
        if root_ix is not None:
            stream.metadata[root_ix].metadata.pop("selected", None)
        else:
            stream.metadata.append(SingerCatalogStreamMetadata(breadcrumb=[], metadata={}))
        for stream_glob, breadcrumb_glob, invert in patterns:
            if not fnmatch.fnmatch(stream_id, stream_glob):
                continue
            for attribute in stream.metadata:
                if fnmatch.fnmatch(
                    ".".join(attribute.get("breadcrumb", ["properties"])[1:]),
                    breadcrumb_glob,
                ):
                    attribute.metadata["selected"] = True ^ invert

    # Pass-2
    streams_to_remove: t.List[int] = []
    for i, stream in enumerate(catalog.streams):
        # Mark stream for removal if no attributes are selected
        if not any(_select_attribute(attr) for attr in stream.metadata):
            streams_to_remove.append(i)
            continue

        stream.selected = True
        stream.metadata[
            next((i for i, entry in enumerate(stream.metadata) if entry.is_root), 0)
        ].metadata["selected"] = True

        attr_to_remove: t.List[int] = []
        for j, entry in enumerate(stream.metadata):
            # Select ambiguous attributes
            if entry.metadata.get("selected") is None:
                entry.metadata["selected"] = True
            # Mark attributes for removal
            elif not entry.metadata["selected"]:
                attr_to_remove.append(j)

        # Remove attributes in reverse order to avoid index shifting
        for j in reversed(attr_to_remove):
            if strategy == CatalogMutationStrategy.PRUNE:
                # Remove the property from the schema erring on the side of runtime safety
                _remove_breadcrumb_from_schema(stream.schema, stream.metadata.pop(j))
            elif strategy == CatalogMutationStrategy.DESELECT:
                stream.metadata[j].metadata["selected"] = False

    # Remove streams in reverse order to avoid index shifting
    for i in reversed(streams_to_remove):
        if strategy == CatalogMutationStrategy.PRUNE:
            catalog.streams.pop(i)
        elif strategy == CatalogMutationStrategy.DESELECT:
            catalog.streams[i].selected = False

    if write and isinstance(target_catalog, Path):
        target_catalog.write_text(json.dumps(catalog.to_dict(), indent=2))

    return catalog


def apply_metadata(
    target_catalog: t.Union[Path, str, SingerCatalog],
    metadata: t.Dict[str, t.Dict[str, t.Any]],
    write: bool = True,
) -> SingerCatalog:
    """Applies the metadata to the target catalog"""

    if not metadata:
        metadata = {}

    if isinstance(target_catalog, Path):
        catalog = SingerCatalog.parse_file(target_catalog)
    elif isinstance(target_catalog, str):
        catalog = SingerCatalog.parse_str(target_catalog)
    else:
        catalog: SingerCatalog = target_catalog

    for criteria, payload in metadata.items():
        # Ensure users cannot mess with selection which is handled by
        # dedicated apply_selected function
        payload.pop("selected", None)

        for stream in catalog.streams:
            # Skip streams that do not match the criteria
            if not fnmatch.fnmatch(stream.tap_stream_id, criteria):
                continue

            # Apply the metadata to the root of the stream
            stream.metadata[
                next((i for i, entry in enumerate(stream.metadata) if entry.is_root), 0)
            ].metadata.update(payload)

            # Bubble up the metadata to the parent stream for legacy compatibility
            if "replication-method" in payload:
                stream.replication_method = payload["replication-method"]
            if "replication-key" in payload:
                stream.replication_key = payload["replication-key"]

    if write and isinstance(target_catalog, Path):
        target_catalog.write_text(json.dumps(catalog.to_dict(), indent=2))

    return catalog
