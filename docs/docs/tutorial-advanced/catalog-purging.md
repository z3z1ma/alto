---
sidebar_position: 1
---

# Catalog Purging

Alto will not automatically purge your base catalog. You must explicitly tell Alto to purge the catalog. This is done by running the `alto clean catalog:{tap-name}` command.

For example, if you have a tap named `my-tap` and you want to purge the catalog for that tap, you would run the following command:

```bash
alto clean catalog:my-tap
```

This will delete the catalog file for the tap named `my-tap` in the `catalogs` directory of your remote storage.

## Purging All Catalogs

If you want to purge all catalogs, you can run the following command:

```bash
alto clean catalog
```

:::danger Danger

This will delete all catalogs in the `catalogs` directory of your remote storage. This may make subsequent runs of your pipelines slower. Generally, you should only purge the catalogs for the taps that you are actively working on.

:::

## Reasoning

Alto does not automatically purge the catalog because it is a destructive operation. Our goal is to make the DX similar to tools like `terraform` and `dbt`. In those tools, you must explicitly tell the tool to destroy something. Alto is no different. We want to make sure that you are aware of what you are doing when you purge the catalog. It is often done intentionally as part of a cycle where a source schema changes and you want to re-discover the new schema. In any other situation, we prefer explicitness over implicitness. That can simply mean a few extra keystrokes, but it is worth it to us.

This command would permit the user to run a pipeline with a fresh catalog and is not much added effort vs any automatic purging:

```bash
alto clean catalog:my-tap ; alto my-tap:my-target
```

:::tip Tip

This is all in relation to what we refer to as a "base" catalog. The "runtime" catalog is always rendered fresh and is not stored in the remote storage.

:::
