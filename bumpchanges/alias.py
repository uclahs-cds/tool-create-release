"""Create a major version alias for a semantic version release."""

import argparse
import json
import logging
import operator
import re
import subprocess
import sys

from dataclasses import dataclass
from pathlib import Path

import semver

from .logging import setup_logging, NOTICE, LoggingMixin


@dataclass
class Release:
    """A representation of a GitHub release."""
    # These names match the attributes returned by the GitHub API
    # pylint: disable=invalid-name
    name: str
    tagName: str

    isDraft: bool
    isPrerelease: bool


class IneligibleAlias(Exception):
    """
    Exception to major alias shouldn't be updated.

    These are expected and handle cases like prereleases, outdated tags, etc.
    """


class AliasError(Exception):
    """
    Exception indicating that something failed while updating the alias.

    These are never expected.
    """


def tag_to_semver(tag: str) -> semver.version.Version:
    """
    Return the Version associated with this git tag.

    Raises ValueError for invalid tags.
    """
    if not tag.startswith("v"):
        raise ValueError(f"Tag `{tag}` doesn't start with a `v`")

    return semver.Version.parse(tag[1:])


class ReleaseAliaser(LoggingMixin):
    """A class to manage aliasing release tags."""

    def __init__(self, repo_dir: Path):
        super().__init__()

        self.logger.debug("Creating ReleaseAliaser")

        self.repo_dir = repo_dir

        # Map between existing tags and commit hashes, with annotated tags
        # dereferenced
        self.tag_to_commit_map: dict[str, str] = {}

        # Tags associated with a release on GitHub
        self.tag_to_release_map: dict[str, Release] = {}

        # Map between existing tags and semantic versions
        self.tag_to_version_map: dict[str, semver.version.Version] = {}

        # Fill in all data
        self._dereference_git_tags()
        self._get_github_release_tags()


    def assert_invariants(self):
        """Confirm that the collected data is in a reasonable state."""
        # All releases must have corresponding git tags
        if unknown_tags := self.tag_to_release_map.keys() - self.tag_to_commit_map.keys():
            raise AliasError(
                f"GitHub reports tags that are not visible locally: {unknown_tags}"
            )

        # All semantic version tags must also be git tags
        if unknown_tags := self.tag_to_version_map.keys() - self.tag_to_commit_map.keys():
            raise AliasError(
                f"Invalid data state - non-git version tags exist: {unknown_tags}"
            )

        # Issue warnings about SemVer tags not associated with a release
        for tag in sorted(self.tag_to_version_map.keys() - self.tag_to_release_map.keys()):
            self.logger.warning(
                "SemVer tag `%s` does not have a matching GitHub Release.",
                tag
            )

        # Issue warnings about releases not associated with SemVer tags
        for tag in sorted(self.tag_to_release_map.keys() - self.tag_to_version_map.keys()):
            release = self.tag_to_release_map[tag]
            self.logger.warning(
                "Github Release `%s` uses the non-SemVer tag `%s`. "
                "All Releases should use SemVer tags.",
                release.name,
                tag
            )

    def _dereference_git_tags(self):
        """
        Map all git tags to commit hashes.

        Annotated tags are dereferenced to point to the raw commit.
        """
        show_ref_output = (
            subprocess.check_output(
                ["git", "show-ref", "--dereference"], cwd=self.repo_dir
            )
            .decode("utf-8")
            .strip()
        )
        self.logger.debug(show_ref_output)

        pattern = re.compile(
            r"^(?:<commit>\w+) refs/tags/(?:<tag>.*?)(?:<annotated>\^\{\})?$",
            flags=re.MULTILINE,
        )

        tag_to_commit_map: dict[str, str] = {}
        dereferenced_tags: dict[str, str] = {}

        for match in pattern.finditer(show_ref_output):
            operator.setitem(
                dereferenced_tags if match["annotated"] else tag_to_commit_map,
                match["tag"],
                match["commit"],
            )

        # Update all of the annotated tags with the dereferenced commits
        tag_to_commit_map.update(dereferenced_tags)
        for tag, commit in tag_to_commit_map.items():
            self._add_git_tag(tag, commit)

    def _add_git_tag(self, tag: str, commit: str):
        """Shim method to make it easier to test."""
        self.tag_to_commit_map[tag] = commit

        try:
            self.tag_to_version_map[tag] = tag_to_semver(tag)
        except ValueError as err:
            self.logger.info(err)

    def _get_github_release_tags(self):
        """Get all release tags and release data from GitHub."""
        for release_dict in json.loads(
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
                        ))
                    ],
                    cwd=self.repo_dir,
                )
                ):
            self._add_github_release(Release(**release_dict))

    def _add_github_release(self, release: Release):
        """Shim method to make it easier to test."""
        self.tag_to_release_map[release.tagName] = release

    def compute_alias_action(self, major_version: int) -> tuple[str, str]:
        """
        Return a tuple of (alias, target) strings showing the necessary change.

        An example return value is ("v2", "v2.1.0"), meaning that the tag "v2"
        should be updated to point to the existing tag "v2.1.0".
        """
        self.assert_invariants()

        target_alias = f"v{major_version}"

        # Find all semantic version tags that are associated with GitHub releases
        eligible_tags = []

        for tag in self.tag_to_commit_map:
            # Ignore non-semantic-version tags
            if not (version := self.tag_to_version_map.get(tag)):
                continue

            # Ignore non-GitHub-Release tags
            if not (release := self.tag_to_release_map.get(tag)):
                continue

            # Ignore prereleases (either SemVer or GitHub), drafts, and
            # different major releases
            if release.isDraft \
                    or release.isPrerelease \
                    or version.prerelease \
                    or version.major != major_version:
                continue

            eligible_tags.append(tag)

        eligible_tags.sort(key=lambda x: self.tag_to_version_map[x])

        if not eligible_tags:
            raise IneligibleAlias("No eligible release tags for alias `{target_alias}`")

        target_tag = eligible_tags[-1]
        self.logger.info("Alias `%s` should point to `%s`", target_alias, target_tag)

        return (target_alias, target_tag)

    def update_alias(self, target_alias: str, target_tag: str):
        """Actually update the alias and push it to GitHub."""

        if aliased_commit := self.tag_to_commit_map.get(target_alias):
            other_tags = [
                tag
                for tag, commit in self.tag_to_commit_map.items()
                if commit == aliased_commit
                and tag != target_alias
            ]

            if target_tag in other_tags:
                self.logger.log(NOTICE, "Alias `%s` is already up-to-date!", target_alias)
                return

            if other_tags:
                self.logger.info(
                    "Alias `%s` currently points to tag(s): %s (commit %s)",
                    target_alias,
                    other_tags,
                    aliased_commit,
                )
            else:
                self.logger.info(
                    NOTICE,
                    "Alias `%s` currently points to untagged commit: %s",
                    target_alias,
                    aliased_commit,
                )

        else:
            self.logger.info("Alias `%s` does not exist", target_alias)

        # Create the tag locally (forcing if necessary)
        subprocess.run(
            [
                "git",
                "tag",
                "--force",
                "--annotate",
                "--message",
                "Update major tag",
                target_alias,
                target_tag,
            ],
            cwd=self.repo_dir,
            check=True,
        )

        # Push the tag to GitHub
        subprocess.run(
            ["git", "push", "--force", "origin", target_alias],
            cwd=self.repo_dir,
            check=True,
        )

        self.logger.log(
            NOTICE,
            "Alias `%s` updated to `%s` (commit %s)",
            target_alias,
            target_tag,
            self.tag_to_commit_map[target_tag],
        )


def entrypoint():
    """Main entrypoint for this module."""
    setup_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument("repo_dir", type=Path)
    parser.add_argument("changed_ref", type=str)

    args = parser.parse_args()

    if not (tag_re := re.match(r"^refs/tags/([^/]+)$", args.changed_ref)):
        logging.getLogger(__name__).log(
            NOTICE,
            "Ref `%s` is not a tag - this workflow should not have been called",
            args.changed_ref
        )
        sys.exit(1)

    try:
        changed_version = tag_to_semver(tag_re.group(1))
    except ValueError:
        logging.getLogger(__name__).log(
            NOTICE,
            "Tag `%s` is not a semantic version - not updating any aliases",
            args.changed_tag
        )
        sys.exit(0)

    if changed_version.major < 1:
        logging.getLogger(__name__).log(NOTICE, "This workflow only updates `v1` and above")
        sys.exit(0)

    aliaser = ReleaseAliaser(args.repo_dir)
    alias, tag = aliaser.compute_alias_action(changed_version.major)
    aliaser.update_alias(alias, tag)
