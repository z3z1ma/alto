"""Constants used throughout alto."""

ALTO_ROOT = ".alto"
"""The name of the directory where alto stores transient data."""

ALTO_DB_FILE = ".alto.json"
"""The name of the file where alto stores transient data."""

PLUGIN_DIR = "plugins"
"""The name of the subdirectory within the sys dir where alto stores plugins."""

CATALOG_DIR = "catalogs"
"""The name of the subdirectory within the sys dir where alto stores catalogs."""

STATE_DIR = "state/{env}"
"""The name of the subdirectory within the sys dir where alto stores state.json files."""

CONFIG_DIR = "config"
"""The name of the subdirectory within the root dir where alto stores config.json files."""

LOG_DIR = "logs/{env}"
"""The name of the subdirectory within the root dir where alto stores log files."""

DEFAULT_ENVIRONMENT = "dev"
"""The default environment to use when none is specified."""

SUPPORTED_CONFIG_FORMATS = {"json", "yaml", "yml", "toml"}
"""The supported config file formats."""
