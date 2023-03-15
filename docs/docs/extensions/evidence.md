# Evidence.dev

## What is Evidence.dev?

Quoting from the [Evidence.dev](https://evidence.dev) website:

### SQL + Markdown → Beautiful Reports

[Evidence](https://evidence.dev) enables analysts to build a trusted, version-controlled reporting system by writing SQL and a superset of markdown.

It's easy to get started and you can build data products that are both more sophisticated and easier to use than what you can build with a typical BI tool.

### Query your Data from Markdown

Run live SQL from markdown.

Evidence supports BigQuery, Snowflake, and PostgreSQL - with more to come.

### Create Reports that Feel Handwritten

Powerful features for automating text.

Include live data points in the text of your report. Generate lists, sections, headers and more. All controlled by your data.

### Include Charts and Graphs

Add professional graphics to your reports using our growing component library.

### Bring it all Under Version Control

Version control and test your reports.

Earn trust by delivering reliable, consistent outputs. Always have an answer for why the numbers changed.

Never serve broken reports again.

## Configuring Evidence.dev in Alto

Firstly, to enable the Evidence.dev extension, you must add `evidence` to the `extensions` key in your `alto` configuration file.

The Evidence.dev extension is configured primarily through environment variables. You can set these in your `.env` file, in your `alto` configuration file, or in your environment. There are a few exceptions to this rule, which are documented below. You can set the home directory for Evidence.dev in your `alto` configuration file, but you can also set the `EVIDENCE_HOME` environment variable to override this. You can also set the `strict` key in your `alto` configuration file to set the build mode to strict. This will cause the build to fail if any of the Evidence.dev reports fail to build. Lastly, you can set the `database` key in your `alto` configuration file to set the database adapter to use. This will override the `DATABASE` environment variable if set.

```toml title="alto.toml"
[default]
# Enable the evidence extension
extensions = ["evidence"]

[default.utilities.evidence]
# set the database adapter to use
config.database = "duckdb"
# set the home directory for evidence, the env var EVIDENCE_HOME will override this
config.home = "./report"
# set build mode to strict
config.strict = false
```

## Environment Variables

Below are the environment variables per adapter used to configure Evidence.dev in Alto. (not all env vars are required for all adapters).

:::info Heads Up

We are awaiting better documentation from Evidence.dev on adapter configuration.

:::

### ALL

- `DATABASE` - The database adapter to use. One of `bigquery`, `duckdb`, `mysql`, `postgres`, `redshift`, `snowflake`, `sqlite`
- `EVIDENCE_HOME` - (optional) The path to the Evidence project. Defaults to `./report`. Overrides the `config.home` key in your `alto` configuration file if set.

### Bigquery

- `BIGQUERY_PROJECT_ID`
- `BIGQUERY_CLIENT_EMAIL`
- `BIGQUERY_PRIVATE_KEY`

### Duckdb

- `DUCKDB_FILENAME`

### Mysql

- `MYSQL_USER`
- `MYSQL_HOST`
- `MYSQL_DATABASE`
- `MYSQL_PASSWORD`
- `MYSQL_PORT`
- `MYSQL_SOCKETPATH`
- `MYSQL_SSL`

### Postgres & Redshift

- `POSTGRES_USER`
- `POSTGRES_HOST`
- `POSTGRES_DATABASE`
- `POSTGRES_PASSWORD`
- `POSTGRES_PORT`
- `POSTGRES_SSL`
- `POSTGRES_CONNECTIONSTRING`
- `POSTGRES_SCHEMA`

### Snowflake

- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_USERNAME`
- `SNOWFLAKE_PASSWORD`
- `SNOWFLAKE_DATABASE`
- `SNOWFLAKE_WAREHOUSE`

### Sqlite

- `SQLITE_FILENAME`


## Usage

### Available Commands

```
🚀 evidence:initialize           Generate Evidence project from template.
🚀 evidence:build                Build the Evidence dev reports.
🚀 evidence:dev                  Run the Evidence dev server.
🚀 evidence:vars                 Dump env vars used to configure evidence. These must be set in your environment, in your .env file, or in your alto configuration file.
```

Run `evidence:initialize` to generate a new Evidence project from the template. You can commit this to your repository and use it as a starting point for your reports.

Run `evidence:build` to build your Evidence reports. This will run the Evidence dev build command and output the results to the `build` directory.

Run `evidence:dev` to run the Evidence dev server. This will run the Evidence dev dev command and output the results to the `build` directory.

Run `evidence:vars` to dump the environment variables used to configure Evidence.dev. These must be set in your environment, in your `.env` file, or in your `alto` configuration file.
