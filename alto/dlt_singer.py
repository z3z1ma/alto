import os
import typing as t
from queue import Empty, Queue
from threading import Thread

import alto.constants
import alto.engine
from alto.utils import merge

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
        self,
        tap: alto.engine.AltoPlugin,
        engine: alto.engine.AltoTaskEngine,
        init_state: dict,
        *streams: str,
    ) -> None:
        """Initialize the demuxer."""
        super().__init__(daemon=True)
        self.tap = tap
        self.engine = engine
        self.streams = {stream: Queue() for stream in streams}
        self.init_state = init_state
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
            state_key=f"{t.name}-dlt",
            state_dict=self.init_state,
        ) as tap_stream:
            self.setup_complete = True
            for payload in tap_stream:
                if payload is None:
                    continue
                typ, maybe_stream, message = payload
                stream: str
                if typ == "STATE":
                    stream = next(iter(self.streams.keys()))
                    self.streams[stream].put((typ, message["value"]))
                elif typ == "RECORD":
                    stream = maybe_stream
                    self.streams[stream].put((typ, message["record"]))
                elif typ == "SCHEMA":
                    pass
        # Put a None on each stream to signal the end of the stream
        for queue in self.streams.values():
            queue.put(None)
        self.graceful_exit = True


def singer(name: str, **kwargs) -> t.Callable[..., t.Sequence[t.Any]]:
    """Factory for creating a dlt.source function for a singer tap."""

    @dlt.source(name=name, **kwargs)
    def _singer(
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
        # Create the demuxer
        tap.select = streams
        producer = SingerTapDemux(tap, engine, dlt.state().setdefault(tap.name, {}), *streams)
        producer.start()
        # Use the catalog to determine some resource props
        for stream in streams:
            opts: dict = resource_options.setdefault(stream, {})
            for entry in catalog.streams:
                if entry.tap_stream_id == stream:
                    this = entry
                    break
            else:
                continue
            method = this.forced_replication_method or this.replication_method
            if method == "FULL_TABLE":
                opts.setdefault("write_disposition", "replace")
            elif method == "INCREMENTAL":
                opts.setdefault("write_disposition", "append")
        # Create the dlt resources
        return tuple(
            singer_stream_factory(stream, resource_options[stream])(
                producer.streams[stream], producer
            )
            for stream in streams
        )

    return _singer


def singer_stream_factory(
    stream: str, resource_options: t.Dict[str, t.Any]
) -> t.Callable[[Queue], t.Iterator[t.Any]]:
    """Factory for creating a dlt.resource function for each stream."""

    @dlt.resource(name=stream, **resource_options)
    def _singer_stream(_queue: Queue, producer: SingerTapDemux) -> t.Iterator[t.Any]:
        state_dict = dlt.state().setdefault(producer.tap.name, {})
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
                typ, message = item
                if typ == "STATE":
                    merge(message, state_dict)
                elif typ == "RECORD":
                    yield message
                _queue.task_done()
        if not producer.graceful_exit:
            raise RuntimeError("Singer tap exited unexpectedly.")

    return _singer_stream
