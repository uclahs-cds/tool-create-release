"""Update files with a new version number."""

import argparse
import logging
import os
import re

from pathlib import Path

from .logging import setup_logging, NOTICE


VERSION_REGEX = re.compile(r"""
    ^                       # Start of line, followed by any whitespace
    (?P<prefix>             # Open `prefix` capture group
        \s*                 # Any whitespace
        (?P<vquote>['"]?)   # `'`, `"`, or nothing (saved as `vquote` group)
        (?:__)?             # Optional literal `__`
        version             # Literal `version`
        (?:__)?             # Optional literal `__`
        (?P=vquote)         # `'`, `"`, or nothing (back-reference to `vquote`)
        (?:
            \s*             # Any whitespace
            [=:]?           # `=`, `:`, or nothing
            \s*             # Any whitespace
        )
        (?P<quote>['"]?)    # `'`, `"`, or nothing (saved as `quote` group)
    )                       # Close `prefix` capture group
    (?P<version>.*?)        # Non-greedy match of all characters (the version)
    (?P<suffix>             # Open `suffix` capture group
        (?P=quote)          # `'`, `"`, or nothing (back-reference to `quote`)
        ,?                  # Optional comma
        \s*                 # Any whitespace
        (?:\#.*)?           # Optional `#` followed by anyanything
    )                       # Close `suffix` capture group
    $                       # End of line
    """,
    flags=re.VERBOSE | re.IGNORECASE | re.MULTILINE
)


def update_file(version: str, version_file: Path):
    """Update a single file with the new version number."""
    original_text = version_file.read_text(encoding="utf-8")
    updated_text, update_count = VERSION_REGEX.subn(
        r"\g<prefix>" + version + r"\g<suffix>",
        original_text
    )

    if update_count == 0:
        raise ValueError(f"Version regex not found in {version_file}!")

    if update_count > 1:
        # Find the different lines
        original_lines = original_text.splitlines()
        updated_lines = updated_text.splitlines()

        changed_pairs = [
            (orig, updated) for (orig, updated)
            in zip(original_lines, updated_lines)
            if orig != updated
        ]

        assert len(changed_pairs) == update_count
        logging.error("Multiple versions updated in %s", version_file)
        for orig, updated in changed_pairs:
            logging.debug("`%s` -> `%s`", orig, updated)

        raise ValueError(f"Multiple versions changed in {version_file}")

    logging.log(NOTICE, "Version updated in %s", version_file)
    version_file.write_text(updated_text, encoding="utf-8")

def update_files(repo_root: Path, version: str, files_str: str):
    """Update each of the files with the new version number."""
    version_files = [repo_root / item for item in files_str.split(",")]

    for version_file in version_files:
        full_version_file = version_file.resolve()

        # Make sure it is a tracked file
        if not full_version_file.is_relative_to(repo_root):
            raise ValueError(
                f"Version file {version_file} is not within the git repo"
            )

        # Make sure it's not under the .git folder (probably already covered by
        # the above) or the .github folder
        if {".git", ".github"} & set(full_version_file.parts):
            raise ValueError(
                f"Version file {version_file} is within a protected folder"
            )

        # Finally, make sure it is actually a file
        if not full_version_file.is_file():
            raise ValueError(f"Version file {version_file} does not exist")

        update_file(version, version_file)


def entrypoint():
    """Main entrypoint."""
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_root", type=Path)
    parser.add_argument("version", type=str)
    parser.add_argument("files", type=str)

    args = parser.parse_args()

    setup_logging()

    if not args.files:
        logging.debug("No version files need to be updated")
    else:
        try:
            update_files(args.repo_root.resolve(), args.version, args.files)
        except Exception:
            logging.exception("Error updating files")
            raise
