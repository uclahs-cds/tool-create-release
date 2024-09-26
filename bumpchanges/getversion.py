"""Get the next tag version."""

import argparse
import re
import os

from logging import getLogger
from pathlib import Path


from .logging import setup_logging, NOTICE
from .utils import get_closest_semver_ancestor, version_to_tag_str, tag_exists


def get_next_version(repo_dir: Path, bump_type: str, exact_version: str) -> str:
    """Return the next tag after the appropriate bump type."""
    logger = getLogger(__name__)

    if bump_type == "exact":
        last_version = "<ignored>"
        if not exact_version:
            logger.error("Exact version requested, but no version supplied!")
            raise RuntimeError()

        if re.match(r"^v\d", exact_version):
            logger.error(
                "Input version `{exact_version}` should not have a leading `v`"
            )
            raise RuntimeError()

        next_version_str = exact_version

    else:
        last_version = get_closest_semver_ancestor(repo_dir)
        next_version_str = str(last_version.next_version(part=bump_type))

    logger.info("%s -> %s -> %s", last_version, bump_type, next_version_str)
    next_tag = version_to_tag_str(next_version_str)
    logger.log(NOTICE, "New version (tag): %s (%s)", next_version_str, next_tag)

    # Confirm that the corresponding git tag does not exist
    if tag_exists(repo_dir, next_tag):
        # Oops, that tag does exist
        logger.error("Tag %s already exists!", next_tag)
        raise RuntimeError()

    return next_version_str


def entrypoint():
    """Main entrypoint for this module."""
    setup_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument("repo_dir", type=Path)
    parser.add_argument("bump_type", type=str)
    parser.add_argument("exact_version", type=str)

    args = parser.parse_args()
    setup_logging()

    next_version = get_next_version(args.repo_dir, args.bump_type, args.exact_version)

    Path(os.environ["GITHUB_OUTPUT"]).write_text(
        f"next_version={next_version}\n", encoding="utf-8"
    )
