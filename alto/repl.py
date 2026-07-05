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
"""Alto command line interface.

This module provides a command line interface for interacting with an Alto
engine. It is intended to be used for debugging and development purposes.
"""

import cmd
import os
import subprocess
import tempfile
import typing as t
from functools import lru_cache

from alto.utils import bounded_table_rows, filesystem_info_parts

__all__ = ["AltoCmd"]


class _EngineProtocol(t.Protocol):
    fs: t.Any
    filesystem: t.Any


class AltoCmd(cmd.Cmd):
    intro = "\nAlto v0.1.0   Type help or ? to list commands.\n"
    prompt = "(alto engine) "
    use_rawinput = True

    def __init__(self, engine: _EngineProtocol, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.engine = engine

    def do_ls(self, arg: str):
        """List files in a directory."""
        truncate = True
        if "--all" in arg:
            arg = arg.replace("--all", "").strip()
            truncate = False
        getter = self.engine.fs.ls
        if "*" in arg:
            getter = self.engine.fs.glob
        res = getter(arg.lstrip("/"), detail=False)
        rows, remainder = _listing_rows(self.engine, res, truncate)
        for row in rows:
            print(row)
        if truncate and remainder:
            print(f"({remainder} more files)")

    @lru_cache
    def complete_ls(self, text: str, line: str, _begidx: int, _endidx: int) -> t.List[str]:
        """List files in a directory."""
        path = line.split(maxsplit=1)[-1].replace("--all", "").strip()
        if self.engine.fs.isdir(path) and not path.endswith("/"):
            text += "/"
            return [text]
        elif self.engine.fs.isfile(path):
            return []
        elif self.engine.fs.isdir(path):
            getter = self.engine.fs.ls
        else:
            getter = self.engine.fs.glob
            path += "*"
        return [f.split("/")[-1] for i, f in enumerate(getter(path, detail=False)) if i < 25]

    def do_state(self, arg: str):
        """Edit a pipeline state."""

        parts = arg.split()
        tap = parts[0]
        target = parts[1]

        remote_path = self.engine.filesystem.state_path(tap, target, remote=True)
        (fd, tmp_path) = tempfile.mkstemp()

        try:
            self.engine.fs.download(remote_path, tmp_path)
        except Exception:
            print("No state found.")
            return

        fp = os.fdopen(fd, "r")
        original = fp.read()
        fp.close()

        editor = os.getenv("EDITOR", "vi")
        subprocess.run([editor, tmp_path])

        with open(tmp_path, "r") as f:
            modified = f.read()

        if modified != original:
            self.engine.fs.upload(tmp_path, remote_path)

        os.unlink(tmp_path)

    def do_EOF(self, arg: str):
        """Exit the REPL."""
        return True

    # Exit the REPL
    do_q = do_EOF
    do_quit = do_EOF
    do_exit = do_EOF


def _listing_rows(engine: _EngineProtocol, files, truncate: bool):
    return bounded_table_rows(files, lambda fname: _listing_parts(engine, fname), truncate)


def _listing_parts(engine: _EngineProtocol, fname: str):
    info = engine.fs.info(fname)
    return filesystem_info_parts(info, info["name"])
