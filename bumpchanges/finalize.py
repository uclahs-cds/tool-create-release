"""Finalize a release when a PR is merged."""

import argparse
import json
import logging
import os
import subprocess
import textwrap

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


from .logging import setup_logging, NOTICE, LoggingMixin
from .utils import (
    decode_branch_name,
    version_to_tag_str,
    tag_to_semver,
    str_to_bool,
    get_nearest_ancestor_release_tag,
    NoAppropriateTagError,
)


class InvalidReleaseError(Exception):
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
            raise InvalidReleaseError("Workflow requires pull_request events")

        with Path(os.environ["GITHUB_EVENT_PATH"]).open(encoding="utf-8") as infile:
            event_data = json.load(infile)

        if (
            not event_data["pull_request"]["merged"]
            or event_data["pull_request"]["state"] != "closed"
        ):
            raise InvalidReleaseError(
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

    def create(self, draft: bool, archival_path: Optional[Path]):
        """Create the release and return the URL."""
        args = [
            "gh",
            "release",
            "create",
            self.tag,
            "--repo",
            self.owner_repo,
            "--notes",
            f"Automatically generated after merging #{self.pr_number}.",
            "--generate-notes",
            "--target",
            self.target,
            "--title",
            f"Release {self.version}",
        ]

        try:
            prior_tag = get_nearest_ancestor_release_tag(self.owner_repo, self.tag)
            self.logger.info("Autogenerated notes will start from `%s`", prior_tag)
            args.extend(["--notes-start-tag", prior_tag])
        except NoAppropriateTagError as err:
            self.logger.info("No appropriate release notes start tag found: %s", err)

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

        # Create and upload a tarball if the archival path exists
        if archival_path:
            self.logger.info("Creating tarball")

            tarball = Path(
                os.environ["GITHUB_WORKSPACE"],
                f"{archival_path.name}-{self.tag}.tar.gz",
            )

            subprocess.run(
                ["tar", "--exclude-vcs", "-czvf", tarball, archival_path.name],
                cwd=archival_path.parent,
                check=True,
            )

            try:
                subprocess.run(
                    [
                        "gh",
                        "release",
                        "upload",
                        self.tag,
                        "--repo",
                        self.owner_repo,
                        f"{tarball}#Source code with submodules (tar.gz)",
                    ],
                    check=True,
                )
                comment_body += (
                    "\n\nA source tarball including all submodules "
                    "has been attached to the release."
                )

            except subprocess.CalledProcessError:
                self.logger.error("Failed to attach tarball to release!")
                comment_body += (
                    "\n\n**ERROR:** Failed to attach source tarball to release!"
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
    parser.add_argument(
        "--archival-path", help="Path to a directory to tar and attach to the release"
    )

    args = parser.parse_args()

    try:
        # Parse the environment to create the release
        new_release = PreparedRelease.from_environment()

        archival_path = Path(args.archival_path) if args.archival_path else None

        if archival_path:
            # Sanity-check that the cloned name matches the environment
            repo_name = new_release.owner_repo.split("/", maxsplit=1)[-1]
            if repo_name != archival_path.name:
                raise RuntimeError(f"{repo_name} != {archival_path.name}!")

        # Draft or create the release
        new_release.create(args.draft, archival_path)

    except:
        logging.getLogger(__name__).exception("Failed to create new release")
        raise
