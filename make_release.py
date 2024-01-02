#!/bin/env python3

"""
Helper script to make a release

The script performs these actions:

1) Set version of the release into pyproject.py
2) Make a commit
3) Build the package (into dist/ subdirectory)
4) Make a git tag
5) Set the version in pyproject.py to the next version
6) Make another commit
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys


def get_script_dir() -> Path:
    """Return path to the script directory."""
    return Path(__file__).resolve().parent


def get_pyproject_path() -> Path:
    """Return path to the pyproject.toml file."""
    return get_script_dir() / "pyproject.toml"


def get_dist_path():
    """Return path to the "dist" subdirectory."""
    return get_script_dir() / "dist"


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("release_version", help="Current version of the release (e.g. 0.2.0)")
    parser.add_argument("next_version", help="Next version to use after the release (e.g. 0.3.0-dev)")
    return parser.parse_args()


def is_git_clean() -> bool:
    """Determine if git does not contain any uncommited changes."""
    return len(subprocess.check_output(["git", "status", "-s"]).strip()) == 0


def pyproject_set_version(version: str) -> None:
    """Modify the package version in the pyproject.toml file."""
    with get_pyproject_path().open("r") as f:
        lines = f.readlines()

    version_replaced = False
    for i, l in enumerate(lines):
        if l.startswith("version = "):
            lines[i] = "version = \"" + version + "\"\n"
            version_replaced = True
            break

    if not version_replaced:
        raise RuntimeError(
            "Could not find and replace version string "
            f"in file {get_pyproject_path()}"
        )
    
    get_pyproject_path().write_text("".join(lines))



def git_add(file_list) -> None:
    """Add file to the git staging."""
    subprocess.check_call(["git", "add"] + file_list)


def git_commit(msg) -> None:
    """Make a git commit."""
    subprocess.check_call(["git", "commit", "-m", msg, "-S"])


def git_tag(tag_name) -> None:
    """Make a git tag."""
    subprocess.check_call(["git", "tag", tag_name, "-s", "-m", ""])


def build_pkg() -> None:
    """Build the package."""
    subprocess.check_call([sys.executable, "-m", "build"])


def main() -> int:
    args = parse_args()

    os.chdir(get_script_dir())

    if not is_git_clean():
        raise RuntimeError("Repository contains uncommited changes")

    if get_dist_path().exists() and any(get_dist_path().iterdir()):
        raise RuntimeError("dist subdirectory exists and is non-empty, refusing to overwrite it")

    # Set version to release version
    pyproject_set_version(args.release_version)

    # Commit to git
    git_add([get_pyproject_path()])
    git_commit("Set version to: " + args.release_version)

    # Build the package
    build_pkg()

    # Make tag
    git_tag(args.release_version)

    # Set version to the next version
    pyproject_set_version(args.next_version)

    # Commit to git
    git_add([get_pyproject_path()])
    git_commit("Set version to: " + args.next_version)

    print()
    print("Done.")
    print()
    print("Now don't forget to:")
    print()
    print("- upload the release into PyPI:")
    print("    ./upload_release.sh --production")
    print()
    print("- push the changes to the remote:")
    print("    git push origin HEAD && git push origin " + args.release_version)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())