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
import os
import typing as t

from dynaconf import Validator

from alto.engine import AltoExtension
from alto.models import AltoTask


def register():
    """Register the extension."""
    return Evidence


class Evidence(AltoExtension):
    """Evidence.dev extension."""

    def init_hook(self) -> None:
        """Initialize the extension."""
        _path = os.path.expanduser(self.spec.config.home)
        if _path.startswith("/"):
            self.spec.config.home = _path
        else:
            self.spec.config.home = os.path.join(self.filesystem.root_dir, _path)
        os.makedirs(self.spec.config.home, exist_ok=True, mode=0o755)

    @staticmethod
    def get_validators() -> t.List["Validator"]:
        return [
            Validator(
                "UTILITIES.evidence.config.home",
                default="./reports",
                cast=str,
                apply_default_on_none=True,
                description="Evidence home directory.",
            ),
            Validator(
                "UTILITIES.evidence.config.strict",
                default=False,
                cast=bool,
                apply_default_on_none=True,
                description="Run Evidence in strict mode.",
            ),
        ]

    def initialize(self):
        """Run 'npx degit' to generate Evidence project from template."""
        return (
            AltoTask(name="initialize")
            .set_actions(f"npx --yes degit evidence-dev/template {self.spec.config.home}")
            .set_doc("Generate Evidence project from template.")
            .set_clean(f"rm -rf {self.spec.config.home}")
            .set_uptodate(f"test -f {self.spec.config.home}/package.json")
            .set_targets(f"{self.spec.config.home}/package.json")
            .set_verbosity(2)
            .data
        )

    def build(self):
        """Run 'npm run build' in the Evidence home dir."""
        task = (
            AltoTask(name="build")
            .set_actions(f"npm --prefix {self.spec.config.home} install")
            .set_file_dep(f"{self.spec.config.home}/package.json")
            .set_doc("Build the Evidence dev reports.")
            .set_clean(f"rm -rf {self.spec.config.home}/build")
            .set_verbosity(2)
        )
        if self.spec.config.get("strict", False):
            task.set_actions(f"npm --prefix {self.spec.config.home} run build:strict")
        else:
            task.set_actions(f"npm --prefix {self.spec.config.home} run build")
        return task.data

    def dev(self):
        """Run 'npm run dev' in the Evidence home dir."""
        return (
            AltoTask(name="dev")
            .set_actions(
                f"npm --prefix {self.spec.config.home} install",
                f"npm --prefix {self.spec.config.home} run dev",
            )
            .set_file_dep(f"{self.spec.config.home}/package.json")
            .set_doc("Run the Evidence dev server.")
            .set_verbosity(2)
            .data
        )

    def tasks(self):
        """Yields tasks."""
        yield self.initialize()
        yield self.build()
        yield self.dev()
