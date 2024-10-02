# Changelog

All notable changes to the tool-create-release Action.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

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
