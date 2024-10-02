"""Utility functions."""

import argparse
import logging
import json
import operator
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import semver

from .logging import NOTICE


@dataclass
class Release:
    """A representation of a GitHub release."""

    # These names match the attributes returned by the GitHub API
    # pylint: disable=invalid-name
    name: str
    tagName: str

    isDraft: bool
    isPrerelease: bool


BRANCH_PREFIX = "automation-create-release-"


def encode_branch_name(version: str) -> str:
    """Encode this version into a branch name."""
    return BRANCH_PREFIX + version


def decode_branch_name(branch: str) -> str:
    """Decode the branch name into a version."""
    version = branch.removeprefix(BRANCH_PREFIX)

    if version == branch:
        raise ValueError(f"Branch `{branch}` is not correctly encoded!")

    return version


def tag_to_semver(tag: str) -> semver.version.Version:
    """
    Return the Version associated with this git tag.

    Raises ValueError for invalid tags.
    """
    if not tag.startswith("v"):
        raise ValueError(f"Tag `{tag}` doesn't start with a `v`")

    return semver.Version.parse(tag[1:])


def version_to_tag_str(version: Union[str, semver.version.Version]) -> str:
    """Return the git tag associated with this version."""
    # _Do_ add leading `v`s. Versions numbers never have leading `v`s, tags
    # always have leading `v`s.
    version = str(version)
    return f"v{version.lstrip('v')}"


def tag_exists(repo_dir: Path, tag: str) -> bool:
    """Return True if the tag exists, False otherwise."""
    tag_ref_proc = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/tags/{tag}"],
        cwd=repo_dir,
        capture_output=True,
        check=False,
    )

    return tag_ref_proc.returncode == 0


def dereference_tags(repo_dir: Path) -> dict[str, str]:
    """Return a dictionary mapping all tags to commit hashes."""
    show_ref_output = (
        subprocess.check_output(["git", "show-ref", "--dereference"], cwd=repo_dir)
        .decode("utf-8")
        .strip()
    )

    pattern = re.compile(
        r"^(?P<commit>\w+)\s+refs/tags/(?P<tag>.*?)(?P<annotated>\^\{\})?$",
        flags=re.MULTILINE,
    )

    tag_to_commit_map: dict[str, str] = {}
    dereferenced_tags: dict[str, str] = {}

    for match in pattern.finditer(show_ref_output):
        logging.getLogger(__name__).debug(match.groups())
        operator.setitem(
            dereferenced_tags if match["annotated"] else tag_to_commit_map,
            match["tag"],
            match["commit"],
        )

    # Update all of the annotated tags with the dereferenced commits
    tag_to_commit_map.update(dereferenced_tags)

    return tag_to_commit_map


def get_github_releases_from_checkout(repo_dir: Path) -> list[Release]:
    """Get all release data from GitHub."""
    return [
        Release(**item)
        for item in json.loads(
            subprocess.check_output(
                [
                    "gh",
                    "release",
                    "list",
                    "--json",
                    ",".join((
                        "name",
                        "tagName",
                        "isDraft",
                        "isPrerelease",
                    )),
                ],
                cwd=repo_dir,
            )
        )
    ]


def get_github_releases_from_repo_name(owner_repo: str) -> list[Release]:
    """Get all release data from GitHub."""
    return [
        Release(**item)
        for item in json.loads(
            subprocess.check_output(
                [
                    "gh",
                    "release",
                    "list",
                    "--repo",
                    owner_repo,
                    "--json",
                    ",".join((
                        "name",
                        "tagName",
                        "isDraft",
                        "isPrerelease",
                    )),
                ],
            )
        )
    ]


class NoAppropriateTagError(Exception):
    """Exception to indicate the lack of an appropriate ancestor tag."""


def get_nearest_ancestor_release_tag(owner_repo: str, tag_str: str) -> str:
    """
    Return the most appropriate starting tag for the GitHub release notes.

    Raises `NoAppropriateTagError` if the input tag is not a semantic
    version or if there is no appropriate ancestral tag.
    """
    try:
        semantic_version = tag_to_semver(tag_str)
    except ValueError as err:
        raise NoAppropriateTagError(
            f"The input tag `{tag_str}` is not a semantic version"
        ) from err

    logger = logging.getLogger(__name__)
    logger.debug("Searching for most recent prior release...")

    # Get the prior releases from GitHub
    existing_releases = []
    for release in get_github_releases_from_repo_name(owner_repo):
        logger.debug("Examining %s...", release.tagName)

        # Ignore drafts
        if release.isDraft:
            logger.debug("... draft, ignoring")
            continue

        # Ignore non-semver tags
        try:
            prior_version = tag_to_semver(release.tagName)
            logger.debug("... matches version %s ...", prior_version)
        except ValueError:
            logger.debug("... not semver, ignoring")
            continue

        # Ignore higher versions
        if prior_version < semantic_version:
            logger.debug(
                "... %s < %s, keeping for consideration",
                prior_version,
                semantic_version,
            )
            existing_releases.append((prior_version, release.tagName))
        else:
            logger.debug("... %s > %s, ignoring", prior_version, semantic_version)

    existing_releases.sort(key=lambda x: x[0])
    logger.debug("All prior releases: %s", existing_releases)

    if existing_releases:
        logger.debug("The most recent release tag is %s", existing_releases[-1][1])
        return existing_releases[-1][1]

    raise NoAppropriateTagError("No prior release tags found")


def get_closest_semver_ancestor(
    repo_dir: Path, allow_prerelease: bool = False
) -> semver.version.Version:
    """
    Returns the most recent semantic version ancestor of HEAD.

    If `prerelease` is False, ignore prereleases.
    """
    # Previously this was using `git describe --tags --abbrev=0 --match
    # <glob>`, but the differences between the glob and the full regex were
    # causing issues. Do an exhaustive search instead.
    all_tags = (
        subprocess.check_output(["git", "tag"], cwd=repo_dir)
        .decode("utf-8")
        .strip()
        .splitlines()
    )

    version_distances = defaultdict(list)

    for tag in all_tags:
        # Ignore the tag if it's not an ancestor of HEAD or a semantic version
        try:
            subprocess.check_call(
                ["git", "merge-base", "--is-ancestor", tag, "HEAD"], cwd=repo_dir
            )
            version = tag_to_semver(tag)

        except subprocess.CalledProcessError:
            logging.getLogger(__name__).debug(
                "Tag `%s` is not an ancestor of HEAD", tag
            )
            continue
        except ValueError as err:
            logging.getLogger(__name__).debug(err)
            continue

        if version.prerelease and not allow_prerelease:
            logging.getLogger(__name__).debug("Tag `%s` is a prerelease", tag)
            continue

        # Compute the commit distance between the tag and HEAD
        distance = int(
            subprocess.check_output(
                ["git", "rev-list", "--count", f"{tag}..HEAD"],
                cwd=repo_dir,
            )
        )
        version_distances[distance].append(version)
        logging.getLogger(__name__).debug(
            "Tag `%s` (version %s) is %d commits away from HEAD", tag, version, distance
        )

    if not version_distances:
        fallback = semver.Version(0, 0, 0)
        logging.getLogger(__name__).log(
            NOTICE,
            "No direct ancestors of HEAD are semantic versions - defaulting to %s",
            fallback,
        )
        return fallback

    min_distance = min(version_distances)
    closest_versions = sorted(version_distances[min_distance])

    if len(closest_versions) > 1:
        logging.getLogger(__name__).warning(
            "Multiple tags are equidistant from HEAD: %s", closest_versions
        )

    logging.getLogger(__name__).info(
        "Closest ancestor %s is %d commits back", closest_versions[-1], min_distance
    )

    return closest_versions[-1]


def str_to_bool(value: str) -> bool:
    """Convert a string to a boolean (case-insensitive)."""
    truthy_values = {"true", "t", "yes", "y", "1"}
    falsey_values = {"false", "f", "no", "n", "0"}

    # Normalize input to lowercase
    value = value.lower()

    if value in truthy_values:
        return True

    if value in falsey_values:
        return False

    raise argparse.ArgumentTypeError(f"Invalid boolean value: '{value}'")
