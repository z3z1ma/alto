import os
import typing as t
from queue import Empty, Queue
from threading import Thread

import alto.constants
import alto.engine
from alto.utils import merge

try:
    import dlt
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
        super().__init__(daemon=True)
        self.tap = tap
        self.engine = engine
        self.streams: dict[str, Queue] = {stream: Queue() for stream in streams}
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
                if typ == "STATE":
                    stream = next(iter(self.streams.keys()))
                    self.streams[stream].put((typ, message["value"]))
                elif typ == "RECORD":
                    if maybe_stream is None:
                        raise RuntimeError("Singer RECORD message is missing a stream name.")
                    self.streams[maybe_stream].put((typ, message["record"]))
                elif typ == "SCHEMA":
                    pass
        # Put a None on each stream to signal the end of the stream
        for queue in self.streams.values():
            queue.put(None)
        self.graceful_exit = True


def singer(
    source: str,
    streams: t.Optional[t.List[str]] = None,
    env: t.Optional[str] = None,
    resource_options: t.Optional[t.Dict[str, t.Any]] = None,
    name: t.Optional[str] = None,
    **kwargs,
) -> t.Any:
    """Create a dlt source for a singer tap."""
    resolved_resource_options: dict[str, t.Any] = (
        {} if resource_options is None else resource_options
    )
    if env is None:
        env = os.getenv("ALTO_ENV", alto.constants.DEFAULT_ENVIRONMENT)

    @dlt.source(name=name or source, **kwargs)
    def _singer() -> t.Sequence[t.Any]:
        """Singer source function."""
        # Prepare engine and data structures
        engine, tap, catalog = _load_tap(source, env)
        # Use the streams from the catalog if not provided
        selected_streams = _selected_streams(catalog, streams)
        # Create the demuxer
        tap.select = selected_streams
        producer = SingerTapDemux(
            tap,
            engine,
            t.cast(t.Any, dlt).state().setdefault(tap.name, {}),
            *selected_streams,
        )
        producer.start()
        _set_resource_options(catalog, selected_streams, resolved_resource_options)
        # Create the dlt resources
        return _resources(selected_streams, resolved_resource_options, producer)

    return _singer()


def _load_tap(
    source: str, env: str
) -> t.Tuple[alto.engine.AltoTaskEngine, alto.engine.AltoPlugin, t.Any]:
    engine = alto.engine.get_engine(env)
    (tap,) = alto.engine.make_plugins(
        source,
        filesystem=engine.filesystem,
        configuration=engine.configuration,
    )
    return engine, tap, alto.engine.get_and_render_catalog(tap, engine.filesystem)


def _selected_streams(catalog: t.Any, streams: t.Optional[t.List[str]]) -> t.List[str]:
    baseline_streams = [stream.tap_stream_id for stream in catalog.streams]
    selected_streams = baseline_streams if streams is None else streams
    if not selected_streams:
        raise ValueError("No streams were found in the catalog or selected by the user.")
    missing = [stream for stream in selected_streams if stream not in baseline_streams]
    if missing:
        raise ValueError(
            f"Stream '{missing[0]}' was not found in the catalog. "
            f"Available streams: {baseline_streams}"
        )
    return selected_streams


def _set_resource_options(
    catalog: t.Any, selected_streams: t.List[str], resource_options: t.Dict[str, t.Any]
) -> None:
    entries = {entry.tap_stream_id: entry for entry in catalog.streams}
    for stream in selected_streams:
        opts: dict = resource_options.setdefault(stream, {})
        entry = entries.get(stream)
        if entry is None:
            continue
        method = entry.forced_replication_method or entry.replication_method
        if method == "FULL_TABLE":
            opts.setdefault("write_disposition", "replace")
        elif method == "INCREMENTAL":
            opts.setdefault("write_disposition", "append")


def _resources(
    selected_streams: t.List[str],
    resource_options: t.Dict[str, t.Any],
    producer: SingerTapDemux,
) -> t.Tuple[t.Any, ...]:
    return tuple(
        singer_stream_factory(stream, resource_options[stream])(producer.streams[stream], producer)
        for stream in selected_streams
    )


def singer_stream_factory(
    stream: str, resource_options: t.Dict[str, t.Any]
) -> t.Callable[[Queue, SingerTapDemux], t.Iterator[t.Any]]:
    """Factory for creating a dlt.resource function for each stream."""

    @dlt.resource(name=stream, **resource_options)
    def _singer_stream(_queue: Queue, producer: SingerTapDemux) -> t.Iterator[t.Any]:
        state_dict = t.cast(t.Any, dlt).state().setdefault(producer.tap.name, {})
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
