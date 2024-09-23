"""Local plugin to parametrize tests from a JSON file."""

import json
import datetime

from collections import namedtuple
from pathlib import Path

import pytest


ChangelogUpdate = namedtuple(
    "ChangelogUpdate", ("original", "version", "expected", "url", "date")
)

# Named stash keys for storing the ChangelogUpdate objects between hook calls
changelog_updates_key = pytest.StashKey[list[ChangelogUpdate]]()


def pytest_configure(config: pytest.Config) -> None:
    """
    Configure plugin by loading the Changelog data.
    """
    resource_path = Path(__file__).resolve().parent.joinpath("resources")
    changelogs_file = resource_path / "changelogs.json"
    with changelogs_file.open(mode="r", encoding="utf-8") as infile:
        changelog_groups = json.load(infile)

    updates = []
    for group in changelog_groups:
        date = datetime.date.fromisoformat(group["date"])

        updates.append(
            ChangelogUpdate(
                resource_path / group["original"],
                None,
                resource_path / group["formatted"],
                group["url"],
                date,
            )
        )

        for version, expected in group.get("bumps", {}).items():
            updates.append(
                ChangelogUpdate(
                    resource_path / group["original"],
                    version,
                    resource_path / expected,
                    group["url"],
                    date,
                )
            )

    config.stash[changelog_updates_key] = updates


def pytest_generate_tests(metafunc: pytest.Metafunc):
    """
    Inject parameters for the 'changelog_update' fixture.
    """
    if "changelog_update" in metafunc.fixturenames:
        metafunc.parametrize(
            "changelog_update", metafunc.config.stash[changelog_updates_key]
        )
