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
"""Primary alto engine."""
import atexit
import datetime
import fnmatch
import gzip
import io
import itertools
import json
import os
import platform
import queue
import shutil
import subprocess
import sys
import threading
import typing as t
import uuid
from contextlib import contextmanager
from copy import deepcopy
from enum import Enum
from hashlib import md5, sha1
from pathlib import Path

import dynaconf.utils
import fsspec
from doit.cmd_base import CmdAction
from doit.cmd_base import DoitCmdBase as AltoCmdBase
from doit.cmd_base import TaskLoader2 as DoitEngine
from doit.loader import generate_tasks
from doit.tools import config_changed
from dynaconf.utils.boxing import DynaBox
from fsspec.implementations.dirfs import DirFileSystem

from alto.catalog import apply_metadata, apply_selected
from alto.constants import (
    ALTO_DB_FILE,
    ALTO_ROOT,
    CATALOG_DIR,
    CONFIG_DIR,
    DEFAULT_ENVIRONMENT,
    LOG_DIR,
    PLUGIN_DIR,
    STATE_DIR,
    SUPPORTED_CONFIG_FORMATS,
)
from alto.models import (
    AltoEngineConfig,
    AltoTask,
    AltoTaskData,
    AltoTaskGenerator,
    PluginType,
    SingerCatalog,
)
from alto.state import ensure_state, update_state
from alto.ui import AltoEmojiUI, AltoRichUI
from alto.utils import (
    load_extension_from_path,
    load_extension_from_spec,
    load_mapper_from_path,
    merge,
)

if t.TYPE_CHECKING:
    from dynaconf import Dynaconf, Validator

__all__ = [
    "AltoConfiguration",
    "AltoFileSystem",
    "AltoPlugin",
    "AltoTaskEngine",
]

RESERVOIR_VERSION_KEY = "__version__"
"""The key used to store the version of the reservoir format."""
RESERVOIR_BUFFER_SIZE = 10_000
"""The default number of records to buffer before flushing to reservoir filesystem."""


def find_hyphen_key(key: str, data: t.Dict[str, t.Any]) -> t.Optional[str]:
    """Find a key in a dict that matches the given key, allowing for hyphens."""
    if key in data:
        return key
    for k in data.keys():
        if k.replace("-", "_") == key:
            return k
    return None


# Patch dynaconf to support hyphenated keys
# this allows us to override config values with env vars
# even when the config key contains a hyphen.
# ie. `ALTO_TAPS__MY_TAP__SOMETHING` will override `taps.my-tap.something`
# If the hypenated key is not found, the original dynaconf lookup is used.
# This means non-hyphenated keys will still work as expected if they exist.
__case_lookup = dynaconf.utils.find_the_correct_casing
dynaconf.utils.find_the_correct_casing = lambda key, data: find_hyphen_key(
    key, data
) or __case_lookup(key, data)


class AltoCmd(str, Enum):
    """The alto task type is used to determine the type of task to execute."""

    BUILD = "build"
    CONFIG = "config"
    CATALOG = "catalog"
    APPLY = "apply"
    PIPELINE = "pipeline"
    TEST = "test"
    ABOUT = "about"

    def __str__(self) -> str:
        """Return the string representation of the command."""
        return self.value


class AltoConfiguration:
    """A wrapper around dynaconf that provides alto specific accessors."""

    def __init__(self, inner: DynaBox) -> None:
        """Initialize the alto config container."""
        self._inner = inner

    @property
    def inner(self) -> DynaBox:
        """Return the underlying dynaconf config object."""
        return self._inner

    def plugins(self, *types: PluginType) -> t.List["AltoPlugin"]:
        """Return a list of 2-tuples of plugins and their configuration object.

        Args:
            types: The types of plugins to return. If no types are specified, all plugins
            are returned.
        """
        if not types:
            types = (PluginType.TAP, PluginType.TARGET, PluginType.UTILITY)
        return [
            AltoPlugin(name, typ=typ, config=self)
            for typ in types
            for name in self.inner.get(typ.value, {})
        ]

    def get_plugin(self, name: str) -> "AltoPlugin":
        """Return a plugin by name.

        Args:
            name: The name of the plugin to return.
        """
        for plugin in self.plugins():
            if plugin.name == name:
                return plugin
        raise ValueError(f"Plugin {name} not found")

    @property
    def taps(self):
        """Return a dictionary of tap plugins."""
        return {plugin.name: plugin for plugin in self.plugins(PluginType.TAP)}

    @property
    def targets(self):
        """Return a dictionary of target plugins."""
        return {plugin.name: plugin for plugin in self.plugins(PluginType.TARGET)}

    @property
    def utilities(self):
        """Return a dictionary of utility plugins."""
        return {plugin.name: plugin for plugin in self.plugins(PluginType.UTILITY)}

    def spec_for(self, name: str) -> DynaBox:
        """Return the top level data for a plugin from alto config.

        This method will recursively merge the plugin's spec with its parent's spec.

        Args:
            name: The name of the plugin to return the spec for.
        """
        spec = next(
            (
                plugin_spec
                for typ in (PluginType.TAP, PluginType.TARGET, PluginType.UTILITY)
                for plugin_name, plugin_spec in self.inner.get(typ.value, {}).items()
                if plugin_name == name
            ),
            None,
        )
        if spec is None:
            raise ValueError(f"Plugin {name} not found")
        if "inherit_from" in spec:
            layer = self.spec_for(spec["inherit_from"])
            spec = layer + spec
        return spec


class AltoFileSystem:
    """The alto file system is a wrapper around fsspec that provides additional functionality."""

    def __init__(
        self,
        root_dir: Path,
        config: AltoConfiguration,
    ) -> None:
        """Initialize the path manager.

        Args:
            root_dir: The root directory of the alto project.
            wrapper: The alto configuration wrapper object.
        """
        self._root_dir = root_dir
        self._config = config

    @property
    def root_dir(self) -> Path:
        """Return the root directory of the alto project.

        The root directory is the directory where the alto configuration file is located.
        """
        return self._root_dir

    @property
    def sys_dir(self) -> str:
        """Return the path to the system directory.

        The system directory is where alto persists data when no remote storage is configured.
        """
        if not hasattr(self, "_sys_dir"):
            self._sys_dir = str(
                Path.home()
                .joinpath(ALTO_ROOT, self.config.get("PROJECT_NAME", "default"))
                .resolve()
            )
        return self._sys_dir

    @property
    def stg_dir(self) -> str:
        """Return the path to the staging directory.

        The staging directory is where alto persists data during the execution of a task.
        """
        if not hasattr(self, "_stg_dir"):
            tmp = self.root_dir.joinpath(ALTO_ROOT, os.urandom(4).hex())
            tmp.mkdir(parents=True, exist_ok=True)

            def cleanup():
                try:
                    shutil.rmtree(tmp)
                except FileNotFoundError:
                    pass

            # Register a cleanup function to remove the staging directory
            atexit.register(cleanup)
            self._stg_dir = tmp
        return self._stg_dir

    @property
    def config(self) -> DynaBox:
        """Return the alto configuration object."""
        return self._config.inner

    @property
    def fs(self) -> fsspec.AbstractFileSystem:
        """Return the alto storage file system.

        The alto storage file system is used to persist data to a remote storage location.
        """
        if not hasattr(self, "_fs"):
            fsystem: str = str(self.config.get("FILESYSTEM", "FILE")).upper()
            if fsystem == "FILE":
                # Local file system
                self._fs = DirFileSystem(
                    self.sys_dir, fs=fsspec.filesystem(fsystem.lower(), auto_mkdir=True)
                )
            elif fsystem in ("S3", "S3A", "GS", "GCS", "ADLS"):
                # Remote file system
                path: str = self.config.get("BUCKET_PATH", "alto")
                path = path.strip("/")
                self._fs = DirFileSystem(
                    f"{self.config['BUCKET']}/{path}/{self.config['PROJECT_NAME']}",
                    fs=fsspec.filesystem(
                        fsystem.lower(), **self.config.get(f"{fsystem}_SETTINGS", DynaBox())
                    ),
                )
            else:
                # Invalid file system
                raise ValueError(f"Invalid filesystem type specified. Got: {fsystem}")
        return self._fs

    def _remote_path(self, fname: str, key: str = "/") -> str:
        """Return the path to a file in the alto storage directory.

        Args:
            fname: The name of the file.
            key: The key to the file.
        """
        return "/".join([key, fname]).lstrip("/")

    def _temp_path(self, fname: str, key: str = "./") -> str:
        """Return the path to a file in the staging directory.

        Args:
            fname: The name of the file.
            key: The key to the file.
        """
        path = Path(self.stg_dir).joinpath(key, fname).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    def _root_path(self, fname: str, key: str = "./") -> str:
        """Return the path to a file in the root .alto directory.

        Args:
            fname: The name of the file.
            key: The key to the file.
        """
        path = Path(self.root_dir).joinpath(ALTO_ROOT, key, fname).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    def executable_path(self, fname: str, remote: bool = False) -> str:
        """Return the path to the PEX executable for a plugin.

        If remote is True, the path will be in the remote storage directory.

        Args:
            fname: The name of the file.
            remote: Whether or not the path should be in the remote storage directory.
        """
        getter = self._remote_path if remote else self._root_path
        return getter(fname=fname, key=PLUGIN_DIR)

    def config_path(self, name: str, accent: t.Optional[str] = None) -> str:
        """Return the path to the config for a plugin.

        This is the path to the config file in the staging directory. These files are not
        stored in the remote storage directory and are generated as required on each run.

        Args:
            name: The name of the plugin.
            accent: The name of the accent.
        """
        return self._temp_path(
            fname=f"{name}.json" if not accent else f"{name}--{accent}.json", key=CONFIG_DIR
        )

    def state_path(self, tap: str, target: str, remote: bool = False) -> str:
        """Return the path to the state for a plugin.

        If remote is True, the path will be in the remote storage directory. The state file is
        named <tap>-to-<target>.json and is automatically partitioned by environment.

        Args:
            tap: The name of the tap.
            target: The name of the target.
            remote: Whether or not the path should be in the remote storage directory.
        """
        getter = self._remote_path if remote else self._temp_path
        return getter(
            fname=f"{tap}-to-{target}.json", key=STATE_DIR.format(env=self.config.current_env)
        )

    def base_catalog_path(self, name: str, remote: bool = False) -> str:
        """Return the path to the base catalog for a plugin.

        If remote is True, the path will be in the remote storage directory.

        Args:
            name: The name of the plugin.
            remote: Whether or not the path should be in the remote storage directory.
        """
        getter = self._remote_path if remote else self._temp_path
        return getter(fname=f"{name}.base.json", key=CATALOG_DIR)

    def catalog_path(self, name: str) -> str:
        """Return the path to the catalog for a plugin.

        Args:
            name: The name of the plugin.
        """
        return self._temp_path(fname=f"{name}.json", key=CATALOG_DIR)

    def log_path(self, fname: str, remote: bool = False) -> str:
        """Return the path to the log for a filename.

        If remote is True, the path will be in the remote storage directory.

        Args:
            fname: The name of the file.
            remote: Whether or not the path should be in the remote storage directory.
        """
        getter = self._remote_path if remote else self._root_path
        return getter(fname=fname, key=LOG_DIR.format(env=self.config.current_env))


class AltoPlugin:
    """A class representing a plugin in the Alto ecosystem."""

    def __init__(self, name: str, typ: PluginType, config: AltoConfiguration) -> None:
        """Initialize the plugin."""
        self.name = name
        self.type = typ
        self.alto = config
        self._spec = self.alto.spec_for(name)
        # Permit dynamic select override local to the cls instance
        self._select = None
        self._retain_hash_rules = True

    @property
    def spec(self) -> DynaBox:
        """Return the spec for the plugin."""
        return self._spec

    @property
    def pip_url(self) -> t.Optional[str]:
        """Return the pip url for the plugin."""
        if self.type == PluginType.UTILITY:
            # Utility plugins can optionally specify a pip_url
            return self.spec.get("pip_url")
        # All other plugins must specify a pip_url
        try:
            return self.spec["pip_url"]
        except KeyError:
            raise KeyError(f"Plugin {self.name} is missing a pip_url.")

    @property
    def parent(self) -> t.Optional["AltoPlugin"]:
        """Return the parent plugin for the plugin."""
        parent = self.spec.get("inherit_from")
        if parent:
            return self.alto.get_plugin(parent)

    @property
    def cache_version(self) -> t.Optional[str]:
        """Return the internal user-defined version for the plugin.

        This is used for cache invalidation and is not the same as the version of the plugin.
        """
        return self.spec.get("_version")

    @property
    def root_namespace(self) -> str:
        """Return the root namespace for the plugin."""
        try:
            return self.alto.inner["LOAD_PATH"]
        except KeyError:
            raise KeyError("Alto is missing a top-level LOAD_PATH.")

    @property
    def namespace(self) -> str:
        """Return the namespace for the plugin."""
        return self.spec.get("load_path", self.root_namespace)

    @property
    def capabilities(self) -> t.List[str]:
        """Return the capabilities for the plugin."""
        return self.spec.get("capabilities", [])

    @property
    def supports_state(self) -> bool:
        """Return whether or not the plugin supports state."""
        return "state" in self.capabilities

    @property
    def supports_about(self) -> bool:
        """Return whether or not the plugin supports about."""
        return "about" in self.capabilities

    @property
    def supports_test(self) -> bool:
        """Return whether or not the plugin supports test."""
        return "test" in self.capabilities

    @property
    def supports_catalog(self) -> bool:
        """Return whether or not the plugin supports catalog."""
        return "catalog" in self.capabilities

    @property
    def supports_properties(self) -> bool:
        """Return whether or not the plugin supports properties."""
        return "properties" in self.capabilities

    @property
    def config(self) -> DynaBox:
        """Return the config for the plugin."""
        return self.spec.get("config", DynaBox())

    @property
    def select(self) -> t.List[str]:
        """Return the select for the plugin."""
        if self._select is None:
            self._select = self.spec.get("select", ["*.*"])
        return self._select

    @select.setter
    def select(self, value: t.List[str]) -> None:
        """Set the select for the plugin."""
        # If we're setting the select, we want to retain any hash rules
        # as PII hashing is a global concern and it should be on the user
        # to _explicitly_ disable it.
        self._select = (value or ["*.*"]) + [
            rule for rule in self.select if rule.startswith("~") and self._retain_hash_rules
        ]

    @property
    def metadata(self) -> t.Dict[str, t.Any]:
        """Return the select for the plugin."""
        return self.spec.get("metadata", {})

    @property
    def entrypoint(self) -> str:
        """Return the entrypoint for the plugin."""
        return self.spec.get("entrypoint", self.spec.get("executable", self.name))

    @property
    def environment(self) -> str:
        """Return env vars necessary to run our PEX executable."""
        typ = "MODULE" if "entrypoint" in self.spec else "SCRIPT"
        return {
            f"PEX_{typ}": self.entrypoint,
            "ALTO_PLUGIN": self.name,
            **self.spec.get("environment", {}),
        }

    def config_relative_to(self, other: "AltoPlugin") -> DynaBox:
        """Return the config for the plugin."""
        return self.config + other.spec.get(self.name, DynaBox())

    @property
    def pex_name(self) -> str:
        """Return the unique name for the pex executable.

        This is used to cache the pex and reuse it across runs and machines.
        """
        pex_hash = sha1(self.pip_url.strip().encode("utf-8"))
        pex_hash.update(platform.python_version().encode("utf-8"))
        pex_hash.update(platform.machine().encode("utf-8"))
        pex_hash.update(platform.system().encode("utf-8"))
        if self.cache_version:
            pex_hash.update(self.cache_version.encode("utf-8"))
        return pex_hash.hexdigest()

    def get_stream_maps(self, filesystem: AltoFileSystem) -> t.List["AltoStreamMap"]:
        """Return the stream maps for the plugin."""
        mappers: t.List[AltoStreamMap] = []
        if not self.type == PluginType.TAP:
            return mappers
        # Built in PII hasher
        hash_rules: t.List[str] = []
        for select in self.select:
            if select.startswith("~"):
                hash_rules.append(select[1:])
        if hash_rules:
            print(f"🕵️‍♀️ Found {len(hash_rules)} hashing rules for {self.name}")
            mappers.append(HashStreamMap(tap_config=self.config, select=hash_rules))
        # Custom stream maps
        # this is simply a path to a python file that contains a register function which
        # returns a class that inherits from AltoStreamMap. Users can define their own
        # stream maps and use them in their alto config file extremely easily.
        for mapper_spec in self.spec.get("stream_maps", []):
            if isinstance(mapper_spec, str):
                mapper_spec = {"path": mapper_spec}
            mapper = mapper_spec["path"]
            select = mapper_spec.get("select", ["*.*"])
            if mapper.startswith("/"):
                mapper_path = Path(mapper).resolve()
            else:
                mapper_path = Path(mapper).resolve().relative_to(filesystem.root_dir)
            if not mapper_path.is_file():
                raise Exception(f"Stream map {mapper} not found")
            try:
                stream_map_ns = load_mapper_from_path(mapper_path)
            except Exception as e:
                raise RuntimeError(f"Failed to load stream map {mapper}") from e
            try:
                stream_map_cls = stream_map_ns.register()
            except (NameError, AttributeError) as e:
                raise AttributeError(
                    f"Extension {mapper} does not have a register function."
                ) from e
            try:
                stream_map = stream_map_cls(tap_config=self.config, select=select)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize stream map {mapper}") from e
            assert isinstance(
                stream_map, AltoStreamMap
            ), "Stream map must inherit from AltoStreamMap"
            print(f"👨‍🔧 Found custom stream map {stream_map.name} for {self.name}")
            mappers.append(stream_map)
        return mappers

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"{self.name} ({self.type})"


class AltoStreamMap:
    """Base class representing a stream map in the Alto ecosystem.

    A stream map is a class that is responsible for transforming the records emitted by
    a tap. This is useful for things like hashing PII or redacting sensitive data but can
    be used for any purpose. From ML models to custom transformations, stream maps are
    extremely flexible and powerful. Alto comes with a built in stream map for hashing
    PII but users can also define their own stream maps by creating a python file that
    contains a register function which returns a class that inherits from AltoStreamMap.
    The user the enables the map for a field by add a `stream_maps` key to a taps config
    in their alto config file. The value of the `stream_maps` key is a list of dicts
    where each dict contains a `path` key which is the path to the python file containing
    the stream map and a `select` key which is a list of globs that match the fields that
    should be transformed by the stream map.
    """

    name: str = "No-Op Stream Map"

    def __init__(self, tap_config: "DynaBox", select: t.List[str]) -> None:
        """Initialize the stream map."""
        self.tap_config = tap_config
        self.select = select
        self.ignore: t.Set[str] = set()

    def crumb_selected(self, crumb: str) -> bool:
        """Return whether or not the crumb is selected.

        The crumb is the full path to the field in the record. This assists developers in
        implementing their own stream maps.
        """
        return any(fnmatch.fnmatch(crumb, pat) for pat in self.select)

    def _stream_selected(self, stream: str) -> bool:
        """Return whether or not the stream is selected."""
        return any(fnmatch.fnmatch(stream, pat.split(".", 1)[0]) for pat in self.select)

    def recursive_schema_apply(
        self, value: t.Any, crumb: str, transformer: t.Callable[[t.Any], t.Any]
    ) -> t.Any:
        """Recursively apply a function to a schema.

        This respects the `select` property of the stream map. The value `crumb` is
        the full path to the field in the schema. This assists developers in
        implementing their own stream maps.
        """
        if value.get("type") == "object":
            for k, v in value.get("properties", {}).items():
                self.recursive_schema_apply(v, f"{crumb}.{k}", transformer)
        elif value.get("type") == "array":
            self.recursive_schema_apply(value["items"], crumb, transformer)
        elif self.crumb_selected(crumb):
            value = transformer(value)
        return value

    def recursive_record_apply(
        self, value: t.Any, crumb: str, transformer: t.Callable[[t.Any], t.Any]
    ) -> t.Any:
        """Recursively apply a function to a record.

        This respects the `select` property of the stream map. The value `crumb` is
        the full path to the field in the record. This assists developers in
        implementing their own stream maps.
        """
        if isinstance(value, dict):
            return {
                k: self.recursive_record_apply(v, f"{crumb}.{k}", transformer)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [self.recursive_record_apply(v, crumb, transformer) for v in value]
        elif self.crumb_selected(crumb):
            return transformer(value)
        return value

    @t.final
    def _transform_schema(self, schema: dict) -> dict:
        """Checks schema message against `select` before passing on."""
        if schema["stream"] in self.ignore:
            # Micro-optimization to reduce cpu cycles
            return schema
        if not self._stream_selected(schema["stream"]):
            self.ignore.add(schema["stream"])
            return schema
        return self.transform_schema(schema)

    def transform_schema(self, schema: dict) -> dict:
        """Transform the schema."""
        return schema

    @t.final
    def _transform_record(self, record: dict) -> dict:
        """Checks record message against `select` before passing on."""
        if record["stream"] in self.ignore:
            # Micro-optimization to reduce cpu cycles
            return record
        if not self._stream_selected(record["stream"]):
            self.ignore.add(record["stream"])
            return record
        return self.transform_record(record)

    def transform_record(self, record: dict) -> dict:
        """Transform the record."""
        return record


class HashStreamMap(AltoStreamMap):
    """Obfuscate PII in the stream.

    This is a stream map that will obfuscate PII in the stream. It is extremely
    accessible and can be used to obfuscate any field in the record. All you need to
    do is add the field to the select list rule in the tap config prefixed with a `~`.

    For example, if you wanted to hash fields named `password`, `email`, `phone`, `ssn`,
    and `credit_card` for all streams, you would add the following to the tap config:

        "select": ["*.*", "~*.password", "~*.email", "~*.phone", "~*.ssn", "~*.credit_card"]

    """

    name: str = "PII Hasher Stream Map"

    def _jsonschema_string(self, value: t.Any) -> t.Any:
        """Return a JSON schema string type."""
        return {"type": "string", "format": "hash"}

    def transform_schema(self, schema: dict) -> dict:
        """Transform the schema."""
        for k, prop in schema["schema"]["properties"].items():
            schema["schema"]["properties"][k] = self.recursive_schema_apply(
                prop, f"{schema['stream']}.{k}", self._jsonschema_string
            )
        return schema

    def _pii_hash(self, value: t.Any) -> t.Any:
        """Hash a value."""
        return md5(str(value).encode("utf-8")).hexdigest()

    def transform_record(self, record: dict) -> dict:
        """Transform the record."""
        for k in record["record"]:
            record["record"][k] = self.recursive_record_apply(
                record["record"][k], f"{record['stream']}.{k}", self._pii_hash
            )
        return record


class AltoExtension:
    """A class representing an extension in the Alto ecosystem."""

    def __init__(
        self,
        filesystem: AltoFileSystem,
        configuration: AltoConfiguration,
        run_task: t.Callable[[t.List[str]], int],
    ) -> None:
        """Initialize the extension."""
        self.filesystem = filesystem
        self.configuration = configuration
        self.run_task = run_task
        self.init_hook()

    @property
    def name(self) -> str:
        """Return the name of the extension.

        This can be overridden by the subclass. By default, it is the name of the class.
        """
        return self.__class__.__name__.lower()

    @property
    def spec(self):
        """Return the extension spec."""
        return self.configuration.spec_for(self.name)

    def init_hook(self) -> None:
        """Called when the extension is initialized.

        This is called before any tasks are generated.
        """
        pass

    @staticmethod
    def get_validators() -> t.List["Validator"]:
        """Return the validators for the extension."""
        return []

    def remote_path(self, name: str) -> str:
        """Return a remote path. Use this to persist data for the extension.

        Data pushed here is cached.
        """
        return self.filesystem._remote_path(name, key=self.name)

    def temp_path(self, name: str) -> str:
        """Return a temp path. Use this to persist data for the extension.

        Data pushed here is not cached and is cleaned up.
        """
        return self.filesystem._temp_path(name, key=self.name)

    def root_path(self, name: str) -> str:
        """Return a root path. Use this to persist data for the extension.

        Data pushed here is not cached and is not cleaned up.
        """
        return self.filesystem._root_path(name, key=self.name)

    def tasks(self) -> t.Generator[AltoTaskData, None, None]:
        """Return the tasks for the extension."""
        yield from ()

    def _tasks(self) -> t.Generator[AltoTaskData, None, None]:
        """Return the tasks for the extension.

        Not used but exists as reference to a good pattern.
        """
        for task in self.tasks():
            for i, action in enumerate(task["actions"]):
                if isinstance(action, str):
                    task["actions"][i] = CmdAction(action, env=os.environ)
            yield task


class AltoTaskEngine(DoitEngine):
    """The alto task engine builds on top of doit to provide a simple interface for Singer tasks.

    The engine is responsible for loading the configuration, loading the extensions, building and
    executing plugins, and user-specific build tasks supplied via the extension interface.
    """

    Configuration = AltoConfiguration
    FileSystem = AltoFileSystem

    def __init__(
        self,
        root_dir: Path = Path.cwd(),
        config: t.Optional[t.Union["Dynaconf", t.Dict[str, t.Any]]] = None,
    ) -> None:
        """Initialize the alto task engine.

        Args:
            root_dir: The root directory of the project. This is where the configuration is
                loaded from if no configuration is provided. Defaults to the current working
                directory.
            config: The configuration to use. If this is a dictionary, it will be written to a
                temporary file and loaded. If this is a Dynaconf object, it will be used directly.
                If this is None, the configuration will be loaded from the root directory.
        """
        super().__init__()
        from dynaconf import Dynaconf

        kwargs = {
            "root_path": root_dir,
            "envvar_prefix": "ALTO",
            "env_switcher": "ALTO_ENV",
            "load_dotenv": True,
            "environments": True,
            "merge_enabled": True,
        }
        if config is None:
            # Default to loading the configuration from the root directory
            stack = itertools.chain(
                root_dir.glob("alto.*.toml"),
                root_dir.glob("alto.*.json"),
                root_dir.glob("alto.*.yaml"),
            )
            # Load the configuration
            self.alto = Dynaconf(
                settings_files=[
                    root_dir.joinpath(f"alto.{fmt}") for fmt in SUPPORTED_CONFIG_FORMATS
                ],
                includes=[str(s) for s in stack if s.is_file() and "secrets" not in s.name],
                secrets=[
                    root_dir.joinpath(f"alto.secrets.{fmt}") for fmt in SUPPORTED_CONFIG_FORMATS
                ],
                **kwargs,
            )
        elif isinstance(config, Dynaconf):
            # Use the user-provided configuration object
            self.alto = config
        elif isinstance(config, dict):
            # Write the configuration to a temporary file and load it
            from tempfile import NamedTemporaryFile

            with NamedTemporaryFile(mode="w", suffix=".json") as f:
                f.write(json.dumps(config))
                self.alto = Dynaconf(
                    settings_files=[f.name],
                    root_path=root_dir,
                    **kwargs,
                )
        # Instantiate the filesystem and configuration
        self.configuration = AltoTaskEngine.Configuration(inner=self.alto)
        self.filesystem = AltoTaskEngine.FileSystem(root_dir, config=self.configuration)
        self.extensions: t.List[AltoExtension] = []

    @property
    def fs(self) -> fsspec.spec.AbstractFileSystem:
        """Return the filesystem."""
        return self.filesystem.fs

    def setup(self, opt_values: t.Optional[t.Dict[str, t.Any]] = None) -> None:
        """Load extensions and filesystem interface. This is called by doit."""
        if opt_values is None:
            opt_values = {}
        # Set the environment variables
        for k, v in self.alto.get("ENVIRONMENT", {}).items():
            os.environ[k] = str(v)
        # Load the extensions
        self._load_extensions()
        # Validate the configuration
        self.alto.validators.validate_all()

    def _load_extensions(self) -> None:
        """Load the extensions from the configuration file.

        Extensions are python files that are loaded and executed at runtime. They
        are used to add custom tasks to the alto engine. The API for extensions
        is simple. The extension file must contain a function named `register`
        that returns a subclass of AltoExtension as a type. `Type[AltoExtension]`
        """
        for extension in t.cast(t.List[str], self.alto.get("EXTENSIONS", [])):
            # Built-in extensions
            if extension in {"evidence", "rill"}:
                ns = load_extension_from_spec(f"alto.ext.{extension}")
                ext_cls = ns.register()
                for validator in ext_cls.get_validators():
                    # Validators can also seed configuration
                    # so we must run them before instantiating the extension
                    validator.validate(self.alto)
                ext = ext_cls(
                    filesystem=self.filesystem,
                    configuration=self.configuration,
                    run_task=self.__call__,
                )
                self.extensions.append(ext)
                continue
            # External extensions
            py = self.filesystem.root_dir / extension
            if not py.is_file():
                raise ValueError(f"Extension {extension} does not exist.")
            try:
                ext_ns = load_extension_from_path(py)
            except Exception as e:
                raise RuntimeError(f"Extension {extension} failed to load.") from e
            try:
                ext_cls = ext_ns.register()
            except (NameError, AttributeError) as e:
                raise AttributeError(
                    f"Extension {extension} does not have a register function."
                ) from e
            try:
                ext = ext_cls(
                    filesystem=self.filesystem,
                    configuration=self.configuration,
                    run_task=self.__call__,
                )
            except Exception as e:
                raise RuntimeError(f"Extension {extension} failed to instantiate.") from e
            assert isinstance(ext, AltoExtension), f"{ext} is not an AltoExtension"
            self.extensions.append(ext)

    def load_doit_config(self) -> t.Dict[str, t.Any]:
        """Load the doit configuration. This is called by doit."""
        if bool(os.getenv("ALTO_RICH_UI")):
            # If the user has opted into the rich UI, we will try to instantiate it.
            # If it is not available, we will fall back to the default reporter.
            try:
                ui = AltoRichUI(None, {"verbosity": 2})
            except ImportError:
                ui = AltoEmojiUI(sys.stdout, {"verbosity": 2})
        else:
            ui = AltoEmojiUI(sys.stdout, {"verbosity": 2})
        return AltoEngineConfig(
            default_tasks=[AltoCmd.BUILD],
            reporter=ui,
            dep_file=str(self.filesystem.root_dir / ALTO_DB_FILE),
            backend="json",
            verbosity=2,
            par_type="thread",
            failure_verbosity=2,
        )

    def __call__(self, *args) -> int:
        """Execute a configured task by name with the alto task engine."""
        from alto.main import AltoRun

        return AltoRun(
            task_loader=self,
            bin_name="alto",
            config={},
            opt_vals={},
        ).parse_execute(list(args))

    # ===== #
    # Tasks #
    # ===== #

    def task_build(self) -> AltoTaskGenerator:
        """[core] Generate pex plugin based on the alto config."""

        for plugin in self.configuration.plugins():
            # Skip plugins that do not have a pip_url
            if not plugin.pip_url:
                continue
            task = AltoTask(name=plugin.name).set_doc(f"Build the {plugin} plugin").set_verbosity(2)
            if plugin.parent is None:
                # If the plugin does not inherit from another plugin, build it
                task = (
                    task.set_actions((build_pex, (plugin, self.filesystem)))
                    .set_uptodate((maybe_get_pex, (plugin, self.filesystem)))
                    .set_clean((maybe_remove_pex, (plugin, self.filesystem)))
                )
            else:
                # If the plugin inherits from another plugin, just ensure the parent is built
                task.set_task_dep(f"{AltoCmd.BUILD}:{plugin.parent}")
            yield task.data

    def task_config(self) -> AltoTaskGenerator:
        """[core] Generate configuration files on disk."""

        config_lock = threading.Lock()
        for plugin in self.configuration.plugins(PluginType.TAP, PluginType.TARGET):
            yield (
                AltoTask(name=plugin.name)
                .set_actions((render_config, (plugin, config_lock, self.alto, self.filesystem)))
                .set_uptodate(False)
                .set_doc(f"Render configuration for the {plugin} plugin")
                .data
            )

        # Tap Aware Combinatorial Configs
        for tap, target in itertools.product(
            self.configuration.plugins(PluginType.TAP),
            self.configuration.plugins(PluginType.TARGET),
        ):
            yield (
                AltoTask(name=f"{target}--{tap}")
                .set_actions(
                    (render_config, (target, config_lock, self.alto, self.filesystem, tap))
                )
                .set_uptodate(False)
                .set_doc(f"Render configuration for the {target} plugin with {tap} as source")
                .data
            )

    def task_catalog(self) -> AltoTaskGenerator:
        """[singer] Generate base catalog file for a Singer tap.

        These catalogs are used as the basis for applying metadata rules and selections.
        Use `doit clean catalog:plugin-name` to force a rebuild of one or more base catalogs.
        """

        for tap in self.configuration.plugins(PluginType.TAP):
            yield (
                AltoTask(name=tap.name)
                .set_actions((generate_catalog, (tap, self.filesystem)))
                .set_task_dep(f"{AltoCmd.BUILD}:{tap}")
                .set_setup(f"{AltoCmd.CONFIG}:{tap}")
                .set_uptodate((maybe_get_catalog, (tap, self.filesystem)))
                .set_clean((clean_catalog, (tap, self.filesystem)))
                .set_doc(f"Generate base catalog for {tap}")
                .data
            )

    def task_apply(self) -> AltoTaskGenerator:
        """[singer] Apply user config to base catalog file."""

        for tap in self.configuration.plugins(PluginType.TAP):
            yield (
                AltoTask(name=tap.name)
                .set_actions((render_modified_catalog, (tap, self.filesystem)))
                .set_task_dep(f"{AltoCmd.CATALOG}:{tap}")
                .set_uptodate(
                    Path(self.filesystem.catalog_path(tap.name)).exists,
                    config_changed({"select": tap.select, "metadata": tap.metadata}),
                )
                .set_doc(f"Render runtime catalog for {tap}")
                .data
            )

    def task_about(self) -> AltoTaskGenerator:
        """[singer] Run the about command for a Singer tap."""
        for tap in self.configuration.plugins(PluginType.TAP):
            bin = self.filesystem.executable_path(tap.pex_name)
            config = self.filesystem.config_path(tap.name)
            if not tap.supports_about:
                continue
            # TODO: Use subprocess
            yield (
                AltoTask(name=tap.name)
                .set_actions(f"{bin} --about --config {config}")
                .set_uptodate(False)
                .set_file_dep(bin, config)
                .set_doc(f"Run about for {tap}")
                .set_verbosity(2)
                .data
            )

    def task_pipeline(self) -> AltoTaskGenerator:
        """[singer] Execute a data pipeline."""

        # Combinatorial product of all taps and targets
        for tap, target in itertools.product(
            self.configuration.plugins(PluginType.TAP),
            self.configuration.plugins(PluginType.TARGET),
        ):
            # Tap -> Target
            pipeline_id = uuid.uuid4()
            yield (
                AltoTask(name=target.name)
                .set_basename(tap.name)
                .set_actions(
                    (
                        get_remote_state,
                        (tap.name, target.name, self.filesystem, tap.supports_state),
                    ),
                    (run_pipeline, (tap, target, pipeline_id, self.filesystem)),
                )
                .set_task_dep(
                    f"{AltoCmd.BUILD}:{tap}", f"{AltoCmd.APPLY}:{tap}", f"{AltoCmd.BUILD}:{target}"
                )
                .set_setup(f"{AltoCmd.CONFIG}:{target}--{tap}", f"{AltoCmd.CONFIG}:{tap}")
                .set_teardown(
                    (
                        update_remote_state,
                        (tap.name, target.name, pipeline_id, self.filesystem, tap.supports_state),
                    ),
                    (upload_logs, (tap.name, target.name, pipeline_id, self.filesystem)),
                )
                .set_clean(
                    (self.fs.rm, (self.filesystem.state_path(tap.name, target.name, remote=True),))
                )
                .set_uptodate(False)
                .set_doc(f"Run the {tap} to {target} data pipeline")
                .set_verbosity(2)
                .data
            )

        for tap, target in itertools.product(
            self.configuration.plugins(PluginType.TAP),
            self.configuration.plugins(PluginType.TARGET),
        ):
            # Reservoir[Tap] -> Target
            pipeline_id = uuid.uuid4()
            tap_reservoir = tap.name.replace("tap", "reservoir")
            yield (
                AltoTask(name=f"{tap}-{target}")
                .set_basename("reservoir")
                .set_actions(
                    (get_remote_state, (tap_reservoir, target.name, self.filesystem, True)),
                    (
                        reservoir_to_target,
                        (tap, target, pipeline_id, self.filesystem, self.alto.current_env),
                    ),
                )
                .set_task_dep(f"{AltoCmd.BUILD}:{target}")
                .set_setup(f"{AltoCmd.CONFIG}:{target}--{tap}")
                .set_teardown(
                    (update_remote_state_no_stdout, (tap_reservoir, target.name, self.filesystem)),
                    (upload_logs, (tap.name, target.name, pipeline_id, self.filesystem)),
                )
                .set_clean(
                    (
                        self.fs.rm,
                        (self.filesystem.state_path(tap_reservoir, target.name, remote=True),),
                    )
                )
                .set_uptodate(False)
                .set_doc(
                    f"Run the {tap} to {target} data pipeline from the reservoir to the target"
                )
                .set_verbosity(2)
                .data
            )

        for tap in self.configuration.plugins(PluginType.TAP):
            # Tap -> Reservoir
            pipeline_id = uuid.uuid4()
            target = "reservoir"
            yield (
                AltoTask(name=target)
                .set_basename(tap.name)
                .set_actions(
                    (get_remote_state, (tap.name, target, self.filesystem, tap.supports_state)),
                    (
                        tap_to_reservoir,
                        (
                            tap,
                            pipeline_id,
                            self.filesystem,
                            self.alto.current_env,
                            self.alto.get("RESERVOIR_BUFFER_SIZE", RESERVOIR_BUFFER_SIZE),
                        ),
                    ),
                )
                .set_task_dep(f"{AltoCmd.BUILD}:{tap}", f"{AltoCmd.APPLY}:{tap}")
                .set_setup(f"{AltoCmd.CONFIG}:{tap}")
                .set_teardown(
                    (update_remote_state_no_stdout, (tap.name, target, self.filesystem)),
                    (upload_logs, (tap.name, target, pipeline_id, self.filesystem)),
                )
                .set_clean((compact_reservoir, (tap,)))
                .set_uptodate(False)
                .set_doc(f"Run the {tap} to {target} data pipeline to the reservoir from the tap")
                .set_verbosity(2)
                .data
            )

    def task_test(self) -> AltoTaskGenerator:
        """[singer] Run tests for taps."""

        for tap in self.configuration.plugins(PluginType.TAP):
            yield (
                AltoTask(name=tap.name)
                .set_actions((run_test, (tap, self.filesystem, tap.supports_test)))
                .set_task_dep(f"{AltoCmd.BUILD}:{tap}", f"{AltoCmd.APPLY}:{tap}")
                .set_setup(f"{AltoCmd.CONFIG}:{tap}")
                .set_uptodate(False)
                .set_doc(f"Test the {tap} plugin")
                .set_verbosity(2)
                .data
            )

    def load_tasks(self, cmd: AltoCmdBase, pos_args) -> t.List[AltoTaskData]:
        """Loads Alto tasks."""
        return list(
            itertools.chain(
                generate_tasks(AltoCmd.BUILD, self.task_build(), self.task_build.__doc__),
                generate_tasks(AltoCmd.CONFIG, self.task_config(), self.task_config.__doc__),
                generate_tasks(AltoCmd.CATALOG, self.task_catalog(), self.task_catalog.__doc__),
                generate_tasks(AltoCmd.APPLY, self.task_apply(), self.task_apply.__doc__),
                generate_tasks(AltoCmd.PIPELINE, self.task_pipeline(), self.task_pipeline.__doc__),
                generate_tasks(AltoCmd.TEST, self.task_test(), self.task_test.__doc__),
                generate_tasks(AltoCmd.ABOUT, self.task_about(), self.task_about.__doc__),
                *(
                    generate_tasks(ext.name, ext.tasks(), f"[extension] {ext.__doc__}")
                    for ext in self.extensions
                ),
            )
        )


# ================= #
# Stream Map Engine #
# ================= #


def map_worker(
    instream: t.IO[bytes], outstream: t.IO[bytes], mappers: t.List[AltoStreamMap]
) -> None:
    """Read JSON lines from a stream and write them to another stream."""
    for line in instream:
        if not line.strip():
            continue
        if not mappers:
            # no mappers, just pass through
            outstream.write(line)
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if message["type"] == "RECORD":
            for mapper in mappers:
                message = mapper.transform_record(message)
        elif message["type"] == "SCHEMA":
            for mapper in mappers:
                message = mapper.transform_schema(message)
        else:
            outstream.write(line)
            continue
        if message:
            outstream.write(json.dumps(message).encode("utf-8") + b"\n")


# ==================== #
# Realtime Log Capture #
# ==================== #


def pipe_logger(stream: t.IO[bytes], path: str, lock: threading.Lock) -> None:
    """Log a stream to the console."""
    with open(path, "wb") as log_data:
        for line in stream:
            log_data.write(line)
            with lock:
                print(line.decode("utf-8"), end="", flush=True)


# =============== #
# Pipeline Runner #
# =============== #


def run_pipeline(
    tap: AltoPlugin,
    target: AltoPlugin,
    pipeline_id: str,
    filesystem: AltoFileSystem,
) -> None:
    """Execute a data pipeline."""
    tap_bin, tap_config, tap_catalog = (
        filesystem.executable_path(tap.pex_name),
        filesystem.config_path(tap.name),
        filesystem.catalog_path(tap.name),
    )
    target_bin, target_config = (
        filesystem.executable_path(target.pex_name),
        filesystem.config_path(target.name, tap.name),
    )
    state = filesystem.state_path(tap.name, target.name)
    cmd = [tap_bin, "--config", tap_config]
    if os.path.isfile(state) and tap.supports_state:
        cmd += ["--state", state]
    if tap.supports_catalog:
        cmd += ["--catalog", tap_catalog]
    elif tap.supports_properties:
        cmd += ["--properties", tap_catalog]
    print(f"Running pipeline {pipeline_id} ({tap} -> {target})")
    stdout_lock = threading.Lock()
    mappers = tap.get_stream_maps(filesystem)
    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, **tap.environment},
        cwd=filesystem.root_dir,
    ) as tap_proc, open(
        filesystem.log_path(f"state-{pipeline_id}.log"), "w"
    ) as state_log, subprocess.Popen(
        [target_bin, "--config", target_config],
        stdin=tap_proc.stdout if not mappers else subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdout=state_log,
        env={**os.environ, **target.environment},
        cwd=filesystem.root_dir,
    ) as target_proc:
        t1 = threading.Thread(
            target=pipe_logger,
            args=(
                tap_proc.stderr,
                filesystem.log_path(f"tap-{pipeline_id}.log"),
                stdout_lock,
            ),
            daemon=True,
        )
        t2 = threading.Thread(
            target=pipe_logger,
            args=(
                target_proc.stderr,
                filesystem.log_path(f"target-{pipeline_id}.log"),
                stdout_lock,
            ),
            daemon=True,
        )
        t1.start(), t2.start()
        if mappers:
            # Prevent the mapper worker from blocking the pipeline
            map_thread = threading.Thread(
                target=map_worker,
                args=(tap_proc.stdout, target_proc.stdin, mappers),
                daemon=True,
            )
            map_thread.start()
        tap_proc.wait()
        print(f"Tap {tap} exited with code {tap_proc.returncode}")
        if mappers:
            print("Awaiting mapper to complete...")
            map_thread.join()
            target_proc.stdin.close()
        print("Awaiting target process to complete...")
        target_proc.wait()
        print(f"Target {target} exited with code {target_proc.returncode}")
        if tap_proc.returncode != 0:
            raise subprocess.CalledProcessError(tap_proc.returncode, cmd)
        if target_proc.returncode != 0:
            raise subprocess.CalledProcessError(target_proc.returncode, cmd)
        t1.join(), t2.join()


# ================ #
# State Management #
# ================ #


def get_remote_state(
    tap: str,
    target: str,
    filesystem: AltoFileSystem,
    execute: bool = True,
) -> None:
    """Download the remote state file."""
    if execute:
        remote_state = filesystem.state_path(tap, target, remote=True)
        if filesystem.fs.exists(remote_state):
            filesystem.fs.get(remote_state, filesystem.state_path(tap, target))


def update_remote_state(
    tap: str, target: str, pipeline_id: str, filesystem: AltoFileSystem, execute: bool = True
) -> None:
    """Update the remote state file."""
    if execute:
        stdout = Path(filesystem.log_path(f"state-{pipeline_id}.log"))
        if not stdout.exists() or stdout.stat().st_size == 0:
            return
        state = Path(filesystem.state_path(tap, target))
        remote_state = filesystem.state_path(tap, target, remote=True)
        ensure_state(state)
        update_state(state, stdout)
        ts = datetime.datetime.now().strftime("%Y%m%d%H%M")
        # Keep a mutable and immutable copy of the state file for recovery / analysis
        filesystem.fs.put(filesystem.state_path(tap, target), remote_state)
        filesystem.fs.put(
            filesystem.state_path(tap, target),
            remote_state[:-5] + f".{ts}.json",
        )
        stdout.unlink()


def update_remote_state_no_stdout(
    tap: str,
    target: str,
    filesystem: AltoFileSystem,
) -> None:
    """Update the remote state file directly.

    Used for the reservoir emitter.
    """
    local_path, remote_state = (
        filesystem.state_path(tap, target),
        filesystem.state_path(tap, target, remote=True),
    )
    ensure_state(local_path)
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M")
    # Keep a mutable and immutable copy of the state file for recovery / analysis
    filesystem.fs.put(local_path, remote_state)
    filesystem.fs.put(local_path, remote_state[:-5] + f".{ts}.json")
    print(f"Updated state file for {tap} -> {target}.")
    print(f"Remote state file: {remote_state}")


# ================ #
# Log Preservation #
# ================ #


def upload_logs(
    tap: str,
    target: str,
    pipeline_id: str,
    filesystem: AltoFileSystem,
) -> None:
    """Upload the logs for a pipeline run and remove from system."""
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M")
    tap_path, tap_dest = (
        Path(filesystem.log_path(f"tap-{pipeline_id}.log")),
        filesystem.log_path(f"{ts}--{tap}--{pipeline_id}.log", remote=True),
    )
    target_path, target_dest = (
        Path(filesystem.log_path(f"target-{pipeline_id}.log")),
        filesystem.log_path(f"{ts}--{target}--{pipeline_id}.log", remote=True),
    )
    if tap_path.exists():
        filesystem.fs.put(str(tap_path.resolve()), tap_dest), tap_path.unlink()
        print(f"Uploaded tap log for pipeline {pipeline_id} to {tap_dest}")
    if target_path.exists():
        filesystem.fs.put(str(target_path.resolve()), target_dest), target_path.unlink()
        print(f"Uploaded target log for pipeline {pipeline_id} to {target_dest}")


# ============== #
# Data Reservoir #
# ============== #


def reservoir_ingestor(
    stdout: t.IO[bytes],
    reservoir: t.Dict[str, t.List[str]],
    record_key: str,
    state_path: str,
    pipeline_id: str,
    filesystem: AltoFileSystem,
    stream_states: t.Optional[t.Dict[str, t.Any]] = None,
    buffer_size=RESERVOIR_BUFFER_SIZE,
    mappers: t.Optional[t.List[AltoStreamMap]] = None,
) -> None:
    """Primary ingestion loop for the reservoir."""
    from concurrent.futures import ThreadPoolExecutor

    # Set up
    if stream_states is None:
        stream_states = {}
    if mappers is None:
        mappers = []
    record_buffer = {}
    active_schemas = {}

    # Start the ingestion loop
    tpe = ThreadPoolExecutor(max_workers=os.cpu_count())
    for line in stdout:
        try:
            message = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError:
            pass

        # Handle the state message
        if message["type"] == "STATE":
            merge(message["value"], stream_states)
            with open(state_path, "w") as f:
                json.dump(stream_states, f)
            continue
        stream = message["stream"]

        # Handle the schema message
        if message["type"] == "SCHEMA":
            for mapper in mappers:
                message = mapper.transform_schema(message)
            schema_id = md5(
                json.dumps(message["schema"], sort_keys=True).encode("utf-8")
            ).hexdigest()[:15]
            if stream not in record_buffer or schema_id not in record_buffer[stream]:
                # New stream
                print(f"New stream: {stream} ({schema_id})")
                buf, header = gzip.GzipFile(fileobj=io.BytesIO(), mode="wb"), line + b"\n"
                buf.write(header)
                record_buffer[stream] = {
                    schema_id: {
                        "count": 0,
                        "schema": message,
                        "header": header,
                        "records": buf,
                    }
                }
            active_schemas[stream] = schema_id

        # Handle the record message
        elif message["type"] == "RECORD":
            for mapper in mappers:
                message = mapper.transform_record(message)
            container = record_buffer[stream][active_schemas[stream]]
            container["count"] += 1
            container["records"].write(line + b"\n")
            if container["count"] >= buffer_size:
                # Buffer is full, flush to filesystem
                print(f"Flushing {stream} ({active_schemas[stream]})")
                ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
                path = filesystem._remote_path(
                    f"{ts}.singer.gz",
                    key=record_key.format(stream=stream, schema_id=active_schemas[stream]),
                )
                _buf: gzip.GzipFile = container["records"]
                inner_buf: io.BytesIO = _buf.fileobj
                _buf.close()
                inner_buf.flush(), inner_buf.seek(0)
                tpe.submit(filesystem.fs.pipe, path, inner_buf.getvalue())
                # Reset the buffer
                container["count"] = 0
                inner_buf.truncate(0), inner_buf.seek(0)
                new_buf = gzip.GzipFile(fileobj=inner_buf, mode="wb")
                new_buf.write(container["header"])
                container["records"] = new_buf
                # Update the index
                if stream not in reservoir:
                    reservoir[stream] = []
                reservoir[stream].append(path)
                # Write path to pipeline log file
                with open(filesystem.log_path(f"target-{pipeline_id}.log"), "a") as f:
                    f.write(f"{path}\n")
                # Write actualized state to the remote storage directory
                with open(state_path, "w") as state_data:
                    json.dump(stream_states, state_data)

    # Flush the remaining records
    print("Flushing remaining records")
    for stream, schemas in record_buffer.items():
        for schema_id, container in schemas.items():
            if container["count"] == 0:
                continue
            ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
            path = filesystem._remote_path(
                f"{ts}.singer.gz",
                key=record_key.format(stream=stream, schema_id=active_schemas[stream]),
            )
            _buf: gzip.GzipFile = container["records"]
            inner_buf: io.BytesIO = _buf.fileobj
            _buf.close()
            inner_buf.flush(), inner_buf.seek(0)
            tpe.submit(filesystem.fs.pipe, path, inner_buf.getvalue())
            # Update the index
            if stream not in reservoir:
                reservoir[stream] = []
            reservoir[stream].append(path)
            # Write path to pipeline log file
            with open(filesystem.log_path(f"target-{pipeline_id}.log"), "a") as f:
                f.write(f"{path}\n")

    # Write actualized state to the remote storage directory
    tpe.shutdown()
    print("Writing final state")
    with open(state_path, "w") as state_data:
        json.dump(stream_states, state_data)


# TODO: Add retry decorator
def reservoir_emitter(
    stdin: t.IO[bytes], path: str, filesystem: AltoFileSystem, lock: threading.Lock
) -> str:
    """Emits records from the reservoir to the target.

    This function is intended to be used as a target for a
    concurrent.futures.ThreadPoolExecutor, and is responsible
    for pulling data from the reservoir, decompressing, and
    emitting it to the stdin handle of the target process.
    """
    stream = gzip.decompress(filesystem.fs.cat(path))
    with lock:
        # Write the records to the target's stdin handle with a lock
        stdin.writelines((line + b"\n") for line in stream.splitlines() if line)
    return path


def tap_to_reservoir(
    tap: AltoPlugin,
    pipeline_id: str,
    filesystem: AltoFileSystem,
    env: str,
    buffer_size: int = RESERVOIR_BUFFER_SIZE,
) -> None:
    """Execute a data pipeline to the project reservoir."""
    # Set up
    target = "reservoir"
    tap_bin, tap_config, tap_catalog = (
        filesystem.executable_path(tap.pex_name),
        filesystem.config_path(tap.name),
        filesystem.catalog_path(tap.name),
    )
    stream_states = {}
    state = filesystem.state_path(tap.name, target)
    base_path = f"{target}/{env}/{tap}"

    # Build the command to run the pipeline
    cmd = [tap_bin, "--config", tap_config]
    if os.path.isfile(state) and tap.supports_state:
        # Load the last state
        with open(state) as state_file:
            stream_states = json.load(state_file)
        cmd += ["--state", state]
    if tap.supports_catalog:
        cmd += ["--catalog", tap_catalog]
    elif tap.supports_properties:
        cmd += ["--properties", tap_catalog]

    # Load the index
    index_path = filesystem._remote_path("_reservoir.json", key=base_path)
    reservoir = {}
    if filesystem.fs.exists(index_path):
        reservoir = json.loads(filesystem.fs.cat(index_path).decode("utf-8"))

    # Create a lock file to prevent multiple runs of the same pipeline / env
    lock_path = filesystem._remote_path("_reservoir.lock", key=base_path)
    if filesystem.fs.exists(lock_path):
        raise RuntimeError(f"Lock file {lock_path} exists, aborting")
    filesystem.fs.pipe(lock_path, f"{pipeline_id}".encode("utf-8"))

    try:
        # Start the pipeline
        print(f"Running pipeline {pipeline_id} ({tap} -> {target})")
        stdout_lock = threading.Lock()
        mappers = tap.get_stream_maps(filesystem)
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, **tap.environment},
            cwd=filesystem.root_dir,
        ) as tap_proc:
            # Stream stderr
            t1 = threading.Thread(
                target=pipe_logger,
                args=(
                    tap_proc.stderr,
                    filesystem.log_path(f"tap-{pipeline_id}.log"),
                    stdout_lock,
                ),
                daemon=True,
            )
            t1.start()
            # Stream the tap output to the reservoir mutating the reservoir index and
            # the state file. Blocks until the tap process exits. The `finally` statement
            # updates the reservoir index and drops the lock file allowing the next run to proceed.
            reservoir_ingestor(
                stdout=tap_proc.stdout,
                reservoir=reservoir,
                record_key=base_path + "/{stream}/{schema_id}",
                state_path=state,
                pipeline_id=pipeline_id,
                filesystem=filesystem,
                stream_states=stream_states,
                buffer_size=buffer_size,
                mappers=mappers,
            )
            tap_proc.wait(), t1.join()
    finally:
        # Load the reservoir index from the remote storage directory
        filesystem.fs.pipe(index_path, json.dumps(reservoir).encode("utf-8"))
        # Drop the lock file
        filesystem.fs.delete(lock_path)


def reservoir_to_target(
    tap: AltoPlugin,
    target: AltoPlugin,
    pipeline_id: str,
    filesystem: AltoFileSystem,
    env: str,
) -> None:
    """Execute a data pipeline from the project reservoir."""
    from collections import OrderedDict
    from concurrent.futures import ThreadPoolExecutor

    # Set up
    target_bin, target_config = (
        filesystem.executable_path(target.pex_name),
        filesystem.config_path(target.name, tap.name),
    )
    state = filesystem.state_path(tap.name.replace("tap", "reservoir"), target.name)

    # Load the stream states
    stream_states = {}
    if os.path.isfile(state):
        with open(state) as state_data:
            stream_states = json.load(state_data)
    stream_states.setdefault(RESERVOIR_VERSION_KEY, 0)

    # Load the index
    base_path = f"reservoir/{env}/{tap}"
    index_path = filesystem._remote_path("_reservoir.json", key=base_path)
    if not filesystem.fs.exists(index_path):
        print("Reservoir index not found, rebuilding")
        reservoir = {RESERVOIR_VERSION_KEY: 0}
        streams = (
            [
                stream_directory.split("/")[-1]
                for stream_directory in filesystem.fs.ls(base_path, detail=False)
                if not filesystem.fs.isfile(stream_directory)
            ]
            if filesystem.fs.exists(base_path)
            else []
        )
        for stream in streams:
            reservoir[stream] = list(
                sorted(
                    filesystem.fs.glob(
                        filesystem._remote_path("**.singer.gz", key=f"{base_path}/{stream}")
                    )
                )
            )
        filesystem.fs.pipe(
            filesystem._remote_path("_reservoir.json", key=base_path),
            json.dumps(reservoir).encode("utf-8"),
        )
        print("Reservoir index rebuilt")
    else:
        reservoir: t.Dict[str, t.List[str]] = json.loads(
            filesystem.fs.cat(index_path).decode("utf-8")
        )

    # Recreate the state file if the index has changed (from a compaction)
    stream_states.setdefault(RESERVOIR_VERSION_KEY, 0)
    reservoir.setdefault(RESERVOIR_VERSION_KEY, 0)
    if stream_states[RESERVOIR_VERSION_KEY] != reservoir[RESERVOIR_VERSION_KEY]:
        print("Index has changed, recreating state file")
        for stream, paths in reservoir.items():
            # Skip stuff we never saw before
            if stream in (RESERVOIR_VERSION_KEY,) or stream not in stream_states:
                continue
            # Update the state
            for path in sorted(paths):
                fname = path.split("/")[-1]
                if fname > stream_states[stream]["emitted"]:
                    stream_states[stream]["emitted"] = fname
        stream_states[RESERVOIR_VERSION_KEY] = reservoir[RESERVOIR_VERSION_KEY]
        with open(state, "w") as state_dest:
            json.dump(stream_states, state_dest)
        print("Index version:", stream_states[RESERVOIR_VERSION_KEY])

    # Start the pipeline
    print(f"Running pipeline {pipeline_id} ({tap} -> {target})")
    stdout_lock = threading.Lock()
    reservoir_lock = threading.Lock()
    with subprocess.Popen(
        [target_bin, "--config", target_config],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        env={**os.environ, **target.environment},
        cwd=filesystem.root_dir,
    ) as target_proc:
        # Stream stderr
        th = threading.Thread(
            target=pipe_logger,
            args=(
                target_proc.stderr,
                filesystem.log_path(f"target-{pipeline_id}.log"),
                stdout_lock,
            ),
            daemon=True,
        )
        th.start()

        # Batch the reservoir paths by schema
        tpe = ThreadPoolExecutor(max_workers=os.cpu_count())
        files_processed = 0
        for stream, paths in reservoir.items():
            # Gather the paths to process
            if stream in (RESERVOIR_VERSION_KEY,):
                continue
            if stream not in stream_states:
                # Our bookmarks are alphanumerically sortable, so gt is sufficient
                stream_states[stream] = {"emitted": ""}
            work_queue = [
                path for path in paths if path.split("/")[-1] > stream_states[stream]["emitted"]
            ]
            if not work_queue:
                continue

            # Partition the paths by schema
            paths_by_schema: t.Dict[str, t.List[t.Tuple[str, int]]] = OrderedDict()
            for path in work_queue:
                schema = path.split("/")[-2]
                if schema not in paths_by_schema:
                    paths_by_schema[schema] = []
                paths_by_schema[schema].append(path)

            # Emit from the paths
            for schema, paths_to_emit in paths_by_schema.items():
                print(f"Loading {len(paths_to_emit)} path(s) for {stream} (schema_id: {schema})")
                job_res = tpe.map(
                    reservoir_emitter,
                    itertools.repeat(target_proc.stdin),
                    [path for path in paths_to_emit],
                    itertools.repeat(filesystem),
                    itertools.repeat(reservoir_lock),
                )
                stream_states[stream]["emitted"] = max(
                    stream_states[stream]["emitted"],
                    max(path.split("/")[-1] for path in job_res),
                )
                with reservoir_lock, open(state, "w") as state_data:
                    json.dump(stream_states, state_data)
                files_processed += len(paths_to_emit)

        # Close the target
        print("Closing target process")
        target_proc.stdin.close()
        th.join(), target_proc.wait()
        print(f"Processed {files_processed} file(s)")


def compact_reservoir(tap: str, filesystem: AltoFileSystem, env: str) -> None:
    """Compact the reservoir.

    This merges files with the same schema up to the maximum threshold. This is useful for
    reducing the number of files in the reservoir and reducing the cost of running a
    pipeline from the reservoir.
    """
    from collections import OrderedDict
    from functools import reduce

    # Acquire lock
    base_path = f"reservoir/{env}/{tap}"
    lock_path = filesystem._remote_path("_reservoir.lock", key=base_path)
    if filesystem.fs.exists(lock_path):
        raise RuntimeError(f"Lock file {lock_path} exists, aborting")
    filesystem.fs.pipe(lock_path, "compaction in progress".encode("utf-8"))

    # Load the index
    try:
        reservoir = json.loads(
            filesystem.fs.cat(filesystem._remote_path("_reservoir.json", key=base_path))
        )
    except FileNotFoundError:
        print("Reservoir index not found, skipping compaction")
        return

    # Start the compact operation
    changed = False
    try:
        for stream, paths in reservoir.items():
            if stream in (RESERVOIR_VERSION_KEY,):
                continue
            print(f"Inspecting {stream} ({len(paths)} paths)")
            if not len(paths) > 1:
                continue
            # Partition the paths by schema
            paths_by_schema: t.Dict[str, t.List[t.Tuple[str, int]]] = OrderedDict()
            path: str
            for path in paths:
                schema = path.split("/")[-2]
                if schema not in paths_by_schema:
                    paths_by_schema[schema] = []
                paths_by_schema[schema].append((path, filesystem.fs.size(path)))
            for schema, paths_with_size in paths_by_schema.items():
                compactable = [(path, sz) for path, sz in paths_with_size if sz < 2.5e7]
                if len(compactable) < 2:
                    continue
                merge_queue, queue_bytes = [], 0.0
                while compactable:
                    # Gather compaction-eligible files up to the threshold size and merge them
                    path, sz = compactable.pop()
                    merge_queue.append(path)
                    queue_bytes += sz
                    if queue_bytes > 2.5e7:
                        print(
                            f"Merging {len(merge_queue)} file(s) for {stream} (schema_id: {schema})"
                        )
                        targets = list(sorted(merge_queue))
                        filesystem.fs.pipe(
                            targets[-1],
                            reduce(lambda acc, n: acc + n, filesystem.fs.cat(targets).values()),
                        )
                        filesystem.fs.rm(targets[:-1])
                        merge_queue, queue_bytes = [], 0.0
                        changed = True
                if merge_queue:
                    # Merge the remaining files
                    print(f"Merging {len(merge_queue)} file(s) for {stream} (schema_id: {schema})")
                    targets = list(sorted(merge_queue))
                    filesystem.fs.pipe(
                        targets[-1],
                        reduce(lambda acc, n: acc + n, filesystem.fs.cat(targets).values()),
                    ), filesystem.fs.rm(targets[:-1])
                    changed = True
    except Exception as e:
        # If we fail, just rebuild the index
        print(f"Compacting failed: {e}, rebuilding index")
        changed = True

    try:
        if changed:
            # Rebuild the index
            reservoir[RESERVOIR_VERSION_KEY] = reservoir.get(RESERVOIR_VERSION_KEY, 0) + 1
            streams = [k for k in reservoir.keys() if k != RESERVOIR_VERSION_KEY]
            for stream in streams:
                reservoir[stream] = list(
                    sorted(
                        filesystem.fs.glob(
                            filesystem._remote_path("**.singer.gz", key=f"{base_path}/{stream}")
                        )
                    )
                )
            filesystem.fs.pipe(
                filesystem._remote_path("_reservoir.json", key=base_path),
                json.dumps(reservoir).encode("utf-8"),
            )
            print("Reservoir index rebuilt")
        else:
            # No changes, just print a message
            print("Reservoir index unchanged")
    finally:
        # Drop the lock file
        filesystem.fs.delete(lock_path)


# ============ #
# Sync Testing #
# ============ #


def run_test(
    tap: AltoPlugin, filesystem: AltoFileSystem, test_flag_supported: bool = False
) -> None:
    """Run the sync test for a tap."""

    tap_bin, tap_config, tap_catalog = (
        filesystem.executable_path(tap.pex_name),
        filesystem.config_path(tap.name),
        filesystem.catalog_path(tap.name),
    )
    cmd = [tap_bin, "--config", tap_config, "--catalog", tap_catalog]
    if test_flag_supported:
        cmd.append("--test")
    passed = False
    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE if not test_flag_supported else None,
        env={**os.environ, **tap.environment},
        cwd=filesystem.root_dir,
    ) as proc:
        if test_flag_supported:
            # Use the --test flag to run the test, supported by certain taps
            proc.wait()
            passed = proc.returncode == 0
        else:
            for line in proc.stdout:
                decoded_line = line.decode("utf-8")
                try:
                    message = json.loads(decoded_line)
                    # Ensure that the tap is producing RECORD messages
                    if message.get("type") == "RECORD" and message["record"]:
                        print(message)
                        passed = True
                        break
                except Exception:
                    continue
            proc.terminate()
            proc.wait()
        if not passed:
            raise RuntimeError(f"Test for {tap} failed. See output above.")


# ================== #
# Catalog Generation #
# ================== #


def generate_catalog(tap: AltoPlugin, filesystem: AltoFileSystem) -> None:
    """Generate a base catalog for a tap."""
    bin, catalog, config = (
        filesystem.executable_path(tap.pex_name),
        filesystem.base_catalog_path(tap.name),
        filesystem.config_path(tap.name),
    )
    Path(catalog).parent.mkdir(parents=True, exist_ok=True)
    try:
        # Run the tap in discovery mode
        with open(catalog, "w") as f:
            subprocess.run(
                [bin, "--config", config, "--discover"],
                stdout=f,
                check=True,
                env={**os.environ, **tap.environment},
                cwd=filesystem.root_dir,
            )
    except subprocess.CalledProcessError:
        # If the tap fails to discover, delete the compromised catalog
        os.remove(catalog)
        raise
    # Upload the catalog to the remote cache
    filesystem.fs.put(catalog, filesystem.base_catalog_path(tap.name, remote=True))


def maybe_get_catalog(tap: AltoPlugin, filesystem: AltoFileSystem) -> bool:
    """Download a pex from the remote cache if it exists."""
    local, remote = (
        filesystem.base_catalog_path(tap.name),
        filesystem.base_catalog_path(tap.name, remote=True),
    )
    if os.path.isfile(local):
        # Check if the pex is already in the remote cache
        if not filesystem.fs.exists(remote):
            # If not, upload it
            filesystem.fs.put(local, remote)
        return True
    try:
        # If the pex is not in the local cache, download it
        filesystem.fs.get(remote, local)
    except Exception:
        # If the pex is not in the remote cache, build it
        return False
    return True


def clean_catalog(tap: AltoPlugin, filesystem: AltoFileSystem) -> None:
    """Remove a base catalog from the local cache."""
    local, remote = (
        filesystem.base_catalog_path(tap.name),
        filesystem.base_catalog_path(tap.name, remote=True),
    )
    if os.path.isfile(local):
        os.remove(local)
    if filesystem.fs.exists(remote):
        filesystem.fs.delete(remote)


def render_modified_catalog(
    tap: AltoPlugin, filesystem: AltoFileSystem, return_obj: bool = False
) -> SingerCatalog:
    """Download the base catalog for a tap and apply user config to it."""
    catalog = filesystem.catalog_path(tap.name)
    shutil.copy(filesystem.base_catalog_path(tap.name), catalog)
    disk_path_obj = Path(catalog)
    apply_selected(disk_path_obj, tap.select)
    rv = apply_metadata(disk_path_obj, tap.metadata)
    if return_obj:
        return rv


def get_and_render_catalog(tap: AltoPlugin, filesystem: AltoFileSystem) -> SingerCatalog:
    """Download the base catalog generating it if it does not exist. Apply user config."""
    if not maybe_get_catalog(tap, filesystem):
        generate_catalog(tap, filesystem)
    return render_modified_catalog(tap, filesystem, return_obj=True)


# ================ #
# Config Rendering #
# ================ #


def render_config(
    plugin: AltoPlugin,
    lock: threading.Lock,
    settings: t.Dict[str, t.Any],
    filesystem: AltoFileSystem,
    accent: t.Optional[AltoPlugin] = None,
) -> dict:
    """Render a config file for a plugin."""
    # Acquire the lock, this is necessary because the config rendering process
    # is not thread-safe.
    with lock:
        # Set the namespace for the current plugin being rendered
        original_namespace = deepcopy(settings["LOAD_PATH"])
        namespace_override = accent.namespace if accent is not None else plugin.namespace
        if namespace_override:
            settings["LOAD_PATH"] = namespace_override

        # Apply accent
        if accent is not None:
            config = plugin.config_relative_to(accent)
        else:
            config = plugin.config

        # Render the config
        config_path = Path(filesystem.config_path(plugin.name, accent.name if accent else None))
        config_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_config = config.to_dict()
        with open(config_path, "w") as f:
            json.dump(runtime_config, f, indent=2)

        # Reset the namespace
        settings["LOAD_PATH"] = original_namespace

    return runtime_config


# ============== #
# PEX Management #
# ============== #


def build_pex(plugin: AltoPlugin, filesystem: AltoFileSystem) -> None:
    """Build a pex from the requirements string."""
    output = filesystem.executable_path(plugin.pex_name)
    # Build the pex (deferred import speeds up the CLI)
    import pex.bin.pex

    try:
        pex.bin.pex.main(["-o", output, "--no-emit-warnings", *plugin.pip_url.split()])
    except SystemExit as e:
        # A failed pex build will exit with a non-zero code
        # Successfully built pexes will exit with either 0 or None
        if e.code is not None and e.code != 0:
            # If the pex fails to build, delete the compromised pex
            try:
                os.remove(output)
            except FileNotFoundError:
                pass
            raise

    # Upload the pex to the remote cache
    filesystem.fs.put(output, filesystem.executable_path(plugin.pex_name, remote=True))


def maybe_get_pex(plugin: AltoPlugin, filesystem: AltoFileSystem) -> bool:
    """Download a pex from the remote cache if it exists."""
    local, remote = (
        filesystem.executable_path(plugin.pex_name),
        filesystem.executable_path(plugin.pex_name, remote=True),
    )
    if os.path.isfile(local):
        # Check if the pex is already in the remote cache
        if not filesystem.fs.exists(remote):
            # If not, upload it
            filesystem.fs.put(local, remote)
        return True
    try:
        # If the pex is not in the local cache, download it
        filesystem.fs.get(remote, local)
        os.chmod(local, 0o755)
    except Exception:
        # If the pex is not in the remote cache, build it
        return False
    return True


def maybe_remove_pex(plugin: AltoPlugin, filesystem: AltoFileSystem) -> bool:
    """Remove a pex from the remote cache if it exists."""
    local, remote = (
        filesystem.executable_path(plugin.pex_name),
        filesystem.executable_path(plugin.pex_name, remote=True),
    )
    if os.path.isfile(local):
        os.unlink(local)
    try:
        # If the pex is in the remote cache, remove it
        filesystem.fs.delete(remote)
    except Exception:
        raise RuntimeError(f"Could not remove {remote} from remote cache. It may not exist.")
    return True


# ================== #
# Python API Helpers #
# ================== #


def setup_tap_target(
    tap_name: str,
    target_name: str,
    filesystem: AltoFileSystem,
    configuration: AltoConfiguration,
    settings: t.Dict[str, t.Any],
) -> t.Tuple[AltoPlugin, AltoPlugin, t.Dict[str, dict]]:
    """Setup a tap and target for execution.

    This function will build the pexes for the tap and target, generate the
    base catalog for the tap, and render the config files for both the tap
    and target.
    """
    tap, target = make_plugins(
        tap_name, target_name, filesystem=filesystem, configuration=configuration
    )
    get_and_render_catalog(tap, filesystem)
    _lock = threading.Lock()
    output_configs = {}
    output_configs[tap_name] = render_config(tap, _lock, settings, filesystem)
    output_configs[target_name] = render_config(target, _lock, settings, filesystem, tap)
    return tap, target, output_configs


def make_plugins(
    *plugin_names: str,
    filesystem: AltoFileSystem,
    configuration: AltoConfiguration,
) -> t.Tuple[AltoPlugin, ...]:
    """Create a tuple of plugins from a list of plugin names.

    This function will build the pexes for the plugins if they do not exist.
    """
    plugins = []
    for plugin_name in plugin_names:
        plugin = configuration.get_plugin(plugin_name)
        if not maybe_get_pex(plugin, filesystem):
            build_pex(plugin, filesystem)
        plugins.append(plugin)
    return tuple(plugins)


class _QueueFileIterator(io.BytesIO):
    """A file-like object that writes to a queue.

    This is only intended to be used inside the `tap_runner` function. It
    expects a thread to be writing to the queue and a thread to be reading
    from the queue via the `__iter__` and `__next__` methods. Instances of
    this class should be used in a for loop to iterate over the records.
    Some iterations can be None, these should be ignored. A StopIteration
    exception will be raised organically when the producer is finished.
    """

    def __init__(
        self,
        liveness_probe: t.Callable[[], bool],
        poll_interval: int = 1,
        records_only: bool = False,
    ):
        super().__init__()
        self.queue = queue.Queue()
        # Manage the queue
        self.poll_interval = poll_interval
        self.liveness_probe = liveness_probe
        # Whether to only return records or all output, when records_only is
        # True, the output will be a tuple of (stream, record)
        self.records_only = records_only
        # Store internal state
        self._state = {}

    def write(self, data) -> int:
        self.queue.put(data)
        return len(data)

    def __iter__(self):
        return self

    def __next__(self) -> t.Union[t.Tuple[str, t.Optional[str], dict], None]:
        """Callers should expect None values and should ignore them.

        A StopIteration exception will be raised when the queue is empty. To the caller,
        we will appear to be a generator that yields Option<type, maybeStreamName, message>
        when iterated over with an organic termination.
        """
        try:
            data = self.queue.get(timeout=self.poll_interval)
        except queue.Empty:
            if not self.liveness_probe():
                raise StopIteration
            return None
        else:
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                pass
            else:
                if "type" not in msg:
                    pass
                if msg["type"] == "STATE":
                    merge(msg["value"], self._state)
                return msg["type"], msg.get("stream"), msg
            finally:
                self.queue.task_done()

    def close(self) -> None:
        self.queue.join()


@contextmanager
def tap_runner(
    tap: AltoPlugin,
    filesystem: AltoFileSystem,
    settings: t.Dict[str, t.Any],
    state_key: str,
    records_only: bool = False,
    state_dict: t.Optional[dict] = None,
) -> t.Generator[_QueueFileIterator, None, None]:
    """Run a tap and yield a file-like object that reads from the tap's stdout."""
    tap_bin, tap_config, tap_catalog = (
        filesystem.executable_path(tap.pex_name),
        filesystem.config_path(tap.name),
        filesystem.catalog_path(tap.name),
    )
    state = filesystem.state_path(tap.name, state_key)
    cmd = [tap_bin, "--config", tap_config]
    if os.path.isfile(state) and tap.supports_state:
        cmd += ["--state", state]
    if tap.supports_catalog:
        cmd += ["--catalog", tap_catalog]
    elif tap.supports_properties:
        cmd += ["--properties", tap_catalog]
    # Config
    render_config(tap, threading.Lock(), settings, filesystem)
    # Catalog (low overhead if already rendered)
    get_and_render_catalog(tap, filesystem)
    # State (permit override from alto filesystem state)
    if state_dict and tap.supports_state:
        with open(state, "w") as f:
            json.dump(state_dict, f)
    else:
        get_remote_state(tap.name, state_key, filesystem, execute=tap.supports_state)
    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        env={**os.environ, **tap.environment},
        cwd=filesystem.root_dir,
    ) as tap_proc:
        singer_stream = _QueueFileIterator(
            liveness_probe=lambda: tap_proc.poll() is None,
            poll_interval=1,
            records_only=records_only,
        )
        # Shift proxying of messages to a separate thread
        map_thread = threading.Thread(
            target=map_worker,
            args=(tap_proc.stdout, singer_stream, tap.get_stream_maps(filesystem)),
            daemon=True,
        )
        map_thread.start()
        # Return the stream
        yield singer_stream
        # Cleanup
        if tap_proc.returncode is not None and tap_proc.returncode != 0:
            raise RuntimeError(
                f"Tap exited with code {tap_proc.returncode}"
            ) from subprocess.CalledProcessError(tap_proc.returncode, cmd)
        tap_proc.terminate(), tap_proc.wait(), map_thread.join()
        # Update state
        if tap.supports_state:
            if state_dict is not None:
                # If state_dict is provided, merge the tap's state with it
                # as this is "ephemeral" state preserved by the tap runner
                merge(singer_stream._state, state_dict)
            else:
                with open(state, "w") as f:
                    json.dump(singer_stream._state, f)
                update_remote_state_no_stdout(tap.name, state_key, filesystem)


def get_engine(env: str = DEFAULT_ENVIRONMENT, root_dir: t.Optional[Path] = None) -> AltoTaskEngine:
    """Instantiate an AltoTaskEngine.

    This is a convenience function for use in Python scripts. The engine is configured
    entirely from the alto configuration file. This mutates the environment variable `ALTO_ENV`
    to be in sync with the `env` argument.
    """
    if root_dir is None:
        root_dir = Path.cwd()
    if os.getenv("ALTO_ENV") != env:
        os.environ["ALTO_ENV"] = env or DEFAULT_ENVIRONMENT
    engine = AltoTaskEngine(root_dir)
    engine.setup()
    return engine
