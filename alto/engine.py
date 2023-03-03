"""Primary alto engine."""
import atexit
import datetime
import gzip
import inspect
import io
import itertools
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import typing as t
import uuid
from copy import deepcopy
from enum import Enum
from hashlib import md5, sha1
from pathlib import Path

import fsspec
import pex.bin.pex
from doit.cmd_base import DoitCmdBase as AltoCmdBase
from doit.cmd_base import TaskLoader2 as DoitEngine
from doit.loader import generate_tasks
from doit.tools import config_changed
from dynaconf import Dynaconf
from dynaconf.utils.boxing import DynaBox
from fsspec.implementations.dirfs import DirFileSystem

from alto.catalog import apply_metadata, apply_selected
from alto.constants import (
    ALTO_DB_FILE,
    ALTO_ROOT,
    CATALOG_DIR,
    CONFIG_DIR,
    LOG_DIR,
    PLUGIN_DIR,
    STATE_DIR,
    SUPPORTED_CONFIG_FORMATS,
)
from alto.models import AltoEngineConfig, AltoTask, AltoTaskData, AltoTaskGenerator, PluginType
from alto.state import ensure_state, update_state
from alto.ui import AltoEmojiUI, AltoRichUI
from alto.utils import load_extension_from_path, merge

__all__ = [
    "AltoConfiguration",
    "AltoFileSystem",
    "AltoPlugin",
    "AltoTaskEngine",
]


RESERVOIR_BUFFER_SIZE = 10_000
"""The default number of records to buffer before flushing to reservoir filesystem."""


class AltoCmd(str, Enum):
    """The alto task type is used to determine the type of task to execute."""

    BUILD = "build"
    CONFIG = "config"
    CATALOG = "catalog"
    APPLY = "apply"
    PIPELINE = "pipeline"
    TEST = "test"
    ABOUT = "about"
    INVOKE = "invoke"
    REPL = "repl"


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
                .joinpath(ALTO_ROOT, self.config.get("project_name", "default"))
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
            # Register a cleanup function to remove the staging directory
            atexit.register(shutil.rmtree, tmp)
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
            fsystem: str = self.config.get("filesystem", "file")
            if fsystem == "file":
                # Local file system
                self._fs = DirFileSystem(
                    self.sys_dir, fs=fsspec.filesystem("file", auto_mkdir=True)
                )
            elif fsystem in ("s3", "s3a", "gs", "gcs", "azure"):
                # Remote file system
                path: str = self.config.get("bucket_path", "alto")
                path = path.strip("/")
                self._fs = DirFileSystem(
                    f"{self.config['bucket']}/{path}/{self.config['project_name']}",
                    fs=fsspec.filesystem(
                        fsystem, **self.config.get(f"{fsystem}_kwargs", DynaBox())
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
        return getter(fname=f"{tap}-to-{target}.json", key=STATE_DIR.format(env=self.config["env"]))

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
        return getter(fname=fname, key=LOG_DIR.format(env=self.config["env"]))


class AltoPlugin:
    def __init__(self, name: str, typ: PluginType, config: AltoConfiguration) -> None:
        self.name = name
        self.type = typ
        self.alto = config
        self._spec = self.alto.spec_for(name)

    @property
    def spec(self) -> DynaBox:
        """Return the spec for the plugin."""
        return self._spec

    @property
    def pip_url(self) -> str:
        """Return the pip url for the plugin."""
        return self.spec["pip_url"]

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
        return self.alto.inner["namespace"]

    @property
    def namespace(self) -> str:
        """Return the namespace for the plugin."""
        return self.spec.get("namespace", self.root_namespace)

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
        return self.spec.get("select", ["*.*"])

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
        return {f"PEX_{typ}": self.entrypoint, "ALTO_PLUGIN": self.name}

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

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"{self.name} ({self.type})"


class AltoTaskEngine(DoitEngine):
    """The alto task engine builds on top of doit to provide a simple interface for Singer tasks.

    The engine is responsible for loading the configuration, loading the extensions, building and
    executing plugins, and user-specific build tasks supplied via the extension interface.
    """

    Extensions: t.List[t.Callable[["AltoTaskEngine"], AltoTaskGenerator]] = []
    Configuration = AltoConfiguration
    FileSystem = AltoFileSystem

    def __init__(
        self,
        root_dir: Path = Path.cwd(),
    ) -> None:
        """Initialize the alto task engine."""
        super().__init__()
        self.alto = Dynaconf(
            settings_files=[root_dir / f"alto.{fmt}" for fmt in SUPPORTED_CONFIG_FORMATS],
            secrets=[root_dir / f"alto.secrets.{fmt}" for fmt in SUPPORTED_CONFIG_FORMATS],
            root_path=root_dir,
            fresh_vars=["namespace"],
            envvar_prefix="ALTO",
            env_switcher="ALTO_ENV",
            load_dotenv=True,
            environments=True,
            merge_enabled=True,
        )
        # Instantiate the filesystem and configuration
        self.configuration = AltoTaskEngine.Configuration(inner=self.alto)
        self.filesystem = AltoTaskEngine.FileSystem(root_dir, config=self.configuration)

    @property
    def fs(self) -> fsspec.spec.AbstractFileSystem:
        """Return the filesystem."""
        return self.filesystem.fs

    def setup(self, opt_values: t.Dict[str, t.Any]) -> None:
        """Load extensions and filesystem interface. This is called by doit."""
        self._load_extensions()

    def _load_extensions(self) -> None:
        """Load the extensions from the configuration file.

        Extensions are python files that are loaded and executed at runtime. They
        are used to add custom tasks to the alto engine. The API for extensions
        is simple. The extension file must contain a function named `extension`
        that takes a single argument, the alto engine instance. The function must
        return a generator of doit tasks. The extension function is called at
        runtime and the tasks are added to the engine. A `name` attribute must be set.
        """
        for extension_path in t.cast(t.List[str], self.alto.get("extensions", [])):
            py = self.filesystem.root_dir / extension_path
            if not (py.is_file() and py.suffix == ".py"):
                raise Exception("Invalid extension path. Must be a .py file.")
            for name, ext_func in inspect.getmembers(
                load_extension_from_path(py),
                inspect.isfunction,
            ):
                if name == "extension":
                    AltoTaskEngine.Extensions.append(ext_func)

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

    # Tasks

    def task_build(self) -> AltoTaskGenerator:
        """[core] Generate pex plugin based on the alto config."""

        def build_pex(plugin: AltoPlugin) -> None:
            """Build a pex from the requirements string."""
            output = self.filesystem.executable_path(plugin.pex_name)
            # Build the pex
            try:
                pex.bin.pex.main(["-o", output, "--no-emit-warnings", *plugin.pip_url.split()])
            except SystemExit:
                pass
            # Upload the pex to the remote cache
            self.fs.put(output, self.filesystem.executable_path(plugin.pex_name, remote=True))

        def maybe_get_pex(plugin: AltoPlugin) -> bool:
            """Download a pex from the remote cache if it exists."""
            local, remote = (
                self.filesystem.executable_path(plugin.pex_name),
                self.filesystem.executable_path(plugin.pex_name, remote=True),
            )
            if os.path.isfile(local):
                # Check if the pex is already in the remote cache
                if not self.fs.exists(remote):
                    # If not, upload it
                    self.fs.put(local, remote)
                return True
            try:
                # If the pex is not in the local cache, download it
                self.fs.get(remote, local)
                os.chmod(local, 0o755)
            except Exception:
                # If the pex is not in the remote cache, build it
                return False
            return True

        def maybe_remove_pex(plugin: AltoPlugin) -> bool:
            """Remove a pex from the remote cache if it exists."""
            local, remote = (
                self.filesystem.executable_path(plugin.pex_name),
                self.filesystem.executable_path(plugin.pex_name, remote=True),
            )
            if os.path.isfile(local):
                os.unlink(local)
            try:
                # If the pex is in the remote cache, remove it
                self.fs.delete(remote)
            except Exception:
                raise RuntimeError(
                    f"Could not remove {remote} from remote cache. It may not exist."
                )
            return True

        for plugin in self.configuration.plugins():
            task = AltoTask(name=plugin.name).set_doc(f"Build the {plugin} plugin").set_verbosity(2)

            if plugin.parent is None:
                # If the plugin does not inherit from another plugin, build it
                task = (
                    task.set_actions((build_pex, (plugin,)))
                    .set_uptodate((maybe_get_pex, (plugin,)))
                    .set_clean((maybe_remove_pex, (plugin,)))
                )
            else:
                # If the plugin inherits from another plugin, just ensure the parent is built
                task.set_task_dep(f"{AltoCmd.BUILD}:{plugin.parent}")
            yield task.data

    def task_config(self) -> AltoTaskGenerator:
        """[core] Generate configuration files on disk."""

        # This lock is used to prevent multiple threads from mutating the root
        # namespace at the same time. This is necessary because the namespace is
        # a top-level variable used by Alto during dumping. Users reference it
        # in config via "@format {this.namespace}" with the expectation that it
        # will be replaced with the current plugin's namespace.
        config_lock = threading.Lock()

        def render_config(
            plugin: AltoPlugin,
            accent: t.Optional[AltoPlugin] = None,
        ) -> None:
            """Render a config file for a plugin."""
            with config_lock:
                # Set the namespace for the current plugin being rendered
                original_namespace = deepcopy(self.alto["namespace"])
                namespace_override = accent.namespace if accent is not None else plugin.namespace
                if namespace_override:
                    self.alto["namespace"] = namespace_override
                # Apply accent
                if accent is not None:
                    config = plugin.config_relative_to(accent)
                else:
                    config = plugin.config
                # Render the config
                config_path = Path(
                    self.filesystem.config_path(plugin.name, accent.name if accent else None)
                )
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, "w") as f:
                    json.dump(config.to_dict(), f, indent=2)
                # Reset the namespace
                self.alto["namespace"] = original_namespace

        for plugin in self.configuration.plugins(PluginType.TAP, PluginType.TARGET):
            yield (
                AltoTask(name=plugin.name)
                .set_actions((render_config, (plugin,)))
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
                .set_actions((render_config, (target, tap)))
                .set_uptodate(False)
                .set_doc(f"Render configuration for the {target} plugin with {tap} as source")
                .data
            )

    def task_catalog(self) -> AltoTaskGenerator:
        """[singer] Generate base catalog file for a Singer tap.

        These catalogs are used as the basis for applying metadata rules and selections.
        Use `doit clean catalog:plugin-name` to force a rebuild of one or more base catalogs.
        """

        def generate_catalog(tap: AltoPlugin) -> None:
            """Generate a base catalog for a tap."""
            bin, catalog, config = (
                self.filesystem.executable_path(tap.pex_name),
                self.filesystem.base_catalog_path(tap.name),
                self.filesystem.config_path(tap.name),
            )
            Path(catalog).parent.mkdir(parents=True, exist_ok=True)
            try:
                # Run the tap in discovery mode
                subprocess.run(
                    [bin, "--config", config, "--discover"],
                    stdout=open(catalog, "w"),
                    check=True,
                    env={**os.environ, **tap.environment},
                )
            except subprocess.CalledProcessError:
                # If the tap fails to discover, delete the compromised catalog
                os.remove(catalog)
                raise
            # Upload the catalog to the remote cache
            self.fs.put(catalog, self.filesystem.base_catalog_path(tap.name, remote=True))

        def maybe_get_catalog(tap: AltoPlugin) -> bool:
            """Download a pex from the remote cache if it exists."""
            local, remote = (
                self.filesystem.base_catalog_path(tap.name),
                self.filesystem.base_catalog_path(tap.name, remote=True),
            )
            if os.path.isfile(local):
                # Check if the pex is already in the remote cache
                if not self.fs.exists(remote):
                    # If not, upload it
                    self.fs.put(local, remote)
                return True
            try:
                # If the pex is not in the local cache, download it
                self.fs.get(remote, local)
            except Exception:
                # If the pex is not in the remote cache, build it
                return False
            return True

        def clean_catalog(tap: AltoPlugin) -> None:
            """Remove a base catalog from the local cache."""
            local, remote = (
                self.filesystem.base_catalog_path(tap.name),
                self.filesystem.base_catalog_path(tap.name, remote=True),
            )
            if os.path.isfile(local):
                os.remove(local)
            if self.fs.exists(remote):
                self.fs.delete(remote)

        for tap in self.configuration.plugins(PluginType.TAP):
            yield (
                AltoTask(name=tap.name)
                .set_actions((generate_catalog, (tap,)))
                .set_task_dep(f"{AltoCmd.BUILD}:{tap}")
                .set_setup(f"{AltoCmd.CONFIG}:{tap}")
                .set_uptodate((maybe_get_catalog, (tap,)))
                .set_clean((clean_catalog, (tap,)))
                .set_doc(f"Generate base catalog for {tap}")
                .data
            )

    def task_apply(self) -> AltoTaskGenerator:
        """[singer] Apply user config to base catalog file."""

        def render_modified_catalog(tap: AltoPlugin) -> str:
            """Download the base catalog for a tap and apply user config to it."""
            catalog = self.filesystem.catalog_path(tap.name)
            shutil.copy(self.filesystem.base_catalog_path(tap.name), catalog)
            apply_selected(Path(catalog), tap.select)
            apply_metadata(Path(catalog), tap.metadata)

        for tap in self.configuration.plugins(PluginType.TAP):
            yield (
                AltoTask(name=tap.name)
                .set_actions((render_modified_catalog, (tap,)))
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
            # TODO: this should use a subprocess to control for the environment
            # variables that the tap might set and to be system agnostic.
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

        # Lock to prevent interleaved output from the two processes
        # in a pipeline. This permits real-time logging of the pipeline.
        stdout_lock = threading.Lock()

        # Used in the reservoir emitter to ensure that only one thread
        # is writing to the state file or target stdin at a time.
        reservoir_lock = threading.Lock()

        # TODO: Move the locals here to a separate class, PipelineManager
        # or some such. This will make it easier to test the pipeline and
        # enable programmatic execution of pipelines.

        def pipeline_logger(stream: t.IO[bytes], path: str) -> None:
            """Log a stream to the console."""
            with open(path, "wb") as log_data:
                for line in stream:
                    log_data.write(line)
                    with stdout_lock:
                        print(line.decode("utf-8"), end="", flush=True)

        def run_pipeline(tap: AltoPlugin, target: AltoPlugin, pipeline_id: str) -> None:
            """Execute a data pipeline."""
            tap_bin, tap_config, tap_catalog = (
                self.filesystem.executable_path(tap.pex_name),
                self.filesystem.config_path(tap.name),
                self.filesystem.catalog_path(tap.name),
            )
            target_bin, target_config = (
                self.filesystem.executable_path(target.pex_name),
                self.filesystem.config_path(target.name, tap.name),
            )
            state = self.filesystem.state_path(tap.name, target.name)
            cmd = [tap_bin, "--config", tap_config]
            if os.path.isfile(state) and tap.supports_state:
                cmd += ["--state", state]
            if tap.supports_catalog:
                cmd += ["--catalog", tap_catalog]
            elif tap.supports_properties:
                cmd += ["--properties", tap_catalog]
            print(f"Running pipeline {pipeline_id} ({tap} -> {target})")
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, **tap.environment},
            ) as tap_proc, subprocess.Popen(
                [target_bin, "--config", target_config],
                stdin=tap_proc.stdout,
                stderr=subprocess.PIPE,
                stdout=open(self.filesystem.log_path(f"state-{pipeline_id}.log"), "w"),
                env={**os.environ, **target.environment},
            ) as target_proc:
                t1 = threading.Thread(
                    target=pipeline_logger,
                    args=(tap_proc.stderr, self.filesystem.log_path(f"tap-{pipeline_id}.log")),
                    daemon=True,
                )
                t2 = threading.Thread(
                    target=pipeline_logger,
                    args=(
                        target_proc.stderr,
                        self.filesystem.log_path(f"target-{pipeline_id}.log"),
                    ),
                    daemon=True,
                )
                t1.start(), t2.start()
                tap_proc.wait(), target_proc.wait()
                if tap_proc.returncode != 0:
                    raise subprocess.CalledProcessError(tap_proc.returncode, cmd)
                if target_proc.returncode != 0:
                    raise subprocess.CalledProcessError(target_proc.returncode, cmd)
                t1.join(), t2.join()

        def get_remote_state(tap: str, target: str, execute: bool = False) -> None:
            """Download the remote state file."""
            if execute:
                remote_state = self.filesystem.state_path(tap, target, remote=True)
                if self.fs.exists(remote_state):
                    self.fs.get(remote_state, self.filesystem.state_path(tap, target))

        def update_remote_state(
            tap: str, target: str, pipeline_id: str, execute: bool = False
        ) -> None:
            """Update the remote state file."""
            if execute:
                stdout = Path(self.filesystem.log_path(f"state-{pipeline_id}.log"))
                if not stdout.exists() or stdout.stat().st_size == 0:
                    return
                state = Path(self.filesystem.state_path(tap, target))
                remote_state = self.filesystem.state_path(tap, target, remote=True)
                ensure_state(state)
                update_state(state, stdout)
                ts = datetime.datetime.now().strftime("%Y%m%d%H%M")
                # Keep a mutable and immutable copy of the state file for recovery / analysis
                self.fs.put(self.filesystem.state_path(tap, target), remote_state)
                self.fs.put(
                    self.filesystem.state_path(tap, target),
                    remote_state[:-5] + f".{ts}.json",
                )
                stdout.unlink()

        def update_remote_state_no_stdout(tap: str, target: str) -> None:
            """Update the remote state file directly.

            Used for the reservoir emitter.
            """
            local_path, remote_state = (
                self.filesystem.state_path(tap, target),
                self.filesystem.state_path(tap, target, remote=True),
            )
            ensure_state(local_path)
            ts = datetime.datetime.now().strftime("%Y%m%d%H%M")
            # Keep a mutable and immutable copy of the state file for recovery / analysis
            self.fs.put(local_path, remote_state)
            self.fs.put(local_path, remote_state[:-5] + f".{ts}.json")
            print(f"Updated state file for {tap} -> {target}.")
            print(f"Remote state file: {remote_state}")

        def upload_logs(tap: str, target: str, pipeline_id: str) -> None:
            """Upload the logs for a pipeline run and remove from system."""
            ts = datetime.datetime.now().strftime("%Y%m%d%H%M")
            tap_path, tap_dest = (
                Path(self.filesystem.log_path(f"tap-{pipeline_id}.log")),
                self.filesystem.log_path(f"{ts}--{tap}--{pipeline_id}.log", remote=True),
            )
            target_path, target_dest = (
                Path(self.filesystem.log_path(f"target-{pipeline_id}.log")),
                self.filesystem.log_path(f"{ts}--{target}--{pipeline_id}.log", remote=True),
            )
            if tap_path.exists():
                self.fs.put(str(tap_path.resolve()), tap_dest), tap_path.unlink()
                print(f"Uploaded tap log for pipeline {pipeline_id} to {tap_dest}")
            if target_path.exists():
                self.fs.put(str(target_path.resolve()), target_dest), target_path.unlink()
                print(f"Uploaded target log for pipeline {pipeline_id} to {target_dest}")

        def reservoir_ingestor(
            stdout: t.IO[bytes],
            reservoir: t.Dict[str, t.List[str]],
            record_key: str,
            state_path: str,
            stream_states: t.Optional[t.Dict[str, t.Any]] = None,
        ) -> None:
            """Primary ingestion loop for the reservoir."""
            from concurrent.futures import ThreadPoolExecutor

            # Set up
            if stream_states is None:
                stream_states = {}
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
                    container = record_buffer[stream][active_schemas[stream]]
                    container["count"] += 1
                    container["records"].write(line + b"\n")
                    if container["count"] >= self.alto.get(
                        "reservoir_buffer_size", RESERVOIR_BUFFER_SIZE
                    ):
                        # Buffer is full, flush to filesystem
                        print(f"Flushing {stream} ({active_schemas[stream]})")
                        ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
                        path = self.filesystem._remote_path(
                            f"{ts}.singer.gz",
                            key=record_key.format(stream=stream, schema_id=active_schemas[stream]),
                        )
                        _buf: gzip.GzipFile = container["records"]
                        inner_buf: io.BytesIO = _buf.fileobj
                        _buf.close()
                        inner_buf.flush(), inner_buf.seek(0)
                        tpe.submit(self.fs.pipe, path, inner_buf.getvalue())
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
                        with open(self.filesystem.log_path(f"target-{pipeline_id}.log"), "a") as f:
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
                    path = self.filesystem._remote_path(
                        f"{ts}.singer.gz",
                        key=record_key.format(stream=stream, schema_id=active_schemas[stream]),
                    )
                    _buf: gzip.GzipFile = container["records"]
                    inner_buf: io.BytesIO = _buf.fileobj
                    _buf.close()
                    inner_buf.flush(), inner_buf.seek(0)
                    tpe.submit(self.fs.pipe, path, inner_buf.getvalue())
                    # Update the index
                    if stream not in reservoir:
                        reservoir[stream] = []
                    reservoir[stream].append(path)
                    # Write path to pipeline log file
                    with open(self.filesystem.log_path(f"target-{pipeline_id}.log"), "a") as f:
                        f.write(f"{path}\n")
            # Write actualized state to the remote storage directory
            tpe.shutdown()
            print("Writing final state")
            with open(state_path, "w") as state_data:
                json.dump(stream_states, state_data)

        def reservoir_emitter(stdin: t.IO[bytes], path: str) -> str:
            """Emits records from the reservoir to the target.

            This function is intended to be used as a target for a
            concurrent.futures.ThreadPoolExecutor, and is responsible
            for pulling data from the reservoir, decompressing, and
            emitting it to the stdin handle of the target process.
            """
            # TODO: oddly, a failure in this function will lock up the
            # entire pipeline instead of raising an exception in the
            # main thread. This is probably a bug in the ThreadPoolExecutor
            stream = gzip.decompress(self.fs.cat(path))
            with reservoir_lock:
                # Write the records to the target's stdin handle with a lock
                stdin.writelines((line + b"\n") for line in stream.splitlines() if line)
            return path

        def tap_to_reservoir(tap: AltoPlugin, pipeline_id: str) -> None:
            """Execute a data pipeline to the project reservoir."""
            # Set up
            target = "reservoir"
            tap_bin, tap_config, tap_catalog = (
                self.filesystem.executable_path(tap.pex_name),
                self.filesystem.config_path(tap.name),
                self.filesystem.catalog_path(tap.name),
            )
            stream_states = {}
            state = self.filesystem.state_path(tap.name, target)
            base_path = f"{target}/{self.alto['env']}/{tap}"

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
            index_path = self.filesystem._remote_path("_reservoir.json", key=base_path)
            reservoir = {}
            if self.fs.exists(index_path):
                reservoir = json.loads(self.fs.cat(index_path).decode("utf-8"))

            # Create a lock file to prevent multiple runs of the same pipeline / env
            lock_path = self.filesystem._remote_path("_reservoir.lock", key=base_path)
            if self.fs.exists(lock_path):
                raise RuntimeError(f"Lock file {lock_path} exists, aborting")
            self.fs.pipe(lock_path, f"{pipeline_id}".encode("utf-8"))
            try:
                # Start the pipeline
                print(f"Running pipeline {pipeline_id} ({tap} -> {target})")
                with subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env={**os.environ, **tap.environment},
                ) as tap_proc:
                    # Stream stderr
                    t1 = threading.Thread(
                        target=pipeline_logger,
                        args=(tap_proc.stderr, self.filesystem.log_path(f"tap-{pipeline_id}.log")),
                        daemon=True,
                    )
                    t1.start()
                    # Stream the tap output to the reservoir 🚀
                    # mutates the reservoir index and the state file
                    # and blocks until the tap process exits. The finally
                    # block will update the reservoir index and drop the
                    # lock file to allow the next run to proceed.
                    reservoir_ingestor(
                        stdout=tap_proc.stdout,
                        reservoir=reservoir,
                        record_key=base_path + "/{stream}/{schema_id}",
                        state_path=state,
                        stream_states=stream_states,
                    )
                    tap_proc.wait(), t1.join()
            finally:
                # Load the reservoir index from the remote storage directory
                self.fs.pipe(index_path, json.dumps(reservoir).encode("utf-8"))
                # Drop the lock file
                self.fs.delete(lock_path)

        def reservoir_to_target(tap: AltoPlugin, target: AltoPlugin, pipeline_id: str) -> None:
            """Execute a data pipeline from the project reservoir."""
            from collections import OrderedDict
            from concurrent.futures import ThreadPoolExecutor

            # Set up
            target_bin, target_config = (
                self.filesystem.executable_path(target.pex_name),
                self.filesystem.config_path(target.name, tap.name),
            )
            state = self.filesystem.state_path(tap.name.replace("tap", "reservoir"), target.name)

            # Load the stream states
            stream_states = {}
            if os.path.isfile(state):
                with open(state) as state_data:
                    stream_states = json.load(state_data)
            stream_states.setdefault("__version__", 0)

            # Load the index
            base_path = f"reservoir/{self.alto['env']}/{tap}"
            index_path = self.filesystem._remote_path("_reservoir.json", key=base_path)
            if not self.fs.exists(index_path):
                print("Reservoir index not found, rebuilding")
                reservoir = {"__version__": 0}
                streams = (
                    [
                        stream_directory.split("/")[-1]
                        for stream_directory in self.fs.ls(base_path, detail=False)
                        if not self.fs.isfile(stream_directory)
                    ]
                    if self.fs.exists(base_path)
                    else []
                )
                for stream in streams:
                    reservoir[stream] = list(
                        sorted(
                            self.fs.glob(
                                self.filesystem._remote_path(
                                    "**.singer.gz", key=f"{base_path}/{stream}"
                                )
                            )
                        )
                    )
                self.fs.pipe(
                    self.filesystem._remote_path("_reservoir.json", key=base_path),
                    json.dumps(reservoir).encode("utf-8"),
                )
                print("Reservoir index rebuilt")
            else:
                reservoir: t.Dict[str, t.List[str]] = json.loads(
                    self.fs.cat(index_path).decode("utf-8")
                )

            # Recreate the state file if the index has changed (from a compaction)
            stream_states.setdefault("__version__", 0)
            reservoir.setdefault("__version__", 0)
            if stream_states["__version__"] != reservoir["__version__"]:
                print("Index has changed, recreating state file")
                for stream, paths in reservoir.items():
                    # Skip stuff we never saw before
                    if stream in ("__version__",) or stream not in stream_states:
                        continue
                    # Update the state
                    for path in sorted(paths):
                        fname = path.split("/")[-1]
                        if fname > stream_states[stream]["emitted"]:
                            stream_states[stream]["emitted"] = fname
                stream_states["__version__"] = reservoir["__version__"]
                with open(state, "w") as state_dest:
                    json.dump(stream_states, state_dest)
                print("Index version:", stream_states["__version__"])

            # Start the pipeline
            print(f"Running pipeline {pipeline_id} ({tap} -> {target})")
            with subprocess.Popen(
                [target_bin, "--config", target_config],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                env={**os.environ, **target.environment},
            ) as target_proc:
                # Stream stderr
                th = threading.Thread(
                    target=pipeline_logger,
                    args=(
                        target_proc.stderr,
                        self.filesystem.log_path(f"target-{pipeline_id}.log"),
                    ),
                    daemon=True,
                )
                th.start()
                # Batch the reservoir paths by schema
                tpe = ThreadPoolExecutor(max_workers=os.cpu_count())
                files_processed = 0
                for stream, paths in reservoir.items():
                    # Gather the paths to process
                    if stream in ("__version__",):
                        continue
                    if stream not in stream_states:
                        stream_states[stream] = {"emitted": ""}
                    work_queue = [
                        path
                        for path in paths
                        if path.split("/")[-1] > stream_states[stream]["emitted"]
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
                        print(
                            f"Loading {len(paths_to_emit)} path(s) for {stream} "
                            f"(schema_id: {schema})"
                        )
                        job_res = tpe.map(
                            reservoir_emitter,
                            itertools.repeat(target_proc.stdin),
                            [path for path in paths_to_emit],
                        )
                        stream_states[stream]["emitted"] = max(
                            stream_states[stream]["emitted"],
                            max(path.split("/")[-1] for path in job_res),
                        )
                        with reservoir_lock, open(state, "w") as state_data:
                            json.dump(stream_states, state_data)
                        files_processed += len(paths_to_emit)
                target_proc.stdin.close()
                th.join(), target_proc.wait()
                print(f"Processed {files_processed} file(s)")

        def compact_reservoir(tap: str) -> None:
            """Compact the reservoir.

            This merges files with the same schema up to the maximum threshold. This is useful for
            reducing the number of files in the reservoir and reducing the cost of running a
            pipeline from the reservoir.
            """
            from collections import OrderedDict
            from functools import reduce

            # Acquire lock
            base_path = f"reservoir/{self.alto['env']}/{tap}"
            lock_path = self.filesystem._remote_path("_reservoir.lock", key=base_path)
            if self.fs.exists(lock_path):
                raise RuntimeError(f"Lock file {lock_path} exists, aborting")
            self.fs.pipe(lock_path, f"{pipeline_id}".encode("utf-8"))

            # Load the index
            try:
                reservoir = json.loads(
                    self.fs.cat(self.filesystem._remote_path("_reservoir.json", key=base_path))
                )
            except FileNotFoundError:
                print("Reservoir index not found, skipping compaction")
                return

            # Start the compact operation
            changed = False
            try:
                for stream, paths in reservoir.items():
                    if stream in ("__version__",):
                        continue
                    print(f"Inspecting {stream} ({len(paths)} paths)")
                    if not len(paths) > 1:
                        continue
                    paths_by_schema: t.Dict[str, t.List[t.Tuple[str, int]]] = OrderedDict()
                    path: str
                    for path in paths:
                        schema = path.split("/")[-2]
                        if schema not in paths_by_schema:
                            paths_by_schema[schema] = []
                        paths_by_schema[schema].append((path, self.fs.size(path)))
                    for schema, paths_with_size in paths_by_schema.items():
                        compactable = [(path, sz) for path, sz in paths_with_size if sz < 2.5e7]
                        if len(compactable) < 2:
                            continue
                        merge_queue, queue_bytes = [], 0.0
                        while compactable:
                            path, sz = compactable.pop()
                            merge_queue.append(path)
                            queue_bytes += sz
                            if queue_bytes > 2.5e7:
                                print(
                                    f"Merging {len(merge_queue)} file(s) for {stream} "
                                    f"(schema_id: {schema})"
                                )
                                targets = list(sorted(merge_queue))
                                self.fs.pipe(
                                    targets[-1],
                                    reduce(lambda acc, n: acc + n, self.fs.cat(targets).values()),
                                )
                                self.fs.rm(targets[:-1])
                                merge_queue, queue_bytes = [], 0.0
                                changed = True
                        if merge_queue:
                            print(
                                f"Merging {len(merge_queue)} file(s) for {stream} "
                                f"(schema_id: {schema})"
                            )
                            targets = list(sorted(merge_queue))
                            self.fs.pipe(
                                targets[-1],
                                reduce(lambda acc, n: acc + n, self.fs.cat(targets).values()),
                            ), self.fs.rm(targets[:-1])
                            changed = True
            except Exception as e:
                print(f"Compacting failed: {e}, rebuilding index")
                changed = True

            # Rebuild the index
            try:
                if changed:
                    reservoir["__version__"] = reservoir.get("__version__", 0) + 1
                    streams = [k for k in reservoir.keys() if k != "__version__"]
                    for stream in streams:
                        reservoir[stream] = list(
                            sorted(
                                self.fs.glob(
                                    self.filesystem._remote_path(
                                        "**.singer.gz", key=f"{base_path}/{stream}"
                                    )
                                )
                            )
                        )
                    self.fs.pipe(
                        self.filesystem._remote_path("_reservoir.json", key=base_path),
                        json.dumps(reservoir).encode("utf-8"),
                    )
                    print("Reservoir index rebuilt")
                else:
                    print("Reservoir index unchanged")
            finally:
                # Drop the lock file
                self.fs.delete(lock_path)

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
                    (get_remote_state, (tap.name, target.name, tap.supports_state)),
                    (run_pipeline, (tap, target, pipeline_id)),
                )
                .set_task_dep(
                    f"{AltoCmd.BUILD}:{tap}", f"{AltoCmd.APPLY}:{tap}", f"{AltoCmd.BUILD}:{target}"
                )
                .set_setup(f"{AltoCmd.CONFIG}:{target}--{tap}", f"{AltoCmd.CONFIG}:{tap}")
                .set_teardown(
                    (update_remote_state, (tap.name, target.name, pipeline_id, tap.supports_state)),
                    (upload_logs, (tap.name, target.name, pipeline_id)),
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
                    (get_remote_state, (tap_reservoir, target.name, True)),
                    (reservoir_to_target, (tap, target, pipeline_id)),
                )
                .set_task_dep(f"{AltoCmd.BUILD}:{target}")
                .set_setup(f"{AltoCmd.CONFIG}:{target}--{tap}")
                .set_teardown(
                    (update_remote_state_no_stdout, (tap_reservoir, target.name)),
                    (upload_logs, (tap.name, target.name, pipeline_id)),
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
            target = "reservoir"
            pipeline_id = uuid.uuid4()
            yield (
                AltoTask(name=target)
                .set_basename(tap.name)
                .set_actions(
                    (get_remote_state, (tap.name, target, tap.supports_state)),
                    (tap_to_reservoir, (tap, pipeline_id)),
                )
                .set_task_dep(f"{AltoCmd.BUILD}:{tap}", f"{AltoCmd.APPLY}:{tap}")
                .set_setup(f"{AltoCmd.CONFIG}:{tap}")
                .set_teardown(
                    (update_remote_state_no_stdout, (tap.name, target)),
                    (upload_logs, (tap.name, target, pipeline_id)),
                )
                .set_clean((compact_reservoir, (tap,)))
                .set_uptodate(False)
                .set_doc(f"Run the {tap} to {target} data pipeline to the reservoir from the tap")
                .set_verbosity(2)
                .data
            )

    def task_test(self) -> AltoTaskGenerator:
        """[singer] Run tests for taps."""

        def run_test(tap: AltoPlugin, auto: bool = False) -> None:
            """Run the sync test for a tap."""

            tap_bin, tap_config, tap_catalog = (
                self.filesystem.executable_path(tap.pex_name),
                self.filesystem.config_path(tap.name),
                self.filesystem.catalog_path(tap.name),
            )
            cmd = [tap_bin, "--config", tap_config, "--catalog", tap_catalog]
            if auto:
                cmd.append("--test")
            passed = False
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE if not auto else None,
                env={**os.environ, **tap.environment},
            ) as proc:
                if auto:
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

        for tap in self.configuration.plugins(PluginType.TAP):
            yield (
                AltoTask(name=tap.name)
                .set_actions((run_test, (tap, tap.supports_test)))
                .set_task_dep(f"{AltoCmd.BUILD}:{tap}", f"{AltoCmd.APPLY}:{tap}")
                .set_setup(f"{AltoCmd.CONFIG}:{tap}")
                .set_uptodate(False)
                .set_doc(f"Test the {tap} plugin")
                .set_verbosity(2)
                .data
            )

    def task_invoke(self) -> AltoTaskGenerator:
        """[alto] Invoke a plugin."""

        def invoke(plugin: AltoPlugin) -> None:
            """Run the sync test for a tap."""

            exe = self.filesystem.executable_path(plugin.pex_name)
            with subprocess.Popen(
                [exe, *sys.argv[2:]],
                env={**os.environ, **plugin.environment},
            ) as proc:
                proc.wait()

        args = sys.argv[2:]  # Pass through all args after the plugin name
        for plugin in self.configuration.plugins():
            yield {
                **AltoTask(name=plugin.name)
                .set_actions((invoke, (plugin,)))
                .set_task_dep(f"{AltoCmd.BUILD}:{plugin}")
                .set_uptodate(False)
                .set_doc(f"Invoke {plugin} plugin")
                .set_verbosity(2)
                .data,
                # This is a hack to allow for arbitrary params to be passed to the task
                # TODO: create a dedicated `invoke` top-level task
                "params": [
                    {
                        "name": f"param{i}",
                        "long": arg.lstrip("-"),
                        "default": "",
                        "type": bool
                        if len(args) > i + 1 and args[1 + i].startswith("-") or len(args) == i + 1
                        else str,
                    }
                    for i, arg in enumerate(args)
                    if arg.startswith("-")
                ],
            }

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
                generate_tasks(AltoCmd.INVOKE, self.task_invoke(), self.task_invoke.__doc__),
                *(
                    generate_tasks(getattr(ext, "name", f"ext-{n}"), ext(self), ext.__doc__)
                    for n, ext in enumerate(AltoTaskEngine.Extensions)
                ),
            )
        )
