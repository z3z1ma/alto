import json
from pathlib import Path
from typing import Any, BinaryIO, Dict, Optional, TextIO, Union

from alto.utils import merge

__all__ = ["ensure_state", "parse_state_from_stdout", "update_state"]


MELTANO_STATE_CONTAINER = "singer_state"
"""
For unnesting state that was managed by Meltano which wraps raw
state in a singer_state key when accessed via its state get CLI
"""


def ensure_state(state_path: Union[Path, str], indent: Optional[int] = 2) -> None:
    """Ensures the state file exists, is valid JSON, and is not wrapped in a singer_state key"""
    if isinstance(state_path, str):
        state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    if state_path.exists():
        contents = json.loads(state_path.read_text())
    else:
        contents = {}
    if MELTANO_STATE_CONTAINER in contents:
        contents = contents[MELTANO_STATE_CONTAINER]
    state_path.write_text(json.dumps(contents, indent=indent))


def parse_state_from_stdout(stdout: Union[Path, TextIO, BinaryIO]) -> Dict[str, Any]:
    """Parses the state from the target's stdout. Target stdout is expected to be a stream of
    JSON objects, each of which is merged into the state. The state is returned as a dict."""
    state = {}
    if isinstance(stdout, TextIO):
        stdout_iter = stdout
    elif isinstance(stdout, BinaryIO):
        stdout_iter = stdout.read().decode("utf-8").splitlines()
    else:
        stdout_iter = stdout.read_text().splitlines()
    for output in stdout_iter:
        try:
            merge(source=json.loads(output), destination=state)
        except json.JSONDecodeError:
            continue
        except KeyError:
            continue
    return state


def update_state(state_path: Path, target_stdout: Path, write: bool = True) -> Dict[str, Any]:
    """Updates the state file with the latest state from the target's stdout"""
    base_state = json.loads(state_path.read_text())
    merge(source=parse_state_from_stdout(target_stdout), destination=base_state)
    if write:
        state_path.write_text(json.dumps(base_state, indent=2))
    return base_state
