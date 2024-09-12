# BAM's core python module (`bam-core`)

Re-usable functions and settings for automations.

## What's in here?

* [`bam_core.lib`](bam_core/lib/): classes for interacting with common services.
* [`bam_core.utils`](bam_core/utils/): assorted utilities.
* [`bam_core.functions`](bam_core/functions/): Code for our [Digital Ocean Functions](../functions/)
* [`bam_core.settings`](bam_core/settings.py): Shared env-based settings.
* [`bam_core.constants`](bam_core/constants.py): References to Airtable fields, values, views, and schemas.
* [`tests`](tests/): tests run via `pytest -vv .`

## How do I install this locally?

Follow the setup guide in the [README](../README.md) of this repository, then run the tests to confirm everything is working:

```bash
pytest -vv . # run the tests
```

## How do I contribute new functionality?

First, create a new branch and make your changes locally:

```bash
git checkout -b feature/my-new-feature
touch bam_core/lib/new_service.py
git add -A
git commit -m'adding a new service to bam-core'
git push origin feature/my-new-feature
```

When you're ready, open a [pull request](https://github.com/bushwickayudamutua/bam-automation/pulls) which merges your changes to the `main` branch and ask someone in the Signal Chat for a review!
