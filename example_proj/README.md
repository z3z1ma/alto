# Example Project

This is an example to show the structure of an alto project. There is nothing notably unique except the presence of an `alto.{yaml,toml,json}` file when factoring in what is gitignored. That is part of the point. The goal is simplicity.

___

## Local Files

Here is what the full structure of a project might look like. Alto itself is an extremely light dependency, so it would not be unrealistic to have a requirements.txt or pyproject.toml including many other deps such as `dbt`. One can also freely leverage the `utilities` section of the alto config file to have alto generate, cache, and manage PEX files for any python package you may want to use but _not_ install into your environemnt.

```
.
├── .alto (gitignored)
│   ├── logs
│   │   └── dev 👇 logs for each plugin execution
│   │       ├── tap-0ef414a6-e13e-4a83-9028-d5c179631116.log
│   │       ├── tap-0f962970-0cc9-488d-87de-7c32543aad9c.log
│   │       └── tap-1dc51319-e645-4061-985e-977162eb6922.log
│   └── plugins 👇 PEX plugins which are kept here AND in the remote file store
│       ├── 09627b302d6d0cf04269e2bea92debc709c7b6b5
│       ├── 0ba9391fb58b961c59ee16fb9c28eb7b63f145fc
│       ├── 8830cdd6bea9e20ce4481024a80019f14ad822d7
│       ├── 92e48d3efe9639964e7f883e643c0240e7e5d326
│       ├── a67b456bedecaae93717205c7b7dfe7a8a9d3750
│       └── b7c86cd6a344f2a1ca7c9cf3a7294297e6a8c1f2
├── .alto.json          👈 an internal cache of task up-to-date hashes (gitignored)
├── .dlt
│   ├── config.toml     👈 used to configure `dlt`
│   └── secrets.toml    👈 used to configure `dlt` destinations (gitignored)
├── .gitignore
├── README.md
├── alto.secrets.yaml   👈 exact same structure as alto.yaml and merged at runtime (gitignored)
├── alto.yaml           👈 THE central configuration for `alto`
├── asana_pipeline.py
├── bls_pipeline.py     👈 these 3 py files are `dlt` pipelines fed by singer taps
├── carbon_intensity_pipeline.py
└── series.json
```

____

## Remote Files

Remote storage is a key concept baked into Alto from day 1. It was inspired by the simplicity of terraform and nix. A few concepts expressed here are you should never (rarely) need to build the same PEX twice for one Python/OS/Arch version. Especially when your working on a team with multiple devs and you are building and deploying containers. Containers are significantly smaller without needing multiple venvs and significantly faster to build. Another concept is that catalog caches should both be central and transparent and should be preserved in an exact state prior to user overrides. All teams leverage this catalog vs committing it to git and dealing with large diffs if it is generated in a different sort or users having multiple version in multiple branches. The next concept expressed is that we never delete state unless the user specifically does so, so we can always restart replicating from an old checkpoint. Lastly, the concept of a data reservoir as a built in staging area all taps can go to irrespective of any target and it can be pushed out to any target as many times as you want.

```
{gcs,s3,azdl,file}://<bucket name or `~` if file>/alto/<project name>/
├── catalogs 👇 these are catalogs which are cached to the remote file store PRIOR to user overrides
│   ├── tap-asana.base.json
│   ├── tap-bls.base.json
│   └── tap-carbon-intensity.base.json
├── plugins  👇 these are cached PEX plugins
│   ├── 09627b302d6d0cf04269e2bea92debc709c7b6b5
│   ├── 0ba9391fb58b961c59ee16fb9c28eb7b63f145fc
│   ├── 1676da47c022ede0cd691095bcf31c1e55e88b5e
│   ├── 24103a27045b9da59ac31a33f9ca274792d450b8
│   ├── 66605a6c1a0515b108ace90e5bd955149191a034
│   ├── 8830cdd6bea9e20ce4481024a80019f14ad822d7
│   ├── 92e48d3efe9639964e7f883e643c0240e7e5d326
│   ├── a67b456bedecaae93717205c7b7dfe7a8a9d3750
│   └── b7c86cd6a344f2a1ca7c9cf3a7294297e6a8c1f2
├── reservoir 👇 the idea of a data reservoir is a * native * concept so you can extract once, load many, and never lose loads
│   └── dev
│       └── tap-carbon-intensity
│           ├── _reservoir.json
│           ├── entry
│           │   └── db20736ab2d87e6
│           │       └── 20230311065214549869.singer.gz
│           ├── generationmix
│           │   └── d79e10d690ea5e7
│           │       └── 20230311065214556932.singer.gz
│           └── region
│               └── b6252a33b98191e
│                   └── 20230311065214525346.singer.gz
└── state
    └── dev 👇 state is not deleted, but always backed up in the remote store by default
        ├── tap-asana-to-dlt_tap-asana_dev.202303110353.json
        ├── tap-asana-to-dlt_tap-asana_dev.202303110405.json
        ├── tap-asana-to-dlt_tap-asana_dev.json
        ├── tap-bls-to-dlt-tap-bls-dev.202303110601.json
        ├── tap-bls-to-dlt-tap-bls-dev.json
        ├── tap-carbon-intensity-to-dlt_tap-carbon-intensity_dev.202303102212.json
        ├── tap-carbon-intensity-to-dlt_tap-carbon-intensity_dev.202303110343.json
        ├── tap-carbon-intensity-to-dlt_tap-carbon-intensity_dev.json
        ├── tap-carbon-intensity-to-reservoir.202303110652.json
        └── tap-carbon-intensity-to-reservoir.json
```
