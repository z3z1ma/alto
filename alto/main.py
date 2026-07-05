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
from alto.constants import SUPPORTED_CONFIG_FORMATS
from alto.logger import LOGGER
from alto.utils import bounded_table_rows, filesystem_info_parts, padded_table_rows
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
        _ = pos_args
        config_fname = "alto.{ext}"
        local_fname = "alto.local.{ext}"
        config_path = alto.config.working_directory.joinpath(config_fname)
        local_path = alto.config.working_directory.joinpath(local_fname)
        try:
            if self._config_exists(config_fname):
                LOGGER.info(
                    "❌ An Alto file already exists in {}".format(alto.config.working_directory)
                )
                return 1
            format_, project_name, status = self._project_options(
                opt_values, config_fname, local_fname
            )
            if status is not None:
                return status
            LOGGER.info(f"🏗  Building project in {alto.config.working_directory.resolve()}")
            self._write_project_files(config_path, local_path, format_, project_name)
            self._write_env_file()
            self._write_gitignore()
            self._write_example_assets()
            LOGGER.info("✅ Done!")
        except Exception as e:
            LOGGER.info("Failed to initialize project: {}".format(e))
            return 1
        else:
            return 0

    def _config_exists(self, config_fname):
        return any(
            (alto.config.working_directory / config_fname.format(ext=ext)).exists()
            for ext in SUPPORTED_CONFIG_FORMATS
        )

    def _project_options(self, opt_values, config_fname, local_fname):
        format_ = "toml"
        project_name = "default"
        while not opt_values["no-prompt"]:
            format_ = input("❓ Preferred config format? [toml, yaml, json]: ")
            if format_ not in SUPPORTED_CONFIG_FORMATS:
                LOGGER.info("❌ Invalid format")
                return format_, project_name, 1
            project_name = input("❓ Project name [default]: ") or "default"
            self._print_project_plan(project_name, config_fname, local_fname, format_)
            if input("❓ Proceed? [y/N]: ") in ("y", "Y", "yes", "Yes", "YES"):
                break
            LOGGER.info("Aborting...")
            return format_, project_name, 0
        return format_, project_name, None

    def _print_project_plan(self, project_name, config_fname, local_fname, format_) -> None:
        LOGGER.info(
            f"\n🙋 Files to generate for project `{project_name}`:\n\n"
            "1️⃣ "
            f" {alto.config.working_directory.joinpath(config_fname.format(ext=format_))}\n"
            "2️⃣ "
            f" {alto.config.working_directory.joinpath(local_fname.format(ext=format_))}\n"
        )

    def _write_project_files(self, config_path, local_path, format_, project_name) -> None:
        template_root = Path(__file__).parent / "incl"
        config_template_path = template_root / "alto.template.{ext}"
        local_template_path = template_root / "alto.local.template.{ext}"
        with (
            open(config_path.with_suffix("." + format_), "w") as conf,
            open(local_path.with_suffix("." + format_), "w") as local,
            open(config_template_path.with_suffix("." + format_), "r") as conf_template,
            open(local_template_path.with_suffix("." + format_), "r") as local_template,
        ):
            conf.write(conf_template.read().replace("{project}", project_name))
            local.write(local_template.read())

    def _write_env_file(self) -> None:
        env_path = alto.config.working_directory / ".env"
        if not env_path.is_file():
            with open(env_path, "w") as env:
                env.write("MY_SECRET=1\n")

    def _write_gitignore(self) -> None:
        gitignore_path = alto.config.working_directory / ".gitignore"
        if gitignore_path.is_file():
            return
        with open(gitignore_path, "w") as gitignore:
            gitignore.write(".env\n\n")
            gitignore.write(".alto/\n")
            gitignore.write(".alto.json\n")
            gitignore.write("alto.local.*\n")
            gitignore.write("alto.secrets.*\n")

    def _write_example_assets(self) -> None:
        asset_root = Path(__file__).parent / "incl"
        assets = (
            ("bls-series.json", "series.json"),
            ("dlt_example.py", "carbon_pipeline_dlt.py"),
        )
        for source, destination in assets:
            asset = asset_root / source
            with open(alto.config.working_directory / destination, "w") as f:
                f.write(asset.read_text() + "\n")


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
        from alto.repl import AltoCmd

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

        invoke_interpreter = pos_args and pos_args[0] == "python"
        if invoke_interpreter:
            # If the user is invoking python, we need to remove the first argument
            # so that it doesn't get passed to the python interpreter
            pos_args.pop(0)

        try:
            plugin_name = pos_args.pop(0)
        except IndexError:
            LOGGER.info("❌ Plugin name is required.")
            return 1

        plugin = engine.configuration.get_plugin(plugin_name)
        if not alto.engine.maybe_get_pex(plugin, engine.filesystem):
            LOGGER.info(f"🔨 Building {plugin.name}...")
            alto.engine.build_pex(plugin, engine.filesystem)
        exe = engine.filesystem.executable_path(plugin.pex_name)
        env: dict[str, str] = {**os.environ, **plugin.environment}
        if invoke_interpreter:
            LOGGER.info(f"🔨 Spawning Python interpreter in `{plugin.name}` plugin context...")
            env.pop("PEX_MODULE", None)
            env.pop("PEX_SCRIPT", None)
        else:
            LOGGER.info(f"🔨 Invoking {plugin.name}...")
        with subprocess.Popen([exe, *pos_args], env=env, cwd=engine.filesystem.root_dir) as proc:
            proc.wait()
            return proc.returncode or 0


class AltoFs(Command):
    doc_purpose = "interact with the remote filesystem"
    doc_usage = "alto fs [push|pull|rm] [src] [dest]"
    doc_description = (
        "Interact with the remote filesystem. "
        "Push and pull files to and from the remote filesystem or remove files."
    )
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
        action = self._action(pos_args)
        if action is None:
            return 1
        engine = alto.engine.AltoTaskEngine(root_dir=alto.config.working_directory)
        engine.setup(opt_values)
        return getattr(self, f"_{action}")(engine, opt_values, pos_args)

    def _action(self, pos_args):
        try:
            action = pos_args[0]
            assert action in ("push", "pull", "rm", "ls")
        except IndexError:
            LOGGER.info("❌ Must specify an action. See alto help fs")
            return None
        except AssertionError:
            LOGGER.info("❌ Invalid action, must be one of push, pull, rm, ls. See alto help fs")
            return None
        return action

    def _push(self, engine, opt_values, pos_args):
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
        return 0

    def _pull(self, engine, opt_values, pos_args):
        _ = opt_values
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
        return 0

    def _rm(self, engine, opt_values, pos_args):
        _ = opt_values
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
        return 0

    def _ls(self, engine, opt_values, pos_args):
        try:
            src = engine.filesystem._remote_path(pos_args[1])
        except IndexError:
            src = engine.filesystem._remote_path("")
        if not engine.fs.exists(src):
            LOGGER.info(f"❌ Source directory {src} does not exist")
            return 1
        rows, remainder = _fs_listing_rows(engine, src, opt_values["truncate"])
        for row in rows:
            LOGGER.info(row)
        if opt_values["truncate"] and remainder:
            LOGGER.info(f"({remainder} more files)")
        return 0


def _fs_listing_rows(engine, src: str, truncate: bool):
    res = engine.fs.ls(src, detail=False)
    return bounded_table_rows(res, lambda fname: _fs_listing_parts(engine, fname, src), truncate)


def _fs_listing_parts(engine, fname: str, src: str):
    info = engine.fs.info(fname)
    return filesystem_info_parts(info, info["name"][info["name"].index(src) :])


def _padded_rows(output, max_width):
    return padded_table_rows(output, max_width)


class AltoList(List):
    """List the tasks."""

    def _print_task(self, template, task, status, list_deps, tasks) -> None:
        """print a single task"""
        if task.name.split(":")[-1][0] == "_":
            return None
        line_data = {"name": task.name, "doc": task.doc}
        if status:
            assert self.dep_manager is not None
            if self.dep_manager.status_is_ignore(task):
                task_status = "ignore"
            else:
                task_status = self.dep_manager.get_status(task, tasks).status
            line_data["status"] = self.STATUS_MAP[task_status]
        self.outstream.write(_task_icon(task) + template.format(**line_data))
        if list_deps:
            for dep in task.file_dep:
                self.outstream.write(" - ✨  %s\n" % dep)
            self.outstream.write("\n")


def _task_icon(task) -> str:
    prefixes = {
        alto.engine.AltoCmd.CONFIG: "🛠  ",
        alto.engine.AltoCmd.BUILD: "👷 ",
        alto.engine.AltoCmd.CATALOG: "📖 ",
        alto.engine.AltoCmd.ABOUT: "💁 ",
        alto.engine.AltoCmd.APPLY: "📦 ",
        alto.engine.AltoCmd.TEST: "🧪 ",
        "tap-": "🔌 ",
        "target-": "📤 ",
        "reservoir": "💧 ",
    }
    for prefix, icon in prefixes.items():
        if task.name.startswith(prefix):
            return icon
    if "data pipeline" in task.doc:
        return "🔌 "
    return "🚀 "


# Patch the list command to ensure our sort order
AltoList.cmd_options[-1]["default"] = "definition"


class AltoDump(Command):
    doc_purpose = "dump the project configuration"
    doc_usage = "alto dump"
    doc_description = (
        "Dump the project configuration. This is useful for debugging. "
        "It can also be used to run your exact configuration on a different "
        "machine by copying the output to an `alto.json` and shipping it."
    )

    def execute(self, opt_values, pos_args):
        """Execute the command."""
        import json

        engine = alto.engine.AltoTaskEngine(root_dir=alto.config.working_directory)
        engine.setup(opt_values)
        if not pos_args:
            print(json.dumps({"default": engine.alto.to_dict()}, indent=2))
            return
        ptr = engine.alto
        for k in pos_args:
            ptr = ptr[k]
        if isinstance(ptr, (type(engine.alto), dict, list)):
            print(json.dumps(ptr.to_dict(), indent=2))
        else:
            print(ptr)


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
        commands["fs"] = AltoFs
        commands["dump"] = AltoDump
        # Remove commands
        del commands["reset-dep"]
        del commands["dumpdb"]
        return commands


def main(args=sys.argv[1:]) -> int:
    """Main entry point for the CLI."""
    args = args[:]
    LOGGER.info(f"📦 Alto version: {__version__}")
    alto.config.working_directory = _get_root_scrub_args(args)
    # Find the root directory traversing up the tree
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
    # Initialize the engine
    engine = alto.engine.AltoTaskEngine(root_dir=alto.config.working_directory.resolve())
    # Set the environment if not already set
    if "ALTO_ENV" not in os.environ:
        os.environ["ALTO_ENV"] = engine.alto.current_env
    # Report the working directory
    try:
        _work_dir = alto.config.working_directory.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        _work_dir = alto.config.working_directory.resolve()
    LOGGER.info(f"🏗  Working directory: {_work_dir}")
    # Report the environment
    LOGGER.info(f"🌎 Environment: {os.environ['ALTO_ENV']}\n")
    # Run the CLI
    return AltoMain(
        engine,
        config_filenames=(),
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
                raise SystemExit(1)
            except AssertionError:
                LOGGER.info(f"🚨 {root.resolve()} is not a directory")
                raise SystemExit(1)
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
