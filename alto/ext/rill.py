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
"""This module implements the Rill-Developer extension."""
import os
import shlex
import shutil
import subprocess
import typing as t
from pathlib import Path

from doit.tools import LongRunning
from dynaconf import Validator

from alto.engine import AltoExtension
from alto.models import AltoTask, AltoTaskData
from alto.providers.serde import SerdeFormat, deserialize

__all__ = ["register"]
__version__ = "0.1.0"


def register():
    """Register the extension."""
    return RillDeveloper


class RillDeveloper(AltoExtension):
    """Rill Developer extension."""

    name = "rill"

    def init_hook(self) -> None:
        if not shutil.which("rill"):
            raise RuntimeError(
                "The `rill` extension is enabled but rill is not installed. Please "
                "visit https://docs.rilldata.com/using-rill/install to get set up."
            )
        self.root = Path(os.getenv("RILL_HOME", self.spec.home)).resolve()

    @staticmethod
    def get_validators() -> t.List["Validator"]:
        return [
            Validator(
                "utilities.rill.home",
                default="rill",
                cast=str,
                apply_default_on_none=True,
                description="Rill home directory.",
            )
        ]

    def initialize(self) -> AltoTaskData:
        """Create a new, empty Rill project."""
        return (
            AltoTask(name="initialize")
            .set_actions(f"rill init --project {self.root}")
            .set_doc("Create a new, empty Rill project.")
            .set_uptodate((self.root.joinpath("rill.yaml").exists,))
            .set_verbosity(2)
            .data
        )

    def start(self) -> AltoTaskData:
        """Run Rill web server. Optional hooks can be run before starting the server."""

        def _run_hooks(hooks: t.List[str]) -> None:
            """Run hooks before starting the Rill web server.

            Useful for generating or refreshing data sources before starting the server.
            """
            for hook in hooks:
                src = self.root.joinpath("sources", f"{hook}.yaml")
                if not src.exists():
                    raise RuntimeError(f"Source {hook} does not exist.")
                data: dict = deserialize(SerdeFormat.YAML, src.read_text())
                for action in data.get("_hooks", []):
                    subprocess.run(shlex.split(action), check=True)

        return (
            AltoTask(name="start")
            .set_actions(
                (_run_hooks,),
                LongRunning(f"rill start --project {self.root}"),
            )
            .set_task_dep(f"{self.name}:initialize")
            .set_params(
                {
                    "name": "hooks",
                    "short": "h",
                    "long": "hook",
                    "type": list,
                    "default": [],
                    "help": "Run hooks before starting the Rill web server.",
                }
            )
            .set_doc(
                "When you run rill start, it parses your project and ingests any missing data "
                "sources into a local DuckDB database. After your project has been re-hydrated, it "
                "starts the Rill web app on http://localhost:9009"
            )
            .set_verbosity(2)
            .data
        )

    def sync(self) -> t.Iterator[AltoTaskData]:
        """Sync all sources with hooks."""

        def _run_hooks() -> None:
            for src in self.root.glob("sources/**/*.yaml"):
                data: dict = deserialize(SerdeFormat.YAML, src.read_text())
                for action in data.get("_hooks", []):
                    print(f"{src} -> hook: {action}")
                    subprocess.run(shlex.split(action), check=True)

        return (
            AltoTask(name="sync")
            .set_actions(_run_hooks)
            .set_doc("Run hooks for all sources containing a _hooks array.")
            .data
        )

    def tasks(self) -> t.Iterator[AltoTaskData]:
        """Yields tasks."""
        yield self.initialize()
        yield self.start()
        yield self.sync()
