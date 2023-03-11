import dlt  # type: ignore

from alto.dlt_singer import singer

if __name__ == "__main__":
    pipeline = dlt.pipeline(
        pipeline_name="bls",
        destination="bigquery",
        dataset_name="raw_testing_bls",
    )
    streams = [
        "JTU000000000000000JOR",
        "JTU000000000000000TSL",
    ]
    load_info = pipeline.run(
        singer(
            source="tap-bls",
            streams=streams,
        ).with_resources(*streams)
    )
    print(load_info)
