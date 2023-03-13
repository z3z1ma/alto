# Create a Project

## What is an Alto Project?

All an `alto` project is, at its core, is **just a configuration file**. Minimally, 1 file named `alto.{toml,yaml,json}`. Optionally, 1 more file named `alto.local.{toml,yaml,json}`. Alto will look for these files in the current directory when you run a command. If you are using `alto` as a library, you can specify the path to the configuration files.

## Generate a new project

The easiest way to create a new project is to use the `alto init` command:

```bash
alto init
```

This command will create a new project in the current directory.

## Basic Repo Structure

Without doing anything beyond running `alto init`, you will have a project with the following repository structure:

```
.
├── .env
├── .gitignore
├── alto.local.toml
└── alto.toml
```

## Configuration Files

We are going to refer to the configuration file as `alto.toml` in examples moving forward, but it is interchangeable with `yaml` or `json`.

The `alto.toml` file is the main configuration file for your project. It is what makes an `alto` project an `alto` project. It contains the configuration for all the `taps`, `targets`, and `utilities` you want to use. It is _not_ a requirement to generate this file via `alto init`, you can create it manually if you prefer.

The structure is ultimately the same whether represented in `toml`, `yaml`, or `json`. We are not going to go into detail about each of the fields in this section, but we have provided the general structure for you to reference if you are interested in creating your own `alto.{toml,yaml,json}` file.

## Adding New Taps, Targets, and Utilities

`alto` emphasizes simplicity. Users looking to add new taps, targets, and utilities should do so by adding the appropriate configuration to the `alto.toml` file. There are no commands to add new taps, targets, or utilities. Configuration is something that can be done manually, and we believe that it is a **better** experience to do so. The amount of time it takes to add a new tap, target, or utility to your `alto.toml` file when we have resources such as the Meltano [Hub](https://hub.meltano.com/) and author documentation is not significantly different vs imperatively going through a CLI. It is more transparent, you can see exactly what is happening in your configuration file, we are not exposed to stale metadata that may be used in a CLI, and it is a one-time expense. Once you have added a tap, target, or utility to your `alto.toml` file, you can run it as many times as you want.

The next section will show you exactly what a configuration file looks like.
