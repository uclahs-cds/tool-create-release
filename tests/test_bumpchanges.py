"""Tests for the bumpchanges module."""
import contextlib
from pathlib import Path
from unittest.mock import patch

import pytest
from semver import Version

from bumpchanges.getversion import get_next_version


@pytest.mark.parametrize("last,bump_type,expected_str", [
    (Version(1, 1, 1), "prerelease", "1.1.2-rc.1")
])
def test_next_version(last, bump_type, expected_str):
    """Get that the next versions match what is expected."""
    with patch("bumpchanges.getversion.get_closest_semver_ancestor", return_value=last):
        assert get_next_version(Path(), bump_type, "") == expected_str
