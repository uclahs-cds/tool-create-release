"""Tests for CHANGELOG parsing and reformatting."""

from bumpchanges.changelog import Changelog


def test_formatting(changelog_update):
    """Confirm that an example CHANGELOG can be parsed and formatted."""
    changelog = Changelog(changelog_update.original, changelog_update.url)

    if changelog_update.version is not None:
        changelog.update_version(changelog_update.version, changelog_update.date)

    result_text = changelog.render()

    expected_text = changelog_update.expected.read_text(encoding="utf-8")

    assert expected_text == result_text
