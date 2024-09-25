"""Tests for CHANGELOG parsing and reformatting."""

import contextlib
from unittest.mock import patch, Mock

import pytest
import semver

from bumpchanges.alias import ReleaseAliaser, IneligibleAlias, AliasError, Release


# Sample test case to mock _dereference_tags
@pytest.fixture(name="aliaser")
def mock_aliaser_internals(tmp_path):
    """Fixture to mock out the git and GitHub internals of a ReleaseAliaser."""
    # The baseline case here is to have several non-semver-tags and then
    # several semver tags across multiple major versions.
    tag_to_commit_map = {
        "nonsemver": "asdfasdf",
        "2.0.0": "bar",
        "v1.0.0": "tergasdfasdf",
        "v1.0.1": "berqwref",
        "v2.0.0-rc.1": "foo",
        "v2.0.0": "bar",
        "v2.1.0": "baz",
        "v2.2.0-rc.1": "qux",
    }

    releases = [
        Release("", "v1.0.0", False, False),
        Release("", "v1.0.1", False, False),
        Release("", "v2.0.0-rc.1", False, True),
        Release("", "v2.0.0", False, False),
        Release("", "v2.1.0", False, False),
    ]

    with patch.multiple(
        ReleaseAliaser, _dereference_git_tags=Mock(), _get_github_release_tags=Mock()
    ):
        aliaser = ReleaseAliaser(tmp_path)
        for tag, commit in tag_to_commit_map.items():
            aliaser._add_git_tag(tag, commit)

        for release in releases:
            aliaser._add_github_release(release)

        yield aliaser


def test_alias_workflow(aliaser):
    """Test the basic steps of aliasing a new release."""
    assert aliaser.compute_alias_action(1) == ("v1", "v1.0.1")
    assert aliaser.compute_alias_action(2) == ("v2", "v2.1.0")

    with pytest.raises(IneligibleAlias):
        aliaser.compute_alias_action(3)


def test_modified_releases(aliaser):
    """Test how new releases interact with the results."""
    assert aliaser.compute_alias_action(2) == ("v2", "v2.1.0")

    # Act as if this GitHub release never existed
    aliaser.tag_to_release_map.pop("v2.1.0")
    assert aliaser.compute_alias_action(2) == ("v2", "v2.0.0")

    # Act as if this GitHub release never existed. There are no more valid releases.
    aliaser.tag_to_release_map.pop("v2.0.0")
    with pytest.raises(IneligibleAlias):
        aliaser.compute_alias_action(2)

    # Add in a new release
    v220 = "v2.2.0"
    aliaser._add_git_tag(v220, "asdfasdffs")
    aliaser._add_github_release(Release("", v220, False, False))

    assert aliaser.compute_alias_action(2) == ("v2", v220)

    # Add in a lower release, showing that it will be masked
    v211 = "v2.1.1"
    aliaser._add_git_tag(v211, "rtpeoisbf")
    aliaser._add_github_release(Release("", v211, False, False))

    assert aliaser.compute_alias_action(2) == ("v2", v220)

    # Add in a higher release, showing that it will take priority
    v221 = "v2.2.1"
    aliaser._add_git_tag(v221, "aqqqqdfasdffs")
    aliaser._add_github_release(Release("", v221, False, False))

    assert aliaser.compute_alias_action(2) == ("v2", v221)


@pytest.mark.parametrize("semver_pre", [True, False])
@pytest.mark.parametrize("release_draft", [True, False])
@pytest.mark.parametrize("release_pre", [True, False])
def test_drafts_and_prereleases(aliaser, semver_pre, release_draft, release_pre):
    """Test that only non-drafts and full releases are eligible."""
    base_version = semver.Version(3, 0, 0)
    if semver_pre:
        base_version = base_version.bump_prerelease()

    tag = f"v{base_version}"

    aliaser._add_git_tag(tag, "sdflaksfjkalsfj")
    aliaser._add_github_release(Release("", tag, release_draft, release_pre))

    if semver_pre or release_pre or release_draft:
        expectation = pytest.raises(IneligibleAlias)
    else:
        expectation = contextlib.nullcontext()

    with expectation:
        assert aliaser.compute_alias_action(3) == ("v3", tag)


@pytest.mark.parametrize(
    "missing_tag,expectation",
    [
        ("v1.0.1", pytest.raises(AliasError)),
        ("v2.0.0", pytest.raises(AliasError)),
        ("nonsemver", contextlib.nullcontext()),
    ],
)
def test_sanity_checks(aliaser, missing_tag, expectation):
    """Test that invariants will be violated if the GitHub and git tags drift out of sync."""
    # Remove the tag
    aliaser.tag_to_commit_map.pop(missing_tag)

    with expectation:
        assert aliaser.compute_alias_action(2) == ("v2", "v2.1.0")
