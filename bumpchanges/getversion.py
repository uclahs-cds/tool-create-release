"""Get the next tag version."""

import argparse
import re
import os

from logging import getLogger
from pathlib import Path


from .logging import setup_logging, NOTICE
from .utils import get_closest_semver_ancestor, version_to_tag_str, tag_exists


def get_next_semver(repo_dir: Path, bump_type: str, prerelease: bool) -> str:
    """Validate and return the next semantic version."""
    logger = getLogger(__name__)

    last_version = get_closest_semver_ancestor(repo_dir, allow_prerelease=False)
    next_version = last_version.next_version(part=bump_type)

    if prerelease:
        next_version = next_version.bump_prerelease()
        # Look for the next non-existing prerelease version
        while tag_exists(repo_dir, version_to_tag_str(next_version)):
            logger.debug("Prerelease %s already exists, bumping again...", next_version)
            next_version = next_version.bump_prerelease()

    next_version_str = str(next_version)
    validate_version_bump(repo_dir, str(last_version), next_version_str)
    return next_version_str


def get_exact_version(repo_dir: Path, exact_version) -> str:
    """Validate the specified exact version."""
    logger = getLogger(__name__)

    if not exact_version:
        logger.error("Exact version requested, but no version supplied!")
        raise RuntimeError()

    if not re.match(r"^\d", exact_version):
        logger.error("Input version `{exact_version}` does not start with a digit")
        raise RuntimeError()

    validate_version_bump(repo_dir, "<ignored>", exact_version)
    return exact_version


def validate_version_bump(
    repo_dir: Path, prior_version_str: str, next_version_str: str
):
    """Validate that the proposed version is acceptable."""
    logger = getLogger(__name__)

    logger.info("%s -> %s", prior_version_str, next_version_str)
    next_tag = version_to_tag_str(next_version_str)
    logger.log(NOTICE, "New version (tag): %s (%s)", next_version_str, next_tag)

    # Confirm that the corresponding git tag does not exist
    if tag_exists(repo_dir, next_tag):
        # Oops, that tag does exist
        logger.error("Tag %s already exists!", next_tag)
        raise RuntimeError()


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


def entrypoint():
    """Main entrypoint for this module."""
    setup_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument("repo_dir", type=Path)
    parser.add_argument(
        "bump_type", type=str, choices=("major", "minor", "patch", "exact")
    )
    parser.add_argument("prerelease", type=str_to_bool)
    parser.add_argument("exact_version", type=str)

    args = parser.parse_args()
    setup_logging()

    if args.bump_type == "exact":
        next_version = get_exact_version(args.repo_dir, args.exact_version)
    else:
        next_version = get_next_semver(args.repo_dir, args.bump_type, args.prerelease)

    Path(os.environ["GITHUB_OUTPUT"]).write_text(
        f"next_version={next_version}\n", encoding="utf-8"
    )
