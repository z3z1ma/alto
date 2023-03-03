# Alto

Alto is a versatile data integration tool that allows you to easily run Singer plugins, build and cache PEX files encapsulating those plugins, and create a data reservoir whereby you can extract once and replay to as many destinations as you want. With Alto, you can seamlessly connect to various data sources, store your data in a centralized reservoir (singerlake), and manage extract lean, efficient load flows. 

Like [Meltano](https://github.com/meltano/meltano), Alto is driven entirely by configuration and the config structure drew much of its inspiration from Meltano. Alto supports YAML, TOML, and JSON leveraging [Dynaconf](https://github.com/dynaconf/dynaconf) for robust features and the structure is modeled similarly to Meltano making using one or the other, or just giving `alto` a whirl, a fairly straightforward process. 

TODO: Document config spec

Alto uses the popular [Singer](https://www.singer.io/) ETL framework to execute data extraction and transformation tasks, which means you can use any of the [hundreds](https://hub.meltano.com/) of existing Singer taps and targets to connect to the systems you need. Additionally, Alto provides a powerful and flexible way to build [PEX](https://github.com/pantsbuild/pex) files, which are self-contained executable files that encapsulate your code and dependencies, making it easy to distribute your data integration workflows to other systems. All of the existing ecosystem as well as all plugins built via the [Meltano SDK](https://sdk.meltano.com/en/latest/) are usable out of the box.

One of the standout features of Alto is its data reservoir, which allows you to store and manage your data in a centralized location. This can be especially useful for teams that need to share data across multiple targets or replay loads when target plugins change. It provides a consistent and reliable source of truth for your data. It also allows you to run taps and targets independently even on different machines.

Finally, Alto is scaffolded over [Doit](https://github.com/pydoit/doit), a Python-based task automation tool, to manage and execute your data integration workflows. This means it is more like Make and will build dependencies if they do not exist meaning data integrations are executed with a single command.

> How is this different than what exists today; namely Meltano?

I might recommend `alto` if you need a simple codebase as a starting point to extend or if Meltano seems like overkill for what you are hoping to do (IE move data from A to B in a existing project that has dbt and other deps installed). Alto from the perspective of being able to run taps -> targets has more-or-less parity with Meltano since it is really the plugins that do most of the work. There are also some compelling features in `alto` in general around how it manages plugins as cached PEX files, the built in reservoir, and its light footprint. Using Meltano as the baseline of comparison, here are some noteworthy differences:

- The CLI is extremely fast due to the lightness of the package.

- There is no system db so no database migrations or system directory to care about.

- Significantly smaller dependency footprint by an **order of magnitude**. Alto only has 4 direct dependencies with no C or rust extensions in the dependency tree, it is pure python. The below comparison includes transitives:
    - **Meltano**: 151
    - **Alto**: 7

- Because of its dependency footprint, it can be installed in very tiny Docker containers and wheels are cross platform compatible. It also installs extremely quickly.

- We use `PEX` (PythonEXecutable) for all plugins instead of loose venvs making plugins single files that are straightforward to cache.

- We use a (simple) caching algorithm that makes the plugins re-usable across machines when combined with a remote filesystem and re-usable on the same system in general.

- Docker containers do not require you to "install" the plugins during the build process since the plugins are instantly pulled from a remote cache.

- Because of how plugins are handled it can be ran in `lambda` and serverless functions very easily.

- We use `fsspec` to provide that filesystem abstraction layer that provides the exact same experience locally on a single machine as when plugged into a remote blob store such as `s3`, `gcs`, or any supported `fsspec` storage. We do not carry the dep but let the user specify.

- An order of magnitude (`>85%`) less code which makes iteration/maintenance or forking easier (in theory) but of course less code != better

- Because it is scaffolded over a build system, never worry about running `install` again, run pipelines immediately and alto works out the rest.

- We use `Dynaconf` to manage configuration
    - This gives us uniform support for json, toml, and yaml out of the box
    - We get environment management 
    - We get configuration inheritance / deep merging
    - We get `.env` support
    - We get unique ways to render vars with `'@format ` tokens

- Encourages use of `bash` instead of `meltano run` commands. Bash is _already_ a fantastic glue code where you can run multiple extract load blocks, background them via `&` to parallelize loads, run utilities the way they have always been ran since everything is not wrapped in a venv with env vars injected by Meltano which is both a convenience and a constraint. `meltano run tap1 target1 tap2 target2` is functionally identical to `alto tap1:target1 && alto tap2:target2` except in the latter there is massive flexibility.

## Example

An entire timed end-to-end example can be carried out via the below script.

From start to finish, it will:

1. Create a directory
2. Initialize an alto project (create the `alto.toml` file)
3. Run an extract -> load of an open API to target jsonl
    1. Build PEX plugins for `tap-carbon-intensity` and `target-jsonl`
    2. Dynamically generate config for the Singer plugin based on the toml file (supports toml/yaml/json)
    3. Run discovery and cache catalog to ~/.alto/(project-name)/catalog
    4. Apply user configuration to the catalog
    5. Run the pipeline
    6. Clean up the staging directory
    7. Manage and persist the state

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
namespace = "raw"

[default.taps.tap-carbon-intensity]
pip_url = "git+https://gitlab.com/meltano/tap-carbon-intensity.git#egg=tap_carbon_intensity"
namespace = "carbon_intensity"
capabilities = ["state", "catalog"]
select = ["*.*"]

[default.taps.tap-carbon-intensity.config]

[default.targets.target-jsonl]
pip_url = "target-jsonl==0.1.4"

[default.targets.target-jsonl.config]
destination_path = "output"
```
