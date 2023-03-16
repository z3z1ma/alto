"""Serde provider.

This provider keeps track of the supported serialization formats and
provides access to the underlying serialization libraries. It also
keeps us a layer away from the underlying libraries, which allows us
to swap them out if we need to. Currently, we piggyback on the
serialization libraries that are already vendored by Dynaconf.
"""
import io
import json
import typing as t
from enum import Enum

import dynaconf.vendor.ruamel.yaml
import dynaconf.vendor.toml

__all__ = [
    "SerdeFormat",
    "serialize",
    "deserialize",
    "get_serializer",
    "get_deserializer",
]


class SerdeFormat(str, Enum):
    """Supported serialization formats."""

    JSON = "json"
    YAML = "yaml"
    TOML = "toml"


def __yaml_dumps(data: t.Any) -> str:
    """Dump data to YAML."""
    with io.StringIO() as stream:
        dynaconf.vendor.ruamel.yaml.round_trip_dump(data, stream)
        return stream.getvalue()


def __yaml_loads(data: str) -> t.Any:
    """Load data from YAML."""
    with io.StringIO(data) as stream:
        return dynaconf.vendor.ruamel.yaml.round_trip_load(stream)


_serializers: t.Dict[
    SerdeFormat, t.Tuple[t.Callable[[t.Any, t.IO], None], t.Callable[[str], str]]
] = {
    SerdeFormat.JSON: (json.dump, json.dumps),
    SerdeFormat.YAML: (dynaconf.vendor.ruamel.yaml.round_trip_dump, __yaml_dumps),
    SerdeFormat.TOML: (dynaconf.vendor.toml.dump, dynaconf.vendor.toml.dumps),
}
_deserializers: t.Dict[
    SerdeFormat, t.Tuple[t.Callable[[t.IO], t.Any], t.Callable[[str], t.Any]]
] = {
    SerdeFormat.JSON: (json.load, json.loads),
    SerdeFormat.YAML: (dynaconf.vendor.ruamel.yaml.round_trip_load, __yaml_loads),
    SerdeFormat.TOML: (dynaconf.vendor.toml.load, dynaconf.vendor.toml.loads),
}


def serialize(
    fmt: SerdeFormat, data: t.Any, destination: t.Optional[t.Union[str, t.IO]] = None
) -> t.Optional[str]:
    """Serialize data to a given format."""
    try:
        if isinstance(destination, str):
            dumper = _serializers[fmt][0]
            with open(destination, "w") as stream:
                dumper(data, stream)
            return None
        elif isinstance(destination, (t.IO, io.StringIO, io.BytesIO, io.RawIOBase, io.IOBase)):
            dumper = _serializers[fmt][0]
            stream = t.cast(t.IO, destination)
            dumper(data, stream)
            return None
        elif destination is None:
            dumper = _serializers[fmt][1]
            return dumper(data)
        else:
            raise TypeError(f"Unsupported type for destination: {type(destination)}")
    except KeyError:
        raise ValueError(f"Unsupported serialization format: {fmt}")


def deserialize(
    fmt: SerdeFormat, data: str, destination: t.Optional[t.Union[str, t.IO]] = None
) -> t.Any:
    """Deserialize data from a given format."""
    try:
        if isinstance(destination, str):
            loader = _deserializers[fmt][0]
            with open(destination, "r") as stream:
                return loader(stream)
        elif isinstance(destination, t.IO):
            loader = _deserializers[fmt][0]
            return loader(destination)
        elif destination is None:
            loader = _deserializers[fmt][1]
            return loader(data)
        else:
            raise TypeError(f"Unsupported type for destination: {type(destination)}")
    except KeyError:
        raise ValueError(f"Unsupported serialization format: {fmt}")


def get_serializer(
    fmt: SerdeFormat,
) -> t.Tuple[t.Callable[[t.Any, t.IO], None], t.Callable[[str], str]]:
    """Get a serializer by fmt.

    The serializer returns a tuple of a function that takes data and a
    file-like object and serializes the data to the file, and a function
    that takes data and returns a string containing the serialized data.
    """
    return _serializers[fmt]


def get_deserializer(
    fmt: SerdeFormat,
) -> t.Tuple[t.Callable[[t.IO], t.Any], t.Callable[[str], t.Any]]:
    """Get a deserializer by fmt.

    The deserializer returns a tuple of a function that takes a file-like
    object and returns the deserialized data, and a function that takes
    a string and returns the deserialized data.
    """
    return _deserializers[fmt]
