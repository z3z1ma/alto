"""Focused unit tests for core helpers."""

import copy
import io
import json
import runpy
import tempfile
import typing as t
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import alto.config
import alto.engine as engine
import alto.tools as tools
from alto.catalog import CatalogMutationStrategy, apply_metadata, apply_selected
from alto.main import AltoInit, _get_root_scrub_args, _padded_rows, _task_icon
from alto.models import SingerCatalog
from alto.providers.serde import SerdeFormat, deserialize, serialize
from alto.repl import AltoCmd
from alto.state import parse_state_from_stdout
from alto.state import ensure_state, update_state
from alto.ui import AltoRichUI, _task_output_visibility
from alto.utils import merge, message_type


def _catalog_data():
    return {
        "streams": [
            {
                "tap_stream_id": "users",
                "schema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "email": {"type": "string"},
                        "name": {"type": "string"},
                    },
                },
                "metadata": [
                    {"breadcrumb": [], "metadata": {"inclusion": "available"}},
                    {"breadcrumb": ["properties", "id"], "metadata": {}},
                    {"breadcrumb": ["properties", "email"], "metadata": {}},
                    {"breadcrumb": ["properties", "name"], "metadata": {}},
                ],
                "key_properties": [],
                "replication_method": "FULL_TABLE",
            },
            {
                "tap_stream_id": "orders",
                "schema": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "metadata": [{"breadcrumb": [], "metadata": {"inclusion": "available"}}],
                "key_properties": [],
                "replication_method": "FULL_TABLE",
            },
        ]
    }


class TestCatalogHelpers(unittest.TestCase):
    def test_apply_selected_prunes_streams_and_attributes(self):
        catalog = apply_selected(
            copy.deepcopy(_catalog_data()),
            ["users.*", "!users.email"],
            write=False,
        )

        self.assertEqual([stream.tap_stream_id for stream in catalog.streams], ["users"])
        self.assertNotIn("email", catalog["users"].schema["properties"])
        self.assertTrue(catalog["users"].selected)

    def test_apply_selected_can_deselect_without_pruning(self):
        catalog = apply_selected(
            copy.deepcopy(_catalog_data()),
            ["users.*", "!users.email"],
            write=False,
            strategy=CatalogMutationStrategy.DESELECT,
        )

        self.assertEqual([stream.tap_stream_id for stream in catalog.streams], ["users", "orders"])
        self.assertIn("email", catalog["users"].schema["properties"])
        self.assertFalse(catalog["orders"].selected)

    def test_apply_metadata_updates_root_and_stream_fields(self):
        catalog = apply_metadata(
            SingerCatalog.parse_json(copy.deepcopy(_catalog_data())),
            {"users": {"replication-method": "INCREMENTAL", "replication-key": "id"}},
            write=False,
        )

        stream = catalog["users"]
        self.assertEqual(stream.replication_method, "INCREMENTAL")
        self.assertEqual(stream.replication_key, "id")
        root_metadata = stream.root_metadata()
        assert root_metadata is not None
        metadata = t.cast(dict[str, t.Any], root_metadata.metadata)
        self.assertEqual(metadata["replication-method"], "INCREMENTAL")

    def test_catalog_write_back_to_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = Path(tmp) / "catalog.json"
            catalog_path.write_text(json.dumps(_catalog_data()))

            apply_selected(catalog_path, ["users.*", "!users.email"])
            written = json.loads(catalog_path.read_text())

        self.assertEqual([stream["tap_stream_id"] for stream in written["streams"]], ["users"])
        self.assertNotIn("email", written["streams"][0]["schema"]["properties"])


class TestSerializationStateAndUtils(unittest.TestCase):
    def test_json_serde_round_trip_to_string_and_stream(self):
        payload = {"alpha": [1, 2], "enabled": True}
        encoded = serialize(SerdeFormat.JSON, payload)
        assert encoded is not None

        self.assertEqual(deserialize(SerdeFormat.JSON, encoded), payload)

        stream = io.StringIO()
        self.assertIsNone(serialize(SerdeFormat.JSON, payload, stream))
        stream.seek(0)
        self.assertEqual(json.load(stream), payload)

    def test_json_serde_round_trip_to_file(self):
        payload = {"alpha": 1}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            self.assertIsNone(serialize(SerdeFormat.JSON, payload, str(path)))
            self.assertEqual(deserialize(SerdeFormat.JSON, "", str(path)), payload)

    def test_parse_state_from_text_and_binary_streams(self):
        text_state = io.StringIO('{"a": 1}\nnot-json\n{"nested": {"b": 2}}\n')
        binary_state = io.BytesIO(b'{"a": 1}\n{"nested": {"c": 3}}\n')

        self.assertEqual(parse_state_from_stdout(text_state), {"a": 1, "nested": {"b": 2}})
        self.assertEqual(parse_state_from_stdout(binary_state), {"a": 1, "nested": {"c": 3}})

    def test_ensure_and_update_state_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            stdout_path = Path(tmp) / "stdout.log"
            state_path.write_text(json.dumps({"singer_state": {"a": 1}}))
            stdout_path.write_text('{"b": 2}\nnot-json\n')

            ensure_state(state_path)
            updated = update_state(state_path, stdout_path)

        self.assertEqual(updated, {"a": 1, "b": 2})

    def test_merge_and_message_type(self):
        target = {"outer": {"a": 1}, "keep": True}
        merge({"outer": {"b": 2}}, target)

        self.assertEqual(target, {"outer": {"a": 1, "b": 2}, "keep": True})
        self.assertEqual(message_type(b'{"type": "RECORD"}'), 1)
        self.assertEqual(message_type(b'{"type":"SCHEMA"}'), 2)
        self.assertEqual(message_type(b'{"type": "STATE"}'), 3)
        self.assertEqual(message_type(b'{"type":"NOPE"}'), 0)
        self.assertEqual(message_type(b"not-json"), -1)


class TestCliAndEngineHelpers(unittest.TestCase):
    def test_padded_rows_aligns_columns(self):
        rows = _padded_rows([["A", "Name"], ["x", "longer"]], [1, 6])

        self.assertEqual(rows, ["A  Name    ", "x  longer  "])

    def test_task_icon_uses_prefixes_and_pipeline_doc(self):
        task = type("Task", (), {"name": "tap-demo", "doc": ""})()
        pipeline = type("Task", (), {"name": "custom", "doc": "Run a data pipeline"})()

        self.assertEqual(_task_icon(task), "🔌 ")
        self.assertEqual(_task_icon(pipeline), "🔌 ")

    def test_root_scrub_args_uses_root_and_removes_args(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = ["--root", tmp, "list"]

            self.assertEqual(_get_root_scrub_args(args), Path(tmp))

        self.assertEqual(args, ["list"])

    def test_root_scrub_args_exits_for_missing_root_value(self):
        with self.assertRaises(SystemExit):
            _get_root_scrub_args(["--root"])

    def test_init_project_options_cover_prompt_paths(self):
        init = AltoInit()
        self.assertEqual(
            init._project_options({"no-prompt": True}, "alto.{ext}", "alto.local.{ext}"),
            ("toml", "default", None),
        )

        with patch("builtins.input", return_value="xml"):
            self.assertEqual(
                init._project_options({"no-prompt": False}, "alto.{ext}", "alto.local.{ext}"),
                ("xml", "default", 1),
            )

        with patch("builtins.input", side_effect=["toml", "demo", "n"]):
            self.assertEqual(
                init._project_options({"no-prompt": False}, "alto.{ext}", "alto.local.{ext}"),
                ("toml", "demo", 0),
            )

        with patch("builtins.input", side_effect=["toml", "demo", "y"]):
            self.assertEqual(
                init._project_options({"no-prompt": False}, "alto.{ext}", "alto.local.{ext}"),
                ("toml", "demo", None),
            )

    def test_init_helpers_detect_existing_config_and_write_support_files(self):
        original_working_directory = alto.config.working_directory
        try:
            with tempfile.TemporaryDirectory() as tmp:
                alto.config.working_directory = Path(tmp)
                init = AltoInit()
                self.assertFalse(init._config_exists("alto.{ext}"))

                (Path(tmp) / "alto.toml").write_text("")
                self.assertTrue(init._config_exists("alto.{ext}"))

                init._write_env_file()
                init._write_gitignore()
                init._write_example_assets()

                self.assertEqual((Path(tmp) / ".env").read_text(), "MY_SECRET=1\n")
                self.assertIn("alto.local.*", (Path(tmp) / ".gitignore").read_text())
                self.assertTrue((Path(tmp) / "series.json").is_file())
                self.assertTrue((Path(tmp) / "carbon_pipeline_dlt.py").is_file())
        finally:
            alto.config.working_directory = original_working_directory

    def test_rich_ui_task_output_helpers(self):
        task = SimpleNamespace(
            executed=True,
            verbosity=0,
            name="demo",
            actions=[
                SimpleNamespace(err="bad", out="good"),
                SimpleNamespace(err="", out=""),
            ],
        )
        ui = object.__new__(AltoRichUI)
        ui.failure_verbosity = 2
        output: list[tuple[str, t.Any]] = []
        ui.write = lambda text: output.append(("write", text))
        ui.write_stderr = lambda text: output.append(("stderr", text))
        ui.write_stdout = lambda text: output.append(("stdout", text))
        ui._write_failure = lambda result, write_exception=True: output.append(
            ("failure", write_exception)
        )

        self.assertEqual(_task_output_visibility(t.cast(t.Any, task), 2), (True, True))
        AltoRichUI._write_task_output(ui, {"task": task})

        self.assertIn(("failure", 2), output)
        self.assertIn(("stderr", "demo <stderr>:\nbad\n"), output)
        self.assertIn(("stdout", "demo <stdout>:\ngood\n"), output)

    def test_tools_re_exports_doit_helpers(self):
        self.assertIn("CmdAction", tools.__all__)
        self.assertTrue(hasattr(tools, "run_once"))

    def test_module_entrypoint_exits_with_main_status(self):
        with patch("alto.main.main", return_value=7), self.assertRaises(SystemExit) as ctx:
            runpy.run_module("alto.__main__", run_name="__main__")

        self.assertEqual(ctx.exception.code, 7)

    def test_repl_ls_and_completion_use_filesystem(self):
        class FakeFs:
            def ls(self, path, **_kwargs):
                return ["dir/file"]

            def glob(self, path, **_kwargs):
                return ["globbed/file"]

            def info(self, fname):
                return {"type": "file", "size": 4, "name": fname}

            def isdir(self, path):
                return path in {"dir", "folder"}

            def isfile(self, path):
                return path == "file"

        repl = AltoCmd(SimpleNamespace(fs=FakeFs(), filesystem=SimpleNamespace()))
        with patch("builtins.print") as mocked_print:
            repl.do_ls("--all *")

        mocked_print.assert_called()
        self.assertEqual(repl.complete_ls("fol", "ls folder", 0, 0), ["fol/"])
        self.assertEqual(repl.complete_ls("", "ls file", 0, 0), [])

    def test_engine_reservoir_and_mapper_helpers(self):
        reservoir: engine.ReservoirIndex = {"__version__": 2}
        self.assertEqual(engine._version_from_reservoir(reservoir), 2)
        engine._reservoir_stream_paths(reservoir, "users").append("path")
        self.assertEqual(reservoir["users"], ["path"])

        class Mapper(engine.AltoStreamMap):
            def transform_record(self, record):
                record["mapped"] = True
                return record

            def transform_schema(self, schema):
                schema["schema_mapped"] = True
                return schema

        mapper = Mapper(t.cast(t.Any, {}), ["*"])
        mapped = engine._mapped_singer_message({"type": "RECORD"}, [mapper])
        assert mapped is not None
        self.assertEqual(
            mapped["mapped"],
            True,
        )
        self.assertIsNone(engine._mapped_singer_message({"type": "STATE"}, [mapper]))


if __name__ == "__main__":
    unittest.main()
