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

👋 Alto is a versatile data integration tool that allows you to easily run [Singer](https://www.singer.io/) plugins, build and cache [PEX](https://github.com/pantsbuild/pex) files encapsulating those plugins, and create a data reservoir whereby you can extract once and replay to as many destinations as you want as many times as you want. With Alto, you can seamlessly connect to various data sources, store your data in a centralized reservoir (singerlake), and manage lean, efficient extract load flows. Throw it into a `dbt` project, a data science project, or a passion project without fear of conflicting dependencies and watch it *just work*. The alto config file can sit right next to your dbt project yaml with no other changes to your repo beyond adding `singer-alto` to your requirements and you can be running data pipelines, today!

Like [Meltano](https://github.com/meltano/meltano), Alto is driven **entirely by configuration** and the config structure drew much of its inspiration from Meltano. Alto supports YAML, TOML, and JSON leveraging [Dynaconf](https://github.com/dynaconf/dynaconf) for robust features. Because of the similarities to Meltano, using one or the other is a fairly straightforward process -- even if only to give Alto a whirl.

**Install:**
```bash
pipx install singer-alto  # install system wide
pip install singer-alto   # or add it to your project!
```

**Small Example Config (see the bottom of the readme for the same thing as TOML):**

> Also see the massive [alto.example.yaml](./alto.example.yaml) in this repo based on a real-world project.

```yaml
# this key corresponds to the environment, default is a special key which applies to all environments.
# name your environments whatever you want by having more keys
default:
  # each project has a unique project name
  project_name: 4c167d53
  # there is an extension system that lets you add doit tasks to alto or enable built in extensions
  extensions: ["evidence"]
  # the root load_path is often used by targets, it is overwritten by a taps `load_path` during EL
  load_path: raw
  # taps, targets, and utilities are the 3 keys here
  taps:
    # name the tap whatever you want, but naming it after the executable saves us from specifying it
    tap-carbon-intensity:
      # this should all be almost identical to Meltano barring `load_path` which is explained above
      pip_url: git+https://gitlab.com/meltano/tap-carbon-intensity.git#egg=tap_carbon_intensity
      load_path: carbon_intensity
      capabilities:
        - state
        - catalog
      select:
        - "*.*"
      config: {}
  targets:
    target-jsonl:
      pip_url: target-jsonl==0.1.4
      config:
        # an example of how to use the load_path set by a tap
        destination_path: "@format output/{this.load_path}"
```

Alto uses the popular [Singer](https://www.singer.io/) ETL framework to execute data extraction and transformation tasks, which means you can use any of the [hundreds](https://hub.meltano.com/) of existing Singer taps and targets to connect to the systems you need. Additionally, Alto provides a powerful and flexible way to build [PEX](https://github.com/pantsbuild/pex) files, which are self-contained executable files that encapsulate your code and dependencies, making it easy to distribute your data integration workflows to other systems. All of the existing ecosystem as well as all plugins built via the [Meltano SDK](https://sdk.meltano.com/en/latest/) are usable out of the box.

Another standout features of Alto is its data reservoir, which allows you to store and manage your data in a centralized location. This can be especially useful for teams that need to share data across multiple targets or replay loads when target plugins change. It provides a consistent and reliable source of truth for your data. It also allows you to run taps and targets independently even on different machines. This persistence is powered by [fsspec](https://github.com/fsspec/filesystem_spec) and for the end user its as simple as `alto tap-github:reservoir` to send data in and `alto reservoir:tap-github-target-*` to send data out where `*` can be any configured target.

Finally, Alto is scaffolded over [Doit](https://github.com/pydoit/doit), a Python-based task automation tool, to manage and execute your data integration workflows. This means it is more like Make and will build dependencies if they do not exist meaning data integrations are executed with a single command.


## Comparison

> How is this different than what exists today; namely Meltano?

### Pros

I might recommend `alto` if Meltano seems like overkill for what you are doing. What does that mean? If you have a Python project where EL is one of many concerns and you want a dependency you can add that is lean, yet highly functional. You can use `alto` alongside [dbt](https://github.com/dbt-labs/dbt-core/) without conflict, along data science packages without conflict, and there is _very_ low risk for conflict in general. I would recommend `alto` if you don't want everything in your project running in different venvs because they would conflict with Meltano.

Alto is able to run taps -> targets with centralized environment-aware configuration, secret management, automatically managed state, automatic discovery, catalog caching to a remote backend, catalog manipulation via `select` & `metadata` keys, and all the things we love about Meltano. Given this, in most situations -- from a pure EL perspective, it stacks up fairly with Meltano since it is really the plugins that do most of the work once the previous conveniences are factored in. I don't claim `alto` does as much as Meltano but I do claim, in my experience, it does *enough*.

Outside of the prior points, there are some compelling features in `alto` in general around how it manages plugins as cached PEX files, the built in reservoir, and its light footprint. Continuing to use Meltano as the baseline of comparison (since it was the inspiration), here are some noteworthy differences:

- The CLI is extremely fast due to the lightness of the package.

- There is no system db so no database migrations or system directory to care about.

- Significantly smaller dependency footprint by an **order of magnitude**. Alto only has 4 direct dependencies with no C or rust extensions in the dependency tree, it is pure python. The below comparison includes transitives:
    - **Meltano**: 151
    - **Alto**: 7

- Because of its dependency footprint, it can be installed in very tiny Docker containers and wheels are cross platform compatible. It also installs extremely quickly.

- We use `PEX` (PythonEXecutable) for all plugins instead of loose venvs making plugins single files that are straightforward to cache.

- We use a (simple) caching algorithm that makes the plugins re-usable across machines when combined with a remote filesystem and re-usable on the same system in general. This means, most of the time, you will build a PEX artifact once and **never** build it again. This makes an already lightweight `alto` even more portable.

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

### Cons

- No stream map support yet. This will change.

- No commands equivalent to `config set` or `add`. This will not change. The goal is not 1:1 with Meltano but rather lighter weight alternative for the power user. Configuration will be managed via YAML/config exclusively.

## Example

An entire timed end-to-end example can be carried out via the below script.

From start to finish, this script does:

1. Creates a directory
2. Initializes an alto project (creates the `alto.toml` file)
3. Runs an extract -> load of an open API to target jsonl
    1. Builds PEX plugins for `tap-carbon-intensity` and `target-jsonl` caching them so they won't be rebuilt again for this project
    2. Dynamically generates config for the Singer plugin based on the toml file (supports toml/yaml/json)
    3. Runs discovery and caches catalog to ~/.alto/(project-name)/catalog
    4. Applies user configuration (`select` & `metadata`) to the catalog, ~ functionally equivalent to Meltano
    5. Checks for state in the remote backend
    6. Runs the pipeline
    7. Cleans up the staging directory
    8. Parses and persists the state to the remote backend

```bash
# Create a dir
mkdir example_project
# Enter it
cd example_project
# Init a project
alto init --no-prompt
# Run a pipeline immediately
alto tap-carbon-intensity:target-jsonl
# Verify the output
cat output/* | head -8; ls -l output
cd .. && tree example_project
# Clean up
rm -rf example_project
```

Resulting in the below output prior to clean up:

```
example_project
├── .alto
│   ├── logs
│   │   └── dev
│   └── plugins
│       ├── 263b729b56cf48f4bc3d08b687045ad3f81713ce
│       └── 60e33af4f316a41812ee404136d7a747011ba811
├── .alto.json
├── alto.secrets.toml
├── alto.toml
└── output
    ├── entry-20230228T205342.jsonl
    ├── generationmix-20230228T205342.jsonl
    └── region-20230228T205342.jsonl

5 directories, 8 files
```

`>>> cat alto.toml`

```toml
[default]
project_name = "4c167d53"
extensions = []
load_path = "raw"

[default.taps.tap-carbon-intensity]
pip_url = "git+https://gitlab.com/meltano/tap-carbon-intensity.git#egg=tap_carbon_intensity"
load_path = "carbon_intensity"
capabilities = ["state", "catalog"]
select = ["*.*"]

[default.taps.tap-carbon-intensity.config]

[default.targets.target-jsonl]
pip_url = "target-jsonl==0.1.4"

[default.targets.target-jsonl.config]
destination_path = "output"
```

[license]: https://github.com/z3z1ma/alto/blob/main/LICENSE
