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
"""This module implements the Evidence.dev extension."""
import json
import os
import shutil
import typing as t

from dynaconf import Validator

from alto.engine import AltoExtension
from alto.models import AltoTask, AltoTaskData

__all__ = ["register"]
__version__ = "0.1.0"


def register():
    """Register the extension."""
    return Evidence


class Evidence(AltoExtension):
    """Evidence.dev extension."""

    def init_hook(self) -> None:
        """Initialize the extension."""
        # Quick check for executables
        if not (shutil.which("npx") and shutil.which("npm")):
            raise RuntimeError(
                "The `evidence` extension is enabled but npm/npx is not installed. Please "
                "visit https://nodejs.dev/en/download/package-manager/ to get set up."
            )
        # Set the Evidence home directory
        root = os.path.expanduser(os.getenv("EVIDENCE_HOME", self.spec.home))
        if root.startswith("/"):
            self.spec.home = root
        else:
            self.spec.home = str(self.filesystem.root_dir / root)
        # Set the adapter
        adapter = os.getenv("DATABASE", self.spec.database)
        os.environ["DATABASE"] = adapter
        # This will be suppressed if the user has a config file so alto can use its
        # environment aware configuration to manage the Evidence project.
        self._config_file = os.path.join(
            self.spec.home,
            ".evidence",
            "template",
            "evidence.settings.json",
        )
        if os.path.exists(self._config_file):
            with open(self._config_file, "r") as f:
                self._config_file_cached = json.load(f)
        else:
            self._config_file_cached = None

    @staticmethod
    def get_validators() -> t.List["Validator"]:
        return [
            Validator(
                "utilities.evidence.home",
                default="./reports",
                cast=str,
                apply_default_on_none=True,
                description="Evidence home directory.",
            ),
            Validator(
                "utilities.evidence.strict",
                default=False,
                cast=bool,
                description="Run Evidence in strict mode.",
            ),
            Validator(
                "utilities.evidence.database",
                default="duckdb",
                cast=str,
                apply_default_on_none=True,
                description="Database adapter to use.",
            ),
        ]

    def _restore_config_if_cached(self) -> None:
        if self._config_file_cached is not None:
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._config_file_cached, f)

    def suppress_config(self) -> None:
        def _suppress_config() -> None:
            if os.path.exists(self._config_file):
                os.remove(self._config_file)

        return AltoTask(name="_suppress_config").set_actions(_suppress_config).data

    def initialize(self) -> AltoTaskData:
        """Run 'npx degit' to generate Evidence project from template."""
        return (
            AltoTask(name="initialize")
            .set_actions(
                f"mkdir -p {self.spec.home}",
                f"npx --yes degit evidence-dev/template {self.spec.home}",
            )
            .set_doc("Generate Evidence project from template.")
            .set_clean(f"rm -rf {self.spec.home}")
            .set_uptodate((os.path.exists, (f"{self.spec.home}/package.json",)))
            .set_targets(f"{self.spec.home}/package.json")
            .set_verbosity(2)
            .data
        )

    def build(self) -> AltoTaskData:
        """Run 'npm run build' in the Evidence home dir."""
        if self.spec.get("strict", False):
            build = "build:strict"
        else:
            build = "build"
        task = (
            AltoTask(name="build")
            .set_actions(
                f"npm --prefix {self.spec.home} install",
                f"npm --prefix {self.spec.home} run {build}",
            )
            .set_setup(f"{self.name}:_suppress_config")
            .set_teardown((self._restore_config_if_cached,))
            .set_task_dep(f"{self.name}:initialize")
            .set_doc("Build the Evidence dev reports.")
            .set_clean(f"rm -rf {self.spec.home}/build")
            .set_uptodate(False)
            .set_verbosity(2)
        )
        return task.data

    def dev(self) -> AltoTaskData:
        """Run 'npm run dev' in the Evidence home dir."""
        return (
            AltoTask(name="dev")
            .set_actions(
                f"npm --prefix {self.spec.home} install",
                f"npm --prefix {self.spec.home} run dev",
            )
            .set_task_dep(f"{self.name}:initialize")
            .set_setup(f"{self.name}:_suppress_config")
            .set_teardown((self._restore_config_if_cached,))
            .set_doc("Run the Evidence dev server.")
            .set_uptodate(False)
            .set_verbosity(2)
            .data
        )

    def vars(self) -> AltoTaskData:
        """Get help knowing what vars to configure per adapter. Not documented anywhere. 🤷‍♀️"""

        def _print_env_vars() -> t.Dict[str, t.List[str]]:
            import re
            import urllib.request

            adapters = (
                "bigquery",
                "duckdb",
                "mysql",
                "postgres",
                "snowflake",
                "sqlite",
            )
            output = {}
            for adapter in adapters:
                url = (
                    "https://raw.githubusercontent.com/"
                    f"evidence-dev/evidence/main/packages/{adapter}/index.cjs"
                )
                with urllib.request.urlopen(url) as response:
                    content = response.read().decode("utf-8")
                matches = re.findall(
                    rf'process.env\["{adapter.upper()}_([A-Z_]+)"\]',
                    content,
                    flags=re.DOTALL,
                )
                output[adapter] = []
                if matches:
                    print(f"# {adapter}", "& redshift" if adapter == "postgres" else "")
                    for match in matches:
                        print(f"{adapter.upper()}_{match}")
                        output[adapter].append(f"{adapter.upper()}_{match}")
                print()
            return output

        return (
            AltoTask(name="vars")
            .set_actions((_print_env_vars,))
            .set_doc(
                "Dump env vars used to configure evidence. These must be set in your environment, "
                "in your .env file, or in your alto configuration file."
            )
            .set_verbosity(2)
            .set_uptodate(False)
            .data
        )

    def tasks(self) -> t.Iterator[AltoTaskData]:
        """Yields tasks."""
        yield self.initialize()
        yield self.build()
        yield self.dev()
        yield self.vars()
        yield self.suppress_config()
