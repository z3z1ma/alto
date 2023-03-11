import dlt  # type: ignore

from alto.dlt_singer import singer

if __name__ == "__main__":
    pipeline = dlt.pipeline(
        pipeline_name="asana",
        destination="bigquery",
        dataset_name="raw_testing",
    )
    streams = ["users", "projects"]
    load_info = pipeline.run(
        singer(
            source="tap-asana",
            streams=streams,
            resource_options={
                "tasks": {"write_disposition": "replace"},
                "stories": {"write_disposition": "replace"},
            },
        ).with_resources(*streams)
    )
    print(load_info)
