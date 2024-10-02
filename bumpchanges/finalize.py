"""Finalize a release when a PR is merged."""

import argparse
import json
import logging
import os
import subprocess
import textwrap

from dataclasses import dataclass, field
from pathlib import Path


from .logging import setup_logging, NOTICE, LoggingMixin
from .utils import (
    decode_branch_name,
    version_to_tag_str,
    tag_to_semver,
    str_to_bool,
    get_github_releases_from_repo_name,
)


class InvalidReleaseException(Exception):
    """Exception indicating that the workflow should not have run."""


@dataclass
class PreparedRelease(LoggingMixin):
    """A prepared release to finalize."""

    # The git commit to tag
    target: str
    version: str
    pr_number: int
    owner_repo: str

    # These will be infered based on the version string
    tag: str = field(init=False)
    prerelease: bool = field(init=False)

    @classmethod
    def from_environment(cls):
        """Parse a PreparedRelease from the environment."""
        if os.environ["GITHUB_EVENT_NAME"] != "pull_request":
            raise InvalidReleaseException("Workflow requires pull_request events")

        with Path(os.environ["GITHUB_EVENT_PATH"]).open(encoding="utf-8") as infile:
            event_data = json.load(infile)

        if (
            not event_data["pull_request"]["merged"]
            or event_data["pull_request"]["state"] != "closed"
        ):
            raise InvalidReleaseException(
                "Workflow should only be called on merged and closed PRs"
            )

        return cls(
            target=event_data["pull_request"]["merge_commit_sha"],
            version=decode_branch_name(os.environ["GITHUB_HEAD_REF"]),
            pr_number=event_data["number"],
            owner_repo=os.environ["GITHUB_REPOSITORY"],
        )

    def __post_init__(self):
        self.tag = version_to_tag_str(self.version)

        self.prerelease = False

        try:
            if tag_to_semver(self.tag).prerelease:
                self.prerelease = True
        except ValueError:
            pass

    def get_prior_tag(self) -> str:
        """Return the tag corresponding to the prior GitHub release."""
        try:
            semantic_version = tag_to_semver(self.tag)
        except ValueError:
            self.logger.info("The current tag is not using a semantic version")
            return ""

        self.logger.info("Searching for most recent prior release...")

        # Get the prior releases from GitHub
        existing_releases = []
        for release in get_github_releases_from_repo_name(self.owner_repo):
            self.logger.info("Examining %s...", release.tagName)

            # Ignore drafts
            if release.isDraft:
                self.logger.info("... draft, ignoring")
                continue

            # Ignore non-semver tags
            try:
                prior_version = tag_to_semver(release.tagName)
                self.logger.info("... matches version %s ...", prior_version)
            except ValueError:
                self.logger.info("... not semver, ignoring")
                continue

            # Ignore higher versions
            if prior_version < semantic_version:
                self.logger.info(
                    "... %s < %s, keeping for consideration",
                    prior_version,
                    semantic_version,
                )
                existing_releases.append((prior_version, release.tagName))
            else:
                self.logger.info(
                    "... %s > %s, ignoring", prior_version, semantic_version
                )

        existing_releases.sort(key=lambda x: x[0])
        self.logger.info("All prior releases: %s", existing_releases)

        if existing_releases:
            self.logger.info(
                "The most recent release tag is %s", existing_releases[-1][1]
            )
            return existing_releases[-1][1]

        self.logger.info("No prior release tags found")
        return ""

    def create(self, draft: bool):
        """Create the release and return the URL."""
        args = [
            "gh",
            "release",
            "create",
            self.tag,
            "--repo",
            self.owner_repo,
            "--notes",
            f"Automatically generated after merging {self.pr_number}.",
            "--generate-notes",
            "--target",
            self.target,
            "--title",
            f"Release {self.version}",
        ]

        if prior_tag := self.get_prior_tag():
            args.extend(["--notes-start-tag", prior_tag])

        if draft:
            args.append("--draft")

        if self.prerelease:
            args.append("--prerelease")

        release_url = subprocess.check_output(args).decode("utf-8").strip()
        self.logger.log(NOTICE, "Release created at %s", release_url)

        # Post a comment linking to the new release
        comment_header = "*Bleep bloop, I am a robot.*"
        comment_body = textwrap.fill(
            textwrap.dedent(f"""\
                A new release has been {"drafted" if draft else "created"}
                as {release_url}. Please review the details for accuracy.
                """),
            width=2000,
        )

        subprocess.run(
            [
                "gh",
                "issue",
                "comment",
                str(self.pr_number),
                "--repo",
                self.owner_repo,
                "--body",
                f"{comment_header}\n\n{comment_body}",
            ],
            check=True,
        )


def entrypoint():
    """Main entrypoint for this module."""
    setup_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument("draft", type=str_to_bool)

    args = parser.parse_args()

    try:
        # Parse the environment to create the release
        new_release = PreparedRelease.from_environment()

        # Draft or create the release
        new_release.create(args.draft)
    except:
        logging.getLogger(__name__).exception("Failed to create new release")
        raise
