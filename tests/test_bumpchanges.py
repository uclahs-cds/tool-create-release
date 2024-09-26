"""Tests for the bumpchanges module."""

import contextlib

from pathlib import Path
from unittest.mock import patch

import pytest
from semver import Version

from bumpchanges.getversion import get_next_version


@contextlib.contextmanager
def mock_tag_exists(tags):
    """Context manager to mock `tag_exists`."""
    def mock_function(_, tag):
        """Local mock function."""
        return tag in tags

    with patch("bumpchanges.getversion.tag_exists", side_effect=mock_function):
        yield


@pytest.mark.parametrize("last,bump_type,expected_str", [
    # Bumping from a non-prerelease version
    (Version(1, 1, 1), "prerelease", "1.1.2-rc.1"),
    (Version(1, 1, 1), "patch", "1.1.2"),
    (Version(1, 1, 1), "minor", "1.2.0"),
    (Version(1, 1, 1), "major", "2.0.0"),

    # Bumping from a prerelease version
    (Version(1, 1, 1, "rc.1"), "prerelease", "1.1.1-rc.2"),
    (Version(1, 1, 1, "rc.1"), "patch", "1.1.1"),
    (Version(1, 1, 1, "rc.1"), "minor", "1.2.0"),
    (Version(1, 1, 1, "rc.1"), "major", "2.0.0"),

    (Version(2, 0, 0), "prerelease", "2.0.1-rc.1"),
    (Version(0, 0, 0), "patch", "0.0.1"),
])
def test_next_version(last, bump_type, expected_str):
    """Get that the next versions match what is expected."""
    with patch("bumpchanges.getversion.get_closest_semver_ancestor", return_value=last):
        # Ignore any tags in _this_ repository while testing
        with mock_tag_exists([]):
            assert get_next_version(Path(), bump_type, "") == expected_str


@pytest.mark.parametrize("last,bad_type,existing_tags", [
    (Version(1, 1, 58), "patch", ["v1.1.59"]),
    (Version(2, 44, 58), "minor", ["v2.45.0"]),
    (Version(1, 1, 1), "major", ["v2.0.0"]),
    (Version(87600, 1, 1), "major", ["v87601.0.0"]),
    (Version(3, 4, 5, "rc.2"), "prerelease", ["v3.4.5-rc.3"]),
])
def test_fail_on_existing_tags(last, bad_type, existing_tags):
    """Test that bumping to an existing version will raise an error."""
    bump_types = ["major", "minor", "patch", "prerelease"]

    contexts = {
        bump_type: pytest.raises(RuntimeError)
        if bump_type == bad_type
        else contextlib.nullcontext()
        for bump_type in bump_types
    }

    with patch("bumpchanges.getversion.get_closest_semver_ancestor", return_value=last):
        for bump_type in bump_types:
            with mock_tag_exists([]):
                # With no tags, everything is valid
                get_next_version(Path(), bump_type, "")

            with mock_tag_exists(existing_tags):
                with contexts[bump_type]:
                    get_next_version(Path(), bump_type, "")
