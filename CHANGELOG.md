# Changelog

All notable changes to the tool-create-release Action.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.4] - 2025-02-10

### Added

- Add `attach-tarball` argument to finalize workflow to attach source tarball with release

### Changed

- Remove hard-coded UCLA secrets, add explicit `secrets` inputs to workflows
- Automatically delete release branch after merging pull request

### Fixed

- Added `import mdformat.renderer` to fix issue with mdformat v0.7.22

## [1.0.3] - 2024-11-01

### Fixed

- Properly handle non-standard capitalizations of `Unreleased`

## [1.0.2] - 2024-10-18

### Changed

- Set `draft` parameter in template to `false`

### Fixed

- Correct private repository badge template in README

## [1.0.1] - 2024-10-18

### Added

- Add badge linking to release workflow to README
- Add instructions for README badges to README

### Changed

- Comment out `draft` parameter in template
- Update template to refer to `v1` rather than `v1.0.0`

## [1.0.0] - 2024-10-02

### Added

- Add `version_files` input to update hard-coded version numbers during release

### Changed

- Move release finalization logic from JavaScript to python

### Fixed

- GitHub auto-generated release notes now link to prior tag, not alias

## [0.0.3] - 2024-09-30

### Added

- Documentation that versions must begin with a digit
- Documentation that git tags must begin with a `v`
- Template workflows to copy
- Enable Dependabot for GitHub Actions, pip, and template workflows
- Unit tests for version updates
- Workflow to update major tag (e.g. `v2`) when new releases are published or deleted
- Unit tests for aliasing

### Changed

- Change `prerelease` from an input "bump type" to a separate boolean
- Create "prerelease" GitHub Releases from prerelease versions

### Fixed

- Strip leading `v`s from versions in the CHANGELOG files

## [0.0.2] - 2024-08-19

### Fixed

- Stop appending extra `v` to latest tag in change URLs

## [0.0.1] - 2024-08-09

### Changed

- Pull request is created with separate token so workflows will run

## [0.0.1-rc.1] - 2024-08-05

### Added

- Workflow to update CHANGELOG and open pre-release PRs
- Workflow to create/draft releases after pre-release PR merge
- "Dogfood" workflows to self-manage this repository's releases

[0.0.1]: https://github.com/uclahs-cds/tool-create-release/compare/v0.0.1-rc.1...v0.0.1
[0.0.1-rc.1]: https://github.com/uclahs-cds/tool-create-release/releases/tag/v0.0.1-rc.1
[0.0.2]: https://github.com/uclahs-cds/tool-create-release/compare/v0.0.1...v0.0.2
[0.0.3]: https://github.com/uclahs-cds/tool-create-release/compare/v0.0.2...v0.0.3
[1.0.0]: https://github.com/uclahs-cds/tool-create-release/compare/v0.0.3...v1.0.0
[1.0.1]: https://github.com/uclahs-cds/tool-create-release/compare/v1.0.0...v1.0.1
[1.0.2]: https://github.com/uclahs-cds/tool-create-release/compare/v1.0.1...v1.0.2
[1.0.3]: https://github.com/uclahs-cds/tool-create-release/compare/v1.0.2...v1.0.3
[1.0.4]: https://github.com/uclahs-cds/tool-create-release/compare/v1.0.3...v1.0.4
