#! /usr/bin/env python3
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
"""Main entry point for the CLI."""
import os
import sys
import typing as t
from pathlib import Path

from doit.cmd_base import Command
from doit.cmd_list import List
from doit.cmd_run import Run
from doit.doit_cmd import DoitConfig, DoitMain

import alto.config
import alto.engine
from alto.constants import DEFAULT_ENVIRONMENT, SUPPORTED_CONFIG_FORMATS
from alto.logger import LOGGER
from alto.repl import AltoCmd
from alto.version import __version__

# Monkey-patch doit to use the vendored version
DoitConfig._TOML_LIBS = ["dynaconf.vendor.toml"]


class AltoInit(Command):
    doc_purpose = "Initialize a new project"
    doc_usage = "alto init"
    doc_description = (
        "Scan the current directory for a file named alto.{toml,yml,yaml,json} and "
        "create one if it doesn't exist."
    )
    cmd_options = [
        {
            "name": "no-prompt",
            "short": "n",
            "long": "no-prompt",
            "type": bool,
            "default": False,
            "help": "Do not prompt for confirmation before creating files",
        }
    ]

    def execute(self, opt_values, pos_args):
        """Initialize a new project."""
        config_fname = "alto.{ext}"
        secret_fname = "alto.secrets.{ext}"
        config_path = alto.config.working_directory.joinpath(config_fname)
        secret_path = alto.config.working_directory.joinpath(secret_fname)
        try:
            if any(
                (alto.config.working_directory / f"alto.{ext}").exists()
                for ext in SUPPORTED_CONFIG_FORMATS
            ):
                LOGGER.info(
                    "❌ An Alto file already exists in {}".format(alto.config.working_directory)
                )
                return 1

            format_ = "toml"
            from dynaconf.vendor.toml import dump

            while True and not opt_values["no-prompt"]:
                format_ = input("Preferred config format? [toml, yaml, json]: ")
                if format_ not in SUPPORTED_CONFIG_FORMATS:
                    LOGGER.info("❌ Invalid format")
                    return 1
                if format_ == "toml":
                    kwargs = {}
                elif format_ == "yaml":
                    from dynaconf.vendor.ruamel.yaml import dump  # noqa: F811

                    kwargs = {"default_flow_style": False}
                elif format_ == "json":
                    from json import dump  # noqa: F811

                    kwargs = {"indent": 2}
                else:
                    raise ValueError("Invalid format")
                LOGGER.info(
                    "🙋 Files to generate:\n\n"
                    "1️⃣ "
                    f" {alto.config.working_directory.joinpath(config_fname.format(ext=format_))}\n"
                    "2️⃣ "
                    f" {alto.config.working_directory.joinpath(secret_fname.format(ext=format_))}\n"
                )
                confirm = input("Proceed? [y/N]: ")
                if confirm in ("y", "Y", "yes", "Yes", "YES"):
                    break
                else:
                    LOGGER.info("Aborting...")
                    return 0
            # A default template for the config file
            # that lets users get started quickly and immediately run the project
            LOGGER.info(f"🏗  Building project in {alto.config.working_directory.resolve()}")
            with open(config_path.with_suffix("." + format_), "w") as conf, open(
                secret_path.with_suffix("." + format_), "w"
            ) as secret:
                dump(
                    {
                        "default": {
                            "project_name": os.urandom(4).hex(),
                            "extensions": ["evidence"],
                            "load_path": "raw",
                            "taps": {
                                "tap-carbon-intensity": {
                                    "pip_url": (
                                        "git+https://gitlab.com/meltano/tap-carbon-intensity.git"
                                        "#egg=tap_carbon_intensity"
                                    ),
                                    "load_path": "carbon_intensity",
                                    "config": {
                                        "any_key": (
                                            "**This will end up in a config.json passed to the"
                                            " tap**"
                                        ),
                                        "other_key": (
                                            "**You can find config on Github or MeltanoHub**"
                                        ),
                                    },
                                    "capabilities": ["state", "catalog"],
                                    "select": ["*.*"],
                                }
                            },
                            "targets": {
                                "target-jsonl": {
                                    "pip_url": "target-jsonl==0.1.4",
                                    "config": {
                                        "destination_path": "@format output/{this.load_path}"
                                    },
                                }
                            },
                        }
                    },
                    conf,
                    **kwargs,
                )
                dump(
                    {
                        "default": {
                            "_note_1": (
                                f"Notice the structure of this file is the same as alto.{format_}"
                            ),
                            "_note_2": "Anything in here is merged into the main config file",
                            "taps": {
                                "tap-carbon-intensity": {
                                    "some_secret": f"**I will be merged into alto.{format_}**"
                                }
                            },
                            "targets": {
                                "target-jsonl": {
                                    "other_secret": "**use this file for secret management**",
                                    "final_secret": "**exclude it from source control**",
                                }
                            },
                        }
                    },
                    secret,
                    **kwargs,
                )
        except Exception as e:
            LOGGER.info("Failed to initialize project: {}".format(e))
            return 1
        else:
            return 0


class AltoRun(Run):
    """Run the project."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class AltoRepl(Command):
    doc_purpose = "Drop into an interactive prompt with the project loaded"
    doc_usage = "alto repl"
    doc_description = "Uses cmd.Cmd to drop into an interactive prompt with the project loaded."

    def execute(self, opt_values, pos_args):
        """Drop into a REPL."""
        _ = pos_args
        engine = alto.engine.AltoTaskEngine(root_dir=alto.config.working_directory)
        engine.setup(opt_values)
        AltoCmd(engine=engine).cmdloop()


class AltoInvoke(Command):
    doc_purpose = "Invoke a plugin"
    doc_usage = "alto invoke <plugin_name> [args]"
    doc_description = "Invoke a plugin by name."

    def execute(self, opt_values, pos_args):
        """Invoke a plugin."""
        import subprocess

        engine = alto.engine.AltoTaskEngine(root_dir=alto.config.working_directory)
        engine.setup(opt_values)
        try:
            plugin_name = pos_args.pop(0)
        except IndexError:
            LOGGER.info("❌ Plugin name is required.")
            return 1
        from alto.engine import build_pex, maybe_get_pex

        plugin = engine.configuration.get_plugin(plugin_name)
        if not maybe_get_pex(plugin, engine.filesystem):
            LOGGER.info(f"🔨 Building {plugin.name}...")
            build_pex(plugin, engine.filesystem)
        exe = engine.filesystem.executable_path(plugin.pex_name)
        LOGGER.info(f"🔨 Invoking {plugin.name}...")
        with subprocess.Popen(
            [exe, *pos_args],
            env={**os.environ, **plugin.environment},
            cwd=engine.filesystem.root_dir,
        ) as proc:
            proc.wait()


class AltoFs(Command):
    doc_purpose = "Interact with the remote filesystem"
    doc_usage = "alto fs [push|pull|rm] [src] [dest]"
    cmd_options = [
        {
            "name": "truncate",
            "short": "t",
            "long": "truncate",
            "type": bool,
            "default": True,
            "help": "Truncate the output of the task",
        },
        {
            "name": "no-prompt",
            "short": "n",
            "long": "no-prompt",
            "type": bool,
            "default": False,
            "help": "Do not prompt for confirmation before overwriting files",
        },
    ]

    def execute(self, opt_values, pos_args):
        """Drop into a REPL."""
        try:
            action = pos_args[0]
            assert action in ("push", "pull", "rm", "ls")
        except IndexError:
            LOGGER.info("❌ Must specify an action. See alto help fs")
            return 1
        except AssertionError:
            LOGGER.info("❌ Invalid action, must be one of push, pull, rm, ls. See alto help fs")
            return 1
        engine = alto.engine.AltoTaskEngine(root_dir=alto.config.working_directory)
        engine.setup(opt_values)
        if action == "push":
            try:
                src, dest = pos_args[1], engine.filesystem._remote_path(pos_args[2])
            except IndexError:
                LOGGER.info("❌ Missing arguments. [src] [dest] are required.")
                return 1
            if not os.path.exists(src):
                LOGGER.info(f"❌ Source file {src} does not exist.")
                return 1
            if engine.fs.exists(dest) and not opt_values["no-prompt"]:
                LOGGER.info(f"Destination file {dest} already exists.")
                confirm = input("Overwrite? [y/N]: ")
                if confirm not in ("y", "Y", "yes", "Yes", "YES"):
                    LOGGER.info("Aborting...")
                    return 0
            LOGGER.info(f"☁️ Uploading {src} to {dest}...")
            engine.fs.put(src, dest)
        elif action == "pull":
            try:
                src, dest = engine.filesystem._remote_path(pos_args[1]), pos_args[2]
            except IndexError:
                LOGGER.info("❌ Missing arguments")
                return 1
            if not engine.fs.exists(src):
                LOGGER.info(f"❌ Source file {src} does not exist")
                return 1
            os.makedirs(os.path.dirname(dest), exist_ok=True, mode=0o755)
            LOGGER.info(f"☁️ Downloading {src} to {dest}...")
            engine.fs.get(src, dest)
        elif action == "rm":
            try:
                src = engine.filesystem._remote_path(pos_args[1])
            except IndexError:
                LOGGER.info("❌ Missing arguments. [src] is required.")
                return 1
            if not engine.fs.exists(src):
                LOGGER.info(f"❌ Source file {src} does not exist")
                return 1
            LOGGER.info(f"☁️ Deleting {src}...")
            engine.fs.rm(src)
        elif action == "ls":
            try:
                src = engine.filesystem._remote_path(pos_args[1])
            except IndexError:
                src = engine.filesystem._remote_path("")
            if not engine.fs.exists(src):
                LOGGER.info(f"❌ Source directory {src} does not exist")
                return 1
            res = engine.fs.ls(src, detail=False)
            output = [["Type", "Size (Mb)", "Last Updated", "Name"]]
            max_width = [len(w) for w in output[0]]
            remainder = 0
            for n, f in enumerate(res):
                i = engine.fs.info(f)
                parts = [
                    i["type"][0],
                    i["size"] * 1e-6,
                    i.get("updated", ""),
                    i["name"][i["name"].index(src) :],
                ]
                if parts[0] == "d":
                    parts[1] = ""
                else:
                    parts[1] = f"{parts[1]:.02f}"
                output.append(parts)
                for i, p in enumerate(parts):
                    max_width[i] = max(max_width[i], len(str(p)))
                if opt_values["truncate"] and n > 10:
                    output.append(["...", "...", "...", "..."])
                    remainder = len(res[n + 1 :])
                    break
            for i, row in enumerate(output):
                for j, p in enumerate(row):
                    output[i][j] = str(p).ljust(max_width[j] + 2)
            LOGGER.info("".join(map(str, output[0])))
            for row in output[1:]:
                LOGGER.info("".join(map(str, row)))
            if opt_values["truncate"] and remainder:
                LOGGER.info(f"({remainder} more files)")

        return 0


class AltoList(List):
    """List the tasks."""

    def _print_task(self, template, task, status, list_deps, tasks):
        """print a single task"""
        line_data = {"name": task.name, "doc": task.doc}
        if status:
            if self.dep_manager.status_is_ignore(task):
                task_status = "ignore"
            else:
                task_status = self.dep_manager.get_status(task, tasks).status
            line_data["status"] = self.STATUS_MAP[task_status]
        if task.name.startswith(alto.engine.AltoCmd.CONFIG):
            self.outstream.write("🛠  " + template.format(**line_data))
        elif task.name.startswith(alto.engine.AltoCmd.BUILD):
            self.outstream.write("👷 " + template.format(**line_data))
        elif task.name.startswith(alto.engine.AltoCmd.CATALOG):
            self.outstream.write("📖 " + template.format(**line_data))
        elif task.name.startswith(alto.engine.AltoCmd.ABOUT):
            self.outstream.write("💁 " + template.format(**line_data))
        elif task.name.startswith(alto.engine.AltoCmd.APPLY):
            self.outstream.write("📦 " + template.format(**line_data))
        elif task.name.startswith(alto.engine.AltoCmd.TEST):
            self.outstream.write("🧪 " + template.format(**line_data))
        elif task.name.startswith("tap-"):
            self.outstream.write("🔌 " + template.format(**line_data))
        elif task.name.startswith("target-"):
            self.outstream.write("📤 " + template.format(**line_data))
        elif task.name.startswith("reservoir"):
            self.outstream.write("💧 " + template.format(**line_data))
        else:
            self.outstream.write("🚀 " + template.format(**line_data))
        if list_deps:
            for dep in task.file_dep:
                self.outstream.write(" - ✨  %s\n" % dep)
            self.outstream.write("\n")


class AltoMain(DoitMain):
    """Main entry point for the CLI."""

    def get_cmds(self):
        """Get the commands to register.

        This shows how we can add commands as well as override existing ones.
        """
        commands = super().get_cmds()
        # Overrides
        commands["run"] = AltoRun
        commands["list"] = AltoList
        # New commands
        commands["invoke"] = AltoInvoke
        commands["init"] = AltoInit
        commands["repl"] = AltoRepl
        commands["fs"] = AltoFs
        # Remove commands
        del commands["reset-dep"]
        del commands["dumpdb"]
        return commands


def main(args=sys.argv[1:]) -> int:
    """Main entry point for the CLI."""
    args = args[:]
    LOGGER.info(f"📦 Alto version: {__version__}")
    alto.config.working_directory = _get_root_scrub_args(args)
    _init_dir = alto.config.working_directory
    while (
        not any(
            (alto.config.working_directory / f"alto.{ext}").exists()
            for ext in SUPPORTED_CONFIG_FORMATS
        )
        and "init" not in args
    ):
        alto.config.working_directory = alto.config.working_directory.parent
        if alto.config.working_directory == alto.config.working_directory.parent:
            LOGGER.info(f"\n🚨 No Alto file found in {_init_dir.resolve()}")
            LOGGER.info(
                "🚧 Run alto init to create one or invoke "
                "alto with -r/--root to specify a directory..."
            )
            return 1
    if "ALTO_ENV" not in os.environ:
        os.environ["ALTO_ENV"] = DEFAULT_ENVIRONMENT
    LOGGER.info(
        f"🏗  Working directory: {alto.config.working_directory.resolve().relative_to(Path.cwd())}"
    )
    LOGGER.info(f"🌎 Environment: {os.environ['ALTO_ENV']}\n")
    return AltoMain(
        alto.engine.AltoTaskEngine(root_dir=alto.config.working_directory),
        extra_config={"list": {"status": True, "sort": "definition"}},
    ).run(args)


def _get_root_scrub_args(args: t.List[str]) -> Path:
    """Get the root directory and scrub the sys args.

    This is a helper function for the main entry point. It's used to get the root
    directory and scrub the sys args so that the doit CLI doesn't complain about
    unrecognized arguments.
    """
    for ix, arg in enumerate(list(args)):
        if arg in ("--root", "-r"):
            try:
                root = Path(args[ix + 1])
                assert root.is_dir()
            except IndexError:
                LOGGER.info("🚨 Missing root directory argument for --root/-r")
                exit(1)
            except AssertionError:
                LOGGER.info(f"🚨 {root.resolve()} is not a directory")
                exit(1)
            args.pop(ix)
            args.pop(ix)
            break
        elif arg.startswith("--root="):
            root = Path(arg.split("=", 1)[1])
            assert root.is_dir()
            args.pop(ix)
            break
    else:
        root = Path.cwd()
    return root


if __name__ == "__main__":
    sys.exit(main())
