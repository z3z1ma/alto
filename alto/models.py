import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Generic,
    List,
    Optional,
    TypedDict,
    TypeVar,
    Union,
)

from doit.action import BaseAction
from doit.reporter import ConsoleReporter

__all__ = [
    "AltoAction",
    "AltoTask",
    "AltoTaskData",
    "PluginConfiguration",
    "PluginType",
    "SingerCatalog",
    "SingerCatalogStream",
    "SingerCatalogStreamMetadata",
    "SingerCatalogStreamMetadataEntry",
    "SingerCatalogStreamMetadataRoot",
    "TapConfiguration",
    "TargetConfiguration",
    "UtilityConfiguration",
]


class PluginType(str, Enum):
    TAP = "taps"
    TARGET = "targets"
    UTILITY = "utilities"


class DataClassDictMixin:
    def items(self) -> Any:
        return self.__dict__.items()

    def keys(self) -> Any:
        return self.__dict__.keys()

    def values(self) -> Any:
        return self.__dict__.values()

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def setdefault(self, key: str, default: Any = None) -> Any:
        if not hasattr(self, key):
            setattr(self, key, default)
        return getattr(self, key)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def __delitem__(self, key: str) -> None:
        delattr(self, key)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def __iter__(self) -> Any:
        return iter(self.__dict__)

    def __len__(self) -> int:
        return len(self.__dict__)


T = TypeVar("T", bound="ParserMixin")


class ParserMixin(Generic[T]):
    @classmethod
    def parse_json(cls, data: Dict[str, Any]) -> T:
        return cls(**data)

    @classmethod
    def parse_str(cls, data: str) -> T:
        return cls.parse_json(json.loads(data))


@dataclass
class SingerCatalogStreamMetadata(DataClassDictMixin, ParserMixin["SingerCatalogStreamMetadata"]):
    breadcrumb: List[str]
    metadata: Union["SingerCatalogStreamMetadataEntry", "SingerCatalogStreamMetadataRoot"] = field(
        default_factory=lambda: {"selected": False}
    )

    def __post_init__(self) -> None:
        if self.is_root:
            self.metadata["inclusion"] = "available"
        if "selected" not in self.metadata:
            self.metadata["selected"] = False

    def to_dict(self) -> Dict[str, Any]:
        return {"breadcrumb": self.breadcrumb, "metadata": self.metadata}

    @property
    def is_root(self) -> bool:
        return not self.breadcrumb


@dataclass
class SingerCatalogStream(DataClassDictMixin, ParserMixin["SingerCatalogStream"]):
    tap_stream_id: str
    schema: Dict[str, Any]
    metadata: List[SingerCatalogStreamMetadata] = field(default_factory=list)
    key_properties: List[str] = field(default_factory=list)
    replication_key: Optional[str] = None
    replication_method: str = "FULL_TABLE"
    selected: bool = False
    stream: str = None
    database_name: str = None
    schema_name: str = None
    table_name: str = None

    def root_metadata(self) -> Optional[SingerCatalogStreamMetadata]:
        for metadata in self.metadata:
            if metadata.is_root:
                return metadata
        return None

    def __post_init__(self) -> None:
        if self.stream is None:
            self.stream = self.tap_stream_id
        self.replication_method = self.replication_method.upper()
        assert self.replication_method in {"FULL_TABLE", "INCREMENTAL", "LOG_BASED"}
        if self.replication_method == "INCREMENTAL":
            if self.replication_key is not None:
                assert self.replication_key in self.schema["properties"]
        else:
            self.replication_key = None
        for j, metadata in enumerate(self.metadata):
            if not isinstance(metadata, SingerCatalogStreamMetadata):
                self.metadata[j] = SingerCatalogStreamMetadata.parse_json(metadata)

    def to_dict(self) -> Dict[str, Any]:
        rv = {
            "tap_stream_id": self.tap_stream_id,
            "schema": self.schema,
            "metadata": [metadata.to_dict() for metadata in self.metadata],
            "key_properties": self.key_properties,
            "replication_key": self.replication_key,
            "replication_method": self.replication_method,
            "selected": self.selected,
            "stream": self.stream,
        }
        if self.database_name:
            rv["database_name"] = self.database_name
        if self.schema_name:
            rv["schema_name"] = self.schema_name
        if self.table_name:
            rv["table_name"] = self.table_name
        return rv

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SingerCatalogStream):
            return NotImplemented
        return (
            self.tap_stream_id == other.tap_stream_id
            and self.schema == other.schema
            and self.metadata == other.metadata
            and self.key_properties == other.key_properties
            and self.replication_key == other.replication_key
            and self.replication_method == other.replication_method
            and self.selected == other.selected
            and self.stream == other.stream
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.tap_stream_id,
                tuple(self.schema.items()),
                tuple(self.metadata),
                tuple(self.key_properties),
                self.replication_key,
                self.replication_method,
                self.selected,
                self.stream,
            )
        )


@dataclass
class SingerCatalog(ParserMixin["SingerCatalog"]):
    streams: List[SingerCatalogStream] = field(default_factory=list)

    def __post_init__(self) -> None:
        for i, entry in enumerate(self):
            if not isinstance(entry, SingerCatalogStream):
                self.streams[i] = SingerCatalogStream(**entry)

    @classmethod
    def parse_file(cls, path: Union[str, Path]) -> "SingerCatalog":
        with open(path) as fh:
            return cls.parse_json(json.load(fh))

    def to_dict(self) -> Dict[str, Any]:
        return {"streams": [entry.to_dict() for entry in self]}

    def __getitem__(self, key: Union[int, str]) -> SingerCatalogStream:
        if isinstance(key, str):
            # Convenience for getting a stream by tap_stream_id
            for entry in self.streams:
                if entry.tap_stream_id == key:
                    return entry
            raise KeyError(key)
        return self.streams[key]

    def __setitem__(self, key: Union[int, str], value: SingerCatalogStream) -> None:
        if isinstance(key, str):
            for i, entry in enumerate(self.streams):
                if entry.tap_stream_id == key:
                    self.streams[i] = value
                    return
            raise KeyError(key)
        self.streams[key] = value

    def __delitem__(self, key: Union[int, str]) -> None:
        if isinstance(key, str):
            for i, entry in enumerate(self.streams):
                if entry.tap_stream_id == key:
                    del self.streams[i]
                    return
            raise KeyError(key)
        del self.streams[key]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SingerCatalog):
            return NotImplemented
        return self.streams == other.streams

    def __hash__(self) -> int:
        return hash(tuple(self.streams))

    def __contains__(self, entry: SingerCatalogStream) -> bool:
        return entry in self.streams

    def __iter__(self):
        return iter(self.streams)


# Loosely typed via TypedDict

SingerCatalogStreamMetadataEntry = TypedDict(
    "SingerCatalogStreamMetadataEntry",
    {"selected": bool, "inclusion": str, "selected-by-default": bool},
    total=False,
)

SingerCatalogStreamMetadataRoot = TypedDict(
    "SingerCatalogStreamMetadataRoot",
    {
        "selected": bool,
        "inclusion": str,
        "replication-method": str,
        "replication-key": str,
        "table-key-properties": List[str],
    },
    total=False,
)


# Alto specific types use TypedDict exclusively for IDE typing


class BasePluginConfiguration(TypedDict, total=False):
    pip_url: str
    executable: str
    entrypoint: str
    config: Dict[str, Any]


class TapConfiguration(BasePluginConfiguration):
    namespace: str
    select: List[str]
    metadata: Dict[str, Dict[str, Any]]


class TargetConfiguration(BasePluginConfiguration):
    ...


class UtilityConfiguration(BasePluginConfiguration):
    ...


PluginConfiguration = Union[TapConfiguration, TargetConfiguration, UtilityConfiguration]
AltoAction = Union[BaseAction, Callable, str]


class AltoEngineConfig(TypedDict):
    default_tasks: List[str]
    reporter: ConsoleReporter
    dep_file: str
    backend: str
    verbosity: int
    par_type: str
    failure_verbosity: int


class AltoTaskData(TypedDict, total=False):
    basename: str
    name: str
    actions: List[AltoAction]
    clean: List[AltoAction]
    teardown: List[AltoAction]
    targets: List[Union[str, Path]]
    task_dep: List[str]
    file_dep: List[Union[str, Path]]
    uptodate: List[Union[bool, None]]
    setup: List[str]
    meta: Dict[str, Any]
    custom_title: Callable
    doc: str
    verbosity: int


class AltoTask:
    def __init__(self, name: str) -> None:
        self._data: AltoTaskData = {"name": name, "actions": []}

    @property
    def data(self) -> AltoTaskData:
        """Return the underlying data for the task. This is a TypedDict."""
        return self._data

    def set_name(self, name: str) -> "AltoTask":
        """Set the name of the task. This is required for all tasks."""
        self._data["name"] = name
        return self

    def set_basename(self, basename: str) -> "AltoTask":
        """Set the basename of the task. This is used to generate the task name."""
        self._data["basename"] = basename
        return self

    def set_actions(self, *actions: AltoAction, extend: bool = True) -> "AltoTask":
        """Set the actions for the task. A task with no actions will be skipped."""
        if extend:
            self._data.setdefault("actions", []).extend(actions)
        else:
            self._data["actions"] = actions
        return self

    def set_clean(self, *actions: AltoAction, extend: bool = True) -> "AltoTask":
        """Set the clean actions for the task. These will be run if the user invokes clean."""
        if extend:
            self._data.setdefault("clean", []).extend(actions)
        else:
            self._data["clean"] = actions
        return self

    def set_teardown(self, *actions: AltoAction, extend: bool = True) -> "AltoTask":
        """Set the teardown actions for the task. These will be run after the task completes."""
        if extend:
            self._data.setdefault("teardown", []).extend(actions)
        else:
            self._data["teardown"] = actions
        return self

    def set_targets(self, *targets: Union[str, Path], extend: bool = True) -> "AltoTask":
        """Set the targets for the task. These are the files that the task creates."""
        if extend:
            self._data.setdefault("targets", []).extend(targets)
        else:
            self._data["targets"] = targets
        return self

    def set_task_dep(self, *tasks: str, extend: bool = True) -> "AltoTask":
        """Set the task dependencies for the task. These are the tasks that must be run before this task.
        """
        if extend:
            self._data.setdefault("task_dep", []).extend(tasks)
        else:
            self._data["task_dep"] = tasks
        return self

    def set_file_dep(self, *files: Union[str, Path], extend: bool = True) -> "AltoTask":
        """Set the file dependencies for the task. These are the files that must be present before this task can run.
        """
        if extend:
            self._data.setdefault("file_dep", []).extend(files)
        else:
            self._data["file_dep"] = files
        return self

    def set_uptodate(
        self, *uptodate: Callable[..., Union[bool, None]], extend: bool = True
    ) -> "AltoTask":
        """Set the uptodate function for the task. This is a function that determines if the task is up to date.
        """
        if extend:
            self._data.setdefault("uptodate", []).extend(uptodate)
        else:
            self._data["uptodate"] = uptodate
        return self

    def set_setup(self, *tasks: str, extend: bool = True) -> "AltoTask":
        """Set the setup tasks for the task. These are the tasks that must be run before this task.
        """
        if extend:
            self._data.setdefault("setup", []).extend(tasks)
        else:
            self._data["setup"] = tasks
        return self

    def set_meta(self, meta: Dict[str, Any]) -> "AltoTask":
        """Set the meta data for the task. This is a dictionary of arbitrary data that can be used by other tasks.
        """
        self._data["meta"] = meta
        return self

    def set_custom_title(self, custom_title: Callable) -> "AltoTask":
        """Set the custom title function for the task. This is a function that returns a string to be used as the title
        """
        self._data["custom_title"] = custom_title
        return self

    def set_doc(self, doc: str) -> "AltoTask":
        """Set the doc string for the task. This is a string that will be displayed when the user invokes help.
        """
        self._data["doc"] = doc
        return self

    def set_verbosity(self, verbosity: int) -> "AltoTask":
        """Set the verbosity for the task. This is an integer that determines the verbosity level for the task.
        """
        self._data["verbosity"] = verbosity
        return self

    def __dict__(self) -> AltoTaskData:
        """Return the task data as a dictionary. This is used by the Alto engine to create the task.
        """
        return self._data


AltoTaskGenerator = Generator[AltoTaskData, None, None]
