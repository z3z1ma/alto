---
sidebar_position: 2
---

# State Management

Alto never destroys prior state files. We leave it to the user to decide where, when, and how to purge state files. The current state can be found in the `state` directory of your remote storage (we refer to the latest state as the "active state"). Furthermore, state is automatically partitioned by environment. For example, if you have a tap named `my-tap` pushing data to `my-target` and you have an environment named `dev-alex`, the state file for that tap will be located at `state/dev-alex/my-tap-to-my-target.json`. Historical state files will be preserved at `state/dev-alex/my-tap-to-my-target.{timestamp}.json`.

It can be reset by running the `alto clean my-tap:my-target` command.

Following the example above, if you wanted to clear the active state, you would run the following command:

```bash
alto clean my-tap:my-target
```

This will delete the state file for the tap named `my-tap` to the target `my-target` in the `state` directory of your remote storage.

Extending the previous example in a more functional way, if you wanted to clear the active state and then run the tap to target, you would run the following command:

```bash
alto clean my-tap:my-target ; alto my-tap:my-target
```

This would result in a "full refresh" of the tap to target.

## Purging All State Files

If you want to purge all active state files, you can run the following command:

```bash
alto clean state
```

:::danger Danger

This will delete all active state files in the `state` directory of your remote storage. (Historical state files will be preserved.)

:::
