"""Work with CHANGELOG.md files."""

import argparse
import datetime
import logging
import os
import tempfile
import zoneinfo

from logging import getLogger
from pathlib import Path

from .changelog import Changelog, ChangelogError
from .logging import setup_logging, NOTICE


def update_changelog(
    changelog_file: Path, repo_url: str, version: str, date: datetime.date
):
    "Rewrite a CHANGELOG file for a new release."

    try:
        changelog = Changelog(changelog_file, repo_url)
    except ChangelogError:
        getLogger(__name__).exception("Could not parse changelog")
        raise

    changelog.update_version(version, date)

    changelog_file.write_text(changelog.render(), encoding="utf-8")


def write_commit_details(version: str):
    """Write text snippets for the eventual commit and pull request."""
    outputs = {}

    actor = os.environ["GITHUB_ACTOR"]
    trigger_actor = os.environ["GITHUB_TRIGGERING_ACTOR"]
    ref_name = os.environ["GITHUB_REF_NAME"]
    bump_type = os.environ["BUMP_TYPE"]
    exact_version = os.environ["EXACT_VERSION"]

    body_values = {}
    body_values = {"Actor": f"@{actor}"}

    if trigger_actor != actor:
        body_values["Triggering Actor"] = f"@{trigger_actor}"

    body_values.update({
        "Branch": f"`{ref_name}`",
        "Bump Type": f"`{bump_type}`",
    })

    if bump_type == "exact":
        body_values["Exact version"] = exact_version

    # Write the PR body into a temporary file
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=os.environ["GITHUB_WORKSPACE"], delete=False
    ) as bodyfile:
        bodyfile.write(
            f"""\
Update CHANGELOG in preparation for release **{version}**.

Merging this PR will trigger another workflow to create the release tag **v{version}**.

| Input | Value |
| ----- | ----- |
"""
        )

        for key, value in body_values.items():
            bodyfile.write(f"| {key} | {value} |\n")

        outputs["pr_bodyfile"] = bodyfile.name

    outputs["pr_title"] = f"Prepare for version `{version}`"
    outputs["commit_message"] = f"Update CHANGELOG for version `{version}`"

    Path(os.environ["GITHUB_OUTPUT"]).write_text(
        "\n".join(f"{key}={value}" for key, value in outputs.items()) + "\n",
        encoding="utf-8",
    )


def entrypoint():
    """Main entrypoint."""
    parser = argparse.ArgumentParser()
    parser.add_argument("changelog", type=Path)
    parser.add_argument("repo_url", type=str)
    parser.add_argument("version", type=str)

    args = parser.parse_args()
    setup_logging()

    try:
        input_timezone = os.environ["CHANGELOG_TIMEZONE"]
        try:
            tzinfo = zoneinfo.ZoneInfo(input_timezone)
        except zoneinfo.ZoneInfoNotFoundError:
            logging.getLogger(__name__).warning(
                "Time zone `%s` not found! Defaulting to UTC", input_timezone
            )
            tzinfo = datetime.timezone.utc
    except KeyError:
        logging.getLogger(__name__).log(
            NOTICE, "No time zone provided, defaulting to UTC"
        )
        tzinfo = datetime.timezone.utc

    now_date = datetime.datetime.now(tzinfo).date()

    update_changelog(args.changelog, args.repo_url, args.version, now_date)
    write_commit_details(args.version)
