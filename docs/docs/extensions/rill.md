# Rill Developer

## What is Rill Developer?

Quoting from the [Rill Data](https://docs.rilldata.com) website:

Rill Developer makes it effortless to transform your datasets with SQL and create powerful, opinionated dashboards. Rill's principles:

- **feels good to use** – powered by Sveltekit & DuckDB = conversation-fast, not wait-ten-seconds-for-result-set fast
- **works with your local and remote datasets** – imports and exports Parquet and CSV (s3, gcs, https, local)
- **no more data analysis "side-quests"** – helps you build intuition about your dataset through automatic profiling
- **no "run query" button required** – responds to each keystroke by re-profiling the resulting dataset
- **radically simple dashboards** – thoughtful, opinionated defaults to help you quickly derive insights from your data
- **dashboards as code** – each step from data to dashboard has versioning, git sharing, and easy project rehydration

See their for installation instructions.

## Configuring Rill Developer in Alto

To enable the Rill Developer extension, you must add `rill` to the `extensions` key in your `alto` configuration file. Rill only has one configuration option, which is the `home` key. This is the path to the Rill project. The `RILL_HOME` environment variable will override this if set.

```toml title="alto.toml"
[default]
# Enable the evidence extension
extensions = ["rill"]

[default.utilities.rill]
# set the home directory for rill
home = "./exploration"
```

## Rill Source Files & Hooks (new)

One part of rill that beckoned improvement via alto something I've called `hooks`. Hooks are a way to, optionally, run commands on a source file before it is hydrated by rill. This is useful for things like running `bq extract` or a snowflake `export` statement since rill _can_ eagerly consume data from buckets but not from a database. Here is a typical source file:

```yaml title="sources/employees.yaml"
type: gcs
uri: gs://your-bucket/my-data/employees.parquet.gz
```

The problem with this is the **necessary step to update the parquet is now disconnected from the source definition**. The update could be a `dbt run-operation`, a custom python script, or even an `alto` command for alto-ception.

So lets add a `hook` to this source file to fix this:

```yaml title="sources/employees.yaml"
type: gcs
uri: gs://your-bucket/my-data/employees.parquet.gz
_hooks:
  - bq extract --destination_format=PARQUET --compression=GZIP --project_id=your-project-id your-dataset.employees gs://your-bucket/my-data/employees.parquet.gz
```

Now when you run `rill:start -h employees` or `rill:sync` alto will run the hook before the source is hydrated on rill server startup. This is a great way to keep your source definitions up to date and shareable. Please continue reading for more details on how to use hooks.

## Usage

### Available Commands

```
🚀 rill:initialize               Create a new, empty Rill project.
🚀 rill:start                    When you run rill start, it parses your project and ingests any missing data sources into a local DuckDB database. After your project has been re-hydrated, it starts the Rill web app on http://localhost:9009
🚀 rill:sync                     Run hooks for all sources containing a _hooks array.
```

### `rill:initialize`

Run the `rill:initialize` command to create a new Rill project. This will scaffold out a rill project containing a `rill.yaml` and 3 folders: `sources`, `models`, `dashboards`. The `sources` folder contains the data sources for your project as yaml. The `models` folder contains the SQL models for your project. The `dashboards` folder contains the dashboard definitions for your project as yaml.

### `rill:start`

Run the `rill:start` command to start the Rill web app. This will start the Rill web app on http://localhost:9009. You can then navigate to http://localhost:9009 to view your Rill project. This command takes an optional array of sources to execute hooks for. This is useful if you want to jump straight into exploring data that depends on a source that has a hook. The format looks like this:

```bash
alto rill:start -h source1 -h source2 -h source3
```

Where `source1`, `source2`, and `source3` correspond to `source1.yaml`, `source2.yaml`, and `source3.yaml` in the `sources` folder.

### `rill:sync`

Run the `rill:sync` command to run the hooks for all sources containing a `_hooks` array. This will run the hooks for **all** sources containing a `_hooks` array. This is useful if you want to run the hooks for all sources in your project.
