"Get the next tag version."

import os
import subprocess

from logging import getLogger
from pathlib import Path

import semver

from .logging import setup_logging


def get_next_version():
    "Return the next tag after the appropriate bump type."
    setup_logging()
    logger = getLogger(__name__)
    repo_dir = os.environ["REPO_DIR"]
    bump_type = os.environ["BUMP_TYPE"]
    exact_version = os.environ["EXACT_VERSION"]
    output_file = Path(os.environ["GITHUB_OUTPUT"])

    if bump_type == "exact":
        last_version = "<ignored>"
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
    logger.notice("New version (tag): %s (%s)", next_version, next_tag)

    # Confirm that the corresponding git tag does not exist
    try:
        tag_ref = subprocess.check_output(
            ["git", "rev-parse", "--verify", f"refs/tags/{next_tag}"],
            cwd=repo_dir
        )
        # Oops, that tag does exist
        logger.error("Tag %s already exists! %s", next_tag, tag_ref)
        raise RuntimeError()

    except subprocess.CalledProcessError:
        # Tag doesn't exist yet - everything is good!
        pass

    with output_file.open(mode="w", encoding="utf-8") as outfile:
        outfile.write(f"next_version={next_version}\n")
