import os
import typing as t
from queue import Queue
from threading import Thread

import alto.constants
import alto.engine

try:
    import dlt  # type: ignore
except ImportError:
    raise ImportError("dlt is not installed. Please install dlt to use this module.")


class SingerTapDemux(Thread):
    """Singer taps output all records to a single stream.

    This class demuxes the records into separate streams for each tap stream. This permits
    each stream to be processed in parallel and dlt to manage each as a separate target.
    """

    daemon = True

    def __init__(self, source: str, env: str, *streams: t.List[str]) -> None:
        """Initialize the demuxer."""
        super().__init__()
        self.streams = {stream: Queue() for stream in streams}
        self.source = source
        self.env = env

    def run(self) -> None:
        """Run the demuxer thread."""
        engine = alto.engine.get_engine(env=self.env)
        (tap,) = alto.engine.make_plugins(
            self.source,
            filesystem=engine.filesystem,
            configuration=engine.configuration,
        )
        tap.select = list(self.streams.keys())
        with alto.engine.tap_runner(
            tap,
            engine.filesystem,
            engine.alto,
            state_key=f"dlt-{self.source}-{self.env}",
            records_only=True,
        ) as tap_stream:
            for payload in tap_stream:
                if payload is None:
                    continue
                stream, record = payload
                self.streams[stream].put(record)
        # Put a None on each stream to signal the end of the stream
        for stream in self.streams.values():
            stream.put(None)


@dlt.source
def singer(
    source: str,
    streams: t.List[str],
    env: t.Optional[str] = None,
    resource_options: t.Optional[t.Dict[str, t.Any]] = None,
) -> t.Sequence[t.Any]:
    """Singer source function."""
    if resource_options is None:
        resource_options = {}
    if env is None:
        env = os.getenv("ALTO_ENV", alto.constants.DEFAULT_ENVIRONMENT)
    # Ensure the env is set
    os.environ["ALTO_ENV"] = env
    # Create the demuxer
    demux = SingerTapDemux(source, env, *streams)
    demux.start()
    # Create the dlt resources
    return tuple(
        singer_stream_factory(stream, resource_options.get(stream, {}))(demux.streams[stream])
        for stream in streams
    )


def singer_stream_factory(
    stream: str, resource_options: t.Dict[str, t.Any]
) -> t.Callable[[Queue], t.Iterator[t.Any]]:
    """Factory for creating a dlt.resource function for each stream."""

    @dlt.resource(name=stream, **resource_options)
    def _singer_stream(_queue: Queue) -> t.Iterator[t.Any]:
        while True:
            item = _queue.get()
            if item is None:
                break
            yield item

    return _singer_stream
