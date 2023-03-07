"""Example of a custom mapper.

This mapper stamps the current date and time to the record.
"""
from datetime import datetime

from alto.engine import AltoStreamMap


def register():
    return DateStampMapper


class DateStampMapper(AltoStreamMap):
    name: str = "Date Stamp Mapper"

    def transform_schema(self, schema: dict) -> dict:
        schema["schema"]["properties"]["_alto_extracted_at"] = {
            "type": "string",
            "format": "date-time",
        }
        return super().transform_schema(schema)

    def transform_record(self, record: dict) -> dict:
        record["record"]["_alto_extracted_at"] = datetime.now().isoformat(
            sep="T", timespec="seconds"
        )
        return super().transform_record(record)
