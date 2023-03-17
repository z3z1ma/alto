import os
import time
import typing as t
from queue import Empty, Queue
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
    each stream to be processed in parallel and dlt to manage each as a separate resource.
    """

    daemon = True

    def __init__(
        self, tap: alto.engine.AltoPlugin, engine: alto.engine.AltoTaskEngine, *streams: t.List[str]
    ) -> None:
        """Initialize the demuxer."""
        super().__init__(daemon=True)
        self.tap = tap
        self.engine = engine
        self.streams = {stream: Queue() for stream in streams}
        # Lifecycle flags
        self.setup_complete = False
        self.graceful_exit = False

    def run(self) -> None:
        """Run the demuxer thread."""
        t = self.tap
        e = self.engine
        with alto.engine.tap_runner(
            t,
            e.filesystem,
            e.alto,
            max_wait=int(os.getenv("ALTO_MAX_WAIT", 60)),
            state_key=f"{t.name}-{e.alto.current_env}",
            records_only=True,
            state_dict=dlt.state().setdefault(f"{t.name}-{e.alto.current_env}", {}),
        ) as tap_stream:
            self.setup_complete = True
            for payload in tap_stream:
                if payload is None:
                    continue
                stream, record = payload
                self.streams[stream].put(record)
        # Put a None on each stream to signal the end of the stream
        for stream in self.streams.values():
            stream.put(None)
        self.graceful_exit = True


@dlt.source
def singer(
    source: str,
    streams: t.Optional[t.List[str]] = None,
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
    # Prepare engine and data structures
    engine = alto.engine.get_engine(env)
    (tap,) = alto.engine.make_plugins(
        source,
        filesystem=engine.filesystem,
        configuration=engine.configuration,
    )
    catalog = alto.engine.get_and_render_catalog(tap, engine.filesystem)
    # Use the streams from the catalog if not provided
    baseline_streams = [stream.tap_stream_id for stream in catalog.streams]
    if streams is None:
        streams = baseline_streams
    if not streams:
        raise ValueError("No streams were found in the catalog or selected by the user.")
    for stream in streams:
        if stream not in baseline_streams:
            raise ValueError(
                f"Stream '{stream}' was not found in the catalog. "
                f"Available streams: {baseline_streams}"
            )
    # TODO: use the catalog to determine some resource props?
    # otherwise its pure append streams...
    # Create the demuxer
    tap.select = streams
    producer = SingerTapDemux(tap, engine, *streams)
    producer.start()
    # Wait for the producer to start
    start_time = time.time()
    while not producer.is_alive() or not producer.setup_complete:
        time.sleep(0.1)
        if time.time() - start_time > 180.0:
            # Timeout after 180 seconds, this is arbitrary but we are
            # trying to account for build time of a non-cached plugin.
            raise RuntimeError("Singer tap failed to start, aborting.")
    # Create the dlt resources
    return tuple(
        singer_stream_factory(stream, resource_options.get(stream, {}))(
            producer.streams[stream], producer
        )
        for stream in streams
    )


def singer_stream_factory(
    stream: str, resource_options: t.Dict[str, t.Any]
) -> t.Callable[[Queue], t.Iterator[t.Any]]:
    """Factory for creating a dlt.resource function for each stream."""

    @dlt.resource(name=stream, **resource_options)
    def _singer_stream(_queue: Queue, producer: SingerTapDemux) -> t.Iterator[t.Any]:
        poll_interval = 1
        while producer.is_alive() or not _queue.empty():
            try:
                item = _queue.get(timeout=poll_interval)
            except Empty:
                continue
            else:
                if item is None:
                    _queue.task_done()
                    break  # End of stream
                yield item
                _queue.task_done()
        if not producer.graceful_exit:
            raise RuntimeError("Singer tap exited unexpectedly.")

    return _singer_stream
