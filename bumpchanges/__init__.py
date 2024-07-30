#!/usr/bin/env python3
"Work with CHANGELOG.md files."

import argparse

from pathlib import Path

from .changelog import Changelog


def update_changelog(
    changelog_file: Path, repo_url: str, version: str
) -> str:
    "Rewrite a CHANGELOG file for a new release."
    changelog = Changelog(changelog_file, repo_url)
    changelog.update_version(version)
    return changelog.render()


def main():
    "Main entrypoint."
    parser = argparse.ArgumentParser()
    parser.add_argument("changelog", type=Path)
    parser.add_argument("repo_url", type=str)
    parser.add_argument("version", type=str)

    args = parser.parse_args()

    print(update_changelog(args.changelog, args.repo_url, args.version))

if __name__ == "__main__":
    main()
