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

if t.TYPE_CHECKING:
    from alto.engine import AltoTaskEngine

__all__ = ["AltoCmd"]


class AltoCmd(cmd.Cmd):
    intro = "\nAlto v0.1.0   Type help or ? to list commands.\n"
    prompt = "(alto engine) "
    use_rawinput = 1

    def __init__(self, engine: "AltoTaskEngine", *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.engine = engine

    def do_ls(self, arg: str):
        """List files in a directory."""
        truncate, remainder = True, 0
        if "--all" in arg:
            arg = arg.replace("--all", "").strip()
            truncate = False
        getter = self.engine.fs.ls
        if "*" in arg:
            getter = self.engine.fs.glob
        output = [["Type", "Size (Mb)", "Last Updated", "Name"]]
        max_width = [len(w) for w in output[0]]
        res = getter(arg.lstrip("/"), detail=False)
        for n, f in enumerate(res):
            i = self.engine.fs.info(f)
            parts = [i["type"][0], i["size"] * 1e-6, i.get("updated", ""), i["name"]]
            if parts[0] == "d":
                parts[1] = ""
            else:
                parts[1] = f"{parts[1]:.02f}"
            output.append(parts)
            for i, p in enumerate(parts):
                max_width[i] = max(max_width[i], len(str(p)))
            if truncate and n > 10:
                output.append(["...", "...", "...", "..."])
                remainder = len(res[n + 1 :])
                break
        for i, row in enumerate(output):
            for j, p in enumerate(row):
                output[i][j] = str(p).ljust(max_width[j] + 2)
        print("".join(map(str, output[0])))
        for row in output[1:]:
            print("".join(map(str, row)))
        if truncate and remainder:
            print(f"({remainder} more files)")

    @lru_cache
    def complete_ls(self, text: str, line: str, begidx: int, endidx: int) -> t.List[str]:
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
