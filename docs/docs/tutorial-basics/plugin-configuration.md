# Plugin Configuration

## What is a plugin?

A plugin is what `alto` uses to perform work. There are 3 **types** of plugins:

- **Taps** - Taps are used to extract data from a source. For example, a tap might be a plugin that can extract data from a database like Postgres or an API like HubSpot.
- **Targets** - Targets are used to load data to a destination. For example, a target might be a plugin that can load data to BigQuery, local parquets, or blob storage.
- **Utilities** - Utilities are simply python packages that are not taps or targets that you want `alto` to manage. The advantage being that you get the build-once PEX files, remote filesystem caching, and environment isolation that `alto` provides.

## How do I configure a plugin?

As we stated in the last section, there are two main units of configuration in `alto`. There is **project-level** configuration and there is **plugin-level** configuration. Plugin level configuration exists in 3 different sections of the `alto.toml` file:

- `default.taps`
- `default.targets`
- `default.utilities`

Each section corresponds to the **type** of plugin and `alto` uses this information to wire up all the possible tap and target combinations and to expose functionality to the user via the CLI in an intuitive way. Note that `default` could be replaced with any environment name.

## Config Structure

:::tip Tip

You will notice much of this is optional. Where possible, we try to provide sensible defaults. The end-goal is conciseness. Feel free to breeze past this if you want to jump into the more concrete examples in the following sections.

:::

Here we represent it as an abstract **tree** where each node is a possible key in the configuration file. The `->` symbol indicates a key that points to a value. The `?` prefix indicates the key is optional:

```
env-name
├── environment   -> Dict[str, str]
├── extensions    -> List[str or path]
├── load_path     -> str
├── taps
│   └── tap-name
│       ├── pip_url        -> str
│       ├── ?executable    -> str
│       ├── ?entrypoint    -> str
│       ├── ?capabilities  -> List[str]
│       ├── ?config        -> Dict[str, Any]
│       ├── ?select        -> List[str]
│       ├── ?metadata      -> Dict[str, Dict[str, Any]]
│       ├── ?stream_maps   -> List[path or Dict[str, str]]
│       ├── ?load_path     -> str
│       ├── ?inherit_from  -> str
│       ├── ?environment   -> Dict[str, str]
│       └── ?[accent]      -> Dict[str, Any]
├── targets
│   └── target-name
│       ├── pip_url
│       ├── ?executable
│       ├── ?entrypoint
│       ├── ?inherit_from
│       ├── ?environment
│       └── ?config
└── utilities
    └── utility-name
        ├── pip_url
        ├── ?executable
        ├── ?entrypoint
        ├── ?inherit_from
        └── ?environment
```

## Where do I find plugins?

The best source for available taps is the [Meltano Hub](https://hub.meltano.com/). We expose an index of [taps](/docs/integrations/taps) and [targets](/docs/integrations/taps) in the documentation as a convenience too. Alternatively, you can search [GitHub](https://github.com) OR roll your own thanks to the great [SDK](https://sdk.meltano.com/en/latest/).
