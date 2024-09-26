"""Utility functions."""

import logging
import json
import operator
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import semver


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


def dereference_tags(repo_dir: Path) -> dict[str, str]:
    """Return a dictionary mapping all tags to commit hashes."""
    show_ref_output = (
        subprocess.check_output(
            ["git", "show-ref", "--dereference"], cwd=repo_dir
        )
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
    return json.loads(
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
