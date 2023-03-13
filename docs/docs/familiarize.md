# Alto Next Steps

The quickstart guide is a great way to get to quickly get to the **a-ha moment** of Alto. However, it is helpful to move beyond the quickstart and see a more contrived example of what a _real_ project might look like. This will expose you to some more of the possibilities of Alto. While the rest of the learning content will have `toml`, `yaml`, and `json` examples, we will use `toml` in this brief exposure to a more refined project. Exposure is the key here, so don't worry about understanding everything right away. We will cover the details in the next section.

## Configuration

What you will notice right away is that the configuration can be very **concise**. These are the same 3 plugins that `alto init` generates, but with more liberties taken to show off the flexibility of the configuration and most comments removed.

```toml title="alto.toml"
[default]
project_name = "{project}"
load_path = "raw"
extensions = ["evidence"]
environment.STARTER_PROJECT = 1
# https://github.com/dlt-hub/dlt
utilities.dlt.pip_url = "python-dlt[duckdb]>=0.2.0a25"
utilities.dlt.environment.PEX_INHERIT_PATH = "fallback"

[default.taps]
# https://gitlab.com/meltano/tap-carbon-intensity
carbon-data.pip_url = "git+https://gitlab.com/meltano/tap-carbon-intensity.git#egg=tap_carbon_intensity"
carbon-data.executable = "tap-carbon-intensity"
carbon-data.load_path = "carbon_intensity"
carbon-data.capabilities = ["state", "catalog"]
carbon-data.select = ["*.*", "~*.dnoregion"]

# https://hub.meltano.com/extractors/tap-bls
labor-data.pip_url = "git+https://github.com/frasermarlow/tap-bls#egg=tap_bls"
labor-data.executable = "tap-bls"
labor-data.capabilities = ["state", "catalog"]
labor-data.load_path = "bls"
labor-data.select = ["JTU000000000000000JOR", "JTU000000000000000JOL"]
labor-data.config.startyear = "2019"
labor-data.config.endyear = "2020"
labor-data.config.calculations = "true"
labor-data.config.annualaverage = "false"
labor-data.config.aspects = "false"
labor-data.config.disable_collection = "true"
labor-data.config.update_state = "false"
labor-data.config.series_list_file_location = "./series.json"

[default.targets]
# https://hub.meltano.com/loaders/target-singer-jsonl
jsonl.pip_url = "target-jsonl==0.1.4"
jsonl.executable = "target-jsonl"
jsonl.config.destination_path = "@format output/{this.load_path}"

[github_actions]
load_path = "cicd"
targets.jsonl.config.destination_path = "@format /github/workspace/output/{this.load_path}"
```

## Listing the available commands

You will notice here that, because `alto` is entirely driven by configuration, the commands listed here take advantage of the names we have given to the plugins. This is an extremely easy way of **adding context to your CLI experience**.

```
(env) vscode ➜ /workspaces/alto/example_1 (main) $ alto list --all
📦 Alto version: 0.2.10
🏗  Working directory: .
🌎 Environment: DEVELOPMENT

👷 build                         [core] Generate pex plugin based on the alto config.
👷 build:carbon-data             Build the carbon-data plugin
👷 build:labor-data              Build the labor-data plugin
👷 build:jsonl                   Build the jsonl plugin
👷 build:dlt                     Build the dlt plugin
🛠  config                        [core] Generate configuration files on disk.
🛠  config:carbon-data            Render configuration for the carbon-data plugin
🛠  config:labor-data             Render configuration for the labor-data plugin
🛠  config:jsonl                  Render configuration for the jsonl plugin
🛠  config:jsonl--carbon-data     Render configuration for the jsonl plugin with carbon-data as source
🛠  config:jsonl--labor-data      Render configuration for the jsonl plugin with labor-data as source
📖 catalog                       [singer] Generate base catalog file for a Singer tap.
📖 catalog:carbon-data           Generate base catalog for carbon-data
📖 catalog:labor-data            Generate base catalog for labor-data
📦 apply                         [singer] Apply user config to base catalog file.
📦 apply:carbon-data             Render runtime catalog for carbon-data
📦 apply:labor-data              Render runtime catalog for labor-data
🔌 carbon-data                   [singer] Execute a data pipeline.
🔌 carbon-data:jsonl             Run the carbon-data to jsonl data pipeline
🔌 labor-data                    [singer] Execute a data pipeline.
🔌 labor-data:jsonl              Run the labor-data to jsonl data pipeline
💧 reservoir                     [singer] Execute a data pipeline.
💧 reservoir:carbon-data-jsonl   Run the carbon-data to jsonl data pipeline from the reservoir to the target
💧 reservoir:labor-data-jsonl    Run the labor-data to jsonl data pipeline from the reservoir to the target
🔌 carbon-data:reservoir         Run the carbon-data to reservoir data pipeline to the reservoir from the tap
🔌 labor-data:reservoir          Run the labor-data to reservoir data pipeline to the reservoir from the tap
🧪 test                          [singer] Run tests for taps.
🧪 test:carbon-data              Test the carbon-data plugin
🧪 test:labor-data               Test the labor-data plugin
💁 about                         [singer] Run the about command for a Singer tap.
🚀 evidence                      [extension] Evidence.dev extension.
🚀 evidence:initialize           Generate Evidence project from template.
🚀 evidence:build                Build the Evidence dev reports.
🚀 evidence:dev                  Run the Evidence dev server.
```

## Running the pipelines

### Tap to Target

Given the above configuration, you can run the following command to **extract** data from the BLS (Bereau of Labor and Statistics) and Carbon Intensity APIs and **load** it into JSONL files.

```bash
alto carbon-data:jsonl
alto labor-data:jsonl
```

### Tap to Reservoir

Alternatively, you can run the following command to **extract** data from the BLS (Bereau of Labor and Statistics) and Carbon Intensity APIs and load it into the project **reservoir**.

```bash
alto carbon-data:reservoir
alto labor-data:reservoir
```

### Reservoir to Target

From the reservoir, you can replay the data extract (since it is still in Singer format and partitioned for parallelization) into **any** number of targets **any** number of times.

```bash
alto reservoir:carbon-data-jsonl
alto reservoir:carbon-data-snowflake  # here as example, not in config
alto reservoir:carbon-data-parquet    # here as example, not in config
```

### Invoking utilities

Lastly, you can **invoke** the utility, [dlt](https://github.com/dlt-hub/dlt), defined above (you can actually invoke any plugin this way).

```bash
alto invoke dlt --help  # invoke the executable directly

alto invoke python dlt  # drop into a python shell with dlt installed
alto invoke python dlt ./path/to/pipeline.py  # run a python script
```
