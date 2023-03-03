#! /usr/bin/env python3
"""Main entry point for the CLI."""
import os
import sys
import typing as t
from contextlib import contextmanager
from pathlib import Path

from doit.cmd_base import Command
from doit.cmd_list import List
from doit.cmd_run import Run
from doit.doit_cmd import DoitConfig, DoitMain
from dynaconf.vendor.toml import dumps

import alto.config
import alto.engine
from alto.constants import DEFAULT_ENVIRONMENT, SUPPORTED_CONFIG_FORMATS
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
    cmd_options = [{
        "name": "no-prompt",
        "short": "n",
        "long": "no-prompt",
        "type": bool,
        "default": False,
        "help": "Do not prompt for confirmation before creating files",
    }]

    def execute(self, opt_values, pos_args):
        """Initialize a new project."""
        config_fname = "alto.toml"
        secret_fname = "alto.secrets.toml"
        config_path = alto.config.working_directory.joinpath(config_fname)
        secret_path = alto.config.working_directory.joinpath(secret_fname)
        try:
            if any(
                (alto.config.working_directory / f"alto.{ext}").exists()
                for ext in SUPPORTED_CONFIG_FORMATS
            ):
                print("An Alto file already exists in {}".format(alto.config.working_directory))
                return 1

            while True and not opt_values["no-prompt"]:
                print(
                    "🙋 Files to generate:\n\n"
                    f"1️⃣  {alto.config.working_directory.joinpath(config_fname)}\n"
                    f"2️⃣  {alto.config.working_directory.joinpath(secret_fname)}\n"
                )
                confirm = input("Proceed? [y/N]: ")
                if confirm in ("y", "Y", "yes", "Yes", "YES"):
                    break
                else:
                    print("Aborting...")
                    return 0
            # A default template for the config file
            # that lets users get started quickly and immediately run the project
            print(f"🏗  Building project in {alto.config.working_directory.resolve()}")
            config_path.write_text(
                dumps(
                    {
                        "default": {
                            "project_name": os.urandom(4).hex(),
                            "extensions": [],
                            "namespace": "raw",
                            "taps": {
                                "tap-carbon-intensity": {
                                    "pip_url": (
                                        "git+https://gitlab.com/meltano/tap-carbon-intensity.git"
                                        "#egg=tap_carbon_intensity"
                                    ),
                                    "namespace": "carbon_intensity",
                                    "config": {
                                        "any_key": (
                                            "<this will end up in a config.json passed to the tap>"
                                        )
                                    },
                                    "capabilities": ["state", "catalog"],
                                    "select": ["*.*"],
                                }
                            },
                            "targets": {
                                "target-jsonl": {
                                    "pip_url": "target-jsonl==0.1.4",
                                    "config": {"destination_path": "output"},
                                }
                            },
                        }
                    }
                )
            )
            secret_path.write_text(
                dumps(
                    {
                        "default": {
                            "taps": {
                                "tap-carbon-intensity": {
                                    "some_secret": "<I will be merged into alto.toml>"
                                }
                            },
                            "targets": {
                                "target-jsonl": {
                                    "other_secret": "<use this file for secret management>",
                                    "final_secret": "<exclude it from source control>",
                                }
                            },
                        }
                    }
                )
            )
        except Exception as e:
            print("Failed to initialize project: {}".format(e))
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
        elif task.name.startswith(alto.engine.AltoCmd.INVOKE):
            self.outstream.write("🔮 " + template.format(**line_data))
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
        commands["init"] = AltoInit
        commands["run"] = AltoRun
        commands["repl"] = AltoRepl
        commands["list"] = AltoList
        return commands


def main(args = sys.argv[1:]) -> int:
    """Main entry point for the CLI."""
    args = args[:]
    print(f"📦 Alto version: {__version__}")
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
            print(f"\n🚨 No Alto file found in {_init_dir.resolve()}")
            print(
                "🚧 Run alto init to create one or invoke "
                "alto with -r/--root to specify a directory..."
            )
            return 1
    if "ALTO_ENV" not in os.environ:
        os.environ["ALTO_ENV"] = DEFAULT_ENVIRONMENT
    print(
        f"🏗  Working directory: {alto.config.working_directory.resolve().relative_to(Path.cwd())}"
    )
    print(f"🌎 Environment: {os.environ['ALTO_ENV']}\n")

    @contextmanager
    def _ctx(path):
        odir = Path.cwd()
        os.chdir(path)
        try:
            yield
        finally:
            os.chdir(odir)

    with _ctx(alto.config.working_directory):
        return AltoMain(
            alto.engine.AltoTaskEngine(Path.cwd()),
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
                print("🚨 Missing root directory argument for --root/-r")
                exit(1)
            except AssertionError:
                print(f"🚨 {root.resolve()} is not a directory")
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
