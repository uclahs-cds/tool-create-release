"""Utility functions."""

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


def get_github_releases(repo_dir: Path) -> list[Release]:
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
