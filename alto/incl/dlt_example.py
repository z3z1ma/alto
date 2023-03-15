import dlt  # type: ignore

from alto.dlt_singer import singer

if __name__ == "__main__":
    pipeline = dlt.pipeline(
        pipeline_name="carbon_intensity",
        destination="duckdb",
        dataset_name="raw",
    )
    streams = [
        "region",
        "entry",
        "generationmix",
    ]
    load_info = pipeline.run(
        singer(
            source="tap-carbon-intensity",
            streams=streams,
        ).with_resources(*streams)
    )
    print(load_info)
