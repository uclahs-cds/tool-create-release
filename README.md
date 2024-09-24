# Automations for GitHub Releases

This pair of reusable workflows manage the complexity of creating and tagging new software releases on GitHub.

## Versioning Standards

These workflows make the following assumptions:

* Versions begin with a digit. This applies whether the project is using [semantic versioning](https://semver.org/) or not.
* Git tags associated with a version begin with a `v`.

`1.2.3`, `1.alpha`, and `4.2` are all acceptable versions, and will be tagged in git as `v1.2.3`, `v1.alpha`, and `v4.2` respectively.

`alpha`, `one.two`, and `v1.2.3` are **not** acceptable versions.

## Usage

`wf-prepare-release.yaml` is triggered manually (via a `workflow_dispatch`) and takes the following actions:

1. Compute the target version number based on existing tags and user input for `major`/`minor`/`patch`/`prerelease`.
1. Re-write the `CHANGELOG.md` file to move unreleased changes into a new dated release section.
1. Open a PR listing the target version number and release tag.

`wf-finalize-release.yaml`, triggered when a release PR is merged, takes the following actions:

1. Create a new release with auto-generated notes and the target tag.
  * By default the new release is a draft, so no public release or tag are created without user intervention.
1. Comment on the release PR with a link to the new release.

## Example Usage

Usage of this tool requires adding two workflows to each calling repository:

**`prepare-release.yaml`**

```yaml
---
name: Prepare new release

run-name: Open PR for new ${{ inputs.bump_type }} release

on:
  workflow_dispatch:
    inputs:
      bump_type:
        type: choice
        description: >-
          Semantic version bump type. Using `exact` is required for repositories
          without semantic version tags and allows specifying the exact next tag
          to use with the `exact_version` argument.
        required: true
        options:
          - major
          - minor
          - patch
          - prerelease
          - exact
      exact_version:
        type: string
        description: >-
          Exact version number to target. Only used if bump_type is set to
          `exact`. Do not include a leading `v`.
        required: false
        default: ''

permissions:
  actions: read
  contents: write
  pull-requests: write

jobs:
  prepare-release:
    uses: uclahs-cds/tool-create-release/.github/workflows/wf-prepare-release.yaml@v1
    with:
      bump_type: ${{ inputs.bump_type }}
      exact_version: ${{ inputs.exact_version }}
    # Secrets are only required until tool-create-release is made public
    secrets: inherit
```

**`finalize-release.yaml`**

```yaml
---
name: Finalize release

on:
  pull_request:
    branches:
      - main
    types:
      - closed

permissions:
  actions: read
  contents: write
  pull-requests: write

jobs:
  finalize-release:
    # This conditional ensures that the reusable workflow is only run for
    # release pull requests. The called workflow repeats these checks.
    if: ${{ github.event.pull_request.merged == true && startsWith(github.event.pull_request.head.ref, 'automation-create-release') }}
    uses: uclahs-cds/tool-create-release/.github/workflows/wf-finalize-release.yaml@v1
    with:
      draft: true
    # Secrets are only required until tool-create-release is made public
    secrets: inherit
```

## Parameters

Parameters can be specified using the [`with`](https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions#runsstepswith) option.

| Workflow | Parameter | Type | Required | Description |
| ---- | ---- | ---- | ---- | ---- |
| `wf-prepare-release.yaml` | `bump_type` | string | yes | Kind of semantic release version to target. Must be one of `major`, `minor`, `patch`, `prerelease`, or `exact`. Using `exact` requires `exact_version`. |
| `wf-prepare-release.yaml` | `exact_version` | string | no | The exact version to assign to the next release (only used if `bump_type` is `exact`). Must not include a leading `v` - use `1XXXX`, not `v1XXXX`. |
| `wf-prepare-release.yaml` | `changelog` | string | no | Relative path to the CHANGELOG file. Defaults to `./CHANGELOG.md`. |
| `wf-prepare-release.yaml` | `timezone` | string | no | IANA timezone to use when calculating the current date for the CHANGELOG. Defaults to `America/Los_Angeles`. |
| `wf-finalize-release.yaml` | `draft` | boolean | no | If true (the default), mark the new release as a draft and require manual intervention to continue. |

## License

tool-generate-docs is licensed under the GNU General Public License version 2. See the file LICENSE.md for the terms of the GNU GPL license.

Copyright (C) 2024 University of California Los Angeles ("Boutros Lab") All rights reserved.

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
