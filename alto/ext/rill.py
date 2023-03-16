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
import shutil
import typing as t
from pathlib import Path

from doit.tools import LongRunning
from dynaconf import Validator

from alto.engine import AltoExtension
from alto.models import AltoTask, AltoTaskData
from alto.providers.serde import SerdeFormat, serialize

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
        """Run Rill web server."""
        return (
            AltoTask(name="start")
            .set_actions(LongRunning(f"rill start --project {self.root}"))
            .set_task_dep(f"{self.name}:initialize")
            .set_doc(
                "When you run rill start, it parses your project and ingests any missing data "
                "sources into a local DuckDB database. After your project has been re-hydrated, it "
                "starts the Rill web app on http://localhost:9009"
            )
            .set_verbosity(2)
            .data
        )

    def managed_sources(self) -> t.Iterator[AltoTaskData]:
        """Yields managed sources with optional hooks.

        This provide a way to both create rill sources from the alto configuration
        and to further add hooks to the source creation process. For example, you
        can use this to run `bq extract` to refresh a parquet that the source points to.
        Or run dbt, or run a custom python script, a dlt pipeline, etc.
        """

        def _dump_source(name: str, source_settings: t.Dict[str, t.Any]) -> None:
            with open(self.root.joinpath(f"sources/{name}.yaml"), "w") as file:
                serialize(SerdeFormat.YAML, data=dict(source_settings), destination=file)

        for name, source in self.spec.get("sources", {}).items():
            hooks = source.pop("hooks", [])
            if not isinstance(hooks, list):
                raise ValueError(
                    f"Invalid hooks definition in rill.sources.{name} (must be a list)."
                )
            task = AltoTask(name=f"sync-{name}")
            for hook in hooks:
                task.set_actions(hook)
            task.set_actions((_dump_source, (name, source))).set_doc(
                f"Create Rill source {name} and execute hooks."
            )
            yield task.data

    def tasks(self) -> t.Iterator[AltoTaskData]:
        """Yields tasks."""
        yield self.initialize()
        yield self.start()
        yield from self.managed_sources()
