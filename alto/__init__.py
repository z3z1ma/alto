"""Alto is a command line tool for running Singer taps and targets."""
from alto.catalog import CatalogMutationStrategy, apply_metadata, apply_selected
from alto.config import working_directory
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
from alto.engine import AltoConfiguration, AltoFileSystem, AltoPlugin, AltoTaskEngine
from alto.main import AltoInit, AltoMain, AltoRepl, AltoRun, main
from alto.models import (
    AltoAction,
    AltoTask,
    AltoTaskData,
    PluginConfiguration,
    PluginType,
    SingerCatalog,
    SingerCatalogStream,
    SingerCatalogStreamMetadata,
    SingerCatalogStreamMetadataEntry,
    SingerCatalogStreamMetadataRoot,
    TapConfiguration,
    TargetConfiguration,
    UtilityConfiguration,
)
from alto.repl import AltoCmd
from alto.state import ensure_state, parse_state_from_stdout, update_state

__all__ = [
    # engine
    "AltoConfiguration",
    "AltoFileSystem",
    "AltoPlugin",
    "AltoTaskEngine",
    # cli
    "main",
    "AltoInit",
    "AltoRepl",
    "AltoRun",
    "AltoMain",
    # models
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
    # repl
    "AltoCmd",
    # catalog
    "CatalogMutationStrategy",
    "apply_selected",
    "apply_metadata",
    # state
    "ensure_state",
    "parse_state_from_stdout",
    "update_state",
    # constants
    "ALTO_ROOT",
    "ALTO_DB_FILE",
    "PLUGIN_DIR",
    "CATALOG_DIR",
    "STATE_DIR",
    "CONFIG_DIR",
    "LOG_DIR",
    "DEFAULT_ENVIRONMENT",
    "SUPPORTED_CONFIG_FORMATS",
    # config
    "working_directory",
]
