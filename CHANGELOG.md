# Changelog

All notable changes to the tool-create-release Action.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.0.1]: https://github.com/uclahs-cds/tool-create-release/compare/0.0.1-rc.1...0.0.1
[0.0.1-rc.1]: https://github.com/uclahs-cds/tool-create-release/releases/tag/0.0.1-rc.1
[0.0.2]: https://github.com/uclahs-cds/tool-create-release/compare/0.0.1...0.0.2
