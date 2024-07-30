"Get the next tag version."

import os
import subprocess
from pathlib import Path

import semver


def get_next_version():
    "Return the next tag after the appropriate bump type."
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
            print("WARNING: No prior tag found!")
            last_tag = "v0.0.0"

        # Strip off the leading v when parsing the version
        last_version = semver.Version.parse(last_tag[1:])
        next_version = str(last_version.next_version(part=bump_type))

    print(f"{last_version} -> {bump_type} -> {next_version}")

    with output_file.open(mode="w", encoding="utf-8") as outfile:
        outfile.write(f"next_version={next_version}\n")
