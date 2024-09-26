"""Tests for the bumpchanges module."""

import contextlib

from pathlib import Path
from unittest.mock import patch

import pytest
from semver import Version

from bumpchanges.getversion import get_next_semver, get_exact_version


@contextlib.contextmanager
def mock_tag_exists(tags):
    """Context manager to mock `tag_exists`."""

    def mock_function(_, tag):
        """Local mock function."""
        return tag in tags

    with patch("bumpchanges.getversion.tag_exists", side_effect=mock_function):
        yield


@pytest.mark.parametrize(
    "last,bump_type,prerelease,expected_str",
    [
        (Version(1, 1, 1), "patch", True, "1.1.2-rc.1"),
        (Version(1, 1, 1), "patch", False, "1.1.2"),
        (Version(1, 1, 1), "minor", False, "1.2.0"),
        (Version(1, 1, 1), "major", False, "2.0.0"),
    ],
)
def test_next_version(last, bump_type, prerelease, expected_str):
    """Get that the next versions match what is expected."""
    with patch("bumpchanges.getversion.get_closest_semver_ancestor", return_value=last):
        # Ignore any tags in _this_ repository while testing
        with mock_tag_exists([]):
            assert get_next_semver(Path(), bump_type, prerelease) == expected_str


@pytest.mark.parametrize(
    "last,bad_type,existing_tags",
    [
        (Version(1, 1, 58), "patch", ["v1.1.59"]),
        (Version(2, 44, 58), "minor", ["v2.45.0"]),
        (Version(1, 1, 1), "major", ["v2.0.0"]),
        (Version(87600, 1, 1), "major", ["v87601.0.0"]),
    ],
)
def test_fail_on_existing_tags(last, bad_type, existing_tags):
    """Test that bumping to an existing version will raise an error."""
    bump_types = ["major", "minor", "patch"]

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
                get_next_semver(Path(), bump_type, False)

            with mock_tag_exists(existing_tags):
                with contexts[bump_type]:
                    get_next_semver(Path(), bump_type, False)

@pytest.mark.parametrize(
    "last,bump_type,existing_tags,expected",
    [
        (Version(23, 85, 43), "patch", ["v23.85.44-rc.1", "v23.85.44-rc.2"], "23.85.44-rc.3"),
        (Version(1, 2, 3), "minor", ["v1.3.0-rc.1"], "1.3.0-rc.2"),
        (Version(1, 2, 3), "major", ["v2.0.0-rc.1"], "2.0.0-rc.2"),
        (Version(1, 2, 3), "major", ["v2.0.0-rc.2"], "2.0.0-rc.1"),
    ],
)
def test_bumping_prerelease(last, bump_type, existing_tags, expected):
    """Test that multiple generations of prerelease can work."""
    with patch("bumpchanges.getversion.get_closest_semver_ancestor", return_value=last):
        with mock_tag_exists(existing_tags):
            assert get_next_semver(Path(), bump_type, True) == expected

@pytest.mark.parametrize(
    "exact_version_str,expectation",
    [
        ("1-alpha", contextlib.nullcontext()),
        ("5.4.3", contextlib.nullcontext()),
        ("2-alpha", contextlib.nullcontext()),
        ("233.33153", contextlib.nullcontext()),
        ("v2.1.1", pytest.raises(RuntimeError)),
        ("two", pytest.raises(RuntimeError)),
    ],
)

def test_get_exact(exact_version_str, expectation):
    """Test protections when giving an exact version string."""
    with mock_tag_exists([]):
        with expectation:
            assert get_exact_version(Path(), exact_version_str) == exact_version_str


@pytest.mark.parametrize(
    "exact_version_str,tag",
    [
        ("1-alpha", "v1-alpha"),
        ("5.4.3", "v5.4.3"),
        ("2-alpha", "v2-alpha"),
        ("233.33153", "v233.33153"),
    ],
)

def test_exact_tag_protection(exact_version_str, tag):
    """Test that get_exact_version will fail if the version tag already exists."""
    other_tags = ["v1.0.0", "1.0.0", "random"]

    with mock_tag_exists(other_tags):
        assert get_exact_version(Path(), exact_version_str) == exact_version_str

    other_tags.append(tag)

    with mock_tag_exists(other_tags):
        with pytest.raises(RuntimeError):
            get_exact_version(Path(), exact_version_str)
