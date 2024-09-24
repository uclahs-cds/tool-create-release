"""Get the next tag version."""

import argparse
import re
import os
import subprocess

from logging import getLogger
from pathlib import Path

import semver

from .logging import setup_logging, NOTICE


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

        next_version = exact_version

    else:
        # Get the most recent ancestor tag that matches r"v\d.*"
        try:
            last_tag = subprocess.check_output(
                ["git", "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"],
                cwd=repo_dir,
            ).decode("utf-8")
        except subprocess.CalledProcessError:
            # It seems that this is the first release
            last_tag = "v0.0.0"
            logger.warning("No prior tag found! Defaulting to %s", last_tag)

        # Strip off the leading v when parsing the version
        last_version = semver.Version.parse(last_tag[1:])
        next_version = str(last_version.next_version(part=bump_type))

    logger.info("%s -> %s -> %s", last_version, bump_type, next_version)
    next_tag = f"v{next_version}"
    logger.log(NOTICE, "New version (tag): %s (%s)", next_version, next_tag)

    # Confirm that the corresponding git tag does not exist
    tag_ref_proc = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/tags/{next_tag}"],
        cwd=repo_dir,
        capture_output=True,
        check=False,
    )
    if tag_ref_proc.returncode == 0:
        # Oops, that tag does exist
        logger.error(
            "Tag %s already exists! %s", next_tag, tag_ref_proc.stdout.decode("utf-8")
        )
        raise RuntimeError()

    return next_version


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
