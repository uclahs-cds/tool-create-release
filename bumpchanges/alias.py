"""Create a major version alias for a semantic version release."""

import argparse
import json
import re
import subprocess
import operator
import logging

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


class ReleaseAliaser(LoggingMixin):
    """A class to manage aliasing release tags."""

    def __init__(self, repo_dir: Path):
        super().__init__()

        self.repo_dir = repo_dir

        # Map between existing tags and commit hashes, with annotated tags
        # dereferenced
        self.tag_to_commit_map = self._dereference_tags()

        # Tags associated with a release on GitHub
        self.tag_to_release_map = self._get_github_releases()

        # Map between existing tags and semantic versions
        self.tag_to_version_map = self._parse_semver_tags()

        # Verify data integrity - all releases must have tags
        if unknown_tags := self.tag_to_release_map.keys() - self.tag_to_commit_map.keys():
            raise AliasError(
                f"GitHub reports tags that are not visible locally: {unknown_tags}"
            )

        # Issue warnings about SemVer tags not associated with a release
        for tag in sorted(self.tag_to_version_map.keys() - self.tag_to_release_map.keys()):
            self.logger.warning(
                "SemVer tag `%s` does not have a matching GitHub Release. "
                "Please create the Release or remove the tag.",
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


    def _dereference_tags(self) -> dict[str, str]:
        """
        Return a dictionary mapping tags to commit hashes.

        Annotated tags are dereferenced to point to the raw commit.
        """
        show_ref_output = (
            subprocess.check_output(
                ["git", "show-ref", "--dereference"], cwd=self.repo_dir
            )
            .decode("utf-8")
            .strip()
        )

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

        return tag_to_commit_map


    def _get_github_releases(self) -> dict[str, Release]:
        """Return all non-prerelease, non-draft release tags from GitHub."""
        releases = [
            Release(**item) for item in json.loads(
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
            )
        ]

        return {release.tagName: release for release in releases}

    def _parse_semver_tags(self) -> dict[str, semver.version.Version]:
        """Return a dictionary mapping valid input tags to semantic versions."""
        tag_to_version_map = {}

        for git_tag in sorted(self.tag_to_commit_map.keys()):
            if not git_tag.startswith("v"):
                logging.debug("Tag `%s` doesn't start with a `v`", git_tag)
                continue

            try:
                tag_to_version_map[git_tag] = semver.Version.parse(git_tag[1:])
                logging.debug(
                    "Tag %s -> Version %s", git_tag, tag_to_version_map[git_tag]
                )
            except ValueError:
                logging.debug(
                    "%s (from %s) is not valid SemVer", git_tag[1:], git_tag
                )

        return tag_to_version_map

    def _get_major_version_and_alias(self, changed_tag: str) -> tuple[int, str]:
        """Return a tuple of the major version and alias tag."""
        # Only act if the changed tag is a semantic version tag
        if not changed_tag.startswith("v"):
            raise IneligibleAlias(f"Changed tag `{changed_tag}` doesn't start with a `v`")

        try:
            major_version = semver.Version.parse(changed_tag[1:]).major
            target_alias = f"v{major_version}"
        except ValueError as err:
            raise IneligibleAlias(f"Changed tag `{changed_tag}` is not in SemVer format") from err

        self.logger.info(
            "Tag `%s` changed - evaluating tag alias `%s` for major version `%d`",
            changed_tag,
            target_alias,
            major_version
        )

        if target_alias in self.tag_to_commit_map:
            other_tags = [
                tag
                for tag, commit in self.tag_to_commit_map.items()
                if commit == self.tag_to_commit_map[target_alias]
                and tag != target_alias
            ]

            if other_tags:
                self.logger.log(
                    NOTICE,
                    "Tag %s currently points to tag(s): %s (commit %s)",
                    target_alias,
                    other_tags,
                    self.tag_to_commit_map[target_alias],
                )
            else:
                self.logger.log(
                    NOTICE,
                    "Tag %s currently points to untagged commit: %s",
                    target_alias,
                    self.tag_to_commit_map[target_alias],
                )

        else:
            self.logger.log(NOTICE, "Tag %s does not exist")

        return (major_version, target_alias)


    def compute_alias_action(self, changed_tag: str) -> tuple[str, str]:
        """
        Return a tuple of (alias, target) strings showing the necessary change.

        An example return value is ("v2", "v2.1.0"), meaning that the tag "v2"
        should be updated to point to the existing tag "v2.1.0".
        """

        # Find the highest release for this major version
        major_version, target_alias = self._get_major_version_and_alias(changed_tag)

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
            raise IneligibleAlias("No eligible release tags alias `{target_alias}`")

        target_tag = eligible_tags[-1]
        self.logger.log(NOTICE, "Alias `%s` should point to `%s`", target_alias, target_tag)

        if self.tag_to_commit_map[target_tag] == self.tag_to_commit_map.get(target_alias):
            raise IneligibleAlias(f"`{target_alias}` is already up-to-date!")

        return (target_alias, target_tag)

    def update_alias(self, target_alias: str, target_tag: str):
        """Actually update the alias and push it to GitHub."""
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


def entrypoint():
    """Main entrypoint for this module."""
    setup_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument("repo_dir", type=Path)
    parser.add_argument("changed_tag", type=str)

    args = parser.parse_args()

    aliaser = ReleaseAliaser(args.repo_dir)
    alias, tag = aliaser.compute_alias_action(args.changed_tag)
    # aliaser.update_alias(alias, tag)
