"""Tests for CHANGELOG parsing and reformatting."""

from contextlib import nullcontext
from unittest.mock import patch

import pytest

from bumpchanges.utils import (
    encode_branch_name,
    decode_branch_name,
    Release,
    NoAppropriateTagException,
    get_nearest_ancestor_release_tag,
)


@pytest.mark.parametrize(
    "version_str",
    [
        "2.0.0",
        "5.4.3-rc.1+foobar",
        "2.0.0.1.2.3.4.5.6",
        "alpha",
        "48",
        "5vasdf",
    ],
)
def test_encoding_and_decoding(version_str):
    """Test that versions can be encoded and decoded through the branch name."""
    branch_name = encode_branch_name(version_str)
    assert branch_name != version_str
    assert version_str == decode_branch_name(branch_name)


RELEASES = [
    Release("", "v1.0.0", False, False),
    Release("", "v1.0.1", False, False),
    Release("", "v2.0.0-rc.1", False, True),
    Release("", "v2.0.0", False, False),
    Release("", "v2.0.5", True, False),  # This one is a draft
    Release("", "v2.1.0", False, False),
    Release("", "v2.2.0-rc.1", False, True),
    Release("", "nonsemver", False, False),
]


@pytest.mark.parametrize(
    "tag,releases,result",
    [
        ("v1.0.2", RELEASES, nullcontext("v1.0.1")),
        ("v0.0.2", RELEASES, pytest.raises(NoAppropriateTagException)),
        ("v2.0.0-rc.2", RELEASES, nullcontext("v2.0.0-rc.1")),
        ("v2.0.4", RELEASES, nullcontext("v2.0.0")),
        ("v2.0.6", RELEASES, nullcontext("v2.0.0")),
        ("v3.0.0", RELEASES, nullcontext("v2.2.0-rc.1")),
        ("valpha", RELEASES, pytest.raises(NoAppropriateTagException)),
    ],
)
def test_prior_release_tag(tag, releases, result):
    """Test that finding the prior release tag works as expected."""
    with patch(
        "bumpchanges.utils.get_github_releases_from_repo_name", return_value=releases
    ):
        with result as res:
            assert get_nearest_ancestor_release_tag("", tag) == res
