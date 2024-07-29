"Get the next tag version."

import os
import subprocess
from pathlib import Path

import semver


def get_next_tag():
    "Return the next tag after the appropriate bump type."
    repo_dir = os.environ["REPO_DIR"]
    bump_type = os.environ["BUMP_TYPE"]
    exact_version = os.environ["EXACT_VERSION"]
    output_file = Path(os.environ["GITHUB_OUTPUT"])

    if bump_type == "exact":
        return exact_version

    # Get the most recent ancestor tag
    last_tag = subprocess.check_output(
        ["git", "describe", "--tags", "--abbrev=0"],
        cwd=repo_dir
    ).decode("utf-8")

    last_version = semver.Version.parse(last_tag)
    next_version = last_version.next_version(part=bump_type)
    print(f"{last_version} -> {bump_type} -> {next_version}")

    with output_file.open(mode="w", encoding="utf-8") as outfile:
        outfile.write(f"next_version={next_version}\n")

if __name__ == "__main__":
    get_next_tag()
