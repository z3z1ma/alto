"""Example of a custom mapper.

This mapper adds a new field to the schema and populates it with a random value.
"""
import os

from alto.engine import AltoStreamMap


def register():
    return AddField


class AddField(AltoStreamMap):
    name: str = "Add Field Mapper"

    def transform_schema(self, schema: dict) -> dict:
        schema["schema"]["properties"]["new_field"] = {"type": "string"}
        return super().transform_schema(schema)

    def transform_record(self, record: dict) -> dict:
        record["record"]["new_field"] = os.urandom(8).hex()
        return super().transform_record(record)
