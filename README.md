# 👩‍🎤 Alto

[![PyPI](https://img.shields.io/pypi/v/singer-alto)][pypi_]
[![Status](https://img.shields.io/pypi/status/singer-alto.svg)][status]
[![Python Version](https://img.shields.io/pypi/pyversions/singer-alto)][python version]
[![License](https://img.shields.io/pypi/l/singer-alto)][license]

[![Tests](https://github.com/z3z1ma/alto/workflows/Alto%20Tests/badge.svg)][tests]
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)][pre-commit]
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)][black]

[pypi_]: https://pypi.org/project/singer-alto/
[status]: https://pypi.org/project/singer-alto/
[python version]: https://pypi.org/project/singer-alto
[tests]: https://github.com/z3z1ma/alto/actions?workflow=Alto%20Tests
[pre-commit]: https://github.com/pre-commit/pre-commit
[black]: https://github.com/psf/black

## Documentation

Jump into the [docs](https://z3z1ma.github.io/alto/) hosted on GitHub Pages to get started!

[![Documentation](https://github.com/z3z1ma/alto/actions/workflows/pages/pages-build-deployment/badge.svg)](https://z3z1ma.github.io/alto/)

✨ We have a lightweight, searchable **[tap](https://z3z1ma.github.io/alto/docs/integrations/taps)** index and **[target](https://z3z1ma.github.io/alto/docs/integrations/targets)** index embedded in the docs if you want to peruse the available integrations too! All links there forward to the integration documentation on Meltano Hub. ⏩

## Introduction

👋 Alto is a versatile data integration tool that allows you to easily run [Singer](https://www.singer.io/) plugins, build and cache [PEX](https://github.com/pantsbuild/pex) files encapsulating those plugins, and create a data reservoir 💧 whereby you can extract once and replay to as many destinations as you want as many times as you want. With Alto, you can seamlessly connect to various data sources, store your data in a centralized reservoir (singerlake), and manage lean, efficient extract load flows. Throw it into a `dbt` project, a data science project, or a passion project without fear of conflicting dependencies and watch it *just work*. The alto config file can sit right next to your dbt project yaml with no other changes to your repo beyond adding `singer-alto` to your requirements and you can be running data pipelines, today! 🎯

Like [Meltano](https://github.com/meltano/meltano), Alto is driven **entirely by configuration** and the config structure drew much of its inspiration from Meltano. Alto supports YAML, TOML, and JSON leveraging [Dynaconf](https://github.com/dynaconf/dynaconf) for robust features. Because of the similarities to Meltano, using one or the other is a fairly straightforward process!

### Installation

I highly recommend going to the [docs](https://z3z1ma.github.io/alto/) to get up to speed. The docs are a work in progress but they are the best place to get started. If you are familiar with Meltano, you will feel right at home.

```bash
pip install singer-alto
```

___

## Example Configuration

The following is an example configuration file for Alto. It is a TOML file but you can use YAML or JSON as well. Alto will automatically detect the file type and load the configuration accordingly. I recommend using TOML for the most concise yet readable config file. I also recommend reading the [docs](https://z3z1ma.github.io/alto/) to get a better understanding of the config file structure.

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

Given the above configuration, you can run the following command to extract data from the BLS and Carbon Intensity APIs and load it into JSONL files.

```bash
alto carbon-data:jsonl
alto labor-data:jsonl
```

Or send them to the project reservoir.

```bash
alto carbon-data:reservoir
alto labor-data:reservoir
```

And from the reservoir, you can replay to any number of targets.

```bash
alto reservoir:carbon-data-jsonl
alto reservoir:carbon-data-snowflake  # here as example, not in config
alto reservoir:carbon-data-parquet    # here as example, not in config
```

Lastly, you can invoke the utility defined above (you can invoke any plaugin this way).

```bash
alto invoke dlt --help  # invoke an executable

alto invoke python dlt  # drop into a python shell with dlt installed
alto invoke python dlt ./path/to/pipeline.py  # run a python script
```

## Comparison

> How is this different than what exists today; namely Meltano? Outside of some of what we covered above.

### Differences

I would recommend `alto` if you want something lighter than Meltano. If you have a Python project where EL is one of many existing concerns and you want a dependency you can add that is lean, highly functional, and can stand alongside other dependencies without concern of conflict, I would recommend `alto`. I would recommend `alto` if you want a light snappy CLI with emphasis on less-is-more. I would recommend `alto` if you want to use Singer taps and targets but don't want to deal with the Meltano system db, migrations, or system directory. I would recommend `alto` if you want a codebase small enough to quickly iterate on or play with. I would recommend `meltano` if you want a tool that has a large community, more exposure, and features. I would recommend `alto` if those extra features are not necessary for your use case or your just looking to explore whats out there.

Alto is able to run taps -> targets with centralized environment-aware configuration, secret management, automatically managed state, automatic discovery, catalog caching to a remote backend, catalog manipulation via `select` & `metadata` keys, and many of the things users love about Meltano. Given this, in most situations -- from a pure EL perspective, it stacks up well with Meltano since, given all else aside, it is the plugins that do much of the work once the state, configuration, and catalog are managed.

There are some compelling features in `alto` in general around how it manages plugins as cached PEX files, the built in reservoir as an available-by-default source & destination, and its _light_ footprint. Continuing to use Meltano as the baseline of comparison (since it was the inspiration!), here are some noteworthy differences:

- The CLI is extremely fast due to the lightness of the package.

- There is no system db so no database migrations or system directory to care about.

- Significantly smaller dependency footprint by an **order of magnitude**. Alto only has 4 direct dependencies with no C or rust extensions in the dependency tree, it is pure python. The below comparison includes transitives:
    - **Meltano**: >100
    - **Alto**: 7

- Because of its dependency footprint, it can be installed in very tiny Docker containers and wheels are cross platform compatible, naturally. It installs extremely quickly.

- We use `PEX` (PythonEXecutable) for all plugins instead of loose venvs making plugins single files that are straightforward to cache.

- We use a (simple) caching algorithm that makes the plugins re-usable across machines when combined with a remote filesystem and re-usable on the same system in general. This means, most of the time, you will build a PEX artifact once and **never** build it again. This makes an already lightweight `alto` even more portable. The benefits are applicable for your whole team.

- Docker containers do not require you to "install" the plugins during the build process since the plugins are instantly pulled from a remote cache. This can **significantly** reduce image size if you are working with enough plugins.

- Because of how plugins are handled it can be ran in `lambda` and serverless functions very easily. The time to spin up a pipeline is extremely quick.

- We use `fsspec` to provide that filesystem abstraction layer that provides the exact same experience locally on a single machine as when plugged into a remote fsspec filesystem such as [s3](https://github.com/fsspec/s3fs), [gcs](https://github.com/fsspec/gcsfs), or [azure](https://github.com/fsspec/adlfs). We do not pin these remote backend dependencies, even as extras, but give the user the flexibility to include how they see fit.

- An order of magnitude (`>85%`) less code which makes iteration/maintenance, extending, or forking easier (in theory) due to less accumulated tech debt though the flip side is less robustness

- Because it is scaffolded over a build system, never worry about running `install` again, run pipelines immediately and alto works out the rest.

- We use `Dynaconf` to manage configuration
    - This gives us uniform support for json, toml, and yaml out of the box
    - We get environment management
    - We get configuration inheritance / deep merging
    - We get `.env` support
    - We get unique ways to render vars with `@format ` tokens
    - We get hashicorp vault support

- Encourages use of `bash` instead of `meltano run` commands. Bash is _already_ a fantastic glue code where you can run multiple extract load blocks, background them via `&` to parallelize loads, run utilities the way they have always been ran since everything is not wrapped in a venv with env vars injected by Meltano which is both a convenience and a constraint. `meltano run tap1 target1 tap2 target2` is ~ functionally identical to `alto tap1:target1 && alto tap2:target2`.

- Straightforward to take advantage of the Python API exposed by `alto` to build your own custom pipelines.

- A smaller codebase affords agility and flexibility. It has let us prove out integration with [dlt](https://dlthub.com/docs/intro) which is exciting!

## Closing Remarks

Remember, everything in software is a tradeoff. I offer `alto` as another tool in the ecosystem which gets the job done in a radically different way. I hope you find it useful and if you do, please consider contributing to the project or having the interesting discussions about what the ideal is. I am also happy to help with any questions you may have about the project.

Hats off to Meltano 🎉 for being a great inspiration and for being a great tool that helped to shape the ideal of what I wanted to build. I hope you find this interesting and divergent enough to warrant a look.

[license]: https://github.com/z3z1ma/alto/blob/main/LICENSE
